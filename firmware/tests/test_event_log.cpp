// SPDX-License-Identifier: GPL-3.0-or-later
#include <cstdio>
#include <cstring>
#include <string>

#include "sim/event_log.hpp"
#include "test_framework.hpp"

using namespace bukifon::sim;

TEST(EventLogTypeNames) {
  CHECK(std::strcmp(simEventTypeName(SimEventType::NoteOn), "NOTE_ON") == 0);
  CHECK(std::strcmp(simEventTypeName(SimEventType::Plock), "PLOCK") == 0);
  SimEventType type = SimEventType::Marker;
  CHECK(simEventTypeFromName("TRANSPORT", &type));
  CHECK(type == SimEventType::Transport);
  CHECK(!simEventTypeFromName("NOPE", &type));
}

TEST(EventLogRoundtrip) {
  EventLog log;
  log.add(0, SimEventType::Transport, 0, 0, 1.0f);
  log.add(100, SimEventType::NoteOn, 1, 60, 100.0f);
  log.add(4200, SimEventType::NoteOff, 1, 60, 0.0f);
  log.add(4200, SimEventType::Plock, 1, 3, 0.75f);
  log.add(9000, SimEventType::Tempo, 0, 0, 133.0f);
  const std::string text = log.serialize();
  EventLog parsed;
  CHECK(parsed.parse(text));
  CHECK(parsed.size() == log.size());
  CHECK(parsed.equals(log));
  CHECK(parsed.serialize() == text);  // byte-identical roundtrip
  const EventLog::Summary summary = parsed.summarize();
  INFO("event log: %zu events, notes=%zu/%zu, plocks=%zu, first=%llu last=%llu", summary.count,
       summary.notesOn, summary.notesOff, summary.plocks,
       static_cast<unsigned long long>(summary.firstFrame),
       static_cast<unsigned long long>(summary.lastFrame));
  CHECK(summary.notesOn == 1);
  CHECK(summary.notesOff == 1);
  CHECK(summary.plocks == 1);
  CHECK(summary.transports == 1);
  CHECK(summary.monotonic);
}

TEST(EventLogRejectsMalformedInput) {
  EventLog log;
  CHECK(!log.parse("garbage"));
  CHECK(!log.parse("bukifon-eventlog v1\nnot-a-number NOTE_ON 0 0 1.0\n"));
  CHECK(!log.parse("bukifon-eventlog v1\n0 UNKNOWN 0 0 1.0\n"));
  // A valid header with no events is a valid (empty) log.
  CHECK(log.parse("bukifon-eventlog v2\n0 NOTE_ON 0 60 100.0\n") == false);
}

TEST(EventLogStableSort) {
  EventLog log;
  log.add(50, SimEventType::Marker, 1, 0, 1.0f);
  log.add(10, SimEventType::Marker, 2, 0, 2.0f);
  log.add(50, SimEventType::Marker, 3, 0, 3.0f);
  log.sortByFrame();
  CHECK(log.size() == 3);
  CHECK(log[0].frame == 10);
  CHECK(log[1].frame == 50 && log[1].a == 1);  // insertion order kept
  CHECK(log[2].frame == 50 && log[2].a == 3);
}

TEST(EventLogFileRoundtrip) {
  EventLog log;
  log.add(0, SimEventType::Transport, 0, 0, 1.0f);
  log.add(16, SimEventType::NoteOn, 0, 48, 90.0f);
  const char* path = "../tests/out/event_log_roundtrip.txt";
  CHECK(log.saveToFile(path));
  EventLog loaded;
  CHECK(loaded.loadFromFile(path));
  CHECK(loaded.equals(log));
  std::remove(path);
  INFO("event log file roundtrip: %zu events", loaded.size());
}
