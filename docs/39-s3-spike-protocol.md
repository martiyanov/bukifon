# 39. S3 vertical-slice spike — protocol (lite concept platform)

**Status:** protocol ready, firmware skeleton builds (`spike_s3` SUCCESS); no
hardware results yet.
**Priority (round 6, customer decision):** the **first SKU is P4 with RGB565/DSI
+ HS USB**.  S3-base is the "lite later" platform.  This spike stays because it
exercises the **same subsystems** on a cheap devkit (PCM5102A/PCM1808, 1-bit SD,
USB composite, I2C panel scan) and produces the metrics PASS/FAIL pipeline.  The
SPI display path is S3-only; P4 numbers must be re-run with RGB565/DSI (§8).

Related: [rc-definition](36-rc-definition.md) §2 (acceptance criteria),
[core-s3 constraints](31-core-s3-constraints.md), firmware
[`firmware/spike_s3/README.md`](../firmware/spike_s3/README.md).

---

## 1. What this spike proves

One firmware image runs **audio + display + SD + USB composite + panel scan at
the same time** on the devkit and logs machine-readable metrics every second with
a docs/36 pass/fail verdict.  It does not implement the synth UI/engine beyond a
framebuffer pattern: the goal is to find integration limits (DMA, bus contention,
latency spikes) before the PCB.

| Subsystem | Hardware on the bench | Metric |
|---|---|---|
| Audio | PCM5102A DAC (out) + PCM1808 ADC (in), I2S0 | max/p99/mean block, xruns |
| Display | 800×480 SPI panel (ST7796/ILI9488 class) | full fps, partial updates/s, LCD drift |
| SD | microSD, 1-bit SDMMC | write+read latency, errors |
| USB | devkit native USB to PC | composite drops/reconnects |
| Panel | MCP23017 (I2C) 0x20–0x23, optional buttons | scan latency, errors |

## 2. Bench kit (devkit + peripherals)

| Item | Notes |
|---|---|
| ESP32-S3-DevKitC-1 with **N16R8** module | 16 MB flash, 8 MB octal PSRAM @80 MHz, native USB |
| 800×480 SPI display module (ST7796/ILI9488) | 3.3 V logic, FPC/adapter to dupont; BL needs its boost or a bench supply |
| PCM5102A breakout (I2S out) | MCLK optional; 3.3 V; line out to headphones/PC |
| PCM1808 breakout (I2S in) | 5 V analog supply per CORE-S3; 3.3 V logic |
| microSD breakout, 1-bit SDMMC | CLK/CMD/D0 + 3.3 V/GND |
| MCP23017 breakout (0x20, optional 0x21–0x23) | I2C 3.3 V, address pins |
| Bench PSU 5 V/2 A + USB cable + PC | USB provides power/flash/monitor; PSU for load-step test |
| Logic analyzer (optional) | I2S/SPI timing; not required for pass/fail |

## 3. Wiring (pins from `hardware/cores3/pinmap.csv`)

| Signal | GPIO | Connect to |
|---|---|---|
| LCD_SCK / MOSI / CS / DC / RST | 12 / 11 / 10 / 9 / 8 | panel SPI2 pins |
| BL_PWM | 21 | panel backlight PWM (or bench BL supply with series resistor) |
| SD_CLK / CMD / D0 | 15 / 14 / 13 | microSD CLK / CMD / DAT0, 1-bit mode |
| I2C0 SDA / SCL | 16 / 17 | MCP23017 SDA/SCL (4.7 kΩ pull-ups if the breakout lacks them), 400 kHz |
| I2S_MCLK / BCK / LRCK | 18 / 1 / 2 | PCM5102A SCK/BCK/LRCK and PCM1808 SCK/BCK/LRCK |
| I2S_DAC_DIN | 38 | PCM5102A DIN |
| I2S_ADC_DOUT | 39 | PCM1808 DOUT |
| MIDI_TX / RX | 40 / 41 | optional TRS-A DIN via 74HCT125/6N137 |
| GATE1 / PANEL_IRQ | 48 / 47 | optional panel signals |
| GND / 3V3 | — | common ground, 3.3 V logic; **do not feed 5 V into GPIO** |

Power: devkit via USB; codec/display 3.3 V from devkit or a separate LDO; PCM1808
analog 5 V from PSU.  Keep I2S wires short (<10 cm) for the first run.

## 4. Flash and run

