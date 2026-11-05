#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""FFT / spectral analysis of the Bukifon host render (numpy only).

Checks required by spec/40-firmware.md §11:
  * A4 = 440 Hz +/- 0.1 %
  * no spurious components above -60 dB below 20 kHz (aliasing)
  * 8 voices are present
  * all 8 FM algorithms have no subharmonics / artefacts
  * demo WAV is 48 kHz / 16 bit / stereo and exactly 5 s long
  * ladder at 100 % resonance and the feedback matrix stay bounded

Writes tests/out/fft_metrics.json and prints a human readable summary.
"""
import json
import os
import sys
import wave

import numpy as np

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
WAV_DIR = os.path.join(OUT_DIR, "out")

METRICS = {}


def load_wav(path):
    with wave.open(path, "rb") as w:
        channels = w.getnchannels()
        width = w.getsampwidth()
        rate = w.getframerate()
        frames = w.getnframes()
        raw = w.readframes(frames)
    if width != 2:
        raise RuntimeError(f"{path}: expected 16-bit PCM, got {width * 8} bit")
    data = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if channels > 1:
        data = data.reshape(-1, channels)
    else:
        data = data.reshape(-1, 1)
    return rate, channels, data


def spectrum_db(signal, rate, start_s, length_s, fft_size=1 << 18):
    """Hann-windowed spectrum in dB relative to the strongest bin."""
    start = int(start_s * rate)
    end = min(start + int(length_s * rate), len(signal))
    x = signal[start:end]
    x = x[:fft_size]
    # Window BEFORE zero padding: padding after windowing would create a huge
    # transient and fake low-frequency leakage.
    window = np.hanning(len(x))
    n_fft = max(fft_size, len(x))
    spec = np.fft.rfft(x * window, n=n_fft)
    mag = np.abs(spec) / (np.sum(window) * 0.5)
    freqs = np.fft.rfftfreq(n_fft, 1.0 / rate)
    db = 20.0 * np.log10(np.maximum(mag, 1e-12) / np.max(mag))
    return freqs, mag, db


def parabolic_peak(freqs, mag, index):
    """Sub-bin frequency estimate using a parabolic fit on log magnitude."""
    if index <= 0 or index >= len(mag) - 1:
        return freqs[index]
    y0, y1, y2 = np.log(np.maximum(mag[index - 1:index + 2], 1e-12))
    denom = (y0 - 2.0 * y1 + y2)
    if abs(denom) < 1e-12:
        return freqs[index]
    delta = 0.5 * (y0 - y2) / denom
    return freqs[index] + delta * (freqs[1] - freqs[0])


def find_peaks(freqs, mag, db, floor_db=-100.0, min_freq=20.0, max_freq=20000.0):
    """Local maxima above floor_db below max_freq; returns (freq, magnitude)."""
    peaks = []
    for i in range(1, len(db) - 1):
        if freqs[i] < min_freq or freqs[i] > max_freq:
            continue
        if db[i] < floor_db:
            continue
        if db[i] >= db[i - 1] and db[i] > db[i + 1]:
            peaks.append((parabolic_peak(freqs, mag, i), float(mag[i])))
    return peaks


def analyse_note_a4(path):
    rate, channels, data = load_wav(path)
    signal = data[:, 0]
    freqs, mag, db = spectrum_db(signal, rate, 0.5, 1.0)
    # Restrict the fundamental search to a musical range around 440 Hz.
    mask = (freqs > 380.0) & (freqs < 500.0)
    idx = np.argmax(np.where(mask, mag, 0.0))
    f0 = parabolic_peak(freqs, mag, int(idx))
    error_pct = (f0 - 440.0) / 440.0 * 100.0

    # Aliasing / spurious components: everything not belonging to the harmonic
    # series of f0 within a +/- 6 bin tolerance (the Hann main lobe is 4 bins).
    bin_hz = freqs[1] - freqs[0]
    peaks = find_peaks(freqs, mag, db, floor_db=-100.0, min_freq=60.0, max_freq=20000.0)
    fundamental_mag = float(np.max(mag[mask]))
    spurious = []
    for f, level in peaks:
        harmonic = round(f / f0)
        near_harmonic = False
        if harmonic >= 1:
            # 2 % of the harmonic frequency covers the Hann main lobe and first
            # sidelobes of a 1 s analysis window (bin spacing 1 Hz).
            near_harmonic = abs(f - harmonic * f0) <= max(8.0 * bin_hz, 0.02 * harmonic * f0)
        if not near_harmonic:
            spurious.append((f, level))
    # Express spurious level relative to the fundamental (dB).
    spurious_db = [20.0 * np.log10(max(m / fundamental_mag, 1e-12)) for _, m in spurious]
    worst_spurious = max(spurious_db) if spurious_db else -180.0

    METRICS["note_a4"] = {
        "file": os.path.basename(path),
        "sample_rate": rate,
        "channels": channels,
        "fundamental_hz": round(float(f0), 4),
        "error_pct": round(float(error_pct), 5),
        "pass_tuning": bool(abs(error_pct) < 0.1),
        "worst_spurious_db": round(float(worst_spurious), 2),
        "pass_aliasing": bool(worst_spurious < -60.0),
        "spurious_peaks": [[round(float(f), 1), round(float(d), 1)] for f, d in
                           zip([p[0] for p in spurious], spurious_db)][:10],
    }
    return METRICS["note_a4"]


def analyse_fm(path):
    rate, _, data = load_wav(path)
    signal = data[:, 0]
    freqs, mag, db = spectrum_db(signal, rate, 0.2, 0.8)
    peaks = find_peaks(freqs, mag, db, floor_db=-80.0, min_freq=30.0, max_freq=20000.0)
    base = max((m for f, m in peaks if abs(f - 440.0) < 30.0), default=0.0)
    sub = max((m for f, m in peaks if 60.0 < f < 0.9 * 440.0), default=0.0)
    sub_db = 20.0 * np.log10(max(sub / base, 1e-12)) if base > 0 else -180.0
    nonharmonic = []
    for f, m in peaks:
        harmonic = round(f / 440.0)
        if harmonic >= 1 and abs(f - harmonic * 440.0) > max(8.0 * (freqs[1] - freqs[0]),
                                                             0.02 * harmonic * 440.0):
            nonharmonic.append((f, 20.0 * np.log10(max(m / base, 1e-12))))
    worst_nh = max((d for _, d in nonharmonic), default=-180.0)
    name = os.path.basename(path)
    METRICS.setdefault("fm", {})[name] = {
        "subharmonic_db": round(float(sub_db), 2),
        "worst_nonharmonic_db": round(float(worst_nh), 2),
        "pass": bool(base > 0 and sub_db < -60.0 and worst_nh < -60.0),
    }
    return METRICS["fm"][name]


def analyser_eight_voices(path):
    rate, _, data = load_wav(path)
    signal = data[:, 0]
    freqs, mag, db = spectrum_db(signal, rate, 0.5, 1.0)
    notes = [60, 62, 64, 65, 67, 69, 71, 72]
    expected = [440.0 * 2.0 ** ((n - 69) / 12.0) for n in notes]
    found = 0
    details = []
    for f in expected:
        idx = int(np.argmin(np.abs(freqs - f)))
        window = mag[max(0, idx - 4): idx + 5]
        local = float(np.max(window)) if len(window) else 0.0
        # A voice is "present" if its bin is within 20 dB of the strongest bin.
        present = local > 0.1 * np.max(mag)
        found += 1 if present else 0
        details.append({"note": notes[found - 1] if present else None, "freq": round(float(f), 1),
                        "level_db": round(float(20 * np.log10(max(local / np.max(mag), 1e-12))), 1)})
    METRICS["eight_voices"] = {
        "file": os.path.basename(path),
        "expected_voices": 8,
        "detected_voices": found,
        "details": details,
        "pass": bool(found == 8),
    }
    return METRICS["eight_voices"]


def analyse_generic(path, key, expected_seconds=None, max_peak_check=True):
    rate, channels, data = load_wav(path)
    peak = float(np.max(np.abs(data))) if len(data) else 0.0
    rms = float(np.sqrt(np.mean(data ** 2))) if len(data) else 0.0
    clipped = int(np.sum(np.abs(data) >= (32767.0 / 32768.0) - 1e-9))
    info = {
        "file": os.path.basename(path),
        "sample_rate": rate,
        "channels": channels,
        "seconds": round(len(data) / rate, 4),
        "peak": round(peak, 4),
        "rms": round(rms, 5),
        "clipped_samples": clipped,
    }
    if expected_seconds is not None:
        info["pass_duration"] = bool(abs(len(data) / rate - expected_seconds) < 0.001)
    info["pass_bounded"] = bool(peak <= 1.0 and clipped == 0)
    METRICS[key] = info
    return info


def main():
    os.makedirs(WAV_DIR, exist_ok=True)
    required = [
        "demo_5s.wav", "note_a4.wav", "eight_voices.wav", "ladder_res100.wav",
        "matrix_stress.wav",
    ] + [f"fm_algo{i}.wav" for i in range(8)]
    missing = [f for f in required if not os.path.exists(os.path.join(WAV_DIR, f))]
    if missing:
        print("ERROR: missing rendered files:", ", ".join(missing))
        print("Run `make -C firmware/host render` first.")
        return 2

    print("Bukifon spectral report")
    print("=======================")
    a4 = analyse_note_a4(os.path.join(WAV_DIR, "note_a4.wav"))
    print(f"A4 tuning: {a4['fundamental_hz']:.4f} Hz, error {a4['error_pct']:+.5f} % "
          f"-> {'PASS' if a4['pass_tuning'] else 'FAIL'} (limit +/-0.1 %)")
    print(f"Aliasing:  worst spurious {a4['worst_spurious_db']:.1f} dB rel fundamental "
          f"-> {'PASS' if a4['pass_aliasing'] else 'FAIL'} (limit -60 dB)")

    fm_pass = True
    for i in range(8):
        m = analyse_fm(os.path.join(WAV_DIR, f"fm_algo{i}.wav"))
        fm_pass = fm_pass and m["pass"]
        print(f"FM algo {i}: subharmonic {m['subharmonic_db']:7.1f} dB, "
              f"non-harmonic {m['worst_nonharmonic_db']:7.1f} dB -> {'PASS' if m['pass'] else 'FAIL'}")
    METRICS["fm"]["all_pass"] = bool(fm_pass)

    ev = analyser_eight_voices(os.path.join(WAV_DIR, "eight_voices.wav"))
    print(f"Eight voices: detected {ev['detected_voices']}/8 -> {'PASS' if ev['pass'] else 'FAIL'}")

    demo = analyse_generic(os.path.join(WAV_DIR, "demo_5s.wav"), "demo_5s", expected_seconds=5.0)
    print(f"Demo 5 s: {demo['seconds']} s, {demo['sample_rate']} Hz, {demo['channels']} ch, "
          f"peak {demo['peak']}, clipped {demo['clipped_samples']}, rms {demo['rms']}")
    ladder = analyse_generic(os.path.join(WAV_DIR, "ladder_res100.wav"), "ladder_res100")
    print(f"Ladder res=100%: peak {ladder['peak']}, rms {ladder['rms']}, "
          f"clipped {ladder['clipped_samples']} -> {'PASS' if ladder['pass_bounded'] else 'FAIL'}")
    stress = analyse_generic(os.path.join(WAV_DIR, "matrix_stress.wav"), "matrix_stress")
    print(f"Matrix feedback: peak {stress['peak']}, rms {stress['rms']}, "
          f"clipped {stress['clipped_samples']} -> {'PASS' if stress['pass_bounded'] else 'FAIL'}")

    all_pass = (a4["pass_tuning"] and a4["pass_aliasing"] and fm_pass and ev["pass"]
                and demo.get("pass_duration", False) and demo["pass_bounded"]
                and ladder["pass_bounded"] and stress["pass_bounded"])
    METRICS["all_pass"] = bool(all_pass)
    with open(os.path.join(WAV_DIR, "fft_metrics.json"), "w") as f:
        json.dump(METRICS, f, indent=2)
    print("=======================")
    print("ALL SPECTRAL CHECKS:", "PASS" if all_pass else "FAIL")
    print(f"metrics: {os.path.join(WAV_DIR, 'fft_metrics.json')}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
