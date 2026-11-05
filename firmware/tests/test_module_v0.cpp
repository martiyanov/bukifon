// SPDX-License-Identifier: GPL-3.0-or-later
// Tests for Bukifon module API v0 (EXPERIMENTAL): ABI validation, lifecycle,
// state save/load, real-time budget and bypass, two example modules, Lua limits.
#include <cmath>
#include <cstring>
#include <vector>

#include "bukifon_module.h"
#include "modules/lua_layer.hpp"
#include "modules/module_host_v0.hpp"
#include "test_framework.hpp"

using namespace bukifon;

extern "C" const bukifon_module_v0_t* bukifon_module_v0_gain_fx(void);
extern "C" const bukifon_module_v0_t* bukifon_module_v0_lfo_mod(void);

namespace {

const bukifon_module_desc_t* g_baseDesc = nullptr;

const bukifon_module_desc_t* descBadApi() {
  static bukifon_module_desc_t d;
  d = *g_baseDesc;
  d.api_version = 1;
  return &d;
}
const bukifon_module_desc_t* descBadFrames() {
  static bukifon_module_desc_t d;
  d = *g_baseDesc;
  d.max_frames = 128;
  return &d;
}
const bukifon_module_desc_t* descBadStack() {
  static bukifon_module_desc_t d;
  d = *g_baseDesc;
  d.stack_bytes = BUKIFON_MODULE_MAX_STACK + 1;
  return &d;
}
const bukifon_module_desc_t* descBadState() {
  static bukifon_module_desc_t d;
  d = *g_baseDesc;
  d.state_size = BUKIFON_MODULE_MAX_STATE + 1;
  return &d;
}
const bukifon_module_desc_t* descBadParams() {
  static bukifon_module_desc_t d;
  d = *g_baseDesc;
  d.param_count = BUKIFON_MODULE_MAX_PARAMS + 1;
  return &d;
}
const bukifon_module_desc_t* descBadId() {
  static bukifon_module_desc_t d;
  d = *g_baseDesc;
  d.id = nullptr;
  return &d;
}
const bukifon_module_desc_t* descNullParams() {
  static bukifon_module_desc_t d;
  d = *g_baseDesc;
  d.param_count = 1;
  d.params = nullptr;
  return &d;
}

void fillSine(float* left, float* right, int frames, float freq = 220.0f) {
  for (int i = 0; i < frames; ++i) {
    const float v = 0.5f * std::sin(2.0f * 3.14159265f * freq * static_cast<float>(i) / 48000.0f);
    left[i] = v;
    right[i] = -v;
  }
}

bool finiteBuffers(const float* left, const float* right, int frames) {
  for (int i = 0; i < frames; ++i) {
    if (!std::isfinite(left[i]) || !std::isfinite(right[i])) return false;
  }
  return true;
}

}  // namespace

TEST(ModuleV0GainFxLifecycle) {
  const bukifon_module_v0_t* module = bukifon_module_v0_gain_fx();
  CHECK(module != nullptr);
  CHECK(module->api_version == BUKIFON_MODULE_API_VERSION);
  CHECK(module->descriptor != nullptr && module->create != nullptr && module->prepare != nullptr &&
        module->reset != nullptr && module->process != nullptr && module->set_param != nullptr &&
        module->state_size != nullptr && module->save_state != nullptr &&
        module->load_state != nullptr && module->destroy != nullptr);

  ModuleHostV0 host;
  CHECK(host.attach(module));
  const bukifon_module_desc_t* desc = host.descriptor();
  CHECK(desc != nullptr);
  CHECK(std::strcmp(desc->id, "gain_fx") == 0);
  CHECK(std::strcmp(desc->name, "GAIN FX") == 0);
  CHECK(desc->api_version == 0u);
  CHECK(desc->max_frames == BUKIFON_MODULE_MAX_FRAMES);
  CHECK(desc->param_count == 3);
  CHECK(host.paramCount() == 3);
  CHECK(host.paramDesc(0) != nullptr && host.paramDesc(0)->id == 0);
  CHECK(host.stateSize() > 0 && host.stateSize() <= BUKIFON_MODULE_MAX_STATE);
  CHECK(host.prepare(48000));
  CHECK(host.prepare(44100));

  float inL[128], inR[128], outL[128], outR[128];
  fillSine(inL, inR, 128);
  host.process(inL, inR, outL, outR, 128);  // > 64 frames: host must split
  CHECK(finiteBuffers(outL, outR, 128));
  double inEnergy = 0.0, outEnergy = 0.0, diff = 0.0;
  for (int i = 0; i < 128; ++i) {
    inEnergy += static_cast<double>(inL[i]) * inL[i];
    outEnergy += static_cast<double>(outL[i]) * outL[i];
    diff += std::fabs(outL[i] - inL[i]);
  }
  INFO("gain_fx: state=%u B, params=%u, energy in=%.4f out=%.4f diff=%.2f",
       host.stateSize(), host.paramCount(), std::sqrt(inEnergy / 128),
       std::sqrt(outEnergy / 128), diff);
  CHECK(outEnergy > 0.0);
  CHECK(diff > 0.01);  // the drive actually changes the signal
  CHECK(host.setParam(0, 0.0f));   // drive
  CHECK(host.setParam(1, 0.2f));   // tone
  CHECK(host.setParam(2, 1.0f));   // mix
  CHECK(!host.setParam(99, 0.5f)); // unknown parameter
}

