# SDK модулей Букифона — Module API v0 (experimental)

Статус: **v0 experimental**. Стабильный ABI (v1) фиксируется только после P1-бенчмарка
и выбора MCU. API спроектирован так, чтобы переход на v1 был совместим по форме.

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

### Параметры

Параметр: `id`, тип (`float/int/bool/enum`), `min`, `max`, `default`, `unit`,
`smoothing` (`none/linear/exponential`), `name` (для UI). Минимум 1 параметр.

### События

События передаются с sample-offset внутри блока: note on/off, gate, transport,
смена паттерна, параметр-лок. Модуль не читает секвенсор напрямую.

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

- `modules/examples/` — 3 эталонных примера (2 C++, 1 Lua): обязаны собираться и проходить
  `tools/validate_module.py`;
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
