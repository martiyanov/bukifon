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

---

# P1 benchmark (task-17, 2026-11-05)

Frozen workload: [`docs/05-benchmark-workload.md`](../docs/05-benchmark-workload.md)
(v1.0, schema `bukifon-bench-v1`).  Devkit procedure:
[`docs/05a-benchmark-howto.md`](../docs/05a-benchmark-howto.md).
Harness: [`firmware/bench/`](bench/README.md).

## Commands

```bash
make -C firmware/bench host      # build + run host reference, writes results/host.{json,csv}
make -C firmware/host test       # 120 tests (was 112; +8 bench tests, existing untouched)
PLATFORMIO_CORE_DIR=/tmp/piocore pio run -d firmware -e bench_s3   # device skeleton build
```

## Host reference results (actual run, 2000 blocks, 100 warm-up)

Apple clang 21, `-O2`, macOS arm64.  Host is a **workload sanity reference**,
not a device verdict (see the note in docs/05 §2).

| Scenario | mean µs | max µs | p99 µs | overruns | det. | criterion |
|---|---:|---:|---:|---:|---|---|
| `fm_voice` | 71.93 | **218.29** | 103.17 | 0 | yes | max ≤ 650 µs |
| `granular_track` | 11.43 | 43.46 | 21.25 | 0 | yes | max ≤ 650 µs |
| `mix_bus` | 5.09 | 31.00 | 5.46 | 0 | yes | max ≤ 650 µs |
| `psram_stream` | 2.14 | 42.67 | 5.92 | 0 | yes | max ≤ 650 µs |
| `ui_frame` | 53.50 | 143.83 | 102.38 | 0 | yes | ≤ 33.3 ms/frame |
| `ui_frame_partial` | 20.64 | 70.00 | 43.33 | 0 | yes | ≤ 16.7 ms target |
| `usb_descriptor` | 0.63 | 1.83 | 0.71 | 0 | yes | build only |

- Deadline 1333.333 µs; criterion max block ≤ 650 µs.  Worst audio max on host:
  **218.29 µs = 16.4 % of the deadline**, i.e. **431.7 µs of margin below the
  frozen 650 µs criterion** (2.98× headroom to the criterion, 6.1× to the
  deadline).  All seven scenarios PASS, all checksums deterministic (stored in
  `firmware/bench/results/host.json`, timestamp 2026-11-05T21:26:39Z).
- Measured semantics: `psram_stream` = 512 × 64-byte random line reads/block
  (24.576 MB/s equivalent); `usb_descriptor` = HID 6KRO + MIDI + UAC2 + CDC
  descriptor build, 2.304 MB/s UAC2 requirement flagged as HS-only
  (`usb_fs_feasible=0`, `usb_hs_feasible=1`); `ui_frame` CPU draw time only
  (host has no display bus).
- `firmware/bench/results/host.json` + `host.csv` are the stored artifacts.

## Harness tests (+8, all green)

- frozen constants (64-frame block, 1.333 ms deadline, 650 µs criterion, 800×480
  UI, UAC2 2.304 MB/s);
- pass/fail criterion unit tests (max block, overruns, audio vs UI criteria);
- scenario registry: 7 frozen names, unknown names rejected;
- determinism: every scenario run twice → identical checksum;
- **zero allocations in the audio path**: global allocation probe armed around
  `processBlock()` for `fm_voice`, `granular_track`, `mix_bus` → 0 allocations;
- JSON/CSV/table output, PSRAM/UI/USB metrics, full vs partial UI frames.

Test count: **120 passed, 0 failed** (the 112 pre-existing tests are unchanged).

## Device build status

| Env | Result |
|---|---|
| `bench` (native PlatformIO) | prepared (same sources as the verified Makefile target) |
| `bench_s3` | **SUCCESS** — Flash 590 901 / 3 342 336 B (**17.7 %**), RAM 22 144 / 327 680 B (6.8 %) |
| `bench_p4` | **not built** — official `espressif32` 8.0.0 has no ESP32-P4 board/framework; env prepared/commented, switch instructions in docs/05a |
| `bench_h743` | **not built here** — needs `pio platform install ststm32`; env prepared/commented, instructions in docs/05a |

Device run output (table + JSON) is printed over USB serial at 115200 baud;
24 h soak is enabled with `-DBUKIFON_BENCH_SOAK_HOURS=24` (device main loops the
workload, counts overruns and reports every minute).

## What the hardware runs will show (and the decision thresholds)

Host numbers only prove that the workload/harness is sane; the MCU decision
needs the same scenarios on P4/H743 at frozen clocks:

- absolute max block time and p99 for `fm_voice`/`granular_track`/`mix_bus`
  (criterion max ≤ 650 µs, 0 overruns, 24 h soak without xruns);
- PSRAM/SDRAM random-read `ns/line` and MB/s for the granular working set
  (host DRAM proxy is not representative);
- real UI fps for full/partial redraw including display flush
  (750 KiB/frame → 22.5 MB/s at 30 fps);
- USB UAC2 8×8/24/48 (2.304 MB/s) with a HS PHY; SD worst case (768 KB/s +
  4 KiB random read per block) on real cards.

Thresholds/decision matrix are frozen in docs/05-benchmark-workload.md §9:
audio-capable = all audio scenarios max ≤ 650 µs, p99 ≤ 500 µs and 24 h soak
clean; then display + HS USB + PSRAM/SD gates decide P4 vs H743.  S3 is
reference-only (Full-Speed cannot carry UAC2 8×8/24/48).

## Bench limitations

- Host has no PSRAM/SD/USB-PHY/display bus: PSRAM is a DRAM proxy, USB checks
  descriptor bytes/bandwidth only, UI measures CPU draw time.
