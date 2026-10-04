#!/usr/bin/env python3
"""Generate ElevenLabs sound effects from a plan and place them on the video timeline.

Usage:
  python3 scripts/generate_sfx.py work/eden62/sfx/sfx_plan.json [--dry-run] [--force id ...]

The plan lists sounds (prompt, duration, loop, prompt influence) and cues. A cue time is a
number of seconds or a voice anchor such as "l7:coupe+0.78" or "l2:seau#1-0.1" (word prefix,
optional occurrence, optional offset), resolved against the Remotion timing.json so effects
follow the voice if the narration moves. The API key is read from ELEVENLABS_API_KEY,
injected by LibreAgent (run through scripts/with_secrets.sh); it is never printed or
written to disk.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_192"


def api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("ELEVENLABS_API_KEY is missing: run this command through scripts/with_secrets.sh")
    return key


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9']", "", s)


def resolve(at, timing: dict) -> float:
    if isinstance(at, (int, float)):
        return float(at)
    m = re.fullmatch(r"(l\d+):([^#+\-]+)(?:#(\d+))?([+\-]\d+(?:\.\d+)?)?", at.strip())
    if not m:
        raise ValueError(f"bad anchor {at!r}")
    lid, prefix, nth, off = m.group(1), m.group(2), int(m.group(3) or 0), float(m.group(4) or 0)
    line = next(l for l in timing["lines"] if l["id"] == lid)
    words = [w for w in line["words"] if norm(w["w"]).startswith(norm(prefix))]
    if len(words) <= nth:
        raise ValueError(f"word not found for {at!r}")
    return round(words[nth]["t"] + off, 3)


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def generate(sid: str, spec: dict, raw: Path, key: str) -> None:
    text = spec["prompt"] + ". No music, no voices."
    body = {"text": text, "model_id": "eleven_text_to_sound_v2", "prompt_influence": spec.get("influence", 0.5),
            "duration_seconds": spec.get("duration"), "loop": bool(spec.get("loop", False))}
    req = urllib.request.Request(API, data=json.dumps(body).encode(), method="POST",
                                 headers={"xi-api-key": key, "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw.write_bytes(resp.read())
            break
        except urllib.error.HTTPError as err:
            if err.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(3 * (attempt + 1))
                continue
            raise RuntimeError(f"{sid}: HTTP {err.code} {err.read()[:300]!r}") from None
        except urllib.error.URLError:
            if attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))
    print(f"generated {sid}", flush=True)


def finish(sid: str, spec: dict, raw: Path, out: Path) -> None:
    filters = []
    if not spec.get("loop"):
        filters.append("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.01")
    filters.append(f"loudnorm=I={-23 if spec.get('loop') else -18}:TP=-1.5:LRA=11")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", ",".join(filters), "-ar", "48000",
                    "-ac", "2", str(out)], check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--dry-run", action="store_true", help="resolve cues only, no API calls")
    ap.add_argument("--force", nargs="*", default=[], help="regenerate these sound ids")
    args = ap.parse_args()

    plan_path = (ROOT / args.plan).resolve()
    plan = json.loads(plan_path.read_text())
    timing = json.loads((ROOT / plan["timing"]).read_text())
    raw_dir = plan_path.parent / "raw"
    pub = ROOT / plan["public_dir"]
    raw_dir.mkdir(parents=True, exist_ok=True)
    pub.mkdir(parents=True, exist_ok=True)
    sounds = plan["sounds"]

    used = {c["sound"] for c in plan["cues"]}
    missing = used - sounds.keys()
    if missing:
        sys.exit(f"cues use undefined sounds: {sorted(missing)}")

    if not args.dry_run:
        todo = [s for s in sorted(used) if s in args.force or not (raw_dir / f"{s}.mp3").exists()]
        if todo:
            key = api_key()
            with ThreadPoolExecutor(4) as pool:
                list(pool.map(lambda s: generate(s, sounds[s], raw_dir / f"{s}.mp3", key), todo))
        for s in sorted(used):
            out = pub / f"{s}.wav"
            if s in todo or not out.exists():
                finish(s, sounds[s], raw_dir / f"{s}.mp3", out)

    cues = []
    for c in plan["cues"]:
        t = resolve(c["at"], timing)
        spec = sounds[c["sound"]]
        wav = pub / f"{c['sound']}.wav"
        if "until" in c:
            dur = resolve(c["until"], timing) - t
        elif "dur" in c:
            dur = c["dur"]
        else:
            dur = duration(wav) if wav.exists() else spec.get("duration", 1)
        cues.append({"sound": c["sound"], "file": f"sfx/{c['sound']}.wav", "t": t, "dur": round(dur, 3),
                     "vol": c.get("vol", 0.4), "loop": bool(spec.get("loop")) and "until" in c,
                     "fade_in": c.get("fade_in", 0), "fade_out": c.get("fade_out", 0.05),
                     "start_from": c.get("start_from", 0), "note": c.get("note", "")})
    cues.sort(key=lambda c: c["t"])
    (ROOT / plan["cues_out"]).write_text(json.dumps({"cues": cues}, ensure_ascii=False, indent=1))
    for c in cues:
        print(f"{c['t']:7.2f}s  {c['dur']:5.2f}s  vol {c['vol']:.2f}  {c['sound']:<18} {c['note']}")
    print(f"{len(cues)} cues -> {plan['cues_out']}")


if __name__ == "__main__":
    main()
