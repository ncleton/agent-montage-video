#!/usr/bin/env python3
"""Fast, robust Remotion render of a long composition.

  .venv/bin/python ../../../scripts/render_chunks.py --composition AppelsOffresPresentation --out ../out/video.mp4 \
      [--entry src/index.ts] [--chunk 3000] [--gl angle] [--browser-executable <chrome>] [--frames 0-599]

Run from the Remotion project folder. What it does, and why (measured on a 4 min 40 s, 60 fps video):
- renders on the GPU in chunks of --chunk frames, each started --preroll frames early; the pre-roll is
  dropped, because the first frames of a GPU render can come out as a mosaic;
- watches every chunk: if its log does not move for --stall seconds (a render that hangs, seen several
  times at about 94 %), it kills it and starts the chunk again (3 attempts), instead of waiting forever;
- renders the audio once on its own (fast), then joins chunks and audio with a -16 LUFS loudnorm;
- scans the result for isolated parasite frames (detect_inserted.py) and re-renders a small window
  around each one, up to --max-patch frames, then scans again.
Never use --gl=swiftshader on the Mac: about three times slower, and it also produced white frames.
Video clips inside the composition must be image sequences (clip_frames.py), not <OffthreadVideo>.
Fails loudly with the chunk and the log path when a chunk cannot be rendered.
"""
import argparse, json, os, re, signal, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
DETECT = os.path.join(HERE, "..", "plugins", "agent-montage-video", "skills", "video-frame-review", "scripts", "detect_inserted.py")


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit("Command failed (%s):\n%s\n%s" % (" ".join(cmd[:6]), r.stdout[-1500:], r.stderr[-1500:]))
    return r.stdout


def remotion(args, opts):
    cmd = ["npx", "remotion"] + args
    if opts.browser_executable:
        cmd.append("--browser-executable=" + opts.browser_executable)
    return cmd


