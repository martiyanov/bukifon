# SDK модулей Букифона — Module API v0.1 (experimental)

Статус: **v0.1 experimental**. Стабильный ABI (v1) фиксируется только после P1-бенчмарка
и выбора MCU. ABI major остаётся 0: модули, собранные под v0, продолжают работать без
изменений (новые поля таблицы опциональны, `NULL` = не поддерживается).

## Что нового в v0.1 (vs v0)

| Возможность | v0 | v0.1 |
|---|---|---|
| Таблица ABI | 10 функций | **12 функций** (+`attach_host`, `on_event`) |
| Host services | — | `attach_host(instance, services)`: `now_us()` (монотонное время) и `log()`; лог **запрещён** из `process()` — host считает такие вызовы нарушением RT и отбрасывает сообщение |
| События | только параметры | `on_event()`: NOTE_ON/OFF, GATE_ON/OFF, TRANSPORT START/STOP/CONTINUE, TEMPO, PATTERN, PITCH_BEND (с `channel`, `id`, `value`, `frame_offset`) |
| Сглаживание параметров | на модуле | host-side `setParamSmoothed(id, value, timeMs)`: линейно-экспоненциальный ramp на границах ABI-блоков (≤64 фрейма), модуль получает уже сглаженные значения через `set_param` |
| Примеры | 2 C++ (gain, LFO) | **4 C++**: gain_fx, lfo_mod, **grain_fx** (granular-эффект, события/сглаживание), **svf_filter** (state-variable filter, keytrack по NOTE_ON) |
| Тесты | lifecycle/budget | + host services, события, лог-нарушения, smoothing, state roundtrip, совместимость v0 |
| `module.json` | `"abi": 0` | `"abi": 0, "abi_minor": 1` (опционально) |

Ограничения не изменились: стек ≤8 КБ, состояние ≤4 КБ, блок ≤64 фрейма, WCET-бюджет
800 µs на 64-фреймовый вызов @48 кГц, bypass после 2 превышений; в `process()` запрещены
malloc/lock/FS/сеть/UI/логирование. v0.1 — по-прежнему design probe, не публичный SDK.

## Что такое модуль

**Модуль** — единица расширения звука/управления:
- **audio-rate** (C++): генератор, эффект, фильтр — работает внутри аудио-колбэка;
- **control-rate** (Lua): модуляторы, секвенсорные логики, UI-макросы — без доступа к аудио;
- **аналоговый картридж** (шина 26-pin): VCO/фильтр/PT2399 — спецификация в
  `hardware/modules/CARTRIDGE.md`;
- **дека ввода** (18 пэдов / 42 клавиши) — определяется EEPROM (24C32).

## ABI v0 (C++)

Заголовок: [`firmware/include/bukifon_module.h`](../firmware/include/bukifon_module.h).

| Функция | Назначение |
|---|---|
| `descriptor()` | `abi_version`, `struct_size`, UUID, name, vendor, kind, flags |
| `create(host, config)` | создание экземпляра (аллокации разрешены здесь) |
| `prepare(sample_rate, max_block)` | подготовка: таблицы, сглаживания; `max_block ≤ 64` |
| `reset()` | сброс состояния (без аллокаций) |
| `process(ctx, inputs, outputs, frames)` | аудио-колбэк; `frames ≤ 64` |
| `set_param(id, value)` | параметр по индексу (значение нормализовано 0…1) |
| `state_size()` | размер состояния для сохранения |
| `save_state(buf) / load_state(buf, version)` | сериализация состояния (без FS) |
| `destroy()` | освобождение |
| `attach_host(instance, services)` *(v0.1)* | получить `now_us`/`log`; вызывается после `create()` и до `prepare()` |
| `on_event(instance, event)` *(v0.1)* | note/gate/transport/tempo/pattern события; можно хранить состояние, но не блокироваться |

### Параметры

Параметр: `id`, тип (`float/int/bool/enum`), `min`, `max`, `default`, `unit`,
`smoothing` (`none/linear/exponential`), `name` (для UI). Минимум 1 параметр.

### События (v0.1)

`on_event()` получает `bukifon_event_t`: тип, канал, id (нота/CC/паттерн), значение
(velocity, BPM, bend) и `frame_offset` внутри следующего блока. Модуль не читает
секвенсор напрямую и не владеет транспортом; host/секвенсор — единственный источник.

### Host services (v0.1)

`bukifon_host_services_t { context, now_us(context), log(context, level, message) }`.
`now_us()` можно вызывать и из `process()` (это чтение счётчика, без I/O). `log()` —
только вне аудио-пути; host-обёртка в режиме `process()` инкрементирует
`logViolations()` и **не печатает** сообщение (никакого I/O из аудио-потока).
Хост-обёртка хранит таблицу services в своём объекте — модуль может держать указатель
всё время жизни экземпляра.

## Ограничения real-time (обязательны)

- в `process()` **запрещены**: `malloc/new`, блокировки, файловый ввод-вывод, сеть,
  логирование, вызовы UI, неопределённые циклы;
- стек ≤ **8 КБ**, состояние ≤ **4 КБ**, блок ≤ **64** фреймов;
- **WCET-бюджет**: host измеряет worst-case; 2 превышения подряд → модуль в **bypass**
  + fault flag (аудио продолжается);
- никаких глобальных конструкторов с побочными эффектами; всё в `create`.

## Упаковка модуля

```
modules/<vendor>/<name>/
  module.json      # метаданные (см. ниже)
  src/             # C++/Lua исходники
  README.md        # описание, управление, лицензия
  docs/            # опционально: схема, фото
  LICENSE          # GPL-3.0-or-later (по умолчанию) или совместимая
```

`module.json` (schema v1):

