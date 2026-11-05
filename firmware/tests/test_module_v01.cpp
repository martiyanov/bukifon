// SPDX-License-Identifier: GPL-3.0-or-later
// Module API v0.1 tests: host services, events, parameter smoothing, new
// examples (grain FX, SVF filter), lifecycle/budget/state and v0 compatibility.
#include <cmath>
#include <cstring>

#include "modules/module_host_v0.hpp"
#include "test_framework.hpp"

using namespace bukifon;

namespace {

// --- recording test module (v0.1 table) -----------------------------------
bool gLogInsideProcess = false;

struct Recorder {
  float params[2] = {0.0f, 0.0f};
  float lastParam[2] = {0.0f, 0.0f};
  uint32_t events = 0;
  uint32_t lastType = 0;
  uint32_t processCalls = 0;
  uint32_t nowCalls = 0;
  bool logInsideProcess = false;
  const bukifon_host_services_t* services = nullptr;
};

const bukifon_param_desc_t kRecParams[2] = {
    {0, 0, 0, "P0", 0.0f, 1.0f, 0.0f, "%"},
    {1, 0, 0, "P1", 0.0f, 1.0f, 0.0f, "%"},
};

const bukifon_module_desc_t kRecDesc = {
    BUKIFON_MODULE_API_VERSION, BUKIFON_KIND_UTILITY,
    BUKIFON_CAP_AUDIO_IN | BUKIFON_CAP_AUDIO_OUT, BUKIFON_MODULE_MAX_FRAMES, 512, 64,
    "recorder", "RECORDER", "0.1.0", "tests", kRecParams, 2};

const bukifon_module_desc_t* recDescriptor(void) { return &kRecDesc; }
void* recCreate(void) { return new Recorder(); }
int recPrepare(void* instance, uint32_t) { return instance ? 0 : -1; }
void recReset(void* instance) {
  Recorder* r = static_cast<Recorder*>(instance);
  if (!r) return;
  r->events = 0;
  r->processCalls = 0;
}
int recProcess(void* instance, const float* in, float* out, uint32_t frames) {
  Recorder* r = static_cast<Recorder*>(instance);
  if (!r) return -1;
  ++r->processCalls;
  if (gLogInsideProcess && r->services && r->services->log) {
    r->services->log(r->services->context, 0, "log from audio path");
  }
  for (uint32_t i = 0; i < frames * 2; ++i) {
    out[i] = (in ? in[i] : 0.0f) * 0.5f;
  }
  return 0;
}
void recSetParam(void* instance, uint16_t id, float value) {
  Recorder* r = static_cast<Recorder*>(instance);
  if (!r || id > 1) return;
  r->lastParam[id] = value;
  r->params[id] = value;
}
uint32_t recStateSize(void*) { return 16; }
int recSaveState(void* instance, uint8_t* out, uint32_t cap) {
  Recorder* r = static_cast<Recorder*>(instance);
  if (!r || !out || cap < 16) return -1;
  std::memcpy(out, r->params, sizeof(float) * 2);
  std::memcpy(out + 8, &r->events, sizeof(uint32_t));
  return 16;
}
int recLoadState(void* instance, const uint8_t* data, uint32_t size) {
  Recorder* r = static_cast<Recorder*>(instance);
  if (!r || !data || size < 16) return -1;
  std::memcpy(r->params, data, sizeof(float) * 2);
  std::memcpy(&r->events, data + 8, sizeof(uint32_t));
  return 0;
}
void recDestroy(void* instance) { delete static_cast<Recorder*>(instance); }
int recAttachHost(void* instance, const bukifon_host_services_t* services) {
  Recorder* r = static_cast<Recorder*>(instance);
  if (!r || !services) return -1;
  r->services = services;
  if (services->now_us) r->nowCalls += static_cast<uint32_t>(services->now_us(services->context) > 0);
  if (services->log) services->log(services->context, 2, "recorder attached");
  return 0;
}
void recOnEvent(void* instance, const bukifon_event_t* event) {
  Recorder* r = static_cast<Recorder*>(instance);
  if (!r || !event) return;
  ++r->events;
  r->lastType = event->type;
}

const bukifon_module_v0_t kRecorder = {
    BUKIFON_MODULE_API_VERSION, recDescriptor, recCreate, recPrepare, recReset, recProcess,
    recSetParam, recStateSize, recSaveState, recLoadState, recDestroy, recAttachHost, recOnEvent};

extern "C" const bukifon_module_v0_t* bukifon_module_v0_grain_fx(void);
extern "C" const bukifon_module_v0_t* bukifon_module_v0_svf_filter(void);
extern "C" const bukifon_module_v0_t* bukifon_module_v0_gain_fx(void);
extern "C" const bukifon_module_v0_t* bukifon_module_v0_lfo_mod(void);

void runHostBlocks(ModuleHostV0& host, int blocks) {
  float l[64];
  float r[64];
  float ol[64];
  float orr[64];
  for (int b = 0; b < blocks; ++b) {
    for (int i = 0; i < 64; ++i) {
      l[i] = std::sin(0.1f * static_cast<float>(i + b));
      r[i] = -l[i];
    }
    host.process(l, r, ol, orr, 64);
  }
}

}  // namespace

