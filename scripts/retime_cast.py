#!/usr/bin/env python3
"""Turn a Chrome screencast (cast.mjs: JPEG frames plus their compositor timestamps) into an exact
60 fps clip, optionally re-timed on the voice.

  python3 retime_cast.py <cast dir> out.mp4 '<anchors>' <duration s> [--fps 60]

anchors: JSON list of [clip_second, capture_second] pairs, increasing; between anchors the capture is
played faster or slower so that an action lands on the word that names it; outside them at real speed.
Use '[]' for real time. Each output frame shows the last captured image at that instant, so motion keeps
its real cadence: no duplicated or blended frames as with a 25 fps recordVideo converted to 60 fps.
"""
import argparse, bisect, json, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("anchors"); ap.add_argument("duration", type=float)
ap.add_argument("--fps", type=int, default=60)
a = ap.parse_args()
J = json.load(open(a.src + "/frames.json"))
fr = J["frames"] if isinstance(J, dict) else J
t0 = fr[0]["t"]
ts = [f["t"] - t0 for f in fr]
anchors = sorted(json.loads(a.anchors))
for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
    if not (x1 > x0 and y1 >= y0):
        sys.exit("Anchors must increase: %s" % anchors)


def m(o):
    if not anchors:
        return o
    if o <= anchors[0][0]:
        return anchors[0][1] - (anchors[0][0] - o)
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if o <= x1:
            return y0 + (y1 - y0) * (o - x0) / (x1 - x0)
    return anchors[-1][1] + (o - anchors[-1][0])


n = round(a.duration * a.fps)
p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(a.fps), "-c:v", "mjpeg",
                      "-i", "-", "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-pix_fmt", "yuv420p", "-g", "30",
                      "-r", str(a.fps), a.out], stdin=subprocess.PIPE)
cache = {}
for k in range(n):
    s = max(0.0, min(ts[-1], m(k / a.fps)))
    i = max(0, bisect.bisect_right(ts, s + 1e-6) - 1)
    if i not in cache:
        cache.clear()
        cache[i] = open(a.src + "/" + fr[i]["name"], "rb").read()
    p.stdin.write(cache[i])
p.stdin.close()
p.wait()
print("%s: %d frames, capture %.2f -> %.2f s of %.2f" % (a.out, n, m(0), m((n - 1) / a.fps), ts[-1]))