```json
{
  "schema": "bukifon.module.v1",
  "id": "vendor.name",
  "name": "Gain FX",
  "version": "0.1.0",
  "abi": 0,
  "kind": "audio",
  "language": "cpp",
  "license": "GPL-3.0-or-later",
  "author": "your-handle",
  "description": "Простой диодный драйв с tone-контролем",
  "params": [
    {"id": 0, "name": "Drive", "type": "float", "min": 0, "max": 1, "default": 0.5},
    {"id": 1, "name": "Tone",  "type": "float", "min": 0, "max": 1, "default": 0.5}
  ],
  "files": ["src/gain_fx.cpp", "README.md", "LICENSE"],
  "limits": {"stack_bytes": 8192, "state_bytes": 4096, "max_frames": 64}
}
```

## Каталог модулей

- `modules/examples/` — 4 C++ примера (gain_fx, lfo_mod, grain_fx, svf_filter) + Lua-заглушка:
  обязаны собираться и проходить `tools/validate_module.py`;
- `modules/community/` — сторонние модули (PR-ом, с CI-проверкой);
- каталог на сайте/в приложении строится из `module.json` (без запуска кода).

## Валидация

```bash
python3 tools/validate_module.py modules/examples/gain_fx
# проверяет: schema, обязательные поля, версии, лицензию, наличие файлов,
# реальные размеры state/stack, запрет malloc/new в process (эвристика),
# размер кода, дубликаты id в каталоге
```

CI: `.github/workflows/modules.yml` (добавить при первом community-модуле) — валидация
всех `modules/**/module.json` + host-сборка примеров.

## Как написать свой модуль за вечер

```bash
bash tools/new_module.sh my-handle my-fx audio   # создаёт каркас
# реализуй process() и параметры, собери host-тест:
make -C firmware/host test && python3 tools/validate_module.py modules/my-handle/my-fx
```

## Безопасность и доверие

- audio-rate модули в v0 — **статически слинкованный проверенный C++** (доверие автору/ревью);
- Lua — только control-rate, с лимитом инструкций/памяти/времени;
- недоверенный audio-rate код — в **RP2350-картридже** (своя память, watchdog, TDM/I²S);
- несовместимый ABI/CRC — модуль не загружается; safe mode отключает сторонние модули.

## Лицензии

- модули по умолчанию **GPL-3.0-or-later** (совместимо с прошивкой);
- примеры допускаются MIT/Apache-2.0;
- аналоговые картриджи — CERN-OHL-S-2.0, если повторяют открытую схему.

---

## SDK v0.2 — манифест, loader, примеры (раунд 20)

**Статус:** host-реализовано и покрыто тестами (351/351); реальные
динамические библиотеки/песочница на P4 — TODO(hw). ABI-таблица остаётся
`bukifon_module.h` v0.1 (major 0), SDK v0.2 добавляет **манифест/упаковку/loader**.

### Манифест `bukifon.module.v2`

```json
{
  "schema": "bukifon.module.v2",
  "id": "bukifon.mod_tape_delay",
  "name": "Tape Delay",
  "version": "0.2.0",
  "api": "0.2.0",
  "author": "Bukifon",
  "abi": "any",
  "permissions": ["audio", "params"],
  "params": [{"id":0,"name":"TIME","type":"float","min":20,"max":1000,"default":250,"unit":"ms"}],
  "dsp": "model.hpp",
  "size": 1929,
  "sha256": "772397c32b6e8e7b346a17b5bf4823a45ec6ad583a635b38e58340773c8db220",
  "license": "GPL-3.0-or-later",
  "description": "Tape-style feedback delay"
}
```

Правила: `id` `[a-z0-9._-]{3,63}`; `version`/`api` — SemVer; `abi` ∈
`host|p4|s3|any`; `permissions` — непустое подмножество `audio/params/seq/io`;
`params` 1–16, уникальные id, `min < max`, `default ∈ [min,max]`; `dsp` — entry
файл; `size` 1 B…64 MiB; `sha256` — 64 hex (SHA-256 payload).

### Loader (host)

`firmware/src/modules/module_manifest.*` — парсер + валидатор с понятными
ошибками; `module_loader.*` — `ModuleLoader::load(manifestJson,payload,...)` /
`loadFiles(...)`:
- API-совместимость: **major совпадает** (`0`), minor модуля ≤ host minor
  (`0.2`); несовместимый — отказ;
- ABI target, размер и SHA-256 payload (`moduleSha256`, стандартный вектор
  `abc` проверен);
- **до исполнения**: при любой ошибке модуль НЕ устанавливается, ничего не
  исполняется (`executedAnything() == false`), внятный `lastError()`;
- список установленных: id/version/sha256/size/permissions, `find()/at()/count()`,
  счётчики attempts/rejected (макс. 16 модулей).

### Примеры

- `firmware/modules/examples/mod_tape_delay/` — эффект (tape delay); манифест +
  `model.hpp` + README/LICENSE; impulse → эхо через delay, детерминизм.
- `firmware/modules/examples/mod_euclid_arp/` — генеративный/control (Euclidean
  16-step arp + seed→velocity); детерминированные шаги/ноты, 5/16.
- Упаковка: `firmware/tools/package_module.py <path> --check` (проверка
  манифеста/size/sha), без `--check` — zip (`manifest.json + dsp + README +
  LICENSE + module.package.json` с SHA-256 файлов).

### Ограничения / TODO(hw)

- Динамическая загрузка ABI-библиотек на P4, изоляция памяти, watchdog и
  проверка подписи (Ed25519) — не реализованы; сейчас loader — статическая
  валидация/установка в модель, аудио-модули собираются в прошивку.
- ABI major остаётся 0 (экспериментальный); публичный SDK v1 — после P1.
- Песочница audio-rate кода (MCU MPU/отдельный RP2350-картридж) — backlog.
