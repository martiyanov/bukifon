# -*- coding: utf-8 -*-
"""CORE-2 (rev.1, PRE-FREEZE) single source of truth: MCU pin map, connectors,
power tree, panel expander map.  Used by:
  gen_pinmap.py   -> pinmap.csv / pinmap.md
  check_pinmap.py -> validation (dupes, boot safety, reserve)
  gen_power.py    -> power-tree.md
  gen_core2_sch.py-> CORE-2.kicad_sch
  gen_interfaces.py -> interfaces.md
Status: PRE-FREEZE / DO NOT FABRICATE.  MCU: ESP32-P4 (55 GPIO, QFN104), PSRAM
in-package 32 MB (ESP32-P4NRW32).  Facts from ESP32-P4 Series Datasheet v0.7
(Espressif): 55 GPIO; boot strapping = GPIO35..GPIO38; USB HS PHY on dedicated
pins USB_DM/USB_DP; SDMMC slot0 pads on GPIO39..GPIO48; LCD_CAM parallel RGB
8/16/24-bit via GPIO matrix; I2S x3 via GPIO matrix; I2C x2 via GPIO matrix.
"""

MCU = 'ESP32-P4NRW32 (ESP32-P4, 32 MB PSRAM in package, QFN104)'
SLOT = 'J-MCU: 2x32 (64 pin, 2.54 mm) MCU-module slot defined by this board (pre-freeze)'

# ---------------------------------------------------------------- rails -----
# cap_mA = realistic capability of the chosen converter (datasheet/derived),
# budget_mA = worst-case load allocated on the board (documented assumptions).
RAILS = [
 dict(name='VBUS_USB', kind='input', nominal=5.0, source='USB-C 5 V (data+charge)',
      converter='BQ24074 IN (ILIM 1.5 A)', cap_mA=1500, budget_mA=1500,
      loads=['charge 1.5 A (max)'], margin=None,
      note='USB-C 5 V only charges/powers system through BQ24074; not a board rail'),
 dict(name='VSYS', kind='system', nominal=4.2, source='BQ24074 OUT (power path)',
      converter='BQ24074 + 1S2P 18650 / BMS', cap_mA=3000, budget_mA=2900,
      loads=['MT3608 #1 (12 V) input ~1.3 A', 'MT3608 #2 (5 V) input ~1.6 A'],
      margin=3, note='1S2P 5000 mAh => ~0.6C at worst case; BMS FETs >=5 A'),
 dict(name='+12V', kind='rail', nominal=12.0, source='VSYS',
      converter='MT3608 boost #1 (2 A switch)', cap_mA=520, budget_mA=330,
      loads=['bus ports 2 x 60 mA', 'audio op-amps (TL074/TL072) 30 mA',
             'MC34063 -12 V converter input ~120 mA'], margin=36,
      note='MT3608 set 12.1 V; 2 x 100 uF, ferrite + TVS; bus protected per port'),
 dict(name='-12V', kind='rail', nominal=-12.0, source='+12V',
      converter='MC34063 inverting (250 mA)', cap_mA=250, budget_mA=95,
      loads=['bus ports 2 x 40 mA', 'op-amp V- 15 mA'], margin=62,
      note='floating-ground inverting topology, 220 uH, SS34, 33k/3.9k'),
 dict(name='+5V', kind='rail', nominal=5.1, source='VSYS',
      converter='MT3608 boost #2 (2 A switch)', cap_mA=1800, budget_mA=1000,
      loads=['WS2812 chain 74 LED: 550 mA (firmware cap)',
             'PCM1808 VCC / audio 30 mA', 'MIDI 10 mA',
             'panel 5 V logic 20 mA', '3V3 LDOs input 90 mA',
             'BL boost #3 input ~80 mA', 'C6 LDO input 60 mA'],
      margin=44, note='LED brightness hard-capped in firmware + 2.5 A polyfuse'),
 dict(name='+3V3', kind='rail', nominal=3.3, source='+5V',
      converter='AP2112K-3.3 (600 mA LDO)', cap_mA=450, budget_mA=150,
      loads=['LCD logic 60 mA', 'MCP23017 x3 3 mA', 'MCP4728 x2 2 mA',
             'MCP3208 1 mA', '24C32 1 mA', 'PCM5102A 20 mA', 'PCM1808 VDD 15 mA',
             '74HCT1G125 / misc 10 mA', 'panel sensors 20 mA'], margin=67,
      note='LDO output 600 mA; 450 mA allocated for margin >=25 %'),
 dict(name='+3V3_C6', kind='rail', nominal=3.3, source='+5V',
      converter='AP2112K-3.3 dedicated LDO (600 mA)', cap_mA=450, budget_mA=250,
      loads=['ESP32-C6-MINI-1 Wi-Fi/BLE peak 240 mA', 'module/IO 10 mA'],
      margin=44, note='separate LDO for radio: keeps Wi-Fi bursts off the MCU rail; '
                      'bulk 22 uF + 100 nF at module, ferrite optional'),
 dict(name='+3V3_MCU', kind='rail', nominal=3.3, source='+5V',
      converter='MP1584 buck module (3 A)', cap_mA=2400, budget_mA=700,
      loads=['ESP32-P4 module + PSRAM 600 mA (peak)', 'MCU decoupling/IO 100 mA'],
      margin=71, note='separate rail for MCU/PSRAM (R-12 requirement); '
                      'ferrite + 2x10 uF at module'),
 dict(name='BL_20V', kind='rail', nominal=20.0, source='+5V',
      converter='MT3608 boost #3 (2 A switch)', cap_mA=100, budget_mA=30,
      loads=['LCD backlight LED string 20-25 mA'], margin=70,
      note='19-22 V rail for panel backlight; BL_ANODE/BL_CATHODE/BL_PWM go to '
           'PANEL-2 J12, current limit/driver on panel (pre-freeze)'),
]

