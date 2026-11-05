# P1 — протокол измерений P4 vs H743 (frozen workload v1.0)

> **Статус: PRE-FREEZE / DO NOT FABRICATE.** Протокол «на приход стендов»: что запускать,
> что мерить, как решать. Workload заморожен — [docs/05](05-benchmark-workload.md) (v1.0),
> запуск — [docs/05a](05a-benchmark-howto.md), закупка — [docs/29](29-p1-order.md),
> стенд — [docs/26](26-p1-bench-kit.md), bring-up платы — [docs/43](43-p4-bringup.md).

## 1. Стенд и подключение

Минимальный комплект (docs/29): **ESP32-P4-Function-EV-Board** (32 МБ PSRAM) и
**NUCLEO-H743ZI2** (H743; при недоступности — NUCLEO-H753ZI), PCM5102A DAC + PCM1808 ADC
(loopback), USB-C data cable ×2, USB-C хаб с внешним питанием, ЛБП 0–30 В/≥3 А, электронная
нагрузка/резисторы, осциллограф ≥100 МГц, логический анализатор 8–16 каналов, DMM/термопара.
Для полного профиля: RGB FPC-40 800×480 + переходная плата, microSD 32 ГБ + модуль,
**ULPI HS PHY (USB3300) breakout для H743** (у Nucleo на борту только FS — для 8×8 UAC2 HS
нужен внешний PHY; для P4 HS встроен).

```
   ЛБП 5 В/3 А ── USB-C hub ──┬── P4-EV (USB-HS port, CDC)
                              └── Nucleo-H743ZI2 (+ USB3300 ULPI breakout)
   P4/H743 ── I2S ── PCM5102A ── loopback кабель ── PCM1808 ── I2S (ADC)
   P4/H743 ── FPC-40 ── RGB 800×480 (полный профиль)
   P4/H743 ── SDIO/SPI ── microSD 32 ГБ
   P4/H743 ── UART0/USB CDC ── ПК (лог, JSON/CSV)
   Осциллограф/LA: MCLK/BCK/LRCK, D+/D− (HS), питание/ripple
```

**Одинаковые условия:** один и тот же harness/commit, workload v1.0, один хаб/ЛБП, одинаковая
температура (24±3 °C), одинаковый кабель; для H743 — ULPI PHY проверен по enum до запуска
сценариев; для P4 — HS-порт (не FS). Каждый сценарий — 2 прогона с одинаковым seed и
**одинаковым checksum** (иначе run invalid).

## 2. Восемь сценариев

| # | Сценарий | Что запускать | Что мерить | Длительность | Порог (docs/05 §9) |
|---:|---|---|---|---|---|
| 1 | `fm_voice` | 8 synth voices, max project | max/p50/p95/p99 block, xruns, checksum | 100 warm-up + 2000 blocks | max ≤650 µs, p99 ≤500 µs, overruns 0 |
| 2 | `granular_track` | 8 mono tracks, granular, PSRAM random | block-времена, PSRAM random-read (MB/s, ns/line), cache miss | 2100 blocks | ≤650 µs, PSRAM ≥40 MB/s (H743 SDRAM ≥60) |
| 3 | `mix_bus` | mixing/FX/limiter half | block-времена, overruns | 2100 blocks | ≤650 µs, p99 ≤500 µs |
| 4 | `psram_stream` | 24.576 MB/s random PSRAM traffic | MB/s, ns/line, ошибки PSRAM | 2100 blocks | ≥40 MB/s @≤250 ns/line (P4); SDRAM ≥60 MB/s (H743) |
| 5 | `ui_frame` full | полный redraw 800×480 | frame time p50/p99, fps, flush MB/s (750 КиБ/кадр) | 10 мин | ≥30 fps (≤33.3 мс), flush ≥22.5 MB/s |
| 6 | `ui_frame_partial` | 4 dirty rect | frame time p50/p99, updates/s | 10 мин | ≥60 fps (≤16.7 мс) target |
| 7 | `usb_descriptor` + 8×8 enum | composite descriptor (HID+MIDI+UAC2 8×8+CDC), enumerate, 30–60 мин soak | build time, enum time, drops/reconnects, UAC2 8×8 bandwidth (2.304 MB/s), feedback | 30–60 мин | build ≤2 мс, enum OK, 0 drops/reconnect |
| 8 | **Полный профиль** | всё вместе: 8 моно + 8 голосов + UI 30/60 + USB 8×8 + SD | 24 ч soak: xruns, overruns, fps, PSRAM errors, T°, USB drops | 24 ч (1 ч smoke → 24 ч) | 0 xruns/overruns, стабильные fps, 0 USB drops, T° ≤70 °C |

**Порядок:** сначала 1–4 (audio/DSP), затем 4 (PSRAM), 5–6 (UI), 7 (USB), 8 (full). Если
1–4 не проходят — полный профиль не запускать (нет смысла), платформа уже «no».

## 3. Результаты (заполнять при замерах)

### 3.1 Audio (block time, µs)

| Сценарий | Платформа | min | p50 | p95 | p99 | max | overruns | checksum | pass |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| fm_voice | P4 | | | | | | | | |
| fm_voice | H743 | | | | | | | | |
| granular_track | P4 | | | | | | | | |
| granular_track | H743 | | | | | | | | |
| mix_bus | P4 | | | | | | | | |
| mix_bus | H743 | | | | | | | | |
| psram_stream | P4 | | | | | | | | |
| psram_stream | H743 | | | | | | | | |

