# 05a. P1 benchmark — how to run on the three devkits

Companion to [05-benchmark-workload.md](05-benchmark-workload.md) (the frozen
workload) and `firmware/bench/README.md` (harness).  This page is the practical
recipe: flash, run, capture, read, decide.

---

## 1. What you need

| Board | Why | Minimum configuration |
|---|---|---|
| **ESP32-P4-Function-EV-Board** (or equivalent P4 devkit) | candidate #1 | 32 MB PSRAM, USB-HS port, 400 MHz HP core |
| **ESP32-S3-DevKitC-1-N8R8** | reference / harness bring-up | **8 MB octal PSRAM** (N8R8; the N8 without PSRAM is not suitable) |
| **Nucleo-H743ZI2** | candidate #2 (control) | 480 MHz, 1 MB SRAM, SDRAM optional (UI/granular), USB-FS on-board (HS PHY needed for UAC2 8×8) |

No audio jacks, DACs, panel or SD card are required for the DSP/UI/descriptor
part of the benchmark: the workload is computed in RAM and printed over USB
CDC/serial.  SD and USB-PHY checks need the hardware listed in §7.

Software:

- PlatformIO Core (here: `/tmp/msvenv/bin/pio`, `PLATFORMIO_CORE_DIR=/tmp/piocore`).
- ESP32: `platformio/espressif32` (S3).  P4: pioarduino / arduino-esp32 P4
  preview — official espressif32 8.0.0 has **no P4 board**.
- STM32: `platformio/ststm32` + STM32duino (`framework = arduino`).

## 2. Clock / memory configuration

| Board | CPU clock | PSRAM/SDRAM | Compiler flags |
|---|---|---|---|
| P4 | 400 MHz HP core (LP core idle) | 32 MB PSRAM @ full speed | `-O2 -DBUKIFON_BENCH_DEVICE -DBUKIFON_ESP32_P4` |
| S3 | 240 MHz | octal PSRAM 80 MHz | `-O2 -DBUKIFON_BENCH_DEVICE -DBUKIFON_ESP32_S3` |
| H743 | 480 MHz (CPU), 240 MHz AXI | SDRAM 100–200 MHz if fitted | `-O2 -DBUKIFON_BENCH_DEVICE -DBUKIFON_H743` |

The harness prints its own build tag and (on device) the timer source.  Add the
actual `esp_clk_cpu_freq()` / `HAL_RCC_GetHCLKFreq()` value to the capture log
manually if the board menuconfig changes the default — the comparison is only
valid at the frozen clocks above.

## 3. Build and flash

### ESP32-S3 (currently buildable in this repo)

```bash
export PLATFORMIO_CORE_DIR=/tmp/piocore
pio run  -d firmware -e bench_s3                 # build (verified: SUCCESS)
pio run  -d firmware -e bench_s3 -t upload       # flash the devkit
pio device monitor -b 115200 -p /dev/tty.usbmodem* | tee s3_bench.log
```

### ESP32-P4

Official `espressif32` 8.0.0 has no P4 target, so `bench_p4` is prepared but
cannot be built here.  On a machine with a P4-capable platform:

1. install pioarduino/arduino-esp32 P4 preview (URL in
   `firmware/platformio.ini`, commented `env:p4`);
2. uncomment `[env:bench_p4]` (it extends `bench_s3`), set `platform`/`board`;
3. `pio run -d firmware -e bench_p4 -t upload` and capture serial as above.

### STM32H743

```bash
pio platform install ststm32
pio run -d firmware -e bench_h743 -t upload      # env prepared (commented)
pio device monitor -b 115200 | tee h743_bench.log
```

The H743 env is commented in `firmware/platformio.ini`; uncomment it after
installing the platform.  STM32duino's `micros()` resolution is 1 µs — enough
for ~70–650 µs blocks, but the report notes this limitation.

## 4. Run and capture

The device build runs all scenarios once (2000 blocks, 100 warm-up) and prints:

1. a human-readable table (mean/max/p99/overruns/pass/determinism),
2. one JSON object (schema `bukifon-bench-v1`),
3. `RESULT: PASS|FAIL`.

Capture the whole serial log, then extract the JSON into
`firmware/bench/results/<board>.json` (copy the `{ ... }` block).  For the host
reference the same schema is written by:

```bash
make -C firmware/bench host      # -> firmware/bench/results/host.{json,csv}
```

