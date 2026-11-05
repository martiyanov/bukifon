#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify the exported KiCad netlists of PANEL-1 / DECK-PAD / DECK-KEYS.

Two independent checks are performed on the netlist that KiCad itself produced from
the generated schematics:

  1. schematic <-> design intent: the pin->net mapping in the netlist must be exactly
     the mapping recorded by tools/gen.py (tools/netlist-intent.json). This catches
     wrong symbol pin offsets, misplaced labels, shorted/duplicated coordinates and
     accidentally merged nets.
  2. published tables <-> netlist: the tables in ../matrix-tables.md (74HC165 bit map,
     DECK-PAD 3x6 matrix, DECK-KEYS 6x7 matrix, LED chains, DECK_ID dividers) are
     parsed from the markdown file and asserted against the netlist. This catches
     documentation drift.

Usage: python3 tools/verify_netlist.py   (exit code 0 = all checks passed)
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PANEL_DIR = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from kicad_sch import parse, find_all  # noqa: E402

FAILS = []
NCHK = [0]


def is_nc(net):
    """KiCad names single-pin nets 'unconnected-(REF-PIN-PadN)'."""
    return net is None or net.startswith('unconnected-(')


def check(cond, msg):
    NCHK[0] += 1
    if not cond:
        FAILS.append(msg)


def load_netlist(path):
    """Return ({netname: {(ref,pin)}}, {(ref,pin): netname}, {ref: value})."""
    with open(path, encoding='utf-8') as f:
        tree = parse(f.read())
    nets, pin2net, values = {}, {}, {}
    for comp in find_all(tree, 'comp'):
        ref = val = None
        for ch in comp:
            if isinstance(ch, list) and ch and ch[0] == 'ref':
                ref = ch[1]
            if isinstance(ch, list) and ch and ch[0] == 'value':
                val = ch[1]
        if ref:
            values[ref] = val
    for net in find_all(tree, 'net'):
        name = None
        nodes = []
        for ch in net:
            if isinstance(ch, list) and ch and ch[0] == 'name':
                name = ch[1]
            if isinstance(ch, list) and ch and ch[0] == 'node':
                ref = [c[1] for c in ch if isinstance(c, list) and c[0] == 'ref'][0]
                pin = [c[1] for c in ch if isinstance(c, list) and c[0] == 'pin'][0]
                nodes.append((ref, pin))
        clean = name.split('/')[-1] if name.startswith('/') else name
        nodes = [n for n in nodes if not n[0].startswith('#')]
        nets.setdefault(clean, set()).update(nodes)
        for ref, pin in nodes:
            pin2net[(ref, pin)] = clean
    return nets, pin2net, values


def parse_md_tables(md_path):
    """Parse the machine-checkable rows of matrix-tables.md, section by section."""
    txt = open(md_path, encoding='utf-8').read()
    sections, cur = {}, None
    for line in txt.splitlines():
        if line.startswith('#'):
            cur = line.strip()
            sections[cur] = []
        elif cur is not None:
            sections[cur].append(line)
    out = dict(hc_bits=[], pads=[], keys=[], leds=[], panel_leds=[], deckpins={})
    for name, lines in sections.items():
        for line in lines:
            if not line.startswith('|'):
                continue
            if '74HC165' in name:
                # | 24 | U4 | D0 | `BTN_L1` | плечевая L1 ... |
                m = re.match(r'^\|\s*(\d+)\s*\|\s*U(\d)\s*\|\s*D(\d)\s*\|\s*`([^`]+)`', line)
                if m:
                    out['hc_bits'].append((int(m.group(1)), int(m.group(2)),
                                           int(m.group(3)), m.group(4)))
            elif 'DECK-PAD' in name and 'матрица' in name:
                m = re.match(r'^\|\s*PAD(\d+)\s*\|\s*(\d)\s*\|\s*(\d)\s*\|'
                             r'\s*[\d.]+\s*\|\s*[\d.]+\s*\|\s*`([^`]+)`.*?\|\s*`([^`]+)`', line)
                if m:
                    out['pads'].append((int(m.group(1)), int(m.group(2)), int(m.group(3)),
                                        m.group(4), m.group(5)))
            elif 'DECK-KEYS' in name and 'матрица' in name:
                m = re.match(r'^\|\s*KEY(\d+)\s*\|\s*(\d)\s*\|\s*(\d)\s*\|'
                             r'\s*[\d.]+\s*\|\s*[\d.]+\s*\|.*?`([^`]+)`', line)
                if m:
                    out['keys'].append((int(m.group(1)), int(m.group(2)), int(m.group(3)),
                                        m.group(4)))
            elif '2.5' in name and 'J-DECK' in name:
                # | 1 | `+3V3` | 2 | `GND` |
                m = re.match(r'^\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\|\s*`([^`]+)`', line)
                if m:
                    out['deckpins'][m.group(1)] = m.group(2)
                    out['deckpins'][m.group(3)] = m.group(4)
            elif 'LED' in name and ('цепочка' in name or 'chain' in name):
                # | 1 | `LED_IN` | `LED_CH1` | KEY1 | 11 | 72 |
                m = re.match(r'^\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|', line)
                if m:
                    out['leds'].append((int(m.group(1)), m.group(2), m.group(3)))
                # | 1 | LED_ENC1 | `LED_IN` | `LED_CHAIN1` |
                m = re.match(r'^\|\s*(\d+)\s*\|\s*(LED_\w+)\s*\|\s*`([^`]+)`\s*\|'
                             r'\s*`([^`]+)`\s*\|', line)
                if m:
                    out['panel_leds'].append((int(m.group(1)), m.group(2),
                                              m.group(3), m.group(4)))
    return out


