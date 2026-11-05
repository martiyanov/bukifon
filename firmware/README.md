# Bukifon firmware

Open firmware for **Bukifon** — a modular handheld synth/gamepad.

v0.5 adds the **ESP32-P4/S3 path** (800×480 UI, device modes, USB/BLE/Wi-Fi
frameworks) on top of the RP2040 prototype.  The verified, runnable artefact of
this milestone is the **host prototype**: deterministic simulator + 800×480 UI
screenshots + sequencer vertical slice + save/load + experimental Module API v0.
The ESP32-S3 firmware skeleton compiles; ESP32-P4 is prepared but not buildable
with the installed PlatformIO platform (see «Build status»).

**License: GPL-3.0-or-later** (every source file carries an SPDX header).
Specification: `spec/40-firmware.md`, `spec/10-panel-ui.md`, `spec/20-electronics.md`.

---

## What is here

```
firmware/
  src/core/     parameters (4 parts x 91 + 32 global), patch format (488 B), events
  src/dsp/      wavetables (generated), 2x oversampled 4-op FM (8 algorithms),
                ZDF Moog ladder / TPT SVF / Polyvox formant filter, ensemble,
                ADSR + loop envelopes, LFOs, effects (delay/chorus/drive/crush/limiter)
  src/audio/    4 independent parts (Kaleidoscope-style 3D matrix), 8 shared
                voices, multitimbral engine (Kaleidoscope/Elektron hybrid)
  src/io/       MIDI parser+router, encoders, deck scanner, CV calibration,
                WS2812 LED model, 16-step sequencer (plocks, conditions,
                micro timing, swing, generative modulators), arpeggiator
  src/modules/  IModule API + static registry + hardware module descriptors/proxy
  src/storage/  64 presets on LittleFS (RAM cache), 24C32 EEPROM (CV cal, deck
                cal, module table, hours), factory bank of 16 patches
  src/ui/       8-page encoder menu rendered through a portable ICanvas,
               "actual modulated value" display, generated 6x8 font
  src/hal/      RP2040 drivers (i2s_pio, mcp4728, mcp3208, hc165, mcp23017,
                ws2812, st7789, midi_uart, pinmap) + ESP32 HAL seam
  src/sim/      deterministic host simulator + replayable event log
  src/usb/      USB composite descriptor builder (HID + MIDI + UAC2 + CDC)
  src/net/      BLE-MIDI/HID and Wi-Fi AP/web/OTA framework (stubs)
  include/      bukifon_module.h — Module API v0 (EXPERIMENTAL, unstable)
  modules/      two example modules implementing API v0 (gain FX, LFO)
  app/          sim_main.cpp (host demo/screenshots), esp32_main.cpp (skeleton)
  platformio.ini  ESP32-S3 + host(native) project (separate from RP2040)
  engine_unity.cpp / sim_unity.cpp  PlatformIO unity translation units
  Bukifon/      RP2040 Arduino sketch: Bukifon.ino + platformio.ini
  host/         native build (Makefile + CMakeLists.txt), WAV renderer
  tests/        unit tests (311), FFT analysis, run_tests.sh, run_sim_demo.sh, REPORT.md
  tools/        wavetable/font generators, ppm_to_png.py, build_pico.sh
  artifacts/    generated 800x480 UI screenshots + demo logs (git-ignored)
```

## v0.5 host prototype — what to run

```bash
make -C firmware/host test          # 311 unit tests
firmware/tests/run_tests.sh         # build + tests + WAV render + FFT report
firmware/tests/run_sim_demo.sh      # 16-bar demo, event-log determinism, 4 PNG
```

The demo builds the pattern, plays **16 bars** (32 s at 120 BPM), writes a
deterministic event log and renders four 800×480 UI screens:

![main](artifacts/ui/main.png)
![sequencer](artifacts/ui/sequencer.png)

