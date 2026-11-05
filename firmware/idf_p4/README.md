# Bukifon P4 — ESP-IDF scaffold (first SKU)

Minimal **ESP-IDF** project for the ESP32-P4 first SKU (CORE-2, 32 MB PSRAM,
USB HS).  It exists because **PlatformIO's official `platformio/espressif32`
8.0.0 has no ESP32-P4 board/framework** (the P4 `env` in
`firmware/platformio.ini` is prepared/commented for that reason).  ESP-IDF 5.5+
supports `esp32p4` natively.

The hello task proves the toolchain + board basics before engine bring-up:

- logs `esp_chip_info`, PSRAM size, CPU frequency, IDF version, free heap;
- scans I2C0 on GPIO21/22 for the CORE-2 set
  `0x20-0x23,0x36,0x57,0x60,0x61` (panel expanders, EEPROM/rail, DACs);
- starts a 5 s heartbeat task (uptime/heap + repeated I2C scan).

## 1. Install ESP-IDF 5.5+

```bash
# ~2 GB download the first time (tools + Python env); use a fast network.
mkdir -p ~/esp && cd ~/esp
git clone --depth 1 -b v5.5 --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
./install.sh esp32p4          # installs the RISC-V toolchain for ESP32-P4
. ./export.sh                 # sets IDF_PATH + toolchain for the current shell
idf.py --version              # must report v5.5 or newer
```

If the P4 target is unknown, the IDF checkout is older than 5.3 / missing
submodules (`git submodule update --init --recursive`).

## 2. Build / flash

```bash
cd firmware/idf_p4
idf.py set-target esp32p4     # creates sdkconfig from sdkconfig.defaults
idf.py build                  # first build ~3-6 min
idf.py -p /dev/ttyUSB0 flash monitor
# USB-Serial-JTAG alternative: idf.py -p /dev/ttyACM0 flash monitor
# or: idf.py flash monitor      (auto-detect port)
```

Expected log (values depend on the board):

```
I (312) bukifon: Bukifon P4 ESP-IDF scaffold (CORE-2, first SKU)
I (312) bukifon: target=esp32p4 chip_rev=... cores=2 features=0x...
I (312) bukifon: IDF version: v5.5...
I (312) bukifon: CPU frequency: 400000000 Hz
I (312) bukifon: PSRAM: 33554432 bytes (32.0 MiB), initialized=1
I (312) bukifon: I2C0 scan (SDA=21 SCL=22): N devices [...]
I (312) bukifon: I2C expected set OK: 0x20-0x23,0x36,0x57,0x60,0x61 (8/8)
```

`I2C expected set incomplete` is expected on a bare devkit without
PANEL-2/PWR-2/EEPROM/DACs — it is not a build failure.  On a custom board/stand
all 8 addresses must be present (factory self-test, docs/46).

## 3. Layout

```
firmware/idf_p4/
  CMakeLists.txt              # IDF project entry
  sdkconfig.defaults          # P4, PSRAM, 16 MB flash, FreeRTOS 1 kHz, USB HS notes
  main/
    CMakeLists.txt
    app_main.cpp              # hello + chip/PSRAM/I2C scan + heartbeat
  components/bukifon_engine/  # optional engine component (empty scaffold)
    CMakeLists.txt
    src/ include/ app/        # placeholders; copy the portable engine here
  README.md
```

## 4. Connecting the existing engine (components/)

The portable engine (`firmware/src`, `firmware/include`, `firmware/engine_unity.cpp`)
has no Arduino dependency; it can be built as an IDF component.  From the
project:

```bash
cd firmware/idf_p4/components/bukifon_engine
cp ../../../engine_unity.cpp .          # single-TU option (recommended first)
mkdir -p src include
cp -R ../../../src/. src/
cp -R ../../../include/. include/
# optional module examples:
# cp -R ../../../modules/examples ./examples
```

`components/bukifon_engine/CMakeLists.txt` automatically builds:
- every `src/*.cpp` if you copied the tree, or
- `engine_unity.cpp` if that is the only file.

Then from the app: `#include "audio/engine.hpp"` (header path comes from the
component) and link `REQUIRES bukifon_engine` in `main/CMakeLists.txt`.  The
engine is portable C++17; ESP-IDF builds it with `-fno-exceptions` (default
`sdkconfig.defaults`).  Do **not** copy `firmware/src/hal` (Arduino-only
drivers); write IDF drivers around it instead (`driver/i2c_master`,
`driver/i2s_std`, `esp_lcd`, `sdmmc`, `esp_tinyusb`).

## 5. IDF components needed for the product (next steps)

| Feature | IDF component / managed dependency |
|---|---|
| RGB565 / DSI display | `esp_lcd` (RGB panel, PPA/DMA2D), panel driver component |
| USB HS composite | managed `espressif/esp_tinyusb` (UAC2 8×8 + MIDI + HID + CDC) |
| microSD | `sdmmc` (SDMMC slot0, 4-bit) |
| Codecs | `driver/i2s_std` (PCM5102A out, PCM1808 in) |
| I2C rails/expanders | `driver/i2c_master` (already used by the hello app) |
| C6 Wi-Fi/BLE | `esp-hosted` (C6 over SPI) — later |
| Factory identity/OTA | `nvs_flash` + custom partition table (docs/42 §4) |

Add managed components in `main/idf_component.yml` when needed; keep this
scaffold dependency-free so the first build is reproducible.

## 6. Verification status

- **Not built in this development environment**: ESP-IDF was not installed here
  at the time of writing; a clone/install attempt is recorded in
  `docs/59-p4-toolchain.md`.  The project follows the IDF 5.5 CMake layout and
  the hello source is guarded for IDF 5.x (`driver/i2c_master.h`, `esp_psram.h`).
- When IDF 5.5+ is installed, `idf.py set-target esp32p4 && idf.py build` is the
  acceptance step; fix any `sdkconfig` option name changes with menuconfig, then
  record the first-build log in docs/59.
- A real hardware claim (PSRAM 32 MB, CPU 400 MHz, I2C 8/8) requires running the
  flashed image on the P4 devkit and attaching the monitor log.

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `unknown target esp32p4` | IDF < 5.3 or submodules not initialized |
| PSRAM = 0 / < 32 MiB | `idf.py menuconfig` → ESP PSRAM; check module is the 32 MB in-package P4 variant |
| I2C 0 devices | check SDA21/SCL22, 2.2 kΩ pull-ups, panel/PWR connected; the scan is 0x08-0x77 |
| flash size error | `sdkconfig.defaults` asks 16 MB; set the actual devkit flash size in menuconfig |
| USB not enumerated | P4 HS needs the HS-capable USB-C port/cable; TinyUSB is not in this scaffold yet |