def verify_intent(slug, nets, pin2net):
    intent = json.load(open(os.path.join(HERE, 'netlist-intent.json'), encoding='utf-8'))[slug]
    want = {}
    for ref, num, name, net in intent:
        key = (ref, str(num))
        if net is None:
            want[key] = None
        else:
            if key in want and want[key] != net:
                check(False, '%s: conflicting intent for %s.%s (%r vs %r)'
                      % (slug, ref, num, want[key], net))
            want[key] = net
    for key, net in want.items():
        if net is None:
            check(is_nc(pin2net.get(key)), '%s: %s.%s must be no-connect, but is on net %r'
                  % (slug, key[0], key[1], pin2net.get(key)))
        else:
            check(pin2net.get(key) == net, '%s: %s.%s on net %r, intended %r'
                  % (slug, key[0], key[1], pin2net.get(key), net))
    for key, net in pin2net.items():
        if is_nc(net):
            continue        # KiCad always lists unconnected pins as single-pin nets
        check(key in want, '%s: unexpected connected pin %s.%s (net %r)'
              % (slug, key[0], key[1], net))
    # (ref, pin name) -> pin number, so documentation checks can address pins by name
    namemap = {(ref, name): str(num) for ref, num, name, net in intent}
    return want, intent, namemap


def verify_docs(slug, tables, pin2net, values, namemap):
    md = os.path.join(PANEL_DIR, 'matrix-tables.md')
    t = parse_md_tables(md)
    check(len(t['hc_bits']) == 48, 'matrix-tables.md: 48 rows in the 74HC165 bit table, got %d'
          % len(t['hc_bits']))
    if slug == 'panel-1':
        for bit, stage, dj, net in t['hc_bits']:
            ref = 'U%d' % stage
            pin = namemap[(ref, 'D%d' % dj)]
            check(pin2net.get((ref, pin)) == net,
                  'doc PANEL-1: bit %d (%s.D%d) netlist %r, table says %r'
                  % (bit, ref, dj, pin2net.get((ref, pin)), net))
    check(len(t['pads']) == 18, 'matrix-tables.md: 18 DECK-PAD rows, got %d' % len(t['pads']))
    if slug == 'deck-pad':
        for n, row, col, rownet, colnet in t['pads']:
            check(pin2net.get(('PAD%d' % n, '1')) == rownet,
                  'doc DECK-PAD: PAD%d.1 = %r, table row net %r'
                  % (n, pin2net.get(('PAD%d' % n, '1')), rownet))
            check(pin2net.get(('PAD%d' % n, '2')) == colnet,
                  'doc DECK-PAD: PAD%d.2 = %r, table col net %r'
                  % (n, pin2net.get(('PAD%d' % n, '2')), colnet))
        check(values.get('R10') == '33k' and values.get('R11') == '3.3k',
              'doc DECK-PAD: DECK_ID divider must be 33k/3.3k, got %r/%r'
              % (values.get('R10'), values.get('R11')))
    check(len(t['keys']) == 42, 'matrix-tables.md: 42 DECK-KEYS rows, got %d' % len(t['keys']))
    if slug == 'deck-keys':
        for n, row, col, colnet in t['keys']:
            check(pin2net.get(('KEY%d' % n, '1')) == 'ROW%d' % row,
                  'doc DECK-KEYS: KEY%d row net %r' % (n, pin2net.get(('KEY%d' % n, '1'))))
            check(pin2net.get(('D%d' % n, '1')) == colnet,
                  'doc DECK-KEYS: D%d cathode %r, table %r'
                  % (n, pin2net.get(('D%d' % n, '1')), colnet))
        check(values.get('R4') == '3.3k' and values.get('R5') == '33k',
              'doc DECK-KEYS: DECK_ID divider must be 3.3k/33k, got %r/%r'
              % (values.get('R4'), values.get('R5')))
        check(len(t['leds']) == 42, 'matrix-tables.md: 42 rows in the DECK-KEYS LED chain, got %d'
              % len(t['leds']))
        for idx, din, dout in t['leds']:
            ref = 'LED_KEY%d' % idx
            pdin, pdout = namemap[(ref, 'DIN')], namemap[(ref, 'DOUT')]
            check(pin2net.get((ref, pdin)) == din, 'doc: %s DIN %r' % (ref, pin2net.get((ref, pdin))))
            if idx < 42:
                check(pin2net.get((ref, pdout)) == dout,
                      'doc: %s DOUT %r, table %r' % (ref, pin2net.get((ref, pdout)), dout))
    if slug == 'panel-1':
        check(len(t['deckpins']) == 16, 'matrix-tables.md: 16 J-DECK pins documented, got %d'
              % len(t['deckpins']))
        for pin, want in sorted(t['deckpins'].items(), key=lambda kv: int(kv[0])):
            check(pin2net.get(('J-DECK', pin)) == want,
                  'doc PANEL-1: J-DECK.%s netlist %r, table %r'
                  % (pin, pin2net.get(('J-DECK', pin)), want))
        check(len(t['panel_leds']) == 9,
              'matrix-tables.md: 9 rows in the PANEL-1 LED chain, got %d' % len(t['panel_leds']))
        for idx, ref, din, dout in t['panel_leds']:
            pdin, pdout = namemap[(ref, 'DIN')], namemap[(ref, 'DOUT')]
            check(pin2net.get((ref, pdin)) == din, 'doc: %s DIN %r' % (ref, pin2net.get((ref, pdin))))
            check(pin2net.get((ref, pdout)) == dout, 'doc: %s DOUT %r' % (ref, pin2net.get((ref, pdout))))




