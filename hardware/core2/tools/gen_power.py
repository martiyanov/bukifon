#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate power-tree.md for CORE-2 (PRE-FREEZE). Numbers come from
tools/board_def.py; formulas documented inline so they can be re-checked."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_def as B

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def md():
    R = {r['name']: r for r in B.RAILS}
    L = []; A = L.append
    A('# CORE-2 — дерево питания и бюджеты токов')
    A('')
    A('> **STATUS: PRE-FREEZE / DO NOT FABRICATE.** Расчёты — оценочные, для')
    A('> проверки архитектуры до бенчмарка; не являются финальным thermal/PDN-анализом.')
    A('')
    A('## 1. Топология')
    A('')
    A('```')
    A('USB-C (5 V, данные+заряд) -> USBLC6-2SC6 -> F1 polyfuse 1.5 A -> BQ24074 (1.5 A charger,')
    A('    power-path) -> VSYS (3.0..4.4 V) / charge 1S2P 18650 via BMS (BQ297xy + 2x N-MOS)')
    A('')
    A('VSYS --+-- U1 MT3608 boost --> +12 V (12.1 V) --+--> BUS1/BUS2 (IDC-26, protected)')
    A('       |                                        +--> U5 MC34063 inverter --> -12 V')
    A('       +-- U2 MT3608 boost --> +5 V (5.1 V) ---+--> panel backlight / WS2812 chain')
    A('                                                +--> U3 AP2112K-3.3 --> +3V3 (periph/analog)')
    A('                                                +--> U4 MP1584 buck -> +3V3_MCU (P4+PSRAM)')
    A('')
    A('AGND / DGND / PGND — три отдельные цепи, соединены в одной точке NT1/NT2 (net-tie).')
    A('LDO/DC-DC входы и выходы развязаны ферритами FB1..FB5 + 100 nF/10 uF.')
    A('```')
    A('')
    A('## 2. Бюджеты рельсов (worst-case)')
    A('')
    A('| Рельс | Номинал | Источник | Преобразователь | Возможность, мА | Бюджет, мА | Запас | Нагрузки |')
    A('|---|---|---|---|---|---|---|---|')
    for r in B.RAILS:
        m = '—' if r['margin'] is None else '%d %%' % r['margin']
        A('| %s | %s В | %s | %s | %s | %s | %s | %s |' % (
            r['name'], r['nominal'], r['source'], r['converter'],
            r['cap_mA'], r['budget_mA'], m, '<br>'.join(r['loads'])))
    A('')
    A('### Проверка запаса ≥25 %')
    A('')
    A('| Рельс | Бюджет / возможность | Запас | Итог |')
    A('|---|---|---|---|')
    for r in B.RAILS:
        if r['margin'] is None: continue
        ok = 'OK' if r['margin'] >= 25 else 'НЕТ'
        A('| %s | %d / %d мА | %d %% | %s |' % (r['name'], r['budget_mA'], r['cap_mA'], r['margin'], ok))
    A('')
    A('## 3. Расчёт токов')
    A('')
    A('**+5 В (MT3608 #2, 2 A switch).** Бюджет %d мА (WS2812 %d мА при прошивочном' % (
        R['+5V']['budget_mA'], 550))
    A('лимите яркости + подсветка 300 мА + аудио/MIDI/логика 150 мА).')
    A('Входной ток буста с VSYS=3.7 В: `Iin = 5.1*1.0/(0.88*3.7) = %.2f А` — ' % (5.1*1.0/(0.88*3.7)))
    A('%.0f %% от предела 2 А. Без прошивочного лимита 74×WS2812 на полной яркости = 4.4 А —' % (100*(5.1*1.0/(0.88*3.7))/2))
    A('поэтому **аппаратный polyfuse 2.5 А + firmware cap обязательны**.')
    A('')
    A('**+12 В (MT3608 #1).** `Iin = 12.1*0.33/(0.85*3.7) = %.2f А` (%.0f %% от 2 А).' % (
        12.1*0.33/(0.85*3.7), 100*(12.1*0.33/(0.85*3.7))/2))
    A('Рельс идёт на 2 порта шины (2×60 мА), ОУ ±12 В (30 мА) и вход MC34063 (~120 мА).')
    A('')
    A('**−12 В (MC34063).** 95 мА из 250 мА; вход по +12 В ≈ 120 мА; КПД ≈75 %%.')
    A('')
    A('**+3V3 (AP2112K).** 150 мА из 450 мА (LDO 600 мА, derating 75 %%).')
    A('')
    A('**+3V3_MCU (MP1584).** 700 мА из 2400 мА (3 А × 0.8); отдельный LDO/DC-DC')
    A('для MCU+PSRAM — предотвращает просадки при пиках P4/PSRAM и SD-записи.')
    A('')
    A('**Батарея/VSYS.** Суммарная мощность worst-case:')
    A('`P = 12.1*0.33/0.85 + 5.1*1.0/0.88 = %.1f Вт` → `Ibat = %.2f А` при 3.7 В.' % (
        12.1*0.33/0.85 + 5.1*1.0/0.88, (12.1*0.33/0.85 + 5.1*1.0/0.88)/3.7))
    A('1S2P 5 А·ч → ~0.58 C, BMS FET ≥5 А; типичное потребление 2–4 Вт → 3–5 ч работы.')
    A('')
    A('## 4. Power-path и зарядка')
    A('')
    A('| Сценарий | Путь | Поведение |')
    A('|---|---|---|')
    A('| Только USB-C | VBUS → BQ24074 → VSYS → бусты | Система работает; батарея заряжается (если есть) |')
    A('| USB + батарея | BQ24074 power-path | Нагрузка питается от VBUS, излишек идёт в заряд; разряда нет |')
    A('| Только батарея | BMS → VSYS → бусты | Штатная работа; BMS отсекает 2.8 В |')
    A('| Нет питания | BMS deep-discharge | Отключение; P4 CHIP_PU = 0 через 100k PD |')
    A('')
    A('BQ24074 выбран вместо TP4056: встроенный power-path (не разряжает батарею при USB),')
    A('DPPM, ILIM/ISET/ITERM/TMR, вход до 6.5 В. Заряд 1 А (ILIM 1.5 А, ISET 1.5 к).')
    A('')
    A('## 5. Пусковые токи и защита')
    A('')
    A('| Что | Решение |')
    A('|---|---|')
    A('| Inrush USB-C | polyfuse 1.5 А + BQ24074 soft-start/ILIM; X2 10 uF + 100 uF на VBUS |')
    A('| Hot-plug батареи | 100 uF + TVS + BMS; феррит на входе MT3608 |')
    A('| Пуск MT3608 | внутренний soft-start, C_out 220 uF + 22 uF керамика |')
    A('| КЗ на шине | на каждый порт: polyfuse 0.5 А (+12 В), polyfuse 0.3 А (−12 В), SS34 (переполюсовка) |')
    A('| Просадка 3.3 В при SD/PSRAM | отдельный +3V3_MCU, 2×10 uF + 6×100 nF у модуля |')
    A('| Brownout P4 | внутр. BOD + RC 10 k/100 nF на CHIP_PU + супервизор не нужен (pre-freeze) |')
    A('| Watchdog | RTC WDT в прошивке (2 s), сброс CHIP_PU через GPIO expander не требуется |')
    A('')
    A('## 6. Тестпоинты')
    A('')
    A('| TP | Цепь | Назначение |')
    A('|---|---|---|')
    for tp, net, why in [
        ('TP1', 'VBUS_CHG', 'вход USB-C заряд'),
        ('TP2', 'VSYS', 'системный узел после power-path'),
        ('TP3', '12V', '+12 В шина'),
        ('TP4', '-12V', '−12 В шина'),
        ('TP5', '5V', '+5 В (LED/подсветка)'),
        ('TP6', '3V3', '+3.3 В периферия'),
        ('TP7', '3V3_MCU', '+3.3 В MCU/PSRAM'),
        ('TP8', 'BATT_MON', 'делитель батареи (ADC CH6)'),
        ('TP9', 'I2S_MCLK', '12.288 МГц'),
        ('TP10', 'SD_CLK', 'SDIO clock'),
        ('TP11', 'USB_HS_DP', 'USB D+ (диффпара)'),
        ('TP12', 'USB_HS_DM', 'USB D−'),
        ('TP13', 'AGND', 'аналоговая земля'),
        ('TP14', 'DGND', 'цифровая земля'),
        ('TP15', 'PGND', 'силовая земля'),
    ]:
        A('| %s | `%s` | %s |' % (tp, net, why))
    A('')
    A('## 7. Что проверить до заказа плат (PRE-FREEZE gate)')
    A('')
    A('1. Бенчмарк P4: реальный ток 3V3_MCU и +5V при 800×480 RGB + SD-записи (осциллограф, 20 МГц полоса).')
    A('2. Тепловой режим MT3608 #2 при 1.0 А/5 В 30 мин (корпус модуля ≤ 80 °C).')
    A('3. Inrush USB-C при подключении (токовый пробник; не должен срабатывать polyfuse).')
    A('4. Проверить BQ24074 power-path при одновременной зарядке и пиковой нагрузке (DPPM).')
    A('5. Замерить шум −12 В MC34063 (< 50 мВ p-p) — иначе LDO/LC-фильтр на аналог.')
    A('6. Уточнить тепловой бюджет 1S2P при 2.9 А разряда (пакет 2×18650).')
    A('')
    open(os.path.join(OUT, 'power-tree.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('written power-tree.md')

if __name__ == '__main__':
    md()
