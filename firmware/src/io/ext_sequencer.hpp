// SPDX-License-Identifier: GPL-3.0-or-later
// External MIDI sequencer — 8 tracks for external synths (docs/70, v1.0-rc).
//
// Shares tempo/swing/transport/GEN with the internal sequencer.  The class is
// portable and sink-driven: DIN + USB routing is a host/device adapter
// (MidiOutRouter below models "both ports, no duplicates"; real TinyUSB/DIN
// gateway is TODO(hw)).
#pragma once

#include <cstddef>
#include <cstdint>

#include "core/config.hpp"
#include "io/gen.hpp"

namespace bukifon {

constexpr int kExtTracks = 8;
constexpr int kExtSteps = 16;

struct ExtStep {
  bool active = false;
  bool ccPlocked = false;  // CC value is sent for this step
  uint8_t note = 60;
  uint8_t velocity = 100;
  uint8_t length = 50;     // percent of the step (gate)
  uint8_t ccValue = 64;
};

struct ExtTrack {
  uint8_t channel = 1;   // 1..16
  uint8_t program = 0;   // PC 0..127
  bool muted = false;
  bool solo = false;
  uint8_t ccNumber = 74; // filter cutoff by default
  ExtStep steps[kExtSteps];
};

// Sink for the external sequencer (DIN/USB gateway or a host recorder).
class ExtSeqSink {
 public:
  virtual ~ExtSeqSink() = default;
  virtual void onExtNoteOn(int track, int channel, int note, int velocity) {
    (void)track; (void)channel; (void)note; (void)velocity;
  }
  virtual void onExtNoteOff(int track, int channel, int note) { (void)track; (void)channel; (void)note; }
  virtual void onExtProgramChange(int track, int channel, int program) {
    (void)track; (void)channel; (void)program;
  }
  virtual void onExtControlChange(int track, int channel, int cc, int value) {
    (void)track; (void)channel; (void)cc; (void)value;
  }
  virtual void onExtClock() {}
  virtual void onExtStart() {}
  virtual void onExtStop() {}
  virtual void onExtContinue() {}
};

class ExtSequencer {
 public:
  void init(float sampleRate = static_cast<float>(kSampleRate));
  void setSink(ExtSeqSink* sink) { sink_ = sink; }
  ExtSeqSink* sink() const { return sink_; }

  ExtTrack& track(int index);
  const ExtTrack& track(int index) const;
  void setChannel(int index, int channel);
  void setProgram(int index, int program);
  void setTrackMuted(int index, bool muted);
  bool trackMuted(int index) const;
  int trackCount() const { return kExtTracks; }
  int stepCount() const { return kExtSteps; }

  void setBpm(float bpm) { bpm_ = bpm > 1.0f ? bpm : 1.0f; }
  float bpm() const { return bpm_; }
  void setSwing(float swing) { swing_ = swing; }
  float swing() const { return swing_; }

  void setPlaying(bool playing);
  bool playing() const { return playing_; }
  void start();
  void stop();
  void continuePlay();
  void setClockMaster(bool master) { clockMaster_ = master; }
  bool clockMaster() const { return clockMaster_; }
  void setClockSlave(bool slave) { clockSlave_ = slave; }
  bool clockSlave() const { return clockSlave_; }
  // MIDI IN: 24 ppqn clock tick (slave mode), transport from external clock.
  void onClockIn();

  void process(int samples);
  int currentStep(int track) const;
  uint32_t passCount(int track) const;
  float stepLengthSamples() const;

  // GEN for external tracks (same functional layer as internal parts).
  void setGenParams(int index, const GenParams& params);
  const GenParams& genParams(int index) const;
  GenParams& genParams(int index);

  // Live record: quantize note on/off to the current step (0..15).
  void liveRecordNoteOn(int track, int note, int velocity, int quantizedStep = -1);
  void liveRecordNoteOff(int track, int note, int quantizedStep = -1);

  // Clock jitter observed at emitted 24 ppqn ticks (model/measurement).
  float maxClockJitterUs() const { return maxJitterUs_; }
  uint64_t clockCount() const { return clockCount_; }
  void resetJitter() {
    maxJitterUs_ = 0.0f;
    clockCount_ = 0;
  }

  // Versioned, CRC32-protected external-track payload (project v2 / preset).
  static constexpr uint32_t kMagic = 0x45585450u;  // "EXTP"
  static constexpr uint16_t kVersion = 1;
  size_t serialize(uint8_t* out, size_t capacity) const;
  bool deserialize(const uint8_t* data, size_t size);
  size_t serializedSize() const;
  static uint32_t crc32(const uint8_t* data, size_t size);

 private:
  struct Runtime {
    double untilNext = 0.0;
    double noteOffCountdown = 0.0;
    int pendingNote = -1;
    int pendingChannel = 0;
    int step = 0;
    uint32_t pass = 0;
  };
  void triggerStep(int index);
  void noteOffIfPending(int index);
  void emitProgramChanges();
  void emitClockIfDue();

  float sampleRate_ = static_cast<float>(kSampleRate);
  float bpm_ = 120.0f;
  float swing_ = 0.0f;
  bool playing_ = false;
  bool clockMaster_ = true;
  bool clockSlave_ = false;
  float maxJitterUs_ = 0.0f;
  uint64_t clockCount_ = 0;
  int slaveTicks_ = 0;
  int lastRecordStep_[kExtTracks] = {};
  int lastRecordNote_[kExtTracks] = {};
  double clockAccumulator_ = 0.0;
  double lastClockTime_ = 0.0;
  double idealClockSample_ = 0.0;
  double absoluteSamples_ = 0.0;
  ExtTrack tracks_[kExtTracks];
  Runtime runtime_[kExtTracks];
  GenParams gen_[kExtTracks];
  GenArp arp_[kExtTracks];
  ExtSeqSink* sink_ = nullptr;
};

// Host/device MIDI output model: one logical event goes to DIN and USB exactly
// once (no duplicates).  Real DIN/TinyUSB transport is TODO(hw).
struct MidiOutMessage {
  uint32_t tick = 0;
  uint8_t status = 0;
  uint8_t data1 = 0;
  uint8_t data2 = 0;
};

class MidiOutRouter {
 public:
  static constexpr int kMaxMessages = 4096;
  void clear();
  void send(const MidiOutMessage& message);  // writes to DIN + USB exactly once
  int dinCount() const { return dinCount_; }
  int usbCount() const { return usbCount_; }
  const MidiOutMessage& dinAt(int index) const { return din_[index]; }
  const MidiOutMessage& usbAt(int index) const { return usb_[index]; }
  bool hasDuplicates() const;  // consecutive identical message on a port
  MidiOutMessage make(uint8_t status, uint8_t d1, uint8_t d2 = 0) const;

 private:
  MidiOutMessage din_[kMaxMessages];
  MidiOutMessage usb_[kMaxMessages];
  int dinCount_ = 0;
  int usbCount_ = 0;
  uint32_t tick_ = 0;
};

// Convenience sink that records into a MidiOutRouter (host model/tests).
class RouterExtSink : public ExtSeqSink {
 public:
  explicit RouterExtSink(MidiOutRouter* router) : router_(router) {}
  void onExtNoteOn(int track, int channel, int note, int velocity) override;
  void onExtNoteOff(int track, int channel, int note) override;
  void onExtProgramChange(int track, int channel, int program) override;
  void onExtControlChange(int track, int channel, int cc, int value) override;
  void onExtClock() override;
  void onExtStart() override;
  void onExtStop() override;
  void onExtContinue() override;

 private:
  MidiOutRouter* router_;
};

}  // namespace bukifon
