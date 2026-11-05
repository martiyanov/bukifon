# CORE-S3 — питание и бюджеты (PRE-FREEZE / DO NOT FABRICATE)

## Роли: 3.3 В делает CORE-S3, силовые рельсы — PWR-2

`VSYS (BQ24074 OUT) -> TPS63000 (placeholder, target TPS63802 / fallback TPS63020)
 -> +3V3 1 A continuous / >=1.5 A transient`

Требования (consult GPT): дроссель >=3-4 A sat, 2x22 мкФ + 10 мкФ у модуля,
load-step 150->900 мА без reset/щелчка, rail 3.0-3.6 В; Wi-Fi TX cap; не писать flash
во время записи. TPS63000 в схеме — **placeholder** (символ/футпринт), TPS63802/
TPS63020 сверить по datasheet до PCB (pinout/footprint отличаются).

| Рельс | Источник | Бюджет | Возможность | Запас | Нагрузки |
|---|---|---:|---:|---:|---|
| +3V3 (TPS63000 buck-boost) | VSYS 3.0...4.4 V | 700 мА | 1000 мА | 30 % | S3 350 + PSRAM 50 + panel logic 150 + audio 60 + CV 30 + MIDI 10 + misc 50 |
| +5V (PWR-2 J3) | PWR-2 5.10 V | 290 мА | 1600 мА | 82 % | PCM1808 VCC 30 + MIDI 10 + BL-boost input 80 + panel 5V 170 (5V_LED) |
| +12V (PWR-2 J3) | PWR-2 11.7 V | 150 мА | 330 мА | 55 % | module bus 2x60 + opamps 30 |
| -12V (PWR-2 J3) | PWR-2 -11.55 V | 95 мА | 95 мА | 0 % | module bus 2x40 + opamps 15; budget = limit, exception |
| BL_20V (MT3608 #3) | +5V | 30 мА | 100 мА | 70 % | LCD backlight LED string 20-25 mA |

Исключение: −12 В бюджет = 95 мА (предел PWR-2, как в CORE-2).

## Что проверить на P1-стенде

1. Load-step 150->900 мА (TPS63802): просадка <= ±5 %, без reset S3; осциллограмма.
2. Wi-Fi TX (+300 мА импульс) одновременно с LCD DMA — нет reset/артефактов.
3. Тепло TPS63802 и L при 1 А continuous 30 мин: <=70 °C.
4. USB-C VBUS 5 В -> BQ24074: заряд 1 А + система; NTC/TS от PWR-2 J4.

## Нельзя заказывать до P1

PCB CORE-S3 — только после devkit-spike (см. README §Devkit) и замены placeholder
TPS63000 на выбранный TPS63802/TPS63020 с проверенным футпринтом.