# ------------------------------------------------------------ MCU pin map ---
# signal, gpio (int|None => dedicated/non-GPIO), peripheral, voltage, direction,
# pull, boot (state at reset that matters), module pin, connector, note
PINMAP = [
 # --- SDIO microSD (SDMMC slot0 pads GPIO39..GPIO44, IO MUX) ---
 ('SD_D0', 39, 'SDMMC SLOT0 D0', '3.3', 'bidir', '10k PU', 'high', 23, 'J-SD.DAT0', 'IO MUX SD1_CDATA0'),
 ('SD_D1', 40, 'SDMMC SLOT0 D1', '3.3', 'bidir', '10k PU', 'high', 24, 'J-SD.DAT1', 'IO MUX SD1_CDATA1'),
 ('SD_D2', 41, 'SDMMC SLOT0 D2', '3.3', 'bidir', '10k PU', 'high', 25, 'J-SD.DAT2', 'IO MUX SD1_CDATA2'),
 ('SD_D3', 42, 'SDMMC SLOT0 D3', '3.3', 'bidir', '10k PU', 'high', 26, 'J-SD.DAT3/CD', 'IO MUX SD1_CDATA3'),
 ('SD_CLK', 43, 'SDMMC SLOT0 CLK', '3.3', 'out', 'none', 'low', 27, 'J-SD.CLK', 'IO MUX SD1_CCLK'),
 ('SD_CMD', 44, 'SDMMC SLOT0 CMD', '3.3', 'bidir', '10k PU', 'high', 28, 'J-SD.CMD', 'IO MUX SD1_CCMD'),
 ('SD_CD', 45, 'GPIO in (card detect)', '3.3', 'in', '10k PU', 'high', 29, 'J-SD.DET', 'card detect switch to GND'),
 # --- I2S0 (audio DAC+ADC) ---
 ('I2S_MCLK', 20, 'I2S0 MCLK out', '3.3', 'out', 'none', 'low', 30, 'U9.SCK / U10.SCKI', '256fs = 12.288 MHz @48k'),
 ('I2S_BCK', 16, 'I2S0 BCK out', '3.3', 'out', 'none', 'low', 31, 'U9.BCK / U10.BCK', '64fs = 3.072 MHz @48k'),
 ('I2S_LRCK', 17, 'I2S0 WS/LRCK out', '3.3', 'out', 'none', 'low', 32, 'U9.LRCK / U10.LRCK', '48 kHz'),
 ('I2S_DAC_DIN', 18, 'I2S0 SD out', '3.3', 'out', 'none', 'low', 33, 'U9.DIN', 'to PCM5102A'),
 ('I2S_ADC_DOUT', 19, 'I2S0 SD in', '3.3', 'in', 'none', 'high', 34, 'U10.DOUT', 'from PCM1808'),
 # --- I2C0 ---
 ('I2C0_SDA', 21, 'I2C0 SDA', '3.3', 'bidir', '2.2k PU', 'high', 35, 'J-PANEL.5 / J-LCD.34 / U4/U5/U11/U12', 'MCP4728 x2, 24C32, MCP23017 x3'),
 ('I2C0_SCL', 22, 'I2C0 SCL', '3.3', 'out', '2.2k PU', 'high', 36, 'J-PANEL.7 / J-LCD.35 / U4/U5/U11/U12', '400 kHz'),
 # --- SPI2: MCP3208 (CS0) + ESP32-C6 host link (CS1) ---
 ('SPI2_SCK', 6, 'GP-SPI2 SCK', '3.3', 'out', 'none', 'low', 37, 'U6.CLK / U-C6.SCK', 'shared bus, per-device CS'),
 ('SPI2_MOSI', 7, 'GP-SPI2 MOSI', '3.3', 'out', 'none', 'low', 38, 'U6.DIN / U-C6.MOSI', ''),
 ('SPI2_MISO', 8, 'GP-SPI2 MISO', '3.3', 'in', 'none', 'high', 39, 'U6.DOUT / U-C6.MISO', ''),
 ('MCP3208_CS', 9, 'GP-SPI2 CS0', '3.3', 'out', '10k PU', 'high', 40, 'U6.CS', 'active low'),
 # --- MIDI UART (UART1 default pads) ---
 ('MIDI_TX', 10, 'UART1 TX', '3.3', 'out', 'none', 'high', 41, 'U11.2 (74HCT125 A)', 'via 74HCT125 to TRS OUT'),
 ('MIDI_RX', 11, 'UART1 RX', '3.3', 'in', '4.7k PU', 'high', 42, 'U7.VO (6N137)', 'from TRS IN'),
 # --- UART0 testpoints ---
 ('UART0_TX', 37, 'UART0 TX', '3.3', 'out', 'none', 'high', 21, 'J-UART.2', 'boot log / testpoint'),
 ('UART0_RX', 38, 'UART0 RX', '3.3', 'in', 'none', 'high', 22, 'J-UART.3', 'testpoint'),
 # --- LCD_CAM parallel RGB565 + I2C + INT + BL_PWM (25 signals, PANEL-2 J12) ---
 ('LCD_PCLK', 12, 'LCD_CAM PCLK', '3.3', 'out', 'none', 'low', 43, 'J-LCD.7', ''),
 ('LCD_DE', 13, 'LCD_CAM DE', '3.3', 'out', 'none', 'low', 44, 'J-LCD.9', ''),
 ('LCD_HSYNC', 14, 'LCD_CAM HSYNC', '3.3', 'out', 'none', 'low', 45, 'J-LCD.11', ''),
 ('LCD_VSYNC', 15, 'LCD_CAM VSYNC', '3.3', 'out', 'none', 'low', 46, 'J-LCD.13', ''),
 ('LCD_B0', 0, 'LCD_CAM data B0', '3.3', 'out', 'none', 'low', 47, 'J-LCD.15', 'RGB565: B0..B4'),
 ('LCD_B1', 1, 'LCD_CAM data B1', '3.3', 'out', 'none', 'low', 48, 'J-LCD.16', ''),
 ('LCD_B2', 2, 'LCD_CAM data B2', '3.3', 'out', 'none', 'low', 49, 'J-LCD.17', ''),
 ('LCD_B3', 3, 'LCD_CAM data B3', '3.3', 'out', 'none', 'low', 50, 'J-LCD.18', ''),
 ('LCD_B4', 4, 'LCD_CAM data B4', '3.3', 'out', 'none', 'low', 51, 'J-LCD.19', ''),
 ('LCD_G0', 5, 'LCD_CAM data G0', '3.3', 'out', 'none', 'low', 52, 'J-LCD.20', 'G0..G5'),
 ('LCD_G1', 23, 'LCD_CAM data G1', '3.3', 'out', 'none', 'low', 53, 'J-LCD.21', ''),
 ('LCD_G2', 28, 'LCD_CAM data G2', '3.3', 'out', 'none', 'low', 54, 'J-LCD.22', ''),
 ('LCD_G3', 29, 'LCD_CAM data G3', '3.3', 'out', 'none', 'low', 55, 'J-LCD.23', ''),
 ('LCD_G4', 30, 'LCD_CAM data G4', '3.3', 'out', 'none', 'low', 56, 'J-LCD.24', ''),
 ('LCD_G5', 31, 'LCD_CAM data G5', '3.3', 'out', 'none', 'low', 57, 'J-LCD.25', ''),
 ('LCD_R0', 32, 'LCD_CAM data R0', '3.3', 'out', 'none', 'low', 58, 'J-LCD.26', 'R0..R4'),
 ('LCD_R1', 33, 'LCD_CAM data R1', '3.3', 'out', 'none', 'low', 59, 'J-LCD.27', ''),
 ('LCD_R2', 34, 'LCD_CAM data R2', '3.3', 'out', 'none', 'low', 60, 'J-LCD.28', ''),
 ('LCD_R3', 46, 'LCD_CAM data R3', '3.3', 'out', 'none', 'low', 61, 'J-LCD.29', ''),
 ('LCD_R4', 47, 'LCD_CAM data R4', '3.3', 'out', 'none', 'low', 62, 'J-LCD.30', ''),
 ('BL_PWM', 49, 'LEDC PWM', '3.3', 'out', 'none', 'low', 16, 'J-LCD.31', 'backlight PWM -> panel BL driver'),
 # --- panel LED chain + IRQ + gates ---
 ('LED_GPIO', 48, 'RMT TX (WS2812)', '3.3 -> 5 V', 'out', 'none', 'low', 15, 'U-1G125.A', 'level shifter + 330R -> J-PANEL.11 LED_DATA'),
 ('PANEL_IRQ', 51, 'GPIO in', '3.3', 'in', '10k PU', 'high', 18, 'J-PANEL.9 / J-LCD.36', 'MCP23017 INTA (open drain)'),
 ('GATE1', 52, 'GPIO out (2N7000)', '5.0 (open drain)', 'out', 'none', 'low', 19, 'J-PANEL.25 / BUS', '0/5 V gate, 4.7k PU to +5V_BUS'),
 ('GATE2', 53, 'GPIO out (2N7000)', '5.0 (open drain)', 'out', 'none', 'low', 20, 'J-PANEL.26 / BUS', '0/5 V gate'),
 # --- ESP32-C6 coprocessor host link (Wi-Fi/BLE; SPI esp-hosted) ---
 ('C6_CS', 26, 'GP-SPI2 CS1', '3.3', 'out', '10k PU', 'high', 10, 'U-C6.SPI_CS', 'C6 select (shared SPI2)'),
 ('C6_HS', 24, 'GPIO (handshake)', '3.3', 'bidir', '10k PU', 'high', 11, 'U-C6.HANDSHAKE', 'esp-hosted SPI handshake'),
 ('C6_DR', 25, 'GPIO (data ready IRQ)', '3.3', 'in', '10k PU', 'high', 12, 'U-C6.DATA_READY', 'GPIO25 has USB_PU strap at reset (kept high)'),
 ('C6_RST', 27, 'GPIO out (C6 reset)', '3.3', 'out', '10k PD', 'low', 13, 'U-C6.EN', 'resets C6 at power-up; released by firmware'),
 # --- USB / power / strap ---
 ('BOOT', 35, 'boot strapping (GPIO35)', '3.3', 'in (strap)', '10k PU + button to GND', 'high (SPI boot)', 8, 'SW-BOOT', 'low at reset = joint download boot (USB HS / UART0)'),
 ('STRAP36', 36, 'boot strapping (GPIO36)', '3.3', 'in (strap)', '10k PU', 'high', 9, 'R96', 'needs 1 for joint download boot; 10k PU allows BOOT-button flashing'),
 ('VBUS_DET', 54, 'GPIO in (VBUS detect)', '3.3', 'in', '100k/100k divider', 'low', 14, 'D1/R', 'USB-C attach detect (100k/100k + 100nF)'),
 # --- dedicated / non-GPIO module pins ---
 ('USB_HS_DP', None, 'USB 2.0 HS OTG D+ (dedicated pin 50)', 'USB', 'bidir', 'USB internal', 'USB', 6, 'J-USB.A6/B6', 'through USBLC6-2SC6'),
 ('USB_HS_DM', None, 'USB 2.0 HS OTG D- (dedicated pin 49)', 'USB', 'bidir', 'USB internal', 'USB', 7, 'J-USB.A7/B7', 'through USBLC6-2SC6'),
 ('CHIP_PU', None, 'reset (CHIP_PU)', '3.3', 'in', '10k PU + 100nF', 'high', 5, 'SW-RESET', 'power-on reset, RC'),
 ('3V3_MCU', None, 'MCU/PSRAM supply', '3.3', 'power', '-', '-', 3, 'U26 out', 'MP1584 buck, separate rail'),
 ('3V3_MCU', None, 'MCU/PSRAM supply', '3.3', 'power', '-', '-', 4, 'U26 out', ''),
 ('GND', None, 'ground', '0', 'power', '-', '-', 1, 'GND', ''),
 ('GND', None, 'ground', '0', 'power', '-', '-', 2, 'GND', ''),
 ('GND', None, 'ground', '0', 'power', '-', '-', 17, 'GND', ''),
 ('GND', None, 'ground', '0', 'power', '-', '-', 63, 'GND', ''),
 ('GND', None, 'ground', '0', 'power', '-', '-', 64, 'GND', ''),
]
# module slot pins actually assigned in PINMAP
MODULE_PINS = {r[7]: r[0] for r in PINMAP}
assert len(MODULE_PINS) == 64, sorted(set(range(1, 65)) - set(MODULE_PINS))

