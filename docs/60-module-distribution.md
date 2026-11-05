# Распространение модулей (SDK)

Модуль Букифона — папка с `module.json` (схема `bukifon.module.v1`), исходниками,
`README.md` и лицензией. Упаковка:

```bash
python3 tools/package_module.py modules/examples/gain_fx --version 0.1.0
# OK: dist/modules/bukifon.gain_fx-0.1.0.zip
```

## Что проверяет упаковщик

| Проверка | Обязательно |
|---|---|
| schema = `bukifon.module.v1`, поля `id/name/version/abi/author/description` | да |
| semver `X.Y.Z` | да |
| `files[]` указывает на существующие файлы | предупреждение |
| SPDX-заголовок в `.c/.cpp/.h/.hpp/.lua` | предупреждение |
| наличие `LICENSE` (GPL-3.0-or-later для аудио-модулей) | предупреждение для шаблона |
| `module.manifest.json` с SHA256 всех файлов | создаётся автоматически |

## Формат пакета

```
bukifon.gain_fx-0.1.0.zip
├─ module.json            # схема модуля (abi, params, limits)
├─ module.manifest.json   # schema, id, version, abi, files[{path,sha256,size}]
├─ README.md
├─ LICENSE
└─ src/…
```

`module.manifest.json` — для воспроизводимости: по SHA256 можно проверить, что модуль
собран из тех же исходников. Версия модуля независима от версии прошивки; совместимость
определяется **abi** (`0` — Module API v0, экспериментальный).

## Правила публикации

1. `bash tools/validate_module.py modules/...` — статическая проверка API.
2. `python3 tools/package_module.py … --version X.Y.Z` — пакет + манифест.
3. Приложить к релизу GitHub (`dist/modules/*.zip`) и запись в каталоге `modules/README.md`.
4. Обновить CHANGELOG модуля; API v0 не гарантирует бинарную совместимость между мажорами прошивки.
5. Лицензия: аудио-модули — GPL-3.0-or-later (как проект), иначе явно указать в `module.json`.

## Ограничения (из Module API v0)

- `process()` ≤ 64 фреймов, стек ≤ 8 КБ, state ≤ 4 КБ;
- бюджет 800 µs на блок; 2 переполнения → bypass;
- нет аллокаций в audio-пути, нет блокирующих вызовов, `log` только из host-контекста;
- Module API v1 появится после электрического freeze (docs/24).

## CI

`.github/workflows/modules.yml` валидирует и компилирует примеры при каждом PR.
Добавить новый модуль = папка в `modules/<vendor>/<name>/` + `module.json`.
