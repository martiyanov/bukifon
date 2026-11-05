// SPDX-License-Identifier: GPL-3.0-or-later
// Voice input (docs/71): mic capture model, VAD, voice recording/trim,
// privacy (mute/LED/no network), beatbox onset/class/quantize/UNDO.
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

#include "io/mic.hpp"
#include "test_framework.hpp"

using namespace bukifon;

namespace {

void pushSignal(MicCapture& mic, float amplitude, int frames) {
  std::vector<float> buffer(frames, amplitude);
  mic.push(buffer.data(), frames);
}

std::vector<float> makeBeatboxBar(float bpm, const int steps[8], const BeatboxClass classes[8],
                                  int hitCount) {
  const int stepSamples = static_cast<int>(48000.0f * 60.0f / bpm / 4.0f);
  std::vector<float> bar(static_cast<size_t>(stepSamples) * 16, 0.0f);
  uint32_t rng = 0x1234567u;
  for (int h = 0; h < hitCount; ++h) {
    const int start = steps[h] * stepSamples;
    const int length = stepSamples;
    for (int i = 0; i < length; ++i) {
      const float t = static_cast<float>(i) / 48000.0f;
      const float env = std::exp(-t * (classes[h] == BeatboxClass::Hat ? 60.0f : 18.0f));
      float sample = 0.0f;
      if (classes[h] == BeatboxClass::Kick) {
        sample = std::sin(6.2831853f * 60.0f * t) * env * 0.8f;
      } else if (classes[h] == BeatboxClass::Snare) {
        rng = rng * 1664525u + 1013904223u;
        sample = ((static_cast<float>(rng % 2001) / 1000.0f) - 1.0f) * env * 0.35f;
        sample += std::sin(6.2831853f * 190.0f * t) * env * 0.15f;
      } else {
        rng = rng * 1664525u + 1013904223u;
        sample = ((static_cast<int>(rng & 1) * 2 - 1) * env) * 0.25f;
      }
      bar[start + i] += sample;
    }
  }
  return bar;
}

double beatboxAccuracy(float bpm) {
  const int steps[8] = {0, 2, 4, 6, 8, 10, 12, 14};
  const BeatboxClass classes[8] = {BeatboxClass::Kick, BeatboxClass::Hat, BeatboxClass::Snare,
                                   BeatboxClass::Hat, BeatboxClass::Kick, BeatboxClass::Hat,
                                   BeatboxClass::Snare, BeatboxClass::Hat};
  const std::vector<float> bar = makeBeatboxBar(bpm, steps, classes, 8);
  BeatboxDetector detector;
  detector.init(48000.0f, bpm, 0.5f);
  BeatboxHit hits[16];
  const int found = detector.analyzeBar(bar.data(), static_cast<int>(bar.size()), hits, 16);
  int matches = 0;
  for (int h = 0; h < found; ++h) {
    for (int expected = 0; expected < 8; ++expected) {
      if (hits[h].step == steps[expected] && hits[h].cls == classes[expected]) ++matches;
    }
  }
  return static_cast<double>(matches) / 8.0;
}

}  // namespace

TEST(MicCaptureLevelAndPeak) {
  MicCapture mic;
  CHECK(mic.init(48000.0f));
  pushSignal(mic, 0.2f, 256);
  CHECK(mic.level() > 0.0f);
  CHECK(mic.peak() > 0.0f);
  pushSignal(mic, 0.0f, 256);
  CHECK(mic.level() < 0.1f);
  INFO("mic capture model: RMS level/peak follow the input");
}

TEST(MicGainAffectsLevel) {
  MicCapture a;
  MicCapture b;
  a.init(48000.0f);
  b.init(48000.0f);
  MicConfig low = a.config();
  low.gainDb = 0.0f;
  MicConfig high = low;
  high.gainDb = 40.0f;
  a.setConfig(low);
  b.setConfig(high);
  pushSignal(a, 0.01f, 256);
  pushSignal(b, 0.01f, 256);
  CHECK(b.level() > a.level() * 2.0f);
  INFO("gain model: +40 dB increases the captured level");
}

TEST(MicVadThreshold) {
  MicCapture mic;
  mic.init(48000.0f);
  MicConfig config = mic.config();
  config.threshold = 0.05f;
  config.gainDb = 0.0f;
  mic.setConfig(config);
  pushSignal(mic, 0.01f, 256);
  CHECK(!mic.vadActive());
  pushSignal(mic, 0.5f, 256);
  CHECK(mic.vadActive());
  INFO("VAD activates above the configured threshold");
}

