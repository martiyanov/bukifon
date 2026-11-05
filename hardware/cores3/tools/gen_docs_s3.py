#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate CORE-S3 docs: README.md, pinmap.md/.csv, power-tree.md, interfaces.md."""
import os, sys, csv
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_s3 as BS

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USED = [p for p in BS.PINMAP]
AVAIL = [i for i in list(range(0, 19)) + [21] + list(range(38, 49)) if i not in (19, 20)]
FREE = [i for i in AVAIL if i not in [g for _, g, _, _, _ in USED]]

def w(path, lines):
    with open(os.path.join(OUT, path), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')

def pinmap():
    L = ['# CORE-S3 — пин-карта (PRE-FREEZE / DO NOT FABRICATE)', '']
    L.append('ESP32-S3-WROOM-1-N16R8: 16 MB flash, 8 MB octal PSRAM. FPGA нет;')
    L.append('GPIO33-37 заняты octal PSRAM, GPIO26-32 flash, GPIO19/20 — USB FS.')
    L.append('Полезных на модуле: **%d** (GPIO0-18, 21, 38-48; 43/44 = RXD0/TXD0).' % len(AVAIL))
    L.append('')
    L.append('| # | Сигнал | GPIO | Периферия | Напр. | Примечание |')
    L.append('|---|---|---:|---|---|---|')
    for i, (sig, gpio, per, d, note) in enumerate(USED, 1):
        L.append('| %d | `%s` | GPIO%d | %s | %s | %s |' % (i, sig, gpio, per, d, note))
    L.append('')
    L.append('**Занято: %d / %d; свободно: %d (%s) — %.0f %% запас.**' % (
        len(USED), len(AVAIL), len(FREE), ', '.join('GPIO%d' % x for x in FREE),
        100.0*len(FREE)/len(AVAIL)))
    L.append('')
    L.append('## Разъёмы (канон PANEL-2 rev.2 + PWR-2)')
    L.append('')
    for name, lst, desc in [
        ('J14 (IDC-26)', BS.J14_PANEL, 'аналоговое поле PANEL-2 J14'),
        ('J15 (FFC-40)', BS.J15_DISPLAY, 'LCD: SPI-подмножество на разъёме PANEL-2 J12'),
        ('J16 (IDC-16)', BS.J16_PANEL, 'цифра/питание PANEL-2 J13'),
        ('J17 (IDC-20)', BS.J17_PWR3, 'PWR-2 J3 (силовой)'),
        ('J18 (IDC-12)', BS.J18_PWR4, 'PWR-2 J4 (управление)')]:
        L.append('### %s — %s' % (name, desc)); L.append('')
        L.append('| Pin | Цепь | Pin | Цепь |'); L.append('|---|---|---|---|')
        for i in range(0, len(lst), 2):
            a = lst[i]; b = lst[i+1] if i+1 < len(lst) else ('', '')
            L.append('| %s | `%s` | %s | `%s` |' % (a[0], a[1], b[0], b[1]))
        L.append('')
    L.append('## PANEL-2 expanders (0x23) — занятые линии')
    L.append('')
    L.append('| Линия 0x23 | Назначение |')
    L.append('|---|---|')
    for a, b in [('GPA0..GPA6', 'матрица COL0..6'), ('GPB0..GPB5', 'матрица ROW0..5'),
                 ('GPA7', 'EN_RAILS (PWR-2 EN_BUS12/N12/5V)'), ('GPB6', 'EN_LED5'),
                 ('GPB7', 'GATE_IN_CLEAN (PANEL-2)')]:
        L.append('| %s | %s |' % (a, b))
    L.append('')
    L.append('Свободных линий 0x23 **нет** (16/16). Поэтому GATE OUT / LCD DISP / SD-detect')
    L.append('не могут быть на MCP23017 без второго чипа (запрещено ТЗ); LCD DISP — к +3V3,')
    L.append('GATE2 в CORE-S3 не разводится, SD-detect отсутствует (SD только 1-bit).')
    w('pinmap.md', L)
    with open(os.path.join(OUT, 'pinmap.csv'), 'w', newline='', encoding='utf-8') as fh:
        wr = csv.writer(fh, delimiter=';')
        wr.writerow(['signal', 'gpio', 'peripheral', 'direction', 'note'])
        for row in USED:
            wr.writerow(list(row))

def power():
    L = ['# CORE-S3 — питание и бюджеты (PRE-FREEZE / DO NOT FABRICATE)', '']
    L.append('## Роли: 3.3 В делает CORE-S3, силовые рельсы — PWR-2')
    L.append('')
    L.append('`VSYS (BQ24074 OUT) -> TPS63000 (placeholder, target TPS63802 / fallback TPS63020)')
    L.append(' -> +3V3 1 A continuous / >=1.5 A transient`')
    L.append('')
    L.append('Требования (consult GPT): дроссель >=3-4 A sat, 2x22 мкФ + 10 мкФ у модуля,')
    L.append('load-step 150->900 мА без reset/щелчка, rail 3.0-3.6 В; Wi-Fi TX cap; не писать flash')
    L.append('во время записи. TPS63000 в схеме — **placeholder** (символ/футпринт), TPS63802/')
    L.append('TPS63020 сверить по datasheet до PCB (pinout/footprint отличаются).')
    L.append('')
    L.append('| Рельс | Источник | Бюджет | Возможность | Запас | Нагрузки |')
    L.append('|---|---|---:|---:|---:|---|')
    for r in BS.RAILS:
        L.append('| %s | %s | %d мА | %d мА | %d %% | %s |' % (
            r['name'], r['src'], r['bud'], r['cap'], r['margin'], r['loads']))
    L.append('')
    L.append('Исключение: −12 В бюджет = 95 мА (предел PWR-2, как в CORE-2).')
    L.append('')
    L.append('## Что проверить на P1-стенде')
    L.append('')
    L.append('1. Load-step 150->900 мА (TPS63802): просадка <= ±5 %, без reset S3; осциллограмма.')
    L.append('2. Wi-Fi TX (+300 мА импульс) одновременно с LCD DMA — нет reset/артефактов.')
    L.append('3. Тепло TPS63802 и L при 1 А continuous 30 мин: <=70 °C.')
    L.append('4. USB-C VBUS 5 В -> BQ24074: заряд 1 А + система; NTC/TS от PWR-2 J4.')
    L.append('')
    L.append('## Нельзя заказывать до P1')
    L.append('')
    L.append('PCB CORE-S3 — только после devkit-spike (см. README §Devkit) и замены placeholder')
    L.append('TPS63000 на выбранный TPS63802/TPS63020 с проверенным футпринтом.')
    w('power-tree.md', L)

def interfaces():
    L = ['# CORE-S3 — интерфейсы (PRE-FREEZE / DO NOT FABRICATE)', '']
    L.append('## USB FS composite (S3 internal PHY, 12 Mbps)')
    L.append('')
    L.append('HID + MIDI + CDC + **stereo UAC2 24/48**; 8x8 UAC2 — **нет**. Это потолок')
    L.append('endpoint\'ов (6 номеров):')
    L.append('')
    L.append('| Endpoint | Направление | Тип | Назначение |')
    L.append('|---|---|---|---|')
    for a, b, c, d in [('UAC ISO OUT', 'host->dev', 'iso', 'audio playback L/R 24/48'),
                       ('UAC ISO IN', 'dev->host', 'iso', 'audio capture L/R 24/48'),
                       ('UAC feedback IN', 'dev->host', 'iso', 'feedback по I2S clock'),
                       ('MIDI bulk IN', 'dev->host', 'bulk', 'MIDI out'),
                       ('MIDI bulk OUT', 'host->dev', 'bulk', 'MIDI in'),
                       ('CDC bulk IN/OUT + notif IN', 'both', 'bulk/int', 'CDC (debug/config)'),
                       ('HID int IN', 'dev->host', 'interrupt', 'knobs/keys')]:
        L.append('| %s | %s | %s | %s |' % (a, b, c, d))
    L.append('')
    L.append('Прошивка: **ESP-IDF + esp_tinyusb**; FIFO 4 КиБ RX + 4 КиБ TX во внутренней SRAM;')
    L.append('CDC rate-limit; feedback по I2S clock. USB-JTAG/CDC — единственная диагностика')
    L.append('(отдельный debug-UART не разводится).')
    L.append('')
    L.append('## Аудио: I2S-контракт (как CORE-2)')
    L.append('')
    L.append('MCLK 12.288 МГц = 256 fs, BCK 3.072 МГц = 64 fs, LRCK 48 кГц; PCM5102A slave,')
    L.append('PCM1808 slave MD0=MD1=0, FMT=0; PCM1808 VCC = +5 В (PWR-2), VDD = +3V3.')
    L.append('Mute/sequencing как в CORE-2 interfaces §2.')
    L.append('')
    L.append('## Дисплей: два варианта')
    L.append('')
    L.append('| Вариант | Линии | FPS | Статус |')
    L.append('|---|---:|---|---|')
    L.append('| SPI 800x480 16-bit (в схеме rev.0) | 6 (SCK/MOSI/CS/DC/RST/BL) | full ~12-15, partial 10-20 | реализован, ERC 0/0 |')
    L.append('| RGB565 16-bit (цель GPT) | 18 DE-only (16 data + PCLK + DE), 20 если нужны HS/VS | >=15 full / >=30 partial (dirty rect) | **требует 38-40 GPIO; на N16R8 реально 31 — не помещается** |')
    L.append('')
    L.append('Framebuffer: один 800x480 RGB565 (750 КиБ в PSRAM) + bounce buffers 8-16 строк')
    L.append('во внутренней SRAM; dirty rectangles; без двойного буфера. SPI-дисплей для')
    L.append('800x480 GPT не рекомендует; на N16R8 он остаётся рабочим компромиссом.')
    L.append('')
    L.append('## microSD')
    L.append('')
    L.append('**1-bit SDMMC** (CLK/CMD/D0), без card-detect: ~0.8-1.2 МБ/с достаточно для')
    L.append('сэмпл-стриминга; SPI-режим с CS/CD не используется (экономия 2 линий).')
    L.append('')
    L.append('## MIDI / CV / PANEL-2')
    L.append('')
    L.append('MIDI TRS-A: UART1 (matrix) TX/RX -> 74HCT125 / 6N137, 31250 бод.')
    L.append('CV: 2x MCP4728 (I2C 0x60/0x61) + 6x TL074 -> CV OUT1-4 (J14), MCP3208 CH0-7 ->')
    L.append('CV IN1-4, FADER1/2, BATT_MON, TEMP_MON. GATE1 — 1 GPIO; GATE2 не разводится.')
    L.append('PANEL-2 rev.2 canon: J14/J15/J16; EN-линии и GATE_IN — с MCP23017 0x23 PANEL-2;')
    L.append('LCD DISP — к +3V3 (R105); SD-detect отсутствует.')
    L.append('')
    L.append('## Питание/земли')
    L.append('')
    L.append('3V3: TPS63802 (target) от VSYS 1 А continuous; +5/+12/-12/5V_LED — PWR-2 J17;')
    L.append('BL boost 19-22 В — MT3608 #3 от +5 В; AGND/DGND/PGND — звезда NT1/NT2.')
    L.append('PWR_GOOD — GPIO3 (100k PU на CORE-S3); FUEL_ALRT не разводится (опрос MAX17048')
    L.append('по I2C вместо ALRT, как O-8 для S3).')
    w('interfaces.md', L)

def readme():
    L = ['# CORE-S3 — «народная» версия ядра на ESP32-S3 (PRE-FREEZE / DO NOT FABRICATE)', '']
    L.append('> **PRE-FREEZE / DO NOT FABRICATE.** Это исследовательская ревизия rev.0 (SPI-дисплей,')
    L.append('> ERC 0/0). Заказ PCB — только после devkit-spike и подтверждения GPIO-бюджета')
    L.append('> (см. §«Devkit-spike»). Не отправлять в производство до P1-бенчмарка.')
    L.append('')
    L.append('Первый SKU «S3-base kit $199» (решение D-38). Клон CORE-2 rev.2: аналог/CV/MIDI/')
    L.append('PWR-2-интерфейсы те же, MCU — **ESP32-S3-WROOM-1-N16R8** (16 МБ flash, 8 МБ octal')
    L.append('PSRAM), USB 2.0 FS, 3V3 — **buck-boost TPS63000 (placeholder; target TPS63802/')
    L.append('TPS63020)** от VSYS (D-41).')
    L.append('')
    L.append('## Что в плате')
    L.append('')
    L.append('| Блок | Состав |')
    L.append('|---|---|')
    L.append('| MCU | ESP32-S3-WROOM-1-N16R8; USB FS (HID+MIDI+CDC+стерео UAC2); Wi-Fi 4/BLE 5.0 нативно |')
    L.append('| Питание | USB-C + BQ24074 charge/path; TPS63000 3V3 от VSYS; +5/+12/−12/5V_LED с PWR-2 J17; BL boost 19-22 В от +5 В |')
    L.append('| Аудио | PCM5102A DAC + PCM1808 ADC (I2S), TL072 LINE/PHONES, 5 аудио-джеков на задней |')
    L.append('| CV | 2× MCP4728 (0x60/0x61) + 6× TL074 → CV OUT1-4; CV IN1-4 (MCP3208 CH0-5); фейдеры CH2/3; BATT/TEMP CH6/7 |')
    L.append('| MIDI | TRS-A in/out (6N137 / 74HCT125), UART1 |')
    L.append('| microSD | 1-bit SDMMC (CLK/CMD/D0), без card-detect |')
    L.append('| Дисплей | rev.0: SPI 800x480; цель GPT: RGB565 (требует больше GPIO — см. бюджет) |')
    L.append('| PANEL-2 | J14 IDC-26 (аналог), J15 FFC-40 (LCD), J16 IDC-16 (цифра/питание) — канон rev.2 |')
    L.append('| PWR-2 | J17 IDC-20 (силовой), J18 IDC-12 (управление) |')
    L.append('')
    L.append('## GPIO-бюджет: «интерфейс → линии → реально доступно»')
    L.append('')
    L.append('Доступно на N16R8: GPIO0-18, 21, 38-48 = 33; минус USB 19/20 → **31 полезная**.')
    L.append('(GPIO33-37 заняты octal PSRAM, GPIO26-32 — flash; 43/44 = RXD0/TXD0.)')
    L.append('⚠️ Оценка GPT «38-40 линий» **не подтверждается для N16R8**: она соответствует')
    L.append('кристаллу/квад-PSRAM варианту. Для восьмимегабайтного octal PSRAM доступно 31.')
    L.append('')
    L.append('| Интерфейс | Линий (rev.0, SPI) | Линий (RGB565 цель) | Доступно |')
    L.append('|---|---:|---:|---|')
    for name, a, b, note in [('LCD', 6, '18–20', 'SPI: влезает; RGB565: не влезает на 31'),
                       ('microSD', 3, 3, '1-bit SDMMC'),
                       ('I2S (MCLK/BCK/LRCK/DIN/DOUT)', 5, 5, 'влезает'),
                       ('I2C0 (SDA/SCL)', 2, 2, 'влезает'),
                       ('MIDI UART', 2, 2, 'влезает'),
                       ('LED_DATA (WS2812/RMT)', 1, 1, 'влезает'),
                       ('PANEL_IRQ', 1, 1, 'влезает'),
                       ('GATE1 (GATE2 не разводится)', 1, 1, 'влезает'),
                       ('BOOT (страп; USB-JTAG тоже есть)', 1, 1, 'влезает'),
                       ('PWR_GOOD', 1, 1, 'влезает')]:
        L.append('| %s | %d | %s | %s |' % (name, a, b, note))
    L.append('')
    L.append('**Итог rev.0 (SPI): 26 занято, 5 свободно (GPIO13, 43, 44, 45, 46) = 16 %.**')
    L.append('**RGB565 (18 DE-only): 38 линий — на 31 не помещается (не хватает ~7).**')
    L.append('Если devkit подтвердит 38-40 (другой модуль/квад-PSRAM), переходим на RGB565;')
    L.append('иначе остаёмся на SPI (partial UI 10-20 fps) или меняем модуль на N16R2 (2 МБ PSRAM,')
    L.append('не хватает под 4 МиБ sample pool) — решение Lead.')
    L.append('')
    L.append('## CORE-2 vs CORE-S3')
    L.append('')
    L.append('| Параметр | CORE-2 (P4+C6) | CORE-S3 |')
    L.append('|---|---|---|')
    for a, b, c in BS.COMPARISON:
        L.append('| %s | %s | %s |' % (a, b, c))
    L.append('')
    L.append('## Ориентир цены BOM CORE-S3')
    L.append('')
    L.append('Оценка ±30 % (поставщики не проверялись, только порядок):')
    L.append('S3-WROOM-1-N16R8 $8-12; TPS63020 $3-5; PCM5102A $4; PCM1808 $5; MCP4728 ×2 $6;')
    L.append('MCP3208 $4; TL074 ×4 $2; TL072 $1; MIDI $2; USB/ESD $2; разъёмы $8; пассив/PCB $20-25.')
    L.append('**Итого плата ≈ $55-70.** Kit S3-base — **$199** (D-38). Для сравнения: CORE-2')
    L.append('(P4+C6, HS USB, 2 LDO, 32 МБ PSRAM) ориентировочно на $25-40 дороже.')
    L.append('')
    L.append('## Что проверить на P1-стенде / devkit-spike (2-3 дня, до PCB)')
    L.append('')
    L.append('Состав стенда: ESP32-S3-DevKitC-N16R8 + реальный RGB FPC-40 дисплей 800x480 +')
    L.append('PCM5102A + PCM1808 + microSD + макет PWR-2 (VSYS 3.0-4.4 В, 3 А).')
    L.append('')
    L.append('| День | Работа | Критерий pass |')
    L.append('|---|---|---|')
    L.append('| 1 | pin allocation + descriptor allocation; поднять USB composite (HID+MIDI+CDC+UAC2 stereo), I2S, SD 1-bit, дисплей | enumerate на Win/macOS/Linux; audio 48 кГц 24 бит без xrun |')
    L.append('| 2 | 3 стресс-теста: memory/audio/display; USB composite soak 30-60 мин | ≥15 fps full / ≥30 partial; audio xruns 0; USB reconnect 0; PSRAM random-read rate |')
    L.append('| 3 | power: load-step 150→900 мА, thermal 1 А 30 мин, Wi-Fi TX + LCD | 3.0-3.6 В без reset; ≤70 °C; нет артефактов |')
    L.append('')
    L.append('**Fail любого критерия → PCB CORE-S3 не заказывать**, скорректировать (модуль RGB vs')
    L.append('SPI, TPS63802 vs TPS63020, 31 vs 38 GPIO).')
    L.append('')
    L.append('## Файлы')
    L.append('')
    L.append('`CORE-S3.kicad_sch` (+`.kicad_pro`), `CORE-S3.pdf`, `CORE-S3.svg`, `netlist.net/xml`,')
    L.append('`erc/erc.rpt` (**0 errors / 0 warnings**), `BOM-cores3.csv`, `pinmap.md/.csv`,')
    L.append('`power-tree.md`, `interfaces.md`, `sym-lib-table`, `picomod.kicad_sym`,')
    L.append('`gen_cores3_sch.py`, `tools/board_s3.py`, `tools/gen_docs_s3.py`.')
    L.append('')
    L.append('## Открытые вопросы (до PCB)')
    L.append('')
    L.append('1. **GPIO**: подтвердить на devkit реальное число линий N16R8 (31 vs 38-40). Пока rev.0 — SPI-дисплей.')
    L.append('2. RGB565: если панель DE-only — 18 линий; иначе 20 — ещё дальше от 31. Проверить MPN панели.')
    L.append('3. PSRAM 8 МБ: профиль S3 — 4 МиБ sample pool + один framebuffer (750 КиБ), не 8 МиБ.')
    L.append('4. TPS63802/TPS63020: заменить placeholder-символ TPS63000, сверить футпринт до PCB.')
    L.append('5. USB: endpoint budget (6 номеров) проверить в esp_tinyusb на devkit.')
    L.append('6. GATE2 и CV OUT5/6 в S3-версии не разводятся (PANEL-2 J14 canon) — подтвердить у Lead.')
    w('README.md', L)

if __name__ == '__main__':
    pinmap(); power(); interfaces(); readme()
    print('docs written')
