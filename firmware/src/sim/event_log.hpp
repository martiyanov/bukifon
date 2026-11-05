// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon host simulator — deterministic event log.
//
// One event stream is shared by the simulator, the UI and the tests:
// note-on/off, parameter changes, transport, encoder moves, mute, p-lock and
// pattern changes.  The textual format is stable, ordered by frame and
// round-trips byte-identically so a session can be replayed and diffed.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace bukifon {
namespace sim {

enum class SimEventType : uint8_t {
  NoteOn = 0,
  NoteOff,
  Param,        // a = global param id, value = absolute value
  PartParam,    // a = part, b = param id, value = absolute value
  Transport,    // value = 1 (play) / 0 (stop)
  Encoder,      // a = encoder index, value = delta
  Mute,         // a = track, value = 1 (muted) / 0
  Plock,        // a = track, b = param id, value = normalised 0..1
  Pattern,      // a = pattern index
  Tempo,        // value = bpm
  Marker,       // a = free marker id (bar/beat boundaries etc.)
  kNumTypes
};

const char* simEventTypeName(SimEventType type);
bool simEventTypeFromName(const char* name, SimEventType* out);

struct SimEvent {
  uint64_t frame = 0;
  SimEventType type = SimEventType::Marker;
  uint8_t a = 0;
  uint8_t b = 0;
  uint8_t reserved = 0;
  float value = 0.0f;
};

// Ordered collection of events.  Deterministic serialisation:
//   "bukifon-eventlog v1\n"
//   "<frame> <TYPE> <a> <b> <value %.6f>\n" ...
class EventLog {
 public:
  void clear() { events_.clear(); }
  size_t size() const { return events_.size(); }
  bool empty() const { return events_.empty(); }
  const std::vector<SimEvent>& events() const { return events_; }
  SimEvent& operator[](size_t i) { return events_[i]; }
  const SimEvent& operator[](size_t i) const { return events_[i]; }

  void add(const SimEvent& event) { events_.push_back(event); }
  void add(uint64_t frame, SimEventType type, uint8_t a, uint8_t b, float value) {
    SimEvent e;
    e.frame = frame;
    e.type = type;
    e.a = a;
    e.b = b;
    e.value = value;
    events_.push_back(e);
  }

  // Stable insertion sort by frame (keeps insertion order for equal frames,
  // which is what makes the log reproducible).
  void sortByFrame();

  std::string serialize() const;
  bool parse(const std::string& text);
  bool saveToFile(const char* path) const;
  bool loadFromFile(const char* path);

  bool equals(const EventLog& other) const;

  struct Summary {
    size_t count = 0;
    size_t notesOn = 0;
    size_t notesOff = 0;
    size_t plocks = 0;
    size_t params = 0;
    size_t mutes = 0;
    size_t transports = 0;
    uint64_t firstFrame = 0;
    uint64_t lastFrame = 0;
    bool monotonic = true;
  };
  Summary summarize() const;

 private:
  std::vector<SimEvent> events_;
};

}  // namespace sim
}  // namespace bukifon
