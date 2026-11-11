#!/usr/bin/env python3
"""Bring an already mastered film to the delivery loudness with one measured linear gain.

  python3 scripts/normalize_loudness.py <in.mp4> <out.mp4> [--target -16] [--max-peak -1.0]

Measures integrated loudness and true peak (ffmpeg ebur128), applies gain = target - measured to the audio,
copies the picture, then measures the result again. A gain never changes the dynamics, so the mastering of
the input (for example core/render/mux.sh of Lemo-Opuscar at -14 LUFS) is kept. Exits non-zero, writing nothing
at <out>, if the gain would push the true peak above --max-peak or if the result misses the target by over 0.5 LU.
"""
import argparse, os, re, subprocess, sys


def measure(path):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-map", "0:a:0", "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"normalize_loudness: ffmpeg cannot read the audio of {path}: {p.stderr.strip().splitlines()[-1:]}")
    summary = p.stderr[p.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", summary)
    tp = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary)
    if not i or not tp or "inf" in i.group(1):
        sys.exit(f"normalize_loudness: no measurable audio in {path} (silent or missing audio stream)")
    return float(i.group(1)), float(tp.group(1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--target", type=float, default=-16.0)
    ap.add_argument("--max-peak", type=float, default=-1.0)
    a = ap.parse_args()
    lufs, peak = measure(a.src)
    gain = a.target - lufs
    if peak + gain > a.max_peak:
        sys.exit(f"normalize_loudness: {a.src} measures {lufs:.1f} LUFS, true peak {peak:.1f} dBTP; a gain of {gain:+.1f} dB "
                 f"would put the peak at {peak + gain:.1f} dBTP (limit {a.max_peak}). Raise the mix itself (compress or limit it) "
                 f"and master again.")
    tmp = a.dst + ".part.mp4"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.src, "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy",
                        "-af", f"volume={gain:.2f}dB", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", tmp],
                       capture_output=True, text=True)
    if r.returncode != 0:
        if os.path.exists(tmp): os.remove(tmp)
        sys.exit(f"normalize_loudness: ffmpeg failed: {r.stderr.strip()}")
    out_lufs, out_peak = measure(tmp)
    if abs(out_lufs - a.target) > 0.5 or out_peak > a.max_peak:
        os.remove(tmp)
        sys.exit(f"normalize_loudness: result {out_lufs:.1f} LUFS / {out_peak:.1f} dBTP misses {a.target} LUFS "
                 f"(peak limit {a.max_peak}); nothing written to {a.dst}")
    os.replace(tmp, a.dst)
    print(f"{a.dst}: {lufs:.1f} -> {out_lufs:.1f} LUFS (gain {gain:+.2f} dB), true peak {out_peak:.1f} dBTP")


if __name__ == "__main__":
    main()
