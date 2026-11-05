# Пересоздание GitHub-репозитория (purge PII) — по решению заказчика (D-61)

Цель: гарантированно убрать старые объекты с GPS-фото и PDF с IP из публичного репозитория.
Force-push историю уже переписал, но GitHub продолжает отдавать старые объекты по SHA
(см. [docs/30](30-security-purge.md)). Пересоздание — самый надёжный путь.

**Внимание:** удалить репозиторий может только владелец (нужен вход в GitHub). Я (агент)
не могу этого сделать без токена — дальше пошагово, 10 минут.

## 1. Сохранить чистую историю (уже сделано)

```bash
cd /Users/a123/Проекты/Синтезатор
git bundle create dist/bukifon-clean-$(date +%Y%m%d).bundle --all
tar -czf dist/bukifon-clean-$(date +%Y%m%d).tar.gz --exclude=.git --exclude=firmware/host/build* --exclude=firmware/bench/build* .
```

Проверка чистоты (обе команды должны быть пустыми):

```bash
git log --all --oneline -- refs/attach refs/datasheets refs/sketch4-panel.jpg
git grep -nE "/Users/[A-Za-z0-9._-]+/|AAG0t|8604502531" -- . | head
```

## 2. Удалить репозиторий на GitHub

1. Открыть https://github.com/martiyanov/bukifon → **Settings** → внизу **Danger Zone**.
2. **Delete this repository** → ввести имя `martiyanov/bukifon` → подтвердить.
3. Старые объекты удаляются вместе с репозиторием; кэш CDN может отдавать файлы 5–30 минут.

## 3. Создать заново

1. https://github.com/new → имя `bukifon` → Public (для индексации) → **Create repository**.
2. Ничего не инициализировать (без README/.gitignore).
3. Добавить remote и запушить чистую историю:

```bash
cd /Users/a123/Проекты/Синтезатор
git remote set-url origin git@github.com:martiyanov/bukifon.git   # SSH
# или: git remote set-url origin https://github.com/martiyanov/bukifon.git
git push -u origin main
git push origin feature/panel-v04-canonical night/v0.5-integration
git push origin --tags
```

Если репозиторий создан с README — `git push --force origin main` перезапишет.

## 4. Включить GitHub Pages и метаданные

```bash
# Pages (source ветка gh-pages)
GIT_SSH_COMMAND="ssh -o BatchMode=yes" git push --force origin gh-pages

# Описание/темы/домашняя страница (нужен gh auth login):
gh api -X POST repos/martiyanov/bukifon/pages -f build_type=legacy -f source[branch]=gh-pages -f source[path]=/
gh repo edit martiyanov/bukifon --description "Open-source DIY synthesizer/sampler: 42 Lapka-42 keys, 16 encoders, 5\" 800×480, 3D-printed case, open KiCad/C++" --homepage "https://martiyanov.github.io/bukifon/" --add-topic synthesizer --add-topic sampler --add-topic open-source-hardware --add-topic 3d-printing --add-topic kicad --add-topic esp32 --add-topic diy-synth
```

## 5. Проверка

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://github.com/martiyanov/bukifon
curl -s -o /dev/null -w "%{http_code}\n" https://martiyanov.github.io/bukifon/
for sha in 3fd9f1f 5eb1a11 acbe5ed; do
  curl -s -o /dev/null -w "$sha: %{http_code}\n" https://raw.githubusercontent.com/martiyanov/bukifon/$sha/refs/sketch4-panel.jpg
done   # ожидаем 404 для всех
```

## 6. После пересоздания

- [ ] Pages отдаёт 200 (RU/EN), sitemap/robots/llms.txt на месте;
- [ ] старые SHA с PII → 404;
- [ ] ветки/теги на месте (`git ls-remote --heads --tags origin`);
- [ ] repo About/темы/описание заполнены;
- [ ] issue template и SECURITY.md на месте;
- [ ] отправить sitemap в Google Search Console и Яндекс.Вебмастер;
- [ ] сообщить в Telegram, что репо пересоздано.

Если удалять не хочется — альтернатива: приватный репозиторий + GitHub Support purge
(текст готов в [docs/30](30-security-purge.md)).
