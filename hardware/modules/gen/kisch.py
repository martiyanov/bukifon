# -*- coding: utf-8 -*-
"""Minimal generator for KiCad 9/10 .kicad_sch (S-expression) files.

Symbols are embedded from the official KiCad symbol libraries
(/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols), so no
sym-lib-table is required to open the generated schematic.

The generated schematics use "named-net" style: every pin gets a short stub
wire and a net label.  This is deliberate: it makes connectivity machine
checkable and keeps a 110x70 mm module readable on A4/A3.
"""
import os
import re
import uuid

SYMBOL_DIR = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
GRID = 1.27  # mm


def _read(lib):
    p = os.path.join(SYMBOL_DIR, lib + ".kicad_sym")
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def _block(text, name):
    """Return the text of the top level (symbol "name" ...) block."""
    i = text.find('(symbol "%s"' % name)
    if i < 0:
        return None
    d = 0
    j = i
    while j < len(text):
        c = text[j]
        if c == '(':
            d += 1
        elif c == ')':
            d -= 1
            if d == 0:
                return text[i:j + 1]
        j += 1
    return None


_PIN_RE = re.compile(
    r'\(pin\s+(\w+)\s+(\w+)\s*\(at\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\)\s*\(length\s+([-\d.]+)\)'
    r'.*?\(name\s+"([^"]*)"', re.S)


def _pins(block_text):
    """[(number, name, type, x_mm, y_mm, angle)] from a flattened symbol block."""
    out = []
    # walk nested unit symbols to know unit numbers
    for m in re.finditer(r'\(symbol "([^"]+)_(\d+)_(\d+)"', block_text):
        pass
    # simpler: split by unit sub-symbol headers, then regex pins inside each
    pos = [(m.start(), m.group(1), m.group(2)) for m in
           re.finditer(r'\(symbol "[^"]+_(\d+)_(\d+)"', block_text)]
    for idx, (start, unit, style) in enumerate(pos):
        end = pos[idx + 1][0] if idx + 1 < len(pos) else len(block_text)
        seg = block_text[start:end]
        for m in _PIN_RE.finditer(seg):
            num = None
            nm = re.search(r'\(number\s+"([^"]+)"', seg[m.end():m.end() + 800])
            if nm:
                num = nm.group(1)
            out.append(dict(number=num, name=m.group(7), etype=m.group(1),
                            x=float(m.group(3)), y=float(m.group(4)),
                            angle=int(m.group(5)), unit=int(unit)))
    if not out:
        # flat symbol (no unit sub-symbols)
        for m in _PIN_RE.finditer(block_text):
            nm = re.search(r'\(number\s+"([^"]+)"', block_text[m.end():m.end() + 800])
            out.append(dict(number=nm.group(1) if nm else None, name=m.group(7),
                            etype=m.group(1), x=float(m.group(3)), y=float(m.group(4)),
                            angle=int(m.group(5)), unit=1))
    return out


class _Cache(object):
    libs = {}
    syms = {}


CACHE = _Cache()


def raw_symbol(lib, name):
    key = lib + ':' + name
    if key in CACHE.syms:
        return CACHE.syms[key]
    if lib not in CACHE.libs:
        CACHE.libs[lib] = _read(lib)
    text = CACHE.libs[lib]
    blk = _block(text, name)
    if blk is None:
        raise KeyError("symbol %s not found in %s" % (name, lib))
    ext = re.search(r'\(extends\s+"([^"]+)"\)', blk)
    if ext:
        parent_text, parent_name = raw_symbol(lib, ext.group(1))
        # rename nested unit sub-symbols  PARENT_0_1 -> NAME_0_1
        pblk = _block(parent_text, parent_name)
        pblk = re.sub(r'\(symbol "%s_(\d+)_(\d+)"' % re.escape(parent_name),
                      '(symbol "%s_\\1_\\2"' % name, pblk)
        # keep child's own properties: replace property block of parent by child's
        pprop = re.findall(r'\n\t\t\(property\s.*?\n\t\t\)', pblk, re.S)
        cprop = re.findall(r'\n\t\t\(property\s.*?\n\t\t\)', blk, re.S)
        for a, b in zip(pprop, cprop):
            if a in pblk:
                pblk = pblk.replace(a, b, 1)
        blk = pblk
    CACHE.syms[key] = (blk, name)
    return (blk, name)


