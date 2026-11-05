#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PANEL-2 contract verification: exported netlist vs design intent vs published tables.

Checks (all real, against the KiCad-produced netlist):
  1. pin->net in PANEL-2.net equals the generator design intent (both directions) —
     catches wrong symbol pin offsets, dangling labels, accidental shorts;
  2. matrix.md rows: every key's ROW/COL/diode matches the netlist (42 keys);
  3. pinmap.csv: every J12/J13/J14 pin carries the documented net;
  4. uniqueness: 42 unique matrix cells, 16 encoders with unique A/B/SW nets,
     4 MCP23017 with distinct I2C addresses;
  5. geometry: key coordinates in matrix.md match spec/panel-spec-v0.4.json.

Usage: python3 tools/verify_netlist.py   (exit 0 = pass)
"""
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
P2 = os.path.abspath(os.path.join(HERE, '..'))
ROOT = os.path.abspath(os.path.join(P2, '..', '..'))
sys.path.insert(0, HERE)
from kicad_sch import parse, find_all  # noqa: E402

FAILS = []
NCHK = [0]


def check(cond, msg):
    NCHK[0] += 1
    if not cond:
        FAILS.append(msg)


def is_nc(net):
    return net is None or net.startswith('unconnected-(')


def load_netlist(path):
    with open(path, encoding='utf-8') as f:
        tree = parse(f.read())
    nets, pin2net, values = {}, {}, {}
    for comp in find_all(tree, 'comp'):
        ref = [c[1] for c in comp if isinstance(c, list) and c[0] == 'ref']
        val = [c[1] for c in comp if isinstance(c, list) and c[0] == 'value']
        if ref:
            values[ref[0]] = val[0] if val else ''
    for net in find_all(tree, 'net'):
        name = [c[1] for c in net if isinstance(c, list) and c[0] == 'name'][0]
        nodes = []
        for ch in net:
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


def main():
    net_path = os.path.join(P2, 'PANEL-2.net')
    if not os.path.exists(net_path):
        print('missing PANEL-2.net — run tools/build.sh')
        return 2
    nets, pin2net, values = load_netlist(net_path)
    intent = json.load(open(os.path.join(HERE, 'netlist-intent.json'),
                            encoding='utf-8'))['panel-2']

    # 1. intent <-> netlist (both directions)
    want = {}
    for ref, num, name, net in intent:
        key = (ref, str(num))
        if net is None:
            want[key] = None
        else:
            if key in want and want[key] != net:
                check(False, 'conflicting intent %s.%s: %r vs %r' % (ref, num, want[key], net))
            want[key] = net
    for key, net in want.items():
        if net is None:
            check(is_nc(pin2net.get(key)), 'no-connect expected: %s.%s is %r'
                  % (key[0], key[1], pin2net.get(key)))
        else:
            check(pin2net.get(key) == net, '%s.%s net %r, intended %r'
                  % (key[0], key[1], pin2net.get(key), net))
    extra = [k for k, net in pin2net.items() if k not in want and not is_nc(net)]
    for k in extra:
        check(False, 'unexpected connected pin %s.%s (net %r)' % (k[0], k[1], pin2net[k]))

    # 2. matrix.md <-> netlist
    md_path = os.path.join(P2, 'matrix.md')
    txt = open(md_path, encoding='utf-8').read()
    sec = txt.split('## 2.')[0]
    raw = re.findall(r'^\|.*?`([LR]_K\d\d)`.*?\| ROW(\d) \| COL(\d) \| `(D\d+)` \|'
                     r'\s*([\d.]+) \|\s*([\d.]+) \|', sec, re.M)
    rows = []
    for kid, row, col, diode, x, y in raw:
        half, key = kid[0], kid.split('K')[1]        # 'L_K01' -> 'L', '01'
        rows.append(('KEY_%s%s' % (half, key), row, col, diode, x, y))
    check(len(rows) == 42, 'matrix.md: 42 key rows parsed (got %d)' % len(rows))
    cells, diodes = set(), set()
    for ref, row, col, diode, x, y in rows:
        cells.add((row, col))
        diodes.add(diode)
        check(pin2net.get((ref, '1')) == 'ROW%s' % row, '%s row net %r'
              % (ref, pin2net.get((ref, '1'))))
        node = pin2net.get((ref, '2'))
        check(node is not None and node.startswith('K_'), '%s switch node %r' % (ref, node))
        check(pin2net.get((diode, '2')) == node, '%s anode %r != %r'
              % (diode, pin2net.get((diode, '2')), node))
        check(pin2net.get((diode, '1')) == 'COL%s' % col, '%s cathode %r'
              % (diode, pin2net.get((diode, '1'))))
    check(len(cells) == 42, 'matrix: 42 unique cells (got %d)' % len(cells))
    check(len(diodes) == 42, 'matrix: 42 unique diodes (got %d)' % len(diodes))

    # geometry: matrix.md coordinates vs spec JSON
    spec = json.load(open(os.path.join(ROOT, 'spec', 'panel-spec-v0.4.json'), encoding='utf-8'))
    spec_xy = {}
    for half, lst in (('L', spec['controls']['keyboard_left']), ('R', spec['controls']['keyboard_right'])):
        for e in lst:
            spec_xy['KEY_%s%02d' % (half, int(e['key_number']))] = tuple(e['center_mm'])
    worst = 0.0
    for ref, row, col, diode, x, y in rows:
        sx, sy = spec_xy[ref]
        worst = max(worst, abs(float(x) - sx), abs(float(y) - sy))
    check(worst <= 0.05, 'matrix.md key coordinates vs JSON: max dev %.2f mm' % worst)

    # 3. pinmap.csv <-> netlist
    with open(os.path.join(P2, 'pinmap.csv'), encoding='utf-8') as f:
        pm = list(csv.DictReader(f, delimiter=';'))
    names = {'J12 (FFC-40)': 'J12', 'J13 (IDC-16)': 'J13', 'J14 (IDC-26)': 'J14'}
    n = 0
    for r in pm:
        conn = names.get(r['connector'])
        if not conn:
            continue
        n += 1
        if r['signal'] == 'NC':
            check(is_nc(pin2net.get((conn, r['pin']))), 'pinmap: %s.%s should be NC, is %r'
                  % (conn, r['pin'], pin2net.get((conn, r['pin']))))
        else:
            check(pin2net.get((conn, r['pin'])) == r['signal'],
                  'pinmap: %s.%s net %r, table says %r'
                  % (conn, r['pin'], pin2net.get((conn, r['pin'])), r['signal']))
    check(n >= 40, 'pinmap: %d connector pins checked' % n)

    # 4. encoder uniqueness + MCP addresses
    for i in range(1, 17):
        for ph in ('A', 'B', 'SW'):
            net = 'ENC%d_%s' % (i, ph)
            nodes = nets.get(net, set())
            check(len(nodes) == 3, 'encoder line %s has %d nodes (expect pin+RC+MCP)'
                  % (net, len(nodes)))
    addr_bits = {}
    for u in ('U1', 'U2', 'U3', 'U4'):
        bits = tuple(pin2net.get((u, p)) for p in ('15', '16', '17'))  # A0,A1,A2
        addr_bits[u] = bits
        check(all(b in ('GND', '+3V3') for b in bits), '%s address pins: %r' % (u, bits))
    check(len(set(addr_bits.values())) == 4, 'MCP23017 addresses must differ: %r' % addr_bits)

    # 5. connector pin counts
    check(len([k for k in pin2net if k[0] == 'J12']) == 40, 'J12 has %d pins'
          % len([k for k in pin2net if k[0] == 'J12']))
    check(len([k for k in pin2net if k[0] == 'J13']) >= 14, 'J13 pin count')
    check(len([k for k in pin2net if k[0] == 'J14']) >= 24, 'J14 pin count')
    check(len([k for k in pin2net if k[0] == 'J11' and not is_nc(pin2net[k])]) == 34,
          'J11 connected (non-NC) pins')
    # 10 jacks, 2 faders, 17 LEDs
    check(all('J%02d' % i in values for i in range(1, 11)), '10 jacks J01..J10')
    check(len([r for r in values if re.fullmatch(r'F\d', r)]) == 2, '2 faders')
    check(len([r for r in values if r.startswith('LED_')]) == 17, '17 LEDs')

    print('nets=%d components=%d connected pins=%d intent=%d'
          % (len(nets), len(values), len(pin2net), len(intent)))
    print('verification checks: %d, failures: %d' % (NCHK[0], len(FAILS)))
    for f in FAILS[:30]:
        print('  FAIL', f)
    if FAILS:
        return 1
    print('OK - PANEL-2 netlist matches pinmap.csv, matrix.md and the design intent')
    return 0


if __name__ == '__main__':
    sys.exit(main())
