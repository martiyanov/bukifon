// SPDX-License-Identifier: GPL-3.0-or-later
// MIDI -> engine router: USB/TRS notes, MPE-lite, CC, program change, SysEx
// patch dump/version request, clock start/stop/continue.
#pragma once

#include <cstddef>
#include <cstdint>
#include <functional>

#include "audio/engine.hpp"
#include "io/midi_parser.hpp"

namespace bukifon {

struct Patch;

class MidiRouter : public MidiSink {
 public:
  void setEngine(Engine* engine) { engine_ = engine; }
  void setChannelPart(int channel, int part);
  void setSender(std::function<void(const uint8_t*, size_t)> sender) { sender_ = std::move(sender); }

  // Compose a UI/MIDI action into the engine event queue.
  void sendPatchDump(const Patch& patch);
  void sendVersionRequest() const;
  void sendVersionReply() const;
  bool applyPatchFromSysEx(const uint8_t* data, size_t length);

  void onNoteOn(uint8_t channel, uint8_t note, uint8_t velocity) override;
  void onNoteOff(uint8_t channel, uint8_t note, uint8_t velocity) override;
  void onControlChange(uint8_t channel, uint8_t cc, uint8_t value) override;
  void onPitchBend(uint8_t channel, int16_t bend14) override;
  void onAftertouch(uint8_t channel, uint8_t value) override;
  void onPolyAftertouch(uint8_t channel, uint8_t note, uint8_t value) override;
  void onProgramChange(uint8_t channel, uint8_t program) override;
  void onSysEx(const uint8_t* data, size_t length) override;
  void onClock() override;
  void onStart() override;
  void onStop() override;
  void onContinue() override;

  int partForChannel(uint8_t channel) const { return channelPart_[channel & 0x0F]; }
  bool ctrlAllHeld() const { return ctrlAll_; }
  void setCtrlAllHeld(bool held) { ctrlAll_ = held; }

 private:
  void push(const Event& e);
  Engine* engine_ = nullptr;
  uint8_t channelPart_[16] = {0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3};
  bool ctrlAll_ = false;
  std::function<void(const uint8_t*, size_t)> sender_;
};

}  // namespace bukifon
