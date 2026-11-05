# 55. Serial numbers, QR labels, identity and traceability (founders beta)

**Status:** label generator + identity format/CLI are implemented and host-tested;
printing a real label sheet is ready (`dist/labels/`).  Real **writing of
identity to flash `factory_data` / 24C32 is still TODO(hw)** — the two-slot
store model and validation contract are in firmware and covered by tests.

Related: [factory self-test](46-factory-test.md) (test result → `factory --json`),
[DFM/DFT review](42-dfm-review-gpt.md) §3, [RC definition](36-rc-definition.md).

---

## 1. Serial number format

```
BKS3-26A-0001
│    ││ │   └── unit number 0001..9999 (per batch, never reused)
│    ││ └────── batch letter A..Z (revision/line)
│    │└──────── production year 26 (2026)
│    └───────── product generation 3 (S3/P4 founders family)
└────────────── Bukifon prefix
```

- Regex (enforced by `identity.cpp` and `make_labels.py`):
  `^BKS3-[0-9]{2}[A-Z]-[0-9]{4}$` — exactly 13 characters.
- The 3-character batch token (`26A`) must equal the CSV/identity `batch` field.
- Numbers are allocated per batch; **duplicates are rejected** by the CSV tool
  and by the identity store.  A repaired unit keeps its SN; an RMA replacement
  gets a new SN and the old one is marked RMA/retired in the batch log.
- Product/board revs are separate fields (`core_rev` e.g. `2.p4`, `panel_rev`
  `2`, `pwr_rev` `1`), not embedded in the SN.

## 2. QR content

Machine format (fixed key order, no personal data):

```
BKS3-26A-0001|core=2.p4|panel=2|pwr=1|batch=26A|date=2026-11-05
```

- `serial` — as above;
- `core` / `panel` / `pwr` — board revisions of the tested unit;
- `batch` — production batch (matches SN);
- `date` — test/assembly date `YYYY-MM-DD`.

The same JSON identity (firmware `factory/identity.*`) contains additionally:
product, MAC (eFuse anchor), calibration version, test result, CRC32.  QR is the
*human/scanner* key; the full identity is read from flash with
`factory --print-identity` (CDC CLI).

## 3. Label sheet (3 × 8 on A4, label 60 × 30 mm)

`tools/make_labels.py`:

```bash
# dependencies (already installed in the dev venv)
/tmp/msvenv/bin/pip install segno reportlab

# validate + render one batch (24 labels = full A4 page)
/tmp/msvenv/bin/python3 tools/make_labels.py batch26A.csv \
    --out dist/labels --batch 26A --preview

# internal self-test (no input file): PDF + manifest + preview + duplicate check
/tmp/msvenv/bin/python3 tools/make_labels.py --selftest
```

Input CSV (header required, **one batch per file**, max 24 rows):

```csv
serial,core_rev,panel_rev,pwr_rev,date,batch,test_result
BKS3-26A-0001,2.p4,2,1,2026-11-05,26A,PASS
BKS3-26A-0002,2.p4,2,1,2026-11-05,26A,PASS
```

Outputs:

| File | Purpose |
|---|---|
| `dist/labels/labels_<batch>.pdf` | A4 print sheet, 3×8 labels, QR, cut marks |
| `dist/labels/labels_<batch>.json` | manifest: serial, QR payload, revs/date/test per unit |
| `dist/labels/labels_<batch>_preview.png` | `--preview`: first 6 labels at 300 dpi (visual check) |

Label content: large SN, `CORE/PANEL/PWR`, `BATCH/DATE`, `TEST PASS/FAIL/RETEST`,
QR (23 mm) and "BUKIFON founders beta".  The same sheet is regenerated from the
batch CSV; the manifest is the bridge to the factory report (same serials and
test results).

**Verification:** `--selftest` builds a 24-label PDF/manifest/preview and checks
that a duplicate SN is rejected; the current dev sheet is
`dist/labels/labels_26A.pdf` (24 labels, 125 KB) + preview.

