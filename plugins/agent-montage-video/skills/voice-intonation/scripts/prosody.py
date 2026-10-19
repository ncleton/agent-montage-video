#!/usr/bin/env python3
"""Intonation report for voice-over files: pitch range and movement, pauses, speaking rate.

Usage: prosody.py file.mp3 [file2 ...]
A flat, robotic read shows a narrow pitch spread (std below ~2 semitones), little
movement between words and almost no pauses. Natural narration is usually 2.5-4.5 st.
"""
import subprocess, sys, json, os
import numpy as np

SR = 16000
def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

def f0_track(x, frame=0.04, hop=0.01, fmin=70, fmax=350):
    n, h = int(frame * SR), int(hop * SR)
    lo, hi = int(SR / fmax), int(SR / fmin)
    f0, energy = [], []
    win = np.hanning(n)
    for i in range(0, len(x) - n, h):
        s = x[i:i + n] * win
        e = float(np.sqrt(np.mean(s ** 2)))
        energy.append(e)
        if e < 0.01:
            f0.append(np.nan); continue
        ac = np.fft.irfft(np.abs(np.fft.rfft(s, 2 * n)) ** 2)[:n]
        if ac[0] <= 0: f0.append(np.nan); continue
        ac = ac / ac[0]
        k = lo + int(np.argmax(ac[lo:hi]))
        f0.append(SR / k if ac[k] > 0.45 else np.nan)
    return np.array(f0), np.array(energy)

def report(path):
    x = load(path)
    f0, en = f0_track(x)
    v = f0[~np.isnan(f0)]
    st = 12 * np.log2(v / np.median(v))
    st = st[np.abs(st) < 12]
    # pitch movement: semitone change between consecutive 200 ms windows of voiced speech
    seg = [np.median(c[~np.isnan(c)]) for c in (f0[i:i + 20] for i in range(0, len(f0) - 20, 20)) if np.any(~np.isnan(c))]
    seg = np.array([s for s in seg if not np.isnan(s)])
    move = np.abs(np.diff(12 * np.log2(seg))) if len(seg) > 2 else np.array([0.0])
    speech = en > 0.01
    # pauses longer than 250 ms
    pauses, run = 0, 0
    for s in speech:
        run = run + 1 if not s else 0
        if run == 25: pauses += 1
    dur = len(x) / SR
    return {"file": os.path.basename(path), "dur": round(dur, 2), "pitch_std_st": round(float(np.std(st)), 2),
            "pitch_range_st": round(float(np.percentile(st, 95) - np.percentile(st, 5)), 2),
            "movement_st": round(float(np.median(move)), 2), "pauses_per_min": round(pauses / dur * 60, 1),
            "median_f0": round(float(np.median(v)), 1)}

if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(json.dumps(report(p)))

