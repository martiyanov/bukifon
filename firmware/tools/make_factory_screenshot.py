#!/usr/bin/env python3
"""Render the factory self-test station screen (docs/42/DFM 21 checks) to PNG."""
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "factory" / "selftest.png"
REPORT = subprocess.run([str(ROOT / "host" / "build" / "bukifon_factory"), "--json"],
                        capture_output=True, text=True, check=True).stdout
report = json.loads(REPORT)

W, H = 800, 480
BG = (10, 26, 29)
PANEL = (13, 36, 40)
CARD = (14, 32, 36)
LINE = (30, 58, 63)
TEXT = (215, 236, 239)
MUTED = (127, 182, 188)
GREEN = (56, 193, 114)
ORANGE = (246, 153, 63)
RED = (255, 92, 92)
ACCENT = (79, 209, 224)
img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
font_path = "/System/Library/Fonts/Supplemental/DejaVuSansMono.ttf"
try:
    mono = ImageFont.truetype(font_path, 14)
    mono_small = ImageFont.truetype(font_path, 12)
    title_font = ImageFont.truetype(font_path, 26)
    big = ImageFont.truetype(font_path, 24)
except OSError:
    mono = mono_small = title_font = big = ImageFont.load_default()

d.rectangle([0, 0, W, 68], fill=PANEL)
d.rectangle([0, 66, W, 68], fill=ACCENT)
d.text((12, 8), "BUKIFON", font=title_font, fill=ACCENT)
d.text((12, 44), "FACTORY SELF-TEST · CORE-2 / P4", font=mono_small, fill=MUTED)
d.text((470, 6), "21/21", font=big, fill=GREEN if report["overall_pass"] else RED)
d.text((472, 36), f"{report['pass']} PASS · {report['fail']} FAIL · {report['skip']} SKIP",
       font=mono_small, fill=MUTED)
d.text((640, 6), "docs/42", font=mono_small, fill=ORANGE)
d.text((640, 22), "DFM CORE-2 §2", font=mono_small, fill=MUTED)

y = 78
for i, test in enumerate(report["tests"]):
    col = i // 11
    row = i % 11
    x = 10 + col * 392
    yy = 78 + row * 32
    d.rectangle([x, yy, x + 380, yy + 28], fill=CARD, outline=LINE)
    status = test["status"]
    color = {"PASS": GREEN, "FAIL": RED, "SKIP": ORANGE}.get(status, MUTED)
    d.text((x + 6, yy + 2), f"{i + 1:02d}", font=mono_small, fill=MUTED)
    d.text((x + 32, yy + 2), test["name"], font=mono, fill=TEXT)
    d.text((x + 236, yy + 2), status, font=mono_small, fill=color)
    d.text((x + 6, yy + 15), test["detail"][:58], font=mono_small, fill=MUTED)
d.rectangle([0, 434, W, 480], fill=PANEL)
d.text((12, 444), "MOCK HARDWARE · station report: tests/out/factory_report.json",
       font=mono_small, fill=MUTED)
d.text((610, 440), "HOME  ESC", font=mono, fill=ACCENT)
OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print(f"wrote {OUT}")
