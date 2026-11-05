// SPDX-License-Identifier: GPL-3.0-or-later
#include "io/sequencer.hpp"

#include <cmath>
#include <cstring>

#include "core/math.hpp"

namespace bukifon {
namespace {
uint32_t hash32_seq(uint32_t x) {
  x ^= x >> 16;
  x *= 0x7feb352du;
  x ^= x >> 15;
  x *= 0x846ca68bu;
  x ^= x >> 16;
  return x;
}
}  // namespace

float StepModulator::eval(int step, uint32_t pass) const {
  switch (mode) {
    case Sine:
      return 0.5f + 0.5f * std::sin(math::kTwoPi * (static_cast<float>(step) / kStepMods +
                                                   static_cast<float>(pass) * 0.07f));
    case Saw:
      return static_cast<float>(step % kStepMods) / static_cast<float>(kStepMods);
    case Noise:
      return static_cast<float>(hash32_seq(static_cast<uint32_t>(step) * 2654435761u + pass) % 1000u) /
             999.0f;
    case EnvLoop: {
      // Loop envelope shape: 0 -> 1 -> 0 over 8 steps.
      const int s = step % kStepMods;
      const float x = static_cast<float>(s) / static_cast<float>(kStepMods - 1);
      return 1.0f - std::fabs(2.0f * x - 1.0f);
    }
    case Constant:
    default:
      return value;
  }
}

void Sequencer::init(float sampleRate) {
  sampleRate_ = sampleRate;
  ext_.init(sampleRate);
  for (int p = 0; p < kNumPatterns; ++p) {
    for (int t = 0; t < kMaxSeqTracks; ++t) {
      SequenceTrack& track = patterns_[p].tracks[t];
      track.length = kSeqSteps;
      track.speed = 1;
      for (int s = 0; s < kSeqSteps; ++s) {
        track.steps[s] = SequenceStep{};
        track.steps[s].note = static_cast<uint8_t>(48 + ((t % kSeqTracks) * 12) + (s % 12));
      }
      for (int i = 0; i < kStepMods; ++i) {
        track.mods[i] = StepModulator{};
      }
    }
  }
  reset();
}

void Sequencer::reset() {
  for (int t = 0; t < kSeqTracks; ++t) {
    runtime_[t] = TrackRuntime{};
    startStepTimer(t);
  }
  playing_ = false;
  externalClock_ = false;
  undoAvailable_ = false;
  chainLength_ = 0;
  chainPos_ = 0;
  for (int t = 0; t < kMaxSeqTracks; ++t) lastPlockCount_[t] = 0;
}

Pattern& Sequencer::pattern(int index) {
  index = math::clampInt(index, 0, kNumPatterns - 1);
  return patterns_[index];
}
const Pattern& Sequencer::pattern(int index) const {
  index = math::clampInt(index, 0, kNumPatterns - 1);
  return patterns_[index];
}

void Sequencer::setPatternIndex(int index) { patternIndex_ = math::clampInt(index, 0, kNumPatterns - 1); }

void Sequencer::setPlaying(bool playing) {
  ext_.setPlaying(playing);
  playing_ = playing;
  if (playing) {
    // Start from step 0 immediately (like Elektron PLAY).
    for (int t = 0; t < kSeqTracks; ++t) {
      runtime_[t] = TrackRuntime{};
      runtime_[t].untilNext = 0.0;
    }
  } else {
    for (int t = 0; t < kSeqTracks; ++t) noteOffIfPending(t);
  }
}

void Sequencer::setTrackLength(int track, int length) {
  if (track < 0 || track >= kSeqTracks) return;
  patterns_[patternIndex_].tracks[track].length =
      static_cast<uint8_t>(math::clampInt(length, 1, kSeqSteps));
}

int Sequencer::trackLength(int track) const {
  if (track < 0 || track >= kSeqTracks) return 0;
  return patterns_[patternIndex_].tracks[track].length;
}

void Sequencer::setTrackSpeed(int track, int speed) {
  if (track < 0 || track >= kSeqTracks) return;
  patterns_[patternIndex_].tracks[track].speed =
      static_cast<uint8_t>(math::clampInt(speed, 1, 8));
}

void Sequencer::setTrackMuted(int track, bool muted) {
  if (track < 0 || track >= kMaxSeqTracks) return;
  patterns_[patternIndex_].tracks[track].muted = muted;
  if (muted) noteOffIfPending(track);
}

bool Sequencer::trackMuted(int track) const {
  if (track < 0 || track >= kMaxSeqTracks) return false;
  return patterns_[patternIndex_].tracks[track].muted;
}

int Sequencer::trackSpeed(int track) const {
  if (track < 0 || track >= kSeqTracks) return 0;
  return patterns_[patternIndex_].tracks[track].speed;
}

float Sequencer::stepLengthSeconds() const { return 60.0f / bpm_ / 4.0f; }
float Sequencer::stepLengthSamples(int track) const {
  return stepLengthSeconds() * static_cast<float>(trackSpeed(track)) * sampleRate_;
}

int Sequencer::currentStep(int track) const {
  if (track < 0 || track >= kSeqTracks) return 0;
  return runtime_[track].step;
}
uint32_t Sequencer::passCount(int track) const {
  if (track < 0 || track >= kSeqTracks) return 0;
  return runtime_[track].pass;
}

double Sequencer::stepSamplesFor(int track, int nextStep) const {
  double stepSamples = static_cast<double>(stepLengthSamples(track));
  // Swing delays odd 16ths (50..70 % feel).
  if ((nextStep & 1) != 0) stepSamples += stepSamples * static_cast<double>(swing_) * 0.5;
  // Micro timing: +/- 1/16 of a step (parameter is -8..+8 -> up to +/- 1/2 step).
  const SequenceTrack& tr = patterns_[patternIndex_].tracks[track];
  const int micro = tr.steps[(nextStep < tr.length) ? nextStep : 0].micro;
  stepSamples += static_cast<double>(micro) / 16.0 * stepSamples;
  return stepSamples;
}

void Sequencer::startStepTimer(int track) {
  SequenceTrack& tr = patterns_[patternIndex_].tracks[track];
  runtime_[track].untilNext = stepSamplesFor(track, runtime_[track].step);
  runtime_[track].pendingNote = -1;
  runtime_[track].noteOffCountdown = 0.0;
  (void)tr;
}

bool Sequencer::conditionPasses(const SequenceStep& s, int track, uint32_t pass) const {
  switch (s.condition) {
    case TrigFirst:
      return pass == 0;
    case TrigNotFirst:
      return pass != 0;
    case TrigFill:
      return fill_;
    case TrigNotFill:
      return !fill_;
    case TrigAB: {
      const int b = (s.condB < 1) ? 1 : s.condB;
      const int a = (s.condA < 1) ? 1 : s.condA;
      return static_cast<int>(pass % static_cast<uint32_t>(b)) == (a - 1);
    }
    case TrigPercent: {
      const uint32_t h = hash32_seq(static_cast<uint32_t>(track) * 73856093u ^
                                static_cast<uint32_t>(s.note) * 19349663u ^ (pass * 83492791u));
      return static_cast<int>(h % 100u) < s.percent;
    }
    case TrigAlways:
    default:
      return true;
  }
}

void Sequencer::noteOffIfPending(int track) {
  TrackRuntime& rt = runtime_[track];
  if (rt.pendingNote >= 0 && sink_) {
    sink_->onSeqNoteOff(track, rt.pendingNote);
  }
  rt.pendingNote = -1;
  rt.noteOffCountdown = 0.0;
}

void Sequencer::setGenParams(int track, const GenParams& params) {
  if (track < 0 || track >= kMaxSeqTracks) return;
  gen_[track] = params;
  genArp_[track].setParams(params.arpRate, params.arpMode);
}

const GenParams& Sequencer::genParams(int track) const {
  static const GenParams kNeutral;
  return (track >= 0 && track < kMaxSeqTracks) ? gen_[track] : kNeutral;
}

GenParams& Sequencer::genParams(int track) {
  static GenParams fallback;
  if (track < 0 || track >= kMaxSeqTracks) return fallback;
  return gen_[track];
}

void Sequencer::setGenSeed(int track, uint32_t seed) {
  if (track < 0 || track >= kMaxSeqTracks) return;
  gen_[track].seed = seed;
}

void Sequencer::triggerStep(int track) {
  SequenceTrack& tr = patterns_[patternIndex_].tracks[track];
  const int stepIndex = runtime_[track].step % (tr.length > 0 ? tr.length : kSeqSteps);
  SequenceStep& s = tr.steps[stepIndex];
  const uint32_t pass = runtime_[track].pass;

  if (sink_) sink_->onSeqStep(track, stepIndex, pass);

  // Restore parameters p-locked by the previous step (Elektron p-locks last for
  // the duration of their step only), then apply this step's locks.
  if (sink_) {
    for (int i = 0; i < lastPlockCount_[track]; ++i) {
      const uint8_t param = lastPlockParams_[track][i];
      bool lockedAgain = false;
      for (int k = 0; k < s.plockCount && k < kPlocksPerStep; ++k) {
        if (s.plocks[k].param == param) {
          lockedAgain = true;
          break;
        }
      }
      if (!lockedAgain) sink_->onSeqPlockRestore(track, param);
    }
    lastPlockCount_[track] = 0;
    for (int i = 0; i < s.plockCount && i < kPlocksPerStep; ++i) {
      sink_->onSeqPlock(track, s.plocks[i].param,
                        static_cast<float>(s.plocks[i].value) / 255.0f);
      lastPlockParams_[track][i] = s.plocks[i].param;
      lastPlockCount_[track] = static_cast<uint8_t>(i + 1);
    }
  }

  if (!tr.muted && s.active && conditionPasses(s, track, pass)) {
    noteOffIfPending(track);
    if (s.soundLock >= 0 && sink_) sink_->onSeqSoundLock(track, s.soundLock);
    // Generative step modulators: modulate note, velocity and gate length.
    int note = s.note;
    int velocity = s.velocity;
    int gate = s.gate;
    if (tr.modCount > 0) {
      const StepModulator& mNote = tr.mods[0];
      const StepModulator& mVel = tr.mods[tr.modCount > 1 ? 1 : 0];
      const StepModulator& mGate = tr.mods[tr.modCount > 2 ? 2 : 0];
      note += static_cast<int>(std::lround((mNote.eval(stepIndex, pass) - 0.5f) * 24.0f));
      velocity = static_cast<int>(std::lround(static_cast<float>(velocity) *
                                              (0.5f + mVel.eval(stepIndex, pass))));
      gate = static_cast<int>(std::lround(static_cast<float>(gate) *
                                          (0.5f + mGate.eval(stepIndex, pass))));
    }
    note = math::clampInt(note, 0, 127);
    velocity = math::clampInt(velocity, 1, 127);
    gate = math::clampInt(gate, 1, 200);
    // Generative layer: probability/Euclid/mutate/scale-lock/accent and ARP.
    const GenParams& gp = gen_[track];
    const int globalStep = static_cast<int>(pass) * (tr.length > 0 ? tr.length : kSeqSteps) +
                           stepIndex;
    GenStepResult generated = genApplyStep(gp, track, globalStep, note, velocity);
    if (gp.arpOn) {
      uint8_t held[16];
      int heldCount = 0;
      for (int h = 0; h < tr.length && h < kSeqSteps && heldCount < 16; ++h) {
        if (tr.steps[h].active) held[heldCount++] = tr.steps[h].note;
      }
      const int arpNote = genArp_[track].noteAt(
          held, heldCount,
          static_cast<uint32_t>(globalStep) * 2u);
      if (arpNote >= 0) {
        generated.note = genScaleLockNote(arpNote, gp.scale);
        generated.trigger = true;
      }
    }
    if (generated.trigger) {
      if (sink_) sink_->onSeqNoteOn(track, generated.note, generated.velocity);
      TrackRuntime& rt = runtime_[track];
      rt.pendingNote = generated.note;
      rt.noteOffCountdown = static_cast<double>(stepLengthSamples(track)) * gate / 100.0;
    }
  }

  runtime_[track].step = (runtime_[track].step + 1) % (tr.length > 0 ? tr.length : kSeqSteps);
  if (runtime_[track].step == 0) {
    ++runtime_[track].pass;
    if (track == 0 && chainLength_ > 0) advanceChain();
    if (gen_[track].evolve) {
      const int bar = static_cast<int>(runtime_[track].pass);
      for (int h = 0; h < tr.length && h < kSeqSteps; ++h) {
        tr.steps[h].note = static_cast<uint8_t>(genEvolveNote(
            gen_[track].seed, track, bar, h, tr.steps[h].note, 2));
      }
    }
  }
}

void Sequencer::process(int samples) {
  ext_.process(samples);
  if (!playing_) return;
  if (externalClock_) return;  // driven by onClockTick()
  for (int i = 0; i < samples; ++i) {
    for (int t = 0; t < kSeqTracks; ++t) {
      TrackRuntime& rt = runtime_[t];
      if (rt.pendingNote >= 0) {
        rt.noteOffCountdown -= 1.0;
        if (rt.noteOffCountdown <= 0.0) noteOffIfPending(t);
      }
      rt.untilNext -= 1.0;
      if (rt.untilNext <= 0.0) {
        triggerStep(t);
        rt.untilNext += stepSamplesFor(t, runtime_[t].step) + 1.0;
      }
    }
  }
}

void Sequencer::onClockTick() {
  if (!playing_ || !externalClock_) return;
  for (int t = 0; t < kSeqTracks; ++t) {
    TrackRuntime& rt = runtime_[t];
    ++rt.clockTicks;
    const int ticksPerStep = 6 * trackSpeed(t);
    if (rt.clockTicks >= ticksPerStep) {
      rt.clockTicks = 0;
      triggerStep(t);
    }
  }
}

void Sequencer::onStart() {
  ext_.start();
  for (int t = 0; t < kSeqTracks; ++t) {
    runtime_[t] = TrackRuntime{};
    runtime_[t].untilNext = 0.0;  // step 0 on the first clock tick
  }
  playing_ = true;
}
void Sequencer::onStop() {
  ext_.stop(); setPlaying(false); }
void Sequencer::onContinue() {
  ext_.continuePlay(); playing_ = true; }

SequenceStep& Sequencer::step(int track, int index) {
  track = math::clampInt(track, 0, kSeqTracks - 1);
  index = math::clampInt(index, 0, kSeqSteps - 1);
  return patterns_[patternIndex_].tracks[track].steps[index];
}
const SequenceStep& Sequencer::step(int track, int index) const {
  track = math::clampInt(track, 0, kSeqTracks - 1);
  index = math::clampInt(index, 0, kSeqSteps - 1);
  return patterns_[patternIndex_].tracks[track].steps[index];
}

void Sequencer::setPlock(int track, int index, int slot, uint8_t param, uint8_t value) {
  if (track < 0 || track >= kSeqTracks || index < 0 || index >= kSeqSteps) return;
  if (slot < 0 || slot >= kPlocksPerStep) return;
  // Save undo state (single level, like Elektron "undo").
  undoSnapshot_ = patterns_[patternIndex_];
  undoPatternIndex_ = patternIndex_;
  undoAvailable_ = true;
  SequenceStep& s = patterns_[patternIndex_].tracks[track].steps[index];
  s.plocks[slot].param = param;
  s.plocks[slot].value = value;
  if (slot + 1 > s.plockCount) s.plockCount = static_cast<uint8_t>(slot + 1);
}

void Sequencer::clearPlocks(int track, int index) {
  if (track < 0 || track >= kSeqTracks || index < 0 || index >= kSeqSteps) return;
  SequenceStep& s = patterns_[patternIndex_].tracks[track].steps[index];
  s.plockCount = 0;
}

void Sequencer::copyStep(int track, int from, int to) {
  if (track < 0 || track >= kSeqTracks) return;
  if (from < 0 || from >= kSeqSteps || to < 0 || to >= kSeqSteps) return;
  undoSnapshot_ = patterns_[patternIndex_];
  undoPatternIndex_ = patternIndex_;
  undoAvailable_ = true;
  patterns_[patternIndex_].tracks[track].steps[to] =
      patterns_[patternIndex_].tracks[track].steps[from];
}

void Sequencer::undo() {
  if (!undoAvailable_ || undoPatternIndex_ < 0) return;
  // Single-level undo restores the whole pattern slot from the saved snapshot.
  patterns_[undoPatternIndex_] = undoSnapshot_;
  patternIndex_ = undoPatternIndex_;
  undoAvailable_ = false;
}

void Sequencer::setChain(const uint8_t* chain, int length) {
  chainLength_ = math::clampInt(length, 0, kMaxPatternChain);
  for (int i = 0; i < chainLength_; ++i) chain_[i] = chain[i] % kNumPatterns;
  chainPos_ = 0;
}

void Sequencer::advanceChain() {
  if (chainLength_ == 0) return;
  chainPos_ = (chainPos_ + 1) % chainLength_;
  patternIndex_ = chain_[chainPos_];
}

StepModulator& Sequencer::modulator(int track, int index) {
  track = math::clampInt(track, 0, kSeqTracks - 1);
  index = math::clampInt(index, 0, kStepMods - 1);
  return patterns_[patternIndex_].tracks[track].mods[index];
}
const StepModulator& Sequencer::modulator(int track, int index) const {
  track = math::clampInt(track, 0, kSeqTracks - 1);
  index = math::clampInt(index, 0, kStepMods - 1);
  return patterns_[patternIndex_].tracks[track].mods[index];
}

}  // namespace bukifon