def symbol_libdef(lib, name):
    """(lib_symbols text, pins list) with the top level name 'lib:name'."""
    blk, real = raw_symbol(lib, name)
    # check whether the block already has unit sub-symbols whose prefix is `real`
    if '_(\\d+)' not in blk and not re.search(r'\(symbol "%s_\d+_\d+"' % re.escape(real), blk):
        if re.search(r'\(symbol "[^"]+_\d+_\d+"', blk):
            pass
    # rename the top-level symbol line only
    m = re.search(r'\(symbol\s+"([^"]+)"', blk)
    top = blk[:m.start(1)] + lib + ':' + name + blk[m.end(1):]
    pins = _pins(top)
    return top, pins


def pin_outward(angle, rot=0, mirror=None):
    """Screen-space outward unit vector for a library pin (angle = pin dir)."""
    a = (angle + 180) % 360
    lx = {0: 1.0, 90: 0.0, 180: -1.0, 270: 0.0}[a]
    ly = {0: 0.0, 90: 1.0, 180: 0.0, 270: -1.0}[a]
    dx, dy = transform(lx, ly, rot, mirror)
    return dx, dy


def transform(px, py, rot, mirror=None):
    """Symbol local (mm, Y-up) -> schematic offset (mm, Y-down)."""
    if mirror == 'x':
        py = -py
    elif mirror == 'y':
        px = -px
    if rot == 0:
        return (px, -py)
    if rot == 90:
        return (-py, -px)
    if rot == 180:
        return (-px, py)
    if rot == 270:
        return (py, px)
    raise ValueError(rot)


def fmt(v):
    s = "%.4f" % v
    s = s.rstrip('0').rstrip('.')
    return s if s else "0"


