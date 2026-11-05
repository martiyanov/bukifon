# Метаданные репозитория и GitHub Pages

Сайт: **https://martiyanov.github.io/bukifon/** (RU), **/en/** (EN).
Файлы сайта: `docs/index.html`, `docs/en/index.html`, `docs/assets/`, `docs/sitemap.xml`,
`docs/robots.txt`, `docs/llms.txt`, `docs/.nojekyll`. Деплой — `.github/workflows/pages.yml`.

## 1. Включить Pages (один раз)

Settings → Pages → **Source: GitHub Actions**. Либо через API (нужен токен `gh`):

```bash
gh api -X POST repos/martiyanov/bukifon/pages -f build_type=workflow
gh api -X PUT  repos/martiyanov/bukifon/pages -f build_type=workflow
```

После первого пуша в `main` workflow `Deploy site to GitHub Pages` соберёт сайт.
Проверить: `gh run list --workflow pages.yml`.

## 2. Описание и темы репозитория (About)

Описание (RU):
> Открытая платформа настольного синтезатора и сэмплера: 42 клавиши Lapka-42, 16 энкодеров, экран 5″,
> 10 mini-jack, 2 фейдера, корпус 380×210×63 мм на 3D-принтере. Открытые схемы KiCad, прошивка C++,
> пользовательские модули.

Описание (EN):
> Open-source desktop synthesizer + sampler + module platform: 42 Lapka-42 keys, 16 encoders, 5″ display,
> 10 mini-jacks, 2 faders, 380×210×63 mm 3D-printed case. Open KiCad schematics and C++ firmware.

```bash
gh repo edit martiyanov/bukifon \
  --description "Open-source desktop synthesizer + sampler + module platform: 42 Lapka-42 keys, 16 encoders, 5\" display, 3D-printed case (380×210×63). Открытый синтезатор/сэмплер." \
  --homepage "https://martiyanov.github.io/bukifon/" \
  --add-topic synthesizer --add-topic sampler --add-topic open-source-hardware \
  --add-topic open-hardware --add-topic 3d-printing --add-topic kicad --add-topic diy-synth \
  --add-topic music-hardware --add-topic rp2040 --add-topic esp32 --add-topic esp32-p4 \
  --add-topic midi --add-topic cv --add-topic modular-synthesizer --add-topic embedded \
  --add-topic dsp --add-topic arduino --add-topic lapka42 --add-topic choc-keyboard
```

## 3. Индексация

- `docs/robots.txt` — разрешает Googlebot/Bingbot/Yandex и AI-краулеры (GPTBot, OAI-SearchBot,
  ClaudeBot, PerplexityBot), указывает sitemap.
- `docs/sitemap.xml` — RU + EN с `hreflang`.
- В обеих страницах: `<html lang>`, `meta description/keywords`, Open Graph, Twitter Card,
  JSON-LD `SoftwareApplication`, взаимные `hreflang` (`ru`, `en`, `x-default`).
- `docs/llms.txt` — карта проекта для AI-агентов (llmstxt.org).
- `CITATION.cff` — цитирование для научных индексов.
- После публикации: отправить сайт в [Google Search Console](https://search.google.com/search-console)
  и [Яндекс.Вебмастер](https://webmaster.yandex.ru/), добавить sitemap.

## 4. Проверка после мержа

```bash
curl -sI https://martiyanov.github.io/bukifon/ | head -3
curl -s  https://martiyanov.github.io/bukifon/robots.txt
curl -s  https://martiyanov.github.io/bukifon/sitemap.xml | head -5
```
