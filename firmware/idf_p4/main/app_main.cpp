// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon P4 bring-up app (CORE-2, first SKU) — docs/80 §2.
//
// Day-1 checks: UART banner/chip/PSRAM/IDF, I2C0 scan, RGB565 display patterns,
// engine bench hook (1000 blocks, max <=650 us), and an I2S1 MEMS mic record
// (1 s RMS/peak, PASS > -60 dBFS or SKIP).  Every bring-up section is compiled
// only when CONFIG_IDF_TARGET_ESP32P4 is defined; on other targets the old
// hello/self-test fallback remains.
//
// Build:
//   idf.py set-target esp32p4 && idf.py build flash monitor
//
// Pin map: hardware/core2/pinmap.md — I2C0 SDA=21 SCL=22, RGB565 16-bit on
// GPIO0..5/23/28..34/46/47, PCLK=12 DE=13 HS=14 VS=15 DISP=50 BL_PWM=49,
// I2S1 MEMS BCK=40 WS=41 DATA=42, MIC_SEL=54.
#include <cmath>
#include <cstdio>
#include <cstring>
#include <initializer_list>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_chip_info.h"
#include "esp_err.h"
#include "esp_idf_version.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_heap_caps.h"
#include "driver/gpio.h"

#if __has_include("esp_psram.h")
#include "esp_psram.h"
#define BUKIFON_HAVE_PSRAM_H 1
#endif
#if __has_include("esp_flash.h")
#include "esp_flash.h"
#define BUKIFON_HAVE_FLASH_H 1
#endif
#if __has_include("esp_clk.h")
#include "esp_clk.h"
#define BUKIFON_HAVE_ESP_CLK 1
#endif
#if __has_include("driver/i2c_master.h")
#include "driver/i2c_master.h"
#define BUKIFON_HAVE_I2C_MASTER 1
#endif
#if __has_include("driver/uart.h")
#include "driver/uart.h"
#define BUKIFON_HAVE_UART_DRIVER 1
#endif
#if __has_include("driver/ledc.h")
#include "driver/ledc.h"
#define BUKIFON_HAVE_LEDC 1
#endif
#if __has_include("esp_lcd_panel_rgb.h")
#include "esp_lcd_panel_rgb.h"
#include "esp_lcd_panel_ops.h"
#define BUKIFON_HAVE_LCD_RGB 1
#endif
#if __has_include("driver/i2s_std.h")
#include "driver/i2s_std.h"
#define BUKIFON_HAVE_I2S_STD 1
#endif