RESERVED = [
 (36, 'boot strapping GPIO36 - 10k PU (must be 1 for joint download boot)'),
]

# ----------------------------------------------------- connectors (pins) ---
# signal names are nets; None/GND handled by generator
J_PANEL = [
 (1, '3V3', 'power'), (2, 'DGND', 'gnd'), (3, '5V', 'power'), (4, 'CVOUT5', 'a'),
 (5, 'I2C0_SDA', 'd'), (6, 'DGND', 'gnd'), (7, 'I2C0_SCL', 'd'), (8, 'DGND', 'gnd'),
 (9, 'PANEL_IRQ', 'd'), (10, 'CVOUT6', 'a'), (11, 'LED_DATA', 'd'), (12, 'DGND', 'gnd'),
 (13, 'FADER1', 'a'), (14, 'AGND', 'agnd'), (15, 'FADER2', 'a'), (16, 'AGND', 'agnd'),
 (17, 'CVIN1', 'a'), (18, 'AGND', 'agnd'), (19, 'CVIN2', 'a'), (20, 'AGND', 'agnd'),
 (21, 'CVOUT1', 'a'), (22, 'CVOUT2', 'a'), (23, 'CVOUT3', 'a'), (24, 'CVOUT4', 'a'),
 (25, 'GATE1', 'd'), (26, 'GATE2', 'd'),
]
J_LCD = [
 (1, '5V', 'power'), (2, '5V', 'power'), (3, 'DGND', 'gnd'), (4, 'DGND', 'gnd'),
 (5, '3V3', 'power'), (6, 'DGND', 'gnd'),
 (7, 'LCD_PCLK', 'd'), (8, 'DGND', 'gnd'), (9, 'LCD_DE', 'd'), (10, 'DGND', 'gnd'),
 (11, 'LCD_HSYNC', 'd'), (12, 'DGND', 'gnd'), (13, 'LCD_VSYNC', 'd'), (14, 'DGND', 'gnd'),
 (15, 'LCD_B0', 'd'), (16, 'LCD_B1', 'd'), (17, 'LCD_B2', 'd'), (18, 'LCD_B3', 'd'),
 (19, 'LCD_B4', 'd'), (20, 'LCD_G0', 'd'), (21, 'LCD_G1', 'd'), (22, 'LCD_G2', 'd'),
 (23, 'LCD_G3', 'd'), (24, 'LCD_G4', 'd'), (25, 'LCD_G5', 'd'), (26, 'LCD_R0', 'd'),
 (27, 'LCD_R1', 'd'), (28, 'LCD_R2', 'd'), (29, 'LCD_R3', 'd'), (30, 'LCD_R4', 'd'),
 (31, 'BL_PWM', 'd'), (32, 'BL_ANODE', 'power'), (33, 'BL_CATHODE', 'power'),
 (34, 'I2C0_SDA', 'd'), (35, 'I2C0_SCL', 'd'), (36, 'PANEL_IRQ', 'd'),
 (37, 'DGND', 'gnd'), (38, 'DGND', 'gnd'), (39, 'DGND', 'gnd'), (40, 'DGND', 'gnd'),
]

