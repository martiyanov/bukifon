// SPDX-License-Identifier: GPL-3.0-or-later
#include <cmath>
#include <cstring>
#include <vector>

#include "io/cv.hpp"
#include "io/deck.hpp"
#include "io/encoder.hpp"
#include "io/leds.hpp"
#include "test_framework.hpp"

using namespace bukifon;

namespace {

// Fake MCP23017 + MCP3208 deck hardware: a simple 18/42-button matrix.
class FakeDeckIo : public IDeckIo {
 public:
  void writePort(uint8_t port, uint8_t value) override {
    if (port == 0) rowDrive_ = value;
  }
  uint8_t readPort(uint8_t port) override {
    if (port != 1) return 0xFF;
    // Buttons are active low: return 0 bits for pressed keys in the active row.
    uint8_t result = 0xFF;
    const uint8_t activeRow = static_cast<uint8_t>(~rowDrive_ & 0xFF);
    for (int row = 0; row < 8; ++row) {
      if ((activeRow & (1u << row)) == 0) continue;
      for (int col = 0; col < 8; ++col) {
        if (pressed_[row][col]) result &= static_cast<uint8_t>(~(1u << col));
      }
    }
    return result;
  }
  uint16_t readAdc(uint8_t channel) override { return channel == 6 ? fsr_ : 0; }

  void setPressed(int row, int col, bool value) {
    if (row >= 0 && row < 8 && col >= 0 && col < 8) pressed_[row][col] = value;
  }
  uint16_t fsr_ = 0;

 private:
  uint8_t rowDrive_ = 0xFF;
  bool pressed_[8][8] = {};
};

class RecordingDeckSink : public DeckSink {
 public:
  void onPad(uint8_t index, uint8_t velocity, bool pressed) override {
    padEvents.push_back({index, velocity, pressed});
  }
  void onKey(uint8_t index, uint8_t velocity, bool pressed) override {
    keyEvents.push_back({index, velocity, pressed});
  }
  struct Ev {
    uint8_t index, velocity;
    bool pressed;
  };
  std::vector<Ev> padEvents, keyEvents;
};

}  // namespace

TEST(EncoderQuadratureAndAcceleration) {
  Encoder enc;
  enc.init(true);
  // One full detent: 00 -> 01 -> 11 -> 10 -> 00 (standard EC11 sequence).
  const uint8_t seq[] = {0b00, 0b01, 0b11, 0b10, 0b00};
  uint32_t t = 1000000;
  for (uint8_t s : seq) enc.feed(s, t += 100000);
  CHECK(enc.takeDelta() == 1);
  // Two detents in quick succession: acceleration kicks in.
  for (int i = 0; i < 2; ++i) {
    for (uint8_t s : seq) enc.feed(s, t += 5000);
  }
  const int fast = enc.takeDelta();
  INFO("encoder: slow delta=1, fast delta=%d (acceleration)", fast);
  CHECK(fast >= 4);
  // Reverse direction.
  const uint8_t rev[] = {0b00, 0b10, 0b11, 0b01, 0b00};
  for (uint8_t s : rev) enc.feed(s, t += 100000);
  CHECK(enc.takeDelta() == -1);
}

TEST(DeckPadScanAndDebounce) {
  FakeDeckIo io;
  RecordingDeckSink sink;
  DeckScanner scanner;
  scanner.init(DeckType::Pad, &io, &sink);
  CHECK(scanner.ledCount() == kPadLeds);
  CHECK(scanner.buttonCount() == kNumPads);
  io.setPressed(0, 3, true);  // PAD4 (row 0, col 3)
  uint32_t now = 1000000;
  scanner.poll(now);
  scanner.poll(now + 1000);
  CHECK(sink.padEvents.empty());  // inside 5 ms debounce window
  scanner.poll(now + 6000);
  CHECK(sink.padEvents.size() == 1);
  CHECK(sink.padEvents[0].index == 3);
  CHECK(sink.padEvents[0].pressed);
  // Release debounce (3 ms for keys, 5 ms for pads).
  io.setPressed(0, 3, false);
  scanner.poll(now + 7000);
  scanner.poll(now + 14000);
  CHECK(sink.padEvents.size() == 2);
  CHECK(!sink.padEvents[1].pressed);
  INFO("deck pad: %zu events after press+release, index=%d", sink.padEvents.size(),
       sink.padEvents[0].index);
}

TEST(DeckKeysScanAndVelocity) {
  FakeDeckIo io;
  RecordingDeckSink sink;
  DeckScanner scanner;
  scanner.init(DeckType::Keys, &io, &sink);
  CHECK(scanner.ledCount() == kKeyLeds);
  CHECK(scanner.buttonCount() == kNumKeys);
  io.setPressed(2, 4, true);  // key index 2*7+4 = 18
  const uint32_t now = 2000000;
  scanner.poll(now);
  scanner.poll(now + 5000);
  CHECK(sink.keyEvents.size() == 1);
  CHECK(sink.keyEvents[0].index == 18);
  CHECK(sink.keyEvents[0].velocity == 127);
  INFO("deck keys: key index=%d velocity=%d", sink.keyEvents[0].index,
       sink.keyEvents[0].velocity);

  // FSR velocity on the pad deck.
  FakeDeckIo io2;
  RecordingDeckSink sink2;
  DeckScanner pad;
  pad.init(DeckType::Pad, &io2, &sink2);
  pad.setFsrEnabled(true);
  io2.fsr_ = 100;
  pad.poll(now);
  io2.setPressed(1, 1, true);
  io2.fsr_ = 3000;
  pad.poll(now + 1000);
  pad.poll(now + 10000);
  CHECK(sink2.padEvents.size() == 1);
  INFO("FSR velocity: %d (baseline 100, force 3000)", sink2.padEvents[0].velocity);
  CHECK(sink2.padEvents[0].velocity > 20);
  CHECK(sink2.padEvents[0].velocity <= 127);
}

