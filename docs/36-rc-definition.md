# Definition of Done для v1.0-rc (P4, RGB) — решение заказчика 06.11.2025

«Рабочая версия» = **физически собранный P4-Complete kit** (ESP32-P4 + ESP32-C6, RGB565/DSI,
HS USB), который включается, играет, сохраняет проект и проходит повторяемый тест.
S3-base переведён в «lite later» (D-58) и критерии для него — отдельный раздел §7. Рендеры и host-тесты доказывают прогресс,
но не собранный продукт.

## 1. Что входит в S3-base v1.0-rc

| Область | Требование |
|---|---|
| Звук | **8 стерео/моно дорожек + 8 голосов**; 4-оп FM + wavetable + SVF/ZDF; 1 insert + 2 send; P4: 32 МБ PSRAM |
| Секвенсор | 4×16 паттерн, BPM, play/stop, mute, p-lock, save/load с версией |
| UI | **RGB565 800×480**: full **≥30 fps**, partial ≥60; 16 энкодеров, 42 клавиши |
| USB | **HS**: UAC2 8×8/24/48 + MIDI + HID + CDC; reconnect без перезагрузки |
| Ввод/вывод | 10 джеков CV/GATE, 2 фейдера, MIDI TRS in/out, microSD |
| Питание | внешний БП (первая партия без батареи, D-62); brownout/reset без повреждения SD |
| Корпус | B-light 230 г / 11.1 ч, 6×M3, шов 193+190, без люфтов и дребезга |
| Надёжность | 24 ч soak без xruns/drift; recovery после выдёргивания SD/USB |
| Обновление | прошивка по USB/CDC, recovery-режим, rollback |

## 2. Критерии приёмки (тесты)

| # | Тест | Критерий |
|---|---|---|
| 1 | Audio stress 1 ч | max block ≤650 µs, p99 ≤500 µs, 0 xruns |
| 2 | UI 10 мин | full ≥15 fps, partial ≥30 updates/s, 0 LCD drift |
| 3 | USB composite 30–60 мин | UAC duplex + MIDI flood + HID + CDC: 0 drops/reconnect |
| 4 | Power/load-step | 3.3 В в 3.0–3.6 В, без reset/попа; DC/DC ≤80 °C |
| 5 | SD corruption/recovery | выдёргивание на записи → проект не теряется (журнал/резерв) |
| 6 | 24 ч soak | 0 watchdog/xruns/drift, память без утечек |
| 7 | Сборка | 3–5 экземпляров собираются за задокументированное время, без доработок напильником |
| 8 | Self-test | экран, кнопки, энкодеры, CV/GATE loopback, серийник — PASS |

## 3. Критический путь (S3 и P4 раздельно!)

| Ветка | Что | Срок |
|---|---|---|
| **P4 (v1.0-rc)** | RC-DoD → CORE-2/PANEL-2/PWR-2 DFM+testability → P1-стенд P4/H743 → MCU freeze → rev.1 PCB → 3–5 прототипов → bring-up → надёжность → пилот | **12–16 недель**, respin +4–6 |
| **S3 (lite, позже)** | CORE-S3 rev.1 после P4-релиза; SPI-экран, 8 моно/6 голосов | после v1.0 |
| Общее | PANEL-2/PWR-2 rev.1, корпус, доки | параллельно |

P1-стенд (P4 EV + H743 + кодеки) — **заказан/утверждён** (D-60) и блокирует только дату
MCU freeze; всё остальное (DFM, HAL, UI, SDK, BOM, сборка) идёт параллельно.
S3 lite — после v1.0 (D-58).

## 4. Что можно сделать до железа

1. Этот DoD + план vertical slice.
2. **S3 HAL** и сквозной сценарий boot → UI → input → audio → save/load (docs/24, firmware/).
3. **Product BOM** с MPN, поставщиками, MOQ, landed cost, заменами (BOM-s3).
4. DFM/testability: тест-пойнты, self-test, серийник, recovery — до разводки.
5. Каркас сборочного гайда (точный порядок — после первой физической сборки).

## 5. Три метрики после релиза

| Метрика | Как |
|---|---|
| Activation rate | доля kits, которые за 14/30 дней включились, дали звук и сохранили проект |
| Support burden | критические дефекты/100 устройств + support hours/RMA за 90 дней |
| Qualified conversion | waitlist → deposit → paid; contribution margin после брака/комиссий |

## 6. Доказательства рабочей версии (для сообщества/инвестора)

1. Непрерывное демо 3–5 минут: boot → ввод → секвенсор → сэмпл → save → reboot → load → USB audio.
2. Фото/видео одной реальной сборки (внутренности, кабели, закрытый корпус, масса).
3. Публичный test report (24 ч soak, xruns, block time, fps, USB reconnect, SD recovery, температура).
4. Release BOM и экономика (MPN, landed COGS, MOQ, yield).
5. Воспроизводимый release bundle: тег, герберы, PNP, STL, прошивка, recovery, гайд, known limits.
