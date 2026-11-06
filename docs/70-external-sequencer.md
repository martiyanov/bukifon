# Букифон как секвенсор для внешних синтезаторов

Требование: **такая же сильная база для внешнего MIDI-секвенсинга**, как у Octatrack и др.
То есть Букифон — не только самозвучащий инструмент, но и **мозг/хаб**: ведёт внешние
синтезаторы, модули, CV-голоса, а внутренние партии играют одновременно.

## 1. Что берём у Octatrack (паритет-чек)

| Возможность Octatrack | Букифон (цель) |
|---|---|
| 8 MIDI-треков независимо от аудио | **8 внешних MIDI-треков + 4 внутренние партии** одновременно |
| канал/программа на трек | Channel 1–16, Program Change per track (и per step — later) |
| ноты: pitch/velocity/length, арпеджио | note/vel/length, ARP (up/down/updown, rate), chord later |
| p-lock CC на шаг | CC-значение на шаг + выбор CC# (автоматизация) |
| CC learn | «изучи CC» с внешнего контроллера/ручки |
| 3 LFO на трек | LFO на трек (v1), 2–3 позже |
| swing, micro-timing | swing глобальный + micro-timing на шаг |
| MIDI clock master/slave | clock out (DIN+USB), clock in, transport start/stop |
| program change | PC на трек/паттерн |
| scale/transpose | гаммы/транспонирование общие с GEN |
| запись в реальном времени | live record с клавиш/MIDI-in в шаг |

Чего у нас пока нет и это ок: сэмплерные возможности Octatrack не относятся к внешнему MIDI,
а CV/GATE у нас есть отдельно — это преимущество.

## 2. Архитектура

```
                 ┌───────────── SEQ ENGINE ─────────────┐
                 │ 4 internal parts (FM/wavetable)      │
                 │ 8 ext MIDI tracks (ch/PC/CC/p-lock)  │
                 │ GEN: prob/euclid/mutate/scale/evolve │
                 │ трансп��рт, swing, micro, clock       │
                 └──────┬───────────────┬───────────────┘
                        │ audio         │ MIDI
                   CORE-2 DAC      DIN OUT / USB MIDI / CV-GATE
                                        │
                              внешние синтезаторы, модули
```

- Единый sequencer: 12 «треков» (4 внутренних + 8 внешних), общий бар/шаг, общий GEN,
  общий транспорт; у внешних — свой канал/PC/CC.
- **MIDI OUT**: DIN TRS-A (6N137/74HCT125, есть на CORE-2) + USB MIDI (composite).
- **MIDI IN**: DIN + USB — для clock, live record, CC learn.
- **CV/GATE**: 4 CV OUT + GATE OUT — внешние аналоговые голоса; 4 CV IN — модуляция/экспрессия.
- **Питание**: MIDI-хаб работает и от батареи (P4 + C6), DIN out не требует USB-хоста.
- **USB-хост** (P4 умеет host) — будущий режим для USB-MIDI синтезаторов/клавиатур
  (нужен USB-A или OTG-порт; в rev.3 — опция, не блокер).

## 3. UX: как это выглядит на 16 ручках/42 клавишах/2 фейдерах

| Страница | Назначение | 16 ячеек |
|---|---|---|
| **MAIN** | внутренние партии + макросы | как сейчас (docs/68) |
| **EXT** | 8 внешних треков: выбор трека, канал, PC, нота/шаг, p-lock CC | CH / PROG / VEL / LEN / CC# / CC VAL / SWING / CLK |
| **SEQ** | общий секвенсор: паттерн/бар/шаг | 4 внутренних + 8 внешних |
| **GEN** | генеративность для выбранного трека (внутр./внешн.) | PROB / EUCLID / MUTATE / SCALE / ARP RATE / MODE / EVOLVE / SEED |

- **8 внешних треков** выбираются клавишами пар (верхние 8 клавиш левого кластера) или кликом;
- **p-lock**: удержать шаг + крутить энкодер → CC-значение на этот шаг (как у Octatrack);
- **CC learn**: удержать CC-энкодер + принять CC с MIDI-in;
- **live record**: играешь на клавишах/MIDI-клавиатуре при включённой записи — ноты пишутся в шаг;
- **фейдеры**: F1 = громкость/динамика внешних треков? нет — F1/F2 остаются TRACK/SCENE/DJ;
  для внешних треков — «performance» через макросы (отправка CC на выбранный трек);
