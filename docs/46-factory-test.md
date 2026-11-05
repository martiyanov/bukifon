# 46. Factory self-test — P4 first SKU (bring-up + EOL)

**Status:** firmware self-test core + host CLI/mocks ready; **P4 build not
possible in this environment** (official `platformio/espressif32` 8.0.0 has no
P4 board/framework — env `p4` is prepared/commented in `firmware/platformio.ini`
with the attempted result).  Real hardware access methods are explicit
`TODO(hw)` stubs; the production run below becomes hardware-meaningful when the
P4 toolchain and the CORE-2 board are available.

Related: [DFM/DFT review](42-dfm-review-gpt.md) §2–3, [RC definition](36-rc-definition.md),
CORE-2 pin map `hardware/core2/pinmap.md`, firmware
[`firmware/src/factory/`](../firmware/src/factory/).

## 1. What it is

A 14-test factory sequence (docs/42 §2) that runs at end-of-line (and for
bring-up) and produces a machine-readable **PASS/FAIL JSON** report:

- automatic part: ~**38 s** nominal (sum of test times);
- with operator checks (display patterns + controls): target **2–2.5 min**
  automatic+operator per unit; full EOL cycle with flashing/label/packing
  **6–8 min** (docs/42 §2);
- timeouts per test (3× nominal + 500 ms) → `TIMEOUT` status;
- host CLI/mocks for CI and station dry-runs; P4 hardware classes are stubs.

## 2. Run

### 2.1 Host (no hardware) — mock station

```bash
make -C firmware/host factory          # builds build/bukifon_factory and runs --json
firmware/host/build/bukifon_factory --json
firmware/host/build/bukifon_factory             # human table
firmware/host/build/bukifon_factory --out report.json
firmware/host/build/bukifon_factory --stop-on-fail
```

The host run uses `MockHardware` (all values PASS by default).  Exit code 0 =
PASS, 1 = FAIL/TIMEOUT, 2 = usage error.  The mock is the CI gate for the
runner/validators/JSON/CLI; it is **not** a hardware test.

### 2.2 Device (P4, once the toolchain exists)

1. Enable the P4 env (`firmware/platformio.ini`, currently commented) or the
   `p4_factory` comment block; implement `P4FactoryHardware` methods
   (`firmware/src/factory/p4_hardware.cpp`, all `TODO(hw)`):
   power/reset reason, I2C scan, MCP23017/MCP3208/MCP4728, codec loopback,
   SD scratch, display patterns, WS2812 current, MAX17048, USB composite,
   controls, CV/GATE loopback, MIDI loopback;
2. flash over USB HS / ROM bootloader, open CDC serial at 115200;
3. run `factory --json` (CDC CLI) or press the station button; capture JSON;
4. station software stores the report and writes identity (see §6).

> `pio run -d firmware -e p4` today returns `Unknown environment names 'p4'`
> because the env is intentionally commented: the installed platform has no P4
> board definition.  On a P4-capable platform uncomment and set board.

## 3. Fixture / loopback plug (founders beta)

One plug per unit, inserted before the automatic run:

| Connection | Wire / parts |
|---|---|
| CV OUT1–4 → CV IN1–4 | 4× 10 kΩ series (protect inputs; 0–4 V range) |
| GATE OUT → GATE IN | 4.7 kΩ / 10 kΩ divider (5 V → ~3.4 V at panel input) |
| LINE OUT → AUDIO IN | 10–20 kΩ series (as docs/42) |
| MIDI OUT → MIDI IN | standard DIN/TRS-A loopback cable |
| Fixture ID | resistive signature on the panel ID pin (TODO: value table) |

Panel/controls: acrylic comb for 42 keys (groups 6–7), one click CW/CCW + press
per encoder.  Display: operator confirms RGB/white/black/checker with no bands.

## 4. Tests, criteria, timing (docs/42 §2)

| # | Test | Nominal | PASS criterion |
|---:|---|---:|---|
| 1 | Power-on + brownout log | 1.0 s | 1 power-on reset reason, PWR_GOOD high, 0 brownouts |
| 2 | I²C scan | 0.3 s | exactly addresses `0x20–0x23, 0x36, 0x57, 0x60, 0x61` |
| 3 | MCP23017 walking-bit | 1.5 s | 4 addresses ACK, PANEL_IRQ toggles |
| 4 | MCP3208 fixture vector | 0.8 s | 8 channels 0.25/1.25/2.50 V, ±2 LSB |
| 5 | MCP4728→MCP3208/CV loopback | 1.5 s | 0–4 V, error ≤20 mV after calibration |
| 6 | Codec loopback | 2.0 s | 1 kHz, −12 dBFS, gain ±1 dB, THD+N < −60 dB |
| 7 | SD scratch-file | 1.5–2.5 s | 1 MiB write/read + CRC32, ≥0.7 MB/s |
| 8 | Display patterns | 1 s + 2 s operator | RGB/white/black/checker, no bands (operator) |
| 9 | WS2812 chase/current | 1.0 s | all LEDs, current ±20 % of expected |
| 10 | MAX17048 | 0.4 s | VCELL vs DMM ≤30 mV |
| 11 | USB composite enum | 2.5 s | CDC+MIDI+HID+UAC enumerated |
| 12 | Controls | 20 s | 42 keys, 16 encoders (A/B/SW), 2 faders |
| 13 | CV/GATE external loopback | 3.0 s | 4 CV OUT→IN ≤20 mV, GATE loopback OK |
| 14 | MIDI DIN loopback | 1.0 s | 100 packets, 0 errors |

