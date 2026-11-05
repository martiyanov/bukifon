// SPDX-License-Identifier: GPL-3.0-or-later
#include "core/patch.hpp"

#include <cstring>

#include "core/math.hpp"

namespace bukifon {
namespace {

constexpr const char* kFactoryNames[kNumFactoryPatches] = {
    "Init",       "Fat Saw",   "FM Bell",   "Poly Vox",  "Sub Bass", "Ladder Lead",
    "Glass Pad",  "Digi Keys", "Mod Seq",   "Wide Choir", "Acid",    "FM Brass",
    "Night Pad",  "Pluck",     "Drone",     "Kitchen"};

inline uint8_t toU8(const ParamMeta& m, float value) {
  return static_cast<uint8_t>(math::clamp(paramToNorm(m, value) * 255.0f + 0.5f, 0.0f, 255.0f));
}
inline float fromU8(const ParamMeta& m, uint8_t value) {
  return paramFromNorm(m, static_cast<float>(value) / 255.0f);
}

}  // namespace

uint16_t crc16Ccitt(const uint8_t* data, size_t size) {
  uint16_t crc = 0xFFFFu;
  for (size_t i = 0; i < size; ++i) {
    crc ^= static_cast<uint16_t>(data[i]) << 8;
    for (int b = 0; b < 8; ++b) {
      crc = (crc & 0x8000u) ? static_cast<uint16_t>((crc << 1) ^ 0x1021u)
                            : static_cast<uint16_t>(crc << 1);
    }
  }
  return crc;
}

void Patch::initDefault() {
  version = 1;
  flags = 0;
  std::memset(name, 0, sizeof(name));
  std::strncpy(name, "Init", sizeof(name) - 1);
  for (int p = 0; p < kNumParts; ++p) parts[p].reset();
  global.reset();
  for (int i = 0; i < kModSlots; ++i) {
    slots[i].source = MsNone;
    slots[i].target = 0;
    slots[i].depth = 0;
    slots[i].packed = 0;
  }
  // A couple of useful default routings: LFO1 -> cutoff, velocity -> cutoff,
  // envelope 2 -> cutoff depth (audible, test-friendly defaults).
  slots[0].source = MsLfo1;
  slots[0].target = Cutoff;
  slots[0].depth = 20;
  modSlotSetPart(slots[0], 0);
  modSlotSetCurve(slots[0], McLinear);
  slots[1].source = MsVelocity;
  slots[1].target = Cutoff;
  slots[1].depth = 35;
  modSlotSetPart(slots[1], 0);
  slots[2].source = MsEnv2;
  slots[2].target = Cutoff;
  slots[2].depth = 40;
  modSlotSetPart(slots[2], 0);
  modSlotSetCurve(slots[2], McExp);
}

size_t patchSerialize(const Patch& patch, uint8_t* out, size_t capacity) {
  if (capacity < kPatchSerializedBytes) return 0;
  size_t i = 0;
  out[i++] = patch.version;
  out[i++] = patch.flags;
  for (int n = 0; n < 16; ++n) out[i++] = static_cast<uint8_t>(patch.name[n]);
  for (int p = 0; p < kNumParts; ++p) {
    for (int k = 0; k < kNumPartParams; ++k) {
      out[i++] = toU8(kPartParamMeta[k], patch.parts[p].v[k]);
    }
  }
  for (int k = 0; k < kNumGlobalParams; ++k) {
    out[i++] = toU8(kGlobalParamMeta[k], patch.global.v[k]);
  }
  for (int s = 0; s < kModSlots; ++s) {
    out[i++] = patch.slots[s].source;
    out[i++] = patch.slots[s].target;
    out[i++] = static_cast<uint8_t>(patch.slots[s].depth);
    out[i++] = patch.slots[s].packed;
    out[i++] = 0;  // reserved for future slot fields
  }
  const uint16_t crc = crc16Ccitt(out, i);
  out[i++] = static_cast<uint8_t>(crc & 0xFF);
  out[i++] = static_cast<uint8_t>(crc >> 8);
  return i;
}

bool patchValidate(const uint8_t* data, size_t size) {
  if (!data || size != kPatchSerializedBytes) return false;
  const uint16_t stored =
      static_cast<uint16_t>(data[size - 2]) | (static_cast<uint16_t>(data[size - 1]) << 8);
  return crc16Ccitt(data, size - 2) == stored;
}

bool patchDeserialize(const uint8_t* data, size_t size, Patch* out) {
  if (!out || !patchValidate(data, size)) return false;
  Patch patch;
  size_t i = 0;
  patch.version = data[i++];
  patch.flags = data[i++];
  if (patch.version != 1) return false;
  for (int n = 0; n < 16; ++n) patch.name[n] = static_cast<char>(data[i++]);
  patch.name[15] = '\0';
  for (int p = 0; p < kNumParts; ++p) {
    for (int k = 0; k < kNumPartParams; ++k) {
      patch.parts[p].v[k] = fromU8(kPartParamMeta[k], data[i++]);
    }
  }
  for (int k = 0; k < kNumGlobalParams; ++k) {
    patch.global.v[k] = fromU8(kGlobalParamMeta[k], data[i++]);
  }
  for (int s = 0; s < kModSlots; ++s) {
    patch.slots[s].source = data[i++];
    patch.slots[s].target = data[i++];
    patch.slots[s].depth = static_cast<int8_t>(data[i++]);
    patch.slots[s].packed = data[i++];
    ++i;  // reserved
  }
  *out = patch;
  return true;
}

size_t patchToSysEx(const Patch& patch, uint8_t* out, size_t capacity) {
  uint8_t raw[kPatchSerializedBytes];
  const size_t rawSize = patchSerialize(patch, raw, sizeof(raw));
  if (rawSize == 0) return 0;
  // 7-bit packing: every 7 bytes become 8 SysEx data bytes.
  const size_t packed = (rawSize * 8 + 6) / 7;
  if (capacity < packed) return 0;
  size_t o = 0;
  for (size_t group = 0; group < rawSize; group += 7) {
    uint8_t msb = 0;
    for (size_t b = 0; b < 7; ++b) {
      if (group + b < rawSize && (raw[group + b] & 0x80)) msb |= static_cast<uint8_t>(1u << b);
    }
    out[o++] = msb;
    for (size_t b = 0; b < 7 && group + b < rawSize; ++b) {
      out[o++] = static_cast<uint8_t>(raw[group + b] & 0x7F);
    }
  }
  return o;
}

bool patchFromSysEx(const uint8_t* sysexPayload, size_t size, Patch* out) {
  if (!out || size < 8) return false;
  uint8_t raw[kPatchSerializedBytes];
  size_t rawSize = 0;
  for (size_t group = 0; group < size; group += 8) {
    const uint8_t msb = sysexPayload[group];
    const size_t payload = (size - group - 1 < 7) ? (size - group - 1) : 7;
    for (size_t b = 0; b < payload && rawSize < sizeof(raw); ++b) {
      uint8_t v = sysexPayload[group + 1 + b];
      if (msb & (1u << b)) v |= 0x80;
      raw[rawSize++] = v;
    }
  }
  return patchDeserialize(raw, rawSize, out);
}

void makeFactoryPatch(int index, Patch* out) {
  if (!out) return;
  index = math::clampInt(index, 0, kNumFactoryPatches - 1);
  Patch patch;
  patch.initDefault();
  std::memset(patch.name, 0, sizeof(patch.name));
  std::strncpy(patch.name, kFactoryNames[index], sizeof(patch.name) - 1);

  for (int p = 0; p < kNumParts; ++p) {
    PartParams& pp = patch.parts[p];
    pp.set(Osc1Wave, static_cast<float>((index + p) % kNumWaves));
    pp.set(Osc2Wave, static_cast<float>((index * 3 + p + 4) % kNumWaves));
    pp.set(Osc2Level, (index % 3 == 0) ? 0.4f : 0.0f);
    pp.set(Cutoff, 400.0f * std::pow(2.0f, static_cast<float>((index + p) % 6)));
    pp.set(Resonance, 0.2f + 0.08f * static_cast<float>((index + p) % 5));
    pp.set(FilterChar, static_cast<float>((index + p) % 3));
    pp.set(FmAlgorithm, static_cast<float>((index + p) % kFmAlgorithms));
    pp.set(FmMode, (index % 4 == 1) ? 2.0f : ((index % 4 == 0) ? 1.0f : 0.0f));
    pp.set(FmRatio1, 1.0f);
    pp.set(FmRatio2, 1.0f + static_cast<float>(index % 4));
    pp.set(FmRatio3, 2.0f);
    pp.set(FmRatio4, 3.0f + static_cast<float>(p));
    pp.set(Env1A, 0.002f + 0.01f * static_cast<float>(index % 5));
    pp.set(Env1D, 0.2f + 0.1f * static_cast<float>(index % 4));
    pp.set(Env1S, 0.5f + 0.1f * static_cast<float>(index % 3));
    pp.set(Env1R, 0.3f + 0.1f * static_cast<float>(index % 4));
    pp.set(EnsembleAmount, (index % 5 == 3) ? 0.6f : 0.0f);
    pp.set(EnsembleRate, 0.4f + 0.1f * static_cast<float>(index % 4));
    pp.set(PartPan, (p % 2 == 0) ? -0.35f : 0.35f);
    pp.set(PartLevel, 0.7f);
    for (int l = 0; l < kNumLfos; ++l) {
      pp.set(Lfo1Rate + l * 6, 0.2f * std::pow(2.0f, static_cast<float>((index + l) % 5)));
    }
  }
  patch.global.set(FxDelayTime, 0.15f + 0.05f * static_cast<float>(index % 8));
  patch.global.set(FxDelayMix, (index % 3 == 0) ? 0.35f : 0.15f);
  patch.global.set(FxChorusMix, 0.25f);
  *out = patch;
}

void makeFactoryBank(Patch* out, int count) {
  if (!out) return;
  count = math::clampInt(count, 0, kNumFactoryPatches);
  for (int i = 0; i < count; ++i) makeFactoryPatch(i, &out[i]);
}

}  // namespace bukifon
