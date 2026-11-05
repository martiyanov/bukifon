"""Minimal KiCad 9/10 .kicad_sch writer (S-expression), format version 20250114.

Adapted for CORE-1 from hardware/panel/tools/kicad_sch.py (hw-panel):
 - multi-unit symbol instances (TL074/TL072/74HCT125 power units)
 - label-per-pin wiring with automatic escapes (flat single-sheet design)
 - custom project library support (bukifon:*)
 - duplicate wire/label/no-connect suppression (stacked pins).
"""
import re, os
SYM_DIR = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols'
_libcache = {}

def _lib(name):
    if name not in _libcache:
        p = os.path.join(SYM_DIR, name + '.kicad_sym')
        _libcache[name] = open(p, encoding='utf-8').read()
    return _libcache[name]

# ---------- minimal s-expression parser ----------
def tokenize(s):
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in ' \t\r\n':
            i += 1
        elif c in '()':
            yield c; i += 1
        elif c == '"':
            j = i + 1; buf = []
            while j < n:
                if s[j] == '\\':
                    buf.append(s[j+1]); j += 2
                elif s[j] == '"':
                    break
                else:
                    buf.append(s[j]); j += 1
            yield ('STR', ''.join(buf)); i = j + 1
        else:
            j = i
            while j < n and s[j] not in ' \t\r\n()"':
                j += 1
            yield ('ATOM', s[i:j]); i = j

def parse(s):
    toks = tokenize(s); stack = []; cur = None
    for t in toks:
        if t == '(':
            new = []; stack.append(new)
        elif t == ')':
            done = stack.pop()
            if stack: stack[-1].append(done)
            else: return done
        else:
            if stack: stack[-1].append(t[1])
    return None

def find_all(node, key):
    out = []
    if isinstance(node, list):
        if node and node[0] == key:
            out.append(node)
        for ch in node:
            if isinstance(ch, list):
                out.extend(find_all(ch, key))
    return out

def _block(txt, name):
    i = txt.find('(symbol "%s"' % name)
    if i < 0: return None
    d = 0; inq = False; j = i
    while j < len(txt):
        c = txt[j]
        if inq:
            if c == '\\': j += 2; continue
            if c == '"': inq = False
        else:
            if c == '"': inq = True
            elif c == '(': d += 1
            elif c == ')':
                d -= 1
                if d == 0: return txt[i:j+1]
        j += 1
    return None

CUSTOM = {}   # (libname, name) -> raw symbol text (kicad_sym definition)


def _balanced(txt, start):
    """return end index (exclusive) of the balanced s-expr starting at txt[start]=='('."""
    d = 0; inq = False; j = start
    while j < len(txt):
        c = txt[j]
        if inq:
            if c == '\\': j += 2; continue
            if c == '"': inq = False
        else:
            if c == '"': inq = True
            elif c == '(': d += 1
            elif c == ')':
                d -= 1
                if d == 0: return j + 1
        j += 1
    return -1

def _prop_blocks(raw):
    """[(name, value, block_text)] for all (property "name" "value" ...) in a symbol block."""
    out = []
    i = 0
    while True:
        i = raw.find('(property "', i)
        if i < 0: break
        j = _balanced(raw, i)
        if j < 0: break
        blk = raw[i:j]
        m = re.match(r'\(property "([^"]*)"\s+"((?:[^"\\]|\\.)*)"', blk)
        if m: out.append((m.group(1), m.group(2), blk))
        i = j
    return out

def _replace_property(txt, name, block):
    pat = '(property "%s"' % name
    i = txt.find(pat)
    if i < 0:
        # append a new property right before the first sub-symbol of the body
        k = txt.find('\n\t\t(symbol "')
        if k < 0: return txt
        return txt[:k] + '\n\t\t' + block + txt[k:]
    j = _balanced(txt, i)
    return txt[:i] + block + txt[j:]

