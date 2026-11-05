# CORE-S3 — «народная» версия ядра на ESP32-S3 (PRE-FREEZE / DO NOT FABRICATE)

> **PRE-FREEZE / DO NOT FABRICATE.** Это исследовательская ревизия rev.0 (SPI-дисплей,
> ERC 0/0). Заказ PCB — только после devkit-spike и подтверждения GPIO-бюджета
> (см. §«Devkit-spike»). Не отправлять в производство до P1-бенчмарка.

Первый SKU «S3-base kit $199» (решение D-38). Клон CORE-2 rev.2: аналог/CV/MIDI/
PWR-2-интерфейсы те же, MCU — **ESP32-S3-WROOM-1-N16R8** (16 МБ flash, 8 МБ octal
PSRAM), USB 2.0 FS, 3V3 — **buck-boost TPS63000 (placeholder; target TPS63802/
TPS63020)** от VSYS (D-41).

## Что в плате

| Блок | Состав |
|---|---|
| MCU | ESP32-S3-WROOM-1-N16R8; USB FS (HID+MIDI+CDC+стерео UAC2); Wi-Fi 4/BLE 5.0 нативно |
| Питание | USB-C + BQ24074 charge/path; TPS63000 3V3 от VSYS; +5/+12/−12/5V_LED с PWR-2 J17; BL boost 19-22 В от +5 В |
| Аудио | PCM5102A DAC + PCM1808 ADC (I2S), TL072 LINE/PHONES, 5 аудио-джеков на задней |
| CV | 2× MCP4728 (0x60/0x61) + 6× TL074 → CV OUT1-4; CV IN1-4 (MCP3208 CH0-5); фейдеры CH2/3; BATT/TEMP CH6/7 |
| MIDI | TRS-A in/out (6N137 / 74HCT125), UART1 |
| microSD | 1-bit SDMMC (CLK/CMD/D0), без card-detect |
| Дисплей | rev.0: SPI 800x480; цель GPT: RGB565 (требует больше GPIO — см. бюджет) |
| PANEL-2 | J14 IDC-26 (аналог), J15 FFC-40 (LCD), J16 IDC-16 (цифра/питание) — канон rev.2 |
| PWR-2 | J17 IDC-20 (силовой), J18 IDC-12 (управление) |

## GPIO-бюджет: «интерфейс → линии → реально доступно»

Доступно на N16R8: GPIO0-18, 21, 38-48 = 33; минус USB 19/20 → **31 полезная**.
(GPIO33-37 заняты octal PSRAM, GPIO26-32 — flash; 43/44 = RXD0/TXD0.)
⚠️ Оценка GPT «38-40 линий» **не подтверждается для N16R8**: она соответствует
кристаллу/квад-PSRAM варианту. Для восьмимегабайтного octal PSRAM доступно 31.

| Интерфейс | Линий (rev.0, SPI) | Линий (RGB565 цель) | Доступно |
|---|---:|---:|---|
| LCD | 6 | 18–20 | SPI: влезает; RGB565: не влезает на 31 |
| microSD | 3 | 3 | 1-bit SDMMC |
| I2S (MCLK/BCK/LRCK/DIN/DOUT) | 5 | 5 | влезает |
| I2C0 (SDA/SCL) | 2 | 2 | влезает |
| MIDI UART | 2 | 2 | влезает |
| LED_DATA (WS2812/RMT) | 1 | 1 | влезает |
| PANEL_IRQ | 1 | 1 | влезает |
| GATE1 (GATE2 не разводится) | 1 | 1 | влезает |
| BOOT (страп; USB-JTAG тоже есть) | 1 | 1 | влезает |
| PWR_GOOD | 1 | 1 | влезает |

**Итог rev.0 (SPI): 26 занято, 5 свободно (GPIO13, 43, 44, 45, 46) = 16 %.**
**RGB565 (18 DE-only): 38 линий — на 31 не помещается (не хватает ~7).**
Если devkit подтвердит 38-40 (другой модуль/квад-PSRAM), переходим на RGB565;
иначе остаёмся на SPI (partial UI 10-20 fps) или меняем модуль на N16R2 (2 МБ PSRAM,
не хватает под 4 МиБ sample pool) — решение Lead.

## CORE-2 vs CORE-S3

