// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon firmware — Arduino sketch for Raspberry Pi Pico (arduino-pico core).
//
// Core0: UI, encoders, deck, screen, MIDI, CV logic, sequencer.
// Core1: audio engine (portable src/audio + src/dsp), I2S DMA to PCM5102A.
//
// Hardware pin map: src/hal/pinmap.hpp (GATE1=GP22, GATE2=GP26, DECK_ID=GP27,
// DECK_INT=GP28 per the latest contract update).
//
// HARDWARE STATUS: the audio DSP core is fully host-tested (see tests/), the
// drivers below are written against the datasheets/spec but not verified on a
// physical board in this environment (marked TODO(hw) where relevant).

#include <Arduino.h>
#include <LittleFS.h>
#include <SPI.h>
#include <Wire.h>

#include "audio/engine.hpp"
#include "core/patch.hpp"
#include "hal/hc165.hpp"
#include "hal/i2s_pio.hpp"
#include "hal/mcp23017.hpp"
#include "hal/mcp3208.hpp"
#include "hal/mcp4728.hpp"
#include "hal/midi_uart.hpp"
#include "hal/pinmap.hpp"
#include "hal/st7789.hpp"
#include "hal/ws2812.hpp"
#include "io/cv.hpp"
#include "io/deck.hpp"
#include "io/encoder.hpp"
#include "io/leds.hpp"
#include "io/midi_parser.hpp"
#include "io/midi_router.hpp"
#include "io/sequencer.hpp"
#include "storage/eeprom.hpp"
#include "storage/preset_store.hpp"
#include "ui/canvas.hpp"
#include "ui/menu.hpp"

using namespace bukifon;

// --- hardware ---------------------------------------------------------------
hal::I2sPio g_i2s;
hal::Mcp4728 g_dac;
hal::Mcp3208 g_adc;
hal::Hc165Chain g_shift;
hal::Mcp23017 g_expander;
hal::Ws2812Chain g_leds;
hal::St7789 g_lcd;
hal::MidiIo g_midi;
hal::Mcp23017* g_deckIo = &g_expander;

// --- portable firmware ------------------------------------------------------
Engine g_engine;
MidiParser g_parser;
MidiRouter g_router;
Sequencer g_seq;
MenuModel g_menu;
DeckScanner g_deck;
Encoder g_encoders[kNumEncoders];
CvCalibration g_cvCal;
CvInput g_cvIn[kNumCvIn];
PresetStore g_presets;
EepromStore g_eeprom;

DeckSink* g_deckSink = nullptr;
uint32_t g_lastControlUs = 0;
uint32_t g_lastDrawUs = 0;
bool g_deckReady = false;

static constexpr uint32_t kMidBlock = 128;  // audio block (<= kBlockSize)
static int16_t g_audioI16[kBlockSize * 2];
static float g_audioL[kBlockSize];
static float g_audioR[kBlockSize];

// Minimal deck sink: maps deck buttons to engine notes / sequencer steps.
class DeckNoteSink : public DeckSink {
 public:
  void onPad(uint8_t index, uint8_t velocity, bool pressed) override {
    if (pressed) {
      g_engine.noteOn(48 + index, velocity, 0, 0);
    } else {
      g_engine.noteOff(48 + index, 0);
    }
  }
  void onKey(uint8_t index, uint8_t velocity, bool pressed) override {
    const int note = KeyboardMapper::keyToNote(index, 0, 0);
    if (pressed) {
      g_engine.noteOn(note, velocity, 0, 0);
    } else {
      g_engine.noteOff(note, 0);
    }
  }
};
static DeckNoteSink g_deckSinkImpl;

void setup() {
  Serial.begin(115200);
  Serial.println("Bukifon boot");

  Wire.begin();
  Wire.setClock(hal::pins::kI2cClockHz);
  g_dac.begin();
  g_adc.begin();
  g_shift.begin();
  g_expander.begin();
  g_leds.begin();
  g_leds.setLength(DeckDetector::ledCount(DeckType::Pad));
  g_lcd.begin();
  g_lcd.setBacklight(200);
  g_midi.begin(&g_parser);

  g_router.setEngine(&g_engine);
  g_parser.setSink(&g_router);
  g_engine.init();
  g_engine.loadFactoryPatch(0);
  g_seq.init();
  g_seq.setBpm(g_engine.globals().v[Bpm]);
  g_seq.setPlaying(false);
  g_engine.setSequencer(&g_seq);

  g_menu.init(&g_engine);
  g_deckSink = &g_deckSinkImpl;
  g_cvCal.reset();

  // Deck type auto-detection from DECK_ID (GP27, ADC1).
  pinMode(hal::pins::kDeckId, INPUT);
  const uint16_t deckRaw = analogRead(hal::pins::kDeckId);
  const DeckType deckType = DeckDetector::typeFromAdc(deckRaw);
  g_deck.init(deckType == DeckType::None ? DeckType::Pad : deckType, g_deckIo, g_deckSink);
  g_leds.setLength(DeckDetector::ledCount(deckType));
  g_deckReady = true;

  g_i2s.begin(48000);
  Serial.print("audio started: ");
  Serial.println(g_i2s.started() ? "yes" : "no");
}

