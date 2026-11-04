#!/usr/bin/env python3
"""Turn every video clip used by a Remotion project into an image sequence, and write the manifest.

  python3 clip_frames.py public/clips/bureau.mp4 public/clips/pli.mp4 ... [--manifest src/clipframes.json]

Run from the Remotion project folder. Each clip becomes public/frames/<name>/f00000.jpg ... (one JPEG per
recorded frame, quality 3). In the composition, show frame k of a clip with
<Img src={staticFile(dir + "/f" + String(k).padStart(5, "0") + ".jpg")} /> instead of <OffthreadVideo>:
the renderer then never decodes video, which removes the parasite frames (mosaic, image of another
scene) that OffthreadVideo inserted in long renders. Clips must already be at the composition frame
rate (retime_cast.py writes 60 fps clips). Re-extracts a clip when its video is newer than its frames.
"""
import argparse, glob, json, os, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("clips", nargs="+")
ap.add_argument("--manifest", default="src/clipframes.json")
ap.add_argument("--public", default="public")
a = ap.parse_args()
man = json.load(open(a.manifest)) if os.path.exists(a.manifest) else {}
for c in a.clips:
    if not os.path.exists(c):
        sys.exit("Clip not found: %s" % c)
    rel = os.path.relpath(c, a.public)
    name = os.path.splitext(os.path.basename(c))[0]
    d = os.path.join(a.public, "frames", name)
    os.makedirs(d, exist_ok=True)
    old = sorted(glob.glob(d + "/f*.jpg"))
    if not old or os.path.getmtime(old[0]) < os.path.getmtime(c):
        for f in old:
            os.remove(f)
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", c, "-fps_mode", "passthrough", "-q:v", "3",
                        "-start_number", "0", d + "/f%05d.jpg"], check=True)
    n = len(glob.glob(d + "/f*.jpg"))
    man[rel] = {"dir": os.path.relpath(d, a.public), "n": n}
    print("%s -> %s (%d images)" % (rel, man[rel]["dir"], n))
json.dump(man, open(a.manifest, "w"), indent=1)