- Device timer `micros()` has 1 µs resolution (fine for 70–650 µs blocks).
- UI framebuffer is 750 KiB → needs PSRAM on S3/P4 (`prepare()` fails honestly
  without it).
- SD worst case and USB HS PHY are device-only extras (docs/05 §8, docs/05a §7).

---

# Round 5 — S3-base HAL, UI modes, P1 S3 profile, Module API v0.1 (2026-11-05)

## Builds

| Build | Command | Result |
|---|---|---|
| Host tests | `make -C firmware/host test` | **146 / 146 passed** (was 120; +26 new tests, the 120 pre-existing are unchanged) |
| Host pipeline | `firmware/tests/run_tests.sh` | **ALL HOST TESTS PASSED** (146 tests + WAV/FFT checks) |
| Host demo | `firmware/tests/run_sim_demo.sh` | **DEMO OK** — 16 bars, deterministic log, **8 PNG** 800×480 |
| **S3-base firmware** | `PLATFORMIO_CORE_DIR=/tmp/piocore pio run -d firmware -e s3base` | **SUCCESS** — Flash 738 635 / 6 553 600 B (**11.3 %** of the 6.25 MB app partition; 16 MB flash), RAM 205 356 / 327 680 B (**62.7 %**). Board HAL + engine + UI + 4 modules compile for ESP32-S3-N16R8. |
| Native PlatformIO | `pio run -d firmware -e native` | SUCCESS (host simulator build, same sources) |
| Bench host | `make -C firmware/bench host` / `host_s3` | PASS; results `bench/results/host.json` + `host_s3.json` |
| ESP32-P4 | — | **not built**: official espressif32 8.0.0 has no P4 board/framework (documented in `platformio.ini`, no false claim) |

## S3-base board HAL

`firmware/src/hal/board_cores3.*` encodes `hardware/cores3/pinmap.csv` (rev.0):

- SPI2 display 800×480 RGB565: SCK 12 / MOSI 11 / CS 10 / DC 9 / RST 8, BL_PWM 21;
- SPI3 (MCP3208): 4/5/6, CS 7; 1-bit SDMMC: CLK 15 / CMD 14 / D0 13;
- I2C0: SDA 16 / SCL 17 (400 kHz); I2S0: MCLK 18 / BCK 1 / LRCK 2 / DAC 38 / ADC 39;
- MIDI UART1: TX 40 / RX 41; WS2812 42; PANEL_IRQ 47; GATE1 48; PWR_GOOD 3; BOOT 0.
- 27 functional GPIOs, uniqueness enforced by `pinsUnique()`; config 240 MHz CPU / octal
  PSRAM 80 MHz / SPI2 80 MHz / USB FS stereo UAC2 (D-48); RAM profile one 750 KiB
  framebuffer + 8–16-line bounce buffers (D-51), no double buffering.
- `begin()` configures pins/I2C/UART/SDMMC and reports `displayReady=false`,
  `i2sReady=false`, `usbFsReady=false` on the host (explicit `TODO(hw)`); the board app
  (`app/s3base_main.cpp`) prints the real status on the devkit. **No hardware-verified
  display/I2S/USB/TinyUSB path yet — this is a compiling HAL skeleton, not a finished BSP.**

## UI: 4 device-mode panels

`uiSnapshotForDeviceMode()` produces mode-specific snapshots (same shell, different
panels + `MODE` in the status bar):

| Screenshot | MODE | Panel content |
|---|---|---|
| `artifacts/ui/synth.png` | SYN | CUTOFF/RES/ENV/DRIVE/ADSR, PART 1–4 patches |
| `artifacts/ui/sampler.png` | SMP | SAMPLE/START/END/GRAIN/PITCH/RATE/FILTER/MIX, TRACK 1–4 samples |
| `artifacts/ui/daw.png` | DAW | BANK / CC16–CC31 / transport notes, ENC 1–16 banks, MCU stub |
| `artifacts/ui/usb_kbd.png` | KBD | LAYER/KEYMAP/MACRO/SHIFT/HID/REPORT, Lapka-42 key ranges |

`run_sim_demo.sh` now generates all **8** screenshots (4 pages + 4 modes) and verifies
their sizes. New tests render each mode, check the status-bar short name, mode-specific
panel vocabulary and distinct framebuffer checksums.

## P1 S3 profile (`s3_profile` benchmark)

`firmware/bench/lib/scenario_s3.cpp`; results in `bench/results/host_s3.json`
(host reference, 2000 blocks, 100 warm-up):

| Metric | Value |
|---|---|
| Memory profile | 4 MiB sample pool + 750 KiB framebuffer + 25 KiB bounce (16 rows) |
| Compute | 6 FM voices + 4 granular tracks + limiter, 64-frame block, dirty stripe + periodic full UI redraw |
| max block time (host) | **192.1 µs** (mean 56.7 µs, p99 111.8 µs), overruns 0 |
| SPI full refresh (D-51 model, 80 MHz) | **13.02 fps** → **does NOT meet D-46's ≥15 fps** |
| SPI partial updates (40 % area) | **32.55 updates/s** → meets D-46 ≥30 |
| RGB565 target model (20 MHz pixel clock) | **52.08 fps** full → meets D-46 ≥15 |
| USB | stereo UAC2 24/48 = **0.288 MB/s** (FS feasible; 8×8 is P4/H743 only) |

Criterion wiring: `max block ≤650 µs` + D-46 partial ≥30 + RGB full ≥15 (pass); the
SPI full-refresh shortfall is recorded as a metric and called out as the D-51 risk (the
S3-base decision must move to RGB565 per `docs/31`, whose GPIO budget does not fit on
N16R8 — open hardware decision).

## Module API v0.1 (experimental, ABI major 0)

Header `firmware/include/bukifon_module.h`; docs `docs/24-module-sdk.md`.

