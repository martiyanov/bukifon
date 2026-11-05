# 05. P1 benchmark — frozen workload (v1.0, 2026-11-05)

**Status:** frozen for the P1 MCU decision (ESP32-P4 vs STM32H743).
**Owner:** firmware. **Related:** [roadmap](12-roadmap.md) §P1,
[howto](05a-benchmark-howto.md), harness `firmware/bench/`, results
`firmware/bench/results/host.json`.

This document is the single source of truth for *what* is measured.  The
harness implements exactly this workload; scenario names in the code
(`fm_voice`, `granular_track`, `mix_bus`, `psram_stream`, `ui_frame`,
`ui_frame_partial`, `usb_descriptor`) are part of the contract.  Any change to
the workload requires a version bump and a re-run on **both** candidate
platforms — otherwise the P4/H743 numbers are not comparable.

---

## 1. Goal and decision context

P1 must answer: *which MCU can run the v1.0 firmware workload in real time, with
headroom, and show the 800×480 UI?*  The benchmark is a **frozen worst-case
workload**, not a benchmark of individual instructions.  It is deliberately
harder than a typical project ("maximum" project: 8 tracks + 8 voices + all FX).

**Reference candidate hardware**

| Platform | CPU | Expected RAM | Display path | USB |
|---|---|---|---|---|
| ESP32-P4 | 2× RISC-V HP @ up to 400 MHz, LP core | 768 KiB SRAM + up to 32 MiB PSRAM | MIPI-DSI / RGB + PPA | HS USB 2.0 |
| STM32H743 | Cortex-M7 @ 480 MHz | 1 MiB SRAM + SDRAM | LTDC + DMA2D | FS USB 2.0 |
| ESP32-S3 (reference only) | 2× LX7 @ 240 MHz | 512 KiB + PSRAM | RGB via LCD_CAM | FS USB 2.0 |

S3 is a **reference**, not a candidate for UAC2 8×8/24/48 (Full-Speed cannot
carry the required 2.304 MB/s; see §7).

## 2. Measurement protocol

- Audio block: **64 frames @ 48 kHz** = **1.333 ms** deadline.
- Sample format: float32 internally; timing includes the complete per-block DSP
  (oscillators, filters, envelopes, LFOs, effects, mixing, limiter).
- Pass criterion (frozen): **max block time ≤ 0.65 ms** (≤ 48.75 % of the
  deadline) and **0 overruns** (blocks > 1.333 ms).
- Target: p99 ≤ 0.5 ms; typical project should stay ≤ 60 % of the maximum.
- Measurement: 100 warm-up blocks are excluded, then 2000 blocks are timed
  individually.  Reported: min / max / mean / p50 / p95 / p99, overrun count,
  deadline utilisation.
- Determinism: every scenario produces a checksum (FNV-1a over output samples
  or descriptor bytes).  Two runs with the same seed must produce the same
  checksum; a mismatch fails the run.
- Real-time hygiene: **processBlock() must not allocate, lock, log or perform
  I/O**.  The host test suite arms an allocation probe around audio-path blocks
  and expects **0 allocations**.
- Timing source: host = `steady_clock` (ns); device = `micros()` (1 µs
  resolution).  On devices the max block time is the decision metric; mean is
  not.
- Host runs are a **reference/sanity check of the workload and harness**, not a
  device verdict.  The decision is made from P4/H743 device runs only.
- 24-hour soak (device): run the maximum workload continuously, log every
  overrun and every max-block event, record CPU temperature, PSRAM errors and
  audio xruns.  Acceptance: **0 xruns, 0 overruns** in 24 h (a 1 h smoke run is
  the pre-check).

## 3. Scenario `fm_voice` — 8 synth voices

Eight identical-architecture voices, each with:

- **4-operator FM** (`FmCore`, spec/40 §2.1): algorithm `voice % 8` (all eight
  algorithms exercised), ratios `{1, 1, 2, 3}`, levels `{1.0, 0.35, 0.30, 0.25}`,
  feedback `0.15`, **2× oversampling** with the built-in decimation filter.
- **Wavetable oscillator** (2048×8 mip bank, cubic interpolation, wave
  `voice % 8`), detuned +3 cents, unison 1.
