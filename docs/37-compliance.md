# Соответствие и безопасность продукта (риски до продаж)

Не юридическое заключение. Перед продажами нужен короткий compliance-review по странам
доставки (особенно ЕС). Основание — консультация GPT.

## 1. Радио и CE/RED (ЕС)

Wi-Fi/BLE делает изделие **radio equipment**: требуется conformity assessment и
**EU Declaration of Conformity** (RED). CE — ответственность производителя, «купить
сертификат» нельзя. Дополнительно **GPSR** требует анализа рисков и технической
документации. Kit не даёт автоматического освобождения.
Источники: [RED](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX%3A02014L0053-20241228),
[GPSR](https://eur-lex.europa.eu/eli/reg/2023/988/oj/eng), [CE marking](https://europa.eu/youreurope/business/product-rules-compliance/general-product-compliance/ce-marking/).

## 2. Батарея

- В **первой партии батарею не продавать**: внешний квалифицированный адаптер 5 В/2 А.
- Позже — только готовый **traceable pack с PCM/NTC** (не россыпь 18650), thermal/fault
  tests, транспортные документы поставщика.
- EU Battery Regulation распространяется и на встроенные батареи.
  Источник: [EU Battery Regulation](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32023R1542).

## 3. EMC/ESD и аудиошум

Pre-compliance до продаж: conducted/radiated emissions, immunity/ESD, Wi-Fi TX + LCD +
audio worst case, USB, PSU. Модуль/антенну и корпус заморозить до испытаний.

## 4. Лицензии и SBOM

- License manifest/SBOM для прошивки и модулей; автоматическая проверка совместимости;
- обязательный SPDX-заголовок для модулей сообщества;
- запрет неизвестных/несовместимых бинарных blob'ов;
- Module API v0 явно нестабилен (не обещать совместимость).
  Состояние лицензий проекта: [docs/09-licensing.md](09-licensing.md).

## 5. Поддержка и гарантия

- supported host OS, update/recovery, срок поддержки, DOA/RMA, spare parts;
- issue template, safety guide, граница ответственности DIY-сборщика;
- traceability: ревизия PCB, версия firmware, номер партии на каждом экземпляре.

## 6. Что делать сейчас (до продаж)

1. Выбрать рынки запуска (РФ / ЕС / США) — от этого зависит объём compliance.
2. Для ЕС: hazard analysis, technical file, маркировка, DoC (после pre-compliance).
3. Убрать батарею из первой партии (D-39 уже это предполагает).
4. Собрать SBOM и проверить лицензии модулей.
5. Написать safety/known-limitations для покупателя.

## 7. SKU и честная экономика

| SKU | Что | Позиционирование |
|---|---|---|
| **$199 S3 Maker Beta** | платы/PCBA, прошитый S3, дисплей, кодеки, шлейфы, крепёж, базовые печатные детали; без батареи/БП/SD/кабеля/картриджей | **founders batch 10–25, at-cost beta** (COGS $170–185 — не бизнес при $199) |
| **$249–269 S3 Complete** | все органы управления, корпус, клавиши, экран, платы, кабели | честная цена полного S3-base, если COGS не опустится |
| **$299 P4 Standard** | P4+C6, HS USB, RGB/DSI, больше голосов | performance SKU после P1 |
| **$399 Full Bundle** | P4 + проверенные картриджи/дека | bundle, не «всё сразу» |

При $199 устойчивый landed COGS должен быть **≤$125–135**: остальное съедят комиссии,
упаковка, брак, замены, поддержка.

## 8. Как говорить об ограничениях S3

| Неудачно | Правильно |
|---|---|
| «Медленный экран» | «Интерфейс оптимизирован под музыкальные параметры: 10–20 fps и мгновенный отклик органов» |
| «Всего 6 голосов» | «8 mono-движков или до 6 полифонических голосов с эффектами; гарантированный профиль нагрузки» |
| «Урезанный USB» | «USB FS: stereo audio + MIDI + HID; многоканальный USB — в P4 Standard» |
| «Дешёвая версия» | «S3-base: автономный DIY-инструмент; P4 — performance/expansion tier» |
