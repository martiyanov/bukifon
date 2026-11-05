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
 dict(name='VBUS_USB', kind='input', nominal=5.0, source='USB-C CHARGE 5 V',
      converter='BQ24074 IN (ILIM 1.5 A)', cap_mA=1500, budget_mA=1500,
      loads=['charge 1.5 A (max)'], margin=None,
      note='USB-C 5 V only charges/powers system through BQ24074; not a board rail'),
 dict(name='VSYS', kind='system', nominal=4.2, source='BQ24074 OUT (power path)',
      converter='BQ24074 + 1S2P 18650 / BMS', cap_mA=3000, budget_mA=2900,
      loads=['MT3608 #1 (12 V) input ~1.3 A', 'MT3608 #2 (5 V) input ~1.6 A'],
      margin=3, note='1S2P 5000 mAh => ~0.6C at worst case; BMS FETs >=5 A'),
 dict(name='+12V', kind='rail', nominal=12.0, source='VSYS',
      converter='MT3608 boost (2 A switch)', cap_mA=520, budget_mA=330,
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
             'LCD backlight 300 mA', 'PCM1808 VCC / audio 30 mA',
             'MIDI 10 mA', 'panel 5 V logic 20 mA', '3V3 LDOs input 90 mA'],
      margin=44, note='LED brightness hard-capped in firmware + 2.5 A polyfuse'),
 dict(name='+3V3', kind='rail', nominal=3.3, source='+5V',
      converter='AP2112K-3.3 (600 mA LDO)', cap_mA=450, budget_mA=150,
      loads=['LCD logic 60 mA', 'MCP23017 x3 3 mA', 'MCP4728 x2 2 mA',
             'MCP3208 1 mA', '24C32 1 mA', 'PCM5102A 20 mA', 'PCM1808 VDD 15 mA',
             '74HCT1G125 / misc 10 mA', 'panel sensors 20 mA'], margin=67,
      note='LDO output 600 mA; 450 mA allocated for margin >=25 %'),
 dict(name='+3V3_MCU', kind='rail', nominal=3.3, source='+5V',
      converter='MP1584 buck module (3 A)', cap_mA=2400, budget_mA=700,
      loads=['ESP32-P4 module + PSRAM 600 mA (peak)', 'MCU decoupling/IO 100 mA'],
      margin=71, note='separate rail for MCU/PSRAM (R-12 requirement); '
                      'ferrite + 2x10 uF at module'),
]