```bash
export PLATFORMIO_CORE_DIR=/tmp/piocore
pio run -d firmware/spike_s3 -e spike_s3                     # build (verified SUCCESS)
pio run -d firmware/spike_s3 -e spike_s3 -t upload           # flash
pio device monitor -b 115200 | tee spike_s3.log
```

Run length via build flags (`platformio.ini` or `PLATFORMIO_BUILD_FLAGS`):

```bash
# audio/display stress 1 h, then USB soak 30 min
pio run -d firmware/spike_s3 -e spike_s3 \
  -D BUKIFON_SPIKE_AUDIO_SECONDS=3600 \
  -D BUKIFON_SPIKE_DISPLAY_SECONDS=3600 \
  -D BUKIFON_SPIKE_USB_SECONDS=1800 -t upload
```

The firmware prints:

- `SPIKE_CONFIG platform=s3-lite cpu=240 psram=80 lcd=800x480 bounce_rows=16 ...`
- `SPIKE_PINS ...` — the exact pin map in use;
- `SPIKE_READY display=1 sd=? panel=? usb=?` — honesty bits: `0` means a stub or
  a missing peripheral;
- one `SPIKE_METRIC ...` line per second;
- `SPIKE_RESULT pass=0|1 reason=... duration_s=...` at the end.

## 5. Test 1 — memory + audio + display stress (≥10 min, acceptance 1 h)

Purpose: bus/DMA contention and latency spikes with every subsystem active.

1. Wire display + both codecs + SD + panel; flash with audio/display phases =
   600 s (10 min quick check) or 3600 s (acceptance).
2. Keep USB attached (CDC log only) and do not open other heavy USB devices.
3. Watch `SPIKE_METRIC` every second; at the end read `SPIKE_RESULT`.

**PASS (docs/36 §2, tests 1–2):** `audio_max_us ≤ 650`, `audio_p99_us ≤ 500`,
`xruns = 0`; `full_fps ≥ 15`, `partial_per_s ≥ 30`, `lcd_drift = 0`; no watchdog
reset.  Any `SPIKE_STATUS pass=0` line is a lead to investigate (record the
reason and the raw log).

## 6. Test 2 — USB composite soak (30–60 min, acceptance 3)

Purpose: UAC2 stereo duplex + MIDI flood + HID + CDC simultaneously without
drops/reconnect.

1. Flash with USB phase 1800 s (30 min) / 3600 s (60 min).
2. On the PC: open the UAC2 device and play/record a 1 kHz file; flood MIDI with
   `amidi`/`sendmidi` loop; type on the HID keyboard; keep CDC monitor open.
3. After the run: `usb_drops = 0`, `usb_reconnects = 0`, no device re-enumeration.

**Current state:** TinyUSB composite is a stub (`BUKIFON_SPIKE_TINYUSB` not
enabled; counters are exercised and stay 0).  Test 2 becomes meaningful only
after enabling esp_tinyusb and the descriptor set; the protocol and log format
are ready for it.

## 7. Test 3 — power / load-step / thermal (acceptance 4)

Purpose: 3.3 V rail stability under audio+display+SD+USB peaks.

1. Power the devkit from the bench PSU (5 V) via a USB power tap or 5 V/VBUS
   breakout; set 5.0 V, 2 A limit.
2. Load-step: start the spike, then toggle full-frame flushes + maximum
   backlight + SD writes (the firmware already does all three); at the same time
   hot-plug USB audio and MIDI flood.
3. Measure 3.3 V at the devkit 3V3 pin: must stay **3.0–3.6 V**, no reset/pop;
   measure the buck-boost/DC-DC case: **≤80 °C**.
4. Run 10 min; log any brownout/reset (serial reconnect) and audio pops.

**PASS:** no reset/brownout, 3.3 V within 3.0–3.6 V, DC/DC ≤80 °C, no audible
pop at load steps.  (On the devkit the 3.3 V regulator is the devkit's own; the
product rail test is repeated on CORE-S3 rev.1.)

## 8. Test 4 — 24 h soak (acceptance 6, before release)

Run test 1 for 24 h (`-DBUKIFON_SPIKE_AUDIO_SECONDS=86400`), keep USB attached,
log every second, check free heap/PSRAM trend (`heap_free`, `psram_free`),
0 watchdog/xruns/drift, and no memory leak (free heap delta < 1 %).

## 9. How to read the log