### 3.2 PSRAM/SDRAM и UI

| Метрика | P4 | H743 | Порог |
|---|---:|---:|---|
| PSRAM/SDRAM random read, MB/s | | | P4 ≥40, H743 ≥60 |
| ns/line | | | ≤250 (P4) |
| ui_frame full, fps / flush MB/s | | | ≥30 fps / ≥22.5 MB/s |
| ui_frame_partial, updates/s | | | ≥60 fps target |
| frame p99, ms | | | ≤33.3 (full) |

### 3.3 USB 8×8 / full profile / soak

| Метрика | P4 | H743 | Порог |
|---|---:|---:|---|
| descriptor build, ms | | | ≤2 |
| enum time, s | | | стабильно |
| USB drops/reconnects 30–60 мин | | | 0 |
| UAC2 8×8, MB/s | | | 2.304 |
| 24 ч: xruns / overruns | | | 0 / 0 |
| 24 ч: PSRAM errors | | | 0 |
| 24 ч: T°, °C | | | ≤70 |
| Full profile fps full/partial | | | ≥30 / ≥60 |

## 4. Матрица решения

| Критерий | P4 | H743 | Решение |
|---|---|---|---|
| Audio max block | ≤650 µs @400 МГц | ≤650 µs @480 МГц | оба должны пройти |
| p99 block | ≤500 µs | ≤500 µs | оба |
| UI 800×480 | ≥30 fps full, ≥60 partial (DSI/RGB+DMA) | ≥30 fps (LTDC+DMA2D) | оба |
| USB 8×8/24/48 | HS, 0 drops | HS PHY (ULPI), 0 drops | оба |
| 24 ч soak | 0 xruns/overruns | 0 xruns/overruns | оба |
| PSRAM/SDRAM | ≥40 MB/s | ≥60 MB/s | оба |
| **Итог** | **оба прошли → P4** (дисплей/USB/экосистема) | **P4 не прошёл → H743** | при split — cut-list (docs/05 §9.2) |

Правило: **P4 выигрывает при равенстве**; H743 выбирается, только если P4 не проходит по
audio/UI/USB/PSRAM или нестабилен (SDK/silicon). Решение фиксируется в `docs/05` §9 (append)
и `spec/90` (D-xx).

## 5. Fallback H743 — что проверить в тех же прогонах

| Узел | Что мерить | Порог |
|---|---|---|
| LTDC RGB565 | pixel clock, frame time, DMA2D, 800×480@60 | ≥30 fps, без tearing |
| ULPI HS PHY (USB3300) | enum, UAC2 8×8 2.304 MB/s, feedback, drops | 0 drops, 60 МГц клок стабилен |
| SDRAM (FMC) | random read MB/s, ns/line, latency | ≥60 MB/s, без ECC-ошибок |
| C6 over SPI (esp-hosted) | RPC latency, throughput, Wi-Fi/BLE при UI+audio | латентность ≤100 мс, без xruns |
| Питание | 3.3 В rail, load-step, тепло | 3.0–3.6 В, ≤70 °C |

## 6. Чек-лист первого дня

1. [ ] Распаковать/сфотографировать платы, сверить ревизии/модули (P4-EV 32 МБ, Nucleo-H743ZI2).
2. [ ] Прошить harness (`firmware/bench`, pio env `bench_p4` / `bench_h743`); для H743 — ULPI breakout.
3. [ ] ЛБП 5 В/3 А, лимит тока; DMM: 3.3/5 В; осциллограф — ripple.
4. [ ] UART0/USB CDC лог, версия прошивки/commit, seed, workload v1.0.
5. [ ] Host baseline: `firmware/bench/results/host.json` (sanity, не вердикт).
6. [ ] Smoke: fm_voice 2100 blocks, checksum; затем granular/mix/psram.
7. [ ] UI: дисплей FPC-40, ui_frame 10 мин, ui_frame_partial 10 мин.
8. [ ] USB: descriptor build, enum, 30 мин soak; H743 — ULPI enum до этого.
9. [ ] Записать JSON/CSV в `firmware/bench/results/p1-<platform>-<date>/` + `docs/p1-results-template.csv`.
10. [ ] Тепло/питание: T° после 1 ч; load-step; журнал аномалий.

## 7. Форма отчёта и куда писать

- Машиночитаемо: `docs/p1-results-template.csv` (по строке на метрику), плюс JSON harness в
  `firmware/bench/results/`.
- Куда: **`docs/05-benchmark-workload.md` §9** — append «P1 results (P4/H743)», решение;
  **`hardware/core2/dfm.md`** (P4 bring-up/самотест) и **`hardware/cores3/dfm.md`** (S3-lite)
  — факты bring-up; **`docs/43-p4-bringup.md`** — шаги/аномалии; **`spec/90`** — D-xx решение.
- Формат: `platform, scenario, metric, value, threshold, pass, checksum, date, commit, notes`.
- Итоговый вердикт — одна строка: `P1 decision: P4|H743 (date, commit, max block, p99, fps, USB, soak)`.

## 8. Риски

1. P4 SDK/платформа молодые — вердикт только по device-прогонам, не по host.
2. У Nucleo H743 нет HS PHY на борту — без USB3300 сценарий 7/8 недействителен.
3. Workload v1.0 заморожен: любое изменение → v1.1 и повтор на обеих платформах.
4. Температура/питание влияют на max block — фиксировать T° и входное 5 В в отчёте.
5. PSRAM/SD/USB на host — proxy; вердикт только с реальным железом.
