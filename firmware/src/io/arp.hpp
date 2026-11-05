// SPDX-License-Identifier: GPL-3.0-or-later
// Per-part arpeggiator: up/down/updown/random, 1..4 octaves, gate, latch.
#pragma once

#include <cstdint>

#include "core/config.hpp"

namespace bukifon {

enum ArpMode : uint8_t { ArpOff = 0, ArpUp, ArpDown, ArpUpDown, ArpRandom, kNumArpModes };

class ArpSink {
 public:
  virtual ~ArpSink() = default;
  virtual void onArpNoteOn(int part, int note, int velocity) {
    (void)part; (void)note; (void)velocity;
  }
  virtual void onArpNoteOff(int part, int note) { (void)part; (void)note; }
};

class Arpeggiator {
 public:
  void init(float sampleRate = static_cast<float>(kSampleRate));
  void reset();
  void setParams(int mode, int octaves, float gate, bool latch);
  void setSink(ArpSink* sink) { sink_ = sink; }
  bool enabled() const { return mode_ != ArpOff; }

  void noteOn(int note, int velocity);
  void noteOff(int note);
  void allNotesOff();

  // Advances the arp clock by `samples`; emits note on/off through the sink.
  void process(int samples, float bpm, int part);

  int heldCount() const { return heldCount_; }
  int currentNote() const { return pendingNote_; }
  float stepLengthSamples() const { return stepSamples_; }

 private:
  struct HeldNote {
    uint8_t note = 0;
    uint8_t velocity = 0;
    bool active = false;
  };
  void rebuildOrder();
  int noteAt(int stepIndex) const;
  void stepTrigger(int part);

  float sampleRate_ = static_cast<float>(kSampleRate);
  float bpm_ = 120.0f;
  int mode_ = ArpOff;
  int octaves_ = 1;
  float gate_ = 0.6f;
  bool latch_ = false;
  bool latchArmed_ = false;

  HeldNote held_[16] = {};
  int heldCount_ = 0;
  int order_[16 * 4] = {};
  int orderCount_ = 0;
  int orderPos_ = 0;
  int direction_ = 1;
  double untilNext_ = 0.0;
  double noteOffCountdown_ = 0.0;
  int pendingNote_ = -1;
  double stepSamples_ = 6000.0;
  uint32_t rng_ = 0x9E3779B9u;
  uint32_t nextRandom();
  ArpSink* sink_ = nullptr;
};

}  // namespace bukifon
