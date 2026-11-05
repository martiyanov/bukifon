#!/usr/bin/env python3
"""Склейка: эталон заказчика (верх) vs мой эскиз (низ) — для точного diff."""
import os
from PIL import Image

REF = "~/.zcode/cli/image-cache/sess_2a9e5206-3359-479d-9f72-d9f7e3203971/image-637f5da3ade50873dfde9062dff83aa1.png"
MINE = "<repo>/renders/templates/bukifon_v1_7_full.png"
OUT = "<repo>/renders/templates/v1_7_diff_ref_vs_mine.png"

a, b = Image.open(REF).convert("RGB"), Image.open(MINE).convert("RGB")
W = 1400
a = a.resize((W, int(a.height * W / a.width)))
b = b.resize((W, int(b.height * W / b.width)))
gap = 46
canvas = Image.new("RGB", (W, a.height + gap + b.height), (255, 255, 255))
canvas.paste(a, (0, 0))
canvas.paste(b, (0, a.height + gap))
canvas.save(OUT)
print(OUT, canvas.size)