TEST(ModuleV01ConstantsAndCompatibility) {
  CHECK(BUKIFON_MODULE_API_VERSION == 0u);
  CHECK(BUKIFON_MODULE_API_MINOR == 1u);
  CHECK(BUKIFON_EVENT_NOTE_ON == 1);
  CHECK(BUKIFON_EVENT_TRANSPORT_START == 5);
  const bukifon_module_v0_t* grain = bukifon_module_v0_grain_fx();
  const bukifon_module_v0_t* svf = bukifon_module_v0_svf_filter();
  const bukifon_module_v0_t* gain = bukifon_module_v0_gain_fx();
  CHECK(grain && grain->attach_host && grain->on_event);
  CHECK(svf && svf->attach_host && svf->on_event);
  CHECK(gain && gain->attach_host == nullptr && gain->on_event == nullptr);  // v0 module
  CHECK(grain->descriptor()->state_size <= BUKIFON_MODULE_MAX_STATE);
  INFO("Module API v0.1: ABI major 0 + minor 1, 12 callbacks, v0 modules unchanged");
}

TEST(ModuleV01GrainFxLifecycleAndState) {
  ModuleHostV0 host;
  CHECK(host.attach(bukifon_module_v0_grain_fx()));
  CHECK(host.prepare(48000));
  CHECK(host.hostServicesAttached());  // grain_fx implements attach_host (v0.1)
  CHECK(host.logMessages() >= 1);
  runHostBlocks(host, 8);
  CHECK(host.overrunCount() == 0);
  const uint32_t size = host.stateSize();
  CHECK(size > 0 && size <= BUKIFON_MODULE_MAX_STATE);
  uint8_t state[4096];
  CHECK(host.saveState(state, sizeof(state)));
  host.setParam(2, 0.9f);
  CHECK(host.loadState(state, size));
  uint8_t again[4096];
  CHECK(host.saveState(again, sizeof(again)));
  CHECK(std::memcmp(state, again, size) == 0);
  INFO("grain_fx: lifecycle/state OK (%u bytes state)", size);
}

TEST(ModuleV01SvfLifecycleAndState) {
  ModuleHostV0 host;
  CHECK(host.attach(bukifon_module_v0_svf_filter()));
  CHECK(host.prepare(48000));
  runHostBlocks(host, 8);
  CHECK(host.paramCount() == 4);
  uint8_t a[4096];
  uint8_t b[4096];
  const uint32_t size = host.stateSize();
  CHECK(size > 0 && host.saveState(a, sizeof(a)));
  CHECK(host.setParam(0, 0.1f));
  CHECK(host.loadState(a, size));
  CHECK(host.saveState(b, sizeof(b)));
  CHECK(std::memcmp(a, b, size) == 0);
  INFO("svf_filter: lifecycle/state OK (%u bytes state)", size);
}

TEST(ModuleV01HostServices) {
  ModuleHostV0 host;
  CHECK(host.attach(&kRecorder));
  CHECK(host.hostServicesAttached());
  CHECK(host.prepare(48000));
  CHECK(host.hostNowUs() > 0);
  CHECK(host.logMessages() >= 1);
  CHECK(std::strstr(host.lastLogMessage(), "recorder attached") != nullptr);
  INFO("host services: now_us=%llu us, log='%s'",
       static_cast<unsigned long long>(host.hostNowUs()), host.lastLogMessage());
}

