// SPDX-License-Identifier: GPL-3.0-or-later
#include "core/modulation_defs.hpp"

namespace bukifon {

const char* modSourceName(ModSource s) {
  switch (s) {
    case MsNone: return "NONE";
    case MsEnv1: return "ENV1";
    case MsEnv2: return "ENV2";
    case MsEnv3: return "ENV3";
    case MsEnv4: return "ENV4";
    case MsLfo1: return "LFO1";
    case MsLfo2: return "LFO2";
    case MsLfo3: return "LFO3";
    case MsLfo4: return "LFO4";
    case MsRandom: return "RANDOM";
    case MsSmoothRandom: return "S&H";
    case MsVelocity: return "VELO";
    case MsAftertouch: return "AFTERTOUCH";
    case MsKeytrack: return "KEYTRACK";
    case MsModWheel: return "MODWHEEL";
    case MsCv1: return "CV1";
    case MsCv2: return "CV2";
    case MsCv3: return "CV3";
    case MsCv4: return "CV4";
    case MsMidiCc: return "MIDI CC";
    case MsSeqTrack1: return "SEQ1";
    case MsSeqTrack2: return "SEQ2";
    case MsSeqTrack3: return "SEQ3";
    case MsSeqTrack4: return "SEQ4";
    case MsMacro1: return "MACRO1";
    case MsMacro2: return "MACRO2";
    case MsMacro3: return "MACRO3";
    case MsMacro4: return "MACRO4";
    case MsConstant: return "CONST";
    default: break;
  }
  if (s >= MsSlotBase && s < MsSlotBase + kModSlots) {
    static const char* kSlotNames[kModSlots] = {
        "SLOT1",  "SLOT2",  "SLOT3",  "SLOT4",  "SLOT5",  "SLOT6",  "SLOT7",  "SLOT8",
        "SLOT9",  "SLOT10", "SLOT11", "SLOT12", "SLOT13", "SLOT14", "SLOT15", "SLOT16"};
    return kSlotNames[s - MsSlotBase];
  }
  if (s >= MsPartOutBase && s < MsPartOutBase + kNumParts) {
    static const char* kPartNames[kNumParts] = {"PART1", "PART2", "PART3", "PART4"};
    return kPartNames[s - MsPartOutBase];
  }
  return "?";
}

const char* modTargetName(ModTarget t) {
  if (static_cast<int>(t) < static_cast<int>(kNumPartParams)) return kPartParamMeta[t].name;
  if (t >= MtSlotDepth && t < MtSlotDepth + kModSlots) {
    static const char* kSlotNames[kModSlots] = {
        "SLOT1 DP",  "SLOT2 DP",  "SLOT3 DP",  "SLOT4 DP",  "SLOT5 DP",  "SLOT6 DP",
        "SLOT7 DP",  "SLOT8 DP",  "SLOT9 DP",  "SLOT10 DP", "SLOT11 DP", "SLOT12 DP",
        "SLOT13 DP", "SLOT14 DP", "SLOT15 DP", "SLOT16 DP"};
    return kSlotNames[t - MtSlotDepth];
  }
  switch (t) {
    case MtFxDelayTime: return "DELAY TIME";
    case MtFxDelayFb: return "DELAY FB";
    case MtFxDelayMix: return "DELAY MIX";
    case MtFxChorusDepth: return "CHORUS DEPTH";
    case MtFxDrive: return "FX DRIVE";
    case MtFxLimiterThreshold: return "LIMITER";
    case MtSeqSwing: return "SWING";
    case MtSeqTranspose: return "TRANSPOSE";
    default: return "?";
  }
}

const char* modCurveName(ModCurve c) {
  switch (c) {
    case McLinear: return "LIN";
    case McExp: return "EXP";
    case McLog: return "LOG";
    case McSCurve: return "S-CURVE";
  }
  return "?";
}

const char* modConditionName(ModCondition c) {
  switch (c) {
    case McAlways: return "ALWAYS";
    case McFirst: return "1ST";
    case McNotFirst: return "NOT 1ST";
    case McFill: return "FILL";
    case McNotFill: return "!FILL";
    case McAB12: return "1:2";
    case McAB13: return "1:3";
    case McAB23: return "2:3";
    case McAB14: return "1:4";
    case McAB34: return "3:4";
    case McPercent25: return "25%";
    case McPercent50: return "50%";
    case McPercent75: return "75%";
    case McEvery2: return "EVERY 2";
    case McEvery3: return "EVERY 3";
    case McEvery4: return "EVERY 4";
    default: return "?";
  }
}

}  // namespace bukifon