Screens: [main](artifacts/ui/main.png) · [sequencer](artifacts/ui/sequencer.png) ·
[mixer](artifacts/ui/mixer.png) · [modules](artifacts/ui/modules.png)
(status bar with BPM/patch/status/mode, 4 track strips, parameter panel,
transport row, encoder hints).  Measured: 1024 note-on/off events, 32 p-lock
events, audio peak 0.574, two runs produce byte-identical logs.

New in v0.5 (all host-tested):

| Feature | Status |
|---|---|
| Device modes Synth / Sampler / DAW-controller / USB-keyboard, switching without reboot, UI indicator | ready (host-tested) |
| USB composite descriptor builder: HID keyboard (42 keys, layers, macros) + MIDI + UAC2 + CDC | framework (descriptors unit-tested; TinyUSB glue TODO(hw)) |
| DAW mode: 16 encoders × 4 CC banks, transport, keys as notes/hotkeys | framework (Mackie/HUI stub) |
| BLE-MIDI / BLE-HID (S3 NimBLE, P4 via ESP32-C6), Wi-Fi AP/web/OTA | stubs with API + state machine + tests |
| Module API v0 (`include/bukifon_module.h`, 10 functions, 2 examples, WCET budget + 2-overrun bypass), Lua layer stub | ready (EXPERIMENTAL ABI) |
| Versioned save/load with CRC (patterns, mutes, p-locks, chain) | ready, deterministic test |
| 800×480 snapshot-driven UI, PPM→PNG pipeline | ready |

Module API v0 is **experimental and unstable** (see the header warning): v0.5 is
a design probe for the P4 firmware, not an SDK promise.

## Host build and tests (fully verified)

The portable engine has **no Arduino dependencies** and is tested natively:

```bash
make -C firmware/host test          # build + run unit tests
firmware/tests/run_tests.sh         # full pipeline: build, tests, WAV render, FFT report
```

Latest measured results (see `tests/REPORT.md` and `tests/out/test_log.txt`):

- **311 unit tests, 0 failures** (Apple clang 21, C++17, `-O2`)
- line coverage **83.5 %** (4347/5204 lines, gcov, generated tables excluded)
- host demo: 16 bars, 1024 note-ons, 32 p-locks, deterministic event log, 4 PNG screens
- A4 = **440.0000 Hz** (error `-0.0000 %`, limit ±0.1 %)
- aliasing (worst spurious in 60 Hz…20 kHz): **−68.6 dB** (limit −60 dB)
- all **8 FM algorithms**: no subharmonics (−240 dB), worst non-harmonic −62.2 dB
- **8 voices** detected in the rendered chord (8/8)
- **5.00 s / 48 kHz / 16 bit / stereo** demo WAV, 0 clipped samples
- Moog ladder at resonance 100 %: stable, peak 0.055, RMS 0.0316
- 16-slot matrix with feedback + cross-part routing: stable, peak 0.357
- ADSR timings: attack 480/480 samples, decay 2400/2400, release 961/960 (+0.10 %)

Rendered WAVs and `fft_metrics.json` land in `firmware/tests/out/`.

## Firmware build (RP2040) — собрано и проверено

```bash
# 1. PlatformIO в отдельном venv (пример)
python3 -m venv /tmp/pio-venv && /tmp/pio-venv/bin/pip install platformio

# 2. Сборка (важно: PLATFORMIO_CORE_DIR — песочница не пишет ~/.platformio)
export PLATFORMIO_CORE_DIR=/tmp/piocore
/tmp/pio-venv/bin/pio run -d firmware/Bukifon

# 3. Готовый образ
#    firmware/Bukifon/.pio/build/pico/firmware.uf2
#    -> копия: firmware/artifacts/bukifon-pico.uf2  (764 KiB)
```

`platformio.ini`: `env:pico`, `board = pico`, `framework = arduino`,
`board_build.core = earlephilhower`, платформа — community
`https://github.com/maxgerhardt/platform-raspberrypi.git`
(официальная `platform = raspberrypi` не содержит core arduino-pico и падает на
`Arduino.h: No such file`). `Bukifon/engine_unity.cpp` включает портируемые
`src/*.cpp`, т.к. PlatformIO компилирует только файлы внутри проекта скетча.