TEST(ModuleV01Events) {
  ModuleHostV0 host;
  CHECK(host.attach(&kRecorder));
  CHECK(host.prepare(48000));
  CHECK(host.acceptsEvents());
  bukifon_event_t note{};
  note.type = BUKIFON_EVENT_NOTE_ON;
  note.channel = 0;
  note.id = 60;
  note.value = 100.0f / 127.0f;
  CHECK(host.sendEvent(note));
  bukifon_event_t gate{};
  gate.type = BUKIFON_EVENT_GATE_ON;
  CHECK(host.sendEvent(gate));
  bukifon_event_t transport{};
  transport.type = BUKIFON_EVENT_TRANSPORT_START;
  CHECK(host.sendEvent(transport));
  CHECK(host.eventsSent() == 3);
  ModuleHostV0 legacy;
  CHECK(legacy.attach(bukifon_module_v0_gain_fx()));
  CHECK(!legacy.acceptsEvents());  // v0 module has no event input
  bukifon_event_t ignored{};
  ignored.type = BUKIFON_EVENT_NOTE_ON;
  CHECK(!legacy.sendEvent(ignored));
  INFO("events: 3 delivered, legacy module rejects events cleanly");
}

TEST(ModuleV01LogNotAllowedFromAudio) {
  ModuleHostV0 host;
  CHECK(host.attach(&kRecorder));
  CHECK(host.prepare(48000));
  const uint32_t messagesBefore = host.logMessages();
  gLogInsideProcess = true;
  runHostBlocks(host, 1);
  gLogInsideProcess = false;
  CHECK(host.logViolations() >= 1);
  CHECK(host.logMessages() == messagesBefore);  // inside-process log is dropped
  INFO("log from process(): %u violations, message dropped", host.logViolations());
}

TEST(ModuleV01ParamSmoothing) {
  ModuleHostV0 host;
  CHECK(host.attach(&kRecorder));
  CHECK(host.prepare(48000));
  host.setParamSmoothed(0, 0.0f, 0.0f);
  host.setParamSmoothed(0, 1.0f, 50.0f);
  CHECK(host.smoothingActive(0));
  runHostBlocks(host, 5);
  const float mid = host.smoothedValue(0);
  CHECK(mid > 0.0f);
  CHECK(mid < 1.0f);
  runHostBlocks(host, 600);
  const float end = host.smoothedValue(0);
  CHECK(end > 0.99f);
  CHECK(!host.smoothingActive(0));
  CHECK(std::fabs(end - 1.0f) < 0.01f);
  INFO("param smoothing: mid=%.3f after 5 blocks, end=%.4f after 600 blocks", mid, end);
}

TEST(ModuleV01BudgetAndBypass) {
  ModuleHostV0 host;
  CHECK(host.attach(bukifon_module_v0_grain_fx()));
  CHECK(host.prepare(48000));
  host.setCostProvider([](uint32_t) { return 900u; });  // 900 us > 800 us budget
  float l[64];
  float r[64];
  float ol[64];
  float orr[64];
  for (int i = 0; i < 64; ++i) {
    l[i] = 0.25f;
    r[i] = -0.25f;
  }
  host.process(l, r, ol, orr, 64);
  CHECK(host.overrunCount() == 1);
  host.process(l, r, ol, orr, 64);
  CHECK(host.overrunCount() == 2);
  CHECK(host.bypassed());
  host.process(l, r, ol, orr, 64);
  CHECK(std::fabs(ol[0] - l[0]) < 1e-6f);  // bypass = dry signal
  host.clearBypass();
  CHECK(!host.bypassed());
  INFO("budget: bypass after %u overruns, dry passthrough verified", host.overrunCount());
}

TEST(ModuleV01LogViolationFromProcess) {
  ModuleHostV0 host;
  CHECK(host.attach(&kRecorder));
  CHECK(host.prepare(48000));
  gLogInsideProcess = true;
  runHostBlocks(host, 3);
  gLogInsideProcess = false;
  CHECK(host.logViolations() == 3);
  INFO("log violation: %u calls from process() dropped (no I/O in audio path)",
       host.logViolations());
}

TEST(ModuleV01V0ModulesStillWork) {
  ModuleHostV0 gain;
  CHECK(gain.attach(bukifon_module_v0_gain_fx()));
  CHECK(gain.prepare(48000));
  runHostBlocks(gain, 4);
  CHECK(gain.overrunCount() == 0);
  ModuleHostV0 lfo;
  CHECK(lfo.attach(bukifon_module_v0_lfo_mod()));
  CHECK(lfo.prepare(48000));
  runHostBlocks(lfo, 4);
  INFO("v0 modules (gain_fx, lfo_mod) attach/prepare/process without changes");
}
