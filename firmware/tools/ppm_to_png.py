#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Convert Bukifon UI screenshots from binary PPM (P6) to PNG.

Usage:
    python3 firmware/tools/ppm_to_png.py firmware/artifacts/ui [--out DIR]

The host simulator writes 800x480 PPM files (no third-party deps on the C++
side); PNG conversion uses Pillow.  The PNG files are the deliverable UI
screenshots: main.png, sequencer.png, mixer.png, modules.png.
"""
import argparse
import os
import sys

from PIL import Image


def read_ppm(path):
    with open(path, "rb") as f:
        magic = f.readline().strip()
        if magic != b"P6":
            raise ValueError(f"{path}: expected P6 PPM, got {magic!r}")
        line = f.readline()
        while line.startswith(b"#"):
            line = f.readline()
        width, height = map(int, line.split())
        maxval = int(f.readline().strip())
        if maxval != 255:
            raise ValueError(f"{path}: unsupported maxval {maxval}")
        data = f.read(width * height * 3)
        if len(data) != width * height * 3:
            raise ValueError(f"{path}: truncated pixel data")
        return Image.frombytes("RGB", (width, height), data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="directory with .ppm screenshots")
    parser.add_argument("--out", default=None, help="output directory (default: source)")
    args = parser.parse_args()
    out_dir = args.out or args.source
    os.makedirs(out_dir, exist_ok=True)
    count = 0
    for name in sorted(os.listdir(args.source)):
        if not name.lower().endswith(".ppm"):
            continue
        src = os.path.join(args.source, name)
        dst = os.path.join(out_dir, name[:-4] + ".png")
        image = read_ppm(src)
        image.save(dst, format="PNG")
        print(f"{src} -> {dst} ({image.width}x{image.height})")
        count += 1
    if count == 0:
        print("ERROR: no .ppm screenshots found", file=sys.stderr)
        return 1
    print(f"converted {count} screenshot(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
