// SPDX-License-Identifier: GPL-3.0-or-later
// Modulation definitions shared by engine, patch serialization and UI.
#pragma once

#include <cstdint>

#include "core/config.hpp"
#include "core/params.hpp"

namespace bukifon {

// 3D mod-matrix sources. Slot sources may reference other slots (feedback) and
// part outputs (cross-part modulation); the engine clamps/slews the result.
enum ModSource : uint8_t {
  MsNone = 0,
  MsEnv1, MsEnv2, MsEnv3, MsEnv4,
  MsLfo1, MsLfo2, MsLfo3, MsLfo4,
  MsRandom, MsSmoothRandom,
  MsVelocity, MsAftertouch, MsKeytrack, MsModWheel,
  MsCv1, MsCv2, MsCv3, MsCv4,
  MsMidiCc,
  MsSeqTrack1, MsSeqTrack2, MsSeqTrack3, MsSeqTrack4,
  MsSlotBase,                       // +0..kModSlots-1 -> previous block slot outputs
  MsPartOutBase = MsSlotBase + kModSlots,
  MsMacro1 = MsPartOutBase + kNumParts,
  MsMacro2, MsMacro3, MsMacro4,
  MsConstant,
  kNumModSources
};

// Target: part parameter id (< kNumPartParams), another slot's depth, or FX/seq.
enum ModTarget : uint8_t {
  MtPartParam = 0,                       // 0 .. kNumPartParams-1
  MtSlotDepth = kNumPartParams,          // +0..kModSlots-1
  MtFxDelayTime = MtSlotDepth + kModSlots,
  MtFxDelayFb,
  MtFxDelayMix,
  MtFxChorusDepth,
  MtFxDrive,
  MtFxLimiterThreshold,
  MtSeqSwing,
  MtSeqTranspose,
  kNumModTargets
};

enum ModCurve : uint8_t { McLinear = 0, McExp = 1, McLog = 2, McSCurve = 3 };

enum ModCondition : uint8_t {
  McAlways = 0,   // гейт/всегда
  McFirst,        // 1st
  McNotFirst,     // not-1st
  McFill,         // fill
  McNotFill,      // !fill
  McAB12, McAB13, McAB23, McAB14, McAB34,  // A:B trig conditions
  McPercent25, McPercent50, McPercent75,
  McEvery2, McEvery3, McEvery4,
  kNumModConditions
};

// Storage form of one matrix slot (5 bytes) — shared with the patch format.
struct ModSlotData {
  uint8_t source = MsNone;
  uint8_t target = MtPartParam;  // 0 = first part param, meaningless when source == None
  int8_t depth = 0;              // -100..+100
  uint8_t packed = 0;            // bits0..1 part, bits2..3 curve, bits4..7 condition
};

inline uint8_t modSlotPart(const ModSlotData& s) { return s.packed & 0x3; }
inline void modSlotSetPart(ModSlotData& s, uint8_t part) {
  s.packed = static_cast<uint8_t>((s.packed & ~0x3u) | (part & 0x3u));
}
inline ModCurve modSlotCurve(const ModSlotData& s) {
  return static_cast<ModCurve>((s.packed >> 2) & 0x3);
}
inline void modSlotSetCurve(ModSlotData& s, ModCurve c) {
  s.packed = static_cast<uint8_t>((s.packed & ~0x0Cu) | ((static_cast<uint8_t>(c) & 0x3u) << 2));
}
inline ModCondition modSlotCondition(const ModSlotData& s) {
  return static_cast<ModCondition>((s.packed >> 4) & 0x0F);
}
inline void modSlotSetCondition(ModSlotData& s, ModCondition c) {
  s.packed = static_cast<uint8_t>((s.packed & 0x0Fu) | ((static_cast<uint8_t>(c) & 0x0Fu) << 4));
}

const char* modSourceName(ModSource s);
const char* modTargetName(ModTarget t);
const char* modCurveName(ModCurve c);
const char* modConditionName(ModCondition c);

}  // namespace bukifon
