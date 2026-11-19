#!/usr/bin/env python3
"""Find the stable screen-share moments of a meeting recording.

Decodes the recording at a low frame rate, measures how much the picture changes
from one sample to the next (optionally inside a crop that excludes the
participant tiles), cuts the recording into stable segments, and saves one
full-resolution frame per segment, named after its timestamp in the recording.
Writes index.json and timestamped contact sheets for a visual review.

Usage:
  .venv/bin/python keyframes.py recording.mp4 work/keyframes [--fps 1] [--crop x,y,w,h]
                    [--threshold 6] [--min-seconds 4]
"""
import argparse, json, math, os, subprocess, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def probe(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height:format=duration", "-of", "json", path])
    d = json.loads(out)
    s = d["streams"][0]
    return s["width"], s["height"], float(d["format"]["duration"])


def hms(t):
    t = int(round(t))
    return "%02d:%02d:%02d" % (t // 3600, t % 3600 // 60, t % 60)


def grab(path, t, dst):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % t, "-i", path,
                    "-frames:v", "1", "-q:v", "2", dst], check=True)


def font(size):
    for f in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("outdir")
    ap.add_argument("--fps", type=float, default=1.0)
    ap.add_argument("--crop", help="x,y,w,h in source pixels: the shared-screen area")
    ap.add_argument("--threshold", type=float, default=6.0,
                    help="mean absolute difference (0-255) that starts a new segment")
    ap.add_argument("--min-seconds", type=float, default=4.0)
    a = ap.parse_args()

    W, H, dur = probe(a.video)
    os.makedirs(a.outdir, exist_ok=True)
    vf = []
    if a.crop:
        x, y, w, h = [int(v) for v in a.crop.split(",")]
        vf.append("crop=%d:%d:%d:%d" % (w, h, x, y))
    sw, sh = 256, 144
    vf += ["fps=%g" % a.fps, "scale=%d:%d" % (sw, sh), "format=gray"]
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", a.video, "-vf", ",".join(vf),
                             "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    frames = []
    while True:
        b = proc.stdout.read(sw * sh)
        if len(b) < sw * sh:
            break
        frames.append(np.frombuffer(b, np.uint8).reshape(sh, sw).astype(np.int16))
    if proc.wait() != 0 or not frames:
        sys.exit("ffmpeg could not decode %s" % a.video)

    diffs = [0.0] + [float(np.abs(frames[i] - frames[i - 1]).mean()) for i in range(1, len(frames))]
    starts = [0] + [i for i, d in enumerate(diffs) if d > a.threshold]
    segs = []
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else len(frames)
        if (e - s) / a.fps >= a.min_seconds:
            segs.append((s / a.fps, e / a.fps))
    # merge consecutive segments that show the same picture
    merged = []
    last = len(frames) - 1
    for s, e in segs:
        if merged:
            i0 = min(last, int((merged[-1][0] + merged[-1][1]) / 2 * a.fps))
            i1 = min(last, int((s + e) / 2 * a.fps))
            if float(np.abs(frames[i1] - frames[i0]).mean()) < a.threshold / 2:
                merged[-1] = (merged[-1][0], e)
                continue
        merged.append((s, e))

    index = []
    for s, e in merged:
        t = min(dur - 0.1, s + min(2.0, (e - s) / 2))
        name = "k-%s.jpg" % hms(t).replace(":", "")
        grab(a.video, t, os.path.join(a.outdir, name))
        index.append({"file": name, "t": round(t, 2), "tc": hms(t), "start": round(s, 2), "end": round(e, 2)})
    json.dump({"video": os.path.abspath(a.video), "width": W, "height": H, "duration": dur,
               "crop": a.crop, "segments": index}, open(os.path.join(a.outdir, "index.json"), "w"), indent=1)

    f = font(22)
    tw, th = 480, int(480 * H / W)
    for n in range(math.ceil(len(index) / 12)):
        part = index[n * 12:(n + 1) * 12]
        sheet = Image.new("RGB", (tw * 4, (th + 34) * 3), "white")
        for i, k in enumerate(part):
            im = Image.open(os.path.join(a.outdir, k["file"])).resize((tw, th))
            x, y = (i % 4) * tw, (i // 4) * (th + 34)
            sheet.paste(im, (x, y + 34))
            ImageDraw.Draw(sheet).text((x + 8, y + 5), "%s  (%s-%s)" % (k["tc"], hms(k["start"]), hms(k["end"])), fill="black", font=f)
        sheet.save(os.path.join(a.outdir, "sheet-%02d.jpg" % (n + 1)), quality=85)
    print("%d samples, %d stable segments, %d sheets in %s" % (len(frames), len(index), math.ceil(len(index) / 12), a.outdir))


if __name__ == "__main__":
    main()