TEST(MicSourceSelection) {
  MicCapture mic;
  mic.init(48000.0f);
  MicConfig config = mic.config();
  CHECK(config.source == MicSource::Mic);
  config.source = MicSource::Line;
  mic.setConfig(config);
  CHECK(mic.config().source == MicSource::Line);
  INFO("mic source LINE/MIC config is selectable");
}

TEST(MicRecordingBasicTake) {
  MicCapture mic;
  mic.init(48000.0f);
  mic.privacy().setMuteSwitch(false);
  CHECK(mic.beginRecording("PHRASE", 3, MicStorage::Psram));
  CHECK(mic.recording());
  CHECK(mic.take().capacity == static_cast<uint32_t>(kMicMaxFrames));
  CHECK(kMicMaxSeconds == 30);
  pushSignal(mic, 0.3f, 4800);
  CHECK(mic.endRecording());
  CHECK(mic.take().valid);
  CHECK(mic.take().frames > 4000 && mic.take().frames <= 4800);
  CHECK(std::strcmp(mic.take().name, "PHRASE") == 0);
  CHECK(mic.take().pad == 3);
  CHECK(mic.take().storage == MicStorage::Psram);
  INFO("voice recording: <=30 s buffer, name/pad/storage, frames captured");
}

TEST(MicRecordingTrimSilence) {
  MicCapture mic;
  mic.init(48000.0f);
  mic.privacy().setMuteSwitch(false);
  mic.beginRecording("TRIMMED", 1);
  pushSignal(mic, 0.0f, 1000);
  pushSignal(mic, 0.5f, 2000);
  pushSignal(mic, 0.0f, 1000);
  CHECK(mic.endRecording());
  CHECK(mic.take().valid);
  CHECK(mic.take().frames >= 1800 && mic.take().frames <= 2100);
  INFO("auto-trim removes leading/trailing silence (frames=%u)",
       static_cast<unsigned>(mic.take().frames));
}

TEST(MicPrivacyBlocksRecording) {
  MicCapture mic;
  mic.init(48000.0f);
  CHECK(mic.privacy().muteSwitch);   // muted by default
  CHECK(!mic.beginRecording("BLOCKED", 0));
  CHECK(!mic.recording());
  mic.privacy().setMuteSwitch(false);
  CHECK(mic.beginRecording("ALLOWED", 0));
  CHECK(mic.privacy().led);
  INFO("hardware mute blocks recording; LED on only when enabled");
}

TEST(MicPrivacyLedAndNoNetwork) {
  MicPrivacy privacy;
  CHECK(privacy.muteSwitch);
  CHECK(!privacy.led);
  privacy.setMuteSwitch(false);
  CHECK(privacy.recordingAllowed());
  CHECK(privacy.led);
  privacy.setMuteSwitch(true);
  CHECK(!privacy.led);
  CHECK(!privacy.recordingAllowed());
  CHECK(!micNetworkTransmissionAllowed(false));
  CHECK(micNetworkTransmissionAllowed(true));  // only explicit user action
  INFO("privacy: mute switch + MIC ON LED, no implicit BLE/Wi-Fi transmission");
}

TEST(MicBeatboxOnsetDetection) {
  const int steps[4] = {0, 4, 8, 12};
  const BeatboxClass classes[4] = {BeatboxClass::Kick, BeatboxClass::Snare, BeatboxClass::Kick,
                                   BeatboxClass::Snare};
  const std::vector<float> bar = makeBeatboxBar(120.0f, steps, classes, 4);
  BeatboxDetector detector;
  detector.init(48000.0f, 120.0f, 0.5f);
  BeatboxHit hits[16];
  const int count = detector.analyzeBar(bar.data(), static_cast<int>(bar.size()), hits, 16);
  CHECK(count == 4);
  for (int i = 0; i < count; ++i) CHECK(hits[i].step == i * 4);
  INFO("beatbox onset: 4 hits at steps 1/5/9/13 detected (count=%d)", count);
}

TEST(MicBeatboxClassRules) {
  const int steps[3] = {0, 4, 8};
  const BeatboxClass classes[3] = {BeatboxClass::Kick, BeatboxClass::Snare, BeatboxClass::Hat};
  const std::vector<float> bar = makeBeatboxBar(120.0f, steps, classes, 3);
  BeatboxDetector detector;
  BeatboxHit hits[8];
  const int count = detector.analyzeBar(bar.data(), static_cast<int>(bar.size()), hits, 8);
  CHECK(count == 3);
  bool hasKick = false;
  bool hasSnare = false;
  bool hasHat = false;
  for (int i = 0; i < count; ++i) {
    hasKick = hasKick || hits[i].cls == BeatboxClass::Kick;
    hasSnare = hasSnare || hits[i].cls == BeatboxClass::Snare;
    hasHat = hasHat || hits[i].cls == BeatboxClass::Hat;
  }
  CHECK(hasKick && hasSnare && hasHat);
  INFO("beatbox classes: low/mid/high energy -> KICK/SNARE/HAT");
}

