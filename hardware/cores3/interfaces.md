# CORE-S3 — интерфейсы (PRE-FREEZE / DO NOT FABRICATE)

## USB FS composite (S3 internal PHY, 12 Mbps)

HID + MIDI + CDC + **stereo UAC2 24/48**; 8x8 UAC2 — **нет**. Это потолок
endpoint'ов (6 номеров):

| Endpoint | Направление | Тип | Назначение |
|---|---|---|---|
| UAC ISO OUT | host->dev | iso | audio playback L/R 24/48 |
| UAC ISO IN | dev->host | iso | audio capture L/R 24/48 |
| UAC feedback IN | dev->host | iso | feedback по I2S clock |
| MIDI bulk IN | dev->host | bulk | MIDI out |
| MIDI bulk OUT | host->dev | bulk | MIDI in |
| CDC bulk IN/OUT + notif IN | both | bulk/int | CDC (debug/config) |
| HID int IN | dev->host | interrupt | knobs/keys |

Прошивка: **ESP-IDF + esp_tinyusb**; FIFO 4 КиБ RX + 4 КиБ TX во внутренней SRAM;
CDC rate-limit; feedback по I2S clock. USB-JTAG/CDC — единственная диагностика
(отдельный debug-UART не разводится).

## Аудио: I2S-контракт (как CORE-2)

MCLK 12.288 МГц = 256 fs, BCK 3.072 МГц = 64 fs, LRCK 48 кГц; PCM5102A slave,
PCM1808 slave MD0=MD1=0, FMT=0; PCM1808 VCC = +5 В (PWR-2), VDD = +3V3.
Mute/sequencing как в CORE-2 interfaces §2.

## Дисплей: два варианта

| Вариант | Линии | FPS | Статус |
|---|---:|---|---|
| SPI 800x480 16-bit (в схеме rev.0) | 6 (SCK/MOSI/CS/DC/RST/BL) | full ~12-15, partial 10-20 | реализован, ERC 0/0 |
| RGB565 16-bit (цель GPT) | 18 DE-only (16 data + PCLK + DE), 20 если нужны HS/VS | >=15 full / >=30 partial (dirty rect) | **требует 38-40 GPIO; на N16R8 реально 31 — не помещается** |

Framebuffer: один 800x480 RGB565 (750 КиБ в PSRAM) + bounce buffers 8-16 строк
во внутренней SRAM; dirty rectangles; без двойного буфера. SPI-дисплей для
800x480 GPT не рекомендует; на N16R8 он остаётся рабочим компромиссом.

## microSD

**1-bit SDMMC** (CLK/CMD/D0), без card-detect: ~0.8-1.2 МБ/с достаточно для
сэмпл-стриминга; SPI-режим с CS/CD не используется (экономия 2 линий).

## MIDI / CV / PANEL-2

MIDI TRS-A: UART1 (matrix) TX/RX -> 74HCT125 / 6N137, 31250 бод.
CV: 2x MCP4728 (I2C 0x60/0x61) + 6x TL074 -> CV OUT1-4 (J14), MCP3208 CH0-7 ->
CV IN1-4, FADER1/2, BATT_MON, TEMP_MON. GATE1 — 1 GPIO; GATE2 не разводится.
PANEL-2 rev.2 canon: J14/J15/J16; EN-линии и GATE_IN — с MCP23017 0x23 PANEL-2;
LCD DISP — к +3V3 (R105); SD-detect отсутствует.

## Питание/земли

3V3: TPS63802 (target) от VSYS 1 А continuous; +5/+12/-12/5V_LED — PWR-2 J17;
BL boost 19-22 В — MT3608 #3 от +5 В; AGND/DGND/PGND — звезда NT1/NT2.
PWR_GOOD — GPIO3 (100k PU на CORE-S3); FUEL_ALRT не разводится (опрос MAX17048
по I2C вместо ALRT, как O-8 для S3).
