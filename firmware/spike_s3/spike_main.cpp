// SPDX-License-Identifier: GPL-3.0-or-later
// S3 vertical-slice spike — devkit firmware (lite concept platform).
//
// One cooperative loop exercising every subsystem that matters for the lite
// SKU and for the P4 first SKU (same codecs/SD/USB/panel; display is SPI here):
//   * audio: PCM1808 in -> PCM5102A out loopback (I2S stub until the devkit
//     wiring is confirmed; the block timing/xrun metric is real),
//   * display: 800x480 SPI, full flush in 16-row bounce batches + dirty-rect
//     partial updates,
//   * SD: 1-bit SDMMC 4 KiB write+read roundtrip, latency metric,
//   * USB composite: TinyUSB UAC2+MIDI+HID+CDC counters (stub until esp_tinyusb
//     is configured),
//   * panel: I2C MCP23017 scan (0x20..0x23), latency/errors.
//
// Every second it prints one machine-readable SPIKE_METRIC line; at the end of
// the configured run it prints SPIKE_RESULT pass=0|1 reason=...
// Acceptance criteria: docs/36 §2 / docs/39.
#include <Arduino.h>
#include <SD_MMC.h>
#include <SPI.h>
#include <Wire.h>
#include <stdio.h>

#include "spike_config.h"
#include "spike_core.hpp"

// Optional hardware integrations: enable only after checking the devkit wiring
// and the arduino-esp32/IDF API version (see docs/39).
// #define BUKIFON_SPIKE_USE_I2S 1
// #define BUKIFON_SPIKE_TINYUSB 1

using namespace bukifon::spike;