TEST(ModuleV0StateSaveLoad) {
  ModuleHostV0 host;
  CHECK(host.attach(bukifon_module_v0_gain_fx()));
  CHECK(host.prepare(48000));
  const uint32_t size = host.stateSize();
  std::vector<uint8_t> saved(size, 0);
  CHECK(host.saveState(saved.data(), static_cast<uint32_t>(saved.size())));
  CHECK(host.setParam(0, 0.9f));
  std::vector<uint8_t> changed(size, 0);
  CHECK(host.saveState(changed.data(), static_cast<uint32_t>(changed.size())));
  CHECK(saved != changed);
  CHECK(host.loadState(saved.data(), static_cast<uint32_t>(saved.size())));
  std::vector<uint8_t> restored(size, 0);
  CHECK(host.saveState(restored.data(), static_cast<uint32_t>(restored.size())));
  CHECK(saved == restored);
  CHECK(!host.saveState(nullptr, 0));
  CHECK(!host.loadState(nullptr, 0));
  CHECK(!host.loadState(saved.data(), 0));
  INFO("gain_fx state: %u bytes, save/load roundtrip deterministic", size);
}

TEST(ModuleV0BudgetBypass) {
  ModuleHostV0 host;
  CHECK(host.attach(bukifon_module_v0_gain_fx()));
  CHECK(host.prepare(48000));
  host.setBudgetUs(800);
  host.setCostProvider([](uint32_t) { return 1000u; });
  float inL[128], inR[128], outL[128], outR[128];
  fillSine(inL, inR, 128);
  host.process(inL, inR, outL, outR, 128);
  INFO("module budget: overruns=%u bypassed=%d", host.overrunCount(), host.bypassed() ? 1 : 0);
  CHECK(host.overrunCount() == BUKIFON_MODULE_MAX_OVERRUNS);
  CHECK(host.bypassed());
  // Once bypassed the module output is the dry signal.
  fillSine(inL, inR, 64, 440.0f);
  for (int i = 0; i < 64; ++i) outL[i] = outR[i] = 1234.0f;
  host.process(inL, inR, outL, outR, 64);
  bool dry = true;
  for (int i = 0; i < 64; ++i) {
    if (std::fabs(outL[i] - inL[i]) > 1e-6f || std::fabs(outR[i] - inR[i]) > 1e-6f) dry = false;
  }
  CHECK(dry);
  host.clearBypass();
  CHECK(!host.bypassed());
  CHECK(host.overrunCount() == 0);
  // A module that stays inside the budget is not bypassed.
  ModuleHostV0 fast;
  CHECK(fast.attach(bukifon_module_v0_gain_fx()));
  CHECK(fast.prepare(48000));
  fast.setCostProvider([](uint32_t) { return 100u; });
  fast.process(inL, inR, outL, outR, 64);
  CHECK(!fast.bypassed());
  CHECK(fast.overrunCount() == 0);
}

