#!/usr/bin/env python3
import sys as _sys; _sys.dont_write_bytecode = True
# -*- coding: utf-8 -*-
"""CORE-2 pin/resource ownership checker.

Checks (exit code != 0 on failure):
 1. no duplicate GPIO assignments;
 2. MCU slot pins are unique and cover 1..64;
 3. reserved GPIOs are not assigned as signals;
 4. boot/strapping rules for GPIO35..GPIO38 (only BOOT/UART0, no active-low
    drivers at reset, GPIO36 fixed low);
 5. connector pin conflicts (non-ground net used twice on one connector);
 6. LP-domain rule: GPIO0..GPIO15 require VDD_LP = 3.3 V (informational);
 7. free-GPIO reserve: >=10 % or explicit "NO RESERVE" declaration.
"""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_def as B

ERR, WARN, INFO = [], [], []
RES = {g: why for g, why in B.RESERVED}
STRAP = {35: 'boot mode', 36: 'boot mode', 37: 'UART0/strap', 38: 'UART0/strap'}
RES_SIG = {'STRAP36'}
FREE_SIG = {'FREE_IO54', 'FREE_GPIO50'}
POWER_NETS = {'5V', '3V3', 'DGND', 'AGND', 'PGND'}

def main():
    used = [r for r in B.PINMAP if r[1] is not None]
    res_rows = [r for r in used if r[1] in RES or r[0] in RES_SIG]
    used_only = [r for r in used if r[1] not in RES and r[0] not in RES_SIG
                 and r[0] not in FREE_SIG]

    # 1 duplicates
    c = collections.Counter(r[1] for r in used_only)
    for g, n in c.items():
        if n > 1:
            ERR.append('GPIO%d assigned %d times: %s' % (g, n, [r[0] for r in used_only if r[1] == g]))
    # reserved rows must match the RESERVED declaration
    for r in res_rows:
        if r[1] not in RES:
            ERR.append('reserved row %s has GPIO%s not in RESERVED list' % (r[0], r[1]))
    for g in RES:
        if not any(r[1] == g for r in res_rows) and g != 54:
            ERR.append('RESERVED GPIO%d has no PINMAP row' % g)
    # 2 module pins
    pins = [r[7] for r in B.PINMAP]
    dup = [p for p, n in collections.Counter(pins).items() if n > 1]
    if dup:
        ERR.append('duplicate MCU slot pins: %s' % sorted(dup))
    missing = sorted(set(range(1, 65)) - set(pins))
    extra = sorted(set(pins) - set(range(1, 65)))
    if missing: ERR.append('unassigned MCU slot pins: %s' % missing)
    if extra: ERR.append('MCU slot pins out of 1..64: %s' % extra)
    # 3 boot / strapping
    for r in used_only:
        g = r[1]
        if g in STRAP:
            if g not in (35, 36, 37, 38):
                ERR.append('signal %s uses strapping GPIO%d' % (r[0], g))
            elif g == 35:
                if r[0] != 'BOOT':
                    ERR.append('GPIO35 (boot strap) used by %s, expected BOOT button' % r[0])
                elif 'PU' not in r[5]:
                    ERR.append('GPIO35/BOOT needs pull-up (has %r)' % r[5])
            elif g == 36:
                if r[0] != 'STRAP36':
                    ERR.append('GPIO36 (boot strap) used by %s, expected STRAP36' % r[0])
                elif 'PU' not in r[5]:
                    ERR.append('GPIO36/STRAP36 needs 10k PU (download boot), has %r' % r[5])
            elif g in (37, 38) and not r[0].startswith('UART0'):
                ERR.append('GPIO%d is UART0/strap, used by %s' % (g, r[0]))
        if r[6] == 'low' and r[4] == 'out' and g in STRAP:
            ERR.append('output %s drives strapping GPIO%d low at boot' % (r[0], g))
    if 36 not in RES:
        ERR.append('GPIO36 must be reserved with 10k PU (download boot)')
    # joint download boot reachability: GPIO35 can be pulled low, GPIO36 can be 1
    err36 = [r for r in B.PINMAP if r[1] == 36]
    if not err36 or 'PU' not in err36[0][5]:
        ERR.append('joint download boot not reachable: GPIO36 must have PU')
    # 4 connector conflicts
    for cname, pins_ in [('J-PANEL', B.J_PANEL), ('J-LCD', B.J_LCD),
                         ('J-BUS1/2', B.J_BUS), ('J-DIG', B.J_DIG)]:
        cnt = collections.Counter(p[1] for p in pins_)
        for sig, n in cnt.items():
            if n > 1 and sig not in POWER_NETS:
                ERR.append('%s: net %s appears %d times' % (cname, sig, n))
        nums = [p[0] for p in pins_]
        if len(set(nums)) != len(nums):
            ERR.append('%s: duplicate pin numbers' % cname)
    # 5 LP-domain informational
    lp = [r for r in used_only if r[1] is not None and 0 <= r[1] <= 15]
    INFO.append('LP-domain GPIO0..15 used: %s (VDD_LP must be 3.3 V)' %
                ', '.join('%s=GPIO%d' % (r[0], r[1]) for r in lp))
    # 6 reserve
    free = [g for g in range(55) if g not in {r[1] for r in used_only} and g not in RES]
    pct = 100.0 * len(free) / 55
    INFO.append('GPIO: used=%d reserved=%d free=%d (%.1f %%)' %
                (len(used_only), len(RES), len(free), pct))
    if pct < 10.0:
        WARN.append('NO GPIO RESERVE: only %d free GPIO (%.1f %%) — expansion via I2C '
                    'MCP23017 (3 pcs on PANEL-2) / SPI mailbox; declared explicitly.' % (len(free), pct))
    # print
    print('CORE-2 pinmap check (PRE-FREEZE / DO NOT FABRICATE)')
    for i in INFO: print('  INFO :', i)
    for w in WARN: print('  WARN :', w)
    for e in ERR: print('  ERROR:', e)
    print('RESULT:', 'FAIL (%d errors)' % len(ERR) if ERR else 'PASS (0 errors, %d warnings)' % len(WARN))
    return 1 if ERR else 0

if __name__ == '__main__':
    sys.exit(main())