namespace {

alignas(4) float g_inL[kAudioBlockFrames];
alignas(4) float g_inR[kAudioBlockFrames];
alignas(4) float g_outL[kAudioBlockFrames];
alignas(4) float g_outR[kAudioBlockFrames];
alignas(4) float g_ringStorage[256 * 2];
AudioRing g_audioRing;

uint16_t* g_fbMemory = nullptr;
Framebuffer565 g_fb;
uint16_t g_bounceMemory[kBounceRows * kDisplayWidth];
BounceBuffer g_bounce;

uint8_t g_usbRxStorage[kUsbRxBytes];
uint8_t g_usbTxStorage[kUsbTxBytes];
ByteRing g_usbRx;
ByteRing g_usbTx;

SpikeMetrics g_metrics;
DirtyTracker g_dirty;

bool g_displayReady = false;
bool g_sdReady = false;
bool g_panelReady = false;
bool g_usbReady = false;

uint32_t g_bootMs = 0;
uint32_t g_lastLogMs = 0;
uint32_t g_lastFullMs = 0;
uint32_t g_lastPartialMs = 0;
uint32_t g_lastSdMs = 0;
uint32_t g_lastPanelMs = 0;
uint32_t g_windowStartMs = 0;
uint32_t g_windowFullFrames = 0;
uint32_t g_windowPartialUpdates = 0;
bool g_finished = false;

uint32_t g_totalSeconds() {
  return static_cast<uint32_t>(BUKIFON_SPIKE_AUDIO_SECONDS) +
         static_cast<uint32_t>(BUKIFON_SPIKE_DISPLAY_SECONDS) +
         static_cast<uint32_t>(BUKIFON_SPIKE_USB_SECONDS);
}

void displayBegin() {
  pinMode(kLcdCs, OUTPUT);
  pinMode(kLcdDc, OUTPUT);
  pinMode(kLcdRst, OUTPUT);
  pinMode(kBlPwm, OUTPUT);
  digitalWrite(kLcdCs, HIGH);
  digitalWrite(kLcdDc, HIGH);
  digitalWrite(kLcdRst, HIGH);
  analogWrite(kBlPwm, 0);
  SPI.begin(kLcdSck, -1, kLcdMosi, -1);
  // TODO(hw): panel controller init (ST7796/ILI9488 command sequence), MADCTL,
  // gamma; the SPI data path itself is what this spike times.
  g_displayReady = true;
}

// Stages `rows` framebuffer rows into the bounce buffer and clocks them out over
// SPI2.  Returns microseconds spent in the SPI transfer.
uint32_t flushRows(int startRow, int rows) {
  if (!g_fb.pixels || !g_displayReady) return 0;
  const int staged = g_bounce.stageRows(g_fb.pixels, g_fb.width, startRow, rows);
  if (staged <= 0) return 0;
  digitalWrite(kLcdDc, HIGH);
  digitalWrite(kLcdCs, LOW);
  const uint32_t start = micros();
  SPI.beginTransaction(SPISettings(kLcdSpiHz, MSBFIRST, SPI_MODE0));
  SPI.transfer(reinterpret_cast<uint8_t*>(g_bounce.data()),
               static_cast<uint32_t>(staged) * g_fb.width * 2u);
  SPI.endTransaction();
  const uint32_t elapsed = micros() - start;
  digitalWrite(kLcdCs, HIGH);
  return elapsed;
}

void audioBegin() {
  g_audioRing.init(g_ringStorage, 256, 2);
#if defined(BUKIFON_SPIKE_USE_I2S)
  // TODO(hw): i2s_driver_install for I2S0 (MCLK 12.288 MHz, BCK 3.072 MHz,
  // 48 kHz, 2x stereo) with PCM5102A out / PCM1808 in; replace the synthetic
  // input below with i2s_channel_read/write.
#endif
}

// Runs one 64-frame loopback block.  Returns the block time in microseconds.
uint32_t audioBlock() {
  const uint32_t start = micros();
  for (uint32_t f = 0; f < kAudioBlockFrames; ++f) {
    const float tone = std::sin(6.2831853f * 440.0f *
                                static_cast<float>((f + micros()) % 1000) / kAudioSampleRate);
    g_inL[f] = tone * 0.2f;
    g_inR[f] = -tone * 0.2f;
  }
  g_audioRing.push(g_inL, kAudioBlockFrames);
  // pop stereo input into the output (PCM1808 -> PCM5102A loopback model)
  static float frame[2];
  for (uint32_t f = 0; f < kAudioBlockFrames; ++f) {
    g_audioRing.pop(frame, 1);
    g_outL[f] = frame[0];
    g_outR[f] = frame[1];
  }
  // TODO(hw): i2s_channel_write(g_out) + i2s_channel_read(g_in) once enabled.
  return micros() - start;
}

void sdBegin() {
  SD_MMC.setPins(kSdClk, kSdCmd, kSdD0);
  g_sdReady = SD_MMC.begin("/sdcard", true, false, 20000);
  if (!g_sdReady) {
    ++g_metrics.sdErrors;  // protocol expects a card; log makes it visible
  }
}

void sdBenchmark() {
  if (!g_sdReady) {
    ++g_metrics.sdErrors;
    return;
  }
  static uint8_t buffer[kSdBenchBytes];
  for (uint32_t i = 0; i < kSdBenchBytes; ++i) buffer[i] = static_cast<uint8_t>(i * 31u);
  const uint32_t start = micros();
  File file = SD_MMC.open("/spike.bin", FILE_WRITE);
  bool ok = false;
  if (file) {
    ok = file.write(buffer, kSdBenchBytes) == kSdBenchBytes;
    file.close();
  }
  if (ok) {
    file = SD_MMC.open("/spike.bin", FILE_READ);
    if (file) {
      ok = file.read(buffer, kSdBenchBytes) == kSdBenchBytes;
      file.close();
    } else {
      ok = false;
    }
  }
  const uint32_t elapsed = micros() - start;
  g_metrics.sdLatencyUs.add(static_cast<double>(elapsed), kSdLatencyBudgetUs);
  if (!ok) ++g_metrics.sdErrors;
}

void panelBegin() {
  Wire.begin(kI2cSda, kI2cScl, kI2cHz);
  g_panelReady = true;
}

void panelScan() {
  if (!g_panelReady) return;
  const uint32_t start = micros();
  bool any = false;
  for (uint8_t address = 0x20; address <= 0x23; ++address) {
    Wire.beginTransmission(address);
    Wire.write(0x12);  // MCP23017 GPIOA
    const bool ack = Wire.endTransmission(false) == 0;
    if (!ack) continue;
    if (Wire.requestFrom(address, static_cast<uint8_t>(2)) == 2) {
      (void)Wire.read();
      (void)Wire.read();
      any = true;
    }
  }
  const uint32_t elapsed = micros() - start;
  g_metrics.panelScanUs.add(static_cast<double>(elapsed));
  ++g_metrics.panelErrors;  // no expander on the bare devkit: visible in the log
  if (any) --g_metrics.panelErrors;
}

void usbBegin() {
  // TODO(hw): esp_tinyusb composite configuration: UAC2 stereo 24/48 + MIDI +
  // HID keyboard + CDC; 4 KiB RX/TX FIFOs in internal SRAM.  Until then the
  // rings are exercised and drops are counted but always zero.
  g_usbRx.init(g_usbRxStorage, kUsbRxBytes);
  g_usbTx.init(g_usbTxStorage, kUsbTxBytes);
  g_usbReady = false;
}

void usbPoll() {
  uint8_t dummy[64];
  for (uint32_t i = 0; i < sizeof(dummy); ++i) dummy[i] = static_cast<uint8_t>(i);
  g_usbRx.push(dummy, sizeof(dummy));
  g_usbTx.push(dummy, sizeof(dummy));
  uint8_t sink[64];
  g_usbTx.pop(sink, sizeof(sink));
  g_usbRx.pop(sink, sizeof(sink));
  g_metrics.usbDrops = g_usbRx.drops() + g_usbTx.drops();
  // TODO(hw): count TinyUSB UAC2/MIDI/HID/CDC drops and reconnects.
}

void updateDisplayRates(uint32_t nowMs) {
  const uint32_t windowMs = nowMs - g_windowStartMs;
  if (windowMs < 1000) return;
  const double seconds = static_cast<double>(windowMs) / 1000.0;
  g_metrics.fullFps = static_cast<double>(g_metrics.fullFrames - g_windowFullFrames) / seconds;
  g_metrics.partialUpdatesPerSec =
      static_cast<double>(g_metrics.partialUpdates - g_windowPartialUpdates) / seconds;
  g_windowStartMs = nowMs;
  g_windowFullFrames = static_cast<uint32_t>(g_metrics.fullFrames);
  g_windowPartialUpdates = static_cast<uint32_t>(g_metrics.partialUpdates);
}

void printMetrics() {
  char line[512];
  if (g_metrics.logLine(line, sizeof(line))) {
    Serial.printf("%s\n", line);
  }
  char reason[96];
  const bool ok = g_metrics.pass(reason, sizeof(reason));
  Serial.printf("SPIKE_STATUS pass=%d reason=%s free_heap=%u\n", ok ? 1 : 0, reason,
                static_cast<unsigned>(ESP.getFreeHeap()));
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println();
  Serial.println("Bukifon S3 vertical-slice spike (lite concept; P4 is primary SKU)");
  g_bootMs = millis();
  g_windowStartMs = g_bootMs;
  g_lastLogMs = g_bootMs;
  g_lastFullMs = g_bootMs;
  g_lastPartialMs = g_bootMs;
  g_lastSdMs = g_bootMs;
  g_lastPanelMs = g_bootMs;

  g_metrics.reset();
  g_fbMemory = static_cast<uint16_t*>(ps_malloc(static_cast<size_t>(kDisplayWidth) *
                                                kDisplayHeight * 2u));
  if (!g_fbMemory) {
    Serial.println("SPIKE_WARN psram framebuffer allocation failed; using internal RAM");
    g_fbMemory = static_cast<uint16_t*>(malloc(static_cast<size_t>(kDisplayWidth) *
                                               kDisplayHeight * 2u));
  }
  if (g_fbMemory) {
    g_fb.attach(g_fbMemory, kDisplayWidth, kDisplayHeight);
    g_fb.clear(0x0000);
  }
  g_bounce.init(g_bounceMemory, kDisplayWidth, kBounceRows);
  displayBegin();
  audioBegin();
  sdBegin();
  panelBegin();
  usbBegin();
  Serial.printf("SPIKE_CONFIG platform=s3-lite cpu=%u psram=%u lcd=%dx%d bounce_rows=%d "
                "usb_rx=%u usb_tx=%u pins=%d\n",
                static_cast<unsigned>(kCpuMhz), static_cast<unsigned>(kPsramMhz), kDisplayWidth,
                kDisplayHeight, kBounceRows,
                static_cast<unsigned>(kUsbRxBytes), static_cast<unsigned>(kUsbTxBytes),
                kPinCount);
  Serial.printf("SPIKE_PINS lcd_sck=%d lcd_mosi=%d lcd_cs=%d lcd_dc=%d lcd_rst=%d bl=%d "
                "sd_clk=%d sd_cmd=%d sd_d0=%d i2c_sda=%d i2c_scl=%d i2s_mclk=%d i2s_bck=%d "
                "i2s_lrck=%d dac_din=%d adc_dout=%d midi_tx=%d midi_rx=%d panel_irq=%d "
                "gate1=%d pwr_good=%d\n",
                kLcdSck, kLcdMosi, kLcdCs, kLcdDc, kLcdRst, kBlPwm, kSdClk, kSdCmd, kSdD0,
                kI2cSda, kI2cScl, kI2sMclk, kI2sBck, kI2sLrck, kI2sDacDin, kI2sAdcDout,
                kMidiTx, kMidiRx, kPanelIrq, kGate1, kPwrGood);
  Serial.printf("SPIKE_READY display=%d sd=%d panel=%d usb=%d\n", g_displayReady ? 1 : 0,
                g_sdReady ? 1 : 0, g_panelReady ? 1 : 0, g_usbReady ? 1 : 0);
}

void loop() {
  if (g_finished) return;
  const uint32_t now = millis();

  // --- audio block (one per loop) -----------------------------------------
  const uint32_t blockUs = audioBlock();
  g_metrics.blockUs.add(static_cast<double>(blockUs), kAudioBudgetUs);
  if (blockUs > kAudioDeadlineUs) ++g_metrics.xruns;

  // --- display: full flush every ~66 ms, dirty partial every ~10 ms --------
  if (now - g_lastFullMs >= 66) {
    g_lastFullMs = now;
    g_fb.fillRect(0, 0, kDisplayWidth, 2, 0xFFFF);
    uint32_t fullUs = 0;
    for (int row = 0; row < kDisplayHeight; row += kBounceRows) {
      fullUs += flushRows(row, kBounceRows);
    }
    g_metrics.fullFrameUs.add(static_cast<double>(fullUs));
    ++g_metrics.fullFrames;
  }
  if (now - g_lastPartialMs >= 10) {
    g_lastPartialMs = now;
    g_dirty.reset();
    g_dirty.add(10, 300, 300, 40);
    g_fb.fillRect(10, 300, 300, 40, 0x07E0);
    uint32_t partialUs = 0;
    for (int r = 0; r < g_dirty.count(); ++r) {
      const DirtyRect& rect = g_dirty.rect(r);
      const int rows = (rect.h + kBounceRows - 1) / kBounceRows;
      for (int b = 0; b < rows; ++b) {
        partialUs += flushRows(rect.y + b * kBounceRows, kBounceRows);
      }
    }
    g_metrics.partialFrameUs.add(static_cast<double>(partialUs));
    ++g_metrics.partialUpdates;
  }

  // --- SD roundtrip every 5 s ---------------------------------------------
  if (now - g_lastSdMs >= 5000) {
    g_lastSdMs = now;
    sdBenchmark();
  }

  // --- panel scan every 10 ms ---------------------------------------------
  if (now - g_lastPanelMs >= kPanelPollMs) {
    g_lastPanelMs = now;
    panelScan();
  }

  usbPoll();
  updateDisplayRates(now);

  if (now - g_lastLogMs >= 1000) {
    g_lastLogMs = now;
    g_metrics.heapFree = ESP.getFreeHeap();
    g_metrics.psramFree = ESP.getFreePsram();
    printMetrics();
  }

  const uint32_t totalSeconds = g_totalSeconds();
  if (totalSeconds > 0 && (now - g_bootMs) / 1000 >= totalSeconds) {
    char reason[96];
    const bool ok = g_metrics.pass(reason, sizeof(reason));
    Serial.printf("SPIKE_RESULT pass=%d reason=%s duration_s=%u audio_blocks=%llu "
                  "full_fps=%.2f partial_per_s=%.2f xruns=%llu\n",
                  ok ? 1 : 0, reason, static_cast<unsigned>((now - g_bootMs) / 1000),
                  static_cast<unsigned long long>(g_metrics.blockUs.count), g_metrics.fullFps,
                  g_metrics.partialUpdatesPerSec,
                  static_cast<unsigned long long>(g_metrics.xruns));
    g_finished = true;
  }
}
