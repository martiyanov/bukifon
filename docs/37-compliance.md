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
| **$299 P4 Standard (первый SKU)** | P4+C6, 32 МБ PSRAM, HS USB (UAC2 8×8), RGB565/DSI, все органы управления, корпус B-light, шлейфы | **стартовый Complete-комплект** (D-58/D-59); батарея/БП/SD/картриджи — опции |
| **$399 Full Bundle** | P4 Standard + проверенные картриджи/дека | bundle после пилота |
| S3 lite (позже) | CORE-S3, SPI-экран, 8 моно/6 голосов | «lite later» (D-58), не в первой партии |

Для $299 landed COGS должен быть ≤$190–200 (комиссии, упаковка, брак, замены, поддержка).
$199-beta не запускается (D-59).

## 8. Как говорить об ограничениях S3

| Неудачно | Правильно |
|---|---|
| «Медленный экран» | «Интерфейс оптимизирован под музыкальные параметры: 10–20 fps и мгновенный отклик органов» |
| «Всего 6 голосов» | «8 mono-движков или до 6 полифонических голосов с эффектами; гарантированный профиль нагрузки» |
| «Урезанный USB» | «USB FS: stereo audio + MIDI + HID; многоканальный USB — в P4 Standard» |
| «Дешёвая версия» | «S3-base: автономный DIY-инструмент; P4 — performance/expansion tier» |
