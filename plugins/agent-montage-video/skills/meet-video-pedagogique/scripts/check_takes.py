#!/usr/bin/env python3
"""Check every narration take before the edit: intonation, fidelity to the script, silences.

  .venv/bin/python check_takes.py work/script.json work/voice [--take a] [--passages A,B]

For each passage take: pitch variation from voice-intonation/scripts/prosody.py (accept at least
2.5 semitones of standard deviation and 8 of range), share of the script words heard in the
transcript (number words ignored, since transcripts write digits; accept 95 %), longest silence
between two words (reject over 1.2 s), and words heard that are not in the script (tags read
aloud, hesitations). Prints one line per take and the list of takes to regenerate.
"""
import argparse, difflib, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from split_voice import NUM, fold, htoks, toks  # noqa: E402

PROSODY = os.path.join(HERE, "..", "..", "voice-intonation", "scripts", "prosody.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("voice_dir")
    ap.add_argument("--take", default=None, help="take letter (default: script takes, else a)")
    ap.add_argument("--passages")
    a = ap.parse_args()
    script = json.load(open(a.script))
    order, text = [], {}
    for s in script["scenes"]:
        if s.get("narration"):
            if s["passage"] not in order:
                order.append(s["passage"])
            text[s["passage"]] = (text.get(s["passage"], "") + " " + s["narration"]).strip()
    if a.passages:
        order = [p for p in order if p in a.passages.split(",")]
    bad = []
    for p in order:
        take = a.take or script.get("takes", {}).get(p, "a")
        base = os.path.join(a.voice_dir, "%s-%s" % (p, take))
        audio = next((base + e for e in (".wav", ".mp3") if os.path.exists(base + e)), None)
        if not audio:
            print("%-3s %s  missing" % (p, take))
            bad.append(p)
            continue
        pr = json.loads(subprocess.check_output([sys.executable, PROSODY, audio]).decode().strip().splitlines()[-1])
        words = json.load(open(base + ".stt.json"))["words"]
        heard = [t for w in words for t in htoks(w["text"])]
        ref = toks(text[p])
        sm = difflib.SequenceMatcher(None, [fold(t) for t in ref], [fold(t) for t in heard], autojunk=False)
        matched = set()
        for blk in sm.get_matching_blocks():
            matched.update(range(blk.a, blk.a + blk.size))
        content = [i for i, t in enumerate(ref) if t not in NUM and not t.isdigit()]
        fid = sum(1 for i in content if i in matched) / max(1, len(content))
        refset = {fold(t) for t in ref}
        extra = sorted({t for t in heard if fold(t) not in refset and not t.isdigit() and t not in NUM and len(t) > 2})
        gap = max([words[i + 1]["start"] - words[i]["end"] for i in range(len(words) - 1)] or [0])
        ok = pr["pitch_std_st"] >= 2.5 and pr["pitch_range_st"] >= 8 and fid >= 0.95 and gap <= 1.2
        if not ok:
            bad.append(p)
        print("%-3s %s  %5.1f s  pitch %.2f st / range %.1f  fidelity %3.0f%%  max gap %.2f s  %s%s" % (
            p, take, pr["dur"], pr["pitch_std_st"], pr["pitch_range_st"], fid * 100, gap,
            "OK" if ok else "REDO", ("  extra: " + ", ".join(extra[:8])) if extra else ""))
    print("\nto regenerate: " + (",".join(bad) if bad else "none"))


if __name__ == "__main__":
    main()