**Результат сборки 05.11.2025 (PlatformIO Core 6.2.0, arduino-pico, GCC ARM):**

| Параметр | Значение |
|---|---|
| Статус | **SUCCESS** (256 с, полный цикл с загрузкой core) |
| Flash | 395 888 B / 1 044 480 B — **37.9 %** |
| RAM | 230 028 B / 262 144 B — **87.7 %** |
| Артефакты | `firmware/Bukifon/.pio/build/pico/firmware.uf2` (816 KiB), `.elf` |
| Host-тесты | **112/112** после сборки (регрессий нет) |

RAM 87.7 % — запас ~32 KiB; при добавлении эффектов/модулей оптимизировать
буферы (delay-линия, пресет-кэш, 8-дорожечный секвенсор) или перенести часть в
PSRAM (RP2350).

## Round 15 — voice as input: MIC

- **MIC page** (7th tab): MIC ON/MUTED privacy banner, SOURCE LINE/MIC, GAIN,
  THRESH, MONITOR, BEATBOX+SENS, REC→PAD, LEVEL meter; 16-cell mirror.
- **Engine** `src/io/mic.*`: capture/VAD model, ≤30 s voice take with silence
  auto-trim, beatbox onset→kick/snare/hat steps (UNDO, ≥80 % at 90–140 BPM),
  mute switch+LED, no implicit BLE/Wi-Fi transmission.
- Screenshot `artifacts/ui/mic.png`; TODO(hw) in docs/71 §9.

## Round 14 — external MIDI sequencer v1.0-rc

- **8 external MIDI tracks** (`src/io/ext_sequencer.*`): ch 1–16, PC,
  note/vel/length, 1 CC p-lock/step, mute, GEN (prob/Euclid/mutate/scale/ARP),
  shared transport, clock out 24 ppqn + clock-in slave, live record with
  quantization, versioned CRC32 payload; DIN+USB router model without duplicates.
- **EXT page** (6th tab): 8 rows T1 CH1 PC0, 16-step grid, CH/PROG/VEL/LEN/CC#/
  CC VAL/SWING/CLK + macros, p-lock/mute marks; screenshot `artifacts/ui/ext.png`.
- `docs/70` §7–8 implementation/TODO(hw).

## Round 13 — UI readability (docs/68/69)

- **16 encoder cells** (2×8): left 4 columns page params А–З, right 4 macros
  И–П (CUT/RES/ATK/REL/DLY/DRV/CRSH/MST), label `А · CUTOFF`, 18 px value,
  slider; mirror mapping API.
- **Typography roles** from docs/69: Caption 12 px, Value 18 px, Critical
  24 px (BPM/STEP/REC), Title 26 px; no text <12 px in ui800.
- **Context line** PART·SELECTED·PAGE·FADERS·REC·UNSAVED always visible;
  HOME returns to MAIN; 12 px page tabs; Cream palette AA-contrast updated.
- Screenshots: `artifacts/ui/synth.png`, `gen.png` (9 PNG total).

## Round 11 — GEN functions + GEN page + presets

- GEN engine (`src/io/gen.*`): deterministic PROB/EUCLID/MUTATE/SCALE LOCK/
  EVOLVE/SEED + ARP (1/8,1/16,1/32 × UP/DOWN/UPDOWN), applied per sequencer
  step; neutral defaults keep old projects unchanged.
- 5th UI tab **GEN** (ui800) with 8 function fields, Euclid ring, preset slots
  (8, host file; P4 NVS TODO), A/B compare, multi-select group edit and a
  mod-visible **M** marker; screenshot `artifacts/ui/gen.png`.
- `docs/66-ux-implementation.md`: docs/65 UX pattern → implementation → test.

## Round 10 — UI palette tokens in firmware

