// SPDX-License-Identifier: GPL-3.0-or-later
// Cross-core messages (core0 -> core1) and telemetry (core1 -> core0).
#pragma once

#include <cstdint>

#include "core/config.hpp"
#include "core/spsc_queue.hpp"

namespace bukifon {

enum class EventType : uint8_t {
  None = 0,
  NoteOn,
  NoteOff,
  AllNotesOff,
  PitchBend,     // value = normalized -1..+1
  Aftertouch,    // value = 0..1 (channel pressure)
  PolyAftertouch,// index = note, value = 0..1
  ModWheel,      // value = 0..1
  ControlChange, // index = CC number, value = 0..1
  ParamSet,      // index = param id, value = absolute value
  ParamSetNorm,  // index = param id, value = 0..1
  PartParamSet,  // channel = part, index = param id, value = absolute
  ProgramChange, // index = preset index
  MacroSet,      // index = macro index, value = 0..1
  Clock,         // 24 ppqn tick
  Start,
  Stop,
  Continue,
  Panic,
  CvIn,          // channel = cv index, value = volts
  EncoderDelta,  // channel = encoder index, value = delta
  SeqTrig,       // internal/UI trigger of a sequencer step (index = track)
  Undo,
  CtrlAll,       // value = 1 while held (R1)
  NumTypes
};

struct Event {
  EventType type = EventType::None;
  uint8_t channel = 0;
  uint8_t index = 0;
  uint8_t reserved = 0;
  float value = 0.0f;
};

using EventQueue = SpscQueue<Event, 512>;

// Audio -> UI telemetry, pushed once per block.
struct Telemetry {
  float rmsL = 0.0f;
  float rmsR = 0.0f;
  float peak = 0.0f;
  float cpuLoad = 0.0f;        // 0..1 (measured on host/embedded if available)
  float cvOut[kNumCvOut] = {0, 0, 0, 0};
  float partLevel[kNumParts] = {0, 0, 0, 0};
  float modulated[kNumParts][2] = {{0, 0}, {0, 0}, {0, 0}, {0, 0}};  // example displayed values
  uint16_t activeVoices = 0;
  uint16_t voicesPerPart[kNumParts] = {0, 0, 0, 0};
  uint8_t seqStep = 0;
  uint8_t seqPattern = 0;
  uint8_t gate[kNumCvOut] = {0, 0, 0, 0};
  uint8_t deckType = 0;
  uint32_t frames = 0;
};

using TelemetryQueue = SpscQueue<Telemetry, 8>;

}  // namespace bukifon