# ------------------------------------------------------------ MCU pin map ---
# signal, gpio (int|None => dedicated/non-GPIO), peripheral, voltage, direction,
# pull, boot (state at reset that matters), module pin, connector, note
PINMAP = [
 # --- SDIO (SDMMC slot0 pads: GPIO39..GPIO44, IO MUX) ---
 ('SD_D0', 39, 'SDMMC SLOT0 D0', '3.3', 'bidir', '10k PU', 'high', 23, 'J-SD.DAT0', 'IO MUX SD1_CDATA0'),
 ('SD_D1', 40, 'SDMMC SLOT0 D1', '3.3', 'bidir', '10k PU', 'high', 24, 'J-SD.DAT1', 'IO MUX SD1_CDATA1'),
 ('SD_D2', 41, 'SDMMC SLOT0 D2', '3.3', 'bidir', '10k PU', 'high', 25, 'J-SD.DAT2', 'IO MUX SD1_CDATA2'),
 ('SD_D3', 42, 'SDMMC SLOT0 D3', '3.3', 'bidir', '10k PU', 'high', 26, 'J-SD.DAT3/CD', 'IO MUX SD1_CDATA3'),
 ('SD_CLK', 43, 'SDMMC SLOT0 CLK', '3.3', 'out', 'none', 'low', 27, 'J-SD.CLK', 'IO MUX SD1_CCLK'),
 ('SD_CMD', 44, 'SDMMC SLOT0 CMD', '3.3', 'bidir', '10k PU', 'high', 28, 'J-SD.CMD', 'IO MUX SD1_CCMD'),
 ('SD_CD', 45, 'GPIO in (card detect)', '3.3', 'in', '10k PU', 'high', 29, 'J-SD.DET', 'card detect switch to GND'),
 # --- I2S0 (audio) ---
 ('I2S_MCLK', 20, 'I2S0 MCLK out', '3.3', 'out', 'none', 'low', 30, 'U9.SCK / U10.SCKI', '256fs = 12.288 MHz @48k'),
 ('I2S_BCK', 16, 'I2S0 BCK out', '3.3', 'out', 'none', 'low', 31, 'U9.BCK / U10.BCK', '64fs = 3.072 MHz @48k'),
 ('I2S_LRCK', 17, 'I2S0 WS/LRCK out', '3.3', 'out', 'none', 'low', 32, 'U9.LRCK / U10.LRCK', '48 kHz'),
 ('I2S_DAC_DIN', 18, 'I2S0 SD out', '3.3', 'out', 'none', 'low', 33, 'U9.DIN', 'to PCM5102A'),
 ('I2S_ADC_DOUT', 19, 'I2S0 SD in', '3.3', 'in', 'none', 'high', 34, 'U10.DOUT', 'from PCM1808'),
 # --- I2C0 (CV DACs, EEPROM, PANEL expanders) ---
 ('I2C0_SDA', 21, 'I2C0 SDA', '3.3', 'bidir', '2.2k PU', 'high', 35, 'J-PANEL.5 / U4/U5/U12/U13/U14', 'shared bus, see addresses'),
 ('I2C0_SCL', 22, 'I2C0 SCL', '3.3', 'out', '2.2k PU', 'high', 36, 'J-PANEL.7 / U4/U5/U12/U13/U14', '400 kHz'),
 # --- SPI2 (MCP3208 ADC) ---
 ('SPI2_SCK', 6, 'GP-SPI2 SCK', '3.3', 'out', 'none', 'low', 37, 'U6.CLK', '10 MHz max'),
 ('SPI2_MOSI', 7, 'GP-SPI2 MOSI', '3.3', 'out', 'none', 'low', 38, 'U6.DIN', ''),
 ('SPI2_MISO', 8, 'GP-SPI2 MISO', '3.3', 'in', 'none', 'high', 39, 'U6.DOUT', ''),
 ('MCP3208_CS', 9, 'GP-SPI2 CS0', '3.3', 'out', '10k PU', 'high', 40, 'U6.CS', 'active low'),
 # --- MIDI UART (UART1 default pads GPIO10/11) ---
 ('MIDI_TX', 10, 'UART1 TX', '3.3', 'out', 'none', 'high', 41, 'U11.2 (74HCT125 A)', 'via 74HCT125 to TRS OUT'),
 ('MIDI_RX', 11, 'UART1 RX', '3.3', 'in', '4.7k PU', 'high', 42, 'U7.VO (6N137)', 'from TRS IN'),
 # --- UART0 testpoints (ROM boot log) ---
 ('UART0_TX', 37, 'UART0 TX', '3.3', 'out', 'none', 'high', 21, 'J-UART.2', 'boot log / testpoint'),
 ('UART0_RX', 38, 'UART0 RX', '3.3', 'in', 'none', 'high', 22, 'J-UART.3', 'testpoint'),
 # --- LCD_CAM parallel RGB565, 16-bit ---
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
 # --- panel misc ---
 ('LED_DATA', 48, 'RMT TX (WS2812)', '5.0 (via 74HCT1G125)', 'out', 'none', 'low', 15, 'J-PANEL.11', '3.3->5 V level shifter U15 + 330R'),
 ('LCD_BL', 49, 'LEDC PWM', '3.3', 'out', 'none', 'low', 16, 'J-LCD.31', 'backlight enable/PWM (driver on panel)'),
 ('LCD_DISP', 50, 'GPIO out', '3.3', 'out', 'none', 'low', 17, 'J-LCD.32', 'display power/enable'),
 ('PANEL_IRQ', 51, 'GPIO in', '3.3', 'in', '10k PU', 'high', 18, 'J-PANEL.9', 'MCP23017 INTA (open drain)'),
 ('GATE1', 52, 'GPIO out (2N7000)', '5.0 (open drain)', 'out', 'none', 'low', 19, 'J-PANEL.25 / BUS', '0/5 V gate, pull-up 4.7k to +5V_BUS'),
 ('GATE2', 53, 'GPIO out (2N7000)', '5.0 (open drain)', 'out', 'none', 'low', 20, 'J-PANEL.26 / BUS', '0/5 V gate'),
 # --- strapping / reserved / free ---
 ('BOOT', 35, 'boot strapping (GPIO35)', '3.3', 'in (strap)', '10k PU + button to GND', 'high (SPI boot)', 8, 'SW-BOOT', 'low at reset = joint download boot'),
 ('STRAP36', 36, 'boot strapping (GPIO36)', '3.3', 'in (strap)', '10k PD', 'low', 9, 'R96 to GND', 'kept low -> cannot enter download accidentally'),
 ('USB_JTAG_DP', 24, 'USB Serial/JTAG D+', '3.3 (USB PHY)', 'bidir', 'USB internal', 'USB', 10, 'J-DBG.3', 'reserved: flashing/debug console'),
 ('USB_JTAG_DM', 25, 'USB Serial/JTAG D-', '3.3 (USB PHY)', 'bidir', 'USB internal', 'USB', 11, 'J-DBG.2', 'reserved'),
 ('USB_FS_DP', 26, 'USB 2.0 FS OTG D+', '3.3 (USB PHY)', 'bidir', 'USB internal', 'USB', 12, 'NC (header option)', 'reserved alternative USB'),
 ('USB_FS_DM', 27, 'USB 2.0 FS OTG D-', '3.3 (USB PHY)', 'bidir', 'USB internal', 'USB', 13, 'NC (header option)', 'reserved alternative USB'),
 ('FREE_IO54', 54, 'GPIO reserve', '3.3', 'bidir', 'none', 'high', 14, 'TP', 'free GPIO (reserve, 1 of 55)'),
 # --- dedicated / non-GPIO module pins ---
 ('USB_HS_DP', None, 'USB 2.0 HS OTG D+ (dedicated pin 50)', 'USB', 'bidir', 'USB internal', 'USB', 6, 'J-USB.6/A6/B6', 'through USBLC6-2SC6'),
 ('USB_HS_DM', None, 'USB 2.0 HS OTG D- (dedicated pin 49)', 'USB', 'bidir', 'USB internal', 'USB', 7, 'J-USB.7/A7/B7', 'through USBLC6-2SC6'),
 ('CHIP_PU', None, 'reset (CHIP_PU)', '3.3', 'in', '10k PU + 100nF', 'high', 5, 'SW-RESET', 'power-on reset, RC 10k/100nF'),
 ('3V3_MCU', None, 'MCU/PSRAM supply', '3.3', 'power', '-', '-', 3, 'U3 out', 'MP1584 buck, separate rail'),
 ('3V3_MCU', None, 'MCU/PSRAM supply', '3.3', 'power', '-', '-', 4, 'U3 out', ''),
 ('GND', None, 'ground', '0', 'power', '-', '-', 1, 'GND', ''),
 ('GND', None, 'ground', '0', 'power', '-', '-', 2, 'GND', ''),
 ('GND', None, 'ground', '0', 'power', '-', '-', 63, 'GND', ''),
 ('GND', None, 'ground', '0', 'power', '-', '-', 64, 'GND', ''),
]
# module slot pins actually assigned in PINMAP
MODULE_PINS = {r[7]: r[0] for r in PINMAP}
assert len(MODULE_PINS) == 64, sorted(set(range(1, 65)) - set(MODULE_PINS))

