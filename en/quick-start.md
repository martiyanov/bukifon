# Bukifon quick start: an idea in 10 minutes

Short guide for a new owner. Full Russian version — [../77-quick-start.md](../77-quick-start.md).

## 0. Power on (0:30)

1. Connect USB-C (power + data) or external PSU.
2. Wait 2–3 s for the logo; screen shows **PART 1 · SELECTED · PAGE MAIN**.
3. Need the mic? Turn **SW1/SW3 (MIC)** on the case; **MIC ON** LED lights.

## 1. Make sound (1 min)

- Press any key — the current preset plays. Turn **А–Г** (top-left encoders) for MAIN page params.
- **PLAY** starts the sequencer, **STOP** stops it; **HOME** returns to MAIN in one gesture.

## 2. Find a parameter (2 min)

- **Mirrored map:** each encoder has its own on-screen cell — left 8 (А–З) = page,
  right 8 (И–П) = macros (CUT/RES/ATK/REL/DLY/DRV/CRSH/MST).
- Pages: **MAIN/FM/ENV/FX/GEN/EXT/MIC** (L2 = one gesture).
- Hold **Shift** for gesture/shortcut hints.

## 3. Your own idea (3 min)

- **Sequencer:** 16 steps, 4 internal parts + 8 external MIDI tracks (EXT).
- **GEN:** PROB/EUCLID/MUTATE/SCALE/ARP/EVOLVE on the selected track; **UNDO** reverts (Ctrl+Z).
- **Record:** REC + play; **resample:** REC at any time → pad.

## 4. Voice (3 min)

- **MIC → REC MIC** → pad “VOICE nn” (up to 30 s, silence trimmed).
- **BEATBOX → STEPS:** tap a rhythm — steps fill with kick/snare/hat; UNDO reverts.
- **Vocoder** — v1.1 (backlog); for now the voice is a sample/rhythm.

## 5. External synths (2 min)

1. DIN OUT (or USB-MIDI) → external synth; channel/PC on the **EXT** page.
2. Transport/clock shared: PLAY/STOP, 24 ppqn clock.
3. CC p-lock: hold a step + turn an encoder (1 CC per track in v1.0-rc).
4. Save/load: **SAVE** / **LOAD** (project v2 `.bkfp`).

## 6. Troubleshooting

| Symptom | Fix |
|---|---|
| No sound | MASTER/VOL, PAIR LEVEL, part mute, output jack |
| Mic silent | SW1/SW3 on? GAIN/THRESH on MIC page; MIC ON LED |
| Beatbox not writing | SENS/THRESH, less room noise, closer to mic |
| Sequencer not running | PLAY, BPM, pattern not empty; EXT tracks — channel/PC |
| External synth silent | MIDI channel, DIN OUT (not IN), clock/transport |

## 7. Next

- power-on self-test (21 items) — see [../42-dfm-review-gpt.md](../42-dfm-review-gpt.md);
- firmware update over USB; limitations — [../76-known-limitations.md](../76-known-limitations.md);
- build/repair — [../72-assembly-workshops.md](../72-assembly-workshops.md), [../34-assembly.md](../34-assembly.md).