# new analog-only module bus (R-11/R-22): +-12 V, CV, gate, audio
J_BUS = [
 (1, '12V_B', 'power'), (2, 'PGND', 'gnd'), (3, '-12V_B', 'power'), (4, 'PGND', 'gnd'),
 (5, 'CVOUT1', 'a'), (6, 'AGND', 'agnd'), (7, 'CVOUT2', 'a'), (8, 'AGND', 'agnd'),
 (9, 'CVOUT3', 'a'), (10, 'AGND', 'agnd'), (11, 'CVOUT4', 'a'), (12, 'AGND', 'agnd'),
 (13, 'GATE1', 'd'), (14, 'DGND', 'gnd'), (15, 'GATE2', 'd'), (16, 'DGND', 'gnd'),
 (17, 'AUDIN_L', 'a'), (18, 'AGND', 'agnd'), (19, 'AUDIN_R', 'a'), (20, 'AGND', 'agnd'),
 (21, 'AUDOUT_L', 'a'), (22, 'AGND', 'agnd'), (23, 'AUDOUT_R', 'a'), (24, 'AGND', 'agnd'),
 (25, 'SPARE1', 'x'), (26, 'SPARE2', 'x'),
]
# digital expansion for smart modules (R-22): I2S/TDM + SPI + I2C + power
J_DIG = [
 (1, '3V3', 'power'), (2, 'DGND', 'gnd'), (3, '5V', 'power'), (4, 'DGND', 'gnd'),
 (5, 'I2S_BCK', 'd'), (6, 'I2S_LRCK', 'd'), (7, 'I2S_DAC_DIN', 'd'), (8, 'I2S_ADC_DOUT', 'd'),
 (9, 'SPI2_SCK', 'd'), (10, 'SPI2_MOSI', 'd'), (11, 'SPI2_MISO', 'd'), (12, 'DGND', 'gnd'),
 (13, 'I2C0_SDA', 'd'), (14, 'I2C0_SCL', 'd'), (15, 'DGND', 'gnd'), (16, 'DGND', 'gnd'),
]
# rear / edge connectors (off-board panel parts; wired via terminal blocks)
# single USB-C 16P: USB 2.0 HS data + 5 V charge/power (task: "данные + заряд")
J_USB_DATA = [('A4/B4/A9/B9', 'VBUS_CHG', 'power'), ('A6/B6', 'USB_HS_DP', 'usb'),
              ('A7/B7', 'USB_HS_DM', 'usb'), ('A5', 'CC1', 'usb'), ('B5', 'CC2', 'usb'),
              ('A1/B1/A12/B12', 'GND', 'gnd'), ('SH', 'SHIELD', 'gnd')]
