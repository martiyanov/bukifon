#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bukifon founders-beta label sheet generator.

CSV columns (header required, one batch per file):
    serial,core_rev,panel_rev,pwr_rev,date,batch,test_result

Output:
    dist/labels/labels_<batch>.pdf    A4, 3x8 grid, 60x30 mm labels, QR
    dist/labels/labels_<batch>.json   manifest (serial + QR payload + factory link)
    --preview: dist/labels/labels_<batch>_preview.png (first 6 labels)

QR payload: BKS3-26A-0001|core=2.p4|panel=2|pwr=1|batch=26A|date=2026-11-05

Dependencies (installed in /tmp/msvenv during development):
    segno, reportlab, Pillow
    /tmp/msvenv/bin/pip install segno reportlab
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import io
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass

try:
    import segno
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
except ImportError as exc:  # pragma: no cover - environment error path
    sys.stderr.write(
        "missing dependency: %s\n"
        "install into the venv: /tmp/msvenv/bin/pip install segno reportlab\n" % exc
    )
    raise SystemExit(2)

LABEL_W_MM = 60
LABEL_H_MM = 30
COLS = 3
ROWS = 8
PAGE_MARGIN_MM = 10
GAP_X_MM = (210 - 2 * PAGE_MARGIN_MM - COLS * LABEL_W_MM) / (COLS - 1)
GAP_Y_MM = (297 - 2 * PAGE_MARGIN_MM - ROWS * LABEL_H_MM) / (ROWS - 1)
REQUIRED = ["serial", "core_rev", "panel_rev", "pwr_rev", "date", "batch", "test_result"]
SERIAL_RE = re.compile(r"^BKS3-(\d{2})([A-Z])-(\d{4})$")
REV_RE = re.compile(r"^[0-9A-Za-z.]+$")
TEST_VALUES = {"PASS", "FAIL", "RETEST"}


@dataclass
class Label:
    serial: str
    core_rev: str
    panel_rev: str
    pwr_rev: str
    date: str
    batch: str
    test_result: str

    @property
    def qr_payload(self) -> str:
        return (
            f"{self.serial}|core={self.core_rev}|panel={self.panel_rev}|"
            f"pwr={self.pwr_rev}|batch={self.batch}|date={self.date}"
        )


def die(message: str) -> None:
    sys.stderr.write("ERROR: %s\n" % message)
    raise SystemExit(1)


def validate_date(text: str) -> None:
    try:
        _dt.date.fromisoformat(text)
    except ValueError:
        die("invalid date %r (expected YYYY-MM-DD)" % text)


def validate_row(row: dict[str, str], line: int) -> Label:
    for key in REQUIRED:
        if key not in row or row[key] is None or row[key].strip() == "":
            die("line %d: missing %s" % (line, key))
    values = {key: row[key].strip() for key in REQUIRED}
    match = SERIAL_RE.match(values["serial"])
    if not match:
        die("line %d: serial %r must match BKS3-YYA-NNNN" % (line, values["serial"]))
    if values["batch"] != values["serial"][5:8]:
        die(
            "line %d: batch %r does not match serial batch %r"
            % (line, values["batch"], values["serial"][5:8])
        )
    for rev_key in ("core_rev", "panel_rev", "pwr_rev"):
        if not REV_RE.match(values[rev_key]):
            die("line %d: invalid %s %r" % (line, rev_key, values[rev_key]))
    validate_date(values["date"])
    if values["test_result"].upper() not in TEST_VALUES:
        die("line %d: test_result must be PASS/FAIL/RETEST" % line)
    values["test_result"] = values["test_result"].upper()
    return Label(**values)


def load_csv(path: str, batch_filter: str | None) -> tuple[str, list[Label]]:
    try:
        handle = open(path, newline="", encoding="utf-8")
    except OSError as exc:
        die("cannot open CSV %s: %s" % (path, exc))
    with handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            die("empty CSV")
        missing = [key for key in REQUIRED if key not in reader.fieldnames]
        if missing:
            die("CSV missing columns: %s" % ", ".join(missing))
        labels: list[Label] = []
        seen: dict[str, int] = {}
        for line, row in enumerate(reader, start=2):
            label = validate_row(row, line)
            if label.serial in seen:
                die("duplicate serial %s (lines %d and %d)" % (label.serial, seen[label.serial], line))
            seen[label.serial] = line
            labels.append(label)
    if not labels:
        die("CSV has no labels")
    batches = {label.batch for label in labels}
    if len(batches) != 1:
        die("CSV mixes batches: %s (one batch per sheet)" % ", ".join(sorted(batches)))
    batch = batches.pop()
    if batch_filter and batch_filter != batch:
        die("CSV batch %s != requested --batch %s" % (batch, batch_filter))
    if len(labels) > COLS * ROWS:
        die("%d labels do not fit one A4 sheet (%d max)" % (len(labels), COLS * ROWS))
    return batch, labels


