# -*- coding: utf-8 -*-
"""CORE-S3 board data: GPIO budget, connectors, rails, comparison (PRE-FREEZE)."""

# GPIO budget: ESP32-S3-WROOM-1-N16R8. Usable module GPIO = 31
# (GPIO0-18, 21, 38-48; GPIO19/20 = USB, GPIO26-32 flash, GPIO33-37 octal PSRAM).
PINMAP = [
 ('LCD_SCK', 12, 'SPI2 FSPICLK (IOMUX)', 'out', 'SPI display prototytpe variant'),
 ('LCD_MOSI', 11, 'SPI2 FSPID (IOMUX)', 'out', ''),
 ('LCD_CS', 10, 'SPI2 FSPICS0', 'out', ''),
 ('LCD_DC', 9, 'GPIO', 'out', ''),
 ('LCD_RST', 8, 'GPIO', 'out', ''),
 ('BL_PWM', 21, 'LEDC PWM', 'out', 'backlight PWM -> BL boost'),
 ('SPI3_SCK', 4, 'SPI3 SCK (matrix)', 'out', 'MCP3208, 10 MHz'),
 ('SPI3_MOSI', 5, 'SPI3 MOSI', 'out', ''),
 ('SPI3_MISO', 6, 'SPI3 MISO', 'in', 'MCP3208 DOUT'),
 ('MCP3208_CS', 7, 'SPI3 CS0', 'out', ''),
 ('SD_CLK', 15, 'SDMMC CLK', 'out', 'microSD 1-bit SDMMC'),
 ('SD_CMD', 14, 'SDMMC CMD', 'bidir', ''),
 ('SD_D0', 13, 'SDMMC D0', 'bidir', ''),
 ('I2C0_SDA', 16, 'I2C0 SDA', 'bidir', 'MCP4728 x2, 24C32, PANEL-2'),
 ('I2C0_SCL', 17, 'I2C0 SCL', 'out', '400 kHz'),
 ('I2S_MCLK', 18, 'I2S0 MCLK', 'out', '12.288 MHz = 256 fs'),
 ('I2S_BCK', 1, 'I2S0 BCK', 'out', '3.072 MHz'),
 ('I2S_LRCK', 2, 'I2S0 WS', 'out', '48 kHz'),
 ('I2S_DAC_DIN', 38, 'I2S0 SD_OUT', 'out', 'PCM5102A'),
 ('I2S_ADC_DOUT', 39, 'I2S0 SD_IN', 'in', 'PCM1808'),
 ('MIDI_TX', 40, 'UART1 TX (matrix)', 'out', '74HCT125'),
 ('MIDI_RX', 41, 'UART1 RX (matrix)', 'in', '6N137'),
 ('LED_DATA', 42, 'RMT', 'out', 'WS2812 (level shifter on PANEL-2)'),
 ('PANEL_IRQ', 47, 'GPIO in', 'in', '4x MCP23017 INTA (10k PU)'),
 ('GATE1_GPIO', 48, 'GPIO', 'out', '2N7000 gate out (GATE2 dropped)'),
 ('PWR_GOOD', 3, 'GPIO in', 'in', 'PWR-2 supervisor (100k PU)'),
 ('BOOT', 0, 'GPIO / strapping', 'in', 'BOOT button (USB-JTAG also available)'),
]
FREE_GPIO = [3, 13, 45, 46]
USB_PINS = ['USB_D-', 'USB_D+']
STRAP_PINS = [0, 3, 45, 46]

# PANEL-2 rev.2 canon (same as CORE-2 rev.2)
J14_PANEL = [(1,'CVOUT1'),(2,'AGND'),(3,'CVOUT2'),(4,'AGND'),(5,'CVOUT3'),(6,'AGND'),
 (7,'CVOUT4'),(8,'AGND'),(9,'CVIN1'),(10,'AGND'),(11,'CVIN2'),(12,'AGND'),
 (13,'CVIN3'),(14,'AGND'),(15,'CVIN4'),(16,'AGND'),(17,'GATE1'),(18,'AGND'),
 (19,'NC'),(20,'AGND'),(21,'FADER1'),(22,'AGND'),(23,'FADER2'),(24,'AGND'),
 (25,'EN_LED5'),(26,'AGND')]
J16_PANEL = [(1,'I2C0_SDA'),(2,'DGND'),(3,'I2C0_SCL'),(4,'DGND'),(5,'PANEL_IRQ'),(6,'DGND'),
 (7,'LED_DATA'),(8,'DGND'),(9,'5V_LED'),(10,'DGND'),(11,'3V3_PANEL'),(12,'DGND'),
 (13,'5V_LED'),(14,'DGND'),(15,'EN_RAILS'),(16,'LED_RET')]
# J15 FFC-40: mechanical PANEL-2 J12 connector, but CORE-S3 uses SPI panel (partial UI)
J15_DISPLAY = [(1,'DGND'),(2,'DGND'),(3,'LCD_SCK'),(4,'LCD_MOSI'),(5,'LCD_CS'),(6,'LCD_DC'),
 (7,'LCD_RST'),(8,'BL_PWM'),(9,'3V3_PANEL'),(10,'DGND'),(11,'BL_20V'),(12,'BL_CATHODE'),
 (13,'DGND'),(14,'DGND'),(15,'DGND'),(16,'DGND'),(17,'DGND'),(18,'DGND'),(19,'DGND'),(20,'DGND'),
 (21,'DGND'),(22,'DGND'),(23,'DGND'),(24,'DGND'),(25,'DGND'),(26,'DGND'),(27,'3V3_PANEL'),
 (28,'3V3_PANEL'),(29,'DGND'),(30,'DGND'),(31,'DGND'),(32,'DGND'),(33,'DGND'),(34,'DGND'),
 (35,'DGND'),(36,'DGND'),(37,'DGND'),(38,'DGND'),(39,'DGND'),(40,'DGND')]