TPS = [
 ('TP1', 'VBUS_CHG', 'USB-C input'), ('TP2', 'VSYS', 'power-path output'),
 ('TP3', '12V', '+12 V bus rail'), ('TP4', '-12V', '-12 V bus rail'),
 ('TP5', '5V', '+5 V rail'), ('TP6', '3V3', '+3.3 V peripherals'),
 ('TP7', '3V3_MCU', '+3.3 V MCU/PSRAM'), ('TP8', 'BATT_MON', 'battery ADC'),
 ('TP9', 'I2S_MCLK', '12.288 MHz'), ('TP10', 'SD_CLK', 'SDIO clock'),
 ('TP11', 'USB_HS_DP', 'USB D+'), ('TP12', 'USB_HS_DM', 'USB D-'),
 ('TP13', 'AGND', 'analog ground'), ('TP14', 'DGND', 'digital ground'),
 ('TP15', 'PGND', 'power ground'), ('TP16', 'SPARE_IO54', 'free GPIO54'),
 ('TP17', 'CHIP_PU', 'reset'), ('TP18', 'BOOT', 'boot strap GPIO35'),
 ('TP19', '3V3_C6', 'Wi-Fi/BLE coprocessor rail'), ('TP20', 'BL_20V', 'backlight rail'),
 ('TP21', 'C6_CS', 'C6 SPI select'), ('TP22', 'C6_RST', 'C6 reset'),
]
# rear-panel connectors: audio jacks on CORE-2 rear wall (lead change)
TB_REAR = [
 (1, 'AUDOUT_L', 'TB1.1'), (2, 'AUDOUT_R', 'TB1.2'), (3, 'AGND', 'TB1.3'),
 (4, 'PHONES_L', 'TB1.4'), (5, 'PHONES_R', 'TB1.5'), (6, 'AGND', 'TB1.6'),
 (7, 'AUDIN_L', 'TB1.7'), (8, 'AUDIN_R', 'TB1.8'), (9, 'AGND', 'TB1.9'), (10, 'AGND', 'TB1.10'),
 (11, 'MIDI_IN_T', 'TB2.1'), (12, 'MIDI_IN_R', 'TB2.2'), (13, 'DGND', 'TB2.3'),
 (14, 'MIDI_OUT_T', 'TB2.4'), (15, 'MIDI_OUT_R', 'TB2.5'), (16, 'DGND', 'TB2.6'),
 (17, '12V_EXT', 'TB2.7'), (18, 'PGND', 'TB2.8'), (19, 'EXPR', 'TB2.9'), (20, '3V3', 'TB2.10'),
]

