#!/usr/bin/env python3
"""Cut the chosen narration takes into one audio file per scene and write the Remotion audio.json.

  python3 split_voice.py work/script.json work/voice motion/public/voice motion/src/audio.json

script.json gives each passage its chosen take ("takes": {"A": "a", "B": "c"}; default "a") and an
optional "voice.tempo" (for example 0.9 slows the voice by 10 % without changing its pitch).
Scene boundaries come from aligning the scene narration with the transcribed words of the take.
Each scene file is loudness-normalised; audio.json carries its duration, the script words with
their spoken times (for word-triggered animation) and subtitle cues. Fails when a take does not
match its script (number words are ignored in that check, since transcripts write digits).
"""
import difflib, json, math, os, re, subprocess, sys, unicodedata

TAG = re.compile(r"\[[a-zA-Z ]+\]\s*")
NUM = set("zero un une deux trois quatre cinq six sept huit neuf dix onze douze treize quatorze quinze seize "
          "vingt vingts trente quarante cinquante soixante cent cents mille virgule et "
          "pour heure heures h point".split())


def toks(s):
    s = unicodedata.normalize("NFKD", TAG.sub("", s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", s)


UNITS = {"kwh": "kilowattheure", "kw": "kilowatt", "kva": "kilovoltampere", "mm2": "millimetre", "mm": "millimetre",
         "a": "ampere", "v": "volt"}
# spellings the speech recognizer uses for words of these trainings
ASR_ALIASES = {"cosfi": "cos phi", "sokotech": "socotec", "socotech": "socotec", "ispv": "lise pv", "lispv": "lise pv",
               "mm2": "millimetres carres", "mm²": "millimetres carres"}


def htoks(s):
    """Tokens of a transcript: letters and digits split apart ("renault4" -> "renault", "4")."""
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    for k, v in ASR_ALIASES.items():
        s = re.sub(r"(?<![a-z])%s(?![a-z])" % re.escape(k), " " + v + " ", s)
    return re.findall(r"[a-z]+|[0-9]+", s)


def fold(t):
    """Comparison key that ignores plural/feminine endings, -er/-é/-ez/-ent verb homophones and units."""
    t = UNITS.get(t, t)
    if len(t) > 4 and t.endswith("ent"):
        t = t[:-2]
    if len(t) > 4 and (t.endswith("er") or t.endswith("ez")):
        t = t[:-1]
    for suf in ("s", "e"):
        if len(t) > 3 and t.endswith(suf):
            t = t[:-1]
    return t


def cues_of(text, max_len=95):
    parts = [p.strip() for p in re.findall(r"[^.?!…]+[.?!…]+(?:\s|$)|[^.?!…]+$", text) if p.strip()]
    res = []
    for p in parts:
        if len(p) <= max_len + 15:
            res.append(p)
            continue
        words = p.split(" ")
        n = math.ceil(len(p) / max_len)
        size = math.ceil(len(words) / n)
        res += [" ".join(words[i:i + size]) for i in range(0, len(words), size)]
    merged = []
    for c in res:
        if merged and len(c) < 18:
            merged[-1] += " " + c
        else:
            merged.append(c)
    return merged


def main():
    script_path, voice_dir, out_dir, audio_json = sys.argv[1:5]
    script = json.load(open(script_path))
    takes = script.get("takes", {})
    tempo = float(script.get("voice", {}).get("tempo", 1.0))
    os.makedirs(out_dir, exist_ok=True)
    scenes = [s for s in script["scenes"] if s.get("narration")]
    result = {"voice": {}}
    report = []
    order = []
    for s in scenes:
        if s["passage"] not in order:
            order.append(s["passage"])
    for p in order:
        take = takes.get(p, "a")
        base = os.path.join(voice_dir, "%s-%s" % (p, take))
        audio = next((base + e for e in (".wav", ".mp3") if os.path.exists(base + e)), None)
        if not audio:
            sys.exit("Missing audio for passage %s take %s in %s" % (p, take, voice_dir))
        words = json.load(open(base + ".stt.json"))["words"]
        heard = [(t, w["start"], w["end"]) for w in words for t in htoks(w["text"])]
        group = [s for s in scenes if s["passage"] == p]
        ref, owner = [], []
        for k, s in enumerate(group):
            for t in toks(s["narration"]):
                ref.append(t)
                owner.append(k)
        sm = difflib.SequenceMatcher(None, [fold(t) for t in ref], [fold(h[0]) for h in heard], autojunk=False)
        m = {}
        for blk in sm.get_matching_blocks():
            for i in range(blk.size):
                m[blk.a + i] = blk.b + i
        content = [i for i, t in enumerate(ref) if t not in NUM and not t.isdigit()]
        ratio = sum(1 for i in content if i in m) / max(1, len(content))
        report.append("passage %s take %s: %.0f%% of script words heard" % (p, take, ratio * 100))
        if ratio < 0.9:
            sys.exit("Take %s-%s matches only %.0f%% of the script words: regenerate it.\n%s" % (p, take, ratio * 100, report[-1]))
        # time of every script token: matched -> heard time; unmatched -> interpolated between anchors
        times = [None] * len(ref)
        for i, j in m.items():
            times[i] = (heard[j][1], heard[j][2])
        anchors = [i for i in range(len(ref)) if times[i]]
        for i in range(len(ref)):
            if times[i]:
                continue
            prev = max([a for a in anchors if a < i], default=None)
            nxt = min([a for a in anchors if a > i], default=None)
            if prev is None:
                times[i] = (max(0.0, times[nxt][0] - 0.3 * (nxt - i)),) * 2
            elif nxt is None:
                times[i] = (times[prev][1] + 0.3 * (i - prev),) * 2
            else:
                t0, t1 = times[prev][1], times[nxt][0]
                f = (i - prev) / (nxt - prev)
                times[i] = (t0 + (t1 - t0) * f, t0 + (t1 - t0) * f)
        for k, s in enumerate(group):
            idx = [i for i in range(len(ref)) if owner[i] == k]
            start, end = times[idx[0]][0], times[idx[-1]][1]
            nxt = times[idx[-1] + 1][0] if idx[-1] + 1 < len(ref) else end + 0.6
            a, b = max(0.0, start - 0.08), min(end + 0.3, (end + nxt) / 2 + 0.12)
            dst = os.path.join(out_dir, s["id"] + ".wav")
            dur_src = b - a
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", audio, "-af",
                            "atrim=%.3f:%.3f,asetpts=PTS-STARTPTS,atempo=%.4f,afade=t=in:d=0.03,afade=t=out:st=%.3f:d=0.08,"
                            "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000" % (a, b, tempo, max(0, dur_src / tempo - 0.08)),
                            "-ar", "48000", "-ac", "2", dst], check=True)
            dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                 "-of", "default=nw=1:nk=1", dst]).decode())
            spoken = [{"t": ref[i], "s": round(max(0.0, times[i][0] - a) / tempo, 3), "e": round(max(0.0, times[i][1] - a) / tempo, 3)} for i in idx]
            clean = TAG.sub("", s["narration"]).strip()
            cues, used = [], 0
            for c in cues_of(clean):
                first = idx[min(used, len(idx) - 1)]
                used += len(toks(c))
                cues.append({"start": round(max(0.0, times[first][0] - a - 0.05) / tempo, 3), "text": c})
            for i, c in enumerate(cues):
                c["end"] = round(cues[i + 1]["start"] if i + 1 < len(cues) else dur + 0.3, 3)
            result["voice"][s["id"]] = {"file": "voice/%s.wav" % s["id"], "durationSec": round(dur, 3), "words": spoken, "cues": cues}
            report.append("  %-14s %5.2f s, %d cues" % (s["id"], dur, len(cues)))
    json.dump(result, open(audio_json, "w"), ensure_ascii=False, indent=1)
    print("\n".join(report))
    print("total voice: %.1f s" % sum(v["durationSec"] for v in result["voice"].values()))


if __name__ == "__main__":
    main()
