// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon module API v0 example #1 — "GAIN FX" (asymmetric drive + tone + mix).
//
// EXPERIMENTAL ABI v0; this is a design probe, not a stable SDK.
// Real-time rules: no allocation in process(), no locks/IO, <= 64 frames.
#include <math.h>
#include <new>
#include <stddef.h>
#include <string.h>

#include "bukifon_module.h"

namespace {

constexpr uint32_t kSampleRateDefault = 48000;
constexpr uint32_t kDefaultFrames = BUKIFON_MODULE_MAX_FRAMES;

enum GainParam : uint16_t { kDrive = 0, kTone = 1, kMix = 2, kParamCount = 3 };

struct GainState {
  float drive;
  float tone;
  float mix;
  float lp;
  uint32_t sampleRate;
  uint32_t magic;  // included in the saved state so load_state can validate
};

constexpr uint32_t kStateMagic = 0x4741494Eu;  // "GAIN"

const bukifon_param_desc_t kGainParams[kParamCount] = {
    {kDrive, 0, 0, "DRIVE", 0.0f, 1.0f, 0.55f, "%"},
    {kTone, 0, 0, "TONE", 0.0f, 1.0f, 0.45f, "%"},
    {kMix, 0, 0, "MIX", 0.0f, 1.0f, 0.85f, "%"},
};

const bukifon_module_desc_t kGainDesc = {
    BUKIFON_MODULE_API_VERSION,
    BUKIFON_KIND_EFFECT,
    BUKIFON_CAP_AUDIO_IN | BUKIFON_CAP_AUDIO_OUT | BUKIFON_CAP_STEREO,
    kDefaultFrames,
    1024,
    sizeof(GainState),
    "gain_fx",
    "GAIN FX",
    "0.1.0",
    "Bukifon team",
    kGainParams,
    kParamCount,
};

inline void clamp01(float* v) {
  if (*v < 0.0f) *v = 0.0f;
  if (*v > 1.0f) *v = 1.0f;
}

void gainResetState(GainState* s) {
  if (!s) return;
  s->drive = kGainParams[kDrive].default_value;
  s->tone = kGainParams[kTone].default_value;
  s->mix = kGainParams[kMix].default_value;
  s->lp = 0.0f;
  s->sampleRate = kSampleRateDefault;
  s->magic = kStateMagic;
}

const bukifon_module_desc_t* gainDescriptor(void) { return &kGainDesc; }

void* gainCreate(void) {
  GainState* s = new (std::nothrow) GainState();
  if (!s) return nullptr;
  gainResetState(s);
  return s;
}

int gainPrepare(void* instance, uint32_t sampleRate) {
  GainState* s = static_cast<GainState*>(instance);
  if (!s || sampleRate < 8000 || sampleRate > 192000) return -1;
  s->sampleRate = sampleRate;
  return 0;
}

void gainReset(void* instance) {
  GainState* s = static_cast<GainState*>(instance);
  if (!s) return;
  const uint32_t sr = s->sampleRate;
  gainResetState(s);
  s->sampleRate = sr;
}

int gainProcess(void* instance, const float* in, float* out, uint32_t frames) {
  GainState* s = static_cast<GainState*>(instance);
  if (!s || !in || !out) return -1;
  if (frames > BUKIFON_MODULE_MAX_FRAMES) return -2;
  const float gain = 1.0f + s->drive * 14.0f;
  const float comp = 1.0f / (1.0f + s->drive * 4.0f);
  const float coef = 0.02f + s->tone * 0.75f;
  for (uint32_t i = 0; i < frames; ++i) {
    const float l = in[i * 2 + 0];
    const float r = in[i * 2 + 1];
    float dl = tanhf(l * gain) + 0.12f * (l * gain) * (l * gain);
    float dr = tanhf(r * gain) + 0.12f * (r * gain) * (r * gain);
    dl = tanhf(dl) * comp;
    dr = tanhf(dr) * comp;
    s->lp += ((dl + dr) * 0.5f - s->lp) * coef;
    out[i * 2 + 0] = l * (1.0f - s->mix) + dl * s->mix;
    out[i * 2 + 1] = r * (1.0f - s->mix) + dr * s->mix;
  }
  return 0;
}

void gainSetParam(void* instance, uint16_t id, float value) {
  GainState* s = static_cast<GainState*>(instance);
  if (!s) return;
  switch (id) {
    case kDrive: s->drive = value; clamp01(&s->drive); break;
    case kTone: s->tone = value; clamp01(&s->tone); break;
    case kMix: s->mix = value; clamp01(&s->mix); break;
    default: break;
  }
}

uint32_t gainStateSize(void* instance) {
  (void)instance;
  return static_cast<uint32_t>(sizeof(GainState));
}

int gainSaveState(void* instance, uint8_t* out, uint32_t capacity) {
  GainState* s = static_cast<GainState*>(instance);
  if (!s || !out || capacity < sizeof(GainState)) return -1;
  memcpy(out, s, sizeof(GainState));
  return static_cast<int>(sizeof(GainState));
}

int gainLoadState(void* instance, const uint8_t* data, uint32_t size) {
  GainState* s = static_cast<GainState*>(instance);
  if (!s || !data || size != sizeof(GainState)) return -1;
  GainState loaded;
  memcpy(&loaded, data, sizeof(loaded));
  if (loaded.magic != kStateMagic) return -2;
  if (loaded.sampleRate < 8000 || loaded.sampleRate > 192000) return -3;
  *s = loaded;
  return 0;
}

void gainDestroy(void* instance) { delete static_cast<GainState*>(instance); }

const bukifon_module_v0_t kGainTable = {
    BUKIFON_MODULE_API_VERSION, gainDescriptor, gainCreate,     gainPrepare,
    gainReset,                  gainProcess,    gainSetParam,   gainStateSize,
    gainSaveState,              gainLoadState,  gainDestroy,    nullptr, nullptr,
};

}  // namespace

BUKIFON_MODULE_EXPORT_V0(gain_fx, kGainTable)