- Note frequencies: MIDI notes 48, 50, 52 … 62 (8 voices, 2 semitones apart).
- **Moog-style ZDF ladder**: 4-pole (24 dB), cutoff `900 + 160·voice` Hz,
  resonance 0.65, drive 0.20, coefficients updated **once per block** from
  LFO1/LFO2 modulation (`cutoff · 2^(lfo·2)`).
- **4 ADSR envelopes** per voice (sample-accurate): env0 = amplitude
  (A = 4+1·e ms, D = 150+20·e ms, S = 0.55, R = 250 ms, curve −0.15);
  env1/env2/env3 are summed as a slow modulation term (0.8 + 0.2·mod).
  All four are ticked every sample.
- **3 LFOs** per voice (block-rate update): rates 0.6 / 0.85 / 1.1 Hz, shapes
  sine / saw-up / square, free-running (no retrigger, no keytrack).
- Mix: FM 65 % + wavetable 35 %, per-voice equal-power pan alternating ±0.4.

Per block: 8 voices × 64 samples = 512 voice-samples; 4 FM operators × 2×
oversampling → 4096 FM operator evaluations per block (plus decimation filters).

## 4. Scenarios `granular_track` and `mix_bus` — 8 mono tracks

### 4.1 `granular_track` (sampler-heavy part)

- 8 mono tracks, 4 grains per track, **grain size 2048 samples**, Hann window
  (pre-computed table), **4-point Catmull-Rom interpolation**, phase increment
  `1/2048` per sample, new random grain position on wrap.
- Sample working set: **4 MiB float** (1 048 576 samples, power of two) — on
  the device this must live in **PSRAM**; the host uses DRAM as a proxy.
  Positions are random ⇒ cache-miss/PSRAM-random-read behaviour is exercised.
- Per track: TPT SVF (LP24, cutoff `700 + 140·t` Hz, res 0.45), insert drive
  `tanh(1.4·x)·0.7`.
- **2 send buses**: fixed 250 ms and 375 ms delays, feedback 0.30 / 0.25,
  returns mixed at 0.25/0.18 (L) and 0.22/0.20 (R).
- Master: soft limiter (threshold 0.95, release 0.2 s).
- Random source: xorshift32 seeded with `0xB0C0FFEE` (frozen seed); block
  checksum must match between runs.

### 4.2 `mix_bus` (mixing/effects half)

- 8 mono tracks, sine oscillators at 220 + 40·t Hz, per-track SVF LP12
  (cutoff `1200 + 300·t` Hz, res 0.3), insert `tanh(1.3·x)`.
- Same 2 send buses (250/375 ms, feedback 0.30/0.25) and master limiter as
  above.
- Represents the case where the voice/granular load is lower but the desk is
  fully loaded.

## 5. Scenario `psram_stream` — random-read pattern

- Buffer: **8 MiB**, 64-byte-aligned lines, filled from xorshift32
  (seed `0xB0C0FFEE`).
- Per 64-sample block: **512 random 64-byte line reads** (8 tracks × 4 grains ×
  16 lines), each summed into a checksum.  At 750 blocks/s this represents
  **24.576 MB/s** of random PSRAM traffic (the granular working set).
- Reported: ns per line, MB/s, working-set size, checksum.
- Host: DRAM proxy (fast, not representative of PSRAM latency).  **On device
  this scenario must use the real PSRAM** (S3 octal PSRAM / P4 PSRAM / H743
  external SDRAM), and the reported ns/line and MB/s are the P1 numbers to
  compare.
- Also reported on device: sustained sequential throughput and 4 KiB random
  latency (informational, not a pass criterion).

## 6. Scenario `ui_frame` / `ui_frame_partial` — 800×480 UI

- Framebuffer: **800×480 RGB565 = 750 KiB**.
- `ui_frame`: full redraw of the UI shell (status bar with BPM/patch/status/mode,
  4 track strips, parameter panel, transport row, encoder hints) from a
  snapshot.
- `ui_frame_partial`: 4 dirty rectangles (header, one track card, parameter
  panel, hint row) — the planned production update path.
- Measured per frame; criterion **30 fps** (≤ 33.3 ms/frame) for full redraw,
  **60 fps** target for partial.  On device also measure display flush:
  full-frame 750 KiB at 30 fps = **22.5 MB/s** (RGB/DSI/DMA2D path), and
  partial flush proportionally less.