```
SPIKE_METRIC audio_max_us=... audio_p99_us=... audio_mean_us=... audio_blocks=... xruns=...
             full_fps=... partial_per_s=... usb_drops=... usb_reconnects=...
             sd_max_us=... sd_errors=... panel_max_us=... panel_errors=...
             lcd_drift=... heap_free=... psram_free=...
SPIKE_RESULT pass=0|1 reason=... duration_s=...
```

Host parser: `tests/test_spike.cpp` (`SpikeLogParser`) — the same fields are
parsed in CI; use it to turn a captured log into a table.  Quick manual check:

```bash
grep -E 'SPIKE_(METRIC|RESULT|STATUS)' spike_s3.log | tail -20
```

## 10. Pass/fail summary (docs/36 §2)

| # | Test | Criterion | Spike metric |
|---|---|---|---|
| 1 | Audio stress | max ≤650 µs, p99 ≤500 µs, 0 xruns | `audio_*`, `xruns` |
| 2 | UI 10 min | full ≥15 fps, partial ≥30/s, 0 drift | `full_fps`, `partial_per_s`, `lcd_drift` |
| 3 | USB 30–60 min | 0 drops/reconnect | `usb_drops`, `usb_reconnects` |
| 4 | Power/load-step | 3.3 V 3.0–3.6 V, no reset/pop, DC/DC ≤80 °C | manual + `spike_s3.log` |
| 5 | SD recovery | pull card during write → project safe | manual (firmware logs `sd_errors`) |
| 6 | 24 h soak | 0 watchdog/xruns/drift, no leaks | `SPIKE_RESULT` + heap trend |
| 8 | Self-test | screen/buttons/encoders/CV/GATE/serial | manual on devkit |

## 11. Report form (paste into the spike ticket)

```
SPIKE S3-lite — <date> — commit <sha>
Board: ESP32-S3-DevKitC-1 N16R8, PSRAM 8 MiB, CPU 240 MHz
Peripherals: display <model>, DAC <model>, ADC <model>, SD <model>, MCP23017 <yes/no>
Run: audio/display <s>, USB <s>, 24h <yes/no>
Audio: max __ µs (<=650), p99 __ µs (<=500), mean __ µs, xruns __ (0), PASS/FAIL
Display: full __ fps (>=15), partial __ /s (>=30), drift __, PASS/FAIL
USB: drops __ (0), reconnects __ (0), PASS/FAIL
SD: max latency __ ms (<=10), errors __ (0)
Panel: max __ µs, errors __ (0)
Power: 3.3 V min/max __/__ V, reset __ (no), DC/DC __ °C
Log: <path/attachment>; anomalies: <spikes at ...>
SPIKE_RESULT: PASS/FAIL, reason: <...>
```

## 12. P4 transfer (first SKU)

The customer decision makes P4 the first SKU; S3 stays a lite concept platform.
The spike's **metric format, acceptance thresholds, codecs, SD, USB composite
stack and panel scan transfer unchanged**.  Differences to implement for P4:

| Aspect | S3-lite (this spike) | P4 first SKU |
|---|---|---|
| Display | SPI 800×480, 6 wires, ~13 fps full (D-51) | **RGB565/DSI 800×480**, 18–20 wires/DSI lanes, ≥15 fps full / ≥30 partial |
| Framebuffer | 750 KiB RGB565 + 16-row bounce | same 750 KiB + bounce; RGB/DSI + PPA/DMA2D flush |
| USB | FS 12 Mbps, stereo UAC2 only | **HS 480 Mbps, 8×8 UAC2** + HID/MIDI/CDC |
| CPU/RAM | 240 MHz LX7, 8 MiB PSRAM | 400 MHz dual RISC-V, 32 MiB PSRAM |
| P1 profile | `s3_profile` (SPI model, max block) | **`p4_profile`** (RGB565 + 8 voices + 8 stereo tracks + HS 8×8 + 24 h soak) |

Switching the spike to P4: keep `spike_core.hpp`/metrics/log/parser; replace the
display flush in `spike_main.cpp` (`flushRows` SPI → RGB565/DSI backend, update
`kLcdSpiHz`/frame timing), enable HS TinyUSB composite, and build with a
P4-capable PlatformIO platform.  The P4 env is prepared/commented in
`firmware/spike_s3/platformio.ini` (official `espressif32` 8.0.0 has no P4 board).

**UI note:** the 800×480 UI and the four device-mode panels are identical for
S3-lite and P4; only the display backend (SPI vs RGB565/DSI) differs.
