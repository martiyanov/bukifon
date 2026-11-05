# Bukifon P1 benchmark harness

Portable C++17 benchmark for the **P1 MCU decision** (ESP32-P4 vs STM32H743).
It implements the frozen workload from
[`docs/05-benchmark-workload.md`](../../docs/05-benchmark-workload.md); the
how-to for the three devkits is
[`docs/05a-benchmark-howto.md`](../../docs/05a-benchmark-howto.md).

## What it measures

Block 64 frames @ 48 kHz (deadline **1.333 ms**), pass criterion
**max block ≤ 0.65 ms** and **0 overruns**.  Every scenario is deterministic
(seeded xorshift32, FNV-1a checksum), and the audio path is checked for
allocations by the host tests.

| Scenario | Workload |
|---|---|
| `fm_voice` | 8 voices × [4-op FM (8 algorithms, feedback, 2× oversampling) + wavetable + Moog ZDF ladder + 4 ADSR + 3 LFO] |
| `granular_track` | 8 tracks × [4 grains (2048 smp, Hann, 4-pt interpolation) + SVF + insert + 2 sends + master limiter], random reads from a 4 MiB working set |
| `mix_bus` | 8 track inserts + 2 send buses (250/375 ms) + master limiter |
| `psram_stream` | 512 random 64-byte line reads per block from an 8 MiB buffer (granular working set, ≈24.6 MB/s) |
| `ui_frame` | full 800×480 RGB565 UI redraw (snapshot-driven shell) |
| `ui_frame_partial` | 800×480 partial redraw (4 dirty rectangles) |
| `usb_descriptor` | USB composite descriptor build (HID keyboard + MIDI + UAC2 + CDC) and UAC2 8×8/24/48 bandwidth feasibility (2.304 MB/s) |

Reported per scenario: min/max/mean/p50/p95/p99 block time, overruns vs the
real-time deadline, determinism (two runs, same checksum), per-scenario metrics
(PSRAM MB/s and ns/line, UI fps, USB descriptor sizes/feasibility), pass/fail.

## Run on host (verified)

```bash
make -C firmware/bench host        # builds + runs, writes results/host.{json,csv}
# or with control over the run:
./firmware/bench/build/bukifon_bench --scenario fm_voice --blocks 2000 \
    --json firmware/bench/results/host.json --csv firmware/bench/results/host.csv
```

Latest host reference (macOS arm64, Apple clang 21, `-O2`) is stored in
[`results/host.json`](results/host.json).  Host timings are a **workload sanity
reference**, not a device verdict.

## Run on devices

| Environment | Status in this repo | Command |
|---|---|---|
| `bench` (native) | builds (same as Makefile target) | `pio run -d firmware -e bench` |
| `bench_s3` (ESP32-S3 DevKitC-1) | **builds** (Flash 17.7 %, RAM 6.8 %) | `pio run -d firmware -e bench_s3 -t upload` |
| `bench_p4` | **prepared, not buildable** — official `espressif32` 8.0.0 has no P4 board/framework; uncomment after installing a P4-capable platform | see `docs/05a` |
| `bench_h743` (Nucleo-H743ZI2) | **prepared, not buildable here** — needs `pio platform install ststm32`; uncomment the env | see `docs/05a` |

The device build prints the same table + JSON over USB serial at 115200 baud.
24 h soak: add `-DBUKIFON_BENCH_SOAK_HOURS=24` to the env build flags; the device
main then runs the workload continuously and reports overruns per minute.

## Tests

The harness is covered by `firmware/tests/test_bench.cpp` (part of the 120
host tests):

- frozen constants (block/deadline/criterion, UI and USB numbers);
- pass/fail criterion unit tests (max block, overrun, UI vs audio criteria);
- scenario registry (all frozen names present);
- determinism of every scenario (two runs → identical checksum);
- **zero allocations in the audio path** (global `operator new` probe armed
  around `processBlock()` for `fm_voice`, `granular_track`, `mix_bus`);
- JSON/CSV/table rendering, PSRAM/UI/USB metrics;
- full/partial UI frame criteria.

## Limitations (honest)

- Host has no PSRAM, SD, USB PHY or display bus: `psram_stream` is a DRAM proxy,
  `usb_descriptor` validates bytes/bandwidth only, UI measures CPU draw time, not
  panel flush.
- Device timing uses `micros()` (1 µs resolution); max block time is still
  meaningful, but sub-µs jitter is not visible.
- `ui_frame` needs a 750 KiB framebuffer → requires PSRAM on S3/P4; without it
  `prepare()` fails and the row is reported as failed.
- SD worst case and USB UAC2 HS are device/hardware procedures (docs/05 §8,
  docs/05a §7), not part of the host harness.
