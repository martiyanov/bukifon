// SPDX-License-Identifier: GPL-3.0-or-later
// 8 preset slots for the GEN page: write/read, host-file roundtrip, validation.
#include <cstdio>
#include <cstring>

#include "storage/preset_bank.hpp"
#include "test_framework.hpp"

using namespace bukifon;

namespace {

GenParams makeGen(uint32_t seed, uint8_t probability) {
  GenParams params;
  params.seed = seed;
  params.probability = probability;
  params.euclid = 5;
  params.mutate = 3;
  params.scale = GenScale::Dorian;
  params.evolve = true;
  params.arpOn = true;
  params.arpRate = GenArpRate32;
  params.arpMode = GenArpUpDown;
  return params;
}

}  // namespace

TEST(PresetBankSlotsWriteRead) {
  PresetBank bank;
  GenParams gen[kSeqTracks];
  for (int i = 0; i < kSeqTracks; ++i) gen[i] = makeGen(100 + i, 50 + i);
  CHECK(bank.usedCount() == 0);
  CHECK(bank.writeSlot(0, "TECHNO", gen, kSeqTracks, 0b0101u));
  CHECK(bank.writeSlot(7, "EVOLVE", gen, kSeqTracks, 0b1010u));
  CHECK(bank.usedCount() == 2);
  CHECK(bank.hasSlot(0));
  CHECK(bank.hasSlot(7));
  CHECK(!bank.hasSlot(1));
  CHECK(std::strcmp(bank.slotName(0), "TECHNO") == 0);
  CHECK(bank.slotIndexByName("EVOLVE") == 7);
  PresetSlot slot;
  CHECK(bank.readSlot(7, &slot));
  CHECK(slot.used);
  CHECK(slot.selectedParts == 0b1010u);
  CHECK(slot.gen[1].seed == 101u);
  CHECK(slot.gen[3].scale == GenScale::Dorian);
  INFO("preset bank: 8 slots, names, multi-select mask, per-part GenParams");
}

TEST(PresetBankHostFileRoundtrip) {
  const char* path = "../tests/out/preset_bank_test.bin";
  PresetBank bank;
  GenParams gen[kSeqTracks];
  for (int i = 0; i < kSeqTracks; ++i) gen[i] = makeGen(7 + i, 25 + i * 10);
  for (int slot = 0; slot < PresetBank::kSlots; ++slot) {
    char name[24];
    std::snprintf(name, sizeof(name), "SLOT%d", slot + 1);
    CHECK(bank.writeSlot(slot, name, gen, kSeqTracks, static_cast<uint8_t>(1u << (slot % 4))));
  }
  CHECK(bank.usedCount() == 8);
  CHECK(bank.save(path));
  PresetBank loaded;
  CHECK(loaded.load(path));
  CHECK(loaded.usedCount() == 8);
  PresetSlot slot;
  CHECK(loaded.readSlot(5, &slot));
  CHECK(std::strcmp(slot.name, "SLOT6") == 0);
  CHECK(slot.gen[2].probability == 45);
  CHECK(slot.gen[0].seed == 7);
  std::remove(path);
  INFO("preset bank: versioned host file roundtrip (8 slots, CRC32 header)");
}

TEST(PresetBankCorruptFileRejected) {
  const char* path = "../tests/out/preset_bank_corrupt.bin";
  std::FILE* file = std::fopen(path, "wb");
  CHECK(file != nullptr);
  if (file) {
    std::fputs("not a preset bank", file);
    std::fclose(file);
  }
  PresetBank bank;
  GenParams gen[kSeqTracks];
  CHECK(bank.writeSlot(0, "A", gen, kSeqTracks, 1));
  CHECK(!bank.load(path));       // bad magic
  CHECK(bank.usedCount() == 0);  // load failure clears the bank
  CHECK(!bank.load("../tests/out/no_such_presets.bin"));
  std::remove(path);
  INFO("preset bank: bad magic/short/missing file rejected; bank cleared");
}

TEST(PresetBankInvalidSlotArguments) {
  PresetBank bank;
  GenParams gen[kSeqTracks];
  char error[64];
  CHECK(!bank.writeSlot(-1, "X", gen, kSeqTracks, 1, error, sizeof(error)));
  CHECK(error[0] != '\0');
  CHECK(!bank.writeSlot(8, "X", gen, kSeqTracks, 1, error, sizeof(error)));
  CHECK(!bank.writeSlot(0, "", gen, kSeqTracks, 1, error, sizeof(error)));
  CHECK(!bank.writeSlot(0, "X", nullptr, kSeqTracks, 1, error, sizeof(error)));
  CHECK(!bank.writeSlot(0, "X", gen, 0, 1, error, sizeof(error)));
  CHECK(!bank.hasSlot(0));
  PresetSlot slot;
  CHECK(!bank.readSlot(0, &slot));
  CHECK(bank.slotIndexByName("missing") == -1);
  INFO("preset bank: bounds/empty name/null params/zero parts rejected");
}

TEST(PresetBankOverwriteAndAbCompareSources) {
  PresetBank bank;
  GenParams gen[kSeqTracks];
  gen[0] = makeGen(1, 10);
  CHECK(bank.writeSlot(2, "A", gen, kSeqTracks, 0b0001u));
  gen[0] = makeGen(2, 20);
  CHECK(bank.writeSlot(2, "B", gen, kSeqTracks, 0b0010u));
  CHECK(bank.usedCount() == 1);
  CHECK(std::strcmp(bank.slotName(2), "B") == 0);
  gen[0] = makeGen(3, 30);
  CHECK(bank.writeSlot(3, "B-ALT", gen, kSeqTracks, 0b0010u));
  PresetSlot a;
  PresetSlot b;
  CHECK(bank.readSlot(2, &a));
  CHECK(bank.readSlot(3, &b));
  CHECK(a.gen[0].probability == 20);
  CHECK(b.gen[0].probability == 30);
  // A/B compare slots can differ while sharing the selection mask.
  CHECK(a.selectedParts == b.selectedParts);
  INFO("preset bank: overwrite works, A/B compare can use two slots");
}
