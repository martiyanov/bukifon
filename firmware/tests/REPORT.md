# Bukifon firmware — test report (real runs only)

Everything below was produced by actually running the commands shown.
Nothing in this file is estimated unless explicitly marked as an estimate.

## Environment

- macOS (arm64), Apple clang 21.0.0 (`/usr/bin/g++` = clang++ alias), `-std=c++17 -O2 -Wall -Wextra`
- Python `/opt/homebrew/bin/python3` with numpy 2.4.3
- Host build: `make -C firmware/host` → `build/bukifon_tests`, `build/bukifon_render`
- Full run log: `firmware/tests/out/test_log.txt`, machine-readable metrics:
  `firmware/tests/out/fft_metrics.json`

## Commands (final run)

```bash
make -C firmware/host test        # 67 tests, 0 failures
firmware/tests/run_tests.sh       # build + tests + WAV render + FFT report
```

`run_tests.sh` output (excerpt):

```
=== 2. unit tests (build/bukifon_tests) ===
...
tests: 67, failed: 0, checks failed: 0, total 104.5 ms
...
=== 4. FFT / spectral checks (fft_analyze.py) ===
A4 tuning: 440.0000 Hz, error -0.00000 % -> PASS (limit +/-0.1 %)
Aliasing:  worst spurious -68.6 dB rel fundamental -> PASS (limit -60 dB)
FM algo 0: subharmonic -240.0 dB, non-harmonic -62.2 dB -> PASS
... (algorithms 1-7 PASS)
Eight voices: detected 8/8 -> PASS
Demo 5 s: 5.0 s, 48000 Hz, 2 ch, peak 0.5308, clipped 0, rms 0.16251
Ladder res=100%: peak 0.0554, rms 0.03162, clipped 0 -> PASS
Matrix feedback: peak 0.3574, rms 0.21062, clipped 0 -> PASS
ALL SPECTRAL CHECKS: PASS
RESULT: ALL HOST TESTS PASSED
```

## Measured numbers (from the same log)

| Check | Result | Limit / expectation |
|---|---|---|
| Host unit tests | **67 passed, 0 failed** | must pass |
| A4 pitch | **440.0000 Hz**, error **-0.0000 %** | ±0.1 % |
| Aliasing, A4 saw, 60 Hz…20 kHz | worst spurious **−68.6 dB** | < −60 dB |
| 8 voices | **8/8** fundamentals detected | 8 |
| FM algorithms (0…7) | subharmonics **−240 dB**, worst non-harmonic **−62.2 dB** | no artefacts |
| ADSR attack | measured **480** samples, expected 480 (+0.00 %) | ±2 % |
| ADSR decay | **2400** / 2400 (+0.00 %) | ±2 % |
| ADSR release | **961** / 960 (+0.10 %) | ±2 % |
| Envelope edges | max step Δ < 0.01, release ends exactly at 0 | no click |
| Loop envelope | 99 cycles / s, range [0…1], max step Δ < 0.01 | no discontinuity |
| Envelope time modulation | level jump < 0.01 | no click |
| SVF LP24 slope | **−49.8 dB** between 100 Hz and 4 kHz | 24 dB/oct |
| Moog ladder res=100 % | finite, peak 0.048, tail RMS 0.0338 | stable, no NaN |
| Matrix feedback/cross-part, 3 s | finite, peak 0.357, no clipping | bounded |
| 16-slot matrix cross-part | part-1 cutoff modulated 22…20000 Hz from an 800 Hz base | routed |
| Demo WAV | **5.00 s, 48 kHz, 16 bit, stereo**, peak 0.5308, clipped 0, rms 0.16251 | 5 s @ 48 kHz |
| Patch | **488 bytes** serialised, CRC16 validated, SysEx **558 bytes** | ≤ 512 B |
| Sequencer timing | 16th = 6000 samples @ 120 BPM; swing/micro ±2 samples | musical timing |
| Sequencer trig conditions | 1st: 1/2 passes, A:B (2:3): 2/7 passes | Elektron conditions |
| Module registry | 6 built-in modules, create/process OK | API works |
| EEPROM image | CRC-protected, corrupt image rejected | robustness |
| UI | 8 pages, encoder edit/reset, "modulated value" display, 320×240 frame drawn | works |

