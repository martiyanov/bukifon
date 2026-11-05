# 59. P4 toolchain: ESP-IDF scaffold (PlatformIO cannot target ESP32-P4)

**Status:** ESP-IDF project scaffold `firmware/idf_p4/` is ready to build on a
machine with **ESP-IDF 5.5+**.  In this development environment the IDF
toolchain is **not installed/verified** (attempt recorded in §7); no build
success is claimed here.  Host firmware tests are unchanged (216/216).

Related: [P1 measurement stand](56-p1-measurements.md), [CORE-2 pin map](../hardware/core2/pinmap.md),
[factory self-test](46-factory-test.md), [RC definition](36-rc-definition.md).

---

## 1. Why PlatformIO cannot build the P4 here

- The installed official `platformio/espressif32` **8.0.0** ships
  `arduino-esp32` 3.x, whose board definitions cover ESP32/S2/S3/C3/C6 — **there
  is no ESP32-P4 board and no P4 framework package**.
- Our PlatformIO env `p4` is therefore prepared but **commented out**
  (`firmware/platformio.ini`); running it yields
  `UnknownEnvNamesError: Unknown environment names 'p4'`.  That is the honest
  state, not a P4 build failure.
- `pioarduino/platform-espressif32` has preview P4 support and can be used
  experimentally, but it is young; the product path for the first SKU is
  **ESP-IDF + `idf.py`**, not PlatformIO/Arduino.

**Decision:** P4 firmware is built with ESP-IDF (`target esp32p4`), custom board
configuration, C++17/FreeRTOS.  PlatformIO stays for the S3 lite spike/host
tooling only.

## 2. Project layout

```
firmware/idf_p4/
  CMakeLists.txt                  # IDF project entry (include project.cmake)
  sdkconfig.defaults              # P4, 32 MB PSRAM, 16 MB flash, FreeRTOS 1 kHz
  main/
    CMakeLists.txt                # requires esp_driver_i2c, esp_psram, esp_timer
    app_main.cpp                  # hello: chip/PSRAM/CPU/IDF + I2C scan + heartbeat
  components/bukifon_engine/      # optional portable-engine component (empty scaffold)
  README.md                       # install/build/flash + engine integration
```

The hello task is intentionally minimal but useful for bring-up:

1. `esp_chip_info` (target/revision/cores/features);
2. `esp_psram_get_size()` (must be 32 MiB on the P4 first SKU);
3. `esp_clk_cpu_freq()` (400 MHz target) and `esp_get_idf_version()`;
4. I2C0 scan on **GPIO21/22** (CORE-2 pin map) for
   `0x20-0x23,0x36,0x57,0x60,0x61`;
5. 5 s heartbeat: uptime/free heap + repeated scan.

## 3. Install ESP-IDF 5.5+ and build

```bash
mkdir -p ~/esp && cd ~/esp
git clone --depth 1 -b v5.5 --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
./install.sh esp32p4
. ./export.sh

cd firmware/idf_p4
idf.py set-target esp32p4       # generates sdkconfig from sdkconfig.defaults
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

Requirements: Python 3.9+, CMake/Ninja (installed by `install.sh`), ~2 GB disk
for tools, a P4 devkit (ESP32-P4-Function-EV-Board or CORE-2 prototype) with the
**HS USB-C** port.  First build takes ~3-6 min; `idf.py set-target` must print
`esp32p4` (otherwise IDF is older than 5.3 / submodules missing).

**Custom board:** start with the P4-EV board target; the CORE-2 board definition
(pin map `hardware/core2/pinmap.md`) is added as a custom board/`sdkconfig` once
the PCB exists.  Keep `CONFIG_SPIRAM` + 32 MB in-package PSRAM; verify in
`idf.py menuconfig` (ESP PSRAM) on the real module.

## 4. How this plugs into the P1 stand (docs/56)

P1 measures P4 vs H743 (workload frozen in docs/05).  The IDF scaffold is step 0
of the P4 side of the stand:

| Step | What | Pass/exit |
|---|---|---|
| 0 | flash `firmware/idf_p4` hello | boot log: `target=esp32p4`, PSRAM 32 MiB, CPU 400 MHz, IDF 5.5+ |
| 1 | connect PANEL-2/PWR-2 (or devkit I2C peripherals) | I2C expected set 8/8 (0x20-0x23/36/57/60/61) |
| 2 | add the portable engine component (`components/bukifon_engine`) | engine compiles under IDF, no Arduino HAL pulled in |
| 3 | add bench harness component (port `firmware/bench` scenarios) | `p4_profile` measures max block/p99/xruns, RGB fps, HS USB |
| 4 | add esp_lcd RGB/DSI + esp_tinyusb + sdmmc + i2s | display frames, UAC2 8×8 enumeration, SD latency |
| 5 | run P1 scenarios per docs/56, record JSON/CSV | decision P4 vs H743 per docs/05 §9 |

Required IDF/managed components for steps 3–5:

| Feature | Component |
|---|---|
| RGB565/DSI 800×480 | `esp_lcd` (RGB panel + PPA/DMA2D), panel driver |
| USB HS composite (UAC2 8×8, MIDI, HID, CDC) | `espressif/esp_tinyusb` (managed) |
| microSD (4-bit SDMMC slot0) | `sdmmc` |
| PCM5102A/PCM1808 | `driver/i2s_std` |
| Rails/expanders/EEPROM/DACs | `driver/i2c_master` |
| Wi-Fi/BLE via C6 | `esp-hosted` (later) |
| Factory identity / OTA | `nvs_flash` + custom partitions (docs/42 §4) |

## 5. DFM / bring-up implications

- UART0 **GPIO37/38** and USB-Serial-JTAG/USB HS CDC are the two log paths; the
  hello log is the first bring-up evidence for the DFM checklist.
- BOOT (GPIO35) / CHIP_PU reset must be reachable without opening the case
  (docs/42 §4; test points/pogo field docs/42 §1).
- Factory identity and test results need a partition layout with
  `factory_data` (two copies + CRC) and recovery; the scaffold uses a single-app
  partition until that layout is frozen — see docs/46 for identity/CLI and
  docs/55 for labels.
- The first-build log (chip/PSRAM/CPU/IDF/I2C) is captured in the bring-up
  record `docs/43-p4-bringup.md` and the P1 result form (docs/56 §7).

## 6. First-build checklist (hardware day)

1. [ ] Install IDF 5.5+, `idf.py --version` ≥ v5.5; `idf.py set-target esp32p4` OK.
2. [ ] `idf.py build` → SUCCESS; record flash/RAM sizes.
3. [ ] PSU 5 V/3 A, current limit; P4 devkit HS USB-C to PC.
4. [ ] `idf.py flash monitor`; log `target=esp32p4`.
5. [ ] PSRAM = 32 MiB; CPU = 400 MHz; IDF version printed.
6. [ ] I2C scan on GPIO21/22: expected 8/8 with panel/PWR attached; 0 is OK bare.
7. [ ] I2C addresses match CORE-2 table; no bus errors at 400 kHz.
8. [ ] Heartbeat stable ≥10 min; free heap not dropping.
9. [ ] Then add engine component and rebuild; check no Arduino HAL dependency.
10. [ ] Then add esp_lcd RGB + esp_tinyusb + sdmmc + i2s and run P1 step 3.

## 7. Verification attempt in this environment

- Attempted on 2026-11-05 (started 23:18, macOS): `git clone --depth 1 -b v5.5
  --recursive https://github.com/espressif/esp-idf.git /tmp/esp-idf` with
  `IDF_TOOLS_PATH=/tmp/esp-tools`, followed by `./install.sh esp32p4`.
