// SPDX-License-Identifier: GPL-3.0-or-later
// Шаблон аудио-модуля Bukifon (Module API v0). Скопируй каталог и переименуй.
#include <stdint.h>
#include <string.h>

#include "bukifon_module.h"

namespace {

struct ModuleState {
  float param0 = 0.5f;
};

const bukifon_param_desc_t kParams[] = {
    {0, 0, 0, "Param", 0.0f, 1.0f, 0.5f, ""},
};

const bukifon_module_desc_t kDesc = {
    BUKIFON_MODULE_API_VERSION, BUKIFON_KIND_EFFECT,
    BUKIFON_CAP_AUDIO_IN | BUKIFON_CAP_AUDIO_OUT, BUKIFON_MODULE_MAX_FRAMES,
    1024, sizeof(ModuleState), "module", "Module", "0.1.0", "author", kParams, 1,
};

void* create(void) { return new ModuleState(); }
int prepare(void*, uint32_t) { return 0; }
void reset(void*) {}
int process(void* inst, const float* in, float* out, uint32_t frames) {
  auto* s = static_cast<ModuleState*>(inst);
  if (!s || !in || !out || frames > BUKIFON_MODULE_MAX_FRAMES) return -1;
  for (uint32_t i = 0; i < frames; ++i) out[i] = in[i] * s->param0;
  return 0;
}
void set_param(void* inst, uint16_t id, float v) { if (id == 0) static_cast<ModuleState*>(inst)->param0 = v; }
uint32_t state_size(void*) { return sizeof(ModuleState); }
int save_state(void* inst, uint8_t* o, uint32_t cap) { if (cap < sizeof(ModuleState)) return -1; memcpy(o, inst, sizeof(ModuleState)); return 0; }
int load_state(void* inst, const uint8_t* d, uint32_t n) { if (n != sizeof(ModuleState)) return -1; memcpy(inst, d, n); return 0; }
void destroy(void* inst) { delete static_cast<ModuleState*>(inst); }

const bukifon_module_desc_t* descriptor(void) { return &kDesc; }

const bukifon_module_v0_t kModule = {
    BUKIFON_MODULE_API_VERSION, descriptor, create,     prepare, reset,     process,
    set_param,                  state_size, save_state, load_state, destroy,
};

}  // namespace

BUKIFON_MODULE_EXPORT_V0(module, kModule)
