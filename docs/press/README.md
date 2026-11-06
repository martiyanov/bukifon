# Пресс-кит Букифона

Материалы для публикаций. Все изображения — собственные рендеры/скриншоты проекта
(лицензия CC-BY-SA-4.0, атрибуция «Bukifon project»).

## Буилерплейт (RU)

**Букифон** — открытый настольный синтезатор-сэмплер-секвенсор с 42 клавишами Lapka-42,
16 энкодерами, 5″ экраном 800×480, 10 джеками, 2 фейдерами и микрофоном. Корпус печатается
на 3D-принтере, схемы — KiCad (CERN-OHL-S), прошивка — C++ (GPL-3.0), SDK модулей открыт.
Цель — «народный» инструмент за ≤$299, который можно собрать и починить.

## Boilerplate (EN)

**Bukifon** is an open-source desktop synth/sampler/sequencer: 42 keys, 16 encoders, 5″ 800×480,
10 jacks, 2 faders, microphone; 3D-printed case, KiCad hardware (CERN-OHL-S), C++ firmware
(GPL-3.0), open module SDK. Target: a community instrument at ≤$299 that anyone can build and repair.

## Факты

- 380×210×61.5–63 мм, 231–314 г, 4 варианта корпуса (A/B/B-light/C);
- P4: USB HS UAC2 8×8, RGB565, 32 МБ PSRAM; S3-lite: SPI-экран, stereo USB;
- 4 внутренние партии + 8 внешних MIDI-треков; GEN (prob/euclid/mutate/scale/arp/evolve);
- микрофон I2S MEMS + 3.5 мм jack, mute+LED; запись/битбокс; вокодер v1.1;
- открытые: KiCad, C++, STL, paperkit 1:1, SDK; self-test 21; 351 host-тест.

## Изображения

| Файл | Что |
|---|---|
| `design-panel-1.jpg` | рендер панели/дизайна |
| `screenshot-demo.jpg` | веб-демо интерфейса (зеркальная карта ручек) |
| `ui-night.jpg` | экран 800×480, тема Night |

## Ссылки

- сайт: https://martiyanov.github.io/bukifon/ · демо: `/demo/`
- репозиторий: https://github.com/martiyanov/bukifon
- статус/ворота: docs/75 · ограничения: docs/76 · аналоги: docs/79

## Контакт

GitHub Issues (баг-репорт: версия, self-test JSON, шаги) — основной канал.