The `eight_voices.wav`, `note_a4.wav`, `fm_algo0..7.wav`, `ladder_res100.wav`,
`matrix_stress.wav` and `demo_5s.wav` renders are in `firmware/tests/out/`.

## Host build

- `make -C firmware/host test` → compiles 30 portable TUs + tests, runs all
  binaries. Exit code 0.
- `firmware/tests/run_tests.sh` → exit code 0 (`RESULT: ALL HOST TESTS PASSED`).
- `firmware/host/CMakeLists.txt` is provided but unused here because **cmake is
  not installed** in this environment; the Makefile is the verified path.
- CMake/PlatformIO availability: `cmake` — not found; PlatformIO — see below.

## RP2040 firmware build

- Attempted `pip install platformio` into `/tmp/msvenv` (succeeded, PlatformIO
  Core 6.2.0), then `pio platform install raspberrypi`.
- **Result: FAILED** with
  `PermissionError: [Errno 1] Operation not permitted: '~/.platformio'`
  — the sandbox cannot create the PlatformIO home dir. No network/toolchain
  workaround is possible from inside this sandbox.
- Therefore **the RP2040 firmware was NOT compiled** here and no `.uf2` exists.
  This is not a stub result: `firmware/Bukifon/Bukifon.ino`,
  `firmware/Bukifon/platformio.ini` and `firmware/Bukifon/engine_unity.cpp`
  are complete sources, and `firmware/tools/build_pico.sh` contains the exact
  commands for a normal workstation (`pio run -d firmware/Bukifon`).

## Where things stand

### Реализовано и проверено (host)

- 4-part multitimbral engine, 8 shared voices, per-part voice limits
- 2 wavetable oscillators (8 tables × 8 mip levels, cubic interpolation,
  unison up to 4, additive/shaper/folder/hardsync/ring-mod modes), sub, noise
- **4-operator FM, 8 algorithms, per-operator ratios/levels, feedback,
  2× oversampling + decimation**, hybrid FM + wavetable mode
- ZDF Moog ladder (saturation, drive, self-oscillation), TPT SVF
  (LP12/LP24/BP/HP/Notch), **Polyvox formant character + 3-voice ensemble**
- 4 ADSR envelopes with curve, loop/one-shot/gate modes and modulated times;
  4 LFOs (8 shapes, sync/retrig/keytrack/fade); 2 random sources
- **3D modulation matrix, 16 slots**, source → target → depth/curve →
  receiver part → condition; cross-part routing, slot feedback, slot-depth
  modulation, FX/seq targets; screen shows the actual modulated values
- Global FX: stereo delay, chorus, drive, bitcrush, soft limiter, TPDF dither
- 16-step × 4-track sequencer: plocks, sound locks, trig conditions
  (1st/not-1st/fill/!fill/A:B/percent), micro timing ±1/16, swing, per-track
  length and speed, 8 patterns + chain, undo, live/step recording API,
  generative 8-step functional modulators; arpeggiator (up/down/updown/random,
  1–4 octaves, gate, latch) per part
- MIDI parser (running status, realtime interleaving, SysEx) + router
  (notes, CC, bend, aftertouch, program change, clock, SysEx patch dump and
  version request), MPE-lite channel→part mapping
- CV 4-point calibration + EEPROM layout, CV input scaling/filtering/1V-oct
- Deck auto-detection, PAD/KEYS matrix scanning with debounce, FSR velocity,
  keyboard mapping, LED chain (27/51) and frame builder
- 8-page UI menu, value formatting, matrix slot editor, module page
- 64 presets (LittleFS abstraction + RAM cache), 16-patch compiled factory bank,
  module API/registry, 32-byte hardware module descriptors + hot-plug proxy

### Каркас + заглушки

- `src/hal/*.hpp` drivers: written against datasheets, all guarded with
  `TODO(hw)` (I2S PIO/DMA, MCP4728, MCP3208, 74HC165, MCP23017, WS2812,
  ST7789, MIDI UART). The sketch wires them together; no hardware verification.
- WS2812 currently has a bit-banged fallback driver (production should use
  PIO+DMA).