- `include/bukifon_ui_theme.h` + `src/ui/ui_theme.cpp`: 4 frozen themes
  (Night/Amber/Phosphor/Cream) × 12 tokens exactly from
  [docs/62-screen-palette.md](../docs/62-screen-palette.md), default Night;
  `ui_theme_set()`/C++ helpers + host settings file (device NVS TODO(hw)).
- `src/ui/ui800.cpp` (SYNTH + 4 device modes) and `src/ui/menu.cpp` render only
  through tokens (no raw colours; host test enforces it); track colours follow
  green/orange/blue/purple.  Demo CLI: `bukifon_sim --theme Cream`.

## Round 9 — serials/QR labels + factory identity

- **Labels**: `tools/make_labels.py` (CSV → `dist/labels/labels_<batch>.pdf`,
  A4 3×8 / 60×30 mm, QR, manifest, `--preview` PNG, duplicate-SN validation,
  `--selftest`).  Dev sheet: `dist/labels/labels_26A.pdf` + preview; rules in
  [docs/55-labels-traceability.md](../docs/55-labels-traceability.md).
- **Identity**: `src/factory/identity.*` — 114-byte record (serial/revs/date/
  batch/MAC/calibration/CRC32), validator, two-slot store, CLI
  `factory --identity <json>` / `--print-identity`; real flash/24C32 write is
  TODO(hw).

## Round 8 — UAC2 8×8 HS + RGB565 + factory backend hooks

- **USB HS UAC2 8×8** (`src/usb/uac2_8x8.*`): 300 B config, 8 interfaces,
  **9/15 endpoints** (2 ISO + feedback + MIDI 2 + CDC 3 + HID 1); per-channel
  16 ISO layout = 23/15 → impossible, mitigation ≤4 channels or UAC2 channel
  aggregation; JSON dump for the analyser: `make -C firmware/host usbdump` →
  `firmware/artifacts/usb/uac2_8x8.json`.
- **RGB565 display backend** (`src/hal/display_rgb565.*`): full/partial flush,
  dirty rects, 16-row bounce; P4 model **52.08 full fps / 130.21 partial**
  (host simulation; esp_lcd/PPA = TODO(hw)).
- **Factory real/mock hooks** (`src/factory/hw_backends.*`):
  `BUKIFON_HW_{I2C,ADC,DAC,I2S,SD,DISPLAY,USB,CONTROLS,CV,MIDI}`; all-MOCK
  14/14 PASS, all-REAL stubs 14/14 FAIL (no fabricated PASS); bench order in
  [docs/46 §9](../docs/46-factory-test.md).

## Platform priority: P4 first, S3 lite later

**Round 7 — P4 HAL + factory self-test:** `src/hal/board_cores2.*` (CORE-2,
55 GPIO from `hardware/core2/pinmap.csv`) and `src/factory/selftest.*` (14
docs/42 tests, timeouts, JSON, CLI).  Host: `make -C firmware/host factory` →
14/14 PASS mock (38 s nominal; EOL 2–2.5 min), report in
`firmware/tests/out/factory_report.json`; protocol in
[docs/46-factory-test.md](../docs/46-factory-test.md).  `env:p4` is prepared but
**not buildable** (official espressif32 8.0.0 has no P4 board/framework) — no
false SUCCESS; display/I2S/C6 and P4 hardware access are explicit TODO(hw) stubs.

The customer decision is that the **first SKU is P4 with RGB565/DSI + HS USB**;
S3-base is the "lite later" concept platform.  The 800×480 UI and the four
device-mode panels are **identical for P4 and S3-lite** — only the display
backend (RGB565/DSI vs SPI) and USB PHY (HS 8×8 vs FS stereo) differ.

- **P4 profile in bench**: `make -C firmware/bench host_p4` →
  `firmware/bench/results/host_p4.json` (8 voices + 8 stereo tracks, 750 KiB
  RGB565 + bounce, HS USB 8×8 UAC2, max block ≤650 µs, 24 h soak target).  P4
  build itself is still blocked by the missing PlatformIO P4 platform (honest).