- **Result: not verified — attempt aborted at the 15–20 min budget.**  After
  ~15–20 min the shallow recursive clone had reached ~1.6 GB and was still
  cloning submodules (`components/esp_wifi/lib`, `esp_phy/lib`, NimBLE, etc.);
  `install.sh` (the ~1–2 GB toolchain download) was never reached and
  `idf.py build` was not run.  The background job was cancelled to keep the
  round bounded; no P4 build is claimed.
- The scaffold is valid by ESP-IDF 5.5 structure and the source is guarded for
  IDF 5.x APIs (`driver/i2c_master.h`, `esp_psram.h`, `esp_clk.h`,
  `esp_idf_version.h`); on a machine with ESP-IDF installed the acceptance
  command is exactly:
  `cd firmware/idf_p4 && idf.py set-target esp32p4 && idf.py build`.

## 8. Risks

1. **P4 support is young** (IDF 5.5+); API/config changes are likely — pin IDF
   version in CI and record it with every P1 run.
2. **Toolchain size/install time** (~2 GB, 20+ min on slow networks); keep a
   CI image/cache for the stand.
3. **PSRAM configuration** (in-package 32 MB) must match the module; a wrong
   `sdkconfig` silently gives 0/<32 MiB → the hello log catches it.
4. **USB HS/TinyUSB** is a managed component with P4-specific PHY config; not in
   the scaffold yet; UAC2 8×8 descriptors are ready (docs/05 / `uac2_8x8`) but
   enumeration must be validated on hardware.
5. **Display RGB/DSI** requires the correct panel driver and DMA/PPA path; the
   RGB565 backend is currently a host model (`display_rgb565`), not esp_lcd.
6. **C6 esp-hosted** (Wi-Fi/BLE over SPI) is a separate integration; P4 first
   SKU can ship without Wi-Fi/BLE if the P1 schedule demands it.

## 8. Проверенная сборка (06.11.2025, pole)

| Параметр | Значение |
|---|---|
| Хост | `pole` (Tailscale, 8 ядер, 30 ГБ RAM, RTX 3060), Ubuntu, python3.12 |
| ESP-IDF | **v5.5** (`git clone --depth 1 -b v5.5 --recursive`), tools через `install.sh esp32p4` |
| Python env | создан `virtualenv` в `~/.espressif/python_env/idf5.5_py3.12_env` (в системе нет `python3-venv`) |
| Target | `esp32p4`, custom board (CORE-2 пады) |
| Команда | `idf.py set-target esp32p4 && idf.py build` |
| Результат | **SUCCESS**: `bukifon_p4.bin` **250 240 B** (0x3e480), bootloader+table+app собираются, app-раздел 83 % свободен |
| Найдено и исправлено | `file(GLOB ... CONFIGURE_DEPENDS)` в `components/bukifon_engine/CMakeLists.txt` — недопустим в script-режиме IDF 5.5; заменено на обычный GLOB |
| Что дальше | прошить на P4 devkit: `idf.py -p PORT flash monitor`; ожидаемый лог: target=esp32p4, PSRAM 32 MiB, CPU 400 MHz, I2C-скан 8/8 |
| Повторить | `bash tools/home_offload.sh run "cd firmware/idf_p4 && idf.py build"` (после `sync`) |