- **12 callbacks** (v0 table + `attach_host` + `on_event`), backward compatible:
  v0 modules (gain_fx, lfo_mod) keep working unchanged (new pointers `NULL`).
- **Host services**: `now_us()` (monotonic) and `log()`; logging from `process()` is
  forbidden — the host wrapper counts violations, drops the message and exposes
  `logViolations()` / `lastLogMessage()`.
- **Events**: NOTE_ON/OFF, GATE_ON/OFF, TRANSPORT START/STOP/CONTINUE, TEMPO, PATTERN,
  PITCH_BEND with channel/id/value/frame_offset; `sendEvent()` + `eventsSent()`.
- **Parameter smoothing**: `setParamSmoothed(id, value, timeMs)` with per-block
  interpolation at ABI boundaries (≤64 frames); module receives smoothed values via
  `set_param` — no allocation/locks in the audio path.
- **New examples**: `modules/examples/grain_fx.cpp` (granular insert, events + services),
  `modules/examples/svf_filter.cpp` (TPT SVF, NOTE_ON keytrack, state save/load).
- Tests: lifecycle both examples, host services, event delivery/legacy rejection,
  log violation, smoothing ramp, budget bypass, state roundtrip, v0 compatibility.
- **v0.1 is still experimental/unstable** — no third-party modules should target it.

## S3 risks (explicit)

1. **D-51 SPI display**: modelled full refresh 13.0 fps < D-46's 15 fps. S3-base as
   specified in docs/31 needs RGB565, but N16R8 has only 31 usable GPIO and the RGB565
   variant needs 38–40 — unresolved hardware decision; SPI partial redraw (32.5/s) is
   the fallback.
2. **No hardware verification**: board HAL compiles and reports status, but SPI panel,
   I2S codec, SDMMC, TinyUSB composite and PSRAM performance are `TODO(hw)` stubs.
3. **CPU headroom on S3**: host profile max is 177 µs for the modelled workload, but the
   240 MHz LX7 has no DSP accelerators; real device numbers (bench_s3 device run) are
   required before committing to the S3-base SKU.
4. **PSRAM contention**: 4 MiB pool + 750 KiB framebuffer share octal PSRAM with
   cache/display traffic; random-read latency must be measured on the devkit.
5. **USB**: FS only → stereo UAC2 (D-48); 8×8 UAC2 stays P4/H743-only. TinyUSB glue and
   descriptor binding are not implemented yet.
6. **P4**: still not buildable with the installed PlatformIO platform; no false success.

---

# Round 6 — S3 vertical-slice spike + P4 first-SKU priority (2026-11-05)

Customer decision: **P4 with RGB565/DSI + HS USB is the first SKU**; S3-base is
the "lite later" concept platform.  The UI (4 pages + 4 device-mode panels) is
identical for both — only the display backend and USB PHY differ.

## Builds

| Build | Command | Result |
|---|---|---|
| Host tests | `make -C firmware/host test` | **160 / 160 passed** (146 pre-existing unchanged, +9 spike, +5 p4_profile) |
| Host pipeline | `firmware/tests/run_tests.sh` | ALL HOST TESTS PASSED (160 + WAV/FFT) |
| **S3 spike firmware** | `PLATFORMIO_CORE_DIR=/tmp/piocore pio run -d firmware/spike_s3 -e spike_s3` | **SUCCESS** — Flash 432 483 / 6 553 600 B (**6.6 %**), RAM 66 820 / 327 680 B (**20.4 %**) |
| Native / s3base | as before | unchanged SUCCESS (previous round) |
| **P4 build** | — | **not buildable**: official `espressif32` 8.0.0 has no P4 board/framework; `env:p4`/`bench_p4` prepared/commented, no false success |

## S3 vertical-slice spike (`firmware/spike_s3/`, lite concept platform)

Standalone PlatformIO project (`firmware/spike_s3/platformio.ini`, env
`spike_s3`, ESP32-S3-N16R8).  One cooperative loop runs all subsystems and logs
`SPIKE_METRIC` every second + a final `SPIKE_RESULT pass=0|1` per docs/36 §2.

**Ready (real code / real metrics):**
- SPI display 800×480 full flush (30 × 16-row bounce batches) and dirty-rect
  partial updates; fps/lcd-drift metrics.
- SD 1-bit SDMMC 4 KiB write+read roundtrip every 5 s; latency/error metrics.
- I2C MCP23017 panel scan (0x20–0x23, GPIOA), latency/error metrics.
- Audio block timing/xruns, metric accumulation (min/max/mean/p99 histogram),
  pass/fail criteria, machine-readable log, host parser and host simulation.
- `spike_core.hpp` portable core is shared by firmware, host sim and host tests
  (`tests/test_spike.cpp`), so the pass/fail logic is CI-tested.

**Stubs (`TODO(hw)`, honest):** I2S driver init/read/write (synthetic loopback is
timed; enable `BUKIFON_SPIKE_USE_I2S` after wiring), TinyUSB composite UAC2+MIDI+
HID+CDC (`BUKIFON_SPIKE_TINYUSB`), panel controller init sequence
(ST7796/ILI9488 MADCTL/gamma), SD card-detect (absent on CORE-S3), backlight
curve.  No devkit measurements exist yet.

**Host simulation:** `bash firmware/spike_s3/run_host_spike.sh` → PASS:
`audio_max=389 µs`, `p99=416 µs`, `xruns=0`, `full_fps=15.0`,
`partial=31.5/s`, `usb_drops=0`, `sd_max=5.25 ms`, `panel_max=741 µs`,
`panel_errors=0`.  These are simulation values, not hardware.

## P4 first-SKU profile (`p4_profile`, bench)