J17_PWR3 = [(1,'VSYS'),(2,'VSYS'),(3,'BATT_P'),(4,'BATT_P'),(5,'12V_EXT'),(6,'12V_EXT'),
 (7,'PGND'),(8,'PGND'),(9,'N12_EXT'),(10,'N12_EXT'),(11,'PGND'),(12,'PGND'),
 (13,'5V_EXT'),(14,'5V_EXT'),(15,'PGND'),(16,'PGND'),(17,'5V_LED'),(18,'LED_RET'),
 (19,'PGND'),(20,'PGND')]
J18_PWR4 = [(1,'BATT_MON_RAW'),(2,'NTC_PACK'),(3,'I2C0_SDA'),(4,'I2C0_SCL'),(5,'FUEL_ALRT'),
 (6,'PWR_GOOD'),(7,'EN_BUS12'),(8,'EN_N12'),(9,'EN_LED5'),(10,'EN_5V'),(11,'PGND'),(12,'PGND')]

RAILS = [
 dict(name='+3V3 (TPS63000 buck-boost)', src='VSYS 3.0...4.4 V', bud=700, cap=1000,
      margin=30, loads='S3 350 + PSRAM 50 + panel logic 150 + audio 60 + CV 30 + MIDI 10 + misc 50'),
 dict(name='+5V (PWR-2 J3)', src='PWR-2 5.10 V', bud=290, cap=1600,
      margin=82, loads='PCM1808 VCC 30 + MIDI 10 + BL-boost input 80 + panel 5V 170 (5V_LED)'),
 dict(name='+12V (PWR-2 J3)', src='PWR-2 11.7 V', bud=150, cap=330, margin=55,
      loads='module bus 2x60 + opamps 30'),
 dict(name='-12V (PWR-2 J3)', src='PWR-2 -11.55 V', bud=95, cap=95, margin=0,
      loads='module bus 2x40 + opamps 15; budget = limit, exception'),
 dict(name='BL_20V (MT3608 #3)', src='+5V', bud=30, cap=100, margin=70,
      loads='LCD backlight LED string 20-25 mA'),
]
COMPARISON = [
 ('MCU', 'ESP32-P4 (RISC-V 400 MHz, 32 MB PSRAM) + ESP32-C6 (Wi-Fi 6/BLE 5.3)', 'ESP32-S3-WROOM-1-N16R8 (Xtensa LX7 240 MHz, 16 MB flash, 8 MB octal PSRAM), Wi-Fi 4/BLE 5.0 onboard'),
 ('USB', 'HS 480 Mbps, composite HID+MIDI+UAC2+CDC', 'FS 12 Mbps, composite HID+MIDI+UAC1/2 stereo+CDC (8x8 UAC2 NOT supported)'),
 ('Display', 'RGB565 800x480, 20 GPIO, up to 60 fps', 'SPI 800x480 16-bit, 6 GPIO, full frame ~12-15 fps, partial UI 10-20 fps'),
 ('DSP', 'Dual DSP extensions, 360 DMIPS+, 32 MB PSRAM', 'Xtensa LX7 + vector ops, 8 MB PSRAM; 8 mono voices / 6 polyphonic with effects'),
 ('Wi-Fi/BLE', 'C6 coprocessor over SPI (esp-hosted)', 'native Wi-Fi 4 / BLE 5.0; no C6 board/keep-out/LDO'),
 ('SD card', 'SDIO 4-bit', 'SPI mode on shared SPI3 bus (~10-20 MB/s)'),
 ('Power', '+3V3 via AP2112K + MP1584 + AP2112K(+3V3_C6); +5/+-12 from PWR-2', '+3V3 via single TPS63000 buck-boost from VSYS (no MP1584/LDOs/C6 rail)'),
 ('Connectors', 'J14/J15/J16 PANEL-2 + J17/J18 PWR-2', 'same J14/J13/J12 (J15 FFC-40) + J17/J18 (panel J12 pinout used for SPI subset)'),
 ('BOM cost (est.)', 'higher: P4+C6 modules, HS crystal/ESD, 2 extra LDOs', 'lower: one S3 module (~$8-12), no C6/LDOs; board est. $45-65, kit $199 target'),
 ('Firmware', 'ESP-IDF P4 + esp-hosted RPC', 'ESP-IDF S3; shared UI/audio layers; some P4 DSP paths reduced'),
]

SECTIONS = {
 'POWER': 'POWER: USB-C + BQ24074 charge/path, TPS63000 3V3 buck-boost (D-41), +-12V/+5V from PWR-2 J17, BL boost',
 'MCU': 'MCU: ESP32-S3-WROOM-1-N16R8 (USB FS, 8 MB PSRAM), microSD SPI, BOOT/RESET, UART0 TP',
 'AUDIO': 'AUDIO: PCM5102A DAC + PCM1808 ADC (I2S), TL072 LINE/PHONES, rear jacks',
 'CV': 'CV: 2x MCP4728 (0x60/0x61), 6x TL074 x4.9, CV IN level shift (1-4), MCP3208 + chains',
 'MIDI': 'MIDI TRS-A: 6N137 IN / 74HCT125 OUT; GATE_OUT driver',
 'BUS': 'MODULE BUS: 2x IDC-26 analog bus (+-12V, CV1..4, GATE, audio), per-port protection',
 'PANEL': 'PANEL-2 rev.2 canon: J14 IDC-26 analog, J15 FFC-40 SPI display, J16 IDC-16 digital; rear jacks; J17/J18 PWR-2',
 'TP': 'TEST POINTS (TP1..TP22)',
}
