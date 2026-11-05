// SPDX-License-Identifier: GPL-3.0-or-later
#include "core/params.hpp"

#include <cmath>
#include <cstring>

#include "core/math.hpp"

namespace bukifon {
namespace {



}  // namespace

#define PM_META(name, label, lo, hi, def, flags) {label, lo, hi, def, flags},
const ParamMeta kPartParamMeta[kNumPartParams] = {BUKIFON_PART_PARAM_LIST(PM_META)};
const ParamMeta kGlobalParamMeta[kNumGlobalParams] = {BUKIFON_GLOBAL_PARAM_LIST(PM_META)};
#undef PM_META

void PartParams::reset() {
  for (int i = 0; i < kNumPartParams; ++i) v[i] = kPartParamMeta[i].def;
}
void PartParams::set(int id, float value) {
  if (id < 0 || id >= kNumPartParams) return;
  v[id] = snapPartParam(id, value);
}
void GlobalParams::reset() {
  for (int i = 0; i < kNumGlobalParams; ++i) v[i] = kGlobalParamMeta[i].def;
}
void GlobalParams::set(int id, float value) {
  if (id < 0 || id >= kNumGlobalParams) return;
  v[id] = snapGlobalParam(id, value);
}

float paramToNorm(const ParamMeta& m, float value) {
  value = math::clamp(value, m.min, m.max);
  if (m.flags & PF_DISCRETE) {
    const float range = (m.max - m.min);
    return range > 0.0f ? (value - m.min) / range : 0.0f;
  }
  if (m.flags & PF_LOG) {
    const float lo = m.min > 0.0f ? m.min : 1e-4f;
    const float hi = m.max > lo ? m.max : lo * 10.0f;
    value = math::clamp(value, lo, hi);
    return std::log(value / lo) / std::log(hi / lo);
  }
  // Bipolar params (e.g. -1..+1) are stored as plain linear normalised value.
  const float range = m.max - m.min;
  return range > 0.0f ? (value - m.min) / range : 0.0f;
}

float paramFromNorm(const ParamMeta& m, float norm) {
  norm = math::clamp(norm, 0.0f, 1.0f);
  float v;
  if (m.flags & PF_LOG) {
    const float lo = m.min > 0.0f ? m.min : 1e-4f;
    const float hi = m.max > lo ? m.max : lo * 10.0f;
    v = lo * std::pow(hi / lo, norm);
  } else {
    v = m.min + (m.max - m.min) * norm;
  }
  if (m.flags & PF_DISCRETE) v = std::round(v);
  return math::clamp(v, m.min, m.max);
}

float snapPartParam(int id, float value) {
  if (id < 0 || id >= kNumPartParams) return value;
  const ParamMeta& m = kPartParamMeta[id];
  value = math::clamp(value, m.min, m.max);
  if (m.flags & PF_DISCRETE) value = std::round(value);
  return value;
}

float snapGlobalParam(int id, float value) {
  if (id < 0 || id >= kNumGlobalParams) return value;
  const ParamMeta& m = kGlobalParamMeta[id];
  value = math::clamp(value, m.min, m.max);
  if (m.flags & PF_DISCRETE) value = std::round(value);
  return value;
}

float clampPartParam(int id, float value) {
  if (id < 0 || id >= kNumPartParams) return value;
  const ParamMeta& m = kPartParamMeta[id];
  return math::clamp(value, m.min, m.max);
}

float clampGlobalParam(int id, float value) {
  if (id < 0 || id >= kNumGlobalParams) return value;
  const ParamMeta& m = kGlobalParamMeta[id];
  return math::clamp(value, m.min, m.max);
}

}  // namespace bukifon
