#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strip absolute host paths / user names from exported artefacts (PII-clean).

KiCad writes `(source "PANEL-2.kicad_sch")` into the netlist; the PDF and SVG
do not contain host paths. This script rewrites exported files in place and fails if any
absolute path is left.
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
P2 = os.path.abspath(os.path.join(HERE, '..'))

PATTERNS = [
    (re.compile(r'\(source "[^"]*/([^/"]+)"\)'), r'(source "\1")'),
    (re.compile(r'<abs-path>"\s]*'), '<abs-path>'),
    (re.compile(r'<abs-path>"\s]*'), '<abs-path>'),
]

bad = []
for path in sorted(set(glob.glob(os.path.join(P2, '**', '*'), recursive=True))):
    if not os.path.isfile(path) or os.path.getsize(path) > 20 * 1024 * 1024:
        continue
    if os.path.basename(path) in ('LCD-ADAPTER.pdf', 'LCD-ADAPTER.svg'):
        continue                      # binary / vector: checked separately
    try:
        with open(path, encoding='utf-8') as f:
            txt = f.read()
    except (UnicodeDecodeError, OSError):
        continue
    new = txt
    for pat, repl in PATTERNS:
        new = pat.sub(repl, new)
    if new != txt:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new)
    for pat, _ in PATTERNS:
        for m in pat.finditer(new):
            bad.append((os.path.relpath(path, P2), m.group(0)))

if bad:
    print('PII: absolute paths remain:')
    for f, s in bad[:10]:
        print('  %s: %s' % (f, s))
    sys.exit(1)
print('PII-clean: no absolute host paths in text artefacts')
