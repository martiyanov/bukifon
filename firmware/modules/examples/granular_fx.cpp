// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon module API v0.1 example — "GRAIN FX" (granular insert effect).
//
// Shows the v0.1 additions: attach_host() (monotonic time + log outside audio),
// on_event() (note/gate/transport) and host-side parameter smoothing (the host
// calls set_param at ABI block boundaries).  The module itself never allocates
// in process(), does not log from the audio path, and keeps state <= 4 KiB.
#include <math.h>
#include <new>
#include <stddef.h>
#include <string.h>

#include "bukifon_module.h"

namespace {

constexpr uint32_t kRingSamples = 48000;  // 1 s @ 48 kHz, allocated in create()
constexpr uint32_t kGrains = 4;
constexpr uint32_t kStateMagic = 0x4752414Eu;  // "GRAN"
constexpr uint32_t kStateVersion = 1;

enum GrainParam : uint16_t { kGrainMs = 0, kDensity = 1, kMix = 2, kParamCount = 3 };

struct SavedState {
  uint32_t magic;
  uint32_t version;
  float grainMs;
  float density;
  float mix;
  float grainPhase[kGrains];
  uint32_t grainPos[kGrains];
  uint32_t rng;
  uint32_t grainsTriggered;
  uint8_t gate;
  uint8_t transport;
  uint16_t eventsSeen;
  uint64_t lastHostTimeUs;
};

struct GrainState {
  float* ring;
  uint32_t writePos;
  float grainMs;
  float density;
  float mix;
  float grainPhase[kGrains];
  uint32_t grainPos[kGrains];
  uint32_t rng;
  uint32_t grainsTriggered;
  uint32_t sampleRate;
  uint8_t gate;
  uint8_t transport;
  uint16_t eventsSeen;
  uint64_t lastHostTimeUs;
  const bukifon_host_services_t* services;
};

const bukifon_param_desc_t kGrainParams[kParamCount] = {
    {kGrainMs, 0, BUKIFON_PARAM_LOG, "GRAIN", 10.0f, 250.0f, 64.0f, "ms"},
    {kDensity, 0, 0, "DENSITY", 0.0f, 1.0f, 0.6f, "%"},
    {kMix, 0, 0, "MIX", 0.0f, 1.0f, 0.35f, "%"},
};

const bukifon_module_desc_t kGrainDesc = {
    BUKIFON_MODULE_API_VERSION,
    BUKIFON_KIND_EFFECT,
    BUKIFON_CAP_AUDIO_IN | BUKIFON_CAP_AUDIO_OUT | BUKIFON_CAP_STEREO,
    BUKIFON_MODULE_MAX_FRAMES,
    2048,
    sizeof(SavedState),
    "grain_fx",
    "GRAIN FX",
    "0.1.0",
    "Bukifon team",
    kGrainParams,
    kParamCount,
};

inline void clamp01(float* v) {
  if (*v < 0.0f) *v = 0.0f;
  if (*v > 1.0f) *v = 1.0f;
}

uint32_t nextRandom(uint32_t* state) {
  *state = (*state * 1664525u) + 1013904223u;
  return *state;
}

void randomizeGrains(GrainState* s) {
  for (uint32_t g = 0; g < kGrains; ++g) {
    s->grainPos[g] = nextRandom(&s->rng) % kRingSamples;
    s->grainPhase[g] = static_cast<float>(g) / static_cast<float>(kGrains);
  }
}

void grainResetState(GrainState* s) {
  s->writePos = 0;
  s->grainMs = kGrainParams[kGrainMs].default_value;
  s->density = kGrainParams[kDensity].default_value;
  s->mix = kGrainParams[kMix].default_value;
  s->rng = 0x1234ABCDu;
  s->grainsTriggered = 0;
  s->sampleRate = 48000;
  s->gate = 0;
  s->transport = 0;
  s->eventsSeen = 0;
  s->lastHostTimeUs = 0;
  randomizeGrains(s);
}

const bukifon_module_desc_t* grainDescriptor(void) { return &kGrainDesc; }

void* grainCreate(void) {
  GrainState* s = new (std::nothrow) GrainState();
  if (!s) return nullptr;
  s->ring = new (std::nothrow) float[kRingSamples];
  if (!s->ring) {
    delete s;
    return nullptr;
  }
  memset(s->ring, 0, sizeof(float) * kRingSamples);
  s->services = nullptr;
  grainResetState(s);
  return s;
}

int grainPrepare(void* instance, uint32_t sampleRate) {
  GrainState* s = static_cast<GrainState*>(instance);
  if (!s || sampleRate < 8000 || sampleRate > 192000) return -1;
  s->sampleRate = sampleRate;
  return 0;
}

void grainReset(void* instance) {
  GrainState* s = static_cast<GrainState*>(instance);
  if (!s) return;
  memset(s->ring, 0, sizeof(float) * kRingSamples);
  grainResetState(s);
}

int grainProcess(void* instance, const float* in, float* out, uint32_t frames) {
  GrainState* s = static_cast<GrainState*>(instance);
  if (!s || !s->ring || !out) return -1;
  if (frames > BUKIFON_MODULE_MAX_FRAMES) return -2;
  const float mix = s->mix;
  const float grainSamples = (s->grainMs * 0.001f) * static_cast<float>(s->sampleRate);
  const float phaseInc = grainSamples > 1.0f ? 1.0f / grainSamples : 1.0f;
  for (uint32_t i = 0; i < frames; ++i) {
    const float dryL = in ? in[i * 2 + 0] : 0.0f;
    const float dryR = in ? in[i * 2 + 1] : 0.0f;
    s->ring[s->writePos] = 0.5f * (dryL + dryR);
    s->writePos = (s->writePos + 1u) % kRingSamples;
    float wet = 0.0f;
    for (uint32_t g = 0; g < kGrains; ++g) {
      const float window = 0.5f - 0.5f * cosf(6.2831853f * s->grainPhase[g]);
      wet += s->ring[s->grainPos[g]] * window * 0.25f;
      s->grainPhase[g] += phaseInc;
      if (s->grainPhase[g] >= 1.0f) {
        s->grainPhase[g] -= 1.0f;
        s->grainPos[g] = nextRandom(&s->rng) % kRingSamples;
      }
    }
    out[i * 2 + 0] = dryL * (1.0f - mix) + wet * mix;
    out[i * 2 + 1] = dryR * (1.0f - mix) + wet * mix;
  }
  return 0;
}

void grainSetParam(void* instance, uint16_t id, float value) {
  GrainState* s = static_cast<GrainState*>(instance);
  if (!s) return;
  clamp01(&value);
  switch (id) {
    case kGrainMs: {
      const float lo = kGrainParams[kGrainMs].min_value;
      const float hi = kGrainParams[kGrainMs].max_value;
      s->grainMs = lo + value * (hi - lo);
      break;
    }
    case kDensity:
      s->density = value;
      break;
    case kMix:
      s->mix = value;
      break;
    default:
      break;
  }
}

uint32_t grainStateSize(void* instance) {
  (void)instance;
  return static_cast<uint32_t>(sizeof(SavedState));
}

int grainSaveState(void* instance, uint8_t* out, uint32_t capacity) {
  GrainState* s = static_cast<GrainState*>(instance);
  if (!s || !out || capacity < sizeof(SavedState)) return -1;
  SavedState saved;
  memset(&saved, 0, sizeof(saved));
  saved.magic = kStateMagic;
  saved.version = kStateVersion;
  saved.grainMs = s->grainMs;
  saved.density = s->density;
  saved.mix = s->mix;
  for (uint32_t g = 0; g < kGrains; ++g) {
    saved.grainPhase[g] = s->grainPhase[g];
    saved.grainPos[g] = s->grainPos[g];
  }
  saved.rng = s->rng;
  saved.grainsTriggered = s->grainsTriggered;
  saved.gate = s->gate;
  saved.transport = s->transport;
  saved.eventsSeen = s->eventsSeen;
  saved.lastHostTimeUs = s->lastHostTimeUs;
  memcpy(out, &saved, sizeof(saved));
  return static_cast<int>(sizeof(saved));
}

int grainLoadState(void* instance, const uint8_t* data, uint32_t size) {
  GrainState* s = static_cast<GrainState*>(instance);
  if (!s || !data || size < sizeof(SavedState)) return -1;
  SavedState saved;
  memcpy(&saved, data, sizeof(saved));
  if (saved.magic != kStateMagic || saved.version != kStateVersion) return -2;
  s->grainMs = saved.grainMs;
  s->density = saved.density;
  s->mix = saved.mix;
  for (uint32_t g = 0; g < kGrains; ++g) {
    s->grainPhase[g] = saved.grainPhase[g];
    s->grainPos[g] = saved.grainPos[g];
  }
  s->rng = saved.rng;
  s->grainsTriggered = saved.grainsTriggered;
  s->gate = saved.gate;
  s->transport = saved.transport;
  s->eventsSeen = saved.eventsSeen;
  s->lastHostTimeUs = saved.lastHostTimeUs;
  return 0;
}

void grainDestroy(void* instance) {
  GrainState* s = static_cast<GrainState*>(instance);
  if (!s) return;
  delete[] s->ring;
  delete s;
}

int grainAttachHost(void* instance, const bukifon_host_services_t* services) {
  GrainState* s = static_cast<GrainState*>(instance);
  if (!s || !services) return -1;
  s->services = services;
  s->lastHostTimeUs = services->now_us ? services->now_us(services->context) : 0;
  if (services->log) services->log(services->context, 2, "grain_fx: host attached");
  return 0;
}

void grainOnEvent(void* instance, const bukifon_event_t* event) {
  GrainState* s = static_cast<GrainState*>(instance);
  if (!s || !event) return;
  ++s->eventsSeen;
  switch (event->type) {
    case BUKIFON_EVENT_NOTE_ON:
      randomizeGrains(s);
      ++s->grainsTriggered;
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

const bukifon_module_v0_t kGrainModule = {
    BUKIFON_MODULE_API_VERSION,
    grainDescriptor,
    grainCreate,
    grainPrepare,
    grainReset,
    grainProcess,
    grainSetParam,
    grainStateSize,
    grainSaveState,
    grainLoadState,
    grainDestroy,
    grainAttachHost,
    grainOnEvent,
};

}  // namespace

BUKIFON_MODULE_EXPORT_V0(grain_fx, kGrainModule)