Added because P4 is now the first SKU: `make -C firmware/bench host_p4` →
`firmware/bench/results/host_p4.json` (host reference; 2000 blocks, 100 warm-up):

| Metric | Value |
|---|---|
| Compute | 8 FM voices + 8 stereo tracks + limiter, 64-frame blocks |
| Memory | 750 KiB RGB565 framebuffer + 25 KiB (16-row) bounce |
| Host max block | **319.7 µs** (mean 77.0 µs, p99 132.2 µs), 0 overruns |
| RGB565 display model | **52.1 fps full, 130.2 partial/s** (≥15 fps / ≥30 criteria met) |
| HS USB 8×8 UAC2 24/48 | **2.304 MB/s**, HS-feasible flag = 1 |
| Soak target | 24 h recorded for the P1 stand device run |

`s3_profile` remains as the lite-limitation reference: SPI full 13.02 fps (<15,
D-51) vs RGB model 52.08 fps; partial 32.55/s.  `host.json` now runs all 9
scenarios, all PASS.

## What the P1 stand should run first (max value)

1. `p4_profile` on the P4 devkit (audio max/p99/xruns; RGB565 full/partial fps;
   HS USB 8×8 drops; 24 h soak) — the primary SKU decision.
2. `s3_profile` on S3-N16R8 (lite check; SPI limit confirms D-51) — secondary.
3. `bench` device envs (`bench_s3` builds; `bench_p4` prepared) for the full
   frozen workload; `s3_profile`/`p4_profile` scenarios specifically answer the
   RC-DoD tests 1–3 and 6.

## Switch the spike to P4

Keep `spike_core.hpp` (buffers/metrics/log/parser); replace `flushRows` SPI with
an RGB565/DSI backend (PPA/DMA2D), set frame timing from the RGB565 pixel clock,
enable HS TinyUSB composite (8×8 UAC2), and build with a P4-capable PlatformIO
platform (pioarduino/arduino-esp32 P4 preview).  Same codecs/SD/panel metrics,
same acceptance thresholds.  UI is unchanged (same 800×480 snapshot shell + 4
mode panels).

## Risks / limitations

- S3-lite SPI: full refresh ~13 fps < D-46 15 fps (D-51); partial redraw is the
  fallback.  P4 RGB565/DSI is the first-SKU answer.
- No hardware verification: I2S/TinyUSB/panel-init are stubs; devkit spike
  protocol (`docs/39`) is ready but has not been executed.
- P4 toolchain is not available in this environment; P4 numbers are host models
  from `p4_profile`, not silicon measurements.

---

# Round 7 — P4 HAL + factory self-test (2026-11-05)

First SKU is P4; this round adds the CORE-2 board HAL and the 14-test factory
self-test (docs/42 §2) with a host CLI/mocks for the production station.

## Build (P4) — honest status

```bash
PLATFORMIO_CORE_DIR=/tmp/piocore pio run -d firmware -e p4
# => UnknownEnvNamesError: Unknown environment names 'p4'
```

`env:p4` is **prepared but intentionally commented**: the installed official
`platformio/espressif32` 8.0.0 has no ESP32-P4 board definition/framework, so the
env cannot resolve.  `firmware/platformio.ini` contains the attempted result, the
P4 build filter (`app/esp32_main.cpp` + engine + `src/hal/board_cores2.cpp`) and a
commented `p4_factory` entry.  No P4 SUCCESS is claimed.

## CORE-2 board HAL (`firmware/src/hal/board_cores2.*`)

Pins frozen from `hardware/core2/pinmap.csv`: **55 GPIO signals** (54 functional +
GPIO36 strap), uniqueness enforced.  Key buses:

- I2S0: MCLK 20 / BCK 16 / LRCK 17 / DAC DIN 18 / ADC DOUT 19;
- I2C0: SDA 21 / SCL 22 (400 kHz: MCP4728×2, 24C32, 4× MCP23017);
- shared SPI2: SCK 6 / MOSI 7 / MISO 8 / MCP3208 CS 9; C6 CS 26 / HS 24 / DR 25 / RST 27;
- MIDI UART1: TX 10 / RX 11; UART0 37/38; BOOT 35 / STRAP36 / VBUS_DET 54;
- SDMMC slot0 4-bit: D0–D3 39–42, CLK 43, CMD 44, CD 45;
- RGB565 LCD_CAM: PCLK 12, DE 13, HS 14, VS 15, B0–B4/G0–G5/R0–R4 (0–5,23,28–34,46,47),
  BL_PWM 49, LCD_DISP 50; WS2812 48; PANEL_IRQ 51; GATE1/2 52/53;
- USB HS dedicated PHY.  Display RGB/DSI backend, I2S driver and C6 esp-hosted
  link are explicit `TODO(hw)` stubs (status flags report not-ready).

## Factory self-test (`firmware/src/factory/`)

14 tests from docs/42 §2, each with nominal time and timeout (3× nominal + 500 ms),
PASS/FAIL/TIMEOUT, details, and a JSON report (`bukifon-factory-selftest-v1`).

**CLI (host mock):**

```bash
make -C firmware/host factory
firmware/host/build/bukifon_factory --json            # JSON report only
firmware/host/build/bukifon_factory                   # human table
firmware/host/build/bukifon_factory --out report.json --stop-on-fail
```

Actual host run: **14/14 PASS, total 38 000 ms** (nominal automation ≈38 s;
target EOL 2–2.5 min with operator checks).  Exit code 0 PASS / 1 FAIL / 2 usage.
Report written to `firmware/tests/out/factory_report.json`.

