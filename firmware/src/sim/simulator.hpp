// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon host simulator — one deterministic event stream drives the engine,
// the sequencer and the UI snapshot.  The UI never owns live state: it only
// receives a UiSnapshot built here, so the same code path runs in tests, the
// screenshot tool and (later) on the device.
#pragma once

#include <cstdint>
#include <functional>
#include <vector>

#include "audio/engine.hpp"
#include "core/device_mode.hpp"
#include "io/sequencer.hpp"
#include "sim/event_log.hpp"
#include "ui/ui800.hpp"

namespace bukifon {
namespace sim {

class Simulator : public SequencerSink {
 public:
  struct Options {
    float sampleRate;
    int blockFrames;
    bool recordObservationLog;
    explicit Options(float sr = static_cast<float>(kSampleRate), int block = 128,
                     bool record = true)
        : sampleRate(sr), blockFrames(block), recordObservationLog(record) {}
  };

  struct Stats {
    uint64_t frames = 0;
    uint64_t blocks = 0;
    double seconds = 0.0;
    float peak = 0.0f;
    double renderSeconds = 0.0;
  };

  void init(const Options& options = Options{});
  void reset();

  // --- external event stream -------------------------------------------------
  void addEvent(const SimEvent& event);
  void addEvent(uint64_t frame, SimEventType type, uint8_t a, uint8_t b, float value);
  bool loadEvents(const char* path);
  bool saveEvents(const char* path) const;
  const EventLog& pendingEvents() const { return pending_; }
  size_t pendingEventCount() const { return pending_.size(); }

  // --- transport / edit API (sugar over events, applied immediately) --------
  void play();
  void stop();
  void togglePlay();
  void setBpm(float bpm);
  void setPattern(int pattern);
  void setTrackMuted(int track, bool muted);
  void setPartParam(int part, int paramId, float value);
  void setGlobalParam(int paramId, float value);
  void selectParam(int index) { selectedParam_ = index < 0 ? 0 : (index > 7 ? 7 : index); }
  bool setDeviceMode(DeviceMode mode);
  DeviceMode deviceMode() const { return modeManager_.mode(); }

  // --- sequencer demo pattern -------------------------------------------------
  // 4 tracks x 16 steps, deterministic notes/velocities, one p-lock on track 1,
  // step 5 (Cutoff).  Track 4 starts muted for the vertical-slice demo.
  void buildDemoPattern();

  // --- run -------------------------------------------------------------------
  void runSamples(uint64_t frames);
  void runSeconds(double seconds);
  void runBars(int bars);

  // Builds the demo pattern, plays `bars` bars and returns the observation log.
  const EventLog& runDemo(int bars = 16);

  uint64_t frame() const { return frame_; }
  double seconds() const { return static_cast<double>(frame_) / options_.sampleRate; }
  bool playing() const { return sequencer_.playing(); }
  const Stats& stats() const { return stats_; }

  const EventLog& observationLog() const { return observation_; }
  bool saveObservationLog(const char* path) const { return observation_.saveToFile(path); }

  // --- UI snapshot (pure data; the UI draws it) ------------------------------
  ui::UiSnapshot snapshot(ui::Screen screen = ui::Screen::Main) const;

  Engine& engine() { return engine_; }
  const Engine& engine() const { return engine_; }
  Sequencer& sequencer() { return sequencer_; }
  const Sequencer& sequencer() const { return sequencer_; }

  // SequencerSink — forwarded to the engine and recorded in the observation log.
  void onSeqNoteOn(int track, int note, int velocity) override;
  void onSeqNoteOff(int track, int note) override;
  void onSeqPlock(int track, int param, float normalized) override;
  void onSeqPlockRestore(int track, int param) override;
  void onSeqSoundLock(int track, int preset) override;
  void onSeqStep(int track, int step, uint32_t pass) override;
  float seqParamBase(int track, int param) const override;

  static uint64_t samplesPerBar(float bpm, float sampleRate);

 private:
  void applyEvent(const SimEvent& event);
  void observe(SimEventType type, uint8_t a, uint8_t b, float value);
  void updateAudioPeak(const float* l, const float* r, int frames);
  void buildSnapshot(ui::UiSnapshot* snapshot, ui::Screen screen) const;
  static void formatParamValue(const ParamMeta& meta, float value, char* out, size_t capacity);
  void fillParamsForScreen(ui::UiSnapshot* snapshot, ui::Screen screen) const;

  Options options_{};
  Engine engine_;
  Sequencer sequencer_;
  EventLog pending_;
  size_t pendingIndex_ = 0;
  EventLog observation_;
  ui::UiSnapshot cachedSnapshot_;
  DeviceModeManager modeManager_;
  Stats stats_{};
  uint64_t frame_ = 0;
  int selectedParam_ = 0;
  float lastPeak_ = 0.0f;
  float plockSaved_[kNumParts][kNumPartParams] = {};
  bool plockSavedValid_[kNumParts][kNumPartParams] = {};
  bool initialized_ = false;
};

}  // namespace sim
}  // namespace bukifon