def qr_png(payload: str, scale: int = 6) -> bytes:
    code = segno.make(payload, error="m")
    buffer = io.BytesIO()
    code.save(buffer, kind="png", scale=scale, border=2)
    return buffer.getvalue()


def label_xy(col: int, row: int) -> tuple[float, float]:
    x = (PAGE_MARGIN_MM + col * (LABEL_W_MM + GAP_X_MM)) * mm
    # PDF origin is bottom-left: row 0 is the top row.
    y = (297 - PAGE_MARGIN_MM - (row + 1) * LABEL_H_MM - row * GAP_Y_MM) * mm
    return x, y


def build_pdf(labels: list[Label], batch: str, path: str) -> None:
    page = canvas.Canvas(path, pagesize=A4)
    page.setTitle("Bukifon labels %s" % batch)
    for index, label in enumerate(labels):
        col = index % COLS
        row = index // COLS
        x, y = label_xy(col, row)
        w = LABEL_W_MM * mm
        h = LABEL_H_MM * mm
        page.setLineWidth(0.25)
        page.setStrokeColorRGB(0.35, 0.35, 0.35)
        page.rect(x, y, w, h)
        # Cut/corner marks.
        page.setStrokeColorRGB(0.75, 0.75, 0.75)
        page.line(x + 2 * mm, y + h + 1 * mm, x + 8 * mm, y + h + 1 * mm)
        qr_bytes = qr_png(label.qr_payload)
        qr_size = 23 * mm
        page.drawImage(
            ImageReader(io.BytesIO(qr_bytes)),
            x + w - qr_size - 2 * mm,
            y + 2 * mm,
            width=qr_size,
            height=qr_size,
        )
        page.setFillColorRGB(0, 0, 0)
        page.setFont("Helvetica-Bold", 8.5)
        page.drawString(x + 2 * mm, y + h - 7 * mm, label.serial)
        page.setFont("Helvetica", 4.4)
        page.drawString(
            x + 2 * mm,
            y + h - 11.5 * mm,
            "CORE %s  PANEL %s  PWR %s" % (label.core_rev, label.panel_rev, label.pwr_rev),
        )
        page.drawString(
            x + 2 * mm,
            y + h - 15 * mm,
            "BATCH %s  %s" % (label.batch, label.date),
        )
        page.setFont("Helvetica-Bold", 5.2)
        page.drawString(x + 2 * mm, y + 4.2 * mm, "TEST %s" % label.test_result)
        page.setFont("Helvetica", 3.4)
        page.drawString(x + 2 * mm, y + 2 * mm, "BUKIFON founders beta")
        if index + 1 < len(labels) and (index + 1) % (COLS * ROWS) == 0:
            page.showPage()
    page.save()


def _font(size: int):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_preview(labels: list[Label], batch: str, path: str) -> None:
    first = labels[:6]
    cols, rows = 2, 3
    dpi = 300
    mm_px = dpi / 25.4
    label_w = int(LABEL_W_MM * mm_px)
    label_h = int(LABEL_H_MM * mm_px)
    margin = int(6 * mm_px)
    gap = int(4 * mm_px)
    canvas_w = margin * 2 + cols * label_w + (cols - 1) * gap
    canvas_h = margin * 2 + rows * label_h + (rows - 1) * gap
    image = Image.new("RGB", (canvas_w, canvas_h), "white")
    draw = ImageDraw.Draw(image)
    big = _font(34)
    small = _font(15)
    tiny = _font(12)
    test_font = _font(18)
    for index, label in enumerate(first):
        col = index % cols
        row = index // cols
        x = margin + col * (label_w + gap)
        y = margin + row * (label_h + gap)
        draw.rectangle([x, y, x + label_w, y + label_h], outline=(80, 80, 80), width=1)
        qr = Image.open(io.BytesIO(qr_png(label.qr_payload, scale=12))).convert("RGB")
        qr = qr.resize((int(23 * mm_px), int(23 * mm_px)), Image.NEAREST)
        image.paste(qr, (x + label_w - qr.width - int(2 * mm_px), y + label_h - qr.height - int(2 * mm_px)))
        draw.text((x + int(2 * mm_px), y + int(2 * mm_px)), label.serial, fill="black", font=big)
        draw.text((x + int(2 * mm_px), y + int(2 * mm_px) + 42),
                  "CORE %s  PANEL %s  PWR %s" % (label.core_rev, label.panel_rev, label.pwr_rev),
                  fill="black", font=small)
        draw.text((x + int(2 * mm_px), y + int(2 * mm_px) + 64),
                  "BATCH %s  %s" % (label.batch, label.date), fill="black", font=small)
        draw.text((x + int(2 * mm_px), y + label_h - int(5 * mm_px)), "TEST %s" % label.test_result,
                  fill="black", font=test_font)
        draw.text((x + int(2 * mm_px), y + label_h - int(1.5 * mm_px)), "BUKIFON founders beta",
                  fill=(90, 90, 90), font=tiny)
    image.save(path, "PNG")