**24-hour soak:** build the device env with
`-DBUKIFON_BENCH_SOAK_HOURS=24` (add to `build_flags`) and keep the board
powered; the device main runs the workload continuously, tracks overruns and
prints a status line every minute.  Acceptance: 0 overruns, 0 xruns, no reset,
PSRAM/SD error counters unchanged.  A 1-hour smoke run is the pre-check.

## 5. Reading the results

Primary metric — **max block time** of the audio scenarios (not mean):

| Scenario | Frozen deadline | Pass if max ≤ | Target p99 |
|---|---|---|---|
| `fm_voice` | 1333 µs | **650 µs** | ≤ 500 µs |
| `granular_track` | 1333 µs | **650 µs** | ≤ 500 µs |
| `mix_bus` | 1333 µs | **650 µs** | ≤ 500 µs |
| `psram_stream` | 1333 µs (runs inside a block) | **650 µs** | — |
| `ui_frame` | 33.3 ms | ≤ 33.3 ms (30 fps) | ≥ 30 fps |
| `ui_frame_partial` | 33.3 ms | target ≤ 16.7 ms (60 fps) | ≥ 60 fps |
| `usb_descriptor` | 2 ms build | ≤ 2 ms | — |

Also read:

- `overruns` — blocks slower than 1.333 ms; must be 0;
- `deterministic` and `checksum` — two runs with the same seed must match
  (a mismatch means the scenario touched non-deterministic state; treat the
  row as invalid);
- per-scenario `metrics`: `mb_per_s`/`ns_per_line` for PSRAM, `fps` for UI,
  `config_bytes`/`usb_fs_feasible`/`usb_hs_feasible` for USB.

**Headroom** = 1 − max_block / deadline.  The acceptance is ≥ 2× headroom
(max ≤ 48.75 % of the deadline).  Also compare the **worst** of 3 consecutive
runs, not a single lucky one.

## 6. Decision procedure

1. Run all scenarios 3× on each candidate (P4, H743), same build flags/clocks;
   take the worst max block time per scenario.
2. Reject a candidate if any audio scenario exceeds 650 µs, has p99 > 500 µs,
   or fails the 24 h soak with an overrun/underrun.
3. Check the non-audio gates: UI fps (full/partial) and display flush
   bandwidth; USB UAC2 8×8/24/48 (2.304 MB/s → HS PHY required; FS fails);
   PSRAM random-read throughput/latency for the granular working set; SD
   worst-case latency.
4. If both candidates pass audio, prefer the one that also passes display +
   HS USB with real hardware; keep the other as the control.  If only one
   passes audio, the decision is immediate; if neither, apply the roadmap
   cut-list (voice count / granular tracks / FX) before ordering boards.

Record the decision and all raw logs in `firmware/bench/results/` (JSON + log).

## 7. SD-card and USB-PHY extras (device only)

The host harness cannot test these; they are part of the P1 exit criteria:

- **SD worst case**: 8-track 16-bit mono streaming (768 KB/s) + one random
  4 KiB read per audio block (≈ 375 KiB/s), latency budget 10 ms, 1 h run,
  count underruns/sector errors (frozen pattern in workload §8).
- **USB UAC2**: 8 in / 8 out, 24 bit, 48 kHz = 2.304 MB/s; measure the real
  USB path on P4 (HS) and H743 with an HS PHY.  On S3 (FS) the UAC2 8×8 test is
  expected to fail by design; it is not a candidate.
- **Display flush**: full 800×480 RGB565 frame = 750 KiB; at 30 fps this is
  22.5 MB/s.  Measure P4 DSI/RGB+PPA vs H743 LTDC+DMA2D real fps.

## 8. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `ui_frame` prepare fails on S3 | no PSRAM in the board variant (need N8R8 / octal PSRAM); the 750 KiB framebuffer cannot fit internal SRAM |
| All-times look quantised on device | `micros()` resolution (1 µs); still fine for max-block criterion |
| Numbers much worse than expected | CPU governor/clock not at frozen value, PSRAM cache disabled, debug build (`-O0`), or USB serial logging inside the loop |
| P4 env does not resolve | official espressif32 has no P4; install pioarduino/arduino-esp32 P4 preview and uncomment `bench_p4` |
| H743 env not found | `pio platform install ststm32`, then uncomment `bench_h743` |
| Checksum mismatch | non-deterministic scenario (uninitialised state / RNG) — file a bug; do not compare that run |
| Host vs device numbers differ wildly | expected: host is only a workload sanity reference; decision is device-only |
