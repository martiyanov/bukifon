// SPDX-License-Identifier: GPL-3.0-or-later
#include "io/mic.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>

namespace bukifon {
namespace {

float dbToGain(float db) { return std::pow(10.0f, db / 20.0f); }

}  // namespace

MicCapture::~MicCapture() {
  delete[] take_.data;
  take_.data = nullptr;
}

bool MicCapture::init(float sampleRate) {
  sampleRate_ = sampleRate;
  config_ = MicConfig{};
  privacy_.setMuteSwitch(true);  // privacy by default: muted until switched on
  level_ = 0.0f;
  peak_ = 0.0f;
  vad_ = false;
  recording_ = false;
  recorded_ = 0;
  delete[] take_.data;
  take_ = VoiceTake{};
  return true;
}

void MicCapture::push(const float* samples, int frames) {
  if (!samples || frames <= 0) return;
  const float gain = dbToGain(config_.gainDb);
  float sum = 0.0f;
  float localPeak = 0.0f;
  for (int i = 0; i < frames; ++i) {
    const float sample = samples[i] * gain;
    const float clamped = sample < -1.0f ? -1.0f : (sample > 1.0f ? 1.0f : sample);
    sum += clamped * clamped;
    localPeak = std::max(localPeak, std::fabs(clamped));
    if (recording_ && take_.data && recorded_ < take_.capacity) {
      take_.data[recorded_++] = clamped;
      if (clamped > config_.threshold) ++aboveThreshold_;
    }
  }
  level_ = std::sqrt(sum / static_cast<float>(frames));
  peak_ = localPeak;
  vad_ = level_ > config_.threshold;
}

bool MicCapture::beginRecording(const char* name, int pad, MicStorage storage) {
  if (!privacy_.recordingAllowed()) return false;  // hardware mute blocks REC
  if (recording_) return false;
  clearTake();
  take_.data = new (std::nothrow) float[kMicMaxFrames];
  if (!take_.data) return false;
  take_.capacity = kMicMaxFrames;
  take_.pad = pad;
  take_.storage = storage;
  std::snprintf(take_.name, sizeof(take_.name), "%s", name ? name : "TAKE");
  recorded_ = 0;
  aboveThreshold_ = 0;
  recording_ = true;
  return true;
}

bool MicCapture::endRecording() {
  if (!recording_) return false;
  recording_ = false;
  if (!take_.data || recorded_ == 0) return false;
  // Auto-trim leading/trailing silence (threshold from config).
  uint32_t first = 0;
  while (first < recorded_ && std::fabs(take_.data[first]) <= config_.threshold) ++first;
  uint32_t last = recorded_;
  while (last > first && std::fabs(take_.data[last - 1]) <= config_.threshold) --last;
  if (first >= last) {
    clearTake();
    return false;
  }
  const uint32_t trimmed = last - first;
  if (first > 0) std::memmove(take_.data, take_.data + first, sizeof(float) * trimmed);
  take_.frames = trimmed;
  take_.peak = 0.0f;
  for (uint32_t i = 0; i < trimmed; ++i) take_.peak = std::max(take_.peak, std::fabs(take_.data[i]));
  take_.valid = true;
  return true;
}

void MicCapture::clearTake() {
  delete[] take_.data;
  take_.data = nullptr;
  const int pad = take_.pad;
  const MicStorage storage = take_.storage;
  take_ = VoiceTake{};
  take_.pad = pad;
  take_.storage = storage;
  recorded_ = 0;
  aboveThreshold_ = 0;
  recording_ = false;
}

void BeatboxDetector::init(float sampleRate, float bpm, float sensitivity) {
  (void)sampleRate;
  (void)bpm;
  (void)sensitivity;
}

int BeatboxDetector::analyzeBar(const float* samples, int frames, BeatboxHit* hits,
                                int maxHits) const {
  if (!samples || frames <= 0 || !hits || maxHits <= 0) return 0;
  // Fixed 16-step analysis, 3 ms energy windows at 48 kHz; works offline from
  // the recorded bar (host) and on block boundaries (device).
  const int step = frames / kSeqSteps > 0 ? frames / kSeqSteps : 1;
  float energy[kSeqSteps] = {};
  float low[kSeqSteps] = {};
  float high[kSeqSteps] = {};
  float zcr[kSeqSteps] = {};
  for (int s = 0; s < kSeqSteps; ++s) {
    float lp = 0.0f;
    const int start = s * step;
    const int end = std::min(frames, start + step);
    float previous = 0.0f;
    for (int i = start; i < end; ++i) {
      const float x = samples[i];
      lp += 0.08f * (x - lp);  // one-pole low band
      energy[s] += x * x;
      low[s] += lp * lp;
      high[s] += (x - lp) * (x - lp);
      if (i > start && ((x >= 0.0f) != (previous >= 0.0f))) zcr[s] += 1.0f;
      previous = x;
    }
    const float n = static_cast<float>(std::max(1, end - start));
    energy[s] /= n;
    low[s] /= n;
    high[s] /= n;
    zcr[s] /= n;
  }
  float maxEnergy = 0.0f;
  for (int s = 0; s < kSeqSteps; ++s) maxEnergy = std::max(maxEnergy, energy[s]);
  if (maxEnergy <= 1e-7f) return 0;
  int count = 0;
  for (int s = 0; s < kSeqSteps && count < maxHits; ++s) {
    if (energy[s] <= 1e-6f || energy[s] < maxEnergy * 0.03f) continue;
    // Local peak + energy rise (per-16th window); robust for quiet snares/hats.
    const bool rise = (s == 0) || (energy[s] >= energy[s - 1] * 1.25f);
    const bool fall = (s == kSeqSteps - 1) || (energy[s] >= energy[s + 1] * 1.25f);
    // Chained quiet hits (e.g. 8th-note hats) are accepted on the rise alone.
    const bool onset = (rise && fall) || (rise && energy[s] > maxEnergy * 0.08f);
    if (!onset) continue;
    BeatboxHit& hit = hits[count++];
    hit.step = s;
    const float norm = std::min(1.0f, std::sqrt(energy[s]) * 2.0f);
    hit.velocity = static_cast<uint8_t>(std::max(30.0f, 40.0f + norm * 87.0f));
    if (low[s] > high[s] * 1.2f) {
      hit.cls = BeatboxClass::Kick;
    } else if (zcr[s] > 0.8f) {
      hit.cls = BeatboxClass::Hat;
    } else {
      hit.cls = BeatboxClass::Snare;
    }
  }
  return count;
}

bool BeatboxDetector::stepClassToNote(BeatboxClass cls, uint8_t* note) {
  if (!note) return false;
  switch (cls) {
    case BeatboxClass::Kick: *note = 36; break;
    case BeatboxClass::Snare: *note = 38; break;
    case BeatboxClass::Hat: *note = 42; break;
    default: return false;
  }
  return true;
}

int BeatboxDetector::applyToSteps(const BeatboxHit* hits, int count, SequenceTrack* track) {
  if (!hits || !track || count <= 0) return 0;
  int changed = 0;
  for (int i = 0; i < count && i < kSeqSteps; ++i) {
    const BeatboxHit& hit = hits[i];
    if (hit.step < 0 || hit.step >= kSeqSteps) continue;
    SequenceStep& step = track->steps[hit.step];
    step.active = true;
    step.velocity = hit.velocity;
    step.condition = TrigAlways;
    uint8_t note = 60;
    stepClassToNote(hit.cls, &note);
    step.note = note;
    ++changed;
  }
  return changed;
}

int BeatboxPattern::apply(const BeatboxHit* hits, int count, SequenceTrack* track) {
  if (!hits || !track || count <= 0) return 0;
  before_ = *track;
  hasUndo_ = true;
  return BeatboxDetector::applyToSteps(hits, count, track);
}

bool BeatboxPattern::undo(SequenceTrack* track) {
  if (!track || !hasUndo_) return false;
  *track = before_;
  hasUndo_ = false;
  return true;
}

const char* BeatboxDetector::className(BeatboxClass cls) {
  switch (cls) {
    case BeatboxClass::Kick: return "KICK";
    case BeatboxClass::Snare: return "SNARE";
    case BeatboxClass::Hat: return "HAT";
    default: return "?";
  }
}

}  // namespace bukifon
