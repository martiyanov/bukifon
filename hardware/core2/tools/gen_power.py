#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate power-tree.md for CORE-2 rev.2 (imported rails from PWR-2 + local rails)."""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_def as B

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def md():
    L = []; A = L.append
    A('# CORE-2 rev.2 — дерево питания и бюджеты токов')
    A('')
    A('> **STATUS: PRE-FREEZE / DO NOT FABRICATE.** rev.2: рельсы ±12 В/+5 В/5V_LED приходят')
    A('> с **PWR-2** (J17), CORE-2 формирует только локальные +3V3 / +3V3_C6 / +3V3_MCU / BL_20 V.')
    A('> **Схема CORE-2 — rev.2** (ERC 0/0); DNP-список (46) и изменения — `rev2-plan.md`. Числа расчётные.')
    A('')
    A('## 1. Топология rev.2')
    A('')
    A('```')
    A('USB-C (5 V, данные+заряд) -> USBLC6 -> F1 1.5 A -> BQ24074 (power-path, заряд 1S2P)')
    A('       BQ24074 BAT <-> PWR-2 J3 «VBAT» (пакет 1S2P + BMS + MAX17048 на PWR-2)')
    A('       BQ24074 OUT = VSYS --> PWR-2 J3 «VSYS» --> master switch --> PWR-2 boost/IBB:')
    A('            +12 V (330 мА) --D7--> CORE-2 12V_EXT --D2--> +12 V  (DNP MT3608 #1)')
    A('            -12 V (95 мА)  --D8--> CORE-2 N12_EXT --D19--> -12 V (DNP MC34063)')
    A('            +5 V (1.6 А)   -----> CORE-2 +5V_EXT ------> +5 V  (DNP MT3608 #2)')
    A('            5V_LED/LED_RET -----> CORE-2 5V_LED / LED_RET (WS2812, низкий ключ на PWR-2)')
    A('')
    A('CORE-2 local:')
    A('  +5 V --> AP2112K --> +3V3 (periph/analog)   [+3V3 150 мА из 450]')
    A('  +5 V --> AP2112K --> +3V3_C6 (C6 radio)     [+3V3_C6 250 мА из 450]')
    A('  +5 V --> MP1584  --> +3V3_MCU (P4/PSRAM)    [+3V3_MCU 700 мА из 2400; вход ~510 мА]')
    A('  +5 V --> MT3608 #3 --> BL_20 V (LCD BL)     [BL_20 30 мА из 100; вход ~80 мА]')
    A('  AGND/DGND/PGND — звезда NT1/NT2; входы ±12/+5 защищены D19/D20/C112-C115, D2.')
    A('```')
    A('')
    A('## 2. Рельсы, импортируемые с PWR-2 J3')
    A('')
    A('| Рельс | Vout на CORE-2 | Бюджет | Пик | Нагрузки CORE-2 | Запас |')
    A('|---|---|---:|---:|---|---:|')
    for r in B.REV2_IMPORTED:
        A('| %s | %s | %d мА | %d мА | %s | %d %% |' % (
            r['name'], r['vout'], r['budget'], r['peak'], r['loads'], r['margin']))
    A('')
    A('Источник цифр: `hardware/power2/power-tree-pwr2.md` §2 (TPS61088 ×2, LMR33630 IBB).')
    A('Падения D7/D8 на PWR-2 (0.45 В) учтены: +11.7 В / −11.55 В на CORE-2.')
    A('')
    A('## 3. Локальные рельсы CORE-2 (rev.2)')
    A('')
    A('| Рельс | Источник | Преобразователь | Бюджет | Возможность | Запас | Основные нагрузки |')
    A('|---|---|---|---:|---:|---:|---|')
    local = {
      '+3V3': ('+5 V', 'AP2112K-3.3 (600 mA LDO)', 150, 450, 67,
               'LCD logic 60, MCP23017 x4 4, MCP4728 x2 2, MCP3208 1, 24C32 1, PCM5102A 20, PCM1808 VDD 15, mic (MAX9814+MEMS) 8, логика 10, датчики 20'),
      '+3V3_C6': ('+5 V', 'AP2112K-3.3 dedicated (600 mA)', 250, 450, 44,
                  'ESP32-C6 Wi-Fi/BLE peak 240, модуль/IO 10'),
      '+3V3_MCU': ('+5 V (вариант b)', 'MP1584 buck (3 A)', 700, 2400, 71,
                   'P4+PSRAM пик 600, IO 100; вход с +5: 510 мА'),
      'BL_20V': ('+5 V', 'MT3608 boost #3 (2 A switch)', 30, 100, 70,
                 'LCD backlight LED string 20-25 мА; вход с +5: 80 мА'),
    }
    for name in ('+3V3', '+3V3_C6', '+3V3_MCU', 'BL_20V'):
        src, conv, bud, cap, marg, loads = local[name]
        A('| %s | %s | %s | %d мА | %d мА | %d %% | %s |' % (name, src, conv, bud, cap, marg, loads))
    A('')
    A('Проверка запаса ≥25 %: все локальные рельсы проходят (+3V3 67 %, +3V3_C6 44 %,')
    A('+3V3_MCU 71 %, BL_20V 70 %). Импортируемые: +12 36 %, −12 58 %, +5 **25 %** (ровно),')
    A('5V_LED 78 %. Исключение — **VSYS/power-path** (см. §5), зафиксировано в O-2.')
    A('')
    A('## 4. +5 В: бюджет 1.0 → 1.6 А (O-1)')
    A('')
    A('| Нагрузка | Ток | Примечание |')
    A('|---|---:|---|')
    tot_b = 0
    for name, ma, src in B.REV2_5V_LOADS:
        if '5V_LED' in src:
            A('| %s | %d мА | отдельная ветвь PWR-2 (F5 2.5 А, Q7) |' % (name, ma))
        else:
            A('| %s | %d мА | +5 |' % (name, ma)); tot_b += ma
    A('| **Итого +5 (логика, вариант b)** | **%d мА** | из 1.6 А бюджета |' % tot_b)
    A('| 5V_LED (отдельно) | 550 мА | из того же TPS61088 через F5 |')
    A('| **Полная нагрузка на +5 PWR-2** | **%d мА** | 1.6 А бюджет / 2.0 А возможность |' % (tot_b + 550))
    A('')
    A('**Вариант (a):** MP1584 → +3V3_MCU перевести на +12 В (освобождает 510 мА на +5,')
    A('добавляет 216 мА на +12). Итоги: +5 = 1540 мА (77 % возможности),')
    A('**+12 = 366 мА при бюджете 330/возможности 420 → запас 13 % (<25 %)**.')
    A('')
    A('**Вариант (b):** оставить MP1584 на +5 В, принять бюджет **1.6 А**.')
    A('Итоги: +5 = 1500 мА (75 % возможности, **запас 25 %**), +12 = 150 мА (45 % бюджета).')
    A('')
    A('**Рекомендация — (b).** Причина: +12 В у PWR-2 ограничен 330 мА бюджетом / 420 мА')
    A('возможностью, и MP1584 съедает 216 мА резерва; +5 В имеет TPS61088 с 10-А ключом и')
    A('запас 25 % ровно. Вариант (a) — предпочтителен после 2S-пака (O-6) или увеличения')
    A('+12 бюджета PWR-2 до ≥450 мА; переделки CORE-2 не требует (только вход MP1584).')
    A('Тепло PWR-2 на +5: ≈0.76 Вт при 1.5 А (при бюджете 1.6 А — 0.81 Вт) — стенд обязателен.')
    A('')
    A('## 5. VSYS / power-path: 3 А против пика 2.74–3.38 А (O-2, D-35)')
    A('')
    A('| Сценарий (PWR-2 §2.2) | I(VSYS) @3.7 В | @3.0 В |')
    A('|---|---:|---:|')
    A('| Idle (меню, LED 20 %) | 0.66 А | 0.82 А |')
    A('| Типичный (1 модуль, LED 40 %) | 2.13 А | 2.62 А |')
    A('| **Реалистичный максимум** | **2.74 А** | **3.38 А** |')
    A('| Сумма паспортных бюджетов | 3.94 А | 4.87 А |')
    A('')
    A('BQ24074 power-path рассчитан на ≈3 А. Меры: **прошивочный cap WS2812 550 мА** +')
    A('профиль яркости (на батарее ≤30 %, автоснижение при `PWR_GOOD=0`), последовательное')
    A('включение рельсов (EN_RAILS → LED), запрет «3 картриджа + max яркость» на батарее.')
    A('Полная мощность — от внешнего 12 В (снимает +12, но **+5 остаётся от VSYS**); для')
    A('абсолютного максимума — 2S (O-6).')
    A('')
    A('## 6. Защита входов, inrush, DNP')
    A('')
    A('| Вход | Защита CORE-2 |')
    A('|---|---|')
    A('| `12V_EXT` | D2 SS34 (diode-OR с внешним J-DC), C110 100 мкФ/25 В, C111 100 нФ; на PWR-2 — D7 SS34 + F2 0.5 А |')
    A('| `N12_EXT` | **D19 SS34** series, **D20 SMAJ15A**, C112 100 мкФ/25 В, C113 100 нФ; на PWR-2 — D8 SS34 + F3 0.3 А |')
    A('| `+5V_EXT` | C114 100 мкФ/10 В, C115 100 нФ; на PWR-2 — F4 2 А + C-L-C |')
    A('| `5V_LED` / `LED_RET` | ключ Q7 + F5 2.5 А на PWR-2; на CORE-2 только 100 нФ у разъёма |')
    A('| USB-C | USBLC6-2SC6, F1 1.5 A, BQ24074 ILIM |')
    A('')
    A('DNP rev.2 (см. `rev2-plan.md` §3): MT3608 #1/#2, MC34063, BMS, EXPRESSION/SPARE (46 позиций). Остаются:')
    A('MT3608 #3 (BL), MP1584, AP2112K ×2, BQ24074, USB/ESD.')
    A('')
    A('## 7. Тестпоинты rev.2')
    A('')
    A('| TP | Цепь | Назначение |')
    A('|---|---|---|')
    tps = [('TP1','VBUS_CHG','USB-C input'), ('TP2','VSYS','power-path output'),
           ('TP3','12V','+12 V from PWR-2 (after D2)'), ('TP4','-12V','−12 V from PWR-2 (after D19)'),
           ('TP5','5V','+5 V from PWR-2'), ('TP6','3V3','+3.3 V peripherals'),
           ('TP7','3V3_MCU','+3.3 V MCU/PSRAM'), ('TP8','BATT_MON','battery ADC'),
           ('TP9','I2S_MCLK','12.288 MHz'), ('TP10','SD_CLK','SDIO clock'),
           ('TP11','USB_HS_DP','USB D+'), ('TP12','USB_HS_DM','USB D-'),
           ('TP13','AGND','analog ground'), ('TP14','DGND','digital ground'),
           ('TP15','PGND','power ground'), ('TP16','LED_DATA','WS2812 data'),
           ('TP17','CHIP_PU','reset'), ('TP18','BOOT','boot strap GPIO35'),
           ('TP19','3V3_C6','C6 rail'), ('TP20','BL_20V','backlight rail'),
           ('TP21','C6_CS','C6 SPI select'), ('TP22','C6_RST','C6 reset'),
           ('TP23','N12_EXT','−12 V input from PWR-2 (rev.2)'),
           ('TP24','5V_EXT','+5 V input from PWR-2 (rev.2)'),
           ('TP25','5V_LED','LED rail (rev.2)'), ('TP26','PWR_GOOD','supervisor (rev.2)'),
           ('TP27','EN_RAILS','EN analog rails (rev.2)')]
    for tp, net, why in tps:
        A('| %s | `%s` | %s |' % (tp, net, why))
    A('')
    A('## 8. Что нельзя заказывать до стенда PWR-2 (O-5/O-6)')
    A('')
    A('1. Тепло/КПД TPS61088 +5 В при 1.5 А (0.76 Вт) и +12 В при 330/420 мА.')
    A('2. −12 В LMR33630 IBB при VBAT 3.0 В / 150 мА (ripple, устойчивость EN).')
    A('3. Падение/нагрев J3 IDC-20 при 3 А (критерий ≤100 мВ / ≤30 °C) → IDC vs Micro-Fit.')
    A('4. Профиль яркости LED и последовательность EN по замерам VSYS-пиков.')
    A('5. Решение 1S2P vs 2S (O-6) — меняет бюджеты и выбор варианта (a)/(b).')
    A('')
    open(os.path.join(OUT, 'power-tree.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('written power-tree.md (rev.2)')

if __name__ == '__main__':
    md()