- UI must be a pure function of the snapshot (no engine state ownership) — this
  is enforced by the code structure (`UiSnapshot` → `drawUi800`).

## 7. Scenario `usb_descriptor` — USB composite and UAC2 feasibility

- Descriptor set: **HID keyboard (42 keys, 6KRO) + MIDI class + UAC2 stereo
  + CDC**, built by `usb/usb_descriptors.cpp`; measured: descriptor build time,
  config bytes, interfaces, endpoints.
- Bandwidth check, UAC2 **8 in / 8 out, 24 bit, 48 kHz**:
  `8 ch × 3 B × 2 directions × 48000 = 2.304 MB/s`.
  - USB Full-Speed isochronous is ~1 MB/s in practice → **S3 cannot pass**
    (this is why S3 is reference-only).
  - USB High-Speed (P4, H743 with HS PHY) has ample headroom → pass.
- The benchmark does not exercise the USB PHY; it freezes the descriptor and
  bandwidth requirement, and validates the descriptor builder on the host.

## 8. SD card worst case (device-only, not in host harness)

The host harness has no SD.  For P4/H743 device runs the frozen pattern is:

- Sustained 8-track 16-bit mono streaming: `8 × 2 B × 48000 ≈ 768 KB/s`.
- Worst-case random 4 KiB read **once per audio block** (≈ 375 KiB/s
  additional) with a **10 ms** SD latency budget: audio must keep running from
  a preload buffer and must not glitch; count underruns.
- Report: max SD latency, underruns during 1 h, sector errors.  Pass: 0
  underruns, no block overrun.

## 9. Pass/fail and MCU decision rules

### 9.1 Per-scenario criteria (frozen)

| Scenario | Deadline | Max block/frame | Overruns |
|---|---|---|---|
| `fm_voice`, `granular_track`, `mix_bus`, `psram_stream` | 1333.3 µs | **≤ 650 µs** | 0 |
| `ui_frame` | 33.3 ms | ≤ 33.3 ms (30 fps) | 0 |
| `ui_frame_partial` | 33.3 ms | ≤ 16.7 ms (60 fps) target | 0 |
| `usb_descriptor` | 2 ms (build only) | ≤ 2 ms | 0 |

A platform is **audio-capable** when, on the device run: all audio scenarios
pass the 650 µs criterion, p99 ≤ 500 µs, and a 24 h soak shows 0 xruns.

### 9.2 Decision matrix

| Question | P4 threshold | H743 threshold |
|---|---|---|
| Audio max block (max scenario) | ≤ 650 µs at 400 MHz | ≤ 650 µs at 480 MHz |
| Audio headroom | ≥ 2× to deadline (≤ 50 %) | ≥ 2× |
| PSRAM random read | ≥ 40 MB/s at ≤ 250 ns/line (or streaming path proven) | SDRAM ≥ 60 MB/s |
| UI 800×480 | ≥ 30 fps full, ≥ 60 fps partial with DSI/RGB+DMA | ≥ 30 fps with LTDC+DMA2D |
| USB UAC2 8×8/24/48 | HS required (2.304 MB/s) | HS PHY required (FS insufficient) |
| BLE/Wi-Fi | P4: via ESP32-C6 coprocessor (extra link) | H743: external module |
| Ecosystem/toolchain risk | P4 platform young (preliminary) | mature STM32 ecosystem, but display/USB-HS wiring |

**Selected:** the platform with the lower worst-case block time **and** both
display and HS-USB paths verified; if both pass audio but fail different
peripherals, cut-list decides (P4 preferred for the display/USB, H743 as the
control candidate if P4 silicon/SDK is not stable).

## 10. Workload versioning

- **v1.0 (2026-11-05):** initial freeze corresponding to harness schema
  `bukifon-bench-v1`.  Host reference results: `firmware/bench/results/host.json`.
- Changing any parameter in §3–§7 requires **v1.1+**, updating the harness and
  re-running P4 and H743; checksums are the identity of a workload run.
- Harness limitations: host has no PSRAM/SD/USB-PHY, so PSRAM/SD/USB scenarios
  are host-proxy/descriptor-only; device envs are prepared in
  `firmware/platformio.ini` (`bench_s3` built; `bench_p4`/`bench_h743`
  prepared, need their platforms installed — see [howto](05a-benchmark-howto.md)).
