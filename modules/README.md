# Каталог модулей Букифона

Здесь живут модули сообщества и эталонные примеры. Формат — `module.json` (schema v1),
описание — [docs/24-module-sdk.md](../docs/24-module-sdk.md).

```
modules/
  template/              # каркас: скопируй и переименуй
  examples/gain_fx/      # audio-rate C++ (диодный драйв)
  examples/lfo_module/   # control-rate Lua (LFO)
  community/<vendor>/<name>/   # сторонние модули (PR + CI)
```

Правила:
- обязательные файлы: `module.json`, `README.md`, `LICENSE`, исходники из `files`;
- `id` уникален (`vendor.name`), версия по SemVer, `abi: 0` до стабилизации;
- в `process()` нельзя: malloc/locks/FS/logging/UI/неопределённые циклы;
- лицензия по умолчанию GPL-3.0-or-later;
- проверка: `python3 tools/validate_module.py modules/...`.

Добавление своего модуля: `bash tools/new_module.sh <handle> <name> <audio|control>` → PR.
