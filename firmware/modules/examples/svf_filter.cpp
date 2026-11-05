// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon module API v0.1 example — "SVF FILTER" (state-variable filter).
//
// Demonstrates v0.1 events (note/gate/transport), host services (time + log
// outside audio) and a small save/load state.  TPT SVF (Zavalishin topology)
// with LP/BP/HP/notch modes; no allocation in process().
#include <math.h>
#include <new>
#include <stddef.h>
#include <string.h>

#include "bukifon_module.h"

namespace {

constexpr uint32_t kStateMagic = 0x53564621u;  // "SVF!"
constexpr uint32_t kStateVersion = 1;
constexpr float kPi = 3.14159265358979f;

enum SvfParam : uint16_t { kCutoff = 0, kResonance = 1, kMode = 2, kMix = 3, kParamCount = 4 };

struct SavedState {
  uint32_t magic;
  uint32_t version;
  float cutoff;
  float resonance;
  float mode;
  float mix;
  float noteHz;
  uint8_t gate;
  uint8_t transport;
  uint16_t eventsSeen;
  uint64_t lastHostTimeUs;
};

struct SvfState {
  float cutoff;
  float resonance;
  float mode;
  float mix;
  float noteHz;
  float ic1eq;
  float ic2eq;
  uint32_t sampleRate;
  uint8_t gate;
  uint8_t transport;
  uint16_t eventsSeen;
  uint64_t lastHostTimeUs;
  const bukifon_host_services_t* services;
};

const bukifon_param_desc_t kSvfParams[kParamCount] = {
    {kCutoff, 0, BUKIFON_PARAM_LOG, "CUTOFF", 20.0f, 18000.0f, 2400.0f, "Hz"},
    {kResonance, 0, 0, "RES", 0.0f, 1.0f, 0.35f, "%"},
    {kMode, 0, BUKIFON_PARAM_STEPPED, "MODE", 0.0f, 3.0f, 0.0f, ""},
    {kMix, 0, 0, "MIX", 0.0f, 1.0f, 1.0f, "%"},
};

const bukifon_module_desc_t kSvfDesc = {
    BUKIFON_MODULE_API_VERSION,
    BUKIFON_KIND_FILTER,
    BUKIFON_CAP_AUDIO_IN | BUKIFON_CAP_AUDIO_OUT | BUKIFON_CAP_STEREO,
    BUKIFON_MODULE_MAX_FRAMES,
    1024,
    sizeof(SavedState),
    "svf_filter",
    "SVF FILTER",
    "0.1.0",
    "Bukifon team",
    kSvfParams,
    kParamCount,
};

inline void clamp01(float* v) {
  if (*v < 0.0f) *v = 0.0f;
  if (*v > 1.0f) *v = 1.0f;
}

void svfResetState(SvfState* s) {
  s->cutoff = kSvfParams[kCutoff].default_value;
  s->resonance = kSvfParams[kResonance].default_value;
  s->mode = kSvfParams[kMode].default_value;
  s->mix = kSvfParams[kMix].default_value;
  s->noteHz = 440.0f;
  s->ic1eq = 0.0f;
  s->ic2eq = 0.0f;
  s->sampleRate = 48000;
  s->gate = 0;
  s->transport = 0;
  s->eventsSeen = 0;
  s->lastHostTimeUs = 0;
}

const bukifon_module_desc_t* svfDescriptor(void) { return &kSvfDesc; }

void* svfCreate(void) {
  SvfState* s = new (std::nothrow) SvfState();
  if (!s) return nullptr;
  s->services = nullptr;
  svfResetState(s);
  return s;
}

int svfPrepare(void* instance, uint32_t sampleRate) {
  SvfState* s = static_cast<SvfState*>(instance);
  if (!s || sampleRate < 8000 || sampleRate > 192000) return -1;
  s->sampleRate = sampleRate;
  return 0;
}

void svfReset(void* instance) {
  SvfState* s = static_cast<SvfState*>(instance);
  if (!s) return;
  svfResetState(s);
}

int svfProcess(void* instance, const float* in, float* out, uint32_t frames) {
  SvfState* s = static_cast<SvfState*>(instance);
  if (!s || !out) return -1;
  if (frames > BUKIFON_MODULE_MAX_FRAMES) return -2;
  float cutoff = s->cutoff;
  const float maxCutoff = 0.45f * static_cast<float>(s->sampleRate);
  if (cutoff < 20.0f) cutoff = 20.0f;
  if (cutoff > maxCutoff) cutoff = maxCutoff;
  const float g = tanf(kPi * cutoff / static_cast<float>(s->sampleRate));
  const float k = 2.0f - 1.98f * s->resonance;
  const float a1 = 1.0f / (1.0f + g * (g + k));
  const float a2 = g * a1;
  const float a3 = g * a2;
  const int mode = static_cast<int>(s->mode + 0.5f);
  for (uint32_t i = 0; i < frames; ++i) {
    for (int ch = 0; ch < 2; ++ch) {
      const float x = in ? in[i * 2 + ch] : 0.0f;
      const float v3 = x - s->ic2eq;
      const float v1 = a1 * s->ic1eq + a2 * v3;
      const float v2 = s->ic2eq + a2 * s->ic1eq + a3 * v3;
      s->ic1eq = 2.0f * v1 - s->ic1eq;
      s->ic2eq = 2.0f * v2 - s->ic2eq;
      float wet = v2;  // low-pass
      if (mode == 1) wet = v1;              // band-pass
      else if (mode == 2) wet = x - k * v1 - v2;  // high-pass
      else if (mode == 3) wet = x - k * v1;       // notch
      const float dry = in ? in[i * 2 + ch] : 0.0f;
      out[i * 2 + ch] = dry * (1.0f - s->mix) + wet * s->mix;
    }
  }
  return 0;
}

void svfSetParam(void* instance, uint16_t id, float value) {
  SvfState* s = static_cast<SvfState*>(instance);
  if (!s) return;
  clamp01(&value);
  switch (id) {
    case kCutoff:
      s->cutoff = kSvfParams[kCutoff].min_value +
                  value * (kSvfParams[kCutoff].max_value - kSvfParams[kCutoff].min_value);
      break;
    case kResonance:
      s->resonance = value;
      break;
    case kMode:
      s->mode = value * 3.0f;
      break;
    case kMix:
      s->mix = value;
      break;
    default:
      break;
  }
}

uint32_t svfStateSize(void* instance) {
  (void)instance;
  return static_cast<uint32_t>(sizeof(SavedState));
}

int svfSaveState(void* instance, uint8_t* out, uint32_t capacity) {
  SvfState* s = static_cast<SvfState*>(instance);
  if (!s || !out || capacity < sizeof(SavedState)) return -1;
  SavedState saved;
  memset(&saved, 0, sizeof(saved));
  saved.magic = kStateMagic;
  saved.version = kStateVersion;
  saved.cutoff = s->cutoff;
  saved.resonance = s->resonance;
  saved.mode = s->mode;
  saved.mix = s->mix;
  saved.noteHz = s->noteHz;
  saved.gate = s->gate;
  saved.transport = s->transport;
  saved.eventsSeen = s->eventsSeen;
  saved.lastHostTimeUs = s->lastHostTimeUs;
  memcpy(out, &saved, sizeof(saved));
  return static_cast<int>(sizeof(saved));
}

int svfLoadState(void* instance, const uint8_t* data, uint32_t size) {
  SvfState* s = static_cast<SvfState*>(instance);
  if (!s || !data || size < sizeof(SavedState)) return -1;
  SavedState saved;
  memcpy(&saved, data, sizeof(saved));
  if (saved.magic != kStateMagic || saved.version != kStateVersion) return -2;
  s->cutoff = saved.cutoff;
  s->resonance = saved.resonance;
  s->mode = saved.mode;
  s->mix = saved.mix;
  s->noteHz = saved.noteHz;
  s->gate = saved.gate;
  s->transport = saved.transport;
  s->eventsSeen = saved.eventsSeen;
  s->lastHostTimeUs = saved.lastHostTimeUs;
  return 0;
}

void svfDestroy(void* instance) {
  delete static_cast<SvfState*>(instance);
}

int svfAttachHost(void* instance, const bukifon_host_services_t* services) {
  SvfState* s = static_cast<SvfState*>(instance);
  if (!s || !services) return -1;
  s->services = services;
  s->lastHostTimeUs = services->now_us ? services->now_us(services->context) : 0;
  if (services->log) services->log(services->context, 2, "svf_filter: host attached");
  return 0;
}

void svfOnEvent(void* instance, const bukifon_event_t* event) {
  SvfState* s = static_cast<SvfState*>(instance);
  if (!s || !event) return;
  ++s->eventsSeen;
  switch (event->type) {
    case BUKIFON_EVENT_NOTE_ON:
      s->noteHz = 440.0f * powf(2.0f, (event->value * 127.0f - 69.0f) / 12.0f);
      break;
    case BUKIFON_EVENT_GATE_ON:
      s->gate = 1;
      break;
    case BUKIFON_EVENT_GATE_OFF:
      s->gate = 0;
      break;
    case BUKIFON_EVENT_TRANSPORT_START:
    case BUKIFON_EVENT_TRANSPORT_CONTINUE:
      s->transport = 1;
      break;
    case BUKIFON_EVENT_TRANSPORT_STOP:
      s->transport = 0;
      break;
    default:
      break;
  }
}

const bukifon_module_v0_t kSvfModule = {
    BUKIFON_MODULE_API_VERSION,
    svfDescriptor,
    svfCreate,
    svfPrepare,
    svfReset,
    svfProcess,
    svfSetParam,
    svfStateSize,
    svfSaveState,
    svfLoadState,
    svfDestroy,
    svfAttachHost,
    svfOnEvent,
};

}  // namespace

BUKIFON_MODULE_EXPORT_V0(svf_filter, kSvfModule)
