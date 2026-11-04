#!/usr/bin/env python3
"""Shorten the long silences of narration takes without touching the speech.

  .venv/bin/python cap_pauses.py work/voice work/voice-tight 0.6 '{"A": "b", "B": "a"}'

For each chosen take <passage>-<take>.(mp3|wav) and its .stt.json (word timestamps), every gap between
two words longer than MAX seconds loses its middle part, only if that part is really silent (25 dB under
the take's average level); the word timestamps are shifted to match. Writes <passage>-<take>.wav and
.stt.json in the output folder, ready for split_voice.py. ElevenLabs v3 leaves 1 to 1.5 s between some
sentences: capping at 0.6 s saved 21 s on a 4 min 40 s video without any audible cut.
"""
import json, os, subprocess, sys
import numpy as np

src, dst, MAXG = sys.argv[1], sys.argv[2], float(sys.argv[3])
takes = json.loads(sys.argv[4])
os.makedirs(dst, exist_ok=True)
SR = 44100
for p, t in takes.items():
    base = os.path.join(src, "%s-%s" % (p, t))
    audio = next((base + e for e in (".wav", ".mp3") if os.path.exists(base + e)), None)
    if not audio:
        sys.exit("Missing take %s-%s in %s" % (p, t, src))
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", audio, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    stt = json.load(open(base + ".stt.json"))
    w = stt["words"]
    ref = np.sqrt(np.mean(x ** 2)) + 1e-9
    cuts = []
    for i in range(len(w) - 1):
        a, b = w[i]["end"], w[i + 1]["start"]
        if b - a <= MAXG:
            continue
        c0, c1 = a + MAXG / 2, b - MAXG / 2
        seg = x[int(c0 * SR):int(c1 * SR)]
        if len(seg) and 20 * np.log10(np.sqrt(np.mean(seg ** 2)) / ref + 1e-9) <= -25:
            cuts.append((c0, c1))
        elif len(seg):
            print("%s: pause at %.2f s is not silent, kept" % (p, a))
    keep, last = [], 0.0
    for c0, c1 in cuts:
        keep.append(x[int(last * SR):int(c0 * SR)])
        last = c1
    keep.append(x[int(last * SR):])
    y = np.concatenate(keep)

    def shift(tm):
        return tm - sum(min(c1, max(c0, tm)) - c0 for c0, c1 in cuts)

    for word in w:
        word["start"], word["end"] = round(shift(word["start"]), 3), round(shift(word["end"]), 3)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "s16le", "-ac", "1", "-ar", str(SR), "-i", "-",
                    os.path.join(dst, "%s-%s.wav" % (p, t))], input=(np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes(), check=True)
    stt["pauses_capped"] = MAXG
    json.dump(stt, open(os.path.join(dst, "%s-%s.stt.json" % (p, t)), "w"), ensure_ascii=False)
    print("%s-%s: %d pauses shortened, %.1f s saved" % (p, t, len(cuts), sum(c1 - c0 for c0, c1 in cuts)))