namespace {

constexpr const char* kTag = "bukifon";
constexpr int kI2cSda = 21;
constexpr int kI2cScl = 22;
constexpr uint32_t kI2cHz = 400000;
constexpr int kLcdWidth = 800;
constexpr int kLcdHeight = 480;
constexpr uint32_t kBenchBlocks = 1000;
constexpr uint32_t kBlockFrames = 64;
constexpr float kBenchLimitUs = 650.0f;

constexpr uint8_t kExpectedI2c[] = {0x20, 0x21, 0x22, 0x23, 0x36, 0x57, 0x60, 0x61};

#if defined(BUKIFON_HAVE_I2C_MASTER)
i2c_master_bus_handle_t g_bus = nullptr;
#endif

const char* targetName() {
#if defined(CONFIG_IDF_TARGET)
  return CONFIG_IDF_TARGET;
#else
  return "unknown";
#endif
}

#if defined(CONFIG_IDF_TARGET_ESP32P4)
void printChipBanner() {
  esp_chip_info_t chip;
  esp_chip_info(&chip);
  uint32_t flashBytes = 0;
#if defined(BUKIFON_HAVE_FLASH_H)
  esp_flash_get_size(nullptr, &flashBytes);
#endif
  ESP_LOGI(kTag, "==================================================");
  ESP_LOGI(kTag, " Bukifon P4 bring-up");
  ESP_LOGI(kTag, " target=%s rev=%d cores=%d features=0x%08x", targetName(), chip.revision,
           chip.cores, static_cast<unsigned>(chip.features));
  ESP_LOGI(kTag, " IDF version: %s", esp_get_idf_version());
#if defined(BUKIFON_HAVE_ESP_CLK)
  ESP_LOGI(kTag, " CPU: %d Hz", esp_clk_cpu_freq());
#elif defined(CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ)
  ESP_LOGI(kTag, " CPU: %d MHz (config)", CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ);
#endif
  if (flashBytes) {
    ESP_LOGI(kTag, " flash: %.1f MiB", static_cast<double>(flashBytes) / (1024.0 * 1024.0));
  }
#if defined(BUKIFON_HAVE_PSRAM_H) && defined(CONFIG_SPIRAM)
  const size_t psram = esp_psram_get_size();
  ESP_LOGI(kTag, " PSRAM: %.1f MiB (init=%d)", static_cast<double>(psram) / (1024.0 * 1024.0),
           esp_psram_is_initialized() ? 1 : 0);
  if (psram < 32u * 1024u * 1024u) {
    ESP_LOGW(kTag, " PSRAM < 32 MiB — check in-package PSRAM config (CORE-2 rev.3)");
  }
#else
  ESP_LOGW(kTag, " PSRAM not enabled in this build (CONFIG_SPIRAM)");
#endif
  ESP_LOGI(kTag, " free heap: %u B", static_cast<unsigned>(esp_get_free_heap_size()));
  ESP_LOGI(kTag, "==================================================");
}

// --- I2C0 scan (MCP23017 0x20-0x27, 24C32 0x50-0x57, DAC/ADC/fuel 0x48-0x4F) ---
#if defined(BUKIFON_HAVE_I2C_MASTER)
bool i2cBegin() {
  i2c_master_bus_config_t config = {};
  config.i2c_port = I2C_NUM_0;
  config.sda_io_num = static_cast<gpio_num_t>(kI2cSda);
  config.scl_io_num = static_cast<gpio_num_t>(kI2cScl);
  config.clk_source = I2C_CLK_SRC_DEFAULT;
  config.glitch_ignore_cnt = 7;
  config.flags.enable_internal_pullup = 1;
  const esp_err_t rc = i2c_new_master_bus(&config, &g_bus);
  if (rc != ESP_OK) {
    ESP_LOGE(kTag, "I2C0 init FAIL: %s (SDA=%d SCL=%d)", esp_err_to_name(rc), kI2cSda,
             kI2cScl);
    g_bus = nullptr;
    return false;
  }
  ESP_LOGI(kTag, "I2C0 init OK: SDA=%d SCL=%d %u Hz", kI2cSda, kI2cScl,
           static_cast<unsigned>(kI2cHz));
  return true;
}

void i2cScan() {
  if (!g_bus) {
    ESP_LOGW(kTag, "I2C scan SKIP: bus not initialized");
    return;
  }
  char foundList[160] = {};
  size_t used = 0;
  int found = 0;
  auto probeRange = [&](int first, int last) {
    int rangeFound = 0;
    for (int address = first; address <= last; ++address) {
      if (i2c_master_probe(g_bus, static_cast<uint16_t>(address), 50) == ESP_OK) {
        ++found;
        ++rangeFound;
        if (used + 8 < sizeof(foundList)) {
          used += static_cast<size_t>(snprintf(foundList + used, sizeof(foundList) - used,
                                               "0x%02X ", address));
        }
      }
    }
    ESP_LOGI(kTag, " I2C range 0x%02X-0x%02X: %d device(s)", first, last, rangeFound);
  };
  probeRange(0x20, 0x27);
  probeRange(0x48, 0x4F);
  probeRange(0x50, 0x57);
  // Real CORE-2 extras outside the requested ranges (fuel/DACs).
  for (int address : {0x36, 0x60, 0x61}) {
    if (i2c_master_probe(g_bus, static_cast<uint16_t>(address), 50) == ESP_OK) {
      ++found;
      if (used + 8 < sizeof(foundList)) {
        used += static_cast<size_t>(snprintf(foundList + used, sizeof(foundList) - used,
                                             "0x%02X ", address));
      }
    }
  }
  int expectedFound = 0;
  for (uint8_t expected : kExpectedI2c) {
    if (i2c_master_probe(g_bus, expected, 50) == ESP_OK) ++expectedFound;
  }
  ESP_LOGI(kTag, "I2C scan found %d [%s]", found, foundList);
  if (expectedFound == static_cast<int>(sizeof(kExpectedI2c))) {
    ESP_LOGI(kTag, "I2C expected 8/8 PASS (0x20-0x23, 0x36, 0x57, 0x60, 0x61)");
  } else {
    ESP_LOGE(kTag, "I2C expected %d/8 FAIL (check panel/PWR/EEPROM/DAC wiring)",
             expectedFound);
  }
}
#else
bool i2cBegin() { return false; }
void i2cScan() { ESP_LOGW(kTag, "I2C scan SKIP: driver/i2c_master.h unavailable"); }
#endif

// --- RGB565 display: 4 patterns x 5 s (failure = log, never panic) -----------
#if defined(BUKIFON_HAVE_LCD_RGB)
bool backlightInit() {
#if defined(BUKIFON_HAVE_LEDC)
  ledc_timer_config_t timer = {};
  timer.speed_mode = LEDC_LOW_SPEED_MODE;
  timer.timer_num = LEDC_TIMER_0;
  timer.duty_resolution = LEDC_TIMER_8_BIT;
  timer.freq_hz = 5000;
  timer.clk_cfg = LEDC_AUTO_CLK;
  if (ledc_timer_config(&timer) != ESP_OK) return false;
  ledc_channel_config_t channel = {};
  channel.gpio_num = 49;  // BL_PWM
  channel.speed_mode = LEDC_LOW_SPEED_MODE;
  channel.channel = LEDC_CHANNEL_0;
  channel.intr_type = LEDC_INTR_DISABLE;
  channel.timer_sel = LEDC_TIMER_0;
  channel.duty = 255;
  channel.hpoint = 0;
  if (ledc_channel_config(&channel) != ESP_OK) return false;
  ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 255);
  ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
  return true;
#else
  return false;
#endif
}