Tests: power-on/brownout, I2C scan (strict 0x20–0x23/0x36/0x57/0x60/0x61),
MCP23017 walking-bit + IRQ, MCP3208 vector (±2 LSB), MCP4728→MCP3208/CV ≤20 mV,
codec 1 kHz/−12 dBFS/gain ±1 dB/THD<−60 dB, SD 1 MiB CRC32 ≥700 KB/s, display
patterns, WS2812 current ±20 %, MAX17048 ≤30 mV, USB composite enum
(CDC+MIDI+HID+UAC), controls (42 keys/16 encoders/2 faders), CV/GATE loopback,
MIDI 100 packets 0 errors.

**Real vs mocks:** runner/validators/timeouts/JSON/CLI are real and host-tested;
host `MockHardware` is deterministic with failure/timeout injection;
`P4FactoryHardware` methods and flash `factory_data`/24C32 identity/QR are
`TODO(hw)` stubs returning false (no fabricated PASS).  Docs:
[`docs/46-factory-test.md`](../docs/46-factory-test.md) — loopback plug, table,
EOL timing, JSON, serial/QR, risks.

## Tests

**183 / 183 PASS** (160 pre-existing untouched; +6 board_cores2, +17 factory:
validators, timeout, stop-on-fail, every-test-can-fail, JSON, CLI, mock).  Full
pipeline `run_tests.sh` → ALL HOST TESTS PASSED (FFT unchanged).

## Risks

1. **P4 build unavailable** — no P4 PlatformIO board/framework installed; env
   prepared/commented, device run untested.
2. **Hardware methods are stubs** — the factory flow currently proves the
   station software/runner/JSON, not the CORE-2 electrical paths.
3. EOL timings are nominal (docs/42), not measured; operator tests depend on the
   station UI.
4. Identity/QR writing to flash `factory_data` + 24C32 calibrations is `TODO(hw)`.
5. Factory tests depend on TinyUSB/I2S/display backends that are still stubs
   (docs/39) — enable them before the first real EOL run.

---

# Round 8 — UAC2 8x8 HS descriptors, RGB565 backend, factory hooks (2026-11-05)

## USB HS UAC2 8x8 (`firmware/src/usb/uac2_8x8.*`)

Descriptor builder for the P4 first SKU: 8-in/8-out, 24 bit / 48 kHz, explicit
feedback, MIDI+HID+CDC alongside.

- **Measured (host)**: config **300 B**, **8 interfaces**, **9 endpoints**,
  `wTotalLength` matches the descriptor walk; device descriptor is 18 B with
  bcdUSB 2.00.
- **Endpoint budget**: USB 2.0 HS has 16 addresses (EP0 + 15).  UAC2 aggregates
  8 channels into **one ISO endpoint per direction**, so the budget is
  `2 ISO + 1 feedback + 2 MIDI + 3 CDC + 1 HID = 9/15 → fits`.
  A per-channel layout (`16 ISO + feedback + MIDI2 + CDC3 + HID1 = 23/15`) is
  impossible; the builder reports it honestly and provides
  `maxPerChannelChannelsForFit() = 4`.  Mitigation: UAC2 channel aggregation
  (standard) or ≤4 channels per-channel; **alt settings do not free endpoint
  addresses** (they reuse the same endpoints), so they are not a fix by
  themselves.
- **Format/clock**: internal fixed 48 kHz clock source descriptor (UAC2 CS
  subtype 0x0A), AS interfaces with 8 channels, format type I 24-bit/3-byte
  subslot, ISO packet **144 B/microframe** (8ch×3B×6), feedback endpoint 0x82
  (4 B, interval 4), 6KRO HID report 45 B.
- **JSON dump** for the USB analyser: `make -C firmware/host usbdump` →
  [`firmware/artifacts/usb/uac2_8x8.json`](artifacts/usb/uac2_8x8.json)
  (hex device/config + budget + lengths).  This is a byte-level reference, not a
  real enumeration test (TinyUSB glue is still TODO(hw)).
- Tests: wTotalLength/walk consistency, unique endpoint addresses, budget both
  modes, clock/format, feedback sizing, JSON, per-channel diagnostic build.

## RGB565 display backend (`firmware/src/hal/display_rgb565.*`)

Interface `init / attachFramebuffer / flushRows / flushFull / flushPartial /
beginFrame / addDirtyRect`; bounded dirty-rect list (8), 16-row bounce, host
frame simulation.  Model from `host_p4`: **52.08 fps full**, **130.21 fps
partial** at 800×480, 20 MHz pixel clock (full flush ≈19.2 ms).  Host simulation
is allocation-free (alloc probe around flush path = 0).  Real esp_lcd / DSI /
PPA path is an explicit `TODO(hw)`; backend name says so.

## Factory backend enable hooks (`firmware/src/factory/hw_backends.*`)

`BUKIFON_HW_{I2C,ADC,DAC,I2S,SD,DISPLAY,USB,CONTROLS,CV,MIDI}` = REAL/MOCK
(default MOCK in host builds; override with `-D...=BUKIFON_HW_REAL`), runtime
`HwConfig` + `HybridHardware` delegating per subsystem.  Mapping: I2C covers
power/I²C/MCP23017/MAX17048, ADC→MCP3208, DAC→CV DAC loopback, I2S→codec,
SD→scratch, DISPLAY→patterns+WS2812, USB→composite, CONTROLS→keys/encoders/
faders, CV→CV/GATE loopback, MIDI→DIN loopback.  Tests prove: all-MOCK 14/14
PASS; all-REAL with P4 stubs 14/14 FAIL (**mock never fabricates PASS**); each
backend switched individually fails exactly its mapped tests while mock-backed
tests stay PASS; runtime flags independent.  Bench enable order and protection
rules are in [docs/46-factory-test.md](../docs/46-factory-test.md) §9
(I2C → panel/controls → codec → display → SD → USB → CV/MIDI).

## Tests