TEST(DeckDetectionAndKeyMapping) {
  CHECK(DeckDetector::typeFromVolts(0.3f) == DeckType::Pad);
  CHECK(DeckDetector::typeFromVolts(3.0f) == DeckType::Keys);
  CHECK(DeckDetector::typeFromVolts(1.5f) == DeckType::None);
  CHECK(DeckDetector::ledCount(DeckType::Pad) == 27);
  CHECK(DeckDetector::ledCount(DeckType::Keys) == 51);
  CHECK(DeckDetector::typeFromAdc(0) == DeckType::Pad);
  CHECK(DeckDetector::typeFromAdc(2048) == DeckType::None);
  CHECK(KeyboardMapper::keyToNote(0) == 48);                 // chromatic from C3
  CHECK(KeyboardMapper::keyToNote(41) == 89);
  CHECK(KeyboardMapper::keyToNote(0, 0, 1) == 60);           // octave shift
  CHECK(KeyboardMapper::noteToKey(60) == 12);
  // Isomorphic layout must produce distinct notes and stay in a sane range.
  int distinct = 0;
  int used[128] = {};
  for (int k = 0; k < kNumKeys; ++k) {
    const int n = KeyboardMapper::keyToNote(k, 1);
    CHECK(n >= 36 && n <= 96);
    if (!used[n]) ++distinct;
    used[n] = 1;
  }
  INFO("deck detection: PAD=27 LEDs, KEYS=51 LEDs; chromatic key0=C3; iso distinct=%d", distinct);
  CHECK(distinct > 20);
  CHECK(FsrVelocity::fromForceDelta(100, 3000) > 40);
  CHECK(FsrVelocity::fromForceDelta(100, 50) == 1);
}

TEST(CvCalibrationAndInput) {
  CvCalibration cal;
  cal.reset();
  const uint16_t code5 = cal.codeForVolts(0, 5.0f);
  const float volts5 = cal.voltsForCode(0, code5);
  INFO("CV calibration: 5.000 V -> code %u -> %.4f V", code5, volts5);
  CHECK(std::abs(static_cast<int>(code5) - 2048) <= 4);
  CHECK(std::fabs(volts5 - 5.0f) < 0.01f);
  // 4-point calibration with deliberately non-linear points.
  cal.setPoint(0, 0, 0.0f, 10);
  cal.setPoint(0, 1, 2.5f, 1000);
  cal.setPoint(0, 2, 5.0f, 2050);
  cal.setPoint(0, 3, 10.0f, 4095);
  const float v = cal.voltsForCode(0, 2050);
  CHECK(std::fabs(v - 5.0f) < 0.01f);
  const uint16_t c = cal.codeForVolts(0, 2.5f);
  CHECK(std::abs(static_cast<int>(c) - 1000) <= 1);
  // Serialisation roundtrip.
  uint8_t buffer[CvCalibration::kSerializedBytes];
  const size_t n = cal.serialize(buffer, sizeof(buffer));
  CHECK(n == CvCalibration::kSerializedBytes);
  CvCalibration restored;
  CHECK(restored.deserialize(buffer, n));
  CHECK(std::fabs(restored.voltsForCode(0, 2050) - 5.0f) < 0.01f);
  buffer[5] ^= 0xFF;
  CHECK(!restored.deserialize(buffer, n));  // CRC catches corruption

  CvInput input;
  input.init(48000.0f);
  float volts = 0.0f;
  for (int i = 0; i < 4800; ++i) volts = input.update(4095);
  INFO("CV input: 4095 raw -> %.3f V after filter", volts);
  CHECK(std::fabs(volts - 10.0f) < 0.05f);
  CHECK(CvInput::semitonesFromVolts(0.08333f) == 1);
  CHECK(std::fabs(CvInput::quantize1VOct(0.09f) - 0.08333f) < 1e-4f);
}

TEST(LedChainFrame) {
  LedChain chain;
  chain.setLength(27);
  CHECK(chain.length() == 27);
  chain.clear();
  chain.set(0, Rgb{10, 20, 30});
  CHECK(chain.get(0).r == 10 && chain.get(0).g == 20 && chain.get(0).b == 30);
  chain.set(100, Rgb{255, 0, 0});  // out of range ignored
  CHECK(chain.get(100).r == 0);
  CHECK(LedChain::byteCount(27) == 81);
  const Rgb red = LedChain::hsv(0.0f, 1.0f, 1.0f);
  const Rgb green = LedChain::hsv(1.0f / 3.0f, 1.0f, 1.0f);
  const Rgb blue = LedChain::hsv(2.0f / 3.0f, 1.0f, 1.0f);
  CHECK(red.r > 240 && red.g < 10 && red.b < 10);
  CHECK(green.g > 240);
  CHECK(blue.b > 240);
  LedState state;
  for (int i = 0; i < kNumEncoders; ++i) state.encoderValue[i] = static_cast<float>(i) / 7.0f;
  state.activeStep = 3;
  state.playing = true;
  state.masterLevel = 0.5f;
  buildLedFrame(state, DeckType::Pad, &chain);
  CHECK(chain.length() == 27);
  CHECK(chain.get(8).g > 0);  // playing status is green
  buildLedFrame(state, DeckType::Keys, &chain);
  CHECK(chain.length() == 51);
  CHECK(LedChain::levelColor(0.0f).g > 200);
  CHECK(LedChain::levelColor(1.0f).r > 200);
  INFO("LED chain: panel+pad=27, panel+keys=51, byte counts %d/%d", LedChain::byteCount(27),
       LedChain::byteCount(51));
}