class Schematic(object):
    def __init__(self, title, paper="A3", company="Bukifon", rev="1.0"):
        self.title = title
        self.paper = paper
        self.company = company
        self.rev = rev
        self.root_uuid = str(uuid.uuid4())
        self.libdefs = {}       # "lib:name" -> text
        self.pinmap = {}        # "lib:name" -> pins
        self.items = []
        self.n = 0
        self.pins = {}          # (ref, pin) -> (x, y, angle)  sheet coords
        self.nets = {}          # net -> [(ref, pin, x, y)]
        self.power_lib = "power"

    # ---------- low level ----------
    def _u(self):
        self.n += 1
        return str(uuid.uuid5(uuid.UUID('12345678-1234-5678-1234-567812345678'),
                              '%s-%d' % (self.title, self.n)))

    def _emb(self, lib, name):
        key = lib + ':' + name
        if key not in self.libdefs:
            text, pins = symbol_libdef(lib, name)
            self.libdefs[key] = text
            self.pinmap[key] = pins
        return self.pinmap[key]

    # ---------- primitives ----------
    def wire(self, x1, y1, x2, y2):
        self.items.append(
            "\t(wire\n\t\t(pts (xy %s %s) (xy %s %s))\n"
            "\t\t(stroke (width 0) (type default))\n\t\t(uuid \"%s\")\n\t)"
            % (fmt(x1), fmt(y1), fmt(x2), fmt(y2), self._u()))

    def junction(self, x, y):
        self.items.append(
            "\t(junction\n\t\t(at %s %s)\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n"
            "\t\t(uuid \"%s\")\n\t)" % (fmt(x), fmt(y), self._u()))

    def noconnect(self, x, y):
        self.items.append("\t(no_connect\n\t\t(at %s %s)\n\t\t(uuid \"%s\")\n\t)"
                          % (fmt(x), fmt(y), self._u()))

    def label(self, net, x, y, rot=0, justify="left bottom", size=1.27):
        self.items.append(
            "\t(label \"%s\"\n\t\t(at %s %s %d)\n\t\t(effects (font (size %s %s)) (justify %s))\n"
            "\t\t(uuid \"%s\")\n\t)"
            % (net, fmt(x), fmt(y), rot, fmt(size), fmt(size), justify, self._u()))

    def glabel(self, net, x, y, rot=0, shape="input"):
        self.items.append(
            "\t(global_label \"%s\"\n\t\t(shape %s)\n\t\t(at %s %s %d)\n"
            "\t\t(effects (font (size 1.27 1.27)) (justify left))\n\t\t(uuid \"%s\")\n"
            "\t\t(property \"Intersheetrefs\" \"${INTERSHEET_REFS}\"\n"
            "\t\t\t(at %s %s 0)\n\t\t\t(hide yes)\n"
            "\t\t\t(effects (font (size 1.27 1.27)) (justify left))\n\t\t)\n\t)"
            % (net, shape, fmt(x), fmt(y), rot, self._u(), fmt(x), fmt(y)))

    def text(self, s, x, y, size=1.27, rot=0):
        self.items.append(
            "\t(text \"%s\"\n\t\t(at %s %s %d)\n"
            "\t\t(effects (font (size %s %s)) (justify left bottom))\n\t\t(uuid \"%s\")\n\t)"
            % (s.replace('"', '\\"').replace('\n', '\\n'), fmt(x), fmt(y), rot,
               fmt(size), fmt(size), self._u()))

    def rect(self, x1, y1, x2, y2):
        self.items.append(
            "\t(rectangle\n\t\t(start %s %s)\n\t\t(end %s %s)\n"
            "\t\t(stroke (width 0.1524) (type dash))\n\t\t(fill (type none))\n\t\t(uuid \"%s\")\n\t)"
            % (fmt(x1), fmt(y1), fmt(x2), fmt(y2), self._u()))

    # ---------- symbols ----------
    def place(self, lib, name, ref, value, x, y, rot=0, unit=1, mirror=None,
              footprint="", datasheet="~", description="", ref_at=None,
              val_at=None, hide_value=False, hide_ref=False, extra=None):
        pins = self._emb(lib, name)
        u = self._u()
        props = []
        def addprop(k, v, px, py, prot, hide=False, justify=None):
            props.append(
                "\t\t(property \"%s\" \"%s\"\n\t\t\t(at %s %s %d)\n%s"
                "\t\t\t(effects (font (size 1.27 1.27))%s)\n\t\t)"
                % (k, v, fmt(px), fmt(py), prot,
                   "\t\t\t(hide yes)\n" if hide else "",
                   (" (justify %s)" % justify) if justify else ""))
        if ref_at is None:
            ref_at = (x + 2.54, y - 2.54, 0)
        if val_at is None:
            val_at = (x + 2.54, y + 2.54, 0)
        addprop("Reference", ref, ref_at[0], ref_at[1],
                ref_at[2] if len(ref_at) > 2 else 0, hide=hide_ref)
        addprop("Value", value, val_at[0], val_at[1],
                val_at[2] if len(val_at) > 2 else 0, hide=hide_value)
        addprop("Footprint", footprint, x, y, 0, hide=True)
        addprop("Datasheet", datasheet, x, y, 0, hide=True)
        addprop("Description", description, x, y, 0, hide=True)
        if extra:
            for k, v in extra:
                addprop(k, v, x, y, 0, hide=True)
        pin_lines = []
        for p in pins:
            if p['unit'] not in (0, unit):
                continue
            dx, dy = transform(p['x'], p['y'], rot, mirror)
            sx, sy = x + dx, y + dy
            if p['number']:
                ox, oy = pin_outward(p['angle'], rot, mirror)
                self.pins[(ref, p['number'])] = (sx, sy, ox, oy)
                pin_lines.append("\t\t(pin \"%s\" (uuid \"%s\"))\n"
                                 % (p['number'], self._u()))
        self.items.append(
            "\t(symbol\n\t\t(lib_id \"%s:%s\")\n\t\t(at %s %s %d)\n\t\t(unit %d)\n"
            "\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n"
            "\t\t(uuid \"%s\")\n%s%s"
            "\t\t(instances (project \"%s\" (path \"/%s\" (reference \"%s\") (unit %d))))\n\t)"
            % (lib, name, fmt(x), fmt(y), rot, unit, u,
               "".join(props), "".join(pin_lines),
               self.title.replace(' ', '_'), self.root_uuid, ref, unit))
        return self

    def power(self, sym, ref, x, y, rot=0):
        """Power symbol (GND, +12V ...).  Its single pin lands on (x, y)."""
        return self.place("power", sym, ref, sym, x, y, rot=rot,
                          hide_ref=True, hide_value=False,
                          description="Power symbol")

    # ---------- net helpers ----------
    def pin_xy(self, ref, pin):
        return self.pins[(ref, pin)][:2]

    def stub(self, ref, pin, length=2.54, net=None, label=True,
             size=1.27, lab_dy=0.0):
        """Draw a stub wire from a pin outwards; optionally label its end."""
        x, y, ox, oy = self.pins[(ref, pin)]
        ex, ey = x + ox * length, y + oy * length
        self.wire(x, y, ex, ey)
        if net:
            self.nets.setdefault(net, []).append((ref, pin, ex, ey))
            if label:
                if oy == 0:      # horizontal pin
                    rot = 0
                    just = "left bottom" if ox > 0 else "right bottom"
                    self.label(net, ex, ey + lab_dy, rot, just, size)
                else:            # vertical pin -> vertical text
                    rot = 90
                    just = "left bottom" if oy < 0 else "right bottom"
                    self.label(net, ex, ey + lab_dy, rot, just, size)
        return (ex, ey)

    def connect_power(self, ref, pin, sym, length=2.54):
        """Stub from a pin straight into a power symbol pin."""
        x, y, ox, oy = self.pins[(ref, pin)]
        ex, ey = x + ox * length, y + oy * length
        self.wire(x, y, ex, ey)
        rot = {(0, -1): 0, (0, 1): 180, (-1, 0): 90, (1, 0): 270}[(ox, oy)]
        self.power(sym, "#PWR%03d" % (1000 + self.n), ex, ey, rot=rot)
        return (ex, ey)

    def pwr_flag(self, net, x, y, rot=0):
        self.place("power", "PWR_FLAG", "#FLG%03d" % (2000 + self.n), "PWR_FLAG",
                   x, y, rot=rot, hide_value=True, description="Power flag")
        self.wire(x, y, x, y + 2.54)
        self.label(net, x, y + 2.54, 90, "left bottom")
        return (x, y)

    def nc(self, ref, pin):
        x, y = self.pins[(ref, pin)][:2]
        self.noconnect(x, y)

    # ---------- output ----------
    def save(self, path):
        libs = "\n".join(self.libdefs[k] for k in sorted(self.libdefs))
        body = "\n".join(self.items)
        s = (
            "(kicad_sch\n\t(version 20250114)\n\t(generator \"eeschema\")\n"
            "\t(generator_version \"9.0\")\n\t(uuid \"%s\")\n\t(paper \"%s\")\n"
            "\t(title_block\n\t\t(title \"%s\")\n\t\t(company \"%s\")\n\t\t(rev \"%s\")\n\t)\n"
            "\t(lib_symbols\n%s\n\t)\n%s\n"
            "\t(sheet_instances\n\t\t(path \"/\" (page \"1\"))\n\t)\n"
            "\t(embedded_fonts no)\n)\n"
        ) % (self.root_uuid, self.paper, self.title, self.company, self.rev,
             libs, body)
        with open(path, "w", encoding="utf-8") as f:
            f.write(s)
        return path