// Core1: audio rendering, I2S DMA double-buffer (2 x 256 frames).
void setup1() {}

void loop1() {
  const int n = kMidBlock;
  g_engine.process(g_audioL, g_audioR, n);
  for (int i = 0; i < n; ++i) {
    g_audioI16[i * 2 + 0] = g_engine.dither().toPcm16(g_audioL[i]);
    g_audioI16[i * 2 + 1] = g_engine.dither().toPcm16(g_audioR[i]);
  }
  g_i2s.writeFrames(g_audioI16, static_cast<size_t>(n));
}

// Control tick (~1 kHz on core0).
void controlTick(uint32_t nowUs) {
  g_midi.poll();
  g_parser.setSink(&g_router);

  // 74HC165: encoders + buttons.
  uint64_t shift = 0;
  if (g_shift.read(&shift)) {
    for (int e = 0; e < kNumEncoders; ++e) {
      const uint8_t ab = static_cast<uint8_t>((shift >> (e * 2)) & 0x3);
      const int delta = g_encoders[e].feed(ab, nowUs);
      if (delta != 0) {
        const int applied = g_menu.encoderDelta(e, delta);
        g_engine.setGlobalParam(MasterVolume, g_engine.globals().v[MasterVolume]);
        (void)applied;
      }
      const bool push = g_shift.encoderPressed(e);
      if (push) g_menu.encoderPush(e);
    }
    // Shoulder buttons: L1/L2 = octave, R1 = SHIFT, R2 = PLAY/STOP.
    g_menu.setShift(g_shift.shoulder(2));
    if (g_shift.shoulder(3)) {
      g_seq.setPlaying(!g_seq.playing());
      g_engine.setTransport(g_seq.playing());
    }
  }

  // Deck matrix.
  g_deck.poll(nowUs);

  // CV inputs (100 Hz filtered by CvInput).
  for (int c = 0; c < kNumCvIn; ++c) {
    const uint16_t raw = g_adc.read(static_cast<uint8_t>(2 + c));
    g_engine.setCv(c, g_cvIn[c].update(raw));
  }
  const uint16_t sl1 = g_adc.readSlider(0);
  const uint16_t sl2 = g_adc.readSlider(1);
  g_engine.setPartParam(0, Cutoff, 20.0f * powf(1000.0f, static_cast<float>(sl1) / 4095.0f));
  g_engine.setGlobalParam(MasterVolume, static_cast<float>(sl2) / 4095.0f);

  // CV outputs (MCP4728, 1 kHz) — run the sequencer clock.
  g_seq.setBpm(g_engine.globals().v[Bpm]);
  uint16_t codes[kNumCvOut] = {
      g_cvCal.codeForVolts(0, 5.0f), g_cvCal.codeForVolts(1, 5.0f),
      g_cvCal.codeForVolts(2, 0.0f), g_cvCal.codeForVolts(3, 0.0f)};
  g_dac.updateAll(codes);

  // Drain telemetry into the UI state.
  Telemetry telemetry;
  if (g_engine.popTelemetry(&telemetry)) {
    g_lcd.setBacklight(120 + static_cast<uint8_t>(telemetry.peak * 120.0f));
  }
}

void loop() {
  const uint32_t nowUs = micros();
  if (nowUs - g_lastControlUs >= 1000) {  // ~1 kHz
    g_lastControlUs = nowUs;
    controlTick(nowUs);
  }
  if (nowUs - g_lastDrawUs >= 50000) {  // 20 fps UI refresh
    g_lastDrawUs = nowUs;
    g_menu.draw(g_lcd);
    LedState ledState;
    for (int e = 0; e < kNumEncoders; ++e) {
      ledState.encoderValue[e] = 0.5f;
    }
    ledState.activeStep = g_seq.currentStep(0);
    ledState.playing = g_seq.playing();
    ledState.shift = g_menu.shift();
    ledState.masterLevel = g_engine.lastTelemetry().peak;
    buildLedFrame(ledState, g_deck.type(), &g_leds);
    g_leds.show();
  }
  // Keep the event queue fed from the parser (MIDI arrives asynchronously).
  g_parser.setSink(&g_router);
}