- **S3 vertical-slice spike (lite concept)**: `firmware/spike_s3/` — standalone
  env `spike_s3` (builds: Flash 6.6 %, RAM 20.4 %) for the devkit spike
  (audio/display/SD/USB/panel metrics + docs/36 pass/fail), protocol in
  [docs/39-s3-spike-protocol.md](../docs/39-s3-spike-protocol.md).  I2S/TinyUSB/
  panel-init remain explicit `TODO(hw)` stubs; no hardware results yet.

## S3-base firmware (CORE-S3 rev.0, ESP32-S3-N16R8)

```bash
PLATFORMIO_CORE_DIR=/tmp/piocore pio run -d firmware -e s3base   # SUCCESS, see REPORT.md
firmware/tests/run_sim_demo.sh    # 8 screenshots: 4 pages + 4 device modes
```

Board HAL `src/hal/board_cores3.*` follows `hardware/cores3/pinmap.csv` (SPI2 800×480,
1-bit SDMMC, I2S0, I2C0, MIDI UART1, USB FS, BL_PWM).  Measured build: Flash 11.3 %
(16 MB module, 6.25 MB app partition), RAM 62.7 %.  Display/I2S/SD/USB data paths are
explicit `TODO(hw)` — the HAL compiles and reports status, nothing is claimed as
hardware-verified.  D-51 risk: modelled SPI full refresh is 13 fps (< D-46's 15).

Device modes have their own UI panels (status-bar `MODE`): see
[artifacts/ui/synth.png](artifacts/ui/synth.png),
[sampler.png](artifacts/ui/sampler.png), [daw.png](artifacts/ui/daw.png),
[usb_kbd.png](artifacts/ui/usb_kbd.png).  Module API v0.1 adds host services
(time/log), note/gate/transport events and host-side parameter smoothing; ABI major 0
stays backward compatible — see `docs/24-module-sdk.md` and the new examples
`grain_fx.cpp`, `svf_filter.cpp`.

## P1 benchmark (frozen workload, host + devkit harness)

```bash
make -C firmware/bench host     # frozen workload on host -> bench/results/host.{json,csv}
make -C firmware/host test      # 120 tests (includes bench determinism/no-alloc/criteria)
```

Workload freeze: [docs/05-benchmark-workload.md](../docs/05-benchmark-workload.md);
devkit howto: [docs/05a-benchmark-howto.md](../docs/05a-benchmark-howto.md);
harness: [bench/README.md](bench/README.md).  Envs: `bench`/`bench_s3` build,
`bench_p4`/`bench_h743` are prepared (P4 platform / ststm32 not available here).
S3-lite profile: `make -C firmware/bench host_s3` → `bench/results/host_s3.json`
(SPI 13.02 fps full <15 — D-51, so S3-lite uses partial redraw; RGB model
52.08 fps, USB FS stereo 0.288 MB/s).  P4 profile: `host_p4` (RGB565 52.1 fps,
HS USB 8×8 2.304 MB/s).
Host reference worst audio max is 218 µs (16.4 % of the 1.333 ms deadline,
2.98× below the 650 µs criterion); device runs decide P4 vs H743.

## ESP32-P4 / S3 build (v0.5 skeleton)

```bash
export PLATFORMIO_CORE_DIR=/tmp/piocore    # sandbox: ~/.platformio is read-only
pio run -d firmware -e native              # host build (simulator + screenshots)
pio run -d firmware -e s3                  # ESP32-S3 skeleton
# P4: not available in official espressif32 8.0.0 — see env:p4 notes below
```

| Target | Result |
|---|---|
| `native` | SUCCESS, program 519 880 B, same 4 screenshots rendered |
| `s3` (ESP32-S3-DevKitC-1) | SUCCESS, Flash 596 309 / 3 342 336 B (17.8 %), RAM 202 328 / 327 680 B (61.7 %) |
| `p4` | **not built**: PlatformIO espressif32 8.0.0 (arduino-esp32 3.x) has no ESP32-P4 board/framework. `env:p4` is prepared and commented in `firmware/platformio.ini`; on a P4-capable platform (pioarduino / arduino-esp32 P4 preview) the same sources build. |
| RP2040 prototype `firmware/Bukifon` | SUCCESS (unchanged project, rebuild verified) |

The S3/P4 sketch wires the portable engine + 800×480 UI + device modes +
USB/BLE/Wi-Fi frameworks.  Hardware-specific parts are explicit `TODO(hw)`
(`app/esp32_main.cpp`, `src/hal/esp32_hal.hpp`); see the status table above.

## Hardware map (updated contract)

`src/hal/pinmap.hpp`: MIDI GP0/GP1, SPI0 GP2–GP6, WS2812 GP7, I2C0 GP8/9,
ST7789 SPI1 GP10–GP15, I2S GP16/17/18, bus CS GP19–21, **GATE1 = GP22**,
**GATE2 = GP26**, **DECK_ID = GP27 (ADC1)**, **DECK_INT = GP28**.
Audio: PCM5102A via PIO+DMA, 48 kHz, 16 bit, double buffer 2 × 256 frames.

## What is real and what is not

**Implemented and host-verified** (numbers above): DSP engine, 4-part
multitimbral voicing, 4-op FM, Moog/SVF/Polyvox filters, ensemble, envelopes
(incl. loop mode and time modulation), LFOs, 16-slot 3D matrix with cross-part
routes and feedback, sequencer (plocks, sound locks, trig conditions, micro
timing, swing, per-track length/speed, pattern chain, undo, generative step
modulators), arpeggiator, MIDI parser/router incl. SysEx patch dump, CV
calibration, deck/key mapping, LED model, presets/EEPROM, module API/registry,
hardware-module descriptor parsing, 8-page UI, patch format (488 B, CRC16).

**Written but not hardware-verified** (explicit `TODO(hw)` in `src/hal/`):
I2S PIO/DMA, MCP4728, MCP3208, 74HC165, MCP23017, WS2812 (bit-bang fallback
driver included; production should use PIO+DMA), ST7789 init sequence, TRS/UART
MIDI, USB-MIDI (needs TinyUSB core option and the Adafruit TinyUSB library).

**Known limitations / deviations reported to the Lead:**
- 4 envelope generators are per-part modulation sources (paraphonic, like many
  vintage polysynths); the amplitude envelope ENV1 is per voice.
- Matrix is evaluated at control rate (one block, 5.3 ms) — a 2 kHz LFO routed
  through the matrix is therefore sampled coarsely; direct per-sample routing
  is future work.
- 8 wavetable mip levels band-limit notes up to ≈3.4 kHz; above that the table
  cannot stay below Nyquist (contract fixes 8 levels). The A4 test passes.
- Patch is 488 B (timbre + matrix). Elektron-style sequencer data does not fit
  into the 512-byte patch limit, so patterns/plocks/sound-locks and the 4
  performance macros are kept in the project layer (reported as a spec
  inconsistency).
- Patch values are quantised to 8 bit (≤1/255 of range); SysEx dump ≈558 B.
- Parameter locks are limited to 8 per step in RAM; the editor and sequencer
  support them, but they are not serialised into the 512-byte patch.
- `loadFactoryPatch()` resets active voices (used for sound locks/program change).
- v0.5: TinyUSB composite glue, NimBLE, Wi-Fi AP/web/OTA are stubs; Module API v0
  is experimental; Mackie/HUI is a stub.  ESP32-P4 cannot be built with the
  installed PlatformIO platform (evidence and switch instructions in
  `tests/REPORT.md`).
- UI screenshots and demo logs live in `firmware/artifacts/` (git-ignored by the
  repository policy for generated artefacts; reproducible with
  `firmware/tests/run_sim_demo.sh`).