- **HOME** возвращает MAIN; EXT — отдельная страница, не меняет L1.

## 4. Стандарт качества (что считается «сильной базой»)

| # | Требование | Критерий |
|---|---|---|
| 1 | 8 внешних треков | независимые каналы 1–16, PC, velocity, length |
| 2 | p-lock CC | ≤4 CC на трек, значение на шаг, интерполяция по шагам |
| 3 | Clock | master 24 ppqn, slave, stable jitter ≤1 ms |
| 4 | Latency | note-on ≤2 ms от шага (DIN), компенсация задержки |
| 5 | Live record | quantize on/off, шаг/такт, без потери нот |
| 6 | GEN для внешних | prob/euclid/mutate/scale/arp работают на внешних треках |
| 7 | Transport | start/stop/continue, общий с внутренними |
| 8 | Swing/micro | swing ±, micro-timing на шаг (±1/32) |
| 9 | Save/load | внешние треки в проекте/пресете |
| 10 | MIDI-роутинг | DIN out + USB out одновременно, без дублей |

## 5. Этапы

| Версия | Что |
|---|---|
| **v1.0-rc** | 8 ext-треков: канал/PC/нота/vel/length, clock out/in, transport, p-lock CC (1 CC), GEN на внешних, live record (прост.), save/load |
| v1.1 | 4 CC на трек, LFO на трек, chord, ratchet, program change на шаг |
| v1.2 | USB-MIDI host (P4 host mode), MIDI merge/thru, 2-й DIN out (опция), MPE-подобное |
| backlog | внешний секвенсор как «MIDI-хаб» с маршрутизацией на 4 порта |

## 6. Ограничения и честность

- P4 — **USB device** для MIDI; USB-хост требует отдельного режима/порта (rev.3 опция).
- Один DIN OUT: для нескольких синтов — chain через THRU или USB-MIDI интерфейс; 2-й выход — опция.
- CV/GATE — 4+1, для большего — модули/мультиплексор (backlog).
- Jitter DIN ~0.3–1 мс; clock + transport; аудио-latency не влияет на MIDI-тайминг.
- Всё это не требует новых кнопок: 16 энкодеров/42 клавиши/2 фейдера/10 джеков (docs/68).

---

## 7. Реализация в прошивке (v1.0-rc, раунд 14)

**Готово (host-тесты):**

