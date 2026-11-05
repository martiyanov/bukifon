# 66. UX patterns → firmware implementation (docs/65)

**Status:** GEN functions + GEN page + presets/A-B/multi-select/mod-visible are
implemented in the portable firmware and rendered by the host demo; host tests
are green.  NVS/flash persistence of presets and the LED/WS2812 palette remain
`TODO(hw)`.

Sources: [UX patterns](65-ux-patterns.md), [palette](62-screen-palette.md),
[sequencer/gen code](../firmware/src/io/gen.cpp), [UI code](../firmware/src/ui/ui800.cpp).

---

## 1. Coverage table

| # | UX pattern (docs/65) | Implementation (firmware/demo) | Test |
|---:|---|---|---|
| 1 | L1 always on screen: play/filter/seq/mute | MAIN: 4 tracks, playhead, transport, 8 params; no menu needed | `Ui800TracksAndParams`, demo screenshots |
| 2 | L2 ≤1 gesture: pages/tabs | 5-tab strip MAIN/SEQ/MIX/MOD/GEN in the header; page switch is one tab | `UiGenTabDispatch`, `UiModesSnapshotFields` |
| 3 | L3 ≤2 gestures: generative functions | **GEN page** (5th tab) with PROB/EUCLID/MUTATE/SCALE/ARP RATE/ARP MODE/EVOLVE/SEED; one tab + encoder | `UiGenSnapshotFields`, `UiGenScreenRendersAllThemes` |
| 4 | Modulation is visible | `paramModulated[]` in the snapshot → "M" marker on the parameter cell (CUTOFF/LFO in the demo); cut-off value shown post-modulation by the simulator | `UiGenModMarkerAndMultiSelectAffectPixels`, `UiTheme…` |
| 5 | Multi-select / group editing | `genPartSelected[4]`; GEN part chips show `*` and selected border; group line "GROUP: 1 3"; params are edited for the selected group (host demo/API) | `UiGenSnapshotFields`, `UiGenModMarkerAndMultiSelectAffectPixels` |
| 6 | Scenes A/B | `abCompare`/`abShowB` snapshot fields + A/B indicator on GEN page; A/B preset slots can be compared via `PresetBank` | `UiGenPresetsAndAbCompare`, `PresetBankOverwriteAndAbCompareSources` |
| 7 | Undo/pickup | Sequencer already has `undo()` (Elektron workflow); pickup is UI-side (not in this round) | existing `SequencerUndo` tests |
| 8 | GEN functions work and are clear | `io/gen.*`: PROB 0–100 %, EUCLID 0–16 (Euclidean mask, accents on 1/5/9/13), MUTATE ±0–12 semitones `hash(seed,part,step)`, SCALE LOCK OFF/MINOR/MAJOR/PENTA/DORIAN, EVOLVE at bar boundary, SEED, ARP 1/8/1/16/1/32 × UP/DOWN/UPDOWN | `GenHashIsDeterministic`, `GenProbability…`, `GenEuclid…`, `GenMutate…`, `GenScaleLockAllScales`, `GenEvolve…`, `GenArpRatesAndModes`, `SequencerGen…` |
| 9 | Aesthetics: 4 themes, AA contrast | Palette tokens (docs/62) in `ui800.cpp` + `menu.cpp`; GEN page uses the same tokens | `UiTheme…` (10 tests) |
| 10 | Portability: 16 encoders / 42 keys / 2 faders, no extra buttons | GEN parameters map to the 8 encoder cells + hints; no new physical controls; multi-select via part chips/shift on hardware | `UiGenTabDispatch`, `UiGenSnapshotFields` |
| 11 | Presets: 8 slots + compare | `storage/preset_bank.*`: 8 versioned slots, per-part GenParams, multi-select mask, host file (NVS on P4 TODO), `--preset PATH` CLI | `PresetBank…` (5 tests) |
| 12 | GEN on keys/encoders | API `Sequencer::setGenParams`, `GenParams` per part; engine applies probability/Euclid/mutate/scale on each step; ARP over held/active notes | `SequencerGenDeterministic`, `SequencerGenEuclidTriggerCount`, `SequencerGenScaleLockAndEvolve` |

## 2. What is implemented (concrete)

- **Engine/sequencer:** `firmware/src/io/gen.{hpp,cpp}` — pure deterministic
  functions + `GenParams`; `Sequencer::setGenParams(track, params)`,
  `setGenSeed`, per-step application in `triggerStep`, bar-boundary `EVOLVE`,
  simple `GenArp` (1/32-note tick, rates 1/8, 1/16, 1/32; UP/DOWN/UPDOWN).
  Defaults are neutral (probability 100, euclid 0, mutate 0, scale OFF, ARP off)
  so existing projects/songs are unchanged.
- **UI:** 5th tab **GEN**; part chips with multi-select `*` and border; 8
  function cells; Euclid ring (16 steps, accents outlined); SCALE name, ARP
  rate/mode, EVOLVE/SEED; 8 preset slot row with the selected slot; A/B STATUS
  and `A`/`B` indicator; `M` marker on modulated parameters; group line.
- **Presets:** 8 slots (`PresetBank`), host file with magic/version/CRC32;
  per-slot per-part `GenParams` + selection mask; A/B comparison sources.
- **CLI:** `bukifon_sim --preset PATH` loads/creates the 8-slot bank and prints
  `presets: N/8`; `--theme` remains (4 themes).
- **Screenshots:** `firmware/artifacts/ui/gen.png` (5th page), plus the 4 modes
  and 4 legacy pages; `run_sim_demo.sh` now produces **9** PNG.

## 3. Tests (248/248 host)

- GEN functions (12): determinism, probability bounds/distribution, Euclid
  mask/accents, mutate bounds, all scales, evolve, apply pipeline, ARP rates and
  modes; sequencer determinism (same seed => identical event stream), Euclid
  trigger count, scale-locked event notes, deterministic evolve.
- Presets (5): slot write/read, names/multi-select, host file roundtrip,
  corrupt/short file rejection, invalid arguments, overwrite/A/B sources.
- UI GEN (5): snapshot fields, render in 4 themes, mod-marker + multi-select
  affect pixels, preset slot/A-B state, 5th-tab dispatch.
- Existing 226 tests are untouched and green; total **248/248**.

## 4. What remains (`TODO(hw)` / next)

1. **NVS/flash preset storage on P4** — host file and format are ready; the
   device backend (NVS namespace or `factory_data` partition) is TODO.
2. **LED/WS2812 palette** — LEDs still use their own colors; map them to the
   active theme (docs/62) when the LED driver is brought up.
3. **Pickup/undo UX polish** — sequencer undo exists; pickup/gesture tests are
   keyboard/mouse-side (demo) and hardware shift/long-press mapping remains.
4. **EEPROM/flash identity link** — presets are not yet bound to the unit
   identity (docs/55); fine for founders beta.
5. **Hardware timing** — GEN/UI render in the host; P4 bring-up + real
   encoder/keys timing is pending the P4 toolchain (docs/59).

## 5. How to run

```bash
make -C firmware/host test                 # 248/248
bash firmware/tests/run_sim_demo.sh        # 9 screenshots (GEN included)
firmware/host/build/bukifon_sim --preset /tmp/gen.bin   # create/load 8 slots
firmware/host/build/bukifon_sim --theme Cream --preset /tmp/gen.bin
```

GEN page: `firmware/artifacts/ui/gen.png`; snapshot fields are the contract
between engine/demo/UI (`UiSnapshot::gen`, `paramModulated`, `genPartSelected`,
`abCompare`, `presetNames`).
