// SPDX-License-Identifier: GPL-3.0-or-later
// Streaming MIDI 1.0 parser: running status, realtime interleaving, SysEx.
#pragma once

#include <cstddef>
#include <cstdint>

namespace bukifon {

constexpr size_t kMaxSysExBytes = 600;

class MidiSink {
 public:
  virtual ~MidiSink() = default;
  virtual void onNoteOn(uint8_t channel, uint8_t note, uint8_t velocity) { (void)channel; (void)note; (void)velocity; }
  virtual void onNoteOff(uint8_t channel, uint8_t note, uint8_t velocity) { (void)channel; (void)note; (void)velocity; }
  virtual void onControlChange(uint8_t channel, uint8_t cc, uint8_t value) { (void)channel; (void)cc; (void)value; }
  virtual void onPitchBend(uint8_t channel, int16_t bend14) { (void)channel; (void)bend14; }
  virtual void onAftertouch(uint8_t channel, uint8_t value) { (void)channel; (void)value; }
  virtual void onPolyAftertouch(uint8_t channel, uint8_t note, uint8_t value) { (void)channel; (void)note; (void)value; }
  virtual void onProgramChange(uint8_t channel, uint8_t program) { (void)channel; (void)program; }
  virtual void onSysEx(const uint8_t* data, size_t length) { (void)data; (void)length; }
  virtual void onClock() {}
  virtual void onStart() {}
  virtual void onStop() {}
  virtual void onContinue() {}
  virtual void onReset() {}
};

class MidiParser {
 public:
  explicit MidiParser(MidiSink* sink = nullptr) : sink_(sink) {}

  void setSink(MidiSink* sink) { sink_ = sink; }
  void feed(const uint8_t* data, size_t length) {
    for (size_t i = 0; i < length; ++i) feedByte(data[i]);
  }
  void feedByte(uint8_t byte);
  void reset();

  bool inSysEx() const { return inSysEx_; }
  size_t sysexLength() const { return sysexLength_; }
  bool sysexOverflowed() const { return sysexOverflow_; }

 private:
  void handleStatus(uint8_t status);
  void handleData(uint8_t byte);
  void dispatchChannelMessage();

  MidiSink* sink_ = nullptr;
  uint8_t runningStatus_ = 0;
  uint8_t status_ = 0;
  uint8_t data_[2] = {0, 0};
  uint8_t dataCount_ = 0;
  uint8_t expectedData_ = 0;

  bool inSysEx_ = false;
  uint8_t sysex_[kMaxSysExBytes] = {};
  size_t sysexLength_ = 0;
  bool sysexOverflow_ = false;
};

}  // namespace bukifon