RESERVED = [
 (24, 'USB Serial/JTAG D+ (flash/debug)'),
 (25, 'USB Serial/JTAG D- (flash/debug)'),
 (26, 'USB 2.0 FS OTG D+ (alternative USB, header option)'),
 (27, 'USB 2.0 FS OTG D- (alternative USB, header option)'),
 (36, 'boot strapping GPIO36 - fixed low (10k PD)'),
]

# ----------------------------------------------------- connectors (pins) ---
# signal names are nets; None/GND handled by generator
J_PANEL = [
 (1, '3V3', 'power'), (2, 'DGND', 'gnd'), (3, '5V', 'power'), (4, 'DGND', 'gnd'),
 (5, 'I2C0_SDA', 'd'), (6, 'DGND', 'gnd'), (7, 'I2C0_SCL', 'd'), (8, 'DGND', 'gnd'),
 (9, 'PANEL_IRQ', 'd'), (10, 'DGND', 'gnd'), (11, 'LED_DATA', 'd'), (12, 'DGND', 'gnd'),
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
 (31, 'LCD_BL', 'd'), (32, 'LCD_DISP', 'd'), (33, 'DGND', 'gnd'), (34, 'DGND', 'gnd'),
 (35, 'AUDIN_L', 'a'), (36, 'AGND', 'agnd'), (37, 'AUDIN_R', 'a'), (38, 'AGND', 'agnd'),
 (39, 'DGND', 'gnd'), (40, 'DGND', 'gnd'),
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
]
TB_REAR = [
 (1, 'MIDI_IN_T', 'TB1.1'), (2, 'MIDI_IN_R', 'TB1.2'), (3, 'DGND', 'TB1.3'),
 (4, 'MIDI_OUT_T', 'TB1.4'), (5, 'MIDI_OUT_R', 'TB1.5'), (6, 'DGND', 'TB1.6'),
 (7, 'AUDOUT_L', 'TB1.7'), (8, 'AGND', 'TB1.8'), (9, 'AUDOUT_R', 'TB1.9'), (10, 'AGND', 'TB1.10'),
 (11, 'PHONES_L', 'TB1.11'), (12, 'PHONES_R', 'TB1.12'),
 (13, '12V_EXT', 'TB2.1'), (14, 'PGND', 'TB2.2'), (15, 'EXPR', 'TB2.3'), (16, 'AGND', 'TB2.4'),
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
 ('CH0','CVIN1','CV IN 1 jack (100k/16.5k + 1.65 V offset)'),
 ('CH1','CVIN2','CV IN 2 jack'),
 ('CH2','FADER1','panel fader 1 (RC 1k/100nF)'),
 ('CH3','FADER2','panel fader 2'),
 ('CH4','SPARE_ADC1','reserve / expansion (testpoint)'),
 ('CH5','SPARE_ADC2','reserve / expansion (testpoint)'),
 ('CH6','BATT_MON','battery 100k/47k divider, ADC battery monitor'),
 ('CH7','TEMP_MON','NTC 10k/10k divider (pack temperature)'),
]
JACKS = [
 ('CV OUT 1', 'CVOUT1', 'MCP4728#1 CHA -> TL074 x4.883 -> 1k + BAT54S'),
 ('CV OUT 2', 'CVOUT2', 'MCP4728#1 CHB -> TL074 x4.883 -> 1k + BAT54S'),
 ('CV OUT 3', 'CVOUT3', 'MCP4728#1 CHC -> TL074 x4.883 -> 1k + BAT54S'),
 ('CV OUT 4', 'CVOUT4', 'MCP4728#1 CHD -> TL074 x4.883 -> 1k + BAT54S'),
 ('CV OUT 5', 'CVOUT5', 'MCP4728#2 CHA -> TL074 x4.883 -> 1k + BAT54S (rear)'),
 ('CV OUT 6', 'CVOUT6', 'MCP4728#2 CHB -> TL074 x4.883 -> 1k + BAT54S (rear)'),
 ('CV IN 1', 'CVIN1', '100k/16.5k + 1.65 V offset -> BAT54S -> 1k/100nF -> MCP3208 CH0'),
 ('CV IN 2', 'CVIN2', '100k/16.5k + 1.65 V offset -> BAT54S -> 1k/100nF -> MCP3208 CH1'),
 ('GATE OUT 1', 'GATE1', '2N7000 open-drain + 4.7k to +5V + 1k'),
 ('GATE OUT 2', 'GATE2', '2N7000 open-drain + 4.7k to +5V + 1k'),
 ('AUDIO IN L', 'AUDIN_L', '1k + BAT54S + 100pF -> 1uF -> PCM1808 VINL'),
 ('AUDIO IN R', 'AUDIN_R', '1k + BAT54S + 100pF -> 1uF -> PCM1808 VINR'),
 ('AUDIO OUT L', 'AUDOUT_L', 'PCM5102A OUTL -> 10uF -> TL072 buffer -> 100R'),
 ('AUDIO OUT R', 'AUDOUT_R', 'PCM5102A OUTR -> 10uF -> TL072 buffer -> 100R'),
 ('PHONES L/R', 'PHONES_L/R', 'TL072 buffer -> 100R (stereo jack, TB1)'),
 ('MIDI IN', 'MIDI_IN_T/R', '6N137 + 220R'),
 ('MIDI OUT', 'MIDI_OUT_T/R', '74HCT125 + 33R/220R'),
]
# display contract
DISPLAY = dict(interface='LCD_CAM parallel RGB565 (16-bit) + PCLK/DE/HSYNC/VSYNC',
               resolution='800x480', pins='20 GPIO', connector='J-LCD (FFC 40, 0.5 mm)',
               bl='LCD_BL PWM (LEDC) + driver on panel', disp='LCD_DISP power/enable')