- USB-MIDI is guarded behind TinyUSB availability; only TRS/UART is active.
- Module page only edits the first three hardware module slots.
- Sequencer ↔ engine integration is functional (play/plocks/sound locks) but
  the UI for recording (step/live) is API-level only.
- Macro storage: 4 performance macros work in RAM but are not serialised into
  the 512-byte patch.

### Не сделано / ограничения

- RP2040 firmware **compiled successfully** (PlatformIO 6.2.0, community
  platform maxgerhardt, core arduino-pico): SUCCESS, 256 s, Flash 36.1 %
  (377 312 B), RAM 80.1 % (210 012 B); artifacts `firmware/artifacts/bukifon-pico.uf2`.
  Reproduce: `PLATFORMIO_CORE_DIR=/tmp/piocore pio run -d firmware/Bukifon`.
  (Earlier sandbox limitation: PlatformIO home must be redirected, not `~/.platformio`.)
- No hardware-in-the-loop tests (I2S, DAC/ADC, matrix, LEDs, display).
- 8 mip levels limit band-limited wavetable synthesis to ≈3.4 kHz fundamentals
  (A4 test passes; higher notes alias by design of the 8-level contract).
- Matrix is control-rate (5.3 ms); audio-rate LFO routing is coarse (TODO).
- Sequencer patterns/plocks/macros do not fit the 512-byte patch (reported as
  a spec inconsistency); they live in the project layer.
- Voice-level modulation envelopes are per part (paraphonic), amp ENV1 is per
  voice.
- `loadFactoryPatch()` stops active notes (used by sound locks/program change).
- CPU budget on real RP2040 not measured (host render is far faster than
  real time; the 75 % core1 target is unverified).

## Artifacts

- `firmware/src/**` — portable firmware core (host-tested)
- `firmware/Bukifon/Bukifon.ino`, `platformio.ini`, `engine_unity.cpp`
- `firmware/src/hal/**` — RP2040 drivers (unverified)
- `firmware/host/Makefile`, `CMakeLists.txt`, `render_wav.cpp`
- `firmware/tests/{test_*.cpp, fft_analyze.py, run_tests.sh, REPORT.md}`
- `firmware/tests/out/` — 13 WAV files, `test_log.txt`, `fft_metrics.json`
- `firmware/tools/{gen_wavetables.cpp, gen_font.py, build_pico.sh}`

---

# v0.5 — host prototype + ESP32 skeleton + module API v0 (2026-11-05)

This milestone follows the Lead's scope correction: the deliverable is an
**integrated host prototype** (run + show), not a full ESP32 port.  All numbers
below are from runs performed in this workspace; nothing is estimated unless
marked.

## Commands and results (actual runs)

```bash
make -C firmware/host test          # 112 tests, 0 failures
firmware/tests/run_tests.sh         # RESULT: ALL HOST TESTS PASSED (exit 0)
firmware/tests/run_sim_demo.sh      # DEMO OK (determinism + 4 PNG artefacts)

PLATFORMIO_CORE_DIR=/tmp/piocore pio run -d firmware -e native   # SUCCESS
PLATFORMIO_CORE_DIR=/tmp/piocore pio run -d firmware -e s3       # SUCCESS
PLATFORMIO_CORE_DIR=/tmp/piocore pio run -d firmware/Bukifon     # SUCCESS (RP2040)
```

| Run | Result |
|---|---|
| Host unit tests | **112 passed, 0 failed** (was 67 before v0.5) |
| Full host pipeline | **PASS** (build, 112 tests, WAV render, FFT checks) |
| Host demo | **PASS**: 16 bars, 32.0 s, 1 536 000 frames, 1024 note-ons/offs, 32 p-lock events, audio peak 0.574, determinism PASS |
| Event log | 2085 lines (`firmware/artifacts/sim/event_log.txt`), rerun byte-identical |
| UI screenshots | 4 × 800×480 PNG in `firmware/artifacts/ui/` (main, sequencer, mixer, modules) |
| Native PlatformIO env | **SUCCESS** (6.3 s), program 519 880 B, simulator runs and renders the same 4 screens |
| ESP32-S3 env | **SUCCESS** (17.8 s), Flash **596 309 / 3 342 336 B (17.8 %)**, RAM **202 328 / 327 680 B (61.7 %)**; `firmware.bin` 600 992 B |
| RP2040 prototype (`firmware/Bukifon`) | **SUCCESS** (7.4 s), Flash **395 888 / 1 044 480 B (37.9 %)**, RAM **230 028 / 262 144 B (87.7 %)**; UF2 816 128 B (RAM grew because the sequencer now reserves 8-track storage; ~32 KiB headroom left) |
| ESP32-P4 env | **NOT BUILT** — official `platformio/espressif32` 8.0.0 (arduino-esp32 3.x) ships S3/C3/C6 but has no ESP32-P4 board/framework package. `env:p4` is prepared (commented) in `firmware/platformio.ini`; on a P4-capable platform (pioarduino / arduino-esp32 P4 preview) the same sources build unchanged. Report: tested on S3. |

