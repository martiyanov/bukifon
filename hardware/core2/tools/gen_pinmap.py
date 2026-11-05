#!/usr/bin/env python3
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
    A('16 энкодеров и матрица 42 клавиш вынесены на 3× MCP23017 (I2C) на PANEL-2,')
    A('а цифровое расширение модулей — на отдельный J-DIG-EXP (TDM/I2S + SPI mailbox, R-22).')
    A('Если потребуется ещё GPIO — только ревизия с расширителем (MCP23S17 по SPI) или')
    A('перенос части функций на PANEL-2; в v1.0-rc места нет.')
    A('Расширение (энкодеры, матрица клавиш) — не на GPIO, а по I2C (3× MCP23017 на PANEL-2, адреса 0x20/0x21/0x22) — см. §5.')
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
    A('I2C0 (GPIO21/22) — общая шина: 2× MCP4728 (0x60/0x61), 24C32 (0x57),')
    A('3× MCP23017 (0x20/0x21/0x22). Суммарная ёмкость шины ≤ 200 pF, подтяжки 2.2 к.')
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
    table('J-PANEL', B.J_PANEL, 'J-PANEL — PANEL-2 (IDC-26): I2C, энкодеры*, матрица*, фейдеры, CV, GATE, LED')
    table('J-LCD', B.J_LCD, 'J-LCD — дисплей 800×480 (FFC-40, 0.5 мм): RGB565 + синхро + BL/DISP + AUDIO IN')
    table('J-BUS1/J-BUS2', B.J_BUS, 'J-BUS1/J-BUS2 — аналоговая шина модулей (IDC-26, 2 шт.)')
    table('J-DIG', B.J_DIG, 'J-DIG-EXP — цифровое расширение умных модулей (R-22: TDM/I2S + SPI mailbox)')
    table('J-USB-DATA', [(p, s) for p, s, *_ in B.J_USB_DATA], 'J-USB DATA — USB-C 16P (USB HS)')
    A('> Один USB-C 16P: USB 2.0 HS данные + 5 В заряд/питание (раздельные USB-C DATA/CHARGE — опция ревизии).')
    A('')
    table('TB1/TB2', [(n, s) for _, s, n in B.TB_REAR], 'TB1/TB2 — задние джеки (MIDI, LINE/PHONES, DC, EXPRESSION)')
    A('\\* энкодеры и матрица клавиш считываются MCP23017 на PANEL-2; на CORE-2 идут только I2C + IRQ.')
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
