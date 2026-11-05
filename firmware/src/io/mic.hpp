// SPDX-License-Identifier: GPL-3.0-or-later
// Voice as input (docs/71): MEMS I2S1 / line-in capture model, voice recording
// to a pad (<=30 s, silence auto-trim), beatbox onset -> sequencer steps, and
// privacy (hardware mute switch + LED, no network transmission).
//
// Host model: the real I2S1 DMA, PSRAM/SD write and MAX9814/PCM1808 mux are
// TODO(hw).  Everything here is portable and tested without hardware.
#pragma once

#include <cstddef>
#include <cstdint>

#include "core/config.hpp"
#include "io/sequencer.hpp"

namespace bukifon {

enum class MicSource : uint8_t { Line = 0, Mic = 1 };
enum class MicStorage : uint8_t { Psram = 0, Sd = 1 };
enum class BeatboxClass : uint8_t { Kick = 0, Snare = 1, Hat = 2, kNumClasses };

constexpr int kMicMaxSeconds = 30;
constexpr int kMicMaxFrames = kMicMaxSeconds * kSampleRate;

struct MicConfig {
  MicSource source = MicSource::Mic;
  float gainDb = 20.0f;      // 0..60 dB (MAX9814 AGC range model)
  float threshold = 0.02f;   // VAD / onset threshold 0..1
  float sensitivity = 0.5f;  // beatbox sensitivity 0..1
  bool monitor = false;
  bool beatbox = false;
};

struct MicPrivacy {
  bool muteSwitch = true;  // hardware mute (power/signal cut) — default muted
  bool led = false;        // "MIC ON" LED
  void setMuteSwitch(bool mute) {
    muteSwitch = mute;
    led = !mute;  // LED only when the mic is powered/active
  }
  bool recordingAllowed() const { return !muteSwitch; }
};

struct VoiceTake {
  char name[24] = "TAKE 1";
  int pad = 0;
  MicStorage storage = MicStorage::Psram;
  uint32_t frames = 0;
  uint32_t capacity = 0;
  float* data = nullptr;
  bool valid = false;
  float peak = 0.0f;
};

struct BeatboxHit {
  int step = 0;              // 0..15
  uint8_t velocity = 100;    // accent from energy
  BeatboxClass cls = BeatboxClass::Kick;
};

class MicCapture {
 public:
  ~MicCapture();
  bool init(float sampleRate = static_cast<float>(kSampleRate));
  void setConfig(const MicConfig& config) { config_ = config; }
  const MicConfig& config() const { return config_; }
  MicPrivacy& privacy() { return privacy_; }
  const MicPrivacy& privacy() const { return privacy_; }

  // Push capture frames (already at 48 kHz); updates level/peak/VAD and the
  // active recording.  `gainDb` is applied to the level model.
  void push(const float* samples, int frames);

  float level() const { return level_; }
  float peak() const { return peak_; }
  bool vadActive() const { return vad_; }

  bool beginRecording(const char* name, int pad, MicStorage storage = MicStorage::Psram);
  bool recording() const { return recording_; }
  bool endRecording();  // trims leading/trailing silence
  const VoiceTake& take() const { return take_; }
  void clearTake();

 private:
  float sampleRate_ = static_cast<float>(kSampleRate);
  MicConfig config_{};
  MicPrivacy privacy_{};
  float level_ = 0.0f;
  float peak_ = 0.0f;
  bool vad_ = false;
  bool recording_ = false;
  uint32_t recorded_ = 0;
  uint32_t aboveThreshold_ = 0;
  VoiceTake take_{};
};

// Offline beatbox analyser: energy + derivative onset per 1/16 window, simple
// low/high band classification (kick/snare/hat), velocity -> accent.
class BeatboxDetector {
 public:
  void init(float sampleRate = static_cast<float>(kSampleRate), float bpm = 120.0f,
            float sensitivity = 0.5f);
  int analyzeBar(const float* samples, int frames, BeatboxHit* hits, int maxHits) const;
  // Apply hits to a 16-step pattern; returns number of steps changed.
  static int applyToSteps(const BeatboxHit* hits, int count, SequenceTrack* track);
  static bool stepClassToNote(BeatboxClass cls, uint8_t* note);
  static const char* className(BeatboxClass cls);
};

// Beatbox apply with a single UNDO snapshot (docs/71 §4, docs/68 «обратимость»).
class BeatboxPattern {
 public:
  int apply(const BeatboxHit* hits, int count, SequenceTrack* track);
  bool undo(SequenceTrack* track);
  bool hasUndo() const { return hasUndo_; }

 private:
  SequenceTrack before_{};
  bool hasUndo_ = false;
};

// Privacy invariant: no automatic transmission of captured audio over BLE/Wi-Fi.
constexpr bool micNetworkTransmissionAllowed(bool explicitUserAction) {
  return explicitUserAction;  // never implicitly true in firmware
}

}  // namespace bukifon
