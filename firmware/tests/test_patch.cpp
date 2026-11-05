// SPDX-License-Identifier: GPL-3.0-or-later
#include <cstring>
#include <vector>

#include "core/patch.hpp"
#include "test_framework.hpp"

using namespace bukifon;

TEST(PatchSizeAndLayout) {
  INFO("Patch serialized size = %zu bytes (limit %d)", kPatchSerializedBytes, kMaxPatchBytes);
  CHECK(kPatchSerializedBytes <= static_cast<size_t>(kMaxPatchBytes));
  Patch p;
  p.initDefault();
  uint8_t buf[kMaxPatchBytes];
  const size_t n = patchSerialize(p, buf, sizeof(buf));
  CHECK(n == kPatchSerializedBytes);
  CHECK(patchValidate(buf, n));
}

TEST(PatchRoundtrip) {
  Patch p;
  makeFactoryPatch(5, &p);
  p.name[15] = '\0';
  uint8_t buf[kMaxPatchBytes];
  const size_t n = patchSerialize(p, buf, sizeof(buf));
  Patch out;
  CHECK(patchDeserialize(buf, n, &out));
  CHECK(std::strncmp(p.name, out.name, 15) == 0);
  int worstParam = -1;
  double worstErr = 0.0;
  for (int part = 0; part < kNumParts; ++part) {
    for (int id = 0; id < kNumPartParams; ++id) {
      const ParamMeta& m = kPartParamMeta[id];
      const float a = p.parts[part].v[id];
      const float b = out.parts[part].v[id];
      if (m.flags & PF_DISCRETE) {
        CHECK(a == b);
      } else {
        const double range = static_cast<double>(m.max - m.min);
        const double rel = std::fabs(a - b) / range;
        if (rel > worstErr) {
          worstErr = rel;
          worstParam = id;
        }
      }
    }
  }
  INFO("patch roundtrip: worst non-discrete error %.4f%% of range on param %s", worstErr * 100.0,
       worstParam >= 0 ? kPartParamMeta[worstParam].name : "-");
  CHECK(worstErr < 0.01);  // 8-bit normalised storage: <= 1/255 of the range
  for (int id = 0; id < kModSlots; ++id) {
    CHECK(p.slots[id].source == out.slots[id].source);
    CHECK(p.slots[id].target == out.slots[id].target);
    CHECK(p.slots[id].depth == out.slots[id].depth);
    CHECK(p.slots[id].packed == out.slots[id].packed);
  }
}

TEST(PatchCrcDetection) {
  Patch p;
  p.initDefault();
  uint8_t buf[kMaxPatchBytes];
  const size_t n = patchSerialize(p, buf, sizeof(buf));
  CHECK(patchValidate(buf, n));
  buf[40] ^= 0xFF;
  CHECK(!patchValidate(buf, n));
  Patch out;
  CHECK(!patchDeserialize(buf, n, &out));
  CHECK(!patchValidate(buf, n - 1));
}

TEST(PatchSysEx) {
  Patch p;
  makeFactoryPatch(9, &p);
  uint8_t sysex[700];
  const size_t n = patchToSysEx(p, sysex, sizeof(sysex));
  INFO("SysEx dump: %zu bytes (7-bit packed, patch %zu bytes)", n, kPatchSerializedBytes);
  CHECK(n > 0);
  CHECK(n < sizeof(sysex));
  for (size_t i = 0; i < n; ++i) CHECK(sysex[i] < 0x80);
  Patch out;
  CHECK(patchFromSysEx(sysex, n, &out));
  CHECK(std::strncmp(p.name, out.name, 15) == 0);
  CHECK(p.global.v[Bpm] == out.global.v[Bpm] ||
        std::fabs(p.global.v[Bpm] - out.global.v[Bpm]) < 1.0f);
}

TEST(FactoryBank) {
  Patch bank[kNumFactoryPatches];
  makeFactoryBank(bank, kNumFactoryPatches);
  CHECK(bank[0].version == 1);
  bool uniqueNames = true;
  for (int i = 0; i < kNumFactoryPatches; ++i) {
    for (int j = i + 1; j < kNumFactoryPatches; ++j) {
      if (std::strncmp(bank[i].name, bank[j].name, 15) == 0) uniqueNames = false;
    }
  }
  INFO("factory bank: %d patches, unique names=%d, first='%s'", kNumFactoryPatches,
       uniqueNames ? 1 : 0, bank[0].name);
  CHECK(uniqueNames);
  // Every factory patch must serialise and validate.
  for (int i = 0; i < kNumFactoryPatches; ++i) {
    uint8_t buf[kMaxPatchBytes];
    const size_t n = patchSerialize(bank[i], buf, sizeof(buf));
    CHECK(patchValidate(buf, n));
  }
}