AUDIO = dict(fs='48 kHz (44.1 kHz also supported by PLL)',
             mclk='12.288 MHz = 256 fs', bck='3.072 MHz = 64 fs', lrck='48 kHz',
             dac='PCM5102A, I2S, 24-bit, SCK = shared MCLK', dac_cfg='FMT=0 (I2S), DEMP=0, FLT=0, XSMT=1 (unmute via 10k PU)',
             adc='PCM1808, I2S slave, 24-bit, MD0=MD1=0 (slave, 256/384/512fs auto), FMT=0 (I2S)',
             adc_supply='VCC=5 V, VDD=3.3 V, VREF 0.1uF+10uF',
             mute='PCM5102A XSMT low at power-up (RC), unmuted by firmware after I2S clock lock; '
                  'PCM1808 clock-halt reset; DAC out muted by XSMT; relay not used')
USB = dict(device='USB 2.0 HS OTG, 480 Mbit/s, D+/D- dedicated PHY pins USB_DP/USB_DM',
           esd='USBLC6-2SC6', cc='5.1k UFP resistors (CC1/CC2)', diff='90 ohm differential pair, matched +-0.5 mm, GND guard',
           connector='USB-C 16P (USB 2.0 only)', power='VBUS -> BQ24074 charger input')
CV = dict(out_range='0..10.0 V (DAC 0..2.048 V x 4.883; implemented 4.9 with 39k/10k -> 10.04 V)',
          out_prot='1k series + BAT54S to AGND/+12V', out_cal='2-point calibration per channel in 24C32 EEPROM 0x57',
          in_range='-10..+10 V -> 0..3.3 V: Vadc = 1.65 - 0.165*Vin (100k/16.5k + 1.65 V offset)',
          in_prot='BAT54S to AGND/+3V3 after 1k, RC 1k/100nF at ADC')