# PANEL-2 expanders (on the panel board; documented here for the wiring table)
MCP23017 = [
 dict(addr='0x20', ref='U-P1', role='ENC1..ENC8 (A/B)',
      pins=['GPA0..GPA7 = ENC1_A..ENC8_A', 'GPB0..GPB7 = ENC1_B..ENC8_B', 'INTA -> PANEL_IRQ']),
 dict(addr='0x21', ref='U-P2', role='ENC9..ENC16 (A/B)',
      pins=['GPA0..GPA7 = ENC9_A..ENC16_A', 'GPB0..GPB7 = ENC9_B..ENC16_B', 'INTB -> PANEL_IRQ']),
 dict(addr='0x22', ref='U-P3', role='42-key matrix 6 rows x 7 cols',
      pins=['GPA0..GPA6 = COL0..COL6 (inputs, 10k PU)',
            'GPB0..GPB5 = ROW0..ROW5 (outputs, scan)',
            'INTA -> PANEL_IRQ (key press)']),
]
FADERS = [('FADER1','FADER1','1k + 100nF -> MCP3208 CH2'), ('FADER2','FADER2','1k + 100nF -> MCP3208 CH3')]
MCP3208 = [
 ('CH0','CVIN1_ADC','CV IN 1 (panel jack; 100k/16.5k + 1.65 V offset)'),
 ('CH1','CVIN2_ADC','CV IN 2 (panel jack)'),
 ('CH2','FADER1_ADC','panel fader 1 (RC 1k/100nF)'),
 ('CH3','FADER2_ADC','panel fader 2 (RC 1k/100nF)'),
 ('CH4','EXPR_ADC','EXPRESSION pedal (rear jack, 3V3 divider)'),
 ('CH5','SPARE_ADC','reserve / expansion (RC to AGND, testpad)'),
 ('CH6','BATT_MON','battery 100k/47k divider, ADC battery monitor'),
 ('CH7','TEMP_MON','NTC 10k/10k divider (pack temperature)'),
]
JACKS = [
 ('CV OUT 1', 'CVOUT1', 'MCP4728#1 CHA -> TL074 x4.883 -> 1k + BAT54S (panel, J-PANEL.21)'),
 ('CV OUT 2', 'CVOUT2', 'MCP4728#1 CHB -> TL074 x4.883 -> 1k + BAT54S (panel)'),
 ('CV OUT 3', 'CVOUT3', 'MCP4728#1 CHC -> TL074 x4.883 -> 1k + BAT54S (panel)'),
 ('CV OUT 4', 'CVOUT4', 'MCP4728#1 CHD -> TL074 x4.883 -> 1k + BAT54S (panel)'),
 ('CV OUT 5', 'CVOUT5', 'MCP4728#2 CHA -> TL074 x4.883 -> 1k + BAT54S (panel, J-PANEL.4)'),
 ('CV OUT 6', 'CVOUT6', 'MCP4728#2 CHB -> TL074 x4.883 -> 1k + BAT54S (panel, J-PANEL.10)'),
 ('CV IN 1', 'CVIN1', '100k/16.5k + 1.65 V offset -> BAT54S -> 1k/100nF -> MCP3208 CH0 (panel)'),
 ('CV IN 2', 'CVIN2', '100k/16.5k + 1.65 V offset -> BAT54S -> 1k/100nF -> MCP3208 CH1 (panel)'),
 ('GATE OUT 1', 'GATE1', '2N7000 open-drain + 4.7k to +5V + 1k (panel)'),
 ('GATE OUT 2', 'GATE2', '2N7000 open-drain + 4.7k to +5V + 1k (panel)'),
 ('LINE OUT L', 'AUDOUT_L', 'rear 3.5 mm: PCM5102A OUTL -> 10uF -> TL072 -> 100R (TB1.1)'),
 ('LINE OUT R', 'AUDOUT_R', 'rear 3.5 mm: PCM5102A OUTR -> 10uF -> TL072 -> 100R (TB1.2)'),
 ('PHONES L/R', 'PHONES_L/R', 'rear 3.5 mm stereo, TL072 buffer -> 100R (TB1.4/5)'),
 ('AUDIO IN L', 'AUDIN_L', 'rear 3.5 mm -> 1k + BAT54S + 100pF -> 1uF -> PCM1808 VINL (TB1.7)'),
 ('AUDIO IN R', 'AUDIN_R', 'rear 3.5 mm -> 1k + BAT54S + 100pF -> 1uF -> PCM1808 VINR (TB1.8)'),
 ('MIDI IN', 'MIDI_IN_T/R', '6N137 + 220R (rear TRS-A, TB2.1/2)'),
 ('MIDI OUT', 'MIDI_OUT_T/R', '74HCT125 + 33R/220R (rear TRS-A, TB2.4/5)'),
 ('DC 12 V', '12V_EXT', 'rear 5.5/2.1 mm, from PWR-2 / external PSU (TB2.7/8), diode-OR to +12V'),
 ('EXPRESSION', 'EXPR', 'rear 6.35/3.5 mm, 3V3->pot->tip; RC 1k/100nF -> MCP3208 CH4 (TB2.9/10)'),
]
# display contract
DISPLAY = dict(interface='LCD_CAM parallel RGB565 (16-bit) + PCLK/DE/HSYNC/VSYNC',
               resolution='800x480', pins='25 signals: 20 LCD + I2C(2) + INT + BL_PWM',
               connector='J-LCD (FFC-40, 0.5 mm; PANEL-2 J12) + J-PANEL (IDC-26; J14)',
               bl='BL_ANODE/BL_CATHODE from CORE-2 +20 V boost, BL_PWM (LEDC) to panel driver',
               disp='LCD DISP handled on PANEL-2 expander (no P4 GPIO left)')