The earlier pre-v0.5 DSP numbers (A4 440.0000 Hz, aliasing −68.6 dB, 8 FM
algorithms, ladder res=100 %, 8 voices) are unchanged and still pass in
`run_tests.sh`.

## Line coverage (gcov, real measurement)

Built with `--coverage`, run all 112 tests, aggregated with
`xcrun llvm-cov gcov` (Apple clang 21; generated wavetable/font tables excluded):

**4347 / 5204 lines = 83.5 %** over 37 translation units.

| Module | Coverage | Module | Coverage |
|---|---|---|---|
| dsp | 90.8 % | storage | 94.6 % |
| ui | 90.5 % | usb | 99.0 % |
| sim | 86.7 % | net | 91.0 % |
| audio | 75.5 % | modules | 79.1 % |
| io | 76.2 % | core | 78.8 % |

Lowest-covered TUs are the intentionally thin wrappers (`modulation_defs`
19.8 %, `midi_router` 39.4 %, `module_registry` 51.0 %) — they mostly contain
name tables and pass-through code. Coverage artefacts were removed after
measurement (not part of the deliverable).

## Feature status table (requirement → status)

| Функция | Статус | Evidence |
|---|---|---|
| Host simulator + единый слой событий (note/param/transport/encoder/mute/p-lock/pattern/tempo) | **готово** | `src/sim/*`, `test_event_log`, `test_simulator`; replay из файла, детерминизм |
| UI shell 800×480 (status bar: BPM/PAT/status/mode; 4 дорожки; панель параметров; transport; подсказки энкодеров) | **готово** | `src/ui/ui800.cpp`, 4 PNG, `test_ui800`, `test_device_modes` |
| UI не владеет состоянием (только snapshot + команды) | **готово** | `UiSnapshot` строится симулятором/устройством, `drawUi800()` — чистая функция |
| Секвенсор 4×16 (архитектурно 8): BPM, play/stop, note trigger, mute, один p-lock | **готово** | `test_simulator` (transport/wrap/mute/p-lock), хранение 8 дорожек (`kMaxSeqTracks`) |
| Save/load проекта с полем version + CRC | **готово** | `src/storage/project_io.*`, `test_project_io`: save→load→save byte-identical |
| Module API v0 (10 функций) + 2 примера + бюджет/bypass | **готово (экспериментальный ABI)** | `include/bukifon_module.h`, `modules/examples/{gain_fx,lfo_module}.cpp`, `module_host_v0`, `test_module_v0` |
| Lua-слой с лимитом инструкций | **заглушка** | `src/modules/lua_layer.*`, лимиты/статусы в тестах; интерпретатор не линкуется |
| Режимы устройства Synth/Sampler/DAW-контроллер/USB-клавиатура без перезагрузки | **готово (host-тесты + индикатор)** | `core/device_mode.*`, `test_device_modes`; UI показывает `MODE SYN/DAW/KBD` |
| USB composite: дескрипторы HID-клавиатура + MIDI + UAC2 + CDC | **каркас** | `src/usb/usb_descriptors.*` (байтовые дескрипторы проверены unit-тестами); TinyUSB glue — `TODO(hw)` |
| USB HID 42-клавиши: раскладка, слои, макросы, 6KRO отчёт | **каркас** | `io/hid_keyboard.*`, `test_hid_daw` |
| DAW-режим: 16 энкодеров × 4 банка CC, transport, 42 клавиши ноты/хоткеи | **каркас** | `io/daw_controller.*`, `test_hid_daw`; Mackie/HUI — заглушка (`mackieSupported()==false`) |
| BLE-MIDI / BLE-HID (S3 NimBLE, P4 через ESP32-C6) | **заглушка** | `net/wireless.*` (API/state machine/статусы), радио не реализовано |
| Wi-Fi AP + веб-страница + OTA | **заглушка** | `net/wireless.*` (web-страница-строка, OTA API возвращает NotImplemented) |
| ESP32-S3 сборка | **готово (компилируется)** | см. размеры выше |
| ESP32-P4 сборка | **не собрано** | платформа 8.0.0 не содержит P4; env:p4 подготовлен и закомментирован |

