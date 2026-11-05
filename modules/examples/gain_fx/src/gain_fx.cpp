// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon Module API v0 example: diode-ish drive + one-pole tone.
#include <math.h>
#include <stdint.h>
#include <string.h>

#include "bukifon_module.h"

namespace {

struct GainFx {
  float drive = 0.5f;
  float tone = 0.5f;
  float drive_s = 0.5f;
  float tone_s = 0.5f;
  float lp = 0.0f;
  float sr = 48000.0f;
};

const bukifon_param_desc_t kParams[] = {
    {0, 0, 0, "Drive", 0.0f, 1.0f, 0.5f, ""},
    {1, 0, 0, "Tone", 0.0f, 1.0f, 0.5f, ""},
};

const bukifon_module_desc_t kDesc = {
    BUKIFON_MODULE_API_VERSION,
    BUKIFON_KIND_EFFECT,
    BUKIFON_CAP_AUDIO_IN | BUKIFON_CAP_AUDIO_OUT | BUKIFON_CAP_STEREO,
    BUKIFON_MODULE_MAX_FRAMES,
    1024,
    sizeof(GainFx),
    "gain_fx",
    "Gain FX",
    "0.1.0",
    "bukifon",
    kParams,
    2,
};

void* create(void) { return new GainFx(); }

int prepare(void* inst, uint32_t sample_rate) {
  if (!inst || sample_rate < 8000u) return -1;
  static_cast<GainFx*>(inst)->sr = static_cast<float>(sample_rate);
  return 0;
}

void reset(void* inst) {
  auto* g = static_cast<GainFx*>(inst);
  g->lp = 0.0f;
  g->drive_s = g->drive;
  g->tone_s = g->tone;
}

int process(void* inst, const float* in, float* out, uint32_t frames) {
  auto* g = static_cast<GainFx*>(inst);
  if (!g || !in || !out || frames > BUKIFON_MODULE_MAX_FRAMES) return -1;
  const float kSmooth = 0.002f;
  const float tone_hz = 400.0f + 9600.0f * g->tone_s;
  const float a = 1.0f - expf(-2.0f * 3.14159265f * tone_hz / g->sr);
  for (uint32_t i = 0; i < frames; ++i) {
    g->drive_s += (g->drive - g->drive_s) * kSmooth;
    g->tone_s += (g->tone - g->tone_s) * kSmooth;
    const float gain = 1.0f + 30.0f * g->drive_s;
    const float x = in[i] * gain;
    const float t = tanhf(x);
    const float y = t / (1.0f + 0.5f * fabsf(t));
    g->lp += a * (y - g->lp);
    out[i] = g->lp;
  }
  return 0;
}

void set_param(void* inst, uint16_t id, float value) {
  auto* g = static_cast<GainFx*>(inst);
  if (!g) return;
  if (value < 0.0f) value = 0.0f;
  if (value > 1.0f) value = 1.0f;
  if (id == 0) g->drive = value;
  if (id == 1) g->tone = value;
}

uint32_t state_size(void*) { return sizeof(GainFx); }

int save_state(void* inst, uint8_t* out, uint32_t capacity) {
  if (!inst || !out || capacity < sizeof(GainFx)) return -1;
  memcpy(out, inst, sizeof(GainFx));
  return 0;
}

int load_state(void* inst, const uint8_t* data, uint32_t size) {
  if (!inst || !data || size != sizeof(GainFx)) return -1;
  memcpy(inst, data, size);
  return 0;
}

void destroy(void* inst) { delete static_cast<GainFx*>(inst); }

const bukifon_module_desc_t* descriptor(void) { return &kDesc; }

const bukifon_module_v0_t kModule = {
    BUKIFON_MODULE_API_VERSION, descriptor, create,     prepare, reset,     process,
    set_param,                  state_size, save_state, load_state, destroy,
};

}  // namespace

BUKIFON_MODULE_EXPORT_V0(gain_fx, kModule)
