// SPDX-License-Identifier: GPL-3.0-or-later
// Host tests for the S3 (lite) vertical-slice spike: buffers, pin-map parser,
// metrics, log parser and the host simulation pass/fail logic.
#include <cstdio>
#include <cstring>

#include "../spike_s3/spike_core.hpp"
#include "test_framework.hpp"

using namespace bukifon::spike;

namespace {

const char* kTestCsv =
    "signal;gpio;peripheral;direction;note\n"
    "LCD_SCK;12;SPI2 FSPICLK;out;\n"
    "LCD_MOSI;11;SPI2 FSPID;out;\n"
    "LCD_CS;10;SPI2 FSPICS0;out;\n"
    "LCD_DC;9;GPIO;out;\n"
    "LCD_RST;8;GPIO;out;\n"
    "BL_PWM;21;LEDC PWM;out;\n"
    "SPI3_SCK;4;SPI3 SCK;out;\n"
    "SPI3_MOSI;5;SPI3 MOSI;out;\n"
    "SPI3_MISO;6;SPI3 MISO;in;\n"
    "MCP3208_CS;7;SPI3 CS0;out;\n"
    "SD_CLK;15;SDMMC CLK;out;\n"
    "SD_CMD;14;SDMMC CMD;bidir;\n"
    "SD_D0;13;SDMMC D0;bidir;\n"
    "I2C0_SDA;16;I2C0 SDA;bidir;\n"
    "I2C0_SCL;17;I2C0 SCL;out;\n"
    "I2S_MCLK;18;I2S0 MCLK;out;\n"
    "I2S_BCK;1;I2S0 BCK;out;\n"
    "I2S_LRCK;2;I2S0 WS;out;\n"
    "I2S_DAC_DIN;38;I2S0 SD_OUT;out;\n"
    "I2S_ADC_DOUT;39;I2S0 SD_IN;in;\n"
    "MIDI_TX;40;UART1 TX;out;\n"
    "MIDI_RX;41;UART1 RX;in;\n"
    "LED_DATA;42;RMT;out;\n"
    "PANEL_IRQ;47;GPIO in;in;\n"
    "GATE1_GPIO;48;GPIO;out;\n"
    "PWR_GOOD;3;GPIO in;in;\n"
    "BOOT;0;GPIO;in;\n";

}  // namespace

TEST(SpikeConfigPinsMatchPinmap) {
  CHECK(kPinCount == 27);
  ParsedPin parsed[32];
  const int count = parsePinmapCsv(kTestCsv, parsed, 32);
  CHECK(count == 27);
  char mismatch[96];
  CHECK(pinsMatchConfig(parsed, count, mismatch, sizeof(mismatch)));
  CHECK(mismatch[0] == '\0');
  CHECK(findPin(parsed, count, "LCD_SCK") == 12);
  CHECK(findPin(parsed, count, "I2S_DAC_DIN") == 38);
  CHECK(findPin(parsed, count, "BOOT") == 0);
  CHECK(findPin(parsed, count, "NO_SUCH_PIN") == -1);
  INFO("spike pin map: %d pins parsed, matches spike_config.h", count);
}

TEST(SpikeConfigClocksAndBuffers) {
  CHECK(kCpuMhz == 240);
  CHECK(kPsramMhz == 80);
  CHECK(kAudioSampleRate == 48000);
  CHECK(kAudioBlockFrames == 64);
  CHECK(kUsbRxBytes == 4096);
  CHECK(kUsbTxBytes == 4096);
  CHECK(kBounceRows >= 8 && kBounceRows <= 16);
  CHECK(kBounceBytes == kDisplayWidth * kBounceRows * 2);
  CHECK(kAudioBudgetUs == 650);
  CHECK(kAudioP99BudgetUs == 500);
  CHECK(kSdLatencyBudgetUs == 10000);
  INFO("spike config: 240 MHz / PSRAM 80 MHz / 4 KiB USB FIFOs / %d-row bounce", kBounceRows);
}