def symbol_raw(libname, name):
    """Return a lib_symbols entry text with the "lib:name" id, resolving `extends`.

    Inner unit sub-symbols are renamed to "<name>_<unit>_<convert>" because KiCad
    requires them to match the parent symbol name ("Invalid symbol name" otherwise).
    """
    if (libname, name) in CUSTOM:
        return CUSTOM[(libname, name)]
    raw = _block(_lib(libname), name)
    if raw is None: raise KeyError('%s:%s' % (libname, name))
    newname = '%s:%s' % (libname, name)
    m = re.search(r'\(extends "([^"]+)"', raw)
    if m:
        base = m.group(1)
        txt = symbol_raw(libname, base)
        txt = re.sub(r'^\(symbol "[^"]+"', '(symbol "%s"' % newname, txt, count=1)
        txt = re.sub(r'\(symbol "%s_' % re.escape(base), '(symbol "%s_' % name, txt)
        for pname, pval, pblk in _prop_blocks(raw):
            if pname in ('Reference', 'Value', 'Footprint', 'Datasheet', 'Description') or True:
                txt = _replace_property(txt, pname, pblk)
        return txt
    txt = re.sub(r'^\(symbol "[^"]+"', '(symbol "%s"' % newname, raw, count=1)
    return txt

def _refprefix(libname, name):
    # reference designator prefix from the symbol's own property if present
    raw = _block(_lib(libname), name)
    m = re.search(r'\(property "Reference"\s+"([^"]*)"', raw)
    return m.group(1) if m else 'U'

_pincache = {}

def pins(libname, name):
    """[(number, name, x, y, angle, type, unit)] in library coords (y up)."""
    key = (libname, name)
    if key in _pincache: return _pincache[key]
    tree = parse(symbol_raw(libname, name))
    out = []
    seen = set()
    for sub in tree[1:]:
        if not (isinstance(sub, list) and sub and sub[0] == 'symbol'):
            continue
        m = re.match(r'(.+)_(\d+)_(\d+)$', sub[1])
        unit = int(m.group(2)) if m else 0
        for p in find_all(sub, 'pin'):
            if len(p) < 3 or not isinstance(p[1], str): continue
            at = [x for x in p if isinstance(x, list) and x and x[0] == 'at']
            if not at: continue
            at = at[0]
            nm = [x for x in p if isinstance(x, list) and x and x[0] == 'name']
            no = [x for x in p if isinstance(x, list) and x and x[0] == 'number']
            num = no[0][1] if no else ''
            nam = nm[0][1] if nm else ''
            if num in seen: continue
            seen.add(num)
            out.append((num, nam, float(at[1]), float(at[2]), int(float(at[3])), p[1], unit))
    _pincache[key] = out
    return out

def pin(libname, name, num):
    for p in pins(libname, name):
        if p[0] == str(num): return p
    raise KeyError('%s:%s pin %s' % (libname, name, num))

def pin_by_name(libname, name, pname):
    for p in pins(libname, name):
        if p[1] == pname: return p
    raise KeyError('%s:%s pin name %s' % (libname, name, pname))

def _u():
    import uuid
    return str(uuid.uuid4())

def _fmt(v):
    v = round(float(v), 3)
    return ('%g' % v)

