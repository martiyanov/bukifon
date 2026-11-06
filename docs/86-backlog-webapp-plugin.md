# Бэклог: сайт на VDS, веб-приложение, DAW-плагин

Решение 06.11.2025: **отложить до после v1.0-rc** (сначала железо/релиз), но зафиксировать
требования и план, чтобы не потерять. Домены **bukifon.ru / bukifon.com** куплены.

## A. Сайт на VDS (как agonarena.ru)

**Статус 06.11:** сайт **задеплоен** на VDS; канон — **https://bukifon.ru/** (HTTPS),
`.com` и `www` → 301 на .ru; sslip-адрес — временный; бэкапы/авто-TLS настроены.

**Цель:** bukifon.ru/.com — витрина + веб-приложение; тот же VDS, что agonarena.ru.

| Шаг | Что |
|---|---|
| 1 | DNS: A/AAAA для `bukifon.ru`, `www.bukifon.ru`, `bukifon.com`, `www.bukifon.com`, `app.bukifon.ru` (или `/app/`) → IP VDS |
| 2 | nginx vhosts: 80 → 301 HTTPS; 443 TLS (Let's Encrypt/certbot), HSTS; gzip/brotli; кэш статики |
| 3 | Каталоги: `/var/www/bukifon/{site,app}`; `git pull`/rsync из `docs/` (сайт) и `docs/app/` (PWA) |
| 4 | systemd/rsync deploy-скрипт + бэкапы; fail2ban; UFW (22/80/443) |
| 5 | Проверка: 200 на ru/com/en, TLS A, Lighthouse ≥90, sitemap/robots/llms.txt |

**Важно:** без DNS-записей TLS не выпустить; до этого — HTTP/временный поддомен.
Секретов/паролей в репозитории не хранить (только плейсхолдеры).

## B. Веб-приложение (не демо)

**Цель:** человек без синтезатора открывает `app.bukifon.ru`, подключает MIDI-клавиатуру и
микрофон и **делает треки** в браузере.

MVP:
- **PWA**: installable, offline (service worker), полноэкранный UI 800×480-стиль, RU/EN;
- **Web MIDI in/out**: выбор устройства, каналы, live-запись в шаги (как на железе);
- **Микрофон**: запись голоса → пэд, битбокс → шаги, уровень; без отправки на сервер;
- **Секвенсор**: 4 внутренние партии + 8 EXT MIDI-треков, 16 шагов, swing, GEN (prob/euclid/
  mutate/scale/arp);
- **Проект**: save/load `.bkfp`-совместимый JSON (project v2), localStorage + файл; share-ссылка;
- **Экспорт**: WAV (performance) и stems (по партиям) через OfflineAudioContext/MediaRecorder;
- **Пресеты/темы** (4 темы), onboarding 10 минут (docs/77/en);
- **Никаких аккаунтов** в MVP; опционально — облако позже.

Технически: переиспользовать `docs/demo` (engine/UI), вынести в `docs/app/`, добавить
`manifest.webmanifest`, `sw.js`, шину MIDI/микрофона, экспорт; тесты Playwright (UX-тест RU/EN,
MIDI fake, mic fake, export smoke).

## B2. Софтовые модули и «машины»

Отдельный бэклог: `.bkm`-модули (machine/effect/generator/utility), загрузка по USB/SD/Wi-Fi,
менеджер модулей, подпись/sandbox — см. [docs/91](91-software-modules.md).

## C. DAW-плагин

**Цель:** тот же движок как инструмент в DAW.

| Вариант | Плюсы | Минусы |
|---|---|---|
| **CLAP** (free-audio/clap) | открытый, лёгкий C API, Bitwig/Reaper/Studio One | не все DAW (Cubase/Logic — нет) |
| **VST3** (Steinberg SDK) | максимум DAW (Ableton/Cubase/FL/Reaper) | SDK/лицензия, сложнее UI |
| **AUv2/AUv3** | Logic/GarageBand | только macOS, Apple SDK |
| **JUCE 8** | один код → VST3/AU/CLAP/Standalone, GUI | зависимость, размер, лицензия (AGPL/коммерч.) |

**Рекомендация:** JUCE 8 (GPLv3-совместимо для open-source) → **VST3 + AU + Standalone**,
далее CLAP. Движок — общий C++ (`firmware/src/audio`, bench-модель), параметры — те же 16+макросы,
пресеты — project v2. Плагин-инструмент (MIDI in, 8 голосов, 4 партии), позже — эффект-версия
(микрофон/вокодер). Сборка: macOS universal + Windows; тесты — pluginval, рендер-тесты.

**Этапы:** M1 сайт/VDS → M2 PWA → M3 веб-приложение (mic/MIDI/tracks/export) → M4 CLAP (лёгкий)
→ M5 VST3/AU через JUCE → M6 облако/аккаунты (опция).

## D. Оценка

| Этап | Объём | Когда |
|---|---|---|
| VDS + домены + TLS | 0.5–1 день | после RC |
| PWA-оболочка | 2–3 дня | после RC |
| Веб-приложение MVP | 1–2 недели | после RC |
| CLAP-плагин | 1–2 недели | после RC/пилота |
| VST3/AU (JUCE) | 2–4 недели | после пилота |

## E. Риски

- Web MIDI не в Safari (macOS/iOS) — нужен Chrome/Edge; microfon — только HTTPS (VDS даёт).
- Аудио-latency браузера 10–30 мс — для идей ок, не для live-сцены.
- Плагин: ABI/лицензии/подпись (macOS notarization, Windows signing).
- Не распылять силы до v1.0-rc — **этот документ = бэклог, не работа сейчас**.