**203 / 203 PASS** (183 pre-existing untouched; +20: 9 UAC2, 5 display, 6 hw
backends).  `run_tests.sh` → ALL HOST TESTS PASSED (FFT unchanged).
`make -C firmware/host usbdump` produces the descriptor JSON artifact.

## Risks / limits

1. Descriptors are byte-checked on the host; **no real USB analyser/TinyUSB
   enumeration** yet.  UAC2 8x8 requires the P4 HS PHY (P4 build still
   unavailable — no P4 PlatformIO board).
2. Per-channel 8×8 endpoint layout is impossible on HS (23>15); the product must
   use UAC2 channel aggregation (implemented) or ≤4 channels if per-channel is
   ever required.
3. RGB565 backend is a host model; esp_lcd/DSI/PPA + bounce DMA are TODO(hw).
4. Factory REAL backends are still TODO stubs; switching them on the bench will
   require implementing `P4FactoryHardware` (docs/46 §9 order).

---

# Round 9 — serials/QR labels + factory identity (2026-11-05)

## Label generator (`tools/make_labels.py`)

CSV → A4 **3×8** sheet, label **60×30 mm**, QR content
`BKS3-26A-0001|core=2.p4|panel=2|pwr=1|batch=26A|date=2026-11-05`, plus manifest
JSON and `--preview` PNG (first 6 labels).  QR library: **segno** (+ reportlab,
Pillow) installed in `/tmp/msvenv`; no system packages assumed.

- Validation: required columns, SN regex `BKS3-YYA-NNNN`, batch↔SN match, ISO
  date, revision charset, `PASS/FAIL/RETEST`, one batch per sheet, ≤24 labels,
  **duplicate SN rejection with line numbers**.
- `--selftest` PASS (24-label PDF/manifest/preview + duplicate rejection).
- Generated dev sheet: `dist/labels/labels_26A.pdf` (24 labels, 125 KB),
  `labels_26A.json`, `labels_26A_preview.png` (300 dpi preview inspected: SN,
  revs/date/batch/test, QR all legible).
- Media/placement/RMA rules: [`docs/55-labels-traceability.md`](../docs/55-labels-traceability.md).

## Factory identity (`firmware/src/factory/identity.*`)

- 114-byte little-endian record: magic `BKID`, version 1, product, serial,
  core/panel/pwr revisions, date, batch, MAC (6 B), calibration version, test
  result, CRC32 over the preceding 110 bytes.
- Validator: serial regex, batch↔serial, date, required revisions/MAC,
  CRC; JSON roundtrip; explicit serialize/deserialize with bounds checks.
- `IdentityStore` = host model of the flash `factory_data` two-copy layout:
  alternating slots, CRC-checked reads, **duplicate SN rejected**, corrupt-slot
  fallback, oldest copy replaced on third write.
- CLI: `factory --identity <json>` validates+stores (prints identity JSON or
  `IDENTITY FAIL`), `factory --print-identity` prints the stored identity; exit
  codes 0 OK / 1 invalid / 2 usage / 3 empty store.  Real flash + 24C32 write are
  explicit `TODO(hw)` (`p4_hardware.cpp`, docs/55 §8).
- Tests: serial/date validation, magic/version/product/batch/MAC validation,
  serialize roundtrip (114 B), CRC single-byte corruption, JSON roundtrip,
  store write/read/rotate/duplicate/corrupt-slot fallback, CLI write/print,
  empty store and invalid JSON rejection.

## Tests

**216 / 216 PASS** (203 pre-existing untouched; +13 identity tests).
`run_tests.sh` → ALL HOST TESTS PASSED (FFT unchanged).  Label tool self-test:
`/tmp/msvenv/bin/python3 tools/make_labels.py --selftest` → PASS.

## What remains (honest)

1. **Real identity write to flash `factory_data` / 24C32 is TODO(hw)** — the
   format/store/CLI contract is ready, hardware programming is not implemented.
2. Label durability (thermal transfer stock, isopropyl/heat/cycle) and QR scan
   rate on the assembled unit must be validated on real labels.
3. Production CSV/serial allocation is manual for the beta; manifest format is
   ready for the factory station export.
4. P4 firmware build is still blocked by the missing P4 PlatformIO platform;
   identity CLI is host/mock-tested.

---

# Round 10 — UI palette tokens: 4 themes in firmware (2026-11-05)

- `firmware/include/bukifon_ui_theme.h`: C API + C++ helpers; 4 themes
  (Night/Amber/Phosphor/Cream) × 12 tokens (`bg/panel/card/line/text/muted/
  accent/green/orange/blue/red/purple`), values exactly docs/62; default Night.
- `firmware/src/ui/ui_theme.cpp`: frozen palette table, RGB888→RGB565,
  `bukifon_ui_theme_set()` (case-insensitive), host file persistence
  `save/load(path)` (NVS/flash on device = TODO(hw)).
- Renderers converted to tokens: `src/ui/ui800.cpp` (SYNTH + all 4 device modes,
  headers/cards/steps/params/status bar) and legacy `src/ui/menu.cpp`; local
  hardcoded RGB565 constants removed.  Part colours follow docs/62
  (green/orange/blue/purple for tracks 1–4).
- Host demo CLI: `bukifon_sim --theme Cream [--theme-config PATH]`; no
  auto-load unless a config path is passed (deterministic screenshots).
- Tests +10 (**226/226 PASS**, 216 pre-existing untouched): exact docs/62 values
  for all 4 themes, RGB565 conversion, selection API/bounds, persistence
  (save/load/missing/corrupt), SYNTH rendering for every theme, 4 modes ×
  4 themes, and a source scan proving `ui800.cpp`/`menu.cpp` contain no
  `colors::`/`rgb565(`/raw 0xRRGGBB colour literals.
