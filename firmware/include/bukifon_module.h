// SPDX-License-Identifier: GPL-3.0-or-later
// =============================================================================
//  Bukifon module API v0.1 — EXPERIMENTAL, NOT STABLE
//  (ABI major 0 stays backward compatible with v0 modules; minor 1 adds
//   host services, events and host-side parameter smoothing.)
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
#define BUKIFON_MODULE_API_MINOR 1u

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

// --- v0.1: host services ---------------------------------------------------
// Attached once via attach_host() after create(), before prepare().  The module
// may call now_us() any time; log() MUST NOT be called from process() (the host
// counts such calls as real-time violations and drops the message).
typedef struct bukifon_host_services {
  void* context;
  uint64_t (*now_us)(void* context);
  void (*log)(void* context, int level, const char* message);
} bukifon_host_services_t;

// --- v0.1: events ----------------------------------------------------------
typedef enum bukifon_event_type {
  BUKIFON_EVENT_NONE = 0,
  BUKIFON_EVENT_NOTE_ON = 1,
  BUKIFON_EVENT_NOTE_OFF = 2,
  BUKIFON_EVENT_GATE_ON = 3,
  BUKIFON_EVENT_GATE_OFF = 4,
  BUKIFON_EVENT_TRANSPORT_START = 5,
  BUKIFON_EVENT_TRANSPORT_STOP = 6,
  BUKIFON_EVENT_TRANSPORT_CONTINUE = 7,
  BUKIFON_EVENT_TEMPO = 8,
  BUKIFON_EVENT_PATTERN = 9,
  BUKIFON_EVENT_PITCH_BEND = 10
} bukifon_event_type_t;

typedef struct bukifon_event {
  uint8_t type;          /* bukifon_event_type_t */
  uint8_t channel;       /* MIDI/part channel 0..15 */
  uint16_t id;           /* note / CC / pattern id */
  float value;           /* velocity 0..1, tempo BPM, bend -1..1, ... */
  uint32_t frame_offset; /* offset inside the next process() block */
  uint32_t reserved;
} bukifon_event_t;

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
  /* --- v0.1 additions (NULL = not implemented, backward compatible) ---- */
  /* 11 */ int (*attach_host)(void* instance, const bukifon_host_services_t* services);
  /* 12 */ void (*on_event)(void* instance, const bukifon_event_t* event);
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
