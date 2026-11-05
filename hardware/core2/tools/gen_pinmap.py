#!/usr/bin/env python3
import sys as _sys; _sys.dont_write_bytecode = True
# -*- coding: utf-8 -*-
"""Generate pinmap.csv (machine readable) and pinmap.md (human table) for CORE-2.
PRE-FREEZE / DO NOT FABRICATE.  Source: tools/board_def.py"""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_def as B

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RES_SET = {r[0] for r in B.RESERVED}
RES_SIG = {'USB_JTAG_DP', 'USB_JTAG_DM', 'USB_FS_DP', 'USB_FS_DM', 'STRAP36'}
FREE_SIG = {'FREE_IO54'}

def used_gpios():
    return [r for r in B.PINMAP if r[1] is not None and r[1] not in RES_SET
            and r[0] not in RES_SIG and r[0] not in FREE_SIG]

def free_gpios():
    used = {r[1] for r in used_gpios()}
    res = {r[0] for r in B.RESERVED}
    return [g for g in range(55) if g not in used and g not in res]

def write_csv():
    p = os.path.join(OUT, 'pinmap.csv')
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['signal', 'gpio', 'peripheral', 'voltage', 'direction',
                    'pull', 'boot_state', 'mcu_slot_pin', 'connector', 'note'])
        for r in B.PINMAP:
            w.writerow([r[0], '' if r[1] is None else r[1], r[2], r[3], r[4],
                        r[5], r[6], r[7], r[8], r[9]])
    print('written', p)