TEST(ModuleV0RejectsInvalidAbi) {
  const bukifon_module_v0_t* good = bukifon_module_v0_gain_fx();
  g_baseDesc = good->descriptor();
  ModuleHostV0 host;
  CHECK(!host.attach(nullptr));
  bukifon_module_v0_t bad;
  bad = *good;
  bad.api_version = 99;
  CHECK(!host.attach(&bad));
  bad = *good;
  bad.create = nullptr;
  CHECK(!host.attach(&bad));
  bad = *good;
  bad.process = nullptr;
  CHECK(!host.attach(&bad));
  bad = *good;
  bad.descriptor = nullptr;
  CHECK(!host.attach(&bad));

  struct Case {
    const char* name;
    const bukifon_module_desc_t* (*fn)();
  };
  const Case cases[] = {
      {"api", descBadApi},           {"frames", descBadFrames},
      {"stack", descBadStack},       {"state", descBadState},
      {"params", descBadParams},     {"id", descBadId},
      {"paramPtr", descNullParams},
  };
  for (const Case& c : cases) {
    bad = *good;
    bad.descriptor = c.fn;
    ModuleHostV0 rejecting;
    const bool attached = rejecting.attach(&bad);
    INFO("invalid ABI case %s rejected=%d", c.name, attached ? 0 : 1);
    CHECK(!attached);
  }
  INFO("module ABI v0: invalid tables/descriptors rejected (%zu cases)", sizeof(cases) / sizeof(cases[0]) + 4);
}

TEST(ModuleV0LfoModulator) {
  const bukifon_module_v0_t* module = bukifon_module_v0_lfo_mod();
  CHECK(module != nullptr);
  ModuleHostV0 host;
  CHECK(host.attach(module));
  CHECK(host.prepare(48000));
  const bukifon_module_desc_t* desc = host.descriptor();
  CHECK(desc->kind == BUKIFON_KIND_MODULATOR);
  CHECK((desc->capabilities & BUKIFON_CAP_MODULATION) != 0);
  CHECK(desc->param_count == 3);
  host.setParam(0, 10.0f);  // rate
  host.setParam(1, 3.0f);   // square
  host.setParam(2, 1.0f);   // depth
  float inL[64] = {}, inR[64] = {};
  float outL[64], outR[64];
  bool finite = true;
  bool bipolar = true;
  float mn = 2.0f, mx = -2.0f;
  for (int block = 0; block < 100; ++block) {  // 6400 frames > one period @10 Hz
    host.process(inL, inR, outL, outR, 64);
    for (int i = 0; i < 64; ++i) {
      if (!std::isfinite(outL[i]) || !std::isfinite(outR[i])) finite = false;
      if (std::fabs(outL[i]) > 1.0001f) bipolar = false;
      mn = std::fmin(mn, outL[i]);
      mx = std::fmax(mx, outL[i]);
    }
  }
  INFO("lfo_mod: range [%.2f..%.2f], finite=%d", mn, mx, finite ? 1 : 0);
  CHECK(finite);
  CHECK(bipolar);
  CHECK(mn < -0.5f && mx > 0.5f);  // square LFO reaches both rails
  // Direct ABI call with too many frames must be rejected by the module.
  void* raw = module->create();
  CHECK(raw != nullptr);
  CHECK(module->prepare(raw, 48000) == 0);
  CHECK(module->process(raw, inL, outL, BUKIFON_MODULE_MAX_FRAMES + 1) == -2);
  module->destroy(raw);
}

TEST(LuaLayerInstructionLimits) {
  LuaLayer lua;
  lua.init();
  CHECK(!LuaLayer::interpreterAvailable());
  CHECK(lua.status() == LuaLayer::Status::Disabled);
  CHECK(!lua.load(nullptr, 0));
  // Script size limit.
  std::string big(LuaLayer::Limits{}.maxScriptBytes + 1, 'a');
  CHECK(!lua.load(big.c_str(), big.size()));
  CHECK(lua.status() == LuaLayer::Status::ScriptTooLarge);
  // Instruction limit at load time.
  LuaLayer tight;
  tight.init(LuaLayer::Limits( /*instructions=*/10));
  const char* script = "dddddddddddddddddddddddddddddd";  // 30 bytes -> ~15 instructions
  CHECK(!tight.load(script, std::strlen(script)));
  CHECK(tight.status() == LuaLayer::Status::InstructionLimit);
  // A small script is accepted and metered.
  LuaLayer normal;
  normal.init(LuaLayer::Limits(/*instructions=*/100));
  const char* small = "x = 1";
  CHECK(normal.load(small, std::strlen(small)));
  CHECK(normal.status() == LuaLayer::Status::Idle);
  const LuaLayer::Status s1 = normal.tick(1);
  CHECK(s1 == LuaLayer::Status::Running || s1 == LuaLayer::Status::Idle);
  CHECK(normal.instructionsExecuted() <= normal.instructionLimit());
  INFO("lua stub: limits instructions=%u script=%u, status=%s (interpreter not linked)",
       normal.instructionLimit(), normal.scriptBytes(), normal.statusName());
}