| Параметр | CORE-2 (P4+C6) | CORE-S3 |
|---|---|---|
| MCU | ESP32-P4 (RISC-V 400 MHz, 32 MB PSRAM) + ESP32-C6 (Wi-Fi 6/BLE 5.3) | ESP32-S3-WROOM-1-N16R8 (Xtensa LX7 240 MHz, 16 MB flash, 8 MB octal PSRAM), Wi-Fi 4/BLE 5.0 onboard |
| USB | HS 480 Mbps, composite HID+MIDI+UAC2+CDC | FS 12 Mbps, composite HID+MIDI+UAC1/2 stereo+CDC (8x8 UAC2 NOT supported) |
| Display | RGB565 800x480, 20 GPIO, up to 60 fps | SPI 800x480 16-bit, 6 GPIO, full frame ~12-15 fps, partial UI 10-20 fps |
| DSP | Dual DSP extensions, 360 DMIPS+, 32 MB PSRAM | Xtensa LX7 + vector ops, 8 MB PSRAM; 8 mono voices / 6 polyphonic with effects |
| Wi-Fi/BLE | C6 coprocessor over SPI (esp-hosted) | native Wi-Fi 4 / BLE 5.0; no C6 board/keep-out/LDO |
| SD card | SDIO 4-bit | SPI mode on shared SPI3 bus (~10-20 MB/s) |
| Power | +3V3 via AP2112K + MP1584 + AP2112K(+3V3_C6); +5/+-12 from PWR-2 | +3V3 via single TPS63000 buck-boost from VSYS (no MP1584/LDOs/C6 rail) |
| Connectors | J14/J15/J16 PANEL-2 + J17/J18 PWR-2 | same J14/J13/J12 (J15 FFC-40) + J17/J18 (panel J12 pinout used for SPI subset) |
| BOM cost (est.) | higher: P4+C6 modules, HS crystal/ESD, 2 extra LDOs | lower: one S3 module (~$8-12), no C6/LDOs; board est. $45-65, kit $199 target |
| Firmware | ESP-IDF P4 + esp-hosted RPC | ESP-IDF S3; shared UI/audio layers; some P4 DSP paths reduced |

## Ориентир цены BOM CORE-S3

Оценка ±30 % (поставщики не проверялись, только порядок):
S3-WROOM-1-N16R8 $8-12; TPS63020 $3-5; PCM5102A $4; PCM1808 $5; MCP4728 ×2 $6;
MCP3208 $4; TL074 ×4 $2; TL072 $1; MIDI $2; USB/ESD $2; разъёмы $8; пассив/PCB $20-25.
**Итого плата ≈ $55-70.** Kit S3-base — **$199** (D-38). Для сравнения: CORE-2
(P4+C6, HS USB, 2 LDO, 32 МБ PSRAM) ориентировочно на $25-40 дороже.

## Что проверить на P1-стенде / devkit-spike (2-3 дня, до PCB)

Состав стенда: ESP32-S3-DevKitC-N16R8 + реальный RGB FPC-40 дисплей 800x480 +
PCM5102A + PCM1808 + microSD + макет PWR-2 (VSYS 3.0-4.4 В, 3 А).

| День | Работа | Критерий pass |
|---|---|---|
| 1 | pin allocation + descriptor allocation; поднять USB composite (HID+MIDI+CDC+UAC2 stereo), I2S, SD 1-bit, дисплей | enumerate на Win/macOS/Linux; audio 48 кГц 24 бит без xrun |
| 2 | 3 стресс-теста: memory/audio/display; USB composite soak 30-60 мин | ≥15 fps full / ≥30 partial; audio xruns 0; USB reconnect 0; PSRAM random-read rate |
| 3 | power: load-step 150→900 мА, thermal 1 А 30 мин, Wi-Fi TX + LCD | 3.0-3.6 В без reset; ≤70 °C; нет артефактов |

**Fail любого критерия → PCB CORE-S3 не заказывать**, скорректировать (модуль RGB vs
SPI, TPS63802 vs TPS63020, 31 vs 38 GPIO).

## DFM/testability (lite later)

S3-base — «lite later»; сокращённый DFM — [`dfm.md`](dfm.md), полный P4-пакет —
[`hardware/core2/dfm.md`](../core2/dfm.md) + [`docs/38`](../../docs/38-dfm-testability.md).

## Файлы

`CORE-S3.kicad_sch` (+`.kicad_pro`), `CORE-S3.pdf`, `CORE-S3.svg.gz`, `netlist.net/xml`,
`erc/erc.rpt` (**0 errors / 0 warnings**), `BOM-cores3.csv`, `pinmap.md/.csv`,
`power-tree.md`, `interfaces.md`, `sym-lib-table`, `picomod.kicad_sym`,
`gen_cores3_sch.py`, `tools/board_s3.py`, `tools/gen_docs_s3.py`.

## Открытые вопросы (до PCB)

1. **GPIO**: подтвердить на devkit реальное число линий N16R8 (31 vs 38-40). Пока rev.0 — SPI-дисплей.
2. RGB565: если панель DE-only — 18 линий; иначе 20 — ещё дальше от 31. Проверить MPN панели.
3. PSRAM 8 МБ: профиль S3 — 4 МиБ sample pool + один framebuffer (750 КиБ), не 8 МиБ.
4. TPS63802/TPS63020: заменить placeholder-символ TPS63000, сверить футпринт до PCB.
5. USB: endpoint budget (6 номеров) проверить в esp_tinyusb на devkit.
6. GATE2 и CV OUT5/6 в S3-версии не разводятся (PANEL-2 J14 canon) — подтвердить у Lead.
