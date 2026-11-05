// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon module API v0 example #2 — "LFO MOD" control-rate modulator.
//
// EXPERIMENTAL ABI v0.  Writes a bipolar modulation signal into the interleaved
// stereo output; the host treats the output as a control signal (CAP_MODULATION).
// Real-time rules: no allocation in process(), no locks/IO, <= 64 frames.
#include <math.h>
#include <new>
#include <string.h>

#include "bukifon_module.h"

namespace {

enum LfoParam : uint16_t { kRate = 0, kShape = 1, kDepth = 2, kParamCount = 3 };
enum Shape : int { kSine = 0, kTriangle = 1, kSaw = 2, kSquare = 3, kNumShapes = 4 };

struct LfoState {
  float rateHz;
  float depth;
  float phase;
  int32_t shape;
  uint32_t sampleRate;
  uint32_t magic;
};

constexpr uint32_t kStateMagic = 0x4C464F31u;  // "LFO1"

const bukifon_param_desc_t kLfoParams[kParamCount] = {
    {kRate, 0, BUKIFON_PARAM_LOG, "RATE", 0.02f, 20.0f, 1.0f, "Hz"},
    {kShape, 0, BUKIFON_PARAM_STEPPED, "SHAPE", 0.0f, 3.0f, 0.0f, ""},
    {kDepth, 0, 0, "DEPTH", 0.0f, 1.0f, 0.6f, "%"},
};

const bukifon_module_desc_t kLfoDesc = {
    BUKIFON_MODULE_API_VERSION,
    BUKIFON_KIND_MODULATOR,
    BUKIFON_CAP_MODULATION | BUKIFON_CAP_STEREO,
    BUKIFON_MODULE_MAX_FRAMES,
    512,
    sizeof(LfoState),
    "lfo_mod",
    "LFO MOD",
    "0.1.0",
    "Bukifon team",
    kLfoParams,
    kParamCount,
};

void lfoResetState(LfoState* s) {
  if (!s) return;
  s->rateHz = kLfoParams[kRate].default_value;
  s->depth = kLfoParams[kDepth].default_value;
  s->phase = 0.0f;
  s->shape = kSine;
  s->sampleRate = 48000;
  s->magic = kStateMagic;
}

const bukifon_module_desc_t* lfoDescriptor(void) { return &kLfoDesc; }

void* lfoCreate(void) {
  LfoState* s = new (std::nothrow) LfoState();
  if (!s) return nullptr;
  lfoResetState(s);
  return s;
}

int lfoPrepare(void* instance, uint32_t sampleRate) {
  LfoState* s = static_cast<LfoState*>(instance);
  if (!s || sampleRate < 8000 || sampleRate > 192000) return -1;
  s->sampleRate = sampleRate;
  return 0;
}

void lfoReset(void* instance) {
  LfoState* s = static_cast<LfoState*>(instance);
  if (!s) return;
  const uint32_t sr = s->sampleRate;
  lfoResetState(s);
  s->sampleRate = sr;
}

float lfoWave(const LfoState* s) {
  const float p = s->phase;
  switch (s->shape) {
    case kTriangle: return 1.0f - 4.0f * fabsf(p - 0.5f);
    case kSaw: return 2.0f * p - 1.0f;
    case kSquare: return p < 0.5f ? 1.0f : -1.0f;
    case kSine:
    default: return sinf(6.28318530718f * p);
  }
}

int lfoProcess(void* instance, const float* in, float* out, uint32_t frames) {
  (void)in;  // modulators do not read audio
  LfoState* s = static_cast<LfoState*>(instance);
  if (!s || !out) return -1;
  if (frames > BUKIFON_MODULE_MAX_FRAMES) return -2;
  const float inc = s->rateHz / static_cast<float>(s->sampleRate);
  for (uint32_t i = 0; i < frames; ++i) {
    s->phase += inc;
    if (s->phase >= 1.0f) s->phase -= 1.0f;
    const float value = lfoWave(s) * s->depth;
    out[i * 2 + 0] = value;
    out[i * 2 + 1] = value;
  }
  return 0;
}

void lfoSetParam(void* instance, uint16_t id, float value) {
  LfoState* s = static_cast<LfoState*>(instance);
  if (!s) return;
  switch (id) {
    case kRate:
      if (value < 0.02f) value = 0.02f;
      if (value > 20.0f) value = 20.0f;
      s->rateHz = value;
      break;
    case kShape: {
      int shape = static_cast<int>(value + 0.5f);
      if (shape < 0) shape = 0;
      if (shape >= kNumShapes) shape = kNumShapes - 1;
      s->shape = shape;
      break;
    }
    case kDepth:
      if (value < 0.0f) value = 0.0f;
      if (value > 1.0f) value = 1.0f;
      s->depth = value;
      break;
    default: break;
  }
}

uint32_t lfoStateSize(void* instance) {
  (void)instance;
  return static_cast<uint32_t>(sizeof(LfoState));
}

int lfoSaveState(void* instance, uint8_t* out, uint32_t capacity) {
  LfoState* s = static_cast<LfoState*>(instance);
  if (!s || !out || capacity < sizeof(LfoState)) return -1;
  memcpy(out, s, sizeof(LfoState));
  return static_cast<int>(sizeof(LfoState));
}

int lfoLoadState(void* instance, const uint8_t* data, uint32_t size) {
  LfoState* s = static_cast<LfoState*>(instance);
  if (!s || !data || size != sizeof(LfoState)) return -1;
  LfoState loaded;
  memcpy(&loaded, data, sizeof(loaded));
  if (loaded.magic != kStateMagic) return -2;
  if (loaded.sampleRate < 8000 || loaded.sampleRate > 192000) return -3;
  if (loaded.shape < 0 || loaded.shape >= kNumShapes) return -4;
  *s = loaded;
  return 0;
}

void lfoDestroy(void* instance) { delete static_cast<LfoState*>(instance); }

const bukifon_module_v0_t kLfoTable = {
    BUKIFON_MODULE_API_VERSION, lfoDescriptor, lfoCreate,    lfoPrepare,
    lfoReset,                   lfoProcess,    lfoSetParam,  lfoStateSize,
    lfoSaveState,               lfoLoadState,  lfoDestroy,
};

}  // namespace

BUKIFON_MODULE_EXPORT_V0(lfo_mod, kLfoTable)
