// SPDX-License-Identifier: GPL-3.0-or-later
#include "sim/event_log.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace bukifon {
namespace sim {
namespace {

constexpr const char* kMagic = "bukifon-eventlog v1";
constexpr const char* kTypeNames[] = {
    "NOTE_ON", "NOTE_OFF", "PARAM", "PART_PARAM", "TRANSPORT",
    "ENCODER", "MUTE",     "PLOCK", "PATTERN",    "TEMPO",
    "MARKER"};

static_assert(sizeof(kTypeNames) / sizeof(kTypeNames[0]) ==
                  static_cast<size_t>(SimEventType::kNumTypes),
              "event type name table out of sync");

bool sameFloat(float a, float b) { return std::fabs(a - b) <= 1e-6f; }

}  // namespace

const char* simEventTypeName(SimEventType type) {
  const int index = static_cast<int>(type);
  if (index < 0 || index >= static_cast<int>(SimEventType::kNumTypes)) return "?";
  return kTypeNames[index];
}

bool simEventTypeFromName(const char* name, SimEventType* out) {
  if (!name || !out) return false;
  for (int i = 0; i < static_cast<int>(SimEventType::kNumTypes); ++i) {
    if (std::strcmp(name, kTypeNames[i]) == 0) {
      *out = static_cast<SimEventType>(i);
      return true;
    }
  }
  return false;
}

void EventLog::sortByFrame() {
  std::stable_sort(events_.begin(), events_.end(),
                   [](const SimEvent& a, const SimEvent& b) { return a.frame < b.frame; });
}

std::string EventLog::serialize() const {
  std::string out;
  out.reserve(events_.size() * 40 + 32);
  out += kMagic;
  out += '\n';
  char line[96];
  for (const SimEvent& e : events_) {
    std::snprintf(line, sizeof(line), "%llu %s %u %u %.6f\n",
                  static_cast<unsigned long long>(e.frame), simEventTypeName(e.type),
                  static_cast<unsigned>(e.a), static_cast<unsigned>(e.b),
                  static_cast<double>(e.value));
    out += line;
  }
  return out;
}

bool EventLog::parse(const std::string& text) {
  EventLog parsed;
  size_t pos = 0;
  // Header line.
  const size_t newline = text.find('\n');
  if (newline == std::string::npos) return false;
  const std::string header = text.substr(0, newline);
  if (header != kMagic) return false;
  pos = newline + 1;
  while (pos < text.size()) {
    const size_t end = text.find('\n', pos);
    if (end == std::string::npos) return false;
    const std::string line = text.substr(pos, end - pos);
    pos = end + 1;
    if (line.empty()) continue;
    unsigned long long frame = 0;
    char typeName[32] = {};
    unsigned a = 0, b = 0;
    double value = 0.0;
    if (std::sscanf(line.c_str(), "%llu %31s %u %u %lf", &frame, typeName, &a, &b, &value) != 5) {
      return false;
    }
    SimEventType type;
    if (!simEventTypeFromName(typeName, &type)) return false;
    SimEvent e;
    e.frame = static_cast<uint64_t>(frame);
    e.type = type;
    e.a = static_cast<uint8_t>(a);
    e.b = static_cast<uint8_t>(b);
    e.value = static_cast<float>(value);
    parsed.events_.push_back(e);
  }
  *this = parsed;
  return true;
}

bool EventLog::saveToFile(const char* path) const {
  if (!path) return false;
  FILE* f = std::fopen(path, "wb");
  if (!f) return false;
  const std::string data = serialize();
  const bool ok = std::fwrite(data.data(), 1, data.size(), f) == data.size();
  std::fclose(f);
  return ok;
}

bool EventLog::loadFromFile(const char* path) {
  if (!path) return false;
  FILE* f = std::fopen(path, "rb");
  if (!f) return false;
  std::string data;
  char buffer[4096];
  size_t n = 0;
  while ((n = std::fread(buffer, 1, sizeof(buffer), f)) > 0) data.append(buffer, n);
  std::fclose(f);
  return parse(data);
}

bool EventLog::equals(const EventLog& other) const {
  if (events_.size() != other.events_.size()) return false;
  for (size_t i = 0; i < events_.size(); ++i) {
    const SimEvent& a = events_[i];
    const SimEvent& b = other.events_[i];
    if (a.frame != b.frame || a.type != b.type || a.a != b.a || a.b != b.b ||
        !sameFloat(a.value, b.value)) {
      return false;
    }
  }
  return true;
}

EventLog::Summary EventLog::summarize() const {
  Summary s;
  s.count = events_.size();
  if (events_.empty()) return s;
  s.firstFrame = events_.front().frame;
  s.lastFrame = events_.front().frame;
  uint64_t prev = events_.front().frame;
  for (const SimEvent& e : events_) {
    if (e.frame < prev) s.monotonic = false;
    prev = e.frame;
    if (e.frame > s.lastFrame) s.lastFrame = e.frame;
    switch (e.type) {
      case SimEventType::NoteOn: ++s.notesOn; break;
      case SimEventType::NoteOff: ++s.notesOff; break;
      case SimEventType::Plock: ++s.plocks; break;
      case SimEventType::Param:
      case SimEventType::PartParam: ++s.params; break;
      case SimEventType::Mute: ++s.mutes; break;
      case SimEventType::Transport: ++s.transports; break;
      default: break;
    }
  }
  return s;
}

}  // namespace sim
}  // namespace bukifon