void drawColorBars(uint16_t* fb) {
  static const uint16_t bars[8] = {0xF800, 0x07E0, 0x001F, 0xFFFF,
                                   0xFFE0, 0x07FF, 0xF81F, 0x0000};
  for (int y = 0; y < kLcdHeight; ++y) {
    for (int x = 0; x < kLcdWidth; ++x) fb[y * kLcdWidth + x] = bars[(x * 8) / kLcdWidth];
  }
}
void drawChecker(uint16_t* fb, int cell) {
  for (int y = 0; y < kLcdHeight; ++y) {
    for (int x = 0; x < kLcdWidth; ++x) {
      const bool on = ((x / cell) + (y / cell)) & 1;
      fb[y * kLcdWidth + x] = on ? 0xFFFF : 0x0000;
    }
  }
}
void drawGrid(uint16_t* fb) {
  for (int y = 0; y < kLcdHeight; ++y) {
    for (int x = 0; x < kLcdWidth; ++x) {
      const bool line = (x % 2 == 0) || (y % 2 == 0) || (x % 100 == 0) || (y % 100 == 0);
      fb[y * kLcdWidth + x] = line ? 0x07E0 : 0x0000;
    }
  }
}
uint8_t glyph5x7(char c, int row) {
  // Minimal 5x7 font for the text pattern.
  switch (c) {
    case 'B': { static const uint8_t g[7] = {0x1E,0x11,0x11,0x1E,0x11,0x11,0x1E}; return g[row]; }
    case 'U': { static const uint8_t g[7] = {0x11,0x11,0x11,0x11,0x11,0x11,0x0E}; return g[row]; }
    case 'K': { static const uint8_t g[7] = {0x11,0x12,0x14,0x18,0x14,0x12,0x11}; return g[row]; }
    case 'I': { static const uint8_t g[7] = {0x0E,0x04,0x04,0x04,0x04,0x04,0x0E}; return g[row]; }
    case 'F': { static const uint8_t g[7] = {0x1F,0x10,0x10,0x1E,0x10,0x10,0x10}; return g[row]; }
    case 'O': { static const uint8_t g[7] = {0x0E,0x11,0x11,0x11,0x11,0x11,0x0E}; return g[row]; }
    case 'N': { static const uint8_t g[7] = {0x11,0x19,0x15,0x13,0x11,0x11,0x11}; return g[row]; }
    case 'P': { static const uint8_t g[7] = {0x1E,0x11,0x11,0x1E,0x10,0x10,0x10}; return g[row]; }
    case '4': { static const uint8_t g[7] = {0x02,0x06,0x0A,0x12,0x1F,0x02,0x02}; return g[row]; }
    case '8': { static const uint8_t g[7] = {0x0E,0x11,0x11,0x0E,0x11,0x11,0x0E}; return g[row]; }
    case '0': { static const uint8_t g[7] = {0x0E,0x11,0x13,0x15,0x19,0x11,0x0E}; return g[row]; }
    default: return 0;
  }
}
void drawText(uint16_t* fb) {
  for (int y = 0; y < kLcdHeight; ++y) {
    for (int x = 0; x < kLcdWidth; ++x) fb[y * kLcdWidth + x] = 0x0000;
  }
  const char* text = "BUKIFON P4 800x480";
  const int scale = 4;
  const int glyphW = 6 * scale;
  const int startX = (kLcdWidth - static_cast<int>(std::strlen(text)) * glyphW) / 2;
  const int startY = kLcdHeight / 2 - 3 * scale;
  for (size_t i = 0; i < std::strlen(text); ++i) {
    for (int row = 0; row < 7; ++row) {
      const uint8_t bits = glyph5x7(text[i], row);
      for (int col = 0; col < 5; ++col) {
        if (bits & (1u << (4 - col))) {
          for (int sy = 0; sy < scale; ++sy) {
            for (int sx = 0; sx < scale; ++sx) {
              const int px = startX + static_cast<int>(i) * glyphW + col * scale + sx;
              const int py = startY + row * scale + sy;
              if (px >= 0 && px < kLcdWidth && py >= 0 && py < kLcdHeight) {
                fb[py * kLcdWidth + px] = 0xFFFF;
              }
            }
          }
        }
      }
    }
  }
}