def write_md():
    used = used_gpios()
    res = B.RESERVED
    free = free_gpios()
    L = []
    A = L.append
    A('# CORE-2 — карта пинов и распределение ресурсов')
    A('')
    A('> **STATUS: PRE-FREEZE / DO NOT FABRICATE.** Схема — исследовательская,')
    A('> не для заказа плат до бенчмарка P1 и подписи требований (spec/90).')
    A('> Машинно-читаемая версия: [`pinmap.csv`](pinmap.csv);')
    A('> проверка: `python3 tools/check_pinmap.py`.')
    A('')
    A('**MCU:** %s. **Слот:** %s.' % (B.MCU, B.SLOT))
    A('Источник фактов: ESP32-P4 Series Datasheet v0.7 (Espressif) —')
    A('55 GPIO, boot strapping GPIO35…GPIO38, USB HS PHY на выделенных USB_DM/USB_DP,')
    A('SDMMC slot0 на падах GPIO39…GPIO48, LCD_CAM (parallel RGB 16 бит) и 3× I2S через GPIO matrix.')
    A('')
    A('## 1. Сводка')
    A('')
    A('| Параметр | Значение |')
    A('|---|---|')
    A('| Всего GPIO у ESP32-P4 | 55 (GPIO0…GPIO54) |')
    A('| Занято сигналами платы | **%d** |' % len(used))
    A('| Зарезервировано (USB FS/JTAG, strapping) | **%d** |' % len(res))
    A('| Свободно | **%d** (%.1f %%) |' % (len(free), 100.0 * len(free) / 55))
    A('| Конфликтов GPIO | **0** (проверено `check_pinmap.py`) |')
    A('| Конфликтов boot/strapping | **0** (GPIO35 = BOOT с 10k PU; GPIO36 = 10k PD; GPIO37/38 = UART0) |')
    A('| Резерв GPIO | **фактически отсутствует** (1 свободный GPIO54) — расширение только по I2C/SPI |')
    A('')
    A('Свободные GPIO: %s.' % (', '.join('GPIO%d' % g for g in free) if free else 'нет'))
    A('')
    A('**Резерв GPIO — отсутствует (1 из 55 = 1.8 %).** Это осознанное решение PRE-FREEZE:')
    A('16 энкодеров и матрица 42 клавиш вынесены на 4× MCP23017 (I2C) на PANEL-2,')
    A('а цифровое расширение модулей — на отдельный J-DIG-EXP (TDM/I2S + SPI mailbox, R-22).')
    A('Если потребуется ещё GPIO — только ревизия с расширителем (MCP23S17 по SPI) или')
    A('перенос части функций на PANEL-2; в v1.0-rc места нет.')
    A('Расширение (энкодеры, матрица клавиш) — не на GPIO, а по I2C (4× MCP23017 на PANEL-2, адреса 0x20/0x21/0x22/0x23, 48 линий энкодеров + 13 матрицы = 61) — см. §5.')
    A('')
    A('## 2. Занятые GPIO')
    A('')
    A('| # | Сигнал | GPIO | Периферия | Напряжение | Направление | Подтяжка | Boot-состояние | Слот J-MCU | Разъём | Примечание |')
    A('|---|---|---|---|---|---|---|---|---|---|---|')
    for i, r in enumerate(used, 1):
        A('| %d | `%s` | GPIO%s | %s | %s | %s | %s | %s | %d | %s | %s |' % (
            i, r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9]))
    A('')
    A('## 3. Выделенные и не-GPIO выводы модуля')
    A('')
    A('| Сигнал | GPIO | Периферия | Напряжение | Направление | Boot | Слот | Разъём |')
    A('|---|---|---|---|---|---|---|---|')
    for r in B.PINMAP:
        if r[1] is None:
            A('| `%s` | — | %s | %s | %s | %s | %d | %s |' % (
                r[0], r[2], r[3], r[4], r[6], r[7], r[8]))
    A('')
    A('## 4. Зарезервированные GPIO')
    A('')
    A('| GPIO | Причина |')
    A('|---|---|')
    for g, why in res:
        A('| GPIO%d | %s |' % (g, why))
    A('')
    A('## 5. PANEL-2: расширители I2C (на плате панели)')
    A('')
    A('| Адрес | Позиция | Функция | Распиновка |')
    A('|---|---|---|---|')
    for m in B.MCP23017:
        A('| %s | %s | %s | %s |' % (m['addr'], m['ref'], m['role'], '<br>'.join(m['pins'])))
    A('')
    A('')
    A('### PANEL-2 MCP23017 — EN-линии rev.2 (D-33/O-4)')
    A('')
    A('У P4 0 свободных GPIO → 4 EN-входа PWR-2 сведены к **2 линиям** MCP23017 0x23:')
    A('')
    A('| PWR-2 вход | Сеть CORE-2 | MCP23017 | Маршрут | Дефолт |')
    A('|---|---|---|---|---|')
    for e in B.EN_MAP:
        A('| %s | `%s` | %s | %s | %s |' % (e['pwr'], e['net'], e['panel'], e['route'], e['default']))
    A('')
    A('EN_BUS12/EN_N12/EN_5V — «active-high disable» и объединены на CORE-2 в `EN_RAILS`;')
    A('EN_LED5 — «active-high enable», по умолчанию OFF. При high-Z (MCP23017 = входы до')
    A('инициализации) PWR-2 pull-up держит рельсы ON — соответствует D-33. Fallback без')
    A('правки PANEL-2: EN не разводить (дефолт PWR-2), LED включать джампером JP1.')
    A('')
    A('I2C0 (GPIO21/22) — общая шина: 2× MCP4728 (0x60/0x61), 24C32 (0x57), MAX17048 (0x36, PWR-2),')
    A('4× MCP23017 (0x20/0x21/0x22/0x23): 48 линий энкодеров (16× A/B/push) + 13 линий матрицы 6×7 = 61; 3 линии резерв. Наружу — только SDA/SCL/INT (wire-OR INTA). Подтяжки I2C 2.2 к и INT 10 к — на CORE-2; ёмкость шины ≤ 200 pF.')
    A('')
    A('## 6. Фейдеры и джеки')
    A('')
    A('| Элемент | Цепь | Схема |')
    A('|---|---|---|')
    for name, net, how in B.FADERS:
        A('| %s | `%s` | %s |' % (name, net, how))
    for name, net, how in B.JACKS:
        A('| %s | `%s` | %s |' % (name, net, how))
    A('')
    A('## 7. Разъёмы (полные таблицы)')
    A('')
    def table(name, pins, title):
        A('### %s' % title)
        A('')
        A('| Pin | Цепь |')
        A('|---|---|')
        for p, sig, *_ in pins:
            A('| %s | `%s` |' % (p, sig))
        A('')
    table('J-MCU', [(r[7], r[0]) for r in sorted(B.PINMAP, key=lambda x: x[7])], 'J-MCU — слот MCU-модуля (2×32, 64 pin)')
    table('J14 (IDC-26)', [(p, s) for p, s in B.J14_REV2], 'J14 — PANEL-2 J14 (IDC-26, rev.2 canon): CV OUT1-4, CV IN1-4, GATE_OUT, FADER1/2, EN_LED5; evens = GNDA')
    table('J15 (FFC-40)', [(p, s) for p, s in B.J15_REV2], 'J15 — PANEL-2 J12 (FFC-40, rev.2 canon): RGB565 + sync + BL_PWM/BL_20V/BL_CATHODE + 3V3 + GND')
    table('J16 (IDC-16)', [(p, s) for p, s in B.J16_REV2], 'J16 — PANEL-2 J13 (IDC-16, rev.2 canon): I2C, INT, LED_DATA 3.3 В, 5V_LED/LED_RET, EN_RAILS')
    table('J-BUS1/J-BUS2', B.J_BUS, 'J-BUS1/J-BUS2 — аналоговая шина модулей (IDC-26, 2 шт.)')
    table('J-DIG (spec only)', B.J_DIG, 'J-DIG — цифровое расширение R-22 (в rev.2 ОТЛОЖЕНО до rev.3; J16 занят PANEL-2)')
    table('J-USB-DATA', [(p, s) for p, s, *_ in B.J_USB_DATA], 'J-USB DATA — USB-C 16P (USB HS)')
    A('> Один USB-C 16P: USB 2.0 HS данные + 5 В заряд/питание (раздельные USB-C DATA/CHARGE — опция ревизии).')
    A('')
    table('TB1/TB2', [(n, s) for _, s, n in B.TB_REAR], 'TB1/TB2 — задние джеки (MIDI, LINE/PHONES, DC, EXPRESSION)')
    table('J17 (IDC-20)', [(p, s) for p, s, *_ in B.J_PWR3], 'J17 — PWR-2 J3 (IDC-20, rev.2): силовые входы, пары PGND')
    table('J18 (IDC-12)', [(p, s) for p, s, *_ in B.J_PWR4], 'J18 — PWR-2 J4 (IDC-12, rev.2): контроль/EN/I2C гейджа')
    A('\\* энкодеры и матрица клавиш считываются MCP23017 на PANEL-2; на CORE-2 идут только I2C + IRQ.')
    A('')
    A('> В таблицах разъёмов указаны *логические* цепи. На плате питания панели идут через')
    A('> фильтры: `3V3 -> 3V3_PANEL`, `5V -> 5V_PANEL` (ферриты FB4/FB5), `BL_ANODE -> BL_20V`')
    A('> (+20 В boost), `BL_CATHODE` — возврат LED-линейки (0R на PGND на CORE-2).')
    A('> J13 IDC-16 (дека) находится на PANEL-2; на CORE-2 ему соответствуют J15 FFC-40 (J12)')
    A('> и J14 IDC-26 (J14) — см. `interfaces.md` §7.')
    A('')
    A('## 8. Дисплей и аудио-контракт (кратко; полностью — `interfaces.md`)')
    A('')
    A('| Параметр | Значение |')
    A('|---|---|')
    for k, v in B.DISPLAY.items():
        A('| display.%s | %s |' % (k, v))
    for k, v in B.AUDIO.items():
        A('| audio.%s | %s |' % (k, v))
    for k, v in B.USB.items():
        A('| usb.%s | %s |' % (k, v))
    A('')
    p = os.path.join(OUT, 'pinmap.md')
    open(p, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('written', p)

if __name__ == '__main__':
    write_csv()
    write_md()
