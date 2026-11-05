# Разведка: аналогичные проекты — что взять для Букифона

Дата: 05–06.11.2025. Источники — официальные сайты, GitHub, вики (проверялись через веб-поиск;
ссылки в конце). Цель: не изобретать заново и выбрать лучшие практики.

## Сводная таблица

| Проект | Железо | Софт | Открытость | Что взять |
|---|---|---|---|---|
| **Synthstrom Deluge** | Renesas RZ/A1L Cortex-A9 400 МГц, 64 МБ SDRAM, PIC для кнопок, OLED/7-seg | C/C++ bare metal, своя ОС | **прошивка открыта** (community firmware) | модель «открытая прошивка = мегафирм»; SDRAM под сэмплер; сетка + минимальный экран |
| **Dirtywave M8** | Teensy 4.1 | tracker-воркфлоу, 8 моно-треков, WavSynth/MacroSynth/FM 4op/12 алг., таблицы модуляции | закрыт | формат «инструмент + таблицы модуляции» (наш 3D-мод-матрикс 16 слотов — то же), 8 моно-треков как рабочий минимум |
| **Polyend Tracker** | NXP i.MX 6ULL, 1 ГБ DDR3, 16 ГБ eMMC, 5″ 800×480 IPS, 5000 мА·ч | Embedded Linux | закрыт | 5″ 800×480 — подтверждение нашего экрана; режимы wavetable/granular на один сэмпл; matrix-модуляция |
| **Polyend Tracker Mini** | 184×110×15 мм, 450 г | Linux | закрыт | ориентир по габаритам для «карманной» версии (не нашей) |
| **Electrosmith Daisy** | STM32H750 + SDRAM, аудио-кодек | libDaisy/DaisySP, Arduino-совместимость | открытая платформа | SDK и библиотека DSP как образец нашего module SDK; Seed как «мозг» в чужих проектах |
| **PreenFM3** | MCU + DAC, 6-оп FM | открытая прошивка, импорт DX7, браузерный редактор | открыт | FM-движок и формат пресетов; UI «мало кнопок + редактор» |
| **Mutable Instruments** | eurorack-модули, STM32 | открытые схемы + код (Beads открыт в 2026) | схемы/код | эталон открытого железа: schematics + BOM + DSP-ссылки; атрибуция и «прозрачность» |
| **Zynthian** | Raspberry Pi + открытый корпус/кит | Linux, 100+ синтов, LV2 | открытый кит | модель комплекта (kit) и корпусов; каталог плагинов |
| **monome norns** | sound computer | Lua + SuperCollider-движки | открыт | «скрипт = инструмент»: наш Lua-слой и магазин модулей; библиотека патчей |
| **mutable/hexinverter и др.** | — | — | — | практика лицензий (CERN/GPL) и NOTICE |
| **ribbon-synth (Daisy)** | Daisy Seed + FSR/softpot | DaisyDuino | открыт (репо) | полный комплект в репо: прошивка + BOM + PCB BOM + datasheets — образец структуры нашего репо |

## Что это даёт Букифону

### 1. Открытая прошивка — главный рычаг
Deluge: сообщество сделало мегафирм (сотни фич) поверх открытой прошивки. Наш план
«модули сообщества + открытый код» совпадает; стоит перенять:
- публичный **plugin API с версией ABI** и каталог модулей;
- возможность пересобрать прошивку без проприетарных тулчейнов;
- обратная совместимость форматов проектов (versioned JSON/binary).

### 2. Мод-матрица и «таблицы» — не новинка, но нужна
M8 «instrument tables» ≈ наши 16 слотов 3D-мод-матрицы; Syntakt/Digitakt — p-locks и LFO.
Взять у M8: таблицы как отдельный пресет-ресурс, переиспользуемый разными инструментами.

### 3. 5″ 800×480 — рабочий стандарт
Polyend Tracker использует ровно 5″ 800×480 IPS. Наши 108 × 64.8 мм и 800×480 — попадание
в зрелый формат (дешёвые панели, готовые FPC, RGB/DSI варианты). Это подтверждает выбор
экрана в v0.4.

### 4. SDK модулей — как у Daisy/Norns, но без их ограничений
- Daisy: C++-классы + Arduino-совместимость — удобно, но аудио-рейт без песочницы;
- Norns: Lua-скрипты поверх движка — безопасно по скорости, но нужен движок на C.
Наш план (C++ audio-rate + Lua control-rate + RP2350-картридж для недоверенного) =
гибрид обеих моделей. Взять у Norns: **каталог/репозиторий скриптов**, примеры, «скрипт
в 100 строк» как порог входа.

### 5. Комплект и документация
Zynthian и Mutable показывают: люди покупают **киты** и собирают по фото-гайду.
Наш `docs/02-build-guide.md` + STL + BOM + печатные шаблоны 1:1 — уже этот путь; добавить
фото-этапы сборки и «список покупок одной ссылкой».

### 6. Чего избегать
- **Закрытые прошивки** (M8, Polyend) — сложно расширять, сообщество обходит.
- **Linux на борту** (Polyend, Zynthian) — большой RAM/CPU за счёт батареи и сложности;
  нам для bare-metal P4 достаточно, если уложимся в бюджет (см. docs/11).
- **Много кнопок без экрана** (старый Deluge) — плохо для FM-редактора; наш экран 5″
  и 16 энкодеров — правильный баланс.

## Приоритеты для нашего SDK (по итогам разведки)

1. ABI v1: `name/version/params/init/process/set_param/ui` + лимиты (стек, WCET, без malloc).
2. Каталог модулей в репо: `modules/<name>/` с `module.json` (метаданные, лицензия, автор),
   исходником, примером пресета, скриншотом.
3. Примеры с первого дня: gain/FX, LFO-модулятор, простой грануляр (3 штуки).
4. Формат проекта: versioned JSON + бинарные сэмплы отдельно (совместимость вперёд).
5. Лицензии модулей: по умолчанию GPL-3.0-or-later, разрешены MIT/Apache для примеров.

## Ссылки

- Deluge community firmware: https://delugecommunity.com/doxygen/ · https://github.com/SynthstromAudible/DelugeFirmware
- Dirtywave M8: https://dirtywave.com/
- Polyend Tracker: https://polyend.com/tracker/ · обзор: https://www.thomann.de/ro/prod_pdfreview_73149-fmu357rev_polyend.pdf
- Polyend Tracker Mini (хардвер): https://fehmijaafar.net/wiki-iot/index.php?title=Polyend_Tracker_Mini
- Electrosmith Daisy: https://www.electro-smith.com/daisy/daisy · пример открытого проекта: https://github.com/ideocentric/ribbon-synth
- PreenFM3: https://github.com/Ixox/preenfm3
- Mutable Instruments: https://mutable-instruments.net/ · открытие Beads: https://www.hispasonic.com/noticias/mutable-instruments-beads-pasa-ser-codigo-abierto-cuatro-anos-despues-cierre-marca/49296
- Zynthian: https://wiki.zynthian.org/
- monome norns: https://monome.org/docs/norns/
