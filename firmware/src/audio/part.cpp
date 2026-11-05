// SPDX-License-Identifier: GPL-3.0-or-later
#include "audio/part.hpp"

#include <cmath>

#include "core/math.hpp"

namespace bukifon {
namespace {

// Small deterministic hash for percentage trig conditions (must be stable so
// that a bar's condition is the same at every block of that bar).
uint32_t hash32(uint32_t x) {
  x ^= x >> 16;
  x *= 0x7feb352du;
  x ^= x >> 15;
  x *= 0x846ca68bu;
  x ^= x >> 16;
  return x;
}

}  // namespace

void Part::init(int index, float sampleRate) {
  index_ = index;
  sampleRate_ = sampleRate;
  base_.reset();
  mod_ = base_;
  for (int i = 0; i < kNumEnvs; ++i) env_[i].init(sampleRate_);
  for (int i = 0; i < kNumLfos; ++i) lfo_[i].init(sampleRate_);
  for (int i = 0; i < kModSlots; ++i) {
    slots_[i].source = MsNone;
    slots_[i].target = 0;
    slots_[i].depth = 0;
    slots_[i].packed = 0;
  }
  reset();
}

void Part::reset() {
  for (int i = 0; i < kNumEnvs; ++i) env_[i].reset();
  for (int i = 0; i < kNumLfos; ++i) lfo_[i].reset();
  for (int i = 0; i < kNumEnvs; ++i) envLevel_[i] = 0.0f;
  for (int i = 0; i < kModSlots; ++i) {
    slotOut_[i] = 0.0f;
    slotPrev_[i] = 0.0f;
    slotDepthMod_[i] = 0.0f;
  }
  for (int i = 0; i < kNumPartParams; ++i) {
    mod_.v[i] = base_.v[i];
    offsets_[i] = 0.0f;
  }
  meter_ = 0.0f;
  gateOn_ = false;
}

void Part::setSlot(int index, const ModSlotData& slot) {
  if (index < 0 || index >= kModSlots) return;
  slots_[index] = slot;
}

void Part::setBaseParam(int id, float value) {
  if (id < 0 || id >= kNumPartParams) return;
  base_.v[id] = snapPartParam(id, value);
  mod_.v[id] = base_.v[id];
}

void Part::triggerNoteOn(float velocity, int note) {
  lastVelocity_ = math::clamp(velocity, 0.0f, 1.0f);
  lastNote_ = note;
  gateOn_ = true;
  for (int i = 0; i < kNumEnvs; ++i) env_[i].noteOn(lastVelocity_);
  for (int i = 0; i < kNumLfos; ++i) {
    lfo_[i].setParams(base_.v[Lfo1Rate + i * 6], static_cast<int>(base_.v[Lfo1Shape + i * 6] + 0.5f),
                      base_.v[Lfo1Sync + i * 6] > 0.5f, base_.v[Lfo1Retrig + i * 6] > 0.5f,
                      base_.v[Lfo1Keytrack + i * 6], base_.v[Lfo1Fade + i * 6], 120.0f);
    lfo_[i].noteOn(static_cast<float>(note));
  }
}

void Part::triggerNoteOff() {
  gateOn_ = false;
  for (int i = 0; i < kNumEnvs; ++i) env_[i].noteOff();
}

void Part::tickGenerators(int samples, float bpm) {
  for (int i = 0; i < kNumEnvs; ++i) {
    env_[i].setParams(base_.v[Env1A + i * 6], base_.v[Env1D + i * 6], base_.v[Env1S + i * 6],
                      base_.v[Env1R + i * 6], base_.v[Env1Curve + i * 6],
                      static_cast<int>(base_.v[Env1Mode + i * 6] + 0.5f));
    envLevel_[i] = env_[i].tickN(samples);
  }
  for (int i = 0; i < kNumLfos; ++i) {
    lfo_[i].setParams(base_.v[Lfo1Rate + i * 6], static_cast<int>(base_.v[Lfo1Shape + i * 6] + 0.5f),
                      base_.v[Lfo1Sync + i * 6] > 0.5f, base_.v[Lfo1Retrig + i * 6] > 0.5f,
                      base_.v[Lfo1Keytrack + i * 6], base_.v[Lfo1Fade + i * 6], bpm);
    lfo_[i].tickN(samples);
  }
}

float Part::applyCurve(float v, ModCurve curve) {
  const float s = (v < 0.0f) ? -1.0f : 1.0f;
  const float a = std::fabs(v);
  switch (curve) {
    case McExp:
      return s * a * a;
    case McLog:
      return s * std::sqrt(a);
    case McSCurve:
      return s * a * (1.5f - 0.5f * a * a);
    case McLinear:
    default:
      return v;
  }
}

bool Part::evaluateCondition(ModCondition cond, const ModContext& ctx, uint32_t slotIndex) {
  switch (cond) {
    case McAlways:
      return true;
    case McFirst:
      return ctx.firstOfBar;
    case McNotFirst:
      return !ctx.firstOfBar;
    case McFill:
      return ctx.fill;
    case McNotFill:
      return !ctx.fill;
    case McAB12:
      return (ctx.bar % 2) == 1;  // 2nd pass
    case McAB13:
      return (ctx.bar % 3) == 0;
    case McAB23:
      return (ctx.bar % 3) == 1;
    case McAB14:
      return (ctx.bar % 4) == 0;
    case McAB34:
      return (ctx.bar % 4) == 2;
    case McPercent25:
      return (hash32(ctx.bar * 2654435761u + slotIndex) % 100u) < 25u;
    case McPercent50:
      return (hash32(ctx.bar * 2654435761u + slotIndex) % 100u) < 50u;
    case McPercent75:
      return (hash32(ctx.bar * 2654435761u + slotIndex) % 100u) < 75u;
    case McEvery2:
      return (ctx.bar % 2) == 0;
    case McEvery3:
      return (ctx.bar % 3) == 0;
    case McEvery4:
      return (ctx.bar % 4) == 0;
    default:
      return true;
  }
}

float Part::evaluateSource(uint8_t source, const ModContext& ctx,
                           const float globalSources[kNumModSources]) const {
  if (source >= MsSlotBase && source < MsSlotBase + kModSlots) {
    return slotPrev_[source - MsSlotBase];  // one block of delay: stable feedback
  }
  if (source >= MsPartOutBase && source < MsPartOutBase + kNumParts) {
    return ctx.partOut[source - MsPartOutBase];
  }
  if (source >= MsMacro1 && source <= MsMacro4) {
    return ctx.macros[source - MsMacro1];
  }
  if (source == MsEnv1) return envLevel_[0];
  if (source == MsEnv2) return envLevel_[1];
  if (source == MsEnv3) return envLevel_[2];
  if (source == MsEnv4) return envLevel_[3];
  if (source >= MsLfo1 && source <= MsLfo4) return lfo_[source - MsLfo1].value();
  if (source == MsVelocity) return ctx.velocity;
  if (source == MsAftertouch) return ctx.aftertouch;
  if (source == MsKeytrack) return ctx.keytrack;
  if (source == MsModWheel) return ctx.modWheel;
  if (source == MsMidiCc) return ctx.midiCc;
  if (source >= MsCv1 && source <= MsCv4) return ctx.cv[source - MsCv1];
  if (source >= MsSeqTrack1 && source <= MsSeqTrack4) return ctx.seqTrack[source - MsSeqTrack1];
  if (source == MsConstant) return 1.0f;
  if (source == MsNone) return 0.0f;
  if (source < kNumModSources) return globalSources[source];
  return 0.0f;
}

void Part::evaluateSlots(const ModContext& ctx, float globalSources[kNumModSources]) {
  for (int s = 0; s < kModSlots; ++s) {
    slotPrev_[s] = slotOut_[s];
    slotOut_[s] = 0.0f;
  }
  for (int s = 0; s < kModSlots; ++s) {
    const ModSlotData& slot = slots_[s];
    if (slot.source == MsNone) continue;
    float v = evaluateSource(slot.source, ctx, globalSources);
    v = applyCurve(math::clamp(v, -1.0f, 1.0f), modSlotCurve(slot));
    // Slot depth can itself be modulated (matrix "modulation of modulation").
    const float depthMod = math::clamp(slotDepthMod_[s], -1.0f, 1.0f);
    float depth = static_cast<float>(slot.depth) / 100.0f;
    depth *= (1.0f + depthMod * 0.95f);
    if (!evaluateCondition(modSlotCondition(slot), ctx, static_cast<uint32_t>(s))) v = 0.0f;
    // Hard limiting keeps positive feedback finite.
    slotOut_[s] = math::clamp(v * depth, -4.0f, 4.0f);
  }
}

float Part::modulatedValue(int id, float base, float offset) {
  const ParamMeta& m = kPartParamMeta[id];
  if (offset == 0.0f) return base;
  if (id == Cutoff) {
    // Cutoff modulation in octaves (offset 1.0 = +6 octaves).
    return math::clamp(base * std::pow(2.0f, offset * 6.0f), m.min, m.max);
  }
  if (m.flags & PF_LOG) {
    return math::clamp(base * std::pow(2.0f, offset * 4.0f), m.min, m.max);
  }
  float v = base + offset * (m.max - m.min);
  if (m.flags & PF_DISCRETE) v = std::round(v);
  return math::clamp(v, m.min, m.max);
}

void Part::applyOffsets(const float* paramOffsets, const float* slotDepthOffsets) {
  for (int i = 0; i < kNumPartParams; ++i) {
    // Limit total modulation per parameter and smooth it (no clipping/zipper).
    float target = math::clamp(paramOffsets[i], -4.0f, 4.0f);
    offsets_[i] += (target - offsets_[i]) * 0.25f;
    mod_.v[i] = modulatedValue(i, base_.v[i], offsets_[i]);
  }
  for (int s = 0; s < kModSlots; ++s) {
    slotDepthMod_[s] = math::clamp(slotDepthOffsets[s], -1.0f, 1.0f);
  }
}

}  // namespace bukifon
