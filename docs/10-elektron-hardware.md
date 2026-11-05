# Что стоит внутри Elektron (для ориентира по архитектуре)

Собрано из публичных тирдаунов/обсуждений (Elektronauts, altstrument). Точность —
«по фото плат»: часть чипов опознана энтузиастами, не официально.

| Инструмент | Год | CPU / управление | DSP / звук | Память / носитель | Источник |
|---|---|---|---|---|---|
| **Octatrack MKI/MKII** | 2010 / 2017 | Freescale **ColdFire** | **Motorola DSP56300**-семейство (DSP56xxx) | CompactFlash, RAM; 8 аудиодорожек, 8 MIDI | [altstrument](http://altstrument.org/devices/elektron-octatrack) |
| **Digitakt** (2017) | 2017 | 2× **ColdFire MCF54415CMJ250**, 250 МГц, 64 КБ SRAM | Xilinx **Spartan XC3S50A** FPGA (мост) | Nanya DRAM, +Drive | [Elektronauts: Digitone II speculations](https://www.elektronauts.com/t/digitone-ii-speculations/213012/162) |
| **Digitone** (2017) | 2017 | 2× ColdFire MCF54415 + FPGA XC3S50A | FM — на ColdFire-софте | — | там же |
| **Syntakt** (2022) | 2022 | 2× ColdFire MCF54415 + FPGA XC3S50A | 2-й FPGA **XC3S200A** управляет аналоговыми голосами; SSI2164 (VCA) | DRAM | [Elektronauts: Syntakt PCB](https://www.elektronauts.com/t/syntakt-pcb/171667/7) |
| **Analog Rytm / Analog Four** | 2014 | ColdFire + FPGA | FPGA рулит аналоговыми схемами голосов | — | [Elektronauts: Rytm OS](https://www.elektronauts.com/t/rytm-os-1-32-speculation/40062/136) |
| **Digitakt II** (2024) | 2024 | ColdFire MCF54415 (UI/IO) | **ADI SHARC ADSP-21569** SoC | DDR3L 512 МБ, eMMC 32 ГБ, QSPI NOR | [Elektronauts: Introducing Digitakt II](https://www.elektronauts.com/t/introducing-digitakt-ii/212312/1234) |

## Выводы для нашего проекта

1. Elektron исторически разделяет **управление** (ColdFire: экран, кнопки, энкодеры,
   USB, MIDI, файлы) и **звук** (DSP или FPGA+аналог). Это не «один мощный чип»,
   а два-три специализированных.
2. DSP56300/SHARC — это ~50–100 MIPS на дорожку при старом коде; современный
   Cortex-M7 @600 МГц / ESP32-P4 @400 МГц с FPU справляются с сопоставимой нагрузкой
   на 8 голосов, но **не** с полным набором 8 стерео-дорожек + time-stretch + 2 FX
   на дорожку одновременно.
3. FPGA у Elektron нужен в основном для **аналоговых голосов** (Syntakt) и как
   быстрый мост; для чисто цифрового синтеза это не обязательно.
4. Сэмплер (Octatrack/Digitakt) требует **много RAM и потока с носителя** — именно
   поэтому у Digitakt II появились 512 МБ DDR3L и eMMC.

## Что это значит для Букифона

Наш текущий RP2040 (264 КБ SRAM, без FPU) — только прототип управления.
Для заявленных режимов нужен класс «MCU с FPU + PSRAM + display-интерфейс»:
ESP32-S3 / ESP32-P4 / STM32H7 / Teensy 4.1. Подробный разбор — `docs/11-esp32-feasibility.md`.
