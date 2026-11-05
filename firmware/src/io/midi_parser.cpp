// SPDX-License-Identifier: GPL-3.0-or-later
#include "io/midi_parser.hpp"

namespace bukifon {
namespace {
constexpr uint8_t kSysExStart = 0xF0;
constexpr uint8_t kSysExEnd = 0xF7;
constexpr uint8_t kTuneRequest = 0xF6;

uint8_t messageDataLength(uint8_t status) {
  const uint8_t type = status & 0xF0;
  switch (type) {
    case 0x80:  // note off
    case 0x90:  // note on
    case 0xA0:  // poly aftertouch
    case 0xB0:  // control change
    case 0xE0:  // pitch bend
      return 2;
    case 0xC0:  // program change
    case 0xD0:  // channel pressure
      return 1;
    default:
      return 0;
  }
}
}  // namespace

void MidiParser::reset() {
  runningStatus_ = 0;
  status_ = 0;
  dataCount_ = 0;
  expectedData_ = 0;
  inSysEx_ = false;
  sysexLength_ = 0;
  sysexOverflow_ = false;
}

void MidiParser::feedByte(uint8_t byte) {
  // Real-time messages (0xF8..0xFF) may interleave any other message.
  if (byte >= 0xF8) {
    switch (byte) {
      case 0xF8:
        if (sink_) sink_->onClock();
        break;
      case 0xFA:
        if (sink_) sink_->onStart();
        break;
      case 0xFB:
        if (sink_) sink_->onContinue();
        break;
      case 0xFC:
        if (sink_) sink_->onStop();
        break;
      case 0xFF:
        if (sink_) sink_->onReset();
        break;
      default:
        break;  // active sensing / undefined
    }
    return;
  }

  if (byte & 0x80) {
    handleStatus(byte);
    return;
  }
  handleData(byte);
}

void MidiParser::handleStatus(uint8_t status) {
  if (status == kSysExStart) {
    if (inSysEx_) sysexLength_ = 0;  // restart a broken dump
    inSysEx_ = true;
    sysexLength_ = 0;
    sysexOverflow_ = false;
    status_ = 0;
    dataCount_ = 0;
    return;
  }
  if (status == kSysExEnd) {
    if (inSysEx_ && sink_ && !sysexOverflow_) sink_->onSysEx(sysex_, sysexLength_);
    inSysEx_ = false;
    sysexLength_ = 0;
    dataCount_ = 0;
    status_ = 0;
    return;
  }
  if (inSysEx_) {
    // System common inside SysEx aborts it.
    inSysEx_ = false;
    sysexLength_ = 0;
  }

  if (status == kTuneRequest) {
    if (sink_) sink_->onReset();
    runningStatus_ = 0;
    status_ = 0;
    dataCount_ = 0;
    return;
  }
  if (status >= 0xF0 && status <= 0xF7) {
    // System common: song position (2 data), song select (1), tune request (0),
    // clock is realtime and handled above.
    runningStatus_ = 0;
    status_ = status;
    dataCount_ = 0;
    expectedData_ = (status == 0xF2) ? 2 : ((status == 0xF1 || status == 0xF3) ? 1 : 0);
    if (expectedData_ == 0) status_ = 0;
    return;
  }

  // Channel message: remember as running status.
  runningStatus_ = status;
  status_ = status;
  dataCount_ = 0;
  expectedData_ = messageDataLength(status);
}

void MidiParser::handleData(uint8_t byte) {
  if (inSysEx_) {
    if (sysexLength_ < kMaxSysExBytes) {
      sysex_[sysexLength_++] = byte;
    } else {
      sysexOverflow_ = true;  // keep parsing, drop the dump
    }
    return;
  }
  if (status_ == 0) {
    if (runningStatus_ == 0) return;  // orphan data byte
    status_ = runningStatus_;
    expectedData_ = messageDataLength(status_);
    dataCount_ = 0;
  }
  if (expectedData_ == 0) return;
  data_[dataCount_++] = byte;
  if (dataCount_ >= expectedData_) dispatchChannelMessage();
}

void MidiParser::dispatchChannelMessage() {
  if (!sink_) {
    dataCount_ = 0;
    return;
  }
  const uint8_t channel = status_ & 0x0F;
  switch (status_ & 0xF0) {
    case 0x80:
      sink_->onNoteOff(channel, data_[0] & 0x7F, data_[1] & 0x7F);
      break;
    case 0x90: {
      const uint8_t velocity = data_[1] & 0x7F;
      if (velocity == 0) {
        sink_->onNoteOff(channel, data_[0] & 0x7F, 0);
      } else {
        sink_->onNoteOn(channel, data_[0] & 0x7F, velocity);
      }
      break;
    }
    case 0xA0:
      sink_->onPolyAftertouch(channel, data_[0] & 0x7F, data_[1] & 0x7F);
      break;
    case 0xB0:
      sink_->onControlChange(channel, data_[0] & 0x7F, data_[1] & 0x7F);
      break;
    case 0xC0:
      sink_->onProgramChange(channel, data_[0] & 0x7F);
      break;
    case 0xD0:
      sink_->onAftertouch(channel, data_[0] & 0x7F);
      break;
    case 0xE0: {
      const int16_t bend = static_cast<int16_t>(((data_[1] & 0x7F) << 7) | (data_[0] & 0x7F)) - 8192;
      sink_->onPitchBend(channel, bend);
      break;
    }
    default:
      break;
  }
  dataCount_ = 0;
  // Running status keeps status_ for the next message.
  if (runningStatus_ == 0) status_ = 0;
}

}  // namespace bukifon
