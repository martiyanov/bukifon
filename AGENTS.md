# Правила ведения Букифона (для агентов и людей)

## 1. Версионирование — SemVer + тег на каждый релиз

Формат: `MAJOR.MINOR.PATCH`, текущая версия — в файле [`VERSION`](VERSION).

- **MAJOR** — несовместимая смена архитектуры/габарита/интерфейсов (например, смена MCU-платформы
  и разъёмов панели).
- **MINOR** — новые возможности/ревизии, обратно совместимые (новая раскладка, новый блок
  документации, новый модуль).
- **PATCH** — исправления без смены геометрии/интерфейсов (опечатки, ошибки в PDF, правки текста).

Порядок выпуска:

1. Обновить `VERSION` и `CHANGELOG.md` (секция `## [x.y.z] — YYYY-MM-DD`).
2. **Обновить `README.md`**: актуальное состояние, ссылки на новые документы/артефакты.
3. Коммит: `release: vX.Y.Z — короткое описание`.
4. Аннотированный тег: `git tag -a vX.Y.Z -m "Букифон vX.Y.Z: ..."`.
5. Пуш ветки и тега: `git push origin <branch> && git push origin vX.Y.Z`.

Теги (ретроспективно): `v0.1.0` — базовый прототип (315×145), `v0.2.0` — печатные листы
Digitone/Octatrack и проработка 340×185, `v0.3.0` — раскладка 380×210 по концепту,
`v0.4.0` — каноническая панель v0.4 (точная Lapka-42 ±18°), корпус v0.4, реестр требований,
консультации по MCU и дорожная карта.

## 2. README — всегда актуален

README не «исторический документ»: при любом изменении, которое видит пользователь
(новая ревизия панели/корпуса, смена платформы, новые документы, изменение BOM),
README обновляется в том же коммите. Устаревшие числа в README — ошибка уровня бага.

## 3. Единственный источник геометрии

- Панель: `spec/panel-spec-v0.4.json` (или более новая версия в `spec/`).
- Корпус: `mechanical/generator/params_v04.py` + `spec/panel-spec-v0.4.json`.
- Требования: `spec/90-requirements-registry.md` (R-xx, журнал D-xx).
- Устаревшие спеки (`spec/20`, `spec/40`, старый README) правятся по реестру, а не
  «как получится».

## 4. Проверки перед коммитом

```bash
# панель: 1:1 шаблон + рендер + пересечения (должно быть 0)
MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python tools/panel_from_json.py spec/panel-spec-v0.4.json bukifon_v04
# корпус: STL + fitcheck (пересечения 0)
MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python mechanical/generator/case_v04.py
MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python mechanical/generator/fitcheck_v04.py
# прошивка: host-тесты
cd firmware/host && make test        # или: make -C firmware/host
```

## 5. Документы, которые нельзя удалять

`docs/00-context-transfer.md` (контекст для внешних агентов), `docs/03-second-opinion-mcu.md`,
`docs/04-consultation-gpt.md`, `docs/12-roadmap.md`, `spec/90-requirements-registry.md`,
`PULL_REQUEST.md`. При переименовании — обновить ссылки в README.