def write_manifest(labels: list[Label], batch: str, path: str) -> None:
    manifest = {
        "schema": "bukifon-labels-v1",
        "batch": batch,
        "count": len(labels),
        "factory_report": "factory --json (same serial/test_result per unit)",
        "labels": [
            {
                "serial": label.serial,
                "qr": label.qr_payload,
                "core_rev": label.core_rev,
                "panel_rev": label.panel_rev,
                "pwr_rev": label.pwr_rev,
                "date": label.date,
                "batch": label.batch,
                "test_result": label.test_result,
            }
            for label in labels
        ],
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def make_sheet(csv_path: str, out_dir: str, preview: bool, batch_filter: str | None) -> None:
    batch, labels = load_csv(csv_path, batch_filter)
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, "labels_%s.pdf" % batch)
    build_pdf(labels, batch, pdf_path)
    manifest_path = os.path.join(out_dir, "labels_%s.json" % batch)
    write_manifest(labels, batch, manifest_path)
    print("labels: %d, batch %s" % (len(labels), batch))
    print("PDF:    %s" % pdf_path)
    print("manifest: %s" % manifest_path)
    for label in labels[:3]:
        print("  %s  QR: %s" % (label.serial, label.qr_payload))
    if preview:
        preview_path = os.path.join(out_dir, "labels_%s_preview.png" % batch)
        build_preview(labels, batch, preview_path)
        print("preview: %s (first %d labels)" % (preview_path, min(6, len(labels))))


def selftest() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = os.path.join(tmp, "batch26A.csv")
        rows = ["serial,core_rev,panel_rev,pwr_rev,date,batch,test_result"]
        for index in range(1, 25):
            rows.append("BKS3-26A-%04d,2.p4,2,1,2026-11-05,26A,%s" %
                        (index, "PASS" if index % 5 else "FAIL"))
        with open(csv_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(rows) + "\n")
        out = os.path.join(tmp, "out")
        batch, labels = load_csv(csv_path, None)
        if batch != "26A" or len(labels) != 24:
            die("selftest: CSV parse failed")
        pdf_path = os.path.join(out, "labels_26A.pdf")
        os.makedirs(out, exist_ok=True)
        build_pdf(labels, batch, pdf_path)
        write_manifest(labels, batch, os.path.join(out, "labels_26A.json"))
        build_preview(labels, batch, os.path.join(out, "labels_26A_preview.png"))
        if os.path.getsize(pdf_path) < 1000:
            die("selftest: PDF too small")
        if not labels[0].qr_payload.startswith("BKS3-26A-0001|core=2.p4|panel=2|pwr=1"):
            die("selftest: QR payload format mismatch")
        # validation must reject duplicates and bad serials
        bad = os.path.join(tmp, "bad.csv")
        with open(bad, "w", encoding="utf-8") as handle:
            handle.write("serial,core_rev,panel_rev,pwr_rev,date,batch,test_result\n")
            handle.write("BKS3-26A-0001,2.p4,2,1,2026-11-05,26A,PASS\n")
            handle.write("BKS3-26A-0001,2.p4,2,1,2026-11-05,26A,PASS\n")
        try:
            load_csv(bad, None)
        except SystemExit:
            pass
        else:
            die("selftest: duplicate serial was accepted")
        print("SELFTEST PASS: PDF/manifest/preview generated, duplicate SN rejected")
        print("  sample QR: %s" % labels[0].qr_payload)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Bukifon founders-beta label sheets")
    parser.add_argument("csv", nargs="?", help="CSV with serial,core_rev,panel_rev,pwr_rev,date,batch,test_result")
    parser.add_argument("--out", default="dist/labels", help="output directory (default dist/labels)")
    parser.add_argument("--preview", action="store_true", help="also write PNG preview of the first 6 labels")
    parser.add_argument("--batch", help="expected batch (e.g. 26A); validated against the CSV")
    parser.add_argument("--selftest", action="store_true", help="run internal self-test (no input CSV)")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.csv:
        parser.error("CSV path is required (or use --selftest)")
    make_sheet(args.csv, args.out, args.preview, args.batch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