# --------------------------------------------------------------------------
# spec/20-electronics.md  <->  netlists (independent of the generator tables)
# --------------------------------------------------------------------------
def _spec_text():
    return open(os.path.abspath(os.path.join(PANEL_DIR, '..', '..', 'spec',
                                             '20-electronics.md')), encoding='utf-8').read()


def verify_spec():
    spec = _spec_text()

    # ---- spec 6.1: 74HC165 bit map ("0..15 encoders A/B, 16..23 encoder push,
    #      24..27 BTN_L1/L2/R1/R2, 28..47 reserved")
    p = os.path.join(PANEL_DIR, 'panel-1', 'panel-1.net')
    nets, pin2net, values = load_netlist(p)
    intent = json.load(open(os.path.join(HERE, 'netlist-intent.json'), encoding='utf-8'))['panel-1']
    namemap = {(ref, name): str(num) for ref, num, name, net in intent}
    bitnames = {}
    for bit in range(48):
        ref = 'U%d' % (bit // 8 + 1)
        pin = namemap[(ref, 'D%d' % (bit % 8))]
        bitnames[bit] = pin2net.get((ref, pin))
    want = {}
    for i in range(1, 9):
        want[(i - 1) * 2] = 'ENC%d_A' % i
        want[(i - 1) * 2 + 1] = 'ENC%d_B' % i
        want[16 + i - 1] = 'ENC%d_PUSH' % i
    want.update({24: 'BTN_L1', 25: 'BTN_L2', 26: 'BTN_R1', 27: 'BTN_R2'})
    for bit in range(48):
        exp = want.get(bit, 'GND')
        check(bitnames[bit] == exp, 'spec 6.1: bit %d net %r, expected %r'
              % (bit, bitnames[bit], exp))
    check(nets.get('HC_CP') and nets.get('HC_PL') and nets.get('HC_QH'),
          'spec 6.1: HC_CP / HC_PL / HC_QH nets exist')
    n165 = [r for r, v in values.items() if v == '74HC165']
    check(len(n165) == 6, 'spec 6.1: 6 x 74HC165 (got %d: %r)' % (len(n165), sorted(n165)))
    # spec 6.1/2: LED chain of PANEL-1 runs from +5V through the 74HCT1G125 buffer
    nbuf = [r for r, v in values.items() if v == '74HCT1G125']
    check(len(nbuf) == 1, 'spec 6.1: one 74HCT1G125 LED_DATA buffer (got %r)' % (nbuf,))
    if nbuf:
        ub = nbuf[0]
        bmap = {(r, nm): num for r, num, nm, net in intent}
        check(pin2net.get((ub, bmap[(ub, 'VCC')])) == '+5V',
              'spec 6.1: LED buffer VCC = +5V')
        check(pin2net.get(('LED_ENC1', '4')) == '+5V', 'spec 6.1: LED chain on +5V')
    for ref in ('LED_ENC1', 'LED_STATUS'):
        check(pin2net.get((ref, '4')) == '+5V', 'spec 3: %s on +5V rail' % ref)

    # ---- spec 6.2: deck IDC-16 pinout table
    m = re.search(r'### 6\.2.*?(?=### 6\.3)', spec, re.S)
    check(m is not None, 'spec 6.2 section found')
    deck = {}
    for mm in re.finditer(r'^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|',
                          m.group(0), re.M):
        deck[mm.group(1)] = mm.group(2).strip()
        deck[mm.group(3)] = mm.group(4).strip()
    check(len(deck) == 16, 'spec 6.2: 16 pins parsed (got %d)' % len(deck))
    spec_to_net = {'3V3': '+3V3', 'GND': 'GND', 'SDA': 'SDA', 'SCL': 'SCL',
                   'INT': 'DECK_INT', 'LED_IN': 'LED_IN',
                   'SL1': 'SL1_RAW', 'SL2': 'SL2_RAW', 'DECK_ID': 'DECK_ID',
                   'FSR': 'FSR', '+5V': '+5V'}

    def _norm(sig):
        # "SDA (I2C0)" -> "SDA", "**+5V** (питание ...)" -> "+5V"
        sig = sig.replace('*', '')
        return sig.split('(')[0].strip()
    for slug, special in (('panel-1', {'7': 'LED_OUT', '15': 'FSR_RAW'}),
                          ('deck-pad', {'15': 'FSR'}),
                          ('deck-keys', {'15': 'GND'})):
        net = os.path.join(PANEL_DIR, slug, slug + '.net')
        _, pin2net, _ = load_netlist(net)
        for pin, sig in deck.items():
            exp = special.get(pin) or spec_to_net.get(_norm(sig))
            got = pin2net.get(('J-DECK', pin))
            if exp is None:
                continue
            check(got == exp, 'spec 6.2: %s J-DECK.%s (%r) net %r, expected %r'
                  % (slug, pin, sig, got, exp))
        # pin 16 is the +5V LED-chain feed on every board (spec 6.2)
        check(pin2net.get(('J-DECK', '16')) == '+5V',
              'spec 6.2: %s J-DECK.16 must be +5V' % slug)

    # ---- spec 6.3/6.4: LED counts and matrix sizes
    all_intent = json.load(open(os.path.join(HERE, 'netlist-intent.json'), encoding='utf-8'))
    for slug, nl, nm in (('panel-1', 9, 0), ('deck-pad', 18, 3), ('deck-keys', 42, 6)):
        net = os.path.join(PANEL_DIR, slug, slug + '.net')
        nets, pin2net, values = load_netlist(net)
        nms = {(r, n): str(num) for r, num, n, netn in all_intent[slug]}
        if slug == 'panel-1':
            leds = [r for r in values if r.startswith('LED_')]
            check(len(leds) == 9, 'spec 6.1: 9 LEDs on PANEL-1 (got %d)' % len(leds))
            prefixes = ('LED_ENC', 'LED_STATUS')
        else:
            pre = 'LED_PAD' if slug == 'deck-pad' else 'LED_KEY'
            leds = [r for r in values if r.startswith(pre)]
            check(len(leds) == nl, 'spec: %d LEDs on %s (got %d)' % (nl, slug, len(leds)))
            prefixes = (pre,)
        for ref in leds:
            vdd = pin2net.get((ref, nms.get((ref, 'VDD'), '4')))
            check(vdd == '+5V', 'spec 3: %s VDD = %r, must be +5V' % (ref, vdd))
        if nm:
            rows = set()
            for ref in values:
                if ref.startswith('PAD') or ref.startswith('KEY'):
                    name = pin2net.get((ref, '1'))
                    if name and name.startswith('ROW'):
                        rows.add(name)
            check(len(rows) == nm, 'spec: %d matrix rows on %s (got %d: %r)'
                  % (nm, slug, len(rows), sorted(rows)))
        # MCP23017 present at 0x20 (A0..A2 to GND) for the decks
        if slug != 'panel-1':
            check(pin2net.get(('U1', '15')) == 'GND' and pin2net.get(('U1', '16')) == 'GND'
                  and pin2net.get(('U1', '17')) == 'GND',
                  'spec 6.2: %s MCP23017 A0..A2 = GND -> address 0x20' % slug)
            check(pin2net.get(('U1', '20')) == 'DECK_INT', 'spec: %s INTA -> DECK_INT' % slug)
        # two 30 mm faders with 3.3 V reference, 10k (decks only)
        for n in ((1, 2) if slug != 'panel-1' else ()):
            check(values.get('SL%d' % n) == 'POT30', 'spec: %s SL%d present' % (slug, n))
            if slug == 'deck-pad':
                check(pin2net.get(('SL%d' % n, '1')) == '+3V3',
                      'spec 6.3: SL%d across 3.3 V' % n)

    # ---- spec 6.2: DECK_ID dividers (4.7k/33k and 33k/4.7k)
    _, pad_vals, _ = (None, load_netlist(os.path.join(PANEL_DIR, 'deck-pad', 'deck-pad.net'))[2], None)
    _, key_vals, _ = (None, load_netlist(os.path.join(PANEL_DIR, 'deck-keys', 'deck-keys.net'))[2], None)
    check(pad_vals.get('R10') == '33k' and pad_vals.get('R11') == '3.3k',
          'spec 6.2: DECK-PAD divider must be 33k/3.3k (got %r/%r)'
          % (pad_vals.get('R10'), pad_vals.get('R11')))
    check(key_vals.get('R4') == '3.3k' and key_vals.get('R5') == '33k',
          'spec 6.2: DECK-KEYS divider must be 3.3k/33k (got %r/%r)'
          % (key_vals.get('R4'), key_vals.get('R5')))


# --------------------------------------------------------------------------
# coords-panel.csv  <->  spec/10-panel-ui.md (independent transcription check)
# --------------------------------------------------------------------------
def _nums(txt):
    return [float(m.group(0)) for m in re.finditer(r'-?\d+(?:\.\d+)?', txt.replace('*', ''))]


def verify_coords():
    csv_path = os.path.join(PANEL_DIR, 'coords-panel.csv')
    spec_path = os.path.abspath(os.path.join(PANEL_DIR, '..', '..', 'spec', '10-panel-ui.md'))
    got = {}
    for line in open(csv_path, encoding='utf-8').read().splitlines()[1:]:
        f = line.split(';')
        if len(f) >= 4:
            got[(f[0], f[1])] = (float(f[2]), float(f[3]))
    txt = open(spec_path, encoding='utf-8').read()

    for m in re.finditer(r'^\|\s*ENC(\d)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|', txt, re.M):
        key = ('panel', 'ENC%s' % m.group(1))
        check(got.get(key) == (float(m.group(2)), float(m.group(3))),
              'coords: %s = %r, spec says %s/%s'
              % (key[1], got.get(key), m.group(2), m.group(3)))
    for m in re.finditer(r'^\|\s*(L1|L2|R1|R2)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|', txt, re.M):
        key = ('panel', 'BTN_%s' % m.group(1))
        check(got.get(key) == (float(m.group(2)), float(m.group(3))),
              'coords: %s = %r, spec says %s/%s'
              % (key[1], got.get(key), m.group(2), m.group(3)))
    check(got.get(('panel', 'J-LCD')) == (157.5, 37.0),
          'coords: screen centre = %r, spec 157.5/37.0' % (got.get(('panel', 'J-LCD')),))

    for group, first in (('LEFT', 1), ('RIGHT', 10)):
        m = re.search(r'^\|\s*%s\s*\|\s*([\d,\s]+)\s*\|\s*([\d,\s]+)\s*\|\s*PAD(\d+)'
                      % group, txt, re.M)
        check(m is not None, 'spec 3.1: %s pad group row found' % group)
        if not m:
            continue
        want = set((round(x, 1), round(y, 1)) for x in _nums(m.group(1)) for y in _nums(m.group(2)))
        have = set()
        for n in range(first, first + 9):
            key = ('deck-pad', 'PAD%d' % n)
            if key in got:
                have.add((round(got[key][0], 1), round(got[key][1], 1)))
        check(have == want, 'coords: DECK-PAD %s pads differ: missing %r, extra %r'
              % (group, sorted(want - have), sorted(have - want)))

    for m in re.finditer(r'^\|\s*SL(\d)\s*\|\s*([\d.]+)\s*\|\s*(\d+)…(\d+)\s*\|', txt, re.M):
        n = m.group(1)
        x = float(m.group(2))
        ycen = (float(m.group(3)) + float(m.group(4))) / 2.0
        for board in ('deck-pad', 'deck-keys'):
            check(got.get((board, 'SL%s' % n)) == (x, ycen),
                  'coords: %s SL%s = %r, spec says %s/%s (centre of travel)'
                  % (board, n, got.get((board, 'SL%s' % n)), x, ycen))

    halves = re.findall(r'^\|\s*(LEFT|RIGHT)\s*\|\s*([\d,\s*]+?)(?:\s*\(шаг[^)]*\))?\s*\|'
                        r'\s*([\d,\s*]+?)(?:\s*\(шаг[^)]*\))?\s*\|\s*y\s*(\d+):\s*x\s*'
                        r'([\d,\s*]+?)\s*\|', txt, re.M)
    check(len(halves) == 2, 'spec 3.2: two keyboard half rows parsed (got %d)' % len(halves))
    for half, xcol, yrow, ythumb, xthumb in halves:
        first, last = (1, 21) if half == 'LEFT' else (22, 42)
        want = set((round(x, 1), round(y, 1)) for x in _nums(xcol) for y in _nums(yrow))
        want |= set((round(x, 1), float(ythumb)) for x in _nums(xthumb))
        have = set()
        for n in range(first, last + 1):
            key = ('deck-keys', 'KEY%d' % n)
            if key in got:
                have.add((round(got[key][0], 1), round(got[key][1], 1)))
        check(have == want, 'coords: DECK-KEYS %s keys differ: missing %r, extra %r'
              % (half, sorted(want - have), sorted(have - want)))
    check(len(got) == 77, 'coords: 77 control positions documented, got %d' % len(got))


def main():
    total_pins = 0
    for slug in ('panel-1', 'deck-pad', 'deck-keys'):
        net = os.path.join(PANEL_DIR, slug, slug + '.net')
        if not os.path.exists(net):
            print('missing netlist %s (run tools/build.sh)' % net)
            sys.exit(2)
        nets, pin2net, values = load_netlist(net)
        want, intent, namemap = verify_intent(slug, nets, pin2net)
        verify_docs(slug, None, pin2net, values, namemap)
        ncomp = len(values)
        total_pins += len(pin2net)
        print('%-10s nets=%3d  components=%3d  connected pins=%4d  intent=%4d'
              % (slug, len(nets), ncomp, len(pin2net), len(intent)))
    verify_spec()
    verify_coords()
    check(total_pins > 700, 'total connected pins = %d' % total_pins)
    print('verification checks: %d, failures: %d' % (NCHK[0], len(FAILS)))
    for f in FAILS[:40]:
        print('  FAIL', f)
    if FAILS:
        sys.exit(1)
    print('OK - schematic netlists match the design intent and matrix-tables.md')


if __name__ == '__main__':
    main()