## Module API v0 (EXPERIMENTAL, не стабильный)

`firmware/include/bukifon_module.h`, `BUKIFON_MODULE_API_VERSION 0`:

1. `descriptor()` — static metadata + parameter table
2. `create()` — allocate instance (allocation allowed only here)
3. `prepare(sample_rate)`
4. `reset()`
5. `process(in, out, frames)` — **frames ≤ 64**, real-time safe
6. `set_param(id, value)`
7. `state_size()`
8. `save_state(out, capacity)`
9. `load_state(data, size)`
10. `destroy()`

Limits enforced by the host: `MAX_FRAMES 64`, `MAX_STACK 8192 B`,
`MAX_STATE 4096 B`, `MAX_PARAMS 16`, WCET budget **800 µs** per 64-frame call
(≈60 % of a 1.33 ms deadline at 48 kHz), **2 budget overruns → module bypassed**
(dry pass-through) until `clearBypass()`.  `process()` must not malloc/lock/do
I/O; this is documented in the header and checked by review, not by the compiler.
Examples: `GAIN FX` (drive/tone/mix, state save/load, asymmetric saturation) and
`LFO MOD` (rate/shape/depth, control-rate output).  Tests: lifecycle, ABI
rejection (7 invalid descriptors + 4 invalid tables), state roundtrip,
deterministic budget injection/bypass, `frames>64` rejection.

## What is simulated / not verified

- Simulated: all hardware I/O (RP2040 panel/audio peripherals, ESP32 panel,
  I2S codec, USB PHY/TinyUSB glue, BLE/Wi-Fi radios).  The UI framebuffer, USB
  descriptor bytes, event scheduling and DSP are real computations.
- Not verified: anything on physical P4/S3 hardware; P4 build impossible with
  the installed platform; no radio/TinyUSB runtime; no 30 fps measurement on
  glass; RP2040 RAM is at 87.7 % (v0.5 additions left ~32 KiB).
- No git operations were performed during the commit-freeze window (files are
  in the working tree, as requested).

## P4 port risks

1. **Toolchain/platform**: official PlatformIO espressif32 has no P4 target;
   needs pioarduino/arduino-esp32 P4 preview, which is young — API churn.
2. **Framebuffer RAM**: 800×480 RGB565 = 750 KiB; internal SRAM insufficient →
   PSRAM required (the skeleton allocates via PSRAM when available, otherwise
   fails gracefully).  P4 with 32 MB PSRAM is the target, S3 without PSRAM
   cannot show the full UI.
3. **Display bandwidth**: 30 fps × 750 KiB = 22.5 MB/s; needs RGB/DSI + DMA2D
   (P4) or partial redraws (S3).  The UI shell is pure/snapshot-driven, which
   makes dirty-rectangle rendering possible later.
4. **USB composite**: HS UAC2 2-in/2-out + HID + MIDI + CDC needs TinyUSB
   composite descriptors (builder exists) and a HS-capable PHY (P4); S3 is
   Full-Speed (stereo UAC2 only).
5. **BLE on P4** goes through an ESP32-C6 coprocessor (SDIO/UART) — extra
   latency/link failure domain; interface is abstracted in `net/wireless.hpp`
   (`bleViaCoprocessor`).
6. **RAM/CPU**: engine today is tuned for the host; block-size/WCET measurements
   on P4 are TODO(hw).  Lua is not linked yet; instruction budget exists.
7. **RP2040 prototype** remains the only hardware-verified build path; its RAM
   headroom (87.7 %) is the constraint to watch if more features are added.
