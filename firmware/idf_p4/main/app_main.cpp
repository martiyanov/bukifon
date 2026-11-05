// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon P4 firmware — ESP-IDF hello/self-test task (first SKU, CORE-2).
//
// Purpose: prove the ESP-IDF toolchain path on a real ESP32-P4 devkit before
// porting the engine: chip info, PSRAM size, CPU/IDF version, and an I2C scan
// of the CORE-2 rail (0x20-0x23 expanders, 0x36? , 0x57 EEPROM, 0x60/0x61 DACs).
//
// Build:
//   idf.py set-target esp32p4
//   idf.py build flash monitor
//
// Pin map: hardware/core2/pinmap.csv — I2C0 SDA GPIO21 / SCL GPIO22 (400 kHz).
#include <cstdio>
#include <cstring>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_chip_info.h"
#include "esp_idf_version.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"

#if __has_include("esp_psram.h")
#include "esp_psram.h"
#define BUKIFON_HAVE_PSRAM_H 1
#endif
#if __has_include("esp_clk.h")
#include "esp_clk.h"
#define BUKIFON_HAVE_ESP_CLK 1
#endif
#if __has_include("driver/i2c_master.h")
#include "driver/i2c_master.h"
#define BUKIFON_HAVE_I2C_MASTER 1
#endif

namespace {

constexpr const char* kTag = "bukifon";
constexpr int kI2cSda = 21;  // CORE-2 I2C0_SDA
constexpr int kI2cScl = 22;  // CORE-2 I2C0_SCL
constexpr uint32_t kI2cHz = 400000;

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

void logChipInfo() {
  esp_chip_info_t chip;
  esp_chip_info(&chip);
  ESP_LOGI(kTag, "target=%s chip_rev=%d cores=%d features=0x%08x", targetName(), chip.revision,
           chip.cores, static_cast<unsigned>(chip.features));
  ESP_LOGI(kTag, "IDF version: %s", esp_get_idf_version());
  ESP_LOGI(kTag, "free heap: %u bytes", static_cast<unsigned>(esp_get_free_heap_size()));
#if defined(BUKIFON_HAVE_ESP_CLK)
  ESP_LOGI(kTag, "CPU frequency: %d Hz", esp_clk_cpu_freq());
#elif defined(CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ)
  ESP_LOGI(kTag, "CPU frequency (config): %d MHz", CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ);
#endif
#if defined(BUKIFON_HAVE_PSRAM_H) && defined(CONFIG_SPIRAM)
  const size_t psram = esp_psram_get_size();
  ESP_LOGI(kTag, "PSRAM: %u bytes (%.1f MiB), initialized=%d", static_cast<unsigned>(psram),
           static_cast<double>(psram) / (1024.0 * 1024.0),
           esp_psram_is_initialized() ? 1 : 0);
  if (psram < 32u * 1024u * 1024u) {
    ESP_LOGW(kTag, "PSRAM < 32 MiB: check the module variant / in-package PSRAM config");
  }
#else
  ESP_LOGW(kTag, "PSRAM not enabled in this build (CONFIG_SPIRAM)");
#endif
}

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
    ESP_LOGE(kTag, "i2c_new_master_bus failed: %s", esp_err_to_name(rc));
    g_bus = nullptr;
    return false;
  }
  return true;
}

void i2cScan() {
  if (!g_bus) {
    ESP_LOGW(kTag, "I2C scan skipped: bus not initialized");
    return;
  }
  int found = 0;
  int expectedFound = 0;
  char foundList[128] = {};
  size_t used = 0;
  for (int address = 0x08; address <= 0x77; ++address) {
    const esp_err_t rc = i2c_master_probe(g_bus, static_cast<uint16_t>(address), 50);
    if (rc == ESP_OK) {
      ++found;
      if (used + 8 < sizeof(foundList)) {
        used += static_cast<size_t>(
            snprintf(foundList + used, sizeof(foundList) - used, "%02X ", address));
      }
    }
  }
  for (uint8_t expected : kExpectedI2c) {
    if (i2c_master_probe(g_bus, expected, 50) == ESP_OK) ++expectedFound;
  }
  ESP_LOGI(kTag, "I2C0 scan (SDA=%d SCL=%d): %d devices [%s]", kI2cSda, kI2cScl, found,
           foundList);
  if (expectedFound == static_cast<int>(sizeof(kExpectedI2c))) {
    ESP_LOGI(kTag, "I2C expected set OK: 0x20-0x23,0x36,0x57,0x60,0x61 (%d/%d)",
             expectedFound, static_cast<int>(sizeof(kExpectedI2c)));
  } else {
    ESP_LOGW(kTag, "I2C expected set incomplete: %d/%d (check panel/PWR/EEPROM/DACs)",
             expectedFound, static_cast<int>(sizeof(kExpectedI2c)));
  }
}
#else
void i2cScan() {
  ESP_LOGW(kTag,
           "I2C scan stubbed: driver/i2c_master.h not found (IDF < 5.2?). "
           "Expected 0x20-0x23,0x36,0x57,0x60,0x61 on GPIO21/22");
}
#endif

void heartbeatTask(void*) {
  for (;;) {
    ESP_LOGI(kTag, "heartbeat: uptime=%llu ms free_heap=%u", esp_timer_get_time() / 1000,
             static_cast<unsigned>(esp_get_free_heap_size()));
    i2cScan();
    vTaskDelay(pdMS_TO_TICKS(5000));
  }
}

}  // namespace

extern "C" void app_main(void) {
  ESP_LOGI(kTag, "Bukifon P4 ESP-IDF scaffold (CORE-2, first SKU)");
  logChipInfo();
#if defined(BUKIFON_HAVE_I2C_MASTER)
  if (i2cBegin()) i2cScan();
#else
  i2cScan();
#endif
  xTaskCreate(heartbeatTask, "bukifon_hb", 4096, nullptr, 5, nullptr);
  ESP_LOGI(kTag, "heartbeat task started; ^C/idf.py monitor to watch logs");
}
