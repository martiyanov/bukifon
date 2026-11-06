# Аналоги 2025–2026: с кем сравнивают Букифон

Обзор актуальных устройств и что из их опыта мы берём (или осознанно не берём).
Цены — розница на 06.11.2025 (могут меняться); источники внизу.

## 1. Сравнение

| Устройство | Цена | Треки/полифония | Экран | Клавиши/ручки | I/O | Микрофон | Открытость |
|---|---|---|---|---|---|---|---|
| **Букифон P4** (наш) | **$299** (Full $399) | 4 внутр. + 8 MIDI, 8 стерео (P4) | 5″ **800×480** RGB | **42 клавиши + 16 энкодеров + 2 фейдера** | 10 джеков, CV/GATE, USB HS UAC2 8×8, DIN+USB MIDI | **да** (I2S MEMS + 3.5 мм) | **KiCad + C++ + STL, DIY** |
| Elektron Digitakt II | ~$1099 | 16 аудио/MIDI, стерео | OLED | 16 триггеров + энкодеры | MIDI in/out/thru, USB | нет | закрыто |
| Polyend Play+ | ~$999 | 16 стерео, 4 синт-движка | OLED | 8×8 падов | 3.5 мм MIDI in/out, USB-C | нет | закрыто |
| Ableton Move | $549 | 4 трека | OLED | 32 пада, 9 энкодеров | USB-C, 3.5 мм | **да** + динамик, батарея | закрыто |
| Dirtywave M8 Model:02 | ~$699 | 8 треков, стриминг с SD | маленький | 8 кнопок-падов | 3.5 мм, USB | нет | закрыто (трекер) |
| Synthstrom Deluge | ~€1300 | 64 голоса | OLED | 8×16 падов + энкодеры | MIDI, CV/GATE, USB | нет (версия с микрофоном — 7-я ревизия?) | **открытая прошивка** (community) |
| TE EP-133 K.O. II | ~$200–300 | 12 голосов, сэмплер | LED | 12 падов | 3.5 мм in/out, USB | **да** | закрыто |
| Sonicware Liven (Ambient/Texture) | ~€270–280 | 3–4 трека | OLED | 27 клавиш | MIDI, USB | нет | закрыто |

## 2. Наше позиционирование

**Букифон — не «ещё один грувбокс», а открытый настольный инструмент с полным набором
физических органов управления и ремонтопригодностью.**

- **Цена**: $299 — ниже Digitakt II/Play+ в 3× и ниже Move/M8; дороже EP-133, но с 42
  клавишами, 16 энкодерами, 10 джеками, CV/GATE и экраном 5″.
- **Эргономика**: полноценная клавиатура Lapka-42 + 16 энкодеров + 2 фейдера + зеркальная карта
  «ручка ↔ ячейка» (docs/68) — не «8 падов и меню».
- **Открытость**: KiCad, C++ SDK, STL, тест-поинты, self-test 21 — можно собрать/починить/изменить.
- **Гибрид**: синтез + сэмплер + секвенсор + внешний MIDI-хаб + CV/GATE — в одном корпусе.
- **DIY/3D-печать**: B-light 231.4 г, печать на обычном принтере.

## 3. Чему учимся у аналогов

| Урок | У кого | Что делаем |
|---|---|---|
| **Скорость «идея → трек»** | TE EP-133, Move | быстрый старт docs/77, UX-тест 8 задач, REC/битбокс за 3 жеста |
| **Мощный секвенсор и p-lock** | Digitakt II, Play+ | 16 шагов, p-lock CC, GEN (prob/euclid/mutate), EXT-треки |
| **Портативность/автономность** | M8, Move (4 ч батарея) | батарея — опция v1.1 (D-39), корпус B-light |
| **Комьюнити-прошивка** | Deluge | открытый SDK, примеры модулей, docs/24 |
| **Простота и цена** | EP-133 | $299 при полном наборе органов; S3-lite $199 |

## 4. Где не конкурируем (честно)

- **Экосистема/DAW-интеграция** (Ableton Move + Live) — у нас открытый USB-MIDI/UAC2, не Live.
- **Полифония/память** (Digitakt II: 400 МБ / 20 ГБ) — у нас PSRAM 32 МБ + SD, стриминг позже.
- **Готовые библиотеки сэмплов/пресетов** — у нас открытые банки и генеративность.
- **Массовое производство/софт-поддержка** — у нас малые партии, DIY, сообщество.

## 5. Вывод

В нише «открытый, ремонтопригодный, с клавиатурой и энкодерами, за $299» прямых конкурентов
нет. Ближе всего по духу — Deluge (открытая прошивка, но дорого) и EP-133 (дёшево, но закрыто
и без клавиатуры). Наша задача — довести качество сборки/UX до уровня Elektron/TE, сохранив
открытость и цену.

## Источники (06.11.2025)

- Elektron Digitakt II — [musicstore](https://www.musicstore.com/en_RU/RUB/Elektron-Digitakt-II/art-SYN0008985-000), $1099
- Polyend Play+ — [vintageking](https://vintageking.com/products/polyend-play-16-track-groovebox-synth-sequencer), $999.99
- Ableton Move — [ableton.com](https://www.ableton.com/de/move-tour/), $549; [Sweetwater](https://www.sweetwater.com/store/detail/MoveMelodicBun--ableton-move-standalone-instrument-with-melodics-lessons)
- Dirtywave M8 Model:02 — [equipboard](https://equipboard.com/items/dirtywave-m8-tracker-model-2), $699
- Synthstrom Deluge — [brack.ch](https://business.brack.ch/en/product/1897234), CHF 1335
- TE EP-133 K.O. II — [Reverb](https://reverb.com/item/96452923-teenage-engineering-ep-133-k-o-ii-64mb-sampler-composer-2025), ~$200–300
- Sonicware Liven — [lenzotti](https://shop.lenzotti.it/negozio/tastiere/synth-a-tastiera/sonicware-liven-texture-lab/), €271; [audiofanzine](https://fr.audiofanzine.com/synthe-numerique/sonicware/liven-ambient/avis/r.217662.html), 275€
