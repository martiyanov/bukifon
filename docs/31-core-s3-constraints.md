# CORE-S3: ограничения и профиль «народной» платы (консультация GPT)

Источник: консультация по CORE-S3 (полный текст — отчёт раунда). Это **не** «P4, но дешевле»:
у S3 другой бюджет GPIO, памяти и USB, и это меняет и плату, и SKU-профиль.

## 1. GPIO: «45 пинов» — иллюзия

У ESP32-S3-WROOM-1-N16R8 часть выводов занята flash/OPI-PSRAM и USB (GPIO19/20),
GPIO35–37 нельзя считать свободными. Реально доступно ~38–40 линий под всё.

| Интерфейс | «Наивно» | Реалистично |
|---|---:|---:|
| RGB565 | 20 (16+4) | 18–20 (DE-only экономит 2) |
| I²C панель/CV/гейдж | 3 | 2 + опц. 1 IRQ |
| I²S ADC+DAC | 5 | 5 |
| SD | 6+CD | **3** (1-bit SDMMC, без CD) |
| USB FS | 2 | 2 |
| CV SPI | 3+CS | 4 |
| MIDI DIN | 2 | 2 |
| LED data / BL PWM | 2 | 2 |
| GATE OUT | 2 | 0–2 (на expander) |
| Debug UART | 2 | **0** (USB CDC/JTAG) |

Меры: **1-bit SDMMC**, DE-only RGB (если MPN позволяет), убрать UART, перенести
GATE OUT/rail EN/LCD DISP/SD detect на MCP23017 PANEL-2. Дополнительный MCP23017 не нужен.

## 2. USB Full-Speed: потолок — endpoints

Stereo 24/48: 288 КБ/с в одну сторону, 576 КБ/с duplex — по полосе проходит.
Но у S3 USB-OTG **6 endpoint numbers** (5 bidirectional + 1 IN):

| Функция | Endpoints |
|---|---|
| UAC playback / capture / feedback | ISO OUT / ISO IN / ISO IN |
| MIDI | bulk IN + OUT |
| CDC data + notification | bulk IN + OUT + int IN |
| HID | int IN |

Это ровно у потолка — MSC/второй MIDI/vendor endpoint уже не влезут.
Рекомендация: **ESP-IDF + esp_tinyusb**, UAC2 stereo 24/48 (+ fallback 16/48),
FIFO 4 КиБ RX + 4 КиБ TX в internal SRAM, feedback по I²S clock, CDC rate-limit,
USB IRQ выше SD/UI, но без DSP/копирования framebuffer в колбэке.
Критерий: 30–60 минут UAC duplex + MIDI flood + HID + CDC + SD + Wi-Fi → **0 drops**.

## 3. Дисплей: RGB, один framebuffer

| Режим | Оценка S3 |
|---|---|
| RGB scanout | 50–60 Гц (панельная развёртка) |
| Full redraw UI | **10–20 fps** |
| Partial dirty rects | **30–60 updates/s** |
| Full 30 fps | stretch goal, конфликтует с PSRAM/DSP/Wi-Fi |
| Double buffering | не делать (ещё 750 КиБ + трафик) |

Конфигурация: один framebuffer 800×480×2 = **750 КиБ в PSRAM**, bounce buffers
8–16 строк (25–50 КиБ) во внутренней SRAM, dirty rectangles, синхронизация по VSYNC.
**SPI-дисплей для 800×480 не использовать** (13 fps максимум и хуже).

## 4. Питание 3.3 В

| ИС | Плюсы | Минусы | Вердикт |
|---|---|---|---|
| **TPS63802** | 1.3–5.5 В, 2 А класс, 11 µA IQ | DFN, layout | **основной** |
| TPS63020 | проверенная, до 2 А при Vin>2.5 В | старее | fallback |
| TPS63820 | телеметрия I²C | дорого/сложно | избыточно |

Проектировать **1 А continuous / ≥1.5 А transient**: 3.3 Вт выход, КПД 90–94 %,
потери 0.21–0.37 Вт, при VSYS 3.0 В вход ~1.2 А → дроссель ≥3–4 А sat.
2×22 мкФ + 10 мкФ у модуля, отдельная π-фильтрация аналогового питания кодеков,
`PG` → supervisor/CHIP_PU, forced-PWM при записи аудио, Wi-Fi TX cap, не писать flash
во время записи. Load-step: 150 → 900 мА (10–50 µs), rail 3.0–3.6 В, без reset/щелчка.

## 5. Профиль бенчмарка S3 (отличается от общего!)

Общий workload использует 8 МиБ PSRAM-буфер — на N16R8 это вытесняет framebuffer.
Для S3-профиля: **4 МиБ sample pool + один framebuffer 750 КиБ + аудиобуферы**,
random-read rate сохранить (512×64 Б линий/блок).

Критерии S3-base: 0 audio xruns; **max block ≤650 µs**; **≥15 fps full / ≥30 partial**;
0 LCD drift за 1 час; USB composite soak 30–60 мин без дропов; 3.3 В без reset/pop.

## 6. Порядок: devkit-spike до PCB

1. S3 как **полноценный третий профиль P1** (не «reference only»).
2. Devkit: S3-N16R8 + реальный RGB FPC-40 + PCM5102A/1808 + SD, **2–3 дня**.
3. Таблица pin allocation + endpoint allocation.
4. Три совместных теста: memory/audio/display stress; USB composite soak; power/load-step/thermal.
5. Только после pass — CORE-S3 rev.0. P4/H743 P1 идёт параллельно.

## 7. Расхождение, которое надо развести

`docs/27` объявляет S3 первым SKU, а `docs/05` рассматривает S3 как reference.
Правильно: **два профиля выхода** — `S3-base` (первый SKU, критерии выше) и `full/P4`
(8 дорожек/8 голосов, HS USB 8×8, DSI). Оба используют PANEL-2 и PWR-2.
