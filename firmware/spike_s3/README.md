# S3 vertical-slice spike (lite concept platform)

> **Priority note (round 6):** the customer decision is that the **first SKU is
> P4 with RGB565/DSI + HS USB**.  S3-base is the "lite later" platform.  This
> spike stays because it validates the **same subsystems** on cheap devkit
> hardware: PCM5102A/PCM1808 over I2S, 1-bit SD, USB composite, I2C panel scan.
> Display numbers here are SPI-only and do **not** transfer to P4 (see
> [P4 transfer](#p4-transfer) below).  The UI is identical for S3-lite and P4 —
> only the display backend (SPI vs RGB565/DSI) and USB PHY differ.

Standalone firmware skeleton for the devkit spike (before PCB).  One cooperative
loop exercises audio + display + SD + USB + panel simultaneously and logs
machine-readable metrics with a docs/36 pass/fail verdict.

## What it measures

| Subsystem | What runs | Metric |
|---|---|---|
| Audio | PCM1808 in → PCM5102A out loopback (I2S), 64-frame blocks | `audio_max_us`, `audio_p99_us`, `audio_mean_us`, `xruns` |
| Display | 800×480 SPI, full flush in 16-row bounce batches + dirty-rect partial updates | `full_fps`, `partial_per_s`, `lcd_drift` |
| SD | 1-bit SDMMC 4 KiB write+read roundtrip every 5 s | `sd_max_us`, `sd_errors` |
| USB | TinyUSB composite UAC2 stereo + MIDI + HID + CDC; 4 KiB RX/TX FIFOs | `usb_drops`, `usb_reconnects` |
| Panel | I2C MCP23017 0x20–0x23 GPIOA scan every 10 ms | `panel_max_us`, `panel_errors` |

Acceptance criteria are taken from [`docs/36`](../../docs/36-rc-definition.md) §2:
audio `max ≤650 µs`, `p99 ≤500 µs`, 0 xruns; UI full ≥15 fps / partial ≥30
updates/s; USB 0 drops/reconnect; SD latency ≤10 ms and 0 errors; panel 0 errors.
24 h soak is the device acceptance test; this firmware logs the per-second metrics
for it.

## Build / flash

```bash
# build (ESP32-S3-WROOM-1-N16R8, 16 MB flash, octal PSRAM 80 MHz)
PLATFORMIO_CORE_DIR=/tmp/piocore pio run -d firmware/spike_s3 -e spike_s3
# flash + monitor
PLATFORMIO_CORE_DIR=/tmp/piocore pio run -d firmware/spike_s3 -e spike_s3 -t upload
pio device monitor -b 115200 | tee spike_s3.log
```

Run length is set by build flags (defaults 60 s each):
`-DBUKIFON_SPIKE_AUDIO_SECONDS=3600` (1 h audio/display stress),
`-DBUKIFON_SPIKE_USB_SECONDS=1800` (30 min USB soak).  Wiring, three tests and
the report form: [`docs/39-s3-spike-protocol.md`](../../docs/39-s3-spike-protocol.md).

## Host simulation (no hardware)

```bash
bash firmware/spike_s3/run_host_spike.sh     # builds spike_sim, prints SPIKE_METRIC/RESULT
```

The host simulation uses the same buffers, metrics and pass/fail logic as the
devkit firmware; it is the CI gate for the spike code and the parser format.
`make -C firmware/host test` covers buffers/parsers/metrics (`tests/test_spike.cpp`).

## Pins (hardware/cores3/pinmap.csv)

| Function | GPIO | Notes |
|---|---|---|
| LCD SCK/MOSI/CS/DC/RST | 12 / 11 / 10 / 9 / 8 | SPI2 |
| LCD backlight | 21 | LEDC PWM → BL boost |
| SD CLK/CMD/D0 | 15 / 14 / 13 | 1-bit SDMMC |
| I2C0 SDA/SCL | 16 / 17 | MCP4728×2, 24C32, PANEL-2, MCP23017 |
| I2S MCLK/BCK/LRCK/DAC/ADC | 18 / 1 / 2 / 38 / 39 | PCM5102A out, PCM1808 in |
| MIDI TX/RX | 40 / 41 | UART1 31250 |
| PANEL_IRQ / GATE1 | 47 / 48 | — |
| PWR_GOOD / BOOT | 3 / 0 | — |

## Ready for hardware vs stubs

**Ready (real code / real metrics):** SPI display flush timing (full + partial),
16-row bounce staging, SD 1-bit write/read latency, I2C MCP23017 scan latency,
audio block timing/xruns, metrics + docs/36 pass/fail + log format, host parser.

**Stubs (honest `TODO(hw)`):** I2S driver init/read/write (synthetic loopback is
timed; enable `BUKIFON_SPIKE_USE_I2S` after wiring), TinyUSB composite
configuration (`BUKIFON_SPIKE_TINYUSB`; counters exercised, always 0 for now),
panel controller init sequence (ST7796/ILI9488 MADCTL/gamma), SD card-detection
(none on CORE-S3), backlight PWM curve.

## P4 transfer

The first SKU is P4.  What transfers unchanged: codecs (I2S), SD (SDMMC), USB
composite stack, MCP23017 panel scan, audio/UI code, the metric/log/parser
format and the docs/36 acceptance criteria.  What changes:

| Aspect | S3-lite spike | P4 first SKU |
|---|---|---|
| Display | SPI 800×480, 6 wires, ~13 fps full (D-51) | **RGB565/DSI 800×480**, 18–20 wires, ≥15 fps full / ≥30 partial |
| Framebuffer | one 750 KiB RGB565 + 16-row bounce | same 750 KiB + bounce, but RGB/DMA (PPA) flush |
| USB | FS 12 Mbps: stereo UAC2 only (D-48) | **HS 480 Mbps: 8×8 UAC2** + HID/MIDI/CDC |
| CPU | 240 MHz LX7 | 400 MHz RISC-V dual-core |
| PSRAM | 8 MiB octal @80 MHz | 32 MiB |
| Firmware switch | `spike_main.cpp` display flush + `kLcdSpiHz` | replace flush with RGB565/DSI backend; enable HS TinyUSB; same metrics |

A P4 env is prepared in `platformio.ini` (commented: official `espressif32` 8.0.0
has no P4 board/framework; use pioarduino/arduino-esp32 P4 preview).  The
`bench` harness already has `p4_profile` / `host_p4.json` so the P1 stand can be
run immediately after the P4 devkit arrives.

## Known limitations

- No hardware has been run yet: all numbers above are code paths + host
  simulation, not devkit measurements.
- The bare devkit has no panel expander: `panel_errors` grows (expected) until an
  MCP23017 is wired; SD errors grow without a card.
- SPI full refresh model is ~13 fps (D-51) — S3-lite cannot meet the ≥15 fps full
  criterion; partial-redraw is the fallback.  P4/RGB565 is the primary answer.