def render_watched(cmd, log, stall, attempts=3):
    for k in range(1, attempts + 1):
        with open(log, "w") as fh:
            p = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)
        last, still = None, 0
        while p.poll() is None:
            time.sleep(10)
            size = os.path.getsize(log)
            still = still + 10 if size == last else 0
            last = size
            if still >= stall:
                print("  stalled for %d s, restarting (attempt %d/%d)" % (stall, k, attempts), flush=True)
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
                break
        if p.returncode == 0:
            return
        if still < stall:
            print("  render exited with code %s (attempt %d/%d), see %s" % (p.returncode, k, attempts, log), flush=True)
    sys.exit("Chunk could not be rendered after %d attempts: %s\nLog: %s" % (attempts, " ".join(cmd[:8]), log))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--composition", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--entry", default="src/index.ts")
    ap.add_argument("--work", default="../work/render-chunks")
    ap.add_argument("--chunk", type=int, default=3000)
    ap.add_argument("--preroll", type=int, default=20)
    ap.add_argument("--stall", type=int, default=180)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--crf", type=int, default=17)
    ap.add_argument("--gl", help="Remotion --gl value (angle on the Mac, swangle on the Linux remote computer)")
    ap.add_argument("--browser-executable")
    ap.add_argument("--frames", help="only render this range, for example 0-599 (test)")
    ap.add_argument("--max-patch", type=int, default=20)
    ap.add_argument("--fresh", action="store_true", help="ignore chunks already rendered in --work")
    o = ap.parse_args()
    os.makedirs(o.work, exist_ok=True)
    t0 = time.time()
    bundle = os.path.join(o.work, "bundle")
    print("bundle...", flush=True)
    run(["npx", "remotion", "bundle", o.entry, "--out-dir", bundle, "--log=error"])
    listing = run(remotion(["compositions", bundle], o))
    m = re.search(r"^%s\s+(\d+)\s+\d+x\d+\s+(\d+)" % re.escape(o.composition), listing, re.M)
    if not m:
        sys.exit("Composition %s not found in the bundle:\n%s" % (o.composition, listing[-800:]))
    fps, total = int(m.group(1)), int(m.group(2))
    first, last = 0, total - 1
    if o.frames:
        first, last = [int(x) for x in o.frames.split("-")]
    print("%s: %d frames at %d fps, rendering %d-%d" % (o.composition, total, fps, first, last), flush=True)
    common = ["--concurrency=%d" % o.concurrency, "--timeout=60000", "--log=info"] + (["--gl=" + o.gl] if o.gl else [])

    audio = os.path.join(o.work, "audio.wav")
    print("audio...", flush=True)
    run(remotion(["render", bundle, o.composition, audio, "--codec=wav", "--frames=%d-%d" % (first, last), "--log=error"], o))

    parts = []
    s = first
    while s <= last:
        e = min(last, s + o.chunk - 1)
        rs = max(first, s - o.preroll)
        out = os.path.join(o.work, "c-%06d.mp4" % s)
        if o.fresh or not os.path.exists(out):
            print("chunk %d-%d..." % (s, e), flush=True)
            tmp = out + ".part.mp4"
            render_watched(remotion(["render", bundle, o.composition, tmp, "--frames=%d-%d" % (rs, e), "--muted",
                                     "--codec=h264", "--crf=%d" % o.crf] + common, o), out + ".log", o.stall)
            os.replace(tmp, out)
        parts.append((out, s - rs))
        s = e + 1

    print("join...", flush=True)
    joined = os.path.join(o.work, "joined.mp4")
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y"]
    for path, _ in parts:
        cmd += ["-i", path]
    cmd += ["-i", audio]
    chains = ["[%d:v]trim=start_frame=%d,setpts=PTS-STARTPTS[v%d]" % (i, skip, i) for i, (_, skip) in enumerate(parts)]
    fc = ";".join(chains) + ";" + "".join("[v%d]" % i for i in range(len(parts))) + "concat=n=%d:v=1:a=0,fps=%d[v]" % (len(parts), fps)
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "%d:a" % len(parts), "-c:v", "libx264", "-crf", "16",
            "-preset", "medium", "-pix_fmt", "yuv420p", "-r", str(fps), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", joined]
    run(cmd)

    py = sys.executable
    for rnd in range(2):
        rep = os.path.join(o.work, "flagged.json")
        r = subprocess.run([py, DETECT, joined, "--json", rep], capture_output=True, text=True)
        if r.returncode not in (0, 1):
            sys.exit("Isolated-frame check failed: %s" % r.stderr[-800:])
        flagged = json.load(open(rep))["flagged"]
        if not flagged:
            break
        if len(flagged) > o.max_patch:
            sys.exit("%d isolated frames in %s: too many to patch, the renderer is unstable (try another --gl). "
                     "Frames: %s" % (len(flagged), joined, flagged[:30]))
        print("patching %d isolated frame(s): %s" % (len(flagged), flagged), flush=True)
        cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", joined]
        chain, prev = [], "0:v"
        for i, f in enumerate(flagged, start=1):
            a, b = max(0, f - o.preroll - 10), min(total - 1, f + 10)
            pth = os.path.join(o.work, "patch-%d-r%d.mp4" % (f, rnd))
            render_watched(remotion(["render", bundle, o.composition, pth, "--frames=%d-%d" % (a, b), "--muted",
                                     "--codec=h264", "--crf=14"] + common, o), pth + ".log", o.stall)
            lo, hi = f - 2 - first, f + 2 - first
            cmd += ["-i", pth]
            chain.append("[%d:v]setpts=PTS-STARTPTS+%d/%d/TB[p%d]" % (i, a - first, fps, i))
            chain.append("[%s][p%d]overlay=eof_action=pass:enable='between(n,%d,%d)'[o%d]" % (prev, i, lo, hi, i))
            prev = "o%d" % i
        fixed = os.path.join(o.work, "joined-fixed-%d.mp4" % rnd)
        cmd += ["-filter_complex", ";".join(chain) + ";[%s]format=yuv420p[v]" % prev, "-map", "[v]", "-map", "0:a",
                "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-r", str(fps), "-c:a", "copy", fixed]
        run(cmd)
        joined = fixed
    else:
        sys.exit("Isolated frames remain after two patch rounds in %s: look at %s" % (joined, rep))
    os.makedirs(os.path.dirname(os.path.abspath(o.out)), exist_ok=True)
    os.replace(joined, o.out)
    print("done: %s (%.1f min)" % (o.out, (time.time() - t0) / 60))


if __name__ == "__main__":
    main()

