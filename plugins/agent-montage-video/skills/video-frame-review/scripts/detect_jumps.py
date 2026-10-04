#!/usr/bin/env python3
"""Detect isolated frame jumps (flashes, pops, glitches) over every frame of a video.

Usage: detect_jumps.py video.mp4 [--threshold 2.0] [--ratio 3.0]
Prints the frame count and the list of suspicious times. Exit code 1 if any jump is found.
"""
import argparse, subprocess, sys
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('video')
ap.add_argument('--threshold', type=float, default=2.0, help='minimum mean abs difference (0-255) for a spike')
ap.add_argument('--ratio', type=float, default=3.0, help='spike must exceed the local median motion by this factor')
a = ap.parse_args()

fps_s = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', '-of', 'default=nw=1:nk=1', a.video], capture_output=True, text=True).stdout.strip().splitlines()[0].strip(',')
num, den = (fps_s.split('/') + ['1'])[:2]
fps = float(num) / float(den or 1)

W, H = 192, 108
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', a.video, '-vf', 'scale=%d:%d,format=gray' % (W, H), '-f', 'rawvideo', '-'], stdout=subprocess.PIPE)
prev, d = None, []
while True:
    b = p.stdout.read(W * H)
    if len(b) < W * H:
        break
    f = np.frombuffer(b, np.uint8).astype(np.int16)
    if prev is not None:
        d.append(np.abs(f - prev).mean())
    prev = f
d = np.array(d)
spikes = []
for i in range(1, len(d) - 1):
    loc = np.median(d[max(0, i - 6):i + 7])
    if d[i] > a.threshold and d[i] > a.ratio * max(loc, 0.3) and d[i] > 1.8 * max(d[i - 1], d[i + 1]):
        t = (i + 1) / fps
        spikes.append((i + 1, t, float(d[i])))
print('frames: %d (%.2f s at %.3g fps)' % (len(d) + 1, (len(d) + 1) / fps, fps))
if not spikes:
    print('no isolated jump detected')
for fr, t, v in spikes:
    print('jump at frame %d  %d:%05.2f  diff %.1f' % (fr, t // 60, t % 60, v))
sys.exit(1 if spikes else 0)