| Требование docs/70 §4 | Реализация | Где |
|---|---|---|
| 8 внешних треков, канал 1–16, PC 0–127 | `ExtTrack`/`ExtSequencer` (kExtTracks=8, kExtSteps=16) | `firmware/src/io/ext_sequencer.*` |
| note/velocity/length (gate %) | `ExtStep` + note-on/off sink, gate в % шага | там же |
| p-lock CC на шаг (1 CC# на трек) | `ExtStep.ccPlocked/ccValue`, `ExtTrack.ccNumber`; CC отправляется на p-locked шагах | там же |
| mute | `setTrackMuted`, PC на старте только для unmuted | там же |
| GEN на внешних | `setGenParams()` + `genApplyStep` (prob/euclid/mutate/scale) и ARP на внешних | `io/gen.*` + ext |
| транспорт start/stop/continue | `start/stop/continuePlay`, общий с `Sequencer` (`external()`) | ext + `io/sequencer.*` |
| clock out 24 ppqn | master clock в `process()`, sink `onExtClock`, jitter-модель (≤1 мс в модели) | ext |
| clock in (slave) | `setClockSlave(true)` + `onClockIn()` (6 MIDI clock = 1/16) | ext |
| live record | `liveRecordNoteOn/Off` с квантизацией на шаг/длиной | ext |
| save/load внешних треков | versioned payload (magic `EXTP`, v1, CRC32), `serialize/deserialize` | ext |
| MIDI out DIN+USB без дублей | `MidiOutRouter` + `RouterExtSink`: каждое логическое сообщение ровно один раз в DIN и USB | ext |
| UI EXT | 6-я вкладка MAIN/SEQ/MIX/MOD/GEN/**EXT**: 8 строк `T1 CH1 PC0`, сетка 16 шагов, выбранный трек/шаг, p-lock-полоски, поля CH/PROG/VEL/LEN/CC#/CC VAL/SWING/CLK + макросы И–П | `ui/ui800.*` |

**MIDI-сообщения:** note on/off (0x90/0x80), CC (0xB0), PC (0xC0), clock (0xF8),
start (0xFA), stop (0xFC), continue (0xFB); на старте отправляются PC всех
unmuted-треков, затем start.

**Скриншот:** [`firmware/artifacts/ui/ext.png`](../firmware/artifacts/ui/ext.png)
(8 внешних треков, 16 шагов, выбранный T1/шаг 5, p-lock bars, CH/PROG/... поля).

**Тесты:** 288/288 host (25 новых в этом раунде: 16 engine/router/serialize,
5 UI EXT, 4 GEN/clock/arp; см. `tests/test_ext_sequencer.cpp`,
`tests/test_ui_ext.cpp`).

## 8. Что осталось на железе (TODO(hw))

1. **Реальный MIDI-шлюз**: DIN TRS (UART1 + 74HCT125/6N137) и USB-MIDI
   (TinyUSB composite) одновременно; сейчас `MidiOutRouter` — host/device
   модель без дублей, реальный транспорт TODO. Приём MIDI-in/clock-in/CC learn
   — на реальном UART/USB.
2. **Интеграция в .bkfp project v2**: payload `EXTP` (version+CRC32) готов и
   тестируется отдельно; запись в общий project/preset формат — отдельный шаг
   (старый project v1 не ломаем).
3. **CC learn** и 4 CC на трек — v1.1; сейчас 1 CC p-lock на трек.
4. **Hardware latency/jitter** DIN ~0.3–1 мс: измерить на CORE-2, компенсация
   задержки; USB-MIDI host на P4 — будущий режим (rev.3 option).
5. **UI p-lock жестом** «удержать шаг + энкодер» — в host-демо показана
   визуализация, обработка жеста на 42 клавишах/энкодерах — bring-up.

---

## 9. Project v2 (`.bkfp`) — единый файл проекта (раунд 23)

Ранее EXTP-пейлоад, 8 preset slots, тема и mic-настройки хранились разрозненно
(§7 TODO). Теперь они интегрированы в **BUKIFON PROJECT v2**:
`firmware/src/storage/project_v2.*`.

### Схема файла

```
magic "BKFP" (u32) | version=2 (u16) | flags (u16) | bodySize (u32)
metadata: name[64] author[64] created[24] appVersion[16]
transport/UI: bpm*10 (u16) swing*1000 (u16) faderMode[10]
              selectedPart selectedTrack currentPattern themeId themeName[16]
sections (tag u32 + size u32 + payload):
  INTP — внутренний project v1 payload (4 партии/паттерны/бар/чейн)
  GENP — 12×GenParams (4 internal + 8 external), по 12 байт
  EXTP — external sequencer payload (8 MIDI-треков: ch/PC/note/vel/len/mute/CC p-lock/16 шагов)
  MIC1 — MicConfig (source/gain/thresh/sensitivity/monitor/beatbox) + 8 pad descriptors
         (name/used/frames/peak/storage; аудио НЕ сохраняется)
  MODS — до 8 модулей: id[64]/version[16]/sha256[65] + параметры (id/value)
CRC32 (u32) по всему файлу, кроме самого CRC
```

**API:** `projectV2Save/Load`, `projectV2Serialize/Deserialize`,
`projectV2Validate`, `projectV2ToJson/FromJson`, `captureProjectV2`,
`applyProjectV2` (общий Sequencer + ExtSequencer + GEN + тема).

### Миграция v1 → v2

Старый `.bkfp` (project_io v1) читается по version=1: INTP-секция
десериализуется старым `projectDeserialize`, паттерны/BPM/чейн сохраняются,
новые секции (EXTP/mic/modules) заполняются дефолтами. Preset bank (8 слотов)
не затрагивается — тест интеграции подтверждает.

### Ошибки и транзакционность

- version/CRC/размер/неизвестная версия → отказ с понятным сообщением
  (`CRC32 mismatch`, `unsupported version`, `body size mismatch`, `file too short`);
- загрузка **транзакционна**: при любой ошибке целевой объект не меняется;
- лимиты: 8 ext-треков, 16 шагов, ≤8 модулей, ≤16 params/модуль, GEN bounds,
  BPM 20–300, swing −1…1.

### Тесты (365/365 host)

Полный roundtrip всех секций; v1-миграция; CRC/версия/короткий файл;
отсутствующие секции→дефолты; 8 external tracks; mic/pads; modules;
детерминизм сериализации; лимиты; preset bank; apply/capture; JSON; missing
file; транзакционность. См. `firmware/tests/test_project_v2.cpp`.

### TODO(hw)

Реальное хранение `.bkfp` в NVS/flash (`factory_data`) и SD, подпись/шифрование
не реализованы; хост-формат/CRC32 готов и переносим. Аудио сэмплов в проекте
нет (только описания pad-ов) — сэмплы как обычные файлы (docs/63).

---

## 10. Хранение: NVS/flash/SD, атомарность, recovery (раунд 27)

Реализовано `firmware/src/storage/storage_backend.*` (host-модели; реальные
ESP-IDF NVS/SDMMC драйверы — TODO(hw)).

### Backend API

`StorageBackend`: `begin/write/read/erase/exists/size/name`, namespace + key
(единый namespace `bukifon`). Реализации:
- **MockFlash** — RAM-флеш 256 КиБ, счётчики записи/стирания, инъекция ошибок:
  `setFailAfterWrites`, `setPowerCutAtWrite` (частичная запись), `setBitFlipAtWrite`,
  `setMaxBytes`;
- **SdFileBackend** — файлы `<root>/<ns>_<key>.bin` (host-модель; реальный SDIO/SDMMC
  TODO(hw));
- **NvsBackend** — in-memory stub с тем же интерфейсом; реальная ESP-IDF `nvs`
  партиция/`nvs_set_blob` — TODO(hw).

### Атомарная запись A/B

Запись `AtomicStorage::write(key,payload)`:
1. читаются оба слота `key.a`/`key.b` (magic `BKA1`, version, sequence, size, CRC32);
2. выбирается неактивный слот; sequence = max(valid)+1;
3. запись → **read-back verify** (CRC + побайтовое сравнение);
4. только после успеха стирается старый слот; при любой ошибке старый остаётся.

`read`: выбирает валидный слот с большей sequence; если второй слот существует, но
повреждён — возвращает данные и выставляет `lastLoadRecovered()`/`recoveryCount()`;
если оба битые — ошибка и **никакой частичной загрузки**. Лимит payload 64 КиБ.

### Интеграция

- project v2 `.bkfp`: `projectV2SaveToStore/loadFromStore` (serialize → A/B slot);
- preset bank (8 слотов, CRC32): `presetBankSaveToStore/loadFromStore`
  (`PresetBank::serialize/deserialize`);
- язык UI: `languageSaveToStore/loadFromStore` (`RU`/`EN`, после reboot модель
  восстанавливает `getLanguage()`);
- серийник/настройки — через тот же backend (namespace `bukifon`).

### Тесты

**407/407 host** (+16): read/write/erase, несколько ключей/размеры, capacity,
wear-счётчики, A/B roundtrip/sequence, power-cut в середине, bit-flip readback,
повреждение одной копии → recovery, обе битые → ошибка без partial, erase/лимиты,
project v2/preset bank/язык через MockFlash, SD backend, NVS stub, recovery после
torn erase. См. `firmware/tests/test_storage_backend.cpp`.

### TODO(hw)

Реальная **NVS-партиция** ESP-IDF (`nvs_flash_init`, namespace `bukifon`,
blob-ключи) и SD-драйвер (SDMMC 1-bit, hot-remove), wear-leveling/flash-сектора,
защита от power-loss на уровне драйвера и подпись/шифрование проекта.