AUDIO = dict(fs='48 kHz (44.1 kHz also supported by PLL)',
             mclk='12.288 MHz = 256 fs', bck='3.072 MHz = 64 fs', lrck='48 kHz',
             dac='PCM5102A, I2S, 24-bit, SCK = shared MCLK', dac_cfg='FMT=0 (I2S), DEMP=0, FLT=0, XSMT=1 (unmute via 10k PU)',
             adc='PCM1808, I2S slave, 24-bit, MD0=MD1=0 (slave, 256/384/512fs auto), FMT=0 (I2S)',
             adc_supply='VCC=5 V, VDD=3.3 V, VREF 0.1uF+10uF',
             mute='PCM5102A XSMT low at power-up (RC), unmuted by firmware after I2S clock lock; '
                  'PCM1808 clock-halt reset; DAC out muted by XSMT; relay not used',
             rear_jacks='LINE OUT L/R + PHONES + AUDIO IN L/R (5 x 3.5 mm) on CORE-2 rear wall (TB1)')
USB = dict(device='USB 2.0 HS OTG, 480 Mbit/s, D+/D- dedicated PHY pins USB_DP/USB_DM',
           esd='USBLC6-2SC6', cc='5.1k UFP resistors (CC1/CC2)',
           diff='90 ohm differential pair, matched +-0.5 mm, GND guard',
           connector='USB-C 16P (USB 2.0 only) - single connector: data + charge',
           power='VBUS -> USBLC6 -> polyfuse 1.5 A -> BQ24074 (power-path)',
           composite='TinyUSB: HID keyboard + MIDI class + UAC2 audio (2 in / 2 out) + CDC debug; '
                     'one USB-C cable for data, MIDI, audio and charging',
           vbus_detect='GPIO54 via 100k/100k divider (device role / host detect)',
           c6='ESP32-C6-MINI-1 coprocessor for Wi-Fi 6 + BLE 5.3 (P4 has no radio); '
              'link: esp-hosted over SPI2 (shared with MCP3208, CS1) + handshake/data-ready + reset; '
              'separate +3V3_C6 LDO; DNP for ESP32-S3 build (native radio)')
CV = dict(out_range='0..10.0 V (DAC 0..2.048 V x 4.883; implemented 4.9 with 39k/10k -> 10.04 V)',
          out_prot='1k series + BAT54S to AGND/+12V', out_cal='2-point calibration per channel in 24C32 EEPROM 0x57',
          in_range='-10..+10 V -> 0..3.3 V: Vadc = 1.65 - 0.165*Vin (100k/16.5k + 1.65 V offset)',
          in_prot='BAT54S to AGND/+3V3 after 1k, RC 1k/100nF at ADC')
