// SPDX-License-Identifier: GPL-3.0-or-later
#include "io/midi_router.hpp"

#include "core/patch.hpp"

namespace bukifon {
namespace {
constexpr uint8_t kManufacturer = 0x7D;  // educational / non-commercial
constexpr uint8_t kBukifonId[3] = {'P', 'M', 'D'};
constexpr uint8_t kVersionMajor = 1;
constexpr uint8_t kVersionMinor = 0;
constexpr uint8_t kMsgVersionReply = 0x01;
constexpr uint8_t kMsgVersionRequest = 0x02;
constexpr uint8_t kMsgPatchDump = 0x03;
}  // namespace

void MidiRouter::setChannelPart(int channel, int part) {
  channel = channel & 0x0F;
  channelPart_[channel] = static_cast<uint8_t>(part & 0x03);
}

void MidiRouter::push(const Event& e) {
  if (!engine_) return;
  engine_->eventQueue().push(e);
}

void MidiRouter::onNoteOn(uint8_t channel, uint8_t note, uint8_t velocity) {
  Event e;
  e.type = EventType::NoteOn;
  e.channel = channel;
  e.index = note;
  e.value = static_cast<float>(velocity) / 127.0f;
  push(e);
}

void MidiRouter::onNoteOff(uint8_t channel, uint8_t note, uint8_t velocity) {
  (void)velocity;
  Event e;
  e.type = EventType::NoteOff;
  e.channel = channel;
  e.index = note;
  push(e);
}

void MidiRouter::onControlChange(uint8_t channel, uint8_t cc, uint8_t value) {
  Event e;
  e.channel = channel;
  e.index = cc;
  e.value = static_cast<float>(value) / 127.0f;
  switch (cc) {
    case 1:  // modulation wheel
      e.type = EventType::ModWheel;
      break;
    case 64:  // sustain pedal -> all-notes-off on release is intentionally not
              // modelled yet (documented limitation)
      e.type = EventType::ControlChange;
      break;
    case 120:
    case 123:
      e.type = EventType::AllNotesOff;
      break;
    case 121:
      e.type = EventType::Panic;
      break;
    default:
      // CC-learn: the UI may map any encoder to a CC; the router still forwards
      // the raw value so the engine modulation matrix can use it.
      e.type = EventType::ControlChange;
      break;
  }
  push(e);
}

void MidiRouter::onPitchBend(uint8_t channel, int16_t bend14) {
  Event e;
  e.type = EventType::PitchBend;
  e.channel = channel;
  e.value = static_cast<float>(bend14) / 8192.0f;
  push(e);
}

void MidiRouter::onAftertouch(uint8_t channel, uint8_t value) {
  Event e;
  e.type = EventType::Aftertouch;
  e.channel = channel;
  e.value = static_cast<float>(value) / 127.0f;
  push(e);
}

void MidiRouter::onPolyAftertouch(uint8_t channel, uint8_t note, uint8_t value) {
  Event e;
  e.type = EventType::PolyAftertouch;
  e.channel = channel;
  e.index = note;
  e.value = static_cast<float>(value) / 127.0f;
  push(e);
}

void MidiRouter::onProgramChange(uint8_t channel, uint8_t program) {
  (void)channel;
  Event e;
  e.type = EventType::ProgramChange;
  e.index = program;
  push(e);
}

void MidiRouter::onClock() {
  Event e;
  e.type = EventType::Clock;
  push(e);
}

void MidiRouter::onStart() {
  Event e;
  e.type = EventType::Start;
  push(e);
}

void MidiRouter::onStop() {
  Event e;
  e.type = EventType::Stop;
  push(e);
}

void MidiRouter::onContinue() {
  Event e;
  e.type = EventType::Continue;
  push(e);
}

void MidiRouter::sendPatchDump(const Patch& patch) {
  uint8_t packed[700];
  const size_t packedLength = patchToSysEx(patch, packed, sizeof(packed));
  if (packedLength == 0 || !sender_) return;
  uint8_t msg[720];
  size_t n = 0;
  msg[n++] = 0xF0;
  msg[n++] = kManufacturer;
  msg[n++] = kBukifonId[0];
  msg[n++] = kBukifonId[1];
  msg[n++] = kBukifonId[2];
  msg[n++] = kMsgPatchDump;
  for (size_t i = 0; i < packedLength; ++i) msg[n++] = packed[i];
  msg[n++] = 0xF7;
  sender_(msg, n);
}

void MidiRouter::sendVersionRequest() const {
  if (!sender_) return;
  const uint8_t msg[7] = {0xF0, kManufacturer, kBukifonId[0], kBukifonId[1], kBukifonId[2],
                          kMsgVersionRequest, 0xF7};
  sender_(msg, sizeof(msg));
}

void MidiRouter::sendVersionReply() const {
  if (!sender_) return;
  const uint8_t msg[8] = {0xF0, kManufacturer, kBukifonId[0], kBukifonId[1], kBukifonId[2],
                          kMsgVersionReply, static_cast<uint8_t>((kVersionMajor << 4) | kVersionMinor),
                          0xF7};
  sender_(msg, sizeof(msg));
}

bool MidiRouter::applyPatchFromSysEx(const uint8_t* data, size_t length) {
  if (!engine_ || length < 6) return false;
  if (data[0] != 0xF0 || data[length - 1] != 0xF7) return false;
  if (data[1] != kManufacturer || data[2] != kBukifonId[0] || data[3] != kBukifonId[1] ||
      data[4] != kBukifonId[2]) {
    return false;
  }
  const uint8_t msg = data[5];
  if (msg == kMsgVersionRequest) {
    sendVersionReply();
    return true;
  }
  if (msg == kMsgPatchDump) {
    const uint8_t* payload = data + 6;
    const size_t payloadLength = length - 7;
    Patch patch;
    if (!patchFromSysEx(payload, payloadLength, &patch)) return false;
    for (int p = 0; p < kNumParts; ++p) {
      for (int i = 0; i < kNumPartParams; ++i) {
        engine_->setPartParam(p, i, patch.parts[p].v[i]);
      }
      for (int s = 0; s < kModSlots; ++s) engine_->setModSlot(p, s, patch.slots[s]);
    }
    for (int i = 0; i < kNumGlobalParams; ++i) engine_->setGlobalParam(i, patch.global.v[i]);
    return true;
  }
  return false;
}

void MidiRouter::onSysEx(const uint8_t* data, size_t length) {
  if (!engine_ || length < 5) return;
  if (data[0] != kManufacturer || data[1] != kBukifonId[0] || data[2] != kBukifonId[1] ||
      data[3] != kBukifonId[2]) {
    return;
  }
  const uint8_t msg = data[4];
  if (msg == kMsgVersionRequest) {
    sendVersionReply();
    return;
  }
  if (msg != kMsgPatchDump) return;
  // Re-wrap the payload into a full F0..F7 SysEx block and apply it.
  uint8_t block[720];
  if (length > 5 + 700) return;
  size_t n = 0;
  block[n++] = 0xF0;
  for (size_t i = 0; i < length; ++i) block[n++] = data[i];
  block[n++] = 0xF7;
  applyPatchFromSysEx(block, n);
}

}  // namespace bukifon
