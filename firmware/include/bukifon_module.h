// SPDX-License-Identifier: GPL-3.0-or-later
// =============================================================================
//  Bukifon module API v0 — EXPERIMENTAL, NOT STABLE
// =============================================================================
//
//  This is the first, deliberately minimal module ABI for Bukifon.  It WILL
//  change before v1.0 (ids, callbacks, capability bits).  Do not ship third-
//  party modules against it; treat it as a design probe for the P4 firmware.
//
//  Lifecycle:
//      entry() -> descriptor()      (static metadata, no allocation)
//      create() -> prepare(sr) -> reset() -> process(<= 64 frames) ...
//          ^ set_param() may be called between process() calls
//          ^ save_state() / load_state() between runs
//      destroy()
//
//  Real-time rules for process():
//    * no malloc/free, no locks, no filesystem/network/logging, no exceptions;
//    * stack <= BUKIFON_MODULE_MAX_STACK bytes;
//    * frames <= BUKIFON_MODULE_MAX_FRAMES (64); host must split larger blocks;
//    * worst-case time <= BUKIFON_MODULE_BUDGET_US per call (measured by host);
//    * after BUKIFON_MODULE_MAX_OVERRUNS budget overruns the host bypasses the
//      module (dry signal) until it is reset/explicitly re-enabled.
//
//  The ABI is a plain C table so Lua/static registries/hardware modules can be
//  wrapped uniformly.  All state is instance-owned (create/destroy).
// =============================================================================
#ifndef BUKIFON_MODULE_H
#define BUKIFON_MODULE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define BUKIFON_MODULE_API_VERSION 0u /* EXPERIMENTAL — unstable */

#define BUKIFON_MODULE_MAX_FRAMES 64u
#define BUKIFON_MODULE_MAX_STACK 8192u
#define BUKIFON_MODULE_MAX_STATE 4096u
#define BUKIFON_MODULE_MAX_PARAMS 16u
#define BUKIFON_MODULE_BUDGET_US 800u /* per 64-frame call @48 kHz */
#define BUKIFON_MODULE_MAX_OVERRUNS 2u

/* Module kinds. */
enum BukifonModuleKind {
  BUKIFON_KIND_EFFECT = 1,
  BUKIFON_KIND_OSCILLATOR = 2,
  BUKIFON_KIND_FILTER = 3,
  BUKIFON_KIND_MODULATOR = 4,
  BUKIFON_KIND_SEQUENCER = 5,
  BUKIFON_KIND_UTILITY = 6
};

/* Capability bits. */
enum BukifonModuleCaps {
  BUKIFON_CAP_AUDIO_IN = 1u << 0,
  BUKIFON_CAP_AUDIO_OUT = 1u << 1,
  BUKIFON_CAP_MODULATION = 1u << 2,
  BUKIFON_CAP_STEREO = 1u << 3,
  BUKIFON_CAP_TICK = 1u << 4
};

enum BukifonParamFlags {
  BUKIFON_PARAM_BIPOLAR = 1u << 0,
  BUKIFON_PARAM_LOG = 1u << 1,
  BUKIFON_PARAM_STEPPED = 1u << 2,
  BUKIFON_PARAM_READONLY = 1u << 3
};

typedef struct bukifon_param_desc {
  uint16_t id;
  uint8_t type;  /* 0 = float32 */
  uint8_t flags;
  const char* name; /* shorten to <= 12 chars */
  float min_value;
  float max_value;
  float default_value;
  const char* unit;
} bukifon_param_desc_t;

typedef struct bukifon_module_desc {
  uint32_t api_version;
  uint32_t kind;
  uint32_t capabilities;
  uint32_t max_frames;  /* <= BUKIFON_MODULE_MAX_FRAMES */
  uint32_t stack_bytes; /* declared stack, <= BUKIFON_MODULE_MAX_STACK */
  uint32_t state_size;  /* bytes returned by state_size(), <= MAX_STATE */
  const char* id;       /* stable machine id, e.g. "gain_fx" */
  const char* name;     /* human-readable */
  const char* version;
  const char* author;
  const bukifon_param_desc_t* params;
  uint32_t param_count; /* <= BUKIFON_MODULE_MAX_PARAMS */
} bukifon_module_desc_t;

typedef struct bukifon_module_v0 {
  uint32_t api_version;
  /* 1 */ const bukifon_module_desc_t* (*descriptor)(void);
  /* 2 */ void* (*create)(void); /* allocation allowed here only */
  /* 3 */ int (*prepare)(void* instance, uint32_t sample_rate); /* 0 = ok */
  /* 4 */ void (*reset)(void* instance);
  /* 5 */ int (*process)(void* instance, const float* in, float* out,
                         uint32_t frames); /* frames <= max_frames; 0 = ok */
  /* 6 */ void (*set_param)(void* instance, uint16_t id, float value);
  /* 7 */ uint32_t (*state_size)(void* instance);
  /* 8 */ int (*save_state)(void* instance, uint8_t* out, uint32_t capacity);
  /* 9 */ int (*load_state)(void* instance, const uint8_t* data, uint32_t size);
  /* 10 */ void (*destroy)(void* instance);
} bukifon_module_v0_t;

/* Entry point: one exported symbol per module binary. */
typedef const bukifon_module_v0_t* (*bukifon_module_entry_v0_t)(void);

#ifdef __cplusplus
} /* extern "C" */
#endif

#ifdef __cplusplus
#define BUKIFON_EXTERN_C extern "C"
#else
#define BUKIFON_EXTERN_C
#endif

#define BUKIFON_MODULE_EXPORT_V0(id, table) \
  BUKIFON_EXTERN_C const bukifon_module_v0_t* bukifon_module_v0_##id(void) { return &(table); }

#endif /* BUKIFON_MODULE_H */