Automatic total ≈ **38 s**; with operator checks the target EOL is **2–2.5 min**
per unit.  Any FAIL/TIMEOUT blocks packing (station gate, exit code 1).

## 5. Report JSON (schema `bukifon-factory-selftest-v1`)

Example (all PASS, host mock):

```json
{
  "schema": "bukifon-factory-selftest-v1",
  "product": "BUKIFON",
  "factory_version": "0.1.0",
  "overall_pass": true,
  "total_ms": 38000,
  "count": 14, "pass": 14, "fail": 0, "timeout": 0, "skip": 0,
  "tests": [
    {"id": 0, "name": "power_on", "status": "PASS", "nominal_ms": 1000,
     "duration_ms": 1000, "detail": "reset reason POWERON, PWR_GOOD high, 0 brownouts"},
    {"id": 1, "name": "i2c_scan", "status": "PASS", "nominal_ms": 300,
     "duration_ms": 300, "detail": "addresses 0x20-0x23,0x36,0x57,0x60,0x61 present"}
  ]
}
```

Statuses: `PASS`, `FAIL`, `TIMEOUT`, `SKIP`.  The report is written to
`firmware/tests/out/factory_report.json` by `make factory`, or passed to the
station with `--out`.

## 6. Serial / QR / traceability (docs/42 §3)

- **No separate serial EEPROM**: CORE has 24C32 at `0x57` for calibration data.
- Identity lives in flash `factory_data` (8–16 KiB, **two copies + CRC32**):
  magic, version, product, serial (`BKS3-26A-0001` uniq), CORE/PANEL/PWR
  revisions, build date, PCB/assembly batch, display MPN/lot, factory firmware
  version, calibration version, test station, test timestamp/result, MAC
  (eFuse anchor), CRC32.
- Read: `factory info` (CDC CLI) / `factory --json`; boot log prints a short
  line.  QR on the case sticker: serial + revisions only (no personal data).
- Writing identity/QR is **TODO(hw)** on P4: host mock models the fields but
  does not program flash/24C32.  Factory reset must not erase calibrations.

## 7. Real vs mock (honesty table)

| Part | Status |
|---|---|
| 14-test runner, timeouts, PASS/FAIL/TIMEOUT | **real, host-tested** |
| Validators (addresses, voltages, CRC, current, classes, counts) | **real, host-tested** |
| JSON schema/report, CLI (`--json`, `--out`, `--stop-on-fail`, exit codes) | **real, host-tested** |
| Host `MockHardware` | real mock (deterministic, failure/timeout injection) |
| `P4FactoryHardware` (I2C/ADC/DAC/codec/SD/display/USB/controls/CV/MIDI) | **stubs `TODO(hw)`** — return false, no fabricated PASS |
| Flash `factory_data` / 24C32 identity / QR | **TODO(hw)** |
| Real P4 build | **not possible here** (no P4 PlatformIO board/framework) |

## 8. Risks / notes

1. **P4 toolchain unavailable** → the device run is untested; the env is
   prepared and commented, no false build claim.
2. Timings above are **nominal from docs/42**, not measured on hardware; the
   host mock uses the same nominal durations.
3. Operator-dependent tests (display patterns, controls) need a station UI;
   `--stop-on-fail` is available for repair-loop debugging.
4. USB composite enumeration and codec loopback depend on TinyUSB/I2S drivers
   that are still stubs in the spike/firmware (see docs/39).
5. Production fixture still needs the resistive fixture-ID signature and
   calibrations written to 24C32; not modelled in the host CLI.

---

## 9. Enabling real backends on the bench (bring-up order)

Host/CI runs all backends as **MOCK**.  On the stand, real drivers are enabled
**one backend at a time**; after every step run the self-test and only proceed
when the newly real tests PASS.  Compile-time defaults live in
`firmware/src/factory/hw_backends.hpp` (`BUKIFON_HW_<NAME>` = `BUKIFON_HW_MOCK`
or `BUKIFON_HW_REAL`), runtime switching uses `HwConfig` + `HybridHardware`.

Build with individual backends real (repeat `-D` per subsystem):