## 4. Print media and placement

- **Thermal transfer** (preferred for 24+ units): resin ribbon, matte white
  polyester label stock, 60×30 mm, 300 dpi.  **Laser** (toner) acceptable for
  prototypes; **inkjet is not allowed** (smearing/solvent).
- Lamination: clear polyester overlaminate or varnish; labels must survive
  isopropyl wipe, 60 °C/24 h, and 10 open/close cycles.
- Placement: **long label inside the bottom lid** (next to the battery bay,
  visible on opening) with full SN + QR; **short 25×8 mm label on the outside
  bottom** with SN only.  Never place a label over a screw, FPC or vent.
- QR quiet zone ≥4 modules (~3 mm at 23 mm code); print at 100 % scale (no
  "fit to page"); verify with a phone/scanner before applying.
- Apply after the factory self-test PASS and after flashing the identity; the
  label SN must equal `factory --print-identity` serial and the QR payload.

## 5. Identity in firmware and link to the factory report

`firmware/src/factory/identity.*`:

- 114-byte little-endian record: magic `BKID`, version 1, product `BUKIFON`,
  serial, core/panel/pwr revs, date, batch, MAC (6 B), calibration version, test
  result, CRC32 (over the first 110 bytes).
- validation: magic/version/product/serial regex/date/batch↔serial/revs non-empty/
  MAC non-zero/CRC; JSON roundtrip and two-copy flash layout (`IdentityStore`,
  alternating slots, duplicate-SN rejection, corrupt-slot fallback).
- CLI (host/device):

```bash
make -C firmware/host factory
firmware/host/build/bukifon_factory --identity identity.json   # validate + store
firmware/host/build/bukifon_factory --print-identity           # print latest JSON
```

- The identity is written **after** `factory --json` PASS: same serial,
  same test result, same date/revs; store the JSON report next to the label
  manifest.  Real flash `factory_data` (two copies + CRC) and 24C32 calibration
  write are **TODO(hw)**; the `TODO` is explicit in `p4_hardware.cpp` /
  `identity.hpp`.

## 6. Batch / revision table (example)

| Batch | Date | CORE rev | PANEL rev | PWR rev | Units | Notes |
|---|---|---|---|---|---|---|
| 26A | 2026-11-05 | 2.p4 | 2 | 1 | 0001–0024 | founders beta, first 24 |
| 26B | 2026-12-10 | 2.p4 | 2 | 1 | 0025–0048 | after DFM fixes |
| 27A | 2027-01-15 | 2.p4-r2 | 2 | 1 | 0049–… | CORE-2 rev.2 |

Keep the authoritative table in the production tracker; labels/manifests are
generated from it (one CSV per batch).

## 7. RMA / traceability

1. Scan QR or read the short SN; look up the batch manifest
   (`dist/labels/labels_<batch>.json`) and the factory JSON report.
2. Check identity via `factory --print-identity` — serial/MAC/calibration
   version confirm the unit was not re-flashed with another identity.
3. Mark the SN as **RMA** in the batch log; do not reuse it.  Repaired units keep
   their SN; replacement units get a new SN/new label and a new identity record.
4. If the identity is missing/corrupt: use the two-copy store fallback; if both
   copies are bad, the unit is treated as unprovisioned (re-test + new identity,
   old SN retired).
5. Store RMA report with: SN, QR scan photo, `factory --json` output, failure
   symptom, repair action, operator/date.

## 8. What remains (TODO)

- **Real identity write** to flash `factory_data` (two copies + CRC) and 24C32
  calibration record — TODO(hw) on P4; host store is the validated contract.
- Print/durability validation: thermal transfer on the actual label stock,
  isopropyl/heat/cycle test, QR scan rate on the assembled case.
- Production CSV export from the factory station (serial allocation, test
  result import) — currently a manual CSV; the manifest format is ready.
- Label vendor/MPN and die-cut tolerance; outside short label placement drawing
  in the enclosure docs.