TEST(SpikeAudioRingLoopback) {
  float storage[8 * 2];
  AudioRing ring;
  CHECK(ring.init(storage, 8, 2));
  float in[2 * 3] = {0.1f, -0.1f, 0.2f, -0.2f, 0.3f, -0.3f};
  CHECK(ring.push(in, 3) == 3);
  CHECK(ring.available() == 3);
  float out[2 * 2] = {};
  CHECK(ring.pop(out, 2) == 2);
  CHECK(out[0] == 0.1f && out[1] == -0.1f);
  CHECK(out[2] == 0.2f && out[3] == -0.2f);
  // Empty pop counts an underrun.
  CHECK(ring.pop(out, 2) == 1);
  CHECK(ring.underruns() == 1);
  // Fill beyond capacity: overflow is counted, never crashes.
  float big[2 * 8] = {};
  ring.push(big, 8);
  ring.push(big, 8);
  CHECK(ring.overflows() > 0);
  INFO("audio ring: pushed=%llu popped=%llu overflows=%llu underruns=%llu",
       static_cast<unsigned long long>(ring.pushed()),
       static_cast<unsigned long long>(ring.popped()),
       static_cast<unsigned long long>(ring.overflows()),
       static_cast<unsigned long long>(ring.underruns()));
}

TEST(SpikeByteRingUsb) {
  uint8_t storage[16];
  ByteRing ring;
  CHECK(ring.init(storage, 16));
  uint8_t data[20];
  for (int i = 0; i < 20; ++i) data[i] = static_cast<uint8_t>(i);
  CHECK(ring.push(data, 10) == 10);
  CHECK(ring.available() == 10);
  uint8_t out[10] = {};
  CHECK(ring.pop(out, 10) == 10);
  CHECK(out[0] == 0 && out[9] == 9);
  // Overfill: drop counter grows (never blocks the audio path).
  ring.push(data, 20);
  CHECK(ring.drops() > 0);
  INFO("USB byte ring: drops=%llu (4 KiB FIFO model)",
       static_cast<unsigned long long>(ring.drops()));
}

TEST(SpikeFramebufferBounceAndDirtyRects) {
  uint16_t framebufferMemory[32 * 4];
  Framebuffer565 fb;
  CHECK(fb.attach(framebufferMemory, 32, 4));
  fb.clear(0);
  fb.fillRect(0, 0, 32, 2, 0x1234);
  CHECK(fb.at(0, 0) == 0x1234);
  CHECK(fb.at(31, 1) == 0x1234);
  CHECK(fb.at(0, 2) == 0);
  uint16_t bounceMemory[32 * 2];
  BounceBuffer bounce;
  CHECK(bounce.init(bounceMemory, 32, 2));
  CHECK(bounce.stageRows(fb.pixels, fb.width, 0, 2) == 2);
  CHECK(bounce.data()[0] == 0x1234);
  CHECK(bounce.stagedBytes() == 32 * 2 * 2);
  DirtyTracker dirty;
  dirty.reset();
  CHECK(dirty.add(10, 300, 300, 40));
  CHECK(dirty.add(0, 0, 800, 56));
  CHECK(dirty.count() == 2);
  CHECK(dirty.rect(0).w == 300);
  // Capacity is bounded (no dynamic allocation in the audio path).
  for (int i = 0; i < 20; ++i) dirty.add(0, 0, 1, 1);
  CHECK(dirty.count() <= DirtyTracker::kMaxRects);
  INFO("framebuffer/bounce: %d-row bounce staging + dirty-rect tracker bounded", kBounceRows);
}

TEST(SpikeMetricsStatsAndPercentile) {
  MetricStats stats;
  stats.reset();
  for (int i = 0; i < 100; ++i) stats.add(300.0, kAudioBudgetUs);
  CHECK(stats.count == 100);
  CHECK(stats.minValue == 300.0);
  CHECK(stats.maxValue == 300.0);
  CHECK(stats.mean() == 300.0);
  CHECK(stats.p99() >= 300.0 && stats.p99() <= 320.0);  // 32 us bins
  stats.add(700.0, kAudioBudgetUs);
  CHECK(stats.maxValue == 700.0);
  CHECK(stats.overBudget == 1);
  INFO("metrics stats: mean=%.1f p99=%.1f max=%.1f overBudget=%llu", stats.mean(), stats.p99(),
       stats.maxValue, static_cast<unsigned long long>(stats.overBudget));
}

