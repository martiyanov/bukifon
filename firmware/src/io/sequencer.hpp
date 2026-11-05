// SPDX-License-Identifier: GPL-3.0-or-later
// Elektron-flavoured 16-step sequencer: 4 tracks (one per part), parameter locks,
// sound locks, trig conditions, micro timing, swing, per-track length/speed,
// pattern chain, undo, generative step modulators and MIDI clock.
#pragma once

#include <cstdint>

#include "core/config.hpp"

namespace bukifon {

enum TrigCondition : uint8_t {
  TrigAlways = 0,
  TrigFirst,
  TrigNotFirst,
  TrigFill,
  TrigNotFill,
  TrigAB,       // A:B, using condA/condB
  TrigPercent,  // probability, using percent
  kNumTrigConditions
};

struct StepPlock {
  uint8_t param = 0;  // PartParam index (fits in a byte)
  uint8_t value = 0;  // normalised 0..255
};

struct SequenceStep {
  uint8_t note = 60;
  uint8_t velocity = 100;
  uint8_t gate = 64;  // gate length in % of the step
  uint8_t condition = TrigAlways;
  uint8_t condA = 1;
  uint8_t condB = 1;
  uint8_t percent = 100;
  int8_t micro = 0;    // +/- 1/16 of a step
  int8_t soundLock = -1;
  bool active = true;
  uint8_t plockCount = 0;
  StepPlock plocks[kPlocksPerStep];
};

// Generative layer: an 8-step functional modulator per track (Kaleidoscope style).
struct StepModulator {
  enum Mode : uint8_t { Constant = 0, Sine, Saw, Noise, EnvLoop, kNumModes };
  uint8_t mode = Constant;
  float value = 0.5f;
  float eval(int step, uint32_t pass) const;
};

struct SequenceTrack {
  SequenceStep steps[kSeqSteps];
  uint8_t length = kSeqSteps;
  uint8_t speed = 1;  // 1..8 multiplier of the 16th step length
  StepModulator mods[kStepMods];
  uint8_t modCount = 0;
};

struct Pattern {
  SequenceTrack tracks[kSeqTracks];
};

class SequencerSink {
 public:
  virtual ~SequencerSink() = default;
  virtual void onSeqNoteOn(int track, int note, int velocity) {
    (void)track; (void)note; (void)velocity;
  }
  virtual void onSeqNoteOff(int track, int note) { (void)track; (void)note; }
  virtual void onSeqPlock(int track, int param, float normalized) {
    (void)track; (void)param; (void)normalized;
  }
  virtual void onSeqSoundLock(int track, int preset) { (void)track; (void)preset; }
  virtual void onSeqStep(int track, int step, uint32_t pass) {
    (void)track; (void)step; (void)pass;
  }
};

class Sequencer {
 public:
  void init(float sampleRate = static_cast<float>(kSampleRate));
  void reset();
  void setSink(SequencerSink* sink) { sink_ = sink; }
  SequencerSink* sink() const { return sink_; }

  Pattern& pattern(int index);
  const Pattern& pattern(int index) const;
  void setPatternIndex(int index);
  int patternIndex() const { return patternIndex_; }

  void setBpm(float bpm) { bpm_ = bpm; }
  float bpm() const { return bpm_; }
  void setSwing(float swing) { swing_ = swing; }
  float swing() const { return swing_; }
  void setPlaying(bool playing);
  bool playing() const { return playing_; }
  void setFill(bool fill) { fill_ = fill; }
  bool fill() const { return fill_; }
  void setExternalClock(bool external) { externalClock_ = external; }
  bool externalClock() const { return externalClock_; }

  void setTrackLength(int track, int length);
  int trackLength(int track) const;
  void setTrackSpeed(int track, int speed);
  int trackSpeed(int track) const;

  void process(int samples);
  void onClockTick();  // 24 ppqn from MIDI clock
  void onStart();
  void onStop();
  void onContinue();

  int currentStep(int track) const;
  uint32_t passCount(int track) const;
  float stepLengthSamples(int track) const;
  float stepLengthSeconds() const;

  // Editing / Elektron workflow.
  SequenceStep& step(int track, int index);
  const SequenceStep& step(int track, int index) const;
  void setPlock(int track, int index, int slot, uint8_t param, uint8_t value);
  void clearPlocks(int track, int index);
  void copyStep(int track, int from, int to);
  void undo();
  bool undoAvailable() const { return undoAvailable_; }
  void setChain(const uint8_t* chain, int length);
  const uint8_t* chain() const { return chain_; }
  int chainLength() const { return chainLength_; }
  void advanceChain();

  StepModulator& modulator(int track, int index);
  const StepModulator& modulator(int track, int index) const;

 private:
  struct TrackRuntime {
    double untilNext = 0.0;
    double noteOffCountdown = 0.0;
    int pendingNote = -1;
    int step = 0;
    uint32_t pass = 0;
    uint8_t clockTicks = 0;
  };

  void triggerStep(int track);
  void noteOffIfPending(int track);
  bool conditionPasses(const SequenceStep& s, int track, uint32_t pass) const;
  double stepSamplesFor(int track, int nextStep) const;
  void startStepTimer(int track);

  float sampleRate_ = static_cast<float>(kSampleRate);
  float bpm_ = 120.0f;
  float swing_ = 0.0f;
  bool playing_ = false;
  bool fill_ = false;
  bool externalClock_ = false;
  bool undoAvailable_ = false;

  Pattern patterns_[kNumPatterns];
  int patternIndex_ = 0;
  Pattern undoSnapshot_{};
  int undoPatternIndex_ = -1;

  TrackRuntime runtime_[kSeqTracks];
  SequencerSink* sink_ = nullptr;

  uint8_t chain_[kMaxPatternChain] = {};
  int chainLength_ = 0;
  int chainPos_ = 0;
};

}  // namespace bukifon