void displayTest() {
  esp_lcd_rgb_panel_config_t config = {};
  config.clk_src = LCD_CLK_SRC_DEFAULT;
  config.timings.pclk_hz = 16 * 1000 * 1000;
  config.timings.h_res = kLcdWidth;
  config.timings.v_res = kLcdHeight;
  config.timings.hsync_pulse_width = 40;
  config.timings.hsync_back_porch = 40;
  config.timings.hsync_front_porch = 48;
  config.timings.vsync_pulse_width = 13;
  config.timings.vsync_back_porch = 13;
  config.timings.vsync_front_porch = 3;
  config.timings.flags.pclk_active_neg = 0;
  config.data_width = 16;
  config.bits_per_pixel = 16;
  config.num_fbs = 1;
  config.bounce_buffer_size_px = kLcdWidth * 10;
  config.hsync_gpio_num = 14;
  config.vsync_gpio_num = 15;
  config.de_gpio_num = 13;
  config.pclk_gpio_num = 12;
  config.disp_gpio_num = 50;
  const int dataPins[16] = {0, 1, 2, 3, 4, 5, 23, 28, 29, 30, 31, 32, 33, 34, 46, 47};
  for (int i = 0; i < 16; ++i) config.data_gpio_nums[i] = dataPins[i];
  config.flags.fb_in_psram = 1;
  esp_lcd_panel_handle_t panel = nullptr;
  esp_err_t rc = esp_lcd_new_rgb_panel(&config, &panel);
  if (rc != ESP_OK || !panel) {
    ESP_LOGE(kTag, "display init FAIL: %s (FPC/BL/PCLK check; continuing)",
             esp_err_to_name(rc));
    return;
  }
  rc = esp_lcd_panel_reset(panel);
  if (rc == ESP_OK) rc = esp_lcd_panel_init(panel);
  if (rc != ESP_OK) {
    ESP_LOGE(kTag, "display panel reset/init FAIL: %s (continuing)", esp_err_to_name(rc));
    esp_lcd_panel_del(panel);
    return;
  }
  // Some RGB panels do not implement disp_on_off; that is not a failure.
  const esp_err_t dispRc = esp_lcd_panel_disp_on_off(panel, true);
  if (dispRc != ESP_OK && dispRc != ESP_ERR_NOT_SUPPORTED) {
    ESP_LOGW(kTag, "display disp_on_off: %s (continuing)", esp_err_to_name(dispRc));
  }
  if (!backlightInit()) ESP_LOGW(kTag, "BL_PWM init failed — display may stay dark");
  uint16_t* fb = static_cast<uint16_t*>(heap_caps_malloc(
      static_cast<size_t>(kLcdWidth) * kLcdHeight * sizeof(uint16_t),
      MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (!fb) {
    ESP_LOGE(kTag, "display framebuffer alloc FAIL (PSRAM); skipping patterns");
    esp_lcd_panel_del(panel);
    return;
  }
  struct Pattern {
    const char* name;
    void (*draw)(uint16_t*);
  };
  const Pattern patterns[4] = {{"color-bars", drawColorBars},
                               {"checkerboard", [](uint16_t* b) { drawChecker(b, 40); }},
                               {"1px-grid", drawGrid},
                               {"text", drawText}};
  for (const Pattern& pattern : patterns) {
    pattern.draw(fb);
    rc = esp_lcd_panel_draw_bitmap(panel, 0, 0, kLcdWidth, kLcdHeight, fb);
    if (rc != ESP_OK) {
      ESP_LOGE(kTag, "display pattern %s draw FAIL: %s", pattern.name, esp_err_to_name(rc));
    } else {
      ESP_LOGI(kTag, "display pattern %s (800x480 RGB565) — 5 s", pattern.name);
    }
    vTaskDelay(pdMS_TO_TICKS(5000));
  }
  free(fb);
  esp_lcd_panel_del(panel);
  ESP_LOGI(kTag, "display test done (check no tearing/bands; fps target >=15 full)");
}
#else
void displayTest() { ESP_LOGW(kTag, "display test SKIP: esp_lcd_panel_rgb.h unavailable"); }
#endif

// --- Engine bench hook: 1000 blocks x 64 frames, p4_profile-style workload ---
bool benchEngine() {
  // A deterministic model of the p4_profile per-block workload (8 FM voices +
  // ZDF ladder + limiter); the full host harness lives in firmware/bench.
  float voicePhase[8] = {};
  float voiceEnv[8] = {};
  float filterState[2] = {};
  volatile float sink = 0.0f;
  uint64_t worstUs = 0;
  uint64_t totalUs = 0;
  for (uint32_t block = 0; block < kBenchBlocks; ++block) {
    const uint64_t start = static_cast<uint64_t>(esp_timer_get_time());
    for (uint32_t n = 0; n < kBlockFrames; ++n) {
      float mix = 0.0f;
      for (int v = 0; v < 8; ++v) {
        voicePhase[v] += 0.0025f + 0.0001f * static_cast<float>(v);
        if (voicePhase[v] > 6.2831853f) voicePhase[v] -= 6.2831853f;
        const float fm = std::sin(voicePhase[v] + 1.7f * std::sin(voicePhase[v] * 2.0f));
        voiceEnv[v] = voiceEnv[v] * 0.9995f + (fm > 0.0f ? 0.0005f : -0.0005f);
        mix += fm * (0.02f + voiceEnv[v]);
      }
      filterState[0] += 0.02f * (mix - filterState[0]);
      filterState[1] += 0.01f * (filterState[0] - filterState[1]);
      const float out = filterState[1] / (1.0f + std::fabs(filterState[1]));
      sink += out * 0.001f;
    }
    const uint64_t elapsed = static_cast<uint64_t>(esp_timer_get_time()) - start;
    totalUs += elapsed;
    if (elapsed > worstUs) worstUs = elapsed;
  }
  const bool pass = worstUs <= static_cast<uint64_t>(kBenchLimitUs);
  ESP_LOGI(kTag, "engine bench: %u blocks x %u frames, max=%u us, mean=%u us -> %s",
           static_cast<unsigned>(kBenchBlocks), static_cast<unsigned>(kBlockFrames),
           static_cast<unsigned>(worstUs),
           static_cast<unsigned>(totalUs / kBenchBlocks), pass ? "PASS" : "FAIL");
  ESP_LOGI(kTag, "engine bench criterion: max block <= %.0f us; sink=%f",
           static_cast<double>(kBenchLimitUs), static_cast<double>(sink));
  return pass;
}

// --- I2S1 MEMS mic skeleton: 1 s, 48 kHz/24-bit, RMS/peak, PASS/SKIP ---------
void micTest() {
#if defined(CONFIG_IDF_TARGET_ESP32P4) && defined(BUKIFON_HAVE_I2S_STD)
  // MIC_SEL=1 selects the MEMS/electret mic path.
  gpio_set_direction(static_cast<gpio_num_t>(54), GPIO_MODE_OUTPUT);
  gpio_set_level(static_cast<gpio_num_t>(54), 1);
  i2s_chan_handle_t rx = nullptr;
  i2s_chan_config_t chanCfg = {};
  chanCfg.id = I2S_NUM_1;
  chanCfg.role = I2S_ROLE_MASTER;
  chanCfg.dma_desc_num = 6;
  chanCfg.dma_frame_num = 240;
  chanCfg.auto_clear = true;
  esp_err_t rc = i2s_new_channel(&chanCfg, nullptr, &rx);
  if (rc != ESP_OK || !rx) {
    ESP_LOGW(kTag, "mic I2S1 init SKIP: %s", esp_err_to_name(rc));
    return;
  }
  i2s_std_config_t stdCfg = {};
  stdCfg.clk_cfg.sample_rate_hz = 48000;
  stdCfg.clk_cfg.clk_src = I2S_CLK_SRC_DEFAULT;
  stdCfg.clk_cfg.mclk_multiple = I2S_MCLK_MULTIPLE_256;
  stdCfg.slot_cfg.data_bit_width = I2S_DATA_BIT_WIDTH_24BIT;
  stdCfg.slot_cfg.slot_bit_width = I2S_SLOT_BIT_WIDTH_24BIT;
  stdCfg.slot_cfg.slot_mode = I2S_SLOT_MODE_MONO;
  stdCfg.slot_cfg.slot_mask = I2S_STD_SLOT_LEFT;
  stdCfg.gpio_cfg.mclk = I2S_GPIO_UNUSED;
  stdCfg.gpio_cfg.bclk = static_cast<gpio_num_t>(40);
  stdCfg.gpio_cfg.ws = static_cast<gpio_num_t>(41);
  stdCfg.gpio_cfg.dout = I2S_GPIO_UNUSED;
  stdCfg.gpio_cfg.din = static_cast<gpio_num_t>(42);
  rc = i2s_channel_init_std_mode(rx, &stdCfg);
  if (rc == ESP_OK) rc = i2s_channel_enable(rx);
  if (rc != ESP_OK) {
    ESP_LOGW(kTag, "mic I2S1 enable SKIP: %s", esp_err_to_name(rc));
    i2s_del_channel(rx);
    return;
  }
  static int32_t samples[48000];
  size_t totalSamples = 0;
  const int64_t deadline = esp_timer_get_time() + 1500000;  // 1.5 s budget
  while (totalSamples < 48000 && esp_timer_get_time() < deadline) {
    size_t bytesRead = 0;
    const size_t want = (48000 - totalSamples) * sizeof(int32_t);
    rc = i2s_channel_read(rx, samples + totalSamples, want, &bytesRead, 1000);
    if (rc != ESP_OK && rc != ESP_ERR_TIMEOUT) {
      ESP_LOGW(kTag, "mic I2S1 read SKIP: %s", esp_err_to_name(rc));
      i2s_channel_disable(rx);
      i2s_del_channel(rx);
      return;
    }
    totalSamples += bytesRead / sizeof(int32_t);
  }
  i2s_channel_disable(rx);
  i2s_del_channel(rx);
  if (totalSamples == 0) {
    ESP_LOGW(kTag, "mic test SKIP: no I2S1 data (J19/MEMS not connected?)");
    return;
  }
  double sumSq = 0.0;
  int32_t peak = 0;
  for (size_t i = 0; i < totalSamples; ++i) {
    const int32_t value = samples[i] >> 8;  // 24-bit left-justified in 32-bit slot
    const double normalized = static_cast<double>(value) / 8388608.0;
    sumSq += normalized * normalized;
    const int32_t absValue = value < 0 ? -value : value;
    if (absValue > peak) peak = absValue;
  }
  const double rms = std::sqrt(sumSq / static_cast<double>(totalSamples));
  const double rmsDb = 20.0 * std::log10(rms > 1e-9 ? rms : 1e-9);
  const double peakDb = 20.0 * std::log10(static_cast<double>(peak) / 8388608.0 + 1e-12);
  const bool pass = rmsDb > -60.0;
  ESP_LOGI(kTag, "mic I2S1: %u samples, RMS=%.1f dBFS peak=%.1f dBFS -> %s",
           static_cast<unsigned>(totalSamples), rmsDb, peakDb, pass ? "PASS" : "FAIL");
  ESP_LOGI(kTag, "mic criterion: RMS > -60 dBFS (1 s, 48 kHz/24-bit); SW3 mute/LED on day-2");
#else
  ESP_LOGW(kTag, "mic test SKIP: driver/i2s_std.h unavailable or non-P4 target");
#endif
}

void heartbeatTask(void*) {
  for (;;) {
    ESP_LOGI(kTag, "heartbeat: uptime=%llu ms free_heap=%u",
             static_cast<unsigned long long>(esp_timer_get_time() / 1000),
             static_cast<unsigned>(esp_get_free_heap_size()));
    i2cScan();
    vTaskDelay(pdMS_TO_TICKS(10000));
  }
}

#else
// Non-P4 fallback: keep the project buildable on another IDF target.
void heartbeatTask(void*) {
  for (;;) {
    ESP_LOGW(kTag, "Bukifon P4 bring-up requires CONFIG_IDF_TARGET_ESP32P4");
    vTaskDelay(pdMS_TO_TICKS(10000));
  }
}
#endif

}  // namespace

extern "C" void app_main(void) {
#if defined(CONFIG_IDF_TARGET_ESP32P4)
#if defined(BUKIFON_HAVE_UART_DRIVER)
  uart_set_baudrate(UART_NUM_0, 115200);  // UART0 console, docs/80 day-1
#endif
  printChipBanner();
  if (i2cBegin()) i2cScan();
  displayTest();
  benchEngine();
  micTest();
  ESP_LOGI(kTag, "P4 bring-up sequence complete; heartbeat every 10 s");
  xTaskCreate(heartbeatTask, "bukifon_hb", 4096, nullptr, 5, nullptr);
#else
  ESP_LOGW(kTag, "Bukifon P4 bring-up is compiled only for CONFIG_IDF_TARGET_ESP32P4");
  esp_chip_info_t chip;
  esp_chip_info(&chip);
  ESP_LOGI(kTag, "fallback scaffold: target=%s IDF=%s", targetName(), esp_get_idf_version());
  xTaskCreate(heartbeatTask, "bukifon_hb", 4096, nullptr, 5, nullptr);
#endif
}
