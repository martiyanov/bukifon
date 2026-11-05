# Bukifon firmware

Open firmware for **Bukifon** — a modular handheld synth/gamepad built on
Raspberry Pi Pico (RP2040, 2 cores) with `arduino-pico`.

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
  src/hal/      RP2040 drivers (headers, Arduino-only): i2s_pio, mcp4728,
                mcp3208, hc165, mcp23017, ws2812, st7789, midi_uart, pinmap
  Bukifon/      Arduino sketch: Bukifon.ino + platformio.ini + engine_unity.cpp
  host/         native build (Makefile + CMakeLists.txt), WAV renderer
  tests/        unit tests, FFT analysis, run_tests.sh, REPORT.md
  tools/        wavetable/font generators, build_pico.sh
```

## Host build and tests (fully verified)

The portable engine has **no Arduino dependencies** and is tested natively:

```bash
make -C firmware/host test          # build + run unit tests
firmware/tests/run_tests.sh         # full pipeline: build, tests, WAV render, FFT report
```

Latest measured results (see `tests/REPORT.md` and `tests/out/test_log.txt`):

- **67 unit tests, 0 failures** (Apple clang 21, C++17, `-O2`)
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
| Flash | 377 312 B / 1 044 480 B — **36.1 %** |
| RAM | 210 012 B / 262 144 B — **80.1 %** |
| Артефакты | `firmware/artifacts/bukifon-pico.uf2` (764 KiB), `.elf` |
| Host-тесты | 67/67 после сборки (регрессий нет) |

RAM 80 % — запас небольшой; при добавлении эффектов/модулей оптимизировать
буферы (delay-линия, пресет-кэш) или перенести часть в PSRAM (RP2350).

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