TEST(SpikeMetricsPassFailCriteria) {
  SpikeMetrics metrics;
  metrics.reset();
  for (int i = 0; i < 100; ++i) metrics.blockUs.add(250.0, kAudioBudgetUs);
  metrics.fullFps = 16.0;
  metrics.partialUpdatesPerSec = 31.0;
  metrics.usbDrops = 0;
  metrics.usbReconnects = 0;
  metrics.sdLatencyUs.add(2200.0, kSdLatencyBudgetUs);
  metrics.panelScanUs.add(400.0);
  char reason[96];
  CHECK(metrics.pass(reason, sizeof(reason)));
  CHECK(std::strcmp(reason, "PASS") == 0);
  // Audio criterion.
  metrics.blockUs.add(700.0);
  CHECK(!metrics.pass(reason, sizeof(reason)));
  CHECK(std::strstr(reason, "max block") != nullptr);
  // UI criterion.
  metrics.reset();
  for (int i = 0; i < 100; ++i) metrics.blockUs.add(250.0, kAudioBudgetUs);
  metrics.fullFps = 14.0;
  metrics.partialUpdatesPerSec = 31.0;
  CHECK(!metrics.pass(reason, sizeof(reason)));
  CHECK(std::strstr(reason, "full UI") != nullptr);
  INFO("docs/36 criteria wired: audio max/p99/xruns, UI fps, USB, SD, panel");
}

TEST(SpikeMetricsLogRoundtrip) {
  SpikeMetrics metrics;
  metrics.reset();
  for (int i = 0; i < 50; ++i) metrics.blockUs.add(240.0 + i, kAudioBudgetUs);
  metrics.fullFps = 15.5;
  metrics.partialUpdatesPerSec = 30.25;
  metrics.usbDrops = 0;
  metrics.usbReconnects = 0;
  metrics.sdLatencyUs.add(1500.0, kSdLatencyBudgetUs);
  metrics.sdErrors = 0;
  metrics.panelScanUs.add(700.0);
  metrics.panelErrors = 0;
  metrics.xruns = 0;
  metrics.heapFree = 180000;
  metrics.psramFree = 7000000;
  char line[512];
  CHECK(metrics.logLine(line, sizeof(line)));
  SpikeLogParser parser;
  CHECK(parser.parseLine(line));
  CHECK(std::fabs(parser.values.audioMaxUs - metrics.blockUs.maxValue) < 0.01);
  CHECK(std::fabs(parser.values.fullFps - 15.5) < 0.01);
  CHECK(std::fabs(parser.values.partialPerSec - 30.25) < 0.01);
  CHECK(parser.values.panelErrors == 0);
  CHECK(parser.values.psramFree == 7000000);
  // Garbage lines are rejected; partial lines are rejected.
  CHECK(!parser.parseLine("SPIKE_METRIC audio_max_us=oops\n"));
  CHECK(!parser.parseLine("hello\n"));
  INFO("log parser roundtrip: audio_max=%.2f full_fps=%.2f", parser.values.audioMaxUs,
       parser.values.fullFps);
}

TEST(SpikeHostSimulation) {
  SpikeMetrics metrics;
  char report[512];
  const bool ok = runHostSpikeSimulation(2000, 0xB0C0FFEEull, &metrics, report, sizeof(report));
  CHECK(ok);
  CHECK(metrics.blockUs.count == 2000);
  CHECK(metrics.blockUs.maxValue <= kAudioBudgetUs);
  CHECK(metrics.xruns == 0);
  CHECK(metrics.fullFps >= 15.0);
  CHECK(metrics.partialUpdatesPerSec >= 30.0);
  CHECK(metrics.fullFrames > 0);
  CHECK(std::strstr(report, "\"pass\":true") != nullptr);
  // Deterministic: same seed -> same metrics.
  SpikeMetrics again;
  char report2[512];
  CHECK(runHostSpikeSimulation(2000, 0xB0C0FFEEull, &again, report2, sizeof(report2)));
  CHECK(again.blockUs.maxValue == metrics.blockUs.maxValue);
  CHECK(again.fullFrames == metrics.fullFrames);
  INFO("host simulation: max=%.1f us full=%.1f fps partial=%.1f/s (%s)", metrics.blockUs.maxValue,
       metrics.fullFps, metrics.partialUpdatesPerSec, report);
}
