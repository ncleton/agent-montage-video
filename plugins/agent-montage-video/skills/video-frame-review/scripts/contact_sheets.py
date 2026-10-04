#!/usr/bin/env python3
"""Build timestamped contact sheets (4x4 frames) covering a video, for a visual frame review.

Usage: contact_sheets.py video.mp4 OUT_DIR [--fps 2] [--start S] [--duration D] [--width 480]
"""
import argparse, glob, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument('video'); ap.add_argument('out')
ap.add_argument('--fps', type=float, default=2.0)
ap.add_argument('--start', type=float, default=0.0)
ap.add_argument('--duration', type=float, default=None)
ap.add_argument('--width', type=int, default=480)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
tmp = tempfile.mkdtemp(prefix='frames_')
cmd = ['ffmpeg', '-v', 'error', '-y', '-ss', str(a.start)]
if a.duration:
    cmd += ['-t', str(a.duration)]
cmd += ['-i', a.video, '-vf', 'fps=%g,scale=%d:-2' % (a.fps, a.width), os.path.join(tmp, 'f%05d.jpg')]
subprocess.run(cmd, check=True)
fs = sorted(glob.glob(os.path.join(tmp, 'f*.jpg')))
font = None
for cand in ['/System/Library/Fonts/Supplemental/Arial.ttf', '/Library/Fonts/Arial.ttf', '/System/Library/Fonts/Helvetica.ttc']:
    if os.path.exists(cand):
        font = ImageFont.truetype(cand, 16); break
font = font or ImageFont.load_default()
n = 0
for s in range(0, len(fs), 16):
    first = Image.open(fs[0]); w, h = first.size
    sh = Image.new('RGB', (4 * (w + 4), 4 * (h + 4)), 'black')
    for k, f in enumerate(fs[s:s + 16]):
        im = Image.open(f).convert('RGB')
        i = int(os.path.basename(f)[1:6]) - 1
        t = a.start + (i + 0.5) / a.fps
        d = ImageDraw.Draw(im)
        d.rectangle([w - 100, h - 22, w, h], fill='white')
        d.text((w - 96, h - 21), '%d:%05.2f' % (t // 60, t % 60), fill='red', font=font)
        sh.paste(im, ((k % 4) * (w + 4), (k // 4) * (h + 4)))
    sh.save(os.path.join(a.out, 'sheet%03d.jpg' % n), quality=86); n += 1
print('%d frames, %d sheets in %s' % (len(fs), n, a.out))