- `docs/62-screen-palette.md` status updated: firmware uses the same tokens;
  remaining: device NVS persistence, RGB565 banding/contrast on hardware, demo/
  site theme selector sync (values already match).

---

# Round 11 — GEN functions + GEN page + presets/UX (2026-11-05)

- **GEN engine** (`src/io/gen.*`): deterministic PROB 0–100 %, EUCLID 0–16
  (Euclidean/Bjorklund mask via bucket algorithm, accents on 1/5/9/13),
  MUTATE ±0–12 semitones `hash(seed,part,step)`, SCALE LOCK
  OFF/MINOR/MAJOR/PENTA/DORIAN (nearest note), EVOLVE at bar boundary, SEED, and
  a simple ARP (1/8, 1/16, 1/32 × UP/DOWN/UPDOWN over held notes).  API:
  `GenParams` per part + `Sequencer::setGenParams`; defaults are neutral.
- **Sequencer integration**: `triggerStep` applies Euclid gate/accents,
  probability, mutation, scale lock and ARP; bar wrap calls deterministic
  evolve.  Same seed => identical event stream (tests); different seed differs.
- **UI**: 5th tab **GEN** (header tabs MAIN/SEQ/MIX/MOD/GEN) with 8 function
  fields, Euclid ring, scale/ARP names, 8 preset slots, A/B indicator,
  multi-select part chips (group edit), and a mod-visible **M** marker on
  modulated parameters (CUTOFF from LFO in the demo).  Snapshot holds
  `gen[]`, `genPartSelected[]`, `paramModulated[]`, `abCompare/abShowB`,
  `presetNames[8]`, `euclidMask`.
- **Presets** (`src/storage/preset_bank.*`): 8 slots, per-part GenParams +
  selection mask, versioned host file with magic/version/CRC32; on P4 NVS is
  TODO(hw).  Host CLI `bukifon_sim --preset PATH` loads/creates the bank.
- **Docs**: `docs/66-ux-implementation.md` maps each docs/65 UX pattern to the
  implementation and test, lists remaining `TODO(hw)`.
- **Tests**: **248/248 PASS** (226 pre-existing untouched; +12 GEN, +5 presets,
  +5 GEN UI).  `run_tests.sh` → ALL HOST TESTS PASSED.
- **Artifacts**: `run_sim_demo.sh` now renders **9** screenshots, including
  `firmware/artifacts/ui/gen.png`; inspected visually (PROB/EUCLID/MUTATE/SCALE/
  ARP/EVOLVE/SEED, preset row, group 1+3, Euclid ring).

## Remaining (`TODO(hw)` / next)

1. P4 NVS/flash backend for preset slots (host file exists).
2. LED/WS2812 palette mapped to docs/62 tokens.
3. Hardware pickup/undo gestures and 16-encoder/42-key mapping.
4. P4 device run (toolchain docs/59) for real-time GEN/UI verification.

---

# Round 13 — UI philosophy/readability: 16 encoders mirror + docs/69 scale (2026-11-06)

- **16-cell encoder mirror** in `ui800.cpp`: 2 rows × 8 cells; left 4 columns are
  page parameters (А–З), right 4 are fixed macros (И–П:
  CUT/RES/ATK/REL/DLY/DRV/CRSH/MST); cell label `А · CUTOFF`, value 18 px,
  slider bar; mapping/API `uiEncoderCellIndex()`/`uiEncoderCellPrefix()`.
  (The 6×8 ASCII font transliterates Cyrillic labels for display.)
- **docs/69 typography roles**: `UiTextRole` Caption 12 px, Value 18 px,
  Critical 24 px (BPM/STEP/REC), Title 26 px; all `ui800.cpp` text renders
  through `drawTextRole` — source test rejects `drawText`/`drawTextScaled(...,1)`
  calls, so no text <12 px remains in the 800×480 renderer.
- **Context line** `PART · SELECTED · PAGE · FADERS · REC · UNSAVED` is built by
  `uiBuildContextLine()` and always drawn in the header; state fields
  `partLabel/selectedLabel/faderMode/transportRecord/unsaved`.
- **HOME** button in the footer + `uiHandleHome()` returns to MAIN in one
  gesture; page tabs are 12 px (5 tabs: MAIN/SEQ/MIX/MOD/GEN).
- **Cream palette** updated: accent `#a8321f`, green `#3f6f2e`, orange
  `#9a4a10`, muted `#5f5548`, red `#9c2a1a`; WCAG contrast for
  text/muted/accent/green/orange ≥4.5:1 (measured 5.18–11.89).
  Note: `docs/62` currently still lists red `#b0301f`; sync pending.
- **Tests**: **263/263 PASS** (248 pre-existing untouched; +15 readability:
  scale heights, no-small-text source scan, encoder mapping, 16 cells,
  context line in all modes + REC/UNSAVED, HOME handler/render, Cream contrast
  and values, 4-theme rendering, selected encoder highlight, five tabs,
  critical header/context rendering).  `run_tests.sh` → ALL HOST TESTS PASSED.
- **Screenshots** regenerated (9 PNG): `artifacts/ui/synth.png` shows the
  16-cell layout with 12/18/24/26 px type; `gen.png` 5th tab; others updated.
- **Docs**: `docs/66-ux-implementation.md` §6 maps docs/68/69 philosophy to
  implementation/tests; known TODO: LED palette, NVS theme/preset persistence,
  1:1 print readability and real P4 screen.

---

# Round 14 — external MIDI sequencer v1.0-rc (2026-11-06)

