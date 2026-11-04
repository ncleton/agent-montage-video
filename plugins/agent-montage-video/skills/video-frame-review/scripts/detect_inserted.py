#!/usr/bin/env python3
"""Find isolated parasite frames in a rendered video: a frame that differs strongly from both
neighbours while the two neighbours match each other (a mosaic, a white block or an image from
another scene slipped in by the renderer). Streams the video, so it works on long renders.

  .venv/bin/python detect_inserted.py out.mp4 [--min 10] [--json flagged.json]

Prints one line per flagged frame (index and time) and exits 1 when any is found. --min is the
mean difference (0-255, on a 320x180 grey thumbnail) a frame must have with both neighbours;
10 catches renderer glitches while ignoring fast scrolls (about 2 to 3).
"""
import argparse, json, subprocess, sys
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("--min", type=float, default=10.0)
ap.add_argument("--json")
a = ap.parse_args()
fps_s = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                        "-of", "default=nw=1:nk=1", a.video], capture_output=True, text=True).stdout.strip()
if not fps_s:
    sys.exit("Cannot read the frame rate of %s (missing file or no video stream)." % a.video)
num, den = (fps_s.split("/") + ["1"])[:2]
fps = float(num) / float(den)
W, H = 320, 180
p = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-i", a.video, "-vf", "scale=%d:%d,format=gray" % (W, H),
                      "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
size = W * H
win, n, flagged = [], 0, []
while True:
    buf = p.stdout.read(size)
    if len(buf) < size:
        break
    win.append(np.frombuffer(buf, np.uint8).astype(np.int16))
    if len(win) > 3:
        win.pop(0)
    if len(win) == 3:
        x, y, z = win
        da, db, dc = np.abs(y - x).mean(), np.abs(z - y).mean(), np.abs(z - x).mean()
        if da >= a.min and db >= a.min and dc < 0.5 * min(da, db):
            flagged.append(n - 1)
            print("isolated frame %d at %.3f s (diff %.1f / %.1f, neighbours %.1f)" % (n - 1, (n - 1) / fps, da, db, dc))
    n += 1
p.wait()
print("frames: %d, isolated: %d" % (n, len(flagged)))
if a.json:
    json.dump({"fps": fps, "frames": n, "flagged": flagged}, open(a.json, "w"))
sys.exit(1 if flagged else 0)

