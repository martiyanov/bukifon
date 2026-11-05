# Запрос на purge старых объектов GitHub (PII)

## Что было

Публичный репозиторий `martiyanov/bukifon` до 06.11.2025 содержал в истории:

- фото макета с **GPS EXIF** (координаты съёмки) — `refs/sketch4-panel.jpg`, `refs/sketch4-small.jpg`;
- HEIC/JPEG-копии — `refs/attach/IMG_0704.heic`, `refs/attach/IMG_0704_small.jpg`;
- PDF, скачанные с Mouser/Farnell/Octopart, с **IP-адресом клиента и трекинг-токенами**
  (`refs/datasheets/*`).

## Что сделано

1. История переписана `git filter-repo` (удалены пути, заменены `/Users/<имя>/...` на `~`).
2. Все ветки и теги force-push; текущее дерево чистое; `tools/security_scan.sh` — ok.
3. Проверка: `curl raw.githubusercontent.com/martiyanov/bukifon/<branch>/refs/sketch4-panel.jpg` → 404.

## Остаточный риск

GitHub продолжает отдавать **старые объекты по SHA** (dangling objects), пока не выполнен GC
или purge. Проверено 06.11.2025: старые коммиты и blobs ниже ещё доступны по прямым ссылкам.

### Старые коммиты (содержат PII-файлы)

| SHA | Коммит |
|---|---|
| `3fd9f1f99d0d9958b1f07d12b33b0c1a5ce4ca3b` | v1.8: панель+корпус по handoff заказчика v0.3 |
| `5eb1a110c726540165ab0c686b431d38dbc19c9f` | context: фото макета IMG_0704 (HEIC) + анализ габарита |
| `acbe5edd83557b25aa0060bfdcb9e057ebe90cb9` | v1.4: панель 340×185 по фото |

### Blobs (PII)

| Blob SHA | Файл |
|---|---|
| `7d610e75a246180d652005f399098805c7c50600` | refs/attach/IMG_0704.heic |
| `6b9e27e16025f28c9509c611e8e1082f8722a1d7` | refs/attach/IMG_0704_small.jpg |
| `9726f37fe157e593753f44dbdffefaf4897d8f5a` | refs/sketch4-panel.jpg |
| `20d0e3a4b3555a7b784ee0bf4d1b7efecb275244` | refs/datasheets/ec11_mouser.pdf |
| `e131b26187da311940b41b34dce131a2e437a8ec` | refs/datasheets/pj307_cad.pdf |
| `cc2849d17c624f93c9ecbf7f69a17ad07d243f17` | refs/datasheets/ec11_farnell.pdf |
| `97e3a60beec6c30c4ad956ac885f8e801c76851d` | refs/datasheets/rs60n11m9_mouser.pdf |

(полный список datasheet-blob'ов — в `refs/` старой истории; все они содержат аналитику
клиента, а не только datasheet).

## Варианты решения

| Вариант | Плюсы | Минусы |
|---|---|---|
| **Удалить и пересоздать репозиторий** (рекомендуется) | гарантированный purge, 10 минут | теряются звёзды/форки/история issues (сейчас ~нет), нужно заново включить Pages |
| **GitHub Support: purge sensitive data** | история/звёзды сохраняются | 1–3 рабочих дня |
| Временно сделать private | мгновенно закрывает доступ | проект перестаёт индексироваться (цель — «народный»), потом всё равно нужен purge |

## Готовый текст в GitHub Support (English)

```
Subject: Request to purge cached sensitive objects (GPS EXIF) from a public repository

Repo: martiyanov/bukifon
Reason: personal data (GPS EXIF in photos) and vendor PDFs containing client IP addresses
were committed before 2025-11-06. I have rewritten the history and force-pushed all branches
and tags; the current tree is clean. Please purge the following unreachable objects:

Commits:
3fd9f1f99d0d9958b1f07d12b33b0c1a5ce4ca3b
5eb1a110c726540165ab0c686b431d38dbc19c9f
acbe5edd83557b25aa0060bfdcb9e057ebe90cb9

Blobs:
7d610e75a246180d652005f399098805c7c50600
6b9e27e16025f28c9509c611e8e1082f8722a1d7
9726f37fe157e593753f44dbdffefaf4897d8f5a
20d0e3a4b3555a7b784ee0bf4d1b7efecb275244
e131b26187da311940b41b34dce131a2e437a8ec
cc2849d17c624f93c9ecbf7f69a17ad07d243f17
97e3a60beec6c30c4ad956ac885f8e801c76851d

They are still reachable via raw.githubusercontent.com/<sha>/<path>.
```

## Проверка после purge

```bash
for sha in 3fd9f1f 5eb1a11 acbe5ed; do
  curl -s -o /dev/null -w "$sha: %{http_code}\n" \
    https://raw.githubusercontent.com/martiyanov/bukifon/$sha/refs/sketch4-panel.jpg
done
# ожидаем 404
```