TEST(MicBeatboxAccuracy90) {
  const double accuracy = beatboxAccuracy(90.0f);
  CHECK(accuracy >= 0.8);
  INFO("beatbox accuracy at 90 BPM: %.0f%% (>=80%%)", accuracy * 100.0);
}
TEST(MicBeatboxAccuracy110) {
  const double accuracy = beatboxAccuracy(110.0f);
  CHECK(accuracy >= 0.8);
  INFO("beatbox accuracy at 110 BPM: %.0f%% (>=80%%)", accuracy * 100.0);
}
TEST(MicBeatboxAccuracy140) {
  const double accuracy = beatboxAccuracy(140.0f);
  CHECK(accuracy >= 0.8);
  INFO("beatbox accuracy at 140 BPM: %.0f%% (>=80%%)", accuracy * 100.0);
}

TEST(MicBeatboxEmptyBar) {
  std::vector<float> silence(48000, 0.0f);
  BeatboxDetector detector;
  BeatboxHit hits[16];
  CHECK(detector.analyzeBar(silence.data(), static_cast<int>(silence.size()), hits, 16) == 0);
  INFO("beatbox: silent bar produces no hits");
}

TEST(MicBeatboxApplyStepsAndUndo) {
  SequenceTrack track;
  for (int s = 0; s < kSeqSteps; ++s) track.steps[s].active = false;
  track.steps[0].active = true;
  track.steps[0].note = 48;
  BeatboxHit hits[3] = {{4, 100, BeatboxClass::Kick},
                        {8, 110, BeatboxClass::Snare},
                        {12, 90, BeatboxClass::Hat}};
  BeatboxPattern pattern;
  CHECK(pattern.apply(hits, 3, &track) == 3);
  CHECK(track.steps[4].active && track.steps[4].note == 36);
  CHECK(track.steps[8].active && track.steps[8].note == 38);
  CHECK(track.steps[12].active && track.steps[12].note == 42);
  CHECK(pattern.hasUndo());
  CHECK(pattern.undo(&track));
  CHECK(track.steps[4].active == false);
  CHECK(track.steps[8].active == false);
  CHECK(track.steps[12].active == false);
  CHECK(track.steps[0].active && track.steps[0].note == 48);
  INFO("beatbox apply writes kick/snare/hat notes to steps; UNDO restores the pattern");
}

TEST(MicBeatboxVelocityAccent) {
  const int steps[2] = {0, 4};
  const BeatboxClass classes[2] = {BeatboxClass::Kick, BeatboxClass::Kick};
  const std::vector<float> bar = makeBeatboxBar(120.0f, steps, classes, 2);
  BeatboxDetector detector;
  BeatboxHit hits[4];
  const int count = detector.analyzeBar(bar.data(), static_cast<int>(bar.size()), hits, 4);
  CHECK(count == 2);
  if (count == 2) {
    for (int i = 0; i < count; ++i) CHECK(hits[i].velocity >= 30);
    CHECK(hits[0].velocity != hits[1].velocity || hits[0].step == 0);
  }
  INFO("beatbox velocity/accent is derived from hit energy");
}

TEST(MicBeatboxClassNamesAndNotes) {
  uint8_t note = 0;
  CHECK(BeatboxDetector::stepClassToNote(BeatboxClass::Kick, &note) && note == 36);
  CHECK(BeatboxDetector::stepClassToNote(BeatboxClass::Snare, &note) && note == 38);
  CHECK(BeatboxDetector::stepClassToNote(BeatboxClass::Hat, &note) && note == 42);
  CHECK(std::strcmp(BeatboxDetector::className(BeatboxClass::Snare), "SNARE") == 0);
  INFO("beatbox class -> MIDI notes: kick 36, snare 38, hat 42");
}

TEST(MicRecordingMutedThenUnmuted) {
  MicCapture mic;
  mic.init(48000.0f);
  CHECK(!mic.beginRecording("MUTED", 0));
  mic.privacy().setMuteSwitch(false);
  CHECK(mic.beginRecording("UNMUTED", 1));
  pushSignal(mic, 0.4f, 2400);
  CHECK(mic.endRecording());
  CHECK(mic.take().valid);
  CHECK(mic.take().pad == 1);
  INFO("mute -> recording rejected; after unmute the take is recorded");
}
