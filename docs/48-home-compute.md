# Вычисления на домашнем ПК (Tailscale)

Цель: тяжёлые задачи (рендеры Blender, STL/булевы операции, сборки PlatformIO, прогоны
тестов) выносить на домашний ПК с GPU, чтобы ноутбук не был узким местом, а работа шла
независимо.

## Статус

- Tailscale на ноутбуке: `100.116.234.8 (macbook-pro-123)`.
- В сети видны: `pole` `100.75.89.89` (online), `vds`, `apparatus` (offline), `vladimir-lenovo` (offline).
- **SSH работает**: `sym@100.75.89.89` (host `pole`), порт 22, ключ `id_ed25519` авторизован.
  Характеристики: 8 ядер, 30 ГБ RAM, RTX 3060, 417 ГБ свободно; `pio`/`cmake`/`ninja`
  поставлены в `~/.local` (python3.12 без venv), ESP-IDF ставится в `~/esp-idf`.
  Инструмент: `tools/home_offload.sh {sync|run|fetch|shell}` (rsync + ssh).

## Что будем выносить

| Задача | Как | Почему home |
|---|---|---|
| Рендеры Blender (витрина, exploded, сравнение корпусов) | `blender -b scene.blend -o //render_ -f 1` | GPU Cycles, долгие кадры |
| Тяжёлые STL/булевы операции, fitcheck больших сеток | trimesh/manifold на `pole` | CPU/RAM |
| Сборки PlatformIO (esp32-s3, rp2040) | `PLATFORMIO_CORE_DIR=~/.pio pio run` | кэш, параллельность |
| Прогоны bench/тестов | `make -C firmware/bench host` | параллельно с ноутбуком |
| CI-подобные проверки перед релизом | `bash tools/check_all.sh` | независимость от ноутбука |
| ESP-IDF сборка P4 | `~/esp-idf/install.sh esp32p4`, затем `idf.py build` | тяжёлый toolchain/2 ГБ |

## Как включить (нужно от владельца)

1. На домашнем ПК: `sudo systemctl enable --now sshd` (Linux) или
   «Системные настройки → Общий доступ → Удалённый вход» (macOS), порт 22.
2. Проверить: `tailscale status` → `pole` online; `ssh <user>@100.75.89.89 'hostname'`.
3. Сообщить имя пользователя (и порт, если не 22) — пропишу в `~/.ssh/config` алиас `bukifon-home`.
4. (Опционально) ключ: `ssh-copy-id <user>@100.75.89.89` — чтобы ходить без пароля.

## Правила

- На home выносятся только **вычисления**; исходники остаются в git (не редактировать
  на home напрямую, синхронизировать `rsync`/`git pull`).
- Результаты (PNG/STL/логи) копируются обратно в репозиторий и коммитятся как обычно.
- Пароли/токены на home не передавать; Telegram/секреты — только на ноутбуке.
