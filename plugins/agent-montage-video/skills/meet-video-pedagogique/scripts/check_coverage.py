#!/usr/bin/env python3
"""Check that the teaching video leaves out no concept of the meeting.

  python3 check_coverage.py work/concepts.json work/script.json [--keyframes work/keyframes]
                            [--final-transcript work/final.stt.json]

concepts.json : {"concepts": [{"id", "title", "evidence": [{"tc": "00:12:31", "quote": "..."}],
                 "must_say": ["kilowattheure", ...], "status": "confirmed|corrected|doubtful"}]}
script.json   : scenes with "concepts": [ids], "narration", optional "onScreen": [texts]
                and shots {"capture": "k-001231.jpg", "tc": "00:12:31"}.

Fails (exit 1) when a concept has no scene, a must_say term is neither spoken nor shown,
a concept has no evidence timecode, a capture file is missing, or (with --final-transcript)
a must_say term is not heard in the final mix.
"""
import argparse, json, os, re, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from split_voice import NUM, fold, htoks  # noqa: E402

TAG = re.compile(r"\[[a-zA-Z ]+\]")


def norm(s):
    s = unicodedata.normalize("NFKD", TAG.sub(" ", s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " " + " ".join(re.findall(r"[a-z0-9]+", s)) + " "


def triggers(scene):
    """Every word trigger used by a scene: shots, camera keys, highlights and visual items."""
    keys = []
    for sh in scene.get("shots", []):
        keys.append(sh.get("at"))
        keys += [c.get("at") for c in sh.get("cam", [])]
        for h in sh.get("hl", []):
            keys += [h.get("at"), h.get("until")]
    v = scene.get("visual") or {}
    for field in ("items", "figures", "lines"):
        keys += [x.get("at") for x in v.get(field, [])]
    return [k for k in keys if k]


def trigger_ok(narration, key):
    words = norm(narration).split()
    kw, _, nth = key.partition("#")
    want = norm(kw).split()
    seen = 0
    for i in range(len(words)):
        if all(i + j < len(words) and words[i + j].startswith(w) for j, w in enumerate(want)):
            seen += 1
            if seen == int(nth or 1):
                return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("concepts")
    ap.add_argument("script")
    ap.add_argument("--keyframes")
    ap.add_argument("--final-transcript")
    a = ap.parse_args()
    concepts = json.load(open(a.concepts))["concepts"]
    script = json.load(open(a.script))
    heard = None
    if a.final_transcript:
        heard = " " + " ".join(fold(t) for t in htoks(json.load(open(a.final_transcript)).get("text", ""))
                               if t not in NUM and not t.isdigit()) + " "
    errors, rows = [], []
    by_concept = {c["id"]: [] for c in concepts}
    for s in script["scenes"]:
        for k in triggers(s):
            if not trigger_ok(s.get("narration", ""), k):
                errors.append("scene %s: trigger word %r is not in its narration" % (s["id"], k))
        for cid in s.get("concepts", []):
            if cid not in by_concept:
                errors.append("scene %s cites unknown concept %s" % (s["id"], cid))
            else:
                by_concept[cid].append(s)
        for sh in s.get("shots", []):
            cap = sh.get("capture")
            if cap and a.keyframes and not os.path.exists(os.path.join(a.keyframes, cap)):
                errors.append("scene %s: capture %s missing in %s" % (s["id"], cap, a.keyframes))
            if cap and not sh.get("tc"):
                errors.append("scene %s: capture %s has no recording timecode (tc)" % (s["id"], cap))
    for c in concepts:
        scenes = by_concept[c["id"]]
        if not c.get("evidence"):
            errors.append("concept %s has no transcript evidence" % c["id"])
        if c.get("status") == "doubtful":
            errors.append("concept %s is still doubtful: settle it against the recording" % c["id"])
        if not scenes:
            errors.append("concept %s (%s) is covered by no scene" % (c["id"], c["title"]))
            rows.append((c["id"], "-", "MISSING"))
            continue
        said = norm(" ".join(s.get("narration", "") for s in scenes))
        shown = norm(" ".join(" ".join(s.get("onScreen", [])) for s in scenes))
        missing = [t for t in c.get("must_say", []) if norm(t) not in said and norm(t) not in shown]
        if missing:
            errors.append("concept %s: %s neither spoken nor shown" % (c["id"], ", ".join(missing)))
        if heard is not None:
            spoken_terms = [t for t in c.get("must_say", []) if norm(t) in said]
            lost = []
            for term in spoken_terms:
                words = [fold(w) for w in htoks(term) if w not in NUM and not w.isdigit()]
                if words and (" " + " ".join(words) + " ") not in heard:
                    lost.append(term)
            if lost:
                errors.append("concept %s: %s not heard in the final mix" % (c["id"], ", ".join(lost)))
        rows.append((c["id"], ",".join(s["id"] for s in scenes), "ok" if not missing else "INCOMPLETE"))
    w = max(len(r[0]) for r in rows) if rows else 10
    for r in rows:
        print("%-*s  %-8s  %s" % (w, r[0], r[2], r[1]))
    print("%d concepts, %d scenes" % (len(concepts), len(script["scenes"])))
    if errors:
        print("\nFAILED:\n- " + "\n- ".join(errors))
        sys.exit(1)
    print("coverage OK")


if __name__ == "__main__":
    main()
