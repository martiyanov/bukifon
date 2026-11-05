# CORE-S3 (lite later) — DFM / testability (сокращённо)

> **STATUS: PRE-FREEZE / DO NOT FABRICATE. S3-base — «lite later»** (решение заказчика:
> первый SKU — P4-версия). Полный DFM-пакет для P4-ветки: `hardware/core2/dfm.md` +
> `docs/38-dfm-testability.md`; этот файл — краткая памятка для будущей lite-платы.

## 1. Test points (из CORE-S3: TP1…TP27 + пады)

Рельсы: TP2 `VSYS`, TP5 `5V`, TP6 `3V3`, TP20 `BL_20V`, TP23 `N12_EXT`, TP24 `5V_EXT`,
TP25 `5V_LED`, TP26 `PWR_GOOD`. Сигналы: TP9 `I2S_MCLK`, TP10 `SD_CLK`, TP11/12 `USB D+/D−`,
TP16 `LED_DATA`, TP17 `EN_S3`, TP18 `BOOT`, TP27 `EN_RAILS`; GND: TP13/14/15.
Добавить пады: `LED_RET`, `I2S_BCK/LRCK/DIN/DOUT`, `I2C SDA/SCL`, `SPI3 SCK/MOSI/MISO/CS`,
`CV OUT1-4/IN1-2`, `GATE1` (доступ через J14/J16/TP).

## 2. Self-test (lite)

| # | Тест | Метод | Pass |
|---:|---|---|---|
| 1 | Рельсы | DMM TP: 3V3 3.0–3.6, 5 В, BL_20V | ±3 % |
| 2 | I2C | 0x57, 0x60/0x61, 0x20–0x23, 0x36 | все адреса |
| 3 | MCP4728/MCP3208 | DAC readback / ADC каналы | ±1 LSB / шум ≤3 LSB |
| 4 | Кодек loopback | LINE OUT→AUDIO IN, 1 кГц | SNR ≥80 дБ |
| 5 | Дисплей | SPI 800×480 тест-картинка | без битых, ≥15 fps full |
| 6 | SD 1-bit | запись/чтение 1 МБ | CRC ok |
| 7 | Панель | 42 клавиши/16 энкодеров/фейдеры | все, без фантомов |
| 8 | CV/GATE | loopback | ≤±0.5 % FS |
| 9 | USB FS composite | enumerate, UAC/MIDI/HID/CDC | 0 drop 30 мин |
| 10 | Recovery | USB-JTAG/CDC, BOOT | прошивка/сброс |

## 3. Исправления O-17 / O-18 (для lite)

- **O-17 исправлен:** `BOM-cores3.csv` — TL074 **4 шт.** (U37/U38/U39/U45; ранее 20 из-за
  мультиюнитов), TL072 1 шт.; количество = число корпусов, позиции уникальны.
- **O-18 зафиксирован:** U46 = `TPS63000 (placeholder; replace with TPS63802/TPS63020, O-18)`;
  в BOM/power-tree — 1 А continuous / ≥1.5 А transient, дроссель ≥3–4 А sat; символ/футпринт
  заменить до PCB (TPS63802/TPS63020; футпринт — из TI datasheet/Ultr, не выдумывать).

## 4. DFM (lite, кратко)

SPI-дисплей FPC-40 (pin1/ключ/stiffener), 1-bit SDMMC, USB FS (90 Ω не нужен, но ESD),
3V3 buck-boost (тепло/load-step), 6×M3, панелизация 2×2, шелкография pin1/rev/SN,
TP не под шлейфами, antenna keepout S3 ≥15 мм. Полный чек-лист — в `hardware/core2/dfm.md` §6.