```bash
# example: first I2C only (everything else stays MOCK)
pio run -d firmware -e p4 \
  -D BUKIFON_HW_I2C=BUKIFON_HW_REAL
# next: panel/controls + I2C
  ... -D BUKIFON_HW_CONTROLS=BUKIFON_HW_REAL
# codec, display, SD, USB, CV/MIDI in that order
  ... -D BUKIFON_HW_I2S=BUKIFON_HW_REAL
  ... -D BUKIFON_HW_DISPLAY=BUKIFON_HW_REAL
  ... -D BUKIFON_HW_SD=BUKIFON_HW_REAL
  ... -D BUKIFON_HW_USB=BUKIFON_HW_REAL
  ... -D BUKIFON_HW_CV=BUKIFON_HW_REAL -D BUKIFON_HW_MIDI=BUKIFON_HW_REAL
```

Runtime equivalent (station firmware; `HybridHardware` picks per method):

```cpp
factory::P4FactoryHardware real;   // TODO(hw) implementations on P4
factory::MockHardware mock;
factory::HwConfig config;          // defaults from BUKIFON_HW_* macros
config.set(factory::HwBackend::I2c, factory::HwMode::Real);
factory::HybridHardware hardware(real, mock, config);
factory::factoryCliMain(argc, argv, hardware, stdout);
```

Mapping (which factory tests use which backend):

| Backend flag | Tests affected |
|---|---|
| `BUKIFON_HW_I2C` | 1 power-on, 2 I²C scan, 3 MCP23017, 10 MAX17048 |
| `BUKIFON_HW_ADC` | 4 MCP3208 vector |
| `BUKIFON_HW_DAC` | 5 MCP4728→MCP3208/CV loopback |
| `BUKIFON_HW_I2S` | 6 codec loopback |
| `BUKIFON_HW_SD` | 7 SD scratch |
| `BUKIFON_HW_DISPLAY` | 8 display patterns, 9 WS2812 current |
| `BUKIFON_HW_USB` | 11 USB composite |
| `BUKIFON_HW_CONTROLS` | 12 controls |
| `BUKIFON_HW_CV` | 13 CV/GATE loopback |
| `BUKIFON_HW_MIDI` | 14 MIDI loopback |

**Order and safety (follow exactly):**

1. **I2C** (rails, 24C32, MCP23017, MAX17048).  Bench PSU 5 V with **current
   limit 100–200 mA** for the first power-up; check 3.3 V (3.0–3.6 V), PWR_GOOD,
   no brownout; `factory --json --stop-on-fail` → tests 1–3,10 PASS.  If I²C
   fails: stop, check pull-ups (2.2 kΩ) and addresses; do not enable more.
2. **PANEL / controls** (`BUKIFON_HW_CONTROLS`): MCP23017 expanders + keys/
   encoders/faders; test 12.  Current limit may be raised to 300 mA; check no
   reset when scanning all 16 encoders.
3. **CODEC** (`BUKIFON_HW_I2S`): PCM5102A/PCM1808; loopback plug; test 6
   (1 kHz/−12 dBFS, THD<−60 dB).  Watch for pops/DC offset; keep volume low.
4. **DISPLAY** (`BUKIFON_HW_DISPLAY`): RGB565/DSI panel + backlight; tests 8–9
   (patterns + WS2812 current).  Increase current limit only after the display
   rails are verified.
5. **SD** (`BUKIFON_HW_SD`): 1-bit/4-bit card; test 7 (1 MiB CRC32 ≥0.7 MB/s).
   Pull-card test: remove during write — project must not be lost (docs/36 #5).
6. **USB** (`BUKIFON_HW_USB`): HS composite enumeration on the PC (CDC+MIDI+
   HID+UAC2); test 11.  Reconnect without reboot.
7. **CV / MIDI** (`BUKIFON_HW_CV`, `BUKIFON_HW_MIDI`): loopback plug; tests 13–14.
   Check gate voltage divider and 0–4 V CV accuracy before connecting external
   gear.

**Protection rules:** current-limited PSU at every step; series 100–220 Ω on
first bring-up prototypes; never hot-plug the FPC/IDC with power on; ESD wrist
strap; keep the loopback plug's CV path 10 kΩ (no direct 5 V into ADC); stop
immediately on brownout (`brownoutCount != 0`), 3.3 V outside 3.0–3.6 V, or
temperature >60 °C on the bench board.  A failed step is rolled back by setting
that backend back to MOCK — the remaining tests stay meaningful.

**Expected factory behavior:** a REAL backend whose driver is a TODO stub returns
false and the mapped test FAILs (no fabricated PASS); MOCK backends keep working
independently.  This is covered by `tests/test_hw_backends.cpp` (all-MOCK PASS,
all-REAL-stub 14/14 FAIL, one-by-one mapping).