- **Engine** `src/io/ext_sequencer.*`: 8 external MIDI tracks (channels 1–16,
  PC, note/velocity/length, 1 CC p-lock per step, mute), GEN (prob/Euclid/
  mutate/scale/ARP) applied to external tracks, transport start/stop/continue,
  **24 ppqn clock out** (master) with ≤1 ms jitter model and **clock-in slave**
  (6 clocks per 16th), live record (quantized note on/off + gate length),
  versioned CRC32 payload (`EXTP`, v1) for save/load, and `MidiOutRouter` +
  `RouterExtSink` modelling DIN+USB output **without duplicates**.
- **Shared sequencer**: `Sequencer::external()` shares tempo/swing/transport and
  processes external tracks in the same timeline as the 4 internal parts.
- **UI**: 6th tab **EXT** (`MAIN/SEQ/MIX/MOD/GEN/EXT`): 8 rows `T1 CH1 PC0`,
  16-step grid, selected track/step, p-lock bars, mute marker, CH/PROG/VEL/LEN/
  CC#/CC VAL/SWING/CLK cells (left) + macros И–П (right), mirrored layout;
  screenshot `artifacts/ui/ext.png`.
- **Tests**: **288/288 PASS** (263 pre-existing untouched; +25: 16 engine/
  router/serialize/GEN/clock/arp, 5 UI EXT, 4 GEN/clock/arp edge cases).
  `run_tests.sh` → ALL HOST TESTS PASSED; `run_sim_demo.sh` → **10** PNG.
- **Docs**: `docs/70` §7–8 (implementation + TODO(hw)); `docs/66` §7 EXT row.
- **TODO(hw)**: real DIN/USB-MIDI gateway, MIDI-in clock/CC learn, project v2
  integration of the `EXTP` payload, 4 CC per track (v1.1), hardware latency
  and USB-MIDI host.

---

# Round 15 — voice as input: MIC capture, recording, beatbox, privacy (2026-11-06)

- **Mic engine** `src/io/mic.*`:
  - `MicCapture`: host model of I2S1 MEMS capture, LINE/MIC source, gain dB,
    RMS level/peak, VAD threshold.
  - `VoiceTake`: record ≤30 s, silence auto-trim, name/pad/PSRAM-SD storage,
    peak; hardware mute blocks recording.
  - `MicPrivacy`: mute switch + MIC ON LED model; no implicit BLE/Wi-Fi
    transmission (`micNetworkTransmissionAllowed(false)`).
  - `BeatboxDetector`: onset (energy + derivative per 1/16 window), classes
    kick/snare/hat (low/high/ZCR), velocity/accent, quantized step fill with
    notes 36/38/42; `BeatboxPattern` provides UNDO.
- **UI**: 7th tab **MIC** (`MAIN/SEQ/MIX/MOD/GEN/EXT/MIC`): MIC ON/MUTED privacy
  banner, SOURCE, LEVEL meter + peak, BEATBOX ON/OFF, REC PAD + take name,
  SRC/GAIN/THR/MON/BEAT/SENS/PAD/LVL fields in the mirrored 16-cell map, MIC
  state in the persistent context line. Screenshot `artifacts/ui/mic.png`.
- **Tests**: **311/311 PASS** (288 pre-existing untouched; +23: 18 mic engine/
  beatbox/privacy/record, 5 UI MIC). Beatbox accuracy ≥80 % at 90/110/140 BPM on
  synthetic 4/4 bars; `run_tests.sh` → ALL HOST TESTS PASSED; `run_sim_demo.sh`
  → **11** PNG.  Profile tests got retry wrappers for host scheduling spikes.
- **Docs**: `docs/71` §8 implementation + §9 TODO(hw); `docs/66` §8 MIC row.
- **TODO(hw)**: I2S1 DMA (MEMS), MAX9814/PCM1808 line/mic mux, PSRAM/SD sample
  write/playback, hardware mute switch/LED GPIO, beatbox robustness v1.1,
  privacy audit of the BLE/Wi-Fi stacks.

---

# Round 19 — factory self-test 21 checks (2026-11-06)

- **Factory self-test extended 14 → 21** (`src/factory/selftest.*`) per
  `hardware/core2/dfm.md` §2:
  - power/rails, I2C scan, MCP23017 walking-bit, MCP3208 vector, DAC/ADC and
    codec loopback, SD, display, WS2812, MAX17048, USB composite, controls
    (42 keys/16 encoders/2 faders), CV/GATE, MIDI loopback (existing 14);
  - **new**: 24C32 EEPROM+SN, MCP4728 ×2 readback, C6 esp-hosted link,
    CV IN1–4/TVS, UART0/BOOT, serial/QR identity match, **mic (D-91)**:
    MEMS 1 s record/VAD, RMS is inside −60..0 dBFS, SNR ≥65 dB, MIC_SEL,
    SW3 mute blocks recording, MIC ON LED, electret loopback, latency ≤5 ms.
- **Runner/report**: 21 enumerated items with id/name/status(PASS/FAIL/TIMEOUT/
  SKIP)/detail/duration; JSON schema `bukifon-factory-selftest-v1` count 21;
  P4 without toolchain reports **21 SKIP** via `isAvailable()` (honest, no
  fabricated PASS/FAIL); mock hardware remains 21/21 PASS.
- **MIDI/EXT**: factory tests reuse the external sequencer router
  (`MidiOutRouter`): DIN+USB one logical note/CC/PC/clock/transport each, no
  duplicates; clock 24 ppqn (24 ticks/quarter at 120 BPM).
- **Screenshot**: `artifacts/factory/selftest.png` (800×480 station screen,
  21/21 PASS, generated from the real mock CLI report).
- **Tests**: **331/331 PASS** (311 pre-existing + 20 new; existing factory/
  backend expectations updated from 14 to 21). `run_tests.sh` → PASS.
- **Docs**: `docs/42` §8 table 21 tests with TODO(hw); `docs/38` synced
  (21 incl. mic, P4 SKIP, docs/42 §8).
