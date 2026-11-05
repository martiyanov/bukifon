# -*- coding: utf-8 -*-
"""Build script for the five Bukifon analog modules.

Every schematic is generated as a KiCad 9/10 .kicad_sch with embedded
library symbols, then checked with `kicad-cli sch erc`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kisch

FP = {
    'dip16': 'Package_DIP:DIP-16_W7.62mm',
    'dip14': 'Package_DIP:DIP-14_W7.62mm',
    'dip8': 'Package_DIP:DIP-8_W7.62mm',
    'dip18': 'Package_DIP:DIP-18_W7.62mm',
    'r': 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal',
    'c': 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm',
    'cp': 'Capacitor_THT:CP_Radial_D6.3mm_P2.50mm',
    'rv': 'Potentiometer_THT:Potentiometer_Alpha_RD901F-40-00D_Single_Vertical',
    'rvtrim': 'Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical',
    'idc26': 'Connector_IDC:IDC-Header_2x13_P2.54mm_Vertical',
    'hdr': 'Connector_PinHeader_2.54mm:PinHeader_1x13_P2.54mm_Vertical',
    'sw': '',
    'relay': 'Relay_THT:Relay_SPDT_Omron_G5V-1',
    'to92': 'Package_TO_SOT_THT:TO-92_Inline',
    'sot23': 'Package_TO_SOT_SMD:SOT-23',
    'soic8': 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    'sod323': 'Diode_SMD:D_SOD-323',
}


class Mod(object):
    COLS = 11
    X0 = 25.4
    Y0 = 38.1
    DX = 45.72
    DY = 52.07

    def __init__(self, title, paper="A2"):
        self.s = kisch.Schematic(title, paper=paper)
        self.title = title
        self.i = 0
        self.notes = []

    def add(self, lib, name, ref, value, unit=1, fp="", desc="", x=None, y=None,
            rot=0):
        if x is None:
            x = self.X0 + (self.i % self.COLS) * self.DX
            y = self.Y0 + (self.i // self.COLS) * self.DY
        self.i += 1
        self.s.place(lib, name, ref, value, x, y, unit=unit, rot=rot,
                     footprint=fp, description=desc)
        return (x, y)

    def pin(self, ref, pinmapping, length=2.54):
        for p, net in pinmapping.items():
            if net in ("+12V", "-12V", "+5V", "+3V3", "GND"):
                self.s.connect_power(ref, str(p), net, length)
            elif net == "NC":
                self.s.nc(ref, str(p))
            else:
                self.s.stub(ref, str(p), length=length, net=net)
        return self

    def nc_pins(self, ref, pins):
        for p in pins:
            self.s.nc(ref, str(p))
        return self

    def note(self, txt, dx=0.0, dy=0.0):
        """Free text placed in the sheet header area."""
        n = len(self.notes)
        x = 25.4 + dx
        y = 309.88 + n * 6.35 + dy
        self.s.text(txt, x, y, size=1.27)
        self.notes.append(txt)

    def save(self, path):
        return self.s.save(path)


# --------------------------------------------------------------------------
# bus connector helper: 26 pins of the Bukifon Bus
# --------------------------------------------------------------------------
BUS = {
    1: "+12V", 2: "GND", 3: "-12V", 4: "GND", 5: "+5V", 6: "GND",
    7: "+3V3", 8: "GND", 9: "CV1", 10: "GND", 11: "CV2", 12: "GND",
    13: "CV3", 14: "GND", 15: "CV4", 16: "GND", 17: "GATE1", 18: "GATE2",
    19: "AUD_IN", 20: "AUD_OUT", 21: "SDA", 22: "SCL", 23: "SCK",
    24: "MOSI", 25: "MISO", 26: "CS",
}


def bus(mod, ref="J1", used=None, unused_nc=True):
    """Place the 26 pin bus connector; `used` = dict of pin -> local net."""
    used = used or {}
    mod.add("Connector_Generic", "Conn_02x13_Odd_Even", ref, "Bukifon Bus 26 pin",
            fp=FP['idc26'], desc="Bukifon Bus IDC-26 (2x13)")
    m = {}
    for p, net in BUS.items():
        if p in used:
            m[p] = used[p]
        elif unused_nc:
            m[p] = "NC"
    mod.pin(ref, m, length=2.54)
    return mod


# --------------------------------------------------------------------------
# module 1: VCO-1
# --------------------------------------------------------------------------
def build_vco(outdir):
    m = Mod("MOD-VCO-1")
    s = m.s
    bus(m, used={1: "+12V", 2: "GND", 3: "-12V", 4: "GND", 5: "+5V", 6: "GND",
                 7: "+3V3", 8: "GND", 9: "CV1", 10: "GND", 11: "CV2",
                 17: "GATE1", 18: "GATE2", 20: "AUD_OUT",
                 21: "SDA", 22: "SCL"})

    # --- AS3340 core
    m.add("Audio", "AS3340", "U1", "AS3340", fp=FP['dip16'],
          desc="Alfa AS3340 VCO (CEM3340 clone)")
    m.pin("U1", {1: "SCALE1", 2: "SCALE2", 3: "-12V", 4: "PULSE",
                 5: "PWM_IN", 6: "SYNC_HARD", 7: "HF_TRIM", 8: "NC",
                 9: "SYNC_SOFT", 10: "NC", 11: "TCAP", 12: "GND",
                 13: "LINFM", 14: "SAW", 15: "VFCI", 16: "+12V"})

    # timing capacitor (C0G, 1 nF) + tempco / scale
    m.add("Device", "C", "C1", "1n C0G", fp=FP['c'], desc="VCO timing capacitor")
    m.pin("C1", {1: "TCAP", 2: "GND"})
    m.add("Device", "R", "RT1", "1k 3300ppm", fp=FP['r'],
          desc="Tempco 1k 3300ppm/K (pin1 -> -12V)")
    m.pin("RT1", {1: "SCALE1", 2: "-12V"})
    m.add("Device", "R_Potentiometer_Trim", "RV3", "20k scale trim",
          fp=FP['rvtrim'], desc="Exponential scale trim")
    m.pin("RV3", {1: "SCALE2", 2: "-12V", 3: "SCALE2"})
    m.add("Device", "R_Potentiometer_Trim", "RV4", "50k HF trim",
          fp=FP['rvtrim'], desc="High frequency tracking trim")
    m.pin("RV4", {1: "HF_TRIM", 2: "-12V", 3: "HF_TRIM"})

    # --- CV summing amplifier (TL074 A) : CV1 + CV2 + tune + octave
    m.add("Amplifier_Operational", "TL074", "U2", "TL074", unit=1,
          fp=FP['dip14'], desc="CV summing amp")
    m.pin("U2", {1: "VSUM", 2: "SUM_N", 3: "GND"}, length=2.54)
    m.add("Device", "R", "R1", "100k", fp=FP['r'], desc="CV1 input resistor")
    m.pin("R1", {1: "CV1", 2: "SUM_N"})
    m.add("Device", "R", "R2", "100k", fp=FP['r'], desc="CV2 input resistor")
    m.pin("R2", {1: "CV2", 2: "SUM_N"})
    m.add("Device", "R", "R3", "100k", fp=FP['r'], desc="Summing feedback")
    m.pin("R3", {1: "SUM_N", 2: "VSUM"})
    m.add("Amplifier_Operational", "TL072", "U5", "TL072", unit=1,
          fp=FP['dip8'], desc="inverter: CV polarity into VFCI")
    m.pin("U5", {1: "VSUM_NI", 2: "VSUM_INV", 3: "GND"})
    m.add("Amplifier_Operational", "TL072", "U5", "TL072", unit=3,
          fp=FP['dip8'], desc="TL072 supply")
    m.pin("U5", {4: "-12V", 8: "+12V"})
    m.add("Device", "R", "R3a", "100k", fp=FP['r'], desc="inverter input")
    m.pin("R3a", {1: "VSUM", 2: "VSUM_INV"})
    m.add("Device", "R", "R3b", "100k", fp=FP['r'], desc="inverter feedback")
    m.pin("R3b", {1: "VSUM_INV", 2: "VSUM_NI"})
    m.add("Device", "R", "R4", "100k", fp=FP['r'], desc="VSUM_NI -> VFCI (10 uA/V)")
    m.pin("R4", {1: "VSUM_NI", 2: "VFCI"})
    # tune pot: +1 V .. -1 V at the summing node, 0 V in the centre
    m.add("Device", "R_Potentiometer", "RV1", "10k tune", fp=FP['rv'],
          desc="Panel tune +/- 1 semitone..octave")
    m.pin("RV1", {1: "TUNE_A", 2: "TUNE_W", 3: "TUNE_B"})
    m.add("Device", "R", "R5", "100k", fp=FP['r'], desc="Tune wiper resistor")
    m.pin("R5", {1: "TUNE_W", 2: "SUM_N"})
    m.add("Device", "R", "R5a", "100k", fp=FP['r'], desc="Tune pot top")
    m.pin("R5a", {1: "+5V", 2: "TUNE_A"})
    m.add("Device", "R", "R5b", "100k", fp=FP['r'], desc="Tune pot bottom")
    m.pin("R5b", {1: "TUNE_B", 2: "GND"})

    # --- 1.000 V reference (TL431 + TL074 C/D buffers)
    m.add("Reference_Voltage", "TL431LP", "U3", "TL431", fp=FP['to92'],
          desc="2.495 V shunt reference")
    m.pin("U3", {1: "REF_K", 2: "GND", 3: "REF_K"})
    m.add("Device", "R", "R6", "1k", fp=FP['r'], desc="TL431 cathode resistor")
    m.pin("R6", {1: "+5V", 2: "REF_K"})
    m.add("Amplifier_Operational", "TL074", "U2", "TL074", unit=3,
          fp=FP['dip14'], desc="1.0 V reference buffer")
    m.pin("U2", {10: "REF25", 9: "REF1", 8: "REF1"})
    m.add("Device", "R", "R7", "20k 1%", fp=FP['r'], desc="divider 2.5V -> 1.0V")
    m.pin("R7", {1: "REF_K", 2: "REF25"})
    m.add("Device", "R", "R8", "30k 1%", fp=FP['r'], desc="divider 2.5V -> 1.0V")
    m.pin("R8", {1: "REF25", 2: "GND"})
    m.add("Device", "C", "C2", "100n", fp=FP['c'], desc="reference decoupling")
    m.pin("C2", {1: "REF_K", 2: "GND"})

    # --- octave switch: 1 / 2 / 3 octave offset from the 1.000 V reference
    m.add("Switch", "SW_SP3T", "SW1", "octave 1/2/3", fp=FP['sw'],
          desc="Octave range switch")
    m.pin("SW1", {1: "OCT_2X", 2: "OCT_1X", 3: "REF1", 4: "OCT_3X"})
    for ref, val in (("R9", "100k 0.1%"), ("R10", "49k9 0.1%"),
                     ("R11", "33k2 0.1%")):
        m.add("Device", "R", ref, val, fp=FP['r'], desc="octave offset resistor")
    m.pin("R9", {1: "OCT_1X", 2: "SUM_N"})
    m.pin("R10", {1: "OCT_2X", 2: "SUM_N"})
    m.pin("R11", {1: "OCT_3X", 2: "SUM_N"})

    # --- PWM
    m.add("Amplifier_Operational", "TL074", "U2", "TL074", unit=2,
          fp=FP['dip14'], desc="PWM comparator drive buffer")
    m.pin("U2", {5: "PWM_BUF", 6: "PWM_IN", 7: "PWM_IN"})
    m.add("Device", "R_Potentiometer", "RV2", "10k PWM depth", fp=FP['rv'],
          desc="Panel PWM depth (CV2 attenuator)")
    m.pin("RV2", {1: "CV2", 2: "CV2_ATT", 3: "GND"})
    m.add("Switch", "SW_SP3T", "SW3", "PWM src (ganged with SW2)", fp=FP['sw'],
          desc="Second pole of the waveform switch: PWM source")
    m.pin("SW3", {1: "GND", 2: "PWM_BUF", 3: "PWM_50", 4: "CV2_ATT"})
    m.add("Device", "R", "R12", "10k", fp=FP['r'], desc="PWM 50% divider top")
    m.pin("R12", {1: "+5V", 2: "PWM_50"})
    m.add("Device", "R", "R13", "10k", fp=FP['r'], desc="PWM 50% divider bottom")
    m.pin("R13", {1: "PWM_50", 2: "GND"})

    # --- waveform select
    m.add("Switch", "SW_SP3T", "SW2", "saw/sq/pulse", fp=FP['sw'],
          desc="Waveform selector")
    m.pin("SW2", {1: "SAW", 2: "WAVE", 3: "PULSE", 4: "PULSE"})

    m.add("Amplifier_Operational", "TL074", "U2", "TL074", unit=5,
          fp=FP['dip14'], desc="TL074 supply")
    m.pin("U2", {4: "+12V", 11: "-12V"})

    # --- output buffer : AC coupled, +/-5 V into 10 k load
    m.add("Amplifier_Operational", "TL074", "U2", "TL074", unit=4,
          fp=FP['dip14'], desc="Output buffer x1.25")
    m.pin("U2", {12: "WAVE", 13: "FB_OUT", 14: "OUT_RAW"})
    m.add("Device", "R", "R15", "10k", fp=FP['r'], desc="buffer feedback")
    m.pin("R15", {1: "OUT_RAW", 2: "FB_OUT"})
    m.add("Device", "R", "R16", "40k2", fp=FP['r'], desc="buffer gain resistor")
    m.pin("R16", {1: "FB_OUT", 2: "GND"})
    m.add("Device", "R_Potentiometer_Trim", "RV5", "10k output level",
          fp=FP['rvtrim'], desc="Output level trim to +/-5 V")
    m.pin("RV5", {1: "OUT_RAW", 2: "OUT_SET", 3: "FB_OUT"})
    m.add("Device", "C", "C3", "10uF", fp=FP['cp'], desc="AUD_OUT AC coupling")
    m.pin("C3", {1: "OUT_SET", 2: "AUD_OUT"})
    m.add("Device", "R", "R17", "100k", fp=FP['r'], desc="AUD_OUT DC return")
    m.pin("R17", {1: "AUD_OUT", 2: "GND"})
    m.add("Device", "R", "R18", "100R", fp=FP['r'], desc="AUD_OUT series")
    m.pin("R18", {1: "AUD_OUT", 2: "AUD_OUT"})
    # protection of CV inputs / audio out
    m.add("Diode", "BAT54S", "D1", "BAT54S", fp=FP['sod323'],
          desc="CV1 clamp to +12V/GND")
    m.pin("D1", {1: "GND", 2: "+12V", 3: "CV1"})
    m.add("Diode", "BAT54S", "D2", "BAT54S", fp=FP['sod323'],
          desc="CV2 clamp")
    m.pin("D2", {1: "GND", 2: "+12V", 3: "CV2"})
    m.add("Diode", "BAT54S", "D3", "BAT54S", fp=FP['sod323'],
          desc="AUD_OUT clamp")
    m.pin("D3", {1: "GND", 2: "+3V3", 3: "AUD_OUT"})
    m.add("Device", "R", "R19", "1k", fp=FP['r'], desc="CV1 series")
    m.pin("R19", {1: "CV1", 2: "CV1_PROT"})
    m.add("Device", "R", "R20", "1k", fp=FP['r'], desc="CV2 series")
    m.pin("R20", {1: "CV2", 2: "CV2_PROT"})
    m.add("Device", "R", "R21a", "100k", fp=FP['r'], desc="CV1 return")
    m.pin("R21a", {1: "CV1_PROT", 2: "GND"})
    m.add("Device", "R", "R21b", "100k", fp=FP['r'], desc="CV2 return")
    m.pin("R21b", {1: "CV2_PROT", 2: "GND"})

    # --- sync inputs
    m.add("Device", "R", "R21", "4k7", fp=FP['r'], desc="hard sync series")
    m.pin("R21", {1: "GATE1", 2: "SYNC_HARD"})
    m.add("Device", "R", "R22", "4k7", fp=FP['r'], desc="soft sync series")
    m.pin("R22", {1: "GATE2", 2: "SYNC_SOFT"})
    m.add("Device", "R", "R23", "100k", fp=FP['r'], desc="linear FM input")
    m.pin("R23", {1: "CV2", 2: "LINFM"})

    # --- EEPROM
    m.add("Memory_EEPROM", "24LC02", "U4", "24C02", fp=FP['dip8'],
          desc="Module descriptor EEPROM, addr 0x50+port")
    m.pin("U4", {1: "EE_A0", 2: "EE_A1", 3: "EE_A2", 4: "GND",
                 5: "SDA", 6: "SCL", 7: "GND", 8: "+3V3"})
    for ref in ("JP1", "JP2", "JP3"):
        m.add("Jumper", "Jumper_3_Open", ref, "addr", fp=FP['sod323'],
              desc="EEPROM address strap")
    m.pin("JP1", {1: "GND", 2: "EE_A0", 3: "+3V3"})
    m.pin("JP2", {1: "GND", 2: "EE_A1", 3: "+3V3"})
    m.pin("JP3", {1: "GND", 2: "EE_A2", 3: "+3V3"})
    m.add("Device", "C", "C4", "100n", fp=FP['c'], desc="EEPROM decoupling")
    m.pin("C4", {1: "+3V3", 2: "GND"})

    # --- power decoupling
    for ref, v1, v2, val in (("C5", "+12V", "GND", "10uF"),
                             ("C6", "-12V", "GND", "10uF"),
                             ("C7", "+12V", "GND", "100n"),
                             ("C8", "-12V", "GND", "100n"),
                             ("C9", "+5V", "GND", "100n"),
                             ("C10", "+3V3", "GND", "100n")):
        m.add("Device", "C", ref, val, fp=FP['cp' if val.startswith("10") else 'c'],
              desc="Rail decoupling")
        m.pin(ref, {1: v1, 2: v2})

    for net, at in (("+12V", (480.06, 330.2)), ("-12V", (480.06, 345.44)),
                    ("+5V", (480.06, 360.68)), ("+3V3", (480.06, 375.92)),
                    ("GND", (480.06, 391.16))):
        s.pwr_flag(net, *at)

    m.note("VCO-1 / MOD-VCO-1 : AS3340 (DIP-16), 1V/oct summing amp TL074, "
           "1.000V reference TL431.")
    m.note("Range: CV1/CV2 (bus, 0..10V). Waveform: saw / square / pulse. "
           "AUD_OUT = +/-5V AC, 10k load, see Calc.md for the CV->frequency table.")
    m.note("NOTE: CV3/CV4 are module->core in spec/20 §7, so the PWM input is "
           "taken from CV2/panel, not CV3.")
    return m.save(os.path.join(outdir, "MOD-VCO-1.kicad_sch"))


# --------------------------------------------------------------------------
# module 2: FILTER-1 (LM13700 SVF)
# --------------------------------------------------------------------------
def build_filter(outdir):
    m = Mod("MOD-FILTER-1")
    s = m.s
    bus(m, used={1: "+12V", 2: "GND", 3: "-12V", 4: "GND", 5: "+5V", 6: "GND",
                 7: "+3V3", 8: "GND", 9: "CV1", 10: "GND", 11: "CV2",
                 19: "AUD_IN", 20: "AUD_OUT", 21: "SDA", 22: "SCL"})

    m.add("Amplifier_Operational", "LM13700", "U1", "LM13700", unit=3,
          fp=FP['dip16'], desc="OTA A: integrator 1 (HP -> BP)")
    m.pin("U1", {1: "IABC", 2: "GND", 3: "HP", 4: "GND", 5: "INT1"})
    m.add("Amplifier_Operational", "LM13700", "U1", "LM13700", unit=1,
          fp=FP['dip16'], desc="OTA B: integrator 2 (BP -> LP)")
    m.pin("U1", {16: "IABC2", 15: "GND", 14: "BP", 13: "GND", 12: "INT2"})
    m.add("Amplifier_Operational", "LM13700", "U1", "LM13700", unit=5,
          fp=FP['dip16'], desc="LM13700 supply")
    m.pin("U1", {11: "+12V", 6: "-12V"})

    m.add("Amplifier_Operational", "TL074", "U2", "TL074", unit=1,
          fp=FP['dip14'], desc="Integrator 1")
    m.pin("U2", {2: "INT1", 3: "GND", 1: "BP"})
    m.add("Amplifier_Operational", "TL074", "U2", "TL074", unit=2,
          fp=FP['dip14'], desc="Integrator 2")
    m.pin("U2", {6: "INT2", 5: "GND", 7: "LP"})
    m.add("Amplifier_Operational", "TL074", "U2", "TL074", unit=3,
          fp=FP['dip14'], desc="Summing stage 1: -(IN + k*BP)")
    m.pin("U2", {10: "GND", 9: "S1", 8: "X1"})
    m.add("Amplifier_Operational", "TL074", "U2", "TL074", unit=4,
          fp=FP['dip14'], desc="Summing stage 2: HP = -(X1 + LP)")
    m.pin("U2", {12: "GND", 13: "S2", 14: "HP"})
    m.add("Amplifier_Operational", "TL074", "U2", "TL074", unit=5,
          fp=FP['dip14'], desc="TL074 supply")
    m.pin("U2", {4: "+12V", 11: "-12V"})
    for ref in ("C1", "C2"):
        m.add("Device", "C", ref, "1n C0G", fp=FP['c'], desc="integrator cap")
    m.pin("C1", {1: "INT1", 2: "BP"})
    m.pin("C2", {1: "INT2", 2: "LP"})
    m.add("Device", "R", "R1", "100k", fp=FP['r'], desc="audio input resistor")
    m.pin("R1", {1: "AUD_IN", 2: "S1"})
    m.add("Device", "R", "R2", "100k", fp=FP['r'], desc="stage 1 feedback")
    m.pin("R2", {1: "S1", 2: "X1"})
    m.add("Device", "R", "R3", "10k", fp=FP['r'], desc="BP into stage 1 (resonance)")
    m.pin("R3", {1: "RES_W", 2: "S1"})
    m.add("Device", "R", "R4", "100k", fp=FP['r'], desc="stage 2: X1 input")
    m.pin("R4", {1: "X1", 2: "S2"})
    m.add("Device", "R", "R5", "100k", fp=FP['r'], desc="stage 2: LP input")
    m.pin("R5", {1: "LP", 2: "S2"})
    m.add("Device", "R", "R17", "100k", fp=FP['r'], desc="stage 2 feedback")
    m.pin("R17", {1: "S2", 2: "HP"})
    m.add("Device", "R_Potentiometer", "RV1", "1M resonance", fp=FP['rv'],
          desc="Panel resonance")
    m.pin("RV1", {1: "RES_A", 2: "RES_W", 3: "GND"})
    m.add("Device", "R", "R6", "10k", fp=FP['r'], desc="resonance min")
    m.pin("R6", {1: "BP", 2: "RES_A"})
    m.add("Device", "R", "R7", "100k", fp=FP['r'], desc="resonance CV")
    m.pin("R7", {1: "CV2", 2: "RES_W"})
    m.add("Device", "C", "C11", "100p", fp=FP['c'], desc="resonance RC")
    m.pin("C11", {1: "RES_W", 2: "GND"})

    # exponential cutoff driver
    m.add("Amplifier_Operational", "TL072", "U3", "TL072", unit=1,
          fp=FP['dip8'], desc="CV summing amplifier")
    m.pin("U3", {2: "CVSUM", 3: "GND", 1: "CV_D"})
    m.add("Device", "R", "R9", "100k", fp=FP['r'], desc="CV1 input")
    m.pin("R9", {1: "CV1", 2: "CVSUM"})
    m.add("Device", "R", "R10", "100k", fp=FP['r'], desc="summing feedback")
    m.pin("R10", {1: "CVSUM", 2: "CV_D"})
    m.add("Device", "R_Potentiometer", "RV2", "100k cutoff", fp=FP['rv'],
          desc="Panel cutoff")
    m.pin("RV2", {1: "+5V", 2: "CVSUM_P", 3: "GND"})
    m.add("Device", "R", "R11", "100k", fp=FP['r'], desc="cutoff pot to summer")
    m.pin("R11", {1: "CVSUM_P", 2: "CVSUM"})

    m.add("Amplifier_Operational", "TL072", "U3", "TL072", unit=3,
          fp=FP['dip8'], desc="TL072 supply")
    m.pin("U3", {4: "-12V", 8: "+12V"})
    m.add("Amplifier_Operational", "TL072", "U3", "TL072", unit=2,
          fp=FP['dip8'], desc="Exponential converter servo")
    m.pin("U3", {5: "GND", 6: "EXPO_C", 7: "EXPO_E"})
    m.add("Transistor_BJT", "BC847BS", "Q2", "BC847BS", unit=1,
          fp=FP['sot23'], desc="expo pair Q1 (servo, base at GND)")
    m.pin("Q2", {1: "EXPO_E", 2: "GND", 6: "EXPO_C"})
    m.add("Transistor_BJT", "BC847BS", "Q2", "BC847BS", unit=2,
          fp=FP['sot23'], desc="expo pair Q2 (CV input)")
    m.pin("Q2", {3: "IABC", 4: "EXPO_E", 5: "EXPO_B"})
    m.add("Device", "R", "R12", "1k", fp=FP['r'], desc="expo tail")
    m.pin("R12", {1: "EXPO_E", 2: "-12V"})
    m.add("Device", "R", "R13", "470k", fp=FP['r'], desc="expo reference current 10.6 uA")
    m.pin("R13", {1: "+5V", 2: "EXPO_C"})
    m.add("Device", "R", "R18", "1k", fp=FP['r'], desc="expo 1V/oct divider top")
    m.pin("R18", {1: "CV_D", 2: "EXPO_B"})
    m.add("Device", "R", "R19", "56k", fp=FP['r'], desc="expo 1V/oct divider bottom")
    m.pin("R19", {1: "EXPO_B", 2: "GND"})
    m.add("Device", "C", "C3", "100p", fp=FP['c'], desc="expo servo stability")
    m.pin("C3", {1: "EXPO_C", 2: "EXPO_E"})
    m.add("Transistor_BJT", "BC847BS", "Q3", "BC847BS", unit=1,
          fp=FP['sot23'], desc="IABC current mirror (diode side)")
    m.pin("Q3", {1: "-12V", 2: "IABC", 6: "IABC"})
    m.add("Transistor_BJT", "BC847BS", "Q3", "BC847BS", unit=2,
          fp=FP['sot23'], desc="IABC current mirror (output)")
    m.pin("Q3", {3: "IABC2", 4: "-12V", 5: "IABC"})

    # output stage
    m.add("Switch", "SW_SP3T", "SW1", "LP/BP/HP", fp=FP['sw'],
          desc="Response selector")
    m.pin("SW1", {1: "LP", 2: "OUT_SEL", 3: "HP", 4: "BP"})
    m.add("Device", "C", "C4", "10uF", fp=FP['cp'], desc="output AC coupling")
    m.pin("C4", {1: "OUT_SEL", 2: "AUD_OUT"})
    m.add("Device", "R", "R14", "100k", fp=FP['r'], desc="AUD_OUT DC return")
    m.pin("R14", {1: "AUD_OUT", 2: "GND"})
    m.add("Device", "R", "R15", "100R", fp=FP['r'], desc="AUD_OUT series")
    m.pin("R15", {1: "AUD_OUT", 2: "AUD_OUT"})
    m.add("Diode", "BAT54S", "D1", "BAT54S", fp=FP['sod323'],
          desc="AUD_IN clamp")
    m.pin("D1", {1: "GND", 2: "+12V", 3: "AUD_IN"})
    m.add("Device", "R", "R16", "1k", fp=FP['r'], desc="AUD_IN series")
    m.pin("R16", {1: "AUD_IN", 2: "AUD_IN"})

    # EEPROM + decoupling
    m.add("Memory_EEPROM", "24LC02", "U4", "24C02", fp=FP['dip8'],
          desc="Module descriptor EEPROM 0x50+port")
    m.pin("U4", {1: "EE_A0", 2: "EE_A1", 3: "EE_A2", 4: "GND",
                 5: "SDA", 6: "SCL", 7: "GND", 8: "+3V3"})
    for ref in ("JP1", "JP2", "JP3"):
        m.add("Jumper", "Jumper_3_Open", ref, "addr", fp=FP['sod323'],
              desc="EEPROM address strap")
        m.pin(ref, {1: "GND", 2: "EE_A%d" % (int(ref[-1]) - 1), 3: "+3V3"})
    for ref, v1, val in (("C5", "+12V", "10uF"), ("C6", "-12V", "10uF"),
                         ("C7", "+12V", "100n"), ("C8", "-12V", "100n"),
                         ("C9", "+3V3", "100n"), ("C10", "+5V", "100n")):
        m.add("Device", "C", ref, val, fp=FP['cp' if val.startswith("10") else 'c'],
              desc="Rail decoupling")
        m.pin(ref, {1: v1, 2: "GND"})
    m.note("FILTER-1 : 12 dB/oct state variable filter, LM13700 OTA integrators "
           "+ TL074 opamp integrators.")
    m.note("Cutoff = gm/(2*pi*C) ; gm = 19.2 uA/V * Iabc. "
           "Cutoff CV on CV1, resonance on CV2 (CV3/CV4 are module->core).")
    m.note("Outputs: 12 dB/oct LP / BP / HP, +/-5V AC on AUD_OUT.")
    for net, at in (("+12V", (480.06, 330.2)), ("-12V", (480.06, 345.44)),
                    ("+5V", (480.06, 360.68)), ("+3V3", (480.06, 375.92)),
                    ("GND", (480.06, 391.16))):
        s.pwr_flag(net, *at)
    return m.save(os.path.join(outdir, "MOD-FILTER-1.kicad_sch"))


# --------------------------------------------------------------------------
# module 3: PROTO-1
# --------------------------------------------------------------------------
def build_proto(outdir):
    m = Mod("MOD-PROTO-1")
    s = m.s
    bus(m, used={1: "+12V", 2: "GND", 3: "-12V", 4: "GND", 5: "+5V", 6: "GND",
                 7: "+3V3", 8: "GND", 9: "CV1", 10: "GND", 11: "CV2",
                 13: "CV3", 14: "GND", 15: "CV4", 16: "GND", 17: "GATE1",
                 18: "GATE2", 19: "AUD_IN", 20: "AUD_OUT", 21: "SDA",
                 22: "SCL", 23: "SCK", 24: "MOSI", 25: "MISO", 26: "CS"})
    # two 2.54 mm comb strips, each bus signal twice
    m.add("Connector_Generic", "Conn_01x13", "J2", "comb A 1-13",
          fp=FP['hdr'], desc="2.54 mm comb, mirror of bus pins 1..13")
    m.pin("J2", {i: ("BUS%d" % i) for i in range(1, 14)})
    m.add("Connector_Generic", "Conn_01x13", "J3", "comb B 14-26",
          fp=FP['hdr'], desc="2.54 mm comb, mirror of bus pins 14..26")
    m.pin("J3", {i: ("BUS%d" % (i + 13)) for i in range(1, 14)})
    m.add("Connector_Generic", "Conn_01x13", "J4", "comb A' 1-13",
          fp=FP['hdr'], desc="second contact of each bus line")
    m.pin("J4", {i: ("BUS%d" % i) for i in range(1, 14)})
    m.add("Connector_Generic", "Conn_01x13", "J5", "comb B' 14-26",
          fp=FP['hdr'], desc="second contact of each bus line")
    m.pin("J5", {i: ("BUS%d" % (i + 13)) for i in range(1, 14)})
    # each BUSn is bridged to the real bus connector net through a 0R link
    busmap = {1: "+12V", 2: "GND", 3: "-12V", 4: "GND", 5: "+5V", 6: "GND",
              7: "+3V3", 8: "GND", 9: "CV1", 10: "GND", 11: "CV2",
              12: "GND", 13: "CV3", 14: "GND", 15: "CV4", 16: "GND",
              17: "GATE1", 18: "GATE2", 19: "AUD_IN", 20: "AUD_OUT",
              21: "SDA", 22: "SCL", 23: "SCK", 24: "MOSI", 25: "MISO",
              26: "CS"}
    # links: use 0R resistors so the comb can be isolated/probed
    for n in range(1, 27):
        ref = "R%d" % n
        m.add("Device", "R", ref, "0R", fp=FP['r'], desc="bus link")
        m.pin(ref, {1: "BUS%d" % n, 2: busmap[n]})
    # EEPROM descriptor
    m.add("Memory_EEPROM", "24LC02", "U1", "24C02", fp=FP['dip8'],
          desc="Module descriptor EEPROM 0x50+port")
    m.pin("U1", {1: "EE_A0", 2: "EE_A1", 3: "EE_A2", 4: "GND",
                 5: "SDA", 6: "SCL", 7: "GND", 8: "+3V3"})
    for ref in ("JP1", "JP2", "JP3"):
        m.add("Jumper", "Jumper_3_Open", ref, "addr", fp=FP['sod323'],
              desc="EEPROM address strap")
        m.pin(ref, {1: "GND", 2: "EE_A%d" % (int(ref[-1]) - 1), 3: "+3V3"})
    for ref, v1, val in (("C1", "+12V", "10uF"), ("C2", "-12V", "10uF"),
                         ("C3", "+5V", "100n"), ("C4", "+3V3", "100n"),
                         ("C5", "+12V", "100n"), ("C6", "-12V", "100n")):
        m.add("Device", "C", ref, val, fp=FP['cp' if val.startswith("10") else 'c'],
              desc="Rail decoupling")
        m.pin(ref, {1: v1, 2: "GND"})
    m.note("PROTO-1 : 60 x 45 mm 2.54 mm prototyping field (not drawn), all 26 "
           "bus lines on comb strips J2..J5, two contacts per line.")
    m.note("Each comb contact goes through a 0R link (R1..R26) to the bus: cut "
           "the link to isolate a line. Power rails are on the field edges.")
    m.note("EEPROM 24C02 descriptor: kind=0xFF (proto), same address scheme "
           "0x50 + port.")
    for net, at in (("+12V", (480.06, 330.2)), ("-12V", (480.06, 345.44)),
                    ("+5V", (480.06, 360.68)), ("+3V3", (480.06, 375.92)),
                    ("GND", (480.06, 391.16))):
        s.pwr_flag(net, *at)
    return m.save(os.path.join(outdir, "MOD-PROTO-1.kicad_sch"))


def main():
    out = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       '..'))
    args = sys.argv[1:] or ["vco", "filter", "proto", "ladder", "ensemble"]
    if "vco" in args:
        print(build_vco(out))
    if "filter" in args:
        print(build_filter(out))
    if "proto" in args:
        print(build_proto(out))
    if "ladder" in args:
        print(build_ladder(out))
    if "ensemble" in args:
        print(build_ensemble(out))


# --------------------------------------------------------------------------
# module 4: LADDER-1 (AS3320 / CEM3320 four pole ladder)
# --------------------------------------------------------------------------
def build_ladder(outdir):
    m = Mod("MOD-LADDER-1")
    s = m.s
    bus(m, used={1: "+12V", 2: "GND", 3: "-12V", 4: "GND", 5: "+5V", 6: "GND",
                 9: "CV1", 10: "GND", 11: "CV2", 12: "GND",
                 19: "AUD_IN", 20: "AUD_OUT", 21: "SDA", 22: "SCL"})

    m.add("Audio", "AS3320", "U1", "AS3320", fp=FP['dip18'],
          desc="Alfa AS3320 four pole VCF (CEM3320 clone)")
    m.pin("U1", {1: "LAD_IN", 2: "NC", 3: "GND", 4: "CAP2", 5: "CAP1",
                 6: "NC", 7: "NC", 8: "VRES", 9: "IRES", 10: "OUT4",
                 11: "CAP4", 12: "VCFI", 13: "-12V", 14: "+12V",
                 15: "NC", 16: "CAP3", 17: "NC", 18: "NC"})
    for i, (ref, net) in enumerate((("C1", "CAP1"), ("C2", "CAP2"),
                                    ("C3", "CAP3"), ("C4", "CAP4"))):
        m.add("Device", "C", ref, "1n C0G", fp=FP['c'], desc="ladder cap")
        m.pin(ref, {1: net, 2: "GND"})
    # input buffer + drive
    m.add("Amplifier_Operational", "TL074", "U2", "TL074", unit=1,
          fp=FP['dip14'], desc="input buffer")
    m.pin("U2", {1: "AUD_BUF", 2: "AUD_BUF", 3: "AUD_IN"})
    m.add("Device", "R", "R1", "100k", fp=FP['r'], desc="input load")
    m.pin("R1", {1: "AUD_IN", 2: "GND"})
    m.add("Device", "R_Potentiometer", "RV1", "100k drive", fp=FP['rv'],
          desc="Drive / saturation into the ladder")
    m.pin("RV1", {1: "AUD_BUF", 2: "DRIVE_W", 3: "GND"})
    m.add("Device", "R", "R2", "10k", fp=FP['r'], desc="input series into ladder")
    m.pin("R2", {1: "DRIVE_W", 2: "LAD_IN"})
    # cutoff: sum CV1 + panel pot -> VCFI (expo input, 1V/oct)
    m.add("Amplifier_Operational", "TL074", "U2", "TL074", unit=2,
          fp=FP['dip14'], desc="cutoff CV summing amp")
    m.pin("U2", {5: "GND", 6: "CUTSUM", 7: "CUT_D"})
    m.add("Device", "R", "R3", "100k", fp=FP['r'], desc="CV1 cutoff input")
    m.pin("R3", {1: "CV1", 2: "CUTSUM"})
    m.add("Device", "R", "R4", "100k", fp=FP['r'], desc="cutoff feedback")
    m.pin("R4", {1: "CUTSUM", 2: "CUT_D"})
    m.add("Device", "R_Potentiometer", "RV2", "100k cutoff", fp=FP['rv'],
          desc="Panel cutoff")
    m.pin("RV2", {1: "+5V", 2: "CUT_P", 3: "GND"})
    m.add("Device", "R", "R5", "100k", fp=FP['r'], desc="cutoff pot series")
    m.pin("R5", {1: "CUT_P", 2: "CUTSUM"})
    m.add("Amplifier_Operational", "TL074", "U2", "TL074", unit=4,
          fp=FP['dip14'], desc="inverter: cutoff polarity into VCFI")
    m.pin("U2", {12: "GND", 13: "CUT_INV", 14: "CUT_NI"})
    m.add("Device", "R", "R6a", "100k", fp=FP['r'], desc="cutoff inverter input")
    m.pin("R6a", {1: "CUT_D", 2: "CUT_INV"})
    m.add("Device", "R", "R6b", "100k", fp=FP['r'], desc="cutoff inverter feedback")
    m.pin("R6b", {1: "CUT_INV", 2: "CUT_NI"})
    m.add("Device", "R", "R6", "100k", fp=FP['r'], desc="VCFI input resistor")
    m.pin("R6", {1: "CUT_NI", 2: "VCFI"})
    # resonance
    m.add("Device", "R_Potentiometer", "RV3", "100k resonance", fp=FP['rv'],
          desc="Resonance (self oscillation at max)")
    m.pin("RV3", {1: "VRES", 2: "RES_W", 3: "GND"})
    m.add("Device", "R", "R7", "10k", fp=FP['r'], desc="IRES bias")
    m.pin("R7", {1: "IRES", 2: "-12V"})
    m.add("Device", "R", "R8", "100k", fp=FP['r'], desc="resonance CV")
    m.pin("R8", {1: "CV2", 2: "RES_W"})
    # HP = IN - LP4 (difference amplifier)
    m.add("Amplifier_Operational", "TL074", "U2", "TL074", unit=3,
          fp=FP['dip14'], desc="HP = IN - LP4")
    m.pin("U2", {8: "HP", 9: "IN_INV", 10: "LP4_DIV"})
    m.add("Device", "R", "R9", "100k", fp=FP['r'], desc="HP difference")
    m.pin("R9", {1: "AUD_BUF", 2: "IN_INV"})
    m.add("Device", "R", "R10", "100k", fp=FP['r'], desc="HP feedback")
    m.pin("R10", {1: "IN_INV", 2: "HP"})
    m.add("Device", "R", "R11", "100k", fp=FP['r'], desc="HP LP4 input")
    m.pin("R11", {1: "OUT4", 2: "LP4_DIV"})
    m.add("Device", "R", "R12", "100k", fp=FP['r'], desc="HP + input divider")
    m.pin("R12", {1: "LP4_DIV", 2: "GND"})
    # LP/HP switch + output buffer
    m.add("Switch", "SW_SPDT", "SW1", "LP/HP", fp=FP['sw'],
          desc="Response: 4-pole LP / 4-pole HP")
    m.pin("SW1", {1: "OUT4", 2: "OUT_SEL", 3: "HP"})
    m.add("Amplifier_Operational", "TL074", "U2", "TL074", unit=5,
          fp=FP['dip14'], desc="TL074 supply")
    m.pin("U2", {4: "+12V", 11: "-12V"})
    m.add("Device", "R", "R13", "100R", fp=FP['r'], desc="output series")
    m.pin("R13", {1: "OUT_SEL", 2: "AUD_OUT"})
    m.add("Device", "C", "C5", "10uF", fp=FP['cp'], desc="AUD_OUT AC coupling")
    m.pin("C5", {1: "OUT_SEL", 2: "AUD_OUT"})
    m.add("Device", "R", "R14", "100k", fp=FP['r'], desc="AUD_OUT DC return")
    m.pin("R14", {1: "AUD_OUT", 2: "GND"})
    m.add("Diode", "BAT54S", "D1", "BAT54S", fp=FP['sod323'], desc="AUD_IN clamp")
    m.pin("D1", {1: "GND", 2: "+12V", 3: "AUD_IN"})
    m.add("Diode", "BAT54S", "D2", "BAT54S", fp=FP['sod323'], desc="CV1 clamp")
    m.pin("D2", {1: "GND", 2: "+12V", 3: "CV1"})
    m.add("Diode", "BAT54S", "D3", "BAT54S", fp=FP['sod323'], desc="CV2 clamp")
    m.pin("D3", {1: "GND", 2: "+12V", 3: "CV2"})
    # EEPROM
    m.add("Memory_EEPROM", "24LC02", "U3", "24C02", fp=FP['dip8'],
          desc="Module descriptor, kind=7, addr 0x50+port")
    m.pin("U3", {1: "EE_A0", 2: "EE_A1", 3: "EE_A2", 4: "GND",
                 5: "SDA", 6: "SCL", 7: "GND", 8: "+3V3"})
    for ref in ("JP1", "JP2", "JP3"):
        m.add("Jumper", "Jumper_3_Open", ref, "addr", fp=FP['sod323'],
              desc="EEPROM address strap")
        m.pin(ref, {1: "GND", 2: "EE_A%d" % (int(ref[-1]) - 1), 3: "+3V3"})
    for ref, v1, val in (("C6", "+12V", "10uF"), ("C7", "-12V", "10uF"),
                         ("C8", "+12V", "100n"), ("C9", "-12V", "100n"),
                         ("C10", "+3V3", "100n"), ("C11", "+5V", "100n")):
        m.add("Device", "C", ref, val, fp=FP['cp' if val.startswith("10") else 'c'],
              desc="Rail decoupling")
        m.pin(ref, {1: v1, 2: "GND"})
    m.note("LADDER-1 : AS3320 four pole ladder VCF (CEM3320 pinout). "
           "4-pole LP / 4-pole HP, resonance up to self oscillation.")
    m.note("Cutoff CV on CV1 (1 V/oct, exponential input VCFI pin 12), "
           "resonance on CV2. Audio in AUD_IN, out AUD_OUT +/-5V AC.")
    m.note("Drive pot RV1 saturates the ladder input (Mug-style overdrive). "
           "Discrete BCM847 four-pole alternative: see availability.md.")
    for net, at in (("+12V", (480.06, 330.2)), ("-12V", (480.06, 345.44)),
                    ("+5V", (480.06, 360.68)), ("+3V3", (480.06, 375.92)),
                    ("GND", (480.06, 391.16))):
        s.pwr_flag(net, *at)
    return m.save(os.path.join(outdir, "MOD-LADDER-1.kicad_sch"))


# --------------------------------------------------------------------------
# module 5: ENSEMBLE-1 (simplified: 2 x PT2399, LFO, formant, bypass)
# --------------------------------------------------------------------------
def build_ensemble(outdir):
    m = Mod("MOD-ENSEMBLE-1")
    s = m.s
    bus(m, used={1: "+12V", 2: "GND", 3: "-12V", 4: "GND", 5: "+5V", 6: "GND",
                 9: "CV1", 10: "GND", 17: "GATE1", 19: "AUD_IN", 20: "AUD_OUT",
                 21: "SDA", 22: "SCL"})
    # two delay lines
    for k in (1, 2):
        m.add("Audio", "PT2399", "U%d" % k, "PT2399", fp=FP['dip16'],
              desc="Delay line %d (BBD replacement)" % k)
        m.pin("U%d" % k, {
            1: "+5V", 2: "REF%d" % k, 3: "GND", 4: "GND",
            5: "CLK%d" % k, 6: "VCO%d" % k, 7: "CC1_%d" % k, 8: "CC0_%d" % k,
            9: "OP1_%d" % k, 10: "OP1I_%d" % k, 11: "OP2I_%d" % k,
            12: "DEL%d" % k, 13: "LPF2I_%d" % k, 14: "LPF2_%d" % k,
            15: "LPF1_%d" % k, 16: "LPF1I_%d" % k})
        m.add("Device", "C", "C%d_a" % k, "100n", fp=FP['c'], desc="REF cap")
        m.pin("C%d_a" % k, {1: "REF%d" % k, 2: "GND"})
        m.add("Device", "C", "C%d_b" % k, "100p", fp=FP['c'], desc="clock cap")
        m.pin("C%d_b" % k, {1: "CLK%d" % k, 2: "GND"})
        m.add("Device", "C", "C%d_c" % k, "100n", fp=FP['c'], desc="CC cap")
        m.pin("C%d_c" % k, {1: "CC1_%d" % k, 2: "GND"})
        m.add("Device", "C", "C%d_d" % k, "100n", fp=FP['c'], desc="CC cap")
        m.pin("C%d_d" % k, {1: "CC0_%d" % k, 2: "GND"})
        m.add("Device", "C", "C%d_e" % k, "100n", fp=FP['c'], desc="LPF1 cap")
        m.pin("C%d_e" % k, {1: "LPF1I_%d" % k, 2: "GND"})
        m.add("Device", "R", "R%d_a" % k, "10k", fp=FP['r'], desc="input series")
        m.pin("R%d_a" % k, {1: "IN_D%d" % k, 2: "LPF1I_%d" % k})
        m.add("Device", "R", "R%d_b" % k, "10k", fp=FP['r'], desc="LPF1 -> LPF2")
        m.pin("R%d_b" % k, {1: "LPF1_%d" % k, 2: "LPF2I_%d" % k})
        m.add("Device", "R", "R%d_c" % k, "10k", fp=FP['r'], desc="LPF2 feedback")
        m.pin("R%d_c" % k, {1: "LPF2_%d" % k, 2: "LPF2I_%d" % k})
        m.add("Device", "R", "R%d_d" % k, "10k", fp=FP['r'], desc="delay CV")
        m.pin("R%d_d" % k, {1: "VCO%d" % k, 2: "GND"})
        m.add("Device", "R", "R%d_e" % k, "100k", fp=FP['r'], desc="LFO mod")
        m.pin("R%d_e" % k, {1: "LFO_TRI", 2: "VCO%d" % k})
        m.add("Device", "R", "R%d_f" % k, "10k", fp=FP['r'], desc="output series")
        m.pin("R%d_f" % k, {1: "DEL%d" % k, 2: "MIX_D%d" % k})
        m.add("Device", "R", "R%d_g" % k, "10k", fp=FP['r'], desc="op2 buffer")
        m.pin("R%d_g" % k, {1: "DEL%d" % k, 2: "OP2I_%d" % k})
        m.add("Device", "R", "R%d_h" % k, "10k", fp=FP['r'], desc="op1 bias")
        m.pin("R%d_h" % k, {1: "OP1_%d" % k, 2: "OP1I_%d" % k})
    # LFO (TL074 A/B)
    m.add("Amplifier_Operational", "TL074", "U3", "TL074", unit=1,
          fp=FP['dip14'], desc="LFO integrator")
    m.pin("U3", {1: "LFO_TRI", 2: "LFO_INV", 3: "GND"})
    m.add("Device", "C", "C1", "1uF", fp=FP['cp'], desc="LFO timing")
    m.pin("C1", {1: "LFO_INV", 2: "LFO_TRI"})
    m.add("Device", "R", "R1", "100k", fp=FP['r'], desc="LFO rate")
    m.pin("R1", {1: "LFO_SQ", 2: "LFO_INV"})
    m.add("Amplifier_Operational", "TL074", "U3", "TL074", unit=2,
          fp=FP['dip14'], desc="LFO comparator")
    m.pin("U3", {5: "LFO_TRI", 6: "GND", 7: "LFO_SQ"})
    m.add("Device", "R", "R2", "100k", fp=FP['r'], desc="comparator hysteresis")
    m.pin("R2", {1: "LFO_SQ", 2: "LFO_TRI"})
    m.add("Device", "R_Potentiometer", "RV1", "100k rate", fp=FP['rv'],
          desc="Ensemble rate")
    m.pin("RV1", {1: "CV1", 2: "RATE_W", 3: "GND"})
    m.add("Device", "R", "R3", "100k", fp=FP['r'], desc="rate into integrator")
    m.pin("R3", {1: "RATE_W", 2: "LFO_INV"})
    m.add("Amplifier_Operational", "TL074", "U3", "TL074", unit=3,
          fp=FP['dip14'], desc="dry/wet mixer")
    m.pin("U3", {8: "MIX_OUT", 9: "MIX_IN", 10: "MIX_IN"})
    m.add("Device", "R", "R4", "100k", fp=FP['r'], desc="dry input")
    m.pin("R4", {1: "IN_DRY", 2: "MIX_IN"})
    m.add("Device", "R", "R5", "100k", fp=FP['r'], desc="wet 1")
    m.pin("R5", {1: "MIX_D1", 2: "MIX_IN"})
    m.add("Device", "R", "R6", "100k", fp=FP['r'], desc="wet 2")
    m.pin("R6", {1: "MIX_D2", 2: "MIX_IN"})
    m.add("Device", "R", "R7", "100k", fp=FP['r'], desc="mixer feedback")
    m.pin("R7", {1: "MIX_IN", 2: "MIX_OUT"})
    # formant band
    m.add("Amplifier_Operational", "TL074", "U3", "TL074", unit=4,
          fp=FP['dip14'], desc="formant bandpass")
    m.pin("U3", {12: "FORM_N", 13: "FORM_N", 14: "FORM_OUT"})
    m.add("Device", "R", "R8", "10k", fp=FP['r'], desc="formant R1")
    m.pin("R8", {1: "MIX_OUT", 2: "FORM_X"})
    m.add("Device", "R", "R9", "10k", fp=FP['r'], desc="formant R2")
    m.pin("R9", {1: "FORM_N", 2: "FORM_X"})
    m.add("Device", "R", "R10", "10k", fp=FP['r'], desc="formant bias")
    m.pin("R10", {1: "FORM_N", 2: "GND"})
    m.add("Device", "C", "C2", "10n", fp=FP['c'], desc="formant C1")
    m.pin("C2", {1: "FORM_X", 2: "GND"})
    m.add("Device", "C", "C3", "10n", fp=FP['c'], desc="formant C2")
    m.pin("C3", {1: "FORM_X", 2: "FORM_OUT"})
    m.add("Amplifier_Operational", "TL074", "U3", "TL074", unit=5,
          fp=FP['dip14'], desc="TL074 supply")
    m.pin("U3", {4: "+12V", 11: "-12V"})
    # bypass switch
    m.add("Analog_Switch", "CD4053B", "U4", "CD4053", fp=FP['dip16'],
          desc="Bypass analogue switch (only section A used)")
    m.pin("U4", {14: "FX_OUT", 12: "FORM_OUT", 13: "MIX_OUT", 11: "BYPASS",
                 6: "GND", 16: "+12V", 7: "-12V", 8: "GND",
                 1: "NC", 2: "NC", 3: "NC", 4: "NC", 5: "NC",
                 9: "NC", 10: "NC", 15: "NC"})
    m.add("Device", "R", "R11", "10k", fp=FP['r'], desc="bypass control")
    m.pin("R11", {1: "GATE1", 2: "BYPASS"})
    m.add("Device", "R", "R12", "100k", fp=FP['r'], desc="bypass pull-down")
    m.pin("R12", {1: "BYPASS", 2: "GND"})
    m.add("Device", "R", "R13", "10k", fp=FP['r'], desc="input series")
    m.pin("R13", {1: "AUD_IN", 2: "IN_DRY"})
    m.add("Device", "C", "C4", "10uF", fp=FP['cp'], desc="input AC coupling")
    m.pin("C4", {1: "IN_DRY", 2: "IN_D1"})
    m.add("Device", "C", "C5", "10uF", fp=FP['cp'], desc="line 2 coupling")
    m.pin("C5", {1: "IN_DRY", 2: "IN_D2"})
    m.add("Device", "R", "R14", "100k", fp=FP['r'], desc="AUD_OUT return")
    m.pin("R14", {1: "AUD_OUT", 2: "GND"})
    m.add("Device", "R", "R15", "100R", fp=FP['r'], desc="AUD_OUT series")
    m.pin("R15", {1: "FX_OUT", 2: "AUD_OUT"})
    m.add("Device", "C", "C6", "10uF", fp=FP['cp'], desc="AUD_OUT coupling")
    m.pin("C6", {1: "FX_OUT", 2: "AUD_OUT"})
    # EEPROM
    m.add("Memory_EEPROM", "24LC02", "U5", "24C02", fp=FP['dip8'],
          desc="Module descriptor, kind=8, addr 0x50+port")
    m.pin("U5", {1: "EE_A0", 2: "EE_A1", 3: "EE_A2", 4: "GND",
                 5: "SDA", 6: "SCL", 7: "GND", 8: "+3V3"})
    for ref in ("JP1", "JP2", "JP3"):
        m.add("Jumper", "Jumper_3_Open", ref, "addr", fp=FP['sod323'],
              desc="EEPROM address strap")
        m.pin(ref, {1: "GND", 2: "EE_A%d" % (int(ref[-1]) - 1), 3: "+3V3"})
    for ref, v1, val in (("C7", "+12V", "10uF"), ("C8", "-12V", "10uF"),
                         ("C9", "+5V", "100n"), ("C10", "+3V3", "100n")):
        m.add("Device", "C", ref, val, fp=FP['cp' if val.startswith("10") else 'c'],
              desc="Rail decoupling")
        m.pin(ref, {1: v1, 2: "GND"})
    m.note("ENSEMBLE-1 (simplified v0.9): 2 x PT2399 modulated delay lines, "
           "triangle LFO (TL074), formant bandpass, CD4053 bypass.")
    m.note("BBD variant (2 x MN3207 + 2 x MN3102 + compander) is documented in "
           "availability.md; not drawn here. PT2399 flavour is brighter/noisier.")
    m.note("Rate: panel RV1 or CV1. Bypass: GATE1. EEPROM kind=8.")
    for net, at in (("+12V", (480.06, 330.2)), ("-12V", (480.06, 345.44)),
                    ("+5V", (480.06, 360.68)), ("+3V3", (480.06, 375.92)),
                    ("GND", (480.06, 391.16))):
        s.pwr_flag(net, *at)
    return m.save(os.path.join(outdir, "MOD-ENSEMBLE-1.kicad_sch"))


def main2():
    out = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       '..'))
    print(build_ladder(out))
    print(build_ensemble(out))

if __name__ == "__main__":
    main()