class Sch:
    def __init__(self, path, title, paper='A1', project='panel'):
        self.path = path
        self.title = title
        self.paper = paper
        self.project = project
        self.uuid = _u()
        self.libsyms = {}     # lib:name -> raw text
        self.items = []       # (kind, text)
        self.comps = []       # dicts
        self.labels = []
        self._r = 0
        self._pwr = 0
        self._nets = set()
        self._ncs = set()
        self.wire_pts = []
        self.power_rails = ('GND', '+3V3', '+5V', '+12V', '-12V')

    # ---- primitives
    def sym(self, libname, name, ref, value, x, y, footprint='', props=None, hide_value=False, hide_ref=False, ref_off=(2.54,-1.27), val_off=(2.54,1.27), unit=1, on_board=True, in_bom=True, dnp=False):
        lid = '%s:%s' % (libname, name)
        if lid not in self.libsyms:
            self.libsyms[lid] = symbol_raw(libname, name)
        x = _grid(x); y = _grid(y)
        p = dict(libname=libname, name=name, lid=lid, ref=ref, value=value, x=float(x), y=float(y),
                 footprint=footprint, props=props or {}, hide_value=hide_value, hide_ref=hide_ref,
                 ref_off=ref_off, val_off=val_off, unit=int(unit), on_board=on_board, in_bom=in_bom,
                 dnp=bool(dnp), uuid=_u())
        self.comps.append(p)
        return p

    def pinpt(self, comp, num=None, pname=None):
        """absolute schematic coordinate of a pin (rotation 0 -> y flipped)."""
        if num is not None:
            n, _, px, py, a, t, u = pin(comp['libname'], comp['name'], num)
        else:
            n, _, px, py, a, t, u = pin_by_name(comp['libname'], comp['name'], pname)
        return (comp['x'] + px, comp['y'] - py, a, n)

    def wire(self, p1, p2):
        self.wire_pts.append((round(float(p1[0]),2), round(float(p1[1]),2), round(float(p2[0]),2), round(float(p2[1]),2)))
        self.items.append(('wire', '\t(wire\n\t\t(pts\n\t\t\t(xy %s %s)\n\t\t\t(xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "%s")\n\t)' % (
            _fmt(p1[0]), _fmt(p1[1]), _fmt(p2[0]), _fmt(p2[1]), _u())))

    def label(self, name, pt, angle=0, justify='left', size=1.27):
        self.labels.append(name)
        self.items.append(('label', '\t(label "%s"\n\t\t(at %s %s %s)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size %s %s)\n\t\t\t)\n\t\t\t(justify %s bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)' % (
            _esc(name), _fmt(pt[0]), _fmt(pt[1]), angle, _fmt(size), _fmt(size), justify, _u())))

    def noconnect(self, pt):
        key = (round(float(pt[0]), 2), round(float(pt[1]), 2))
        if key in self._ncs: return
        self._ncs.add(key)
        self.items.append(('nc', '\t(no_connect\n\t\t(at %s %s)\n\t\t(uuid "%s")\n\t)' % (_fmt(pt[0]), _fmt(pt[1]), _u())))

    def text(self, s, pt, size=1.27):
        self.items.append(('text', '\t(text "%s"\n\t\t(exclude_from_sim no)\n\t\t(at %s %s 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size %s %s)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)' % (
            _esc(s), _fmt(pt[0]), _fmt(pt[1]), size, size, _u())))

    # ---- high level: attach a net label to a pin through a short stub
    def net(self, comp, netname, num=None, pname=None, stub=2.54, side=None, bend=5.08, font=1.27):
        """Attach a net label to a pin via a short escape wire (flat-sheet style)."""
        x, y, a, num = self.pinpt(comp, num=num, pname=pname)
        dx, dy = -_cos(a), _sin(a)          # outward direction, schematic coords
        if side == 'left':   dx, dy = -1.0, 0.0
        elif side == 'right': dx, dy = 1.0, 0.0
        elif side == 'up':   dx, dy = 0.0, -1.0
        elif side == 'down': dx, dy = 0.0, 1.0
        key = (round(x, 2), round(y, 2), netname)
        if key in self._nets:
            return
        self._nets.add(key)
        if dx == 0:                          # vertical pin: straight escape, rotated label
            ex, ey = x, y + dy * stub
            self.wire((x, y), (ex, ey))
            ang = 90 if dy < 0 else 270
            just = 'left' if dy < 0 else 'right'
            self.label(netname, (ex, ey), angle=ang, justify=just, size=font)
        else:                                # horizontal pin: straight escape
            ex, ey = x + dx * stub, y + dy * stub
            self.wire((x, y), (ex, ey))
            ang = 0 if dx > 0 else 180
            just = 'left' if dx > 0 else 'right'
            self.label(netname, (ex, ey), angle=ang, justify=just, size=font)

    def place_power(self, rail, pt):
        self._pwr += 1
        return self.sym('power', rail, '#PWR%03d' % self._pwr, rail, pt[0], pt[1],
                        hide_ref=True, ref_off=(0, -3.81), val_off=(0, 3.81))

    def power_anchor(self, rail, x, y):
        """A power port + PWR_FLAG (net driver) + matching net label.

        KiCad ERC requires every net that carries `power_in` pins to be driven by a
        `power_out` pin; power ports are `power_in`, so the PWR_FLAG tells ERC that
        this board *receives* the rail from the ribbon connector.
        """
        x = _grid(x); y = _grid(y)
        c = self.place_power(rail, (x, y))
        self.wire((x, y), (x + 5.08, y))
        self._pwr += 1
        self.sym('power', 'PWR_FLAG', '#FLG%03d' % self._pwr, 'PWR_FLAG',
                 x + 5.08, y, hide_ref=True)
        self.label(rail, (x + 5.08, y), angle=0, justify='left')
        return c

    def nc_pin(self, comp, num=None, pname=None):
        x, y, a, n = self.pinpt(comp, num=num, pname=pname)
        self.noconnect((x, y))

    # ---- serialization
    def render(self):
        out = []
        out.append('(kicad_sch\n\t(version 20250114)\n\t(generator "eeschema")\n\t(generator_version "9.0")\n\t(uuid "%s")\n\t(paper "%s")\n' % (self.uuid, self.paper))
        out.append('\t(title_block\n\t\t(title "%s")\n\t\t(rev "1.0")\n\t\t(comment 1 "Bukifon open hardware - CERN-OHL-S-2.0")\n\t)\n' % _esc(self.title))
        out.append('\t(lib_symbols\n')
        for k in sorted(self.libsyms):
            body = self.libsyms[k]
            body = '\n'.join('\t\t' + ln for ln in body.split('\n'))
            out.append(body + '\n')
        out.append('\t)\n')
        # symbol instances
        for c in self.comps:
            out.append(self._comp_text(c))
        for kind, t in self.items:
            out.append(t + '\n')
        out.append('\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n')
        return ''.join(out)

    def _comp_text(self, c):
        L = []
        L.append('\t(symbol\n\t\t(lib_id "%s")\n\t\t(at %s %s 0)\n\t\t(unit %d)\n\t\t(exclude_from_sim no)\n\t\t(in_bom %s)\n\t\t(on_board %s)\n\t\t(dnp %s)\n\t\t(uuid "%s")\n' % (
            c['lid'], _fmt(c['x']), _fmt(c['y']), c['unit'],
            'yes' if c['in_bom'] else 'no', 'yes' if c['on_board'] else 'no',
            'yes' if c.get('dnp') else 'no', c['uuid']))
        rx, ry = c['x'] + c['ref_off'][0], c['y'] + c['ref_off'][1]
        vx, vy = c['x'] + c['val_off'][0], c['y'] + c['val_off'][1]
        hide_ref = '\n\t\t\t(hide yes)' if c['hide_ref'] else ''
        hide_val = '\n\t\t\t(hide yes)' if c['hide_value'] else ''
        L.append('\t\t(property "Reference" "%s"\n\t\t\t(at %s %s 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)%s\n\t\t\t)\n\t\t)\n' % (_esc(c['ref']), _fmt(rx), _fmt(ry), hide_ref))
        L.append('\t\t(property "Value" "%s"\n\t\t\t(at %s %s 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)%s\n\t\t\t)\n\t\t)\n' % (_esc(c['value']), _fmt(vx), _fmt(vy), hide_val))
        L.append('\t\t(property "Footprint" "%s"\n\t\t\t(at %s %s 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n' % (_esc(c['footprint']), _fmt(c['x']), _fmt(c['y'])))
        extra = dict(c['props'])
        L.append('\t\t(property "Datasheet" "%s"\n\t\t\t(at %s %s 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n' % (_esc(extra.pop('Datasheet', '~')), _fmt(c['x']), _fmt(c['y'])))
        for k, v in extra.items():
            L.append('\t\t(property "%s" "%s"\n\t\t\t(at %s %s 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n' % (_esc(k), _esc(v), _fmt(c['x']), _fmt(c['y'])))
        for p in pins(c['libname'], c['name']):
            if p[6] not in (0, c['unit']):
                continue
            L.append('\t\t(pin "%s"\n\t\t\t(uuid "%s")\n\t\t)\n' % (p[0], _u()))
        L.append('\t\t(instances\n\t\t\t(project "%s"\n\t\t\t\t(path "/%s"\n\t\t\t\t\t(reference "%s")\n\t\t\t\t\t(unit %d)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n' % (
            _esc(self.project), self.uuid, _esc(c['ref']), c['unit']))
        return ''.join(L)

    def write(self):
        os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write(self.render())
        return self.path

def _grid(v):
    # KiCad connection grid = 1.27 mm (50 mil); never snap to 2.54 (pin offsets
    # of most symbols are odd multiples of 1.27 mm, e.g. R pins at +-3.81).
    return round(math.floor(float(v) / 1.27 + 0.5) * 1.27, 3)

import math
def _cos(a): return round(math.cos(math.radians(a)), 6)
def _sin(a): return round(math.sin(math.radians(a)), 6)
def _esc(s): return str(s).replace('\\', '\\\\').replace('"', '\\"')
