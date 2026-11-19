#!/usr/bin/env python3
"""Choisit la meilleure prise de chaque scène, place les respirations, règle le volume une fois, écrit audio.json.

  .venv/bin/python voice_scenes.py work/script.json work/voice-scenes motion/public/voice motion/src/audio.json

Prises produites par tts_scenes.py. Pour chaque scène :
- contrôle de chaque prise : texte entendu (93 % des mots au moins, fin présente), aucune pause de 0,35 s ou plus
  hors ponctuation, intonation (écart type de F0 d'au moins 2,5 demi-tons, voice-intonation/prosody.py),
  ressemblance avec la voix de référence (ECAPA, cosinus d'au moins 0,85), pas de mots ajoutés ;
- choix parmi les prises valides par rang : ressemblance, intonation, respirations de fin de phrase, fidélité ;
- respirations : la ponctuation du texte dit est rattachée aux mots transcrits par leur POSITION, puis les silences
  trop courts sont allongés en dupliquant le silence de la prise (point 0,55 s, deux-points 0,34 s, virgule 0,20 s) ;
  une fin de phrase sans silence est ouverte au point le plus calme entre les deux mots, seulement s'il est
  à 20 dB sous la parole. La parole n'est jamais étirée ;
- un seul gain pour toute la séquence (-16 LUFS), limiteur à -1,5 dB.
Puis chaque fichier final est retranscrit : aucun silence de 0,2 s hors ponctuation, texte complet, intonation.
Échoue en nommant la scène et la commande à relancer.

Dépendances : numpy (.venv), ffmpeg, VoiceStudio en marche (référence du profil et transcriptions), et un Python
avec torch, librosa et speechbrain pour la ressemblance : VOICE_EVAL_PYTHON, sinon le Python embarqué de VoiceStudio.
"""
import difflib, json, os, re, subprocess, sys, urllib.request
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import split_voice as SV  # noqa: E402
from tts_scenes import scene_text, transcribe, voice_config  # noqa: E402

PROSODY = os.path.join(HERE, "..", "..", "voice-intonation", "scripts", "prosody.py")
SR = 48000
PUNCT_END = re.compile(r"[.?!]$")
RANK = {None: 0, "comma": 1, "colon": 2, "end": 3}
TARGET = {"end": 0.55, "colon": 0.34, "comma": 0.20}


# ---------- audio ----------
def read(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def write_f32(path, y):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_f32le", path],
                   input=y.astype(np.float32).tobytes(), check=True)


def frames_db(y, hop=0.01):
    h = int(SR * hop); n = len(y) // h
    e = np.sqrt(np.mean(y[: n * h].reshape(n, h) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(e), hop


def silences(y, min_len=0.06, below=25):
    db, hop = frames_db(y)
    thr = np.percentile(db, 95) - below
    out, start = [], None
    for i, v in enumerate(np.append(db, 0) < thr):
        if v and start is None:
            start = i
        if not v and start is not None:
            if (i - start) * hop >= min_len:
                out.append((start * hop, i * hop))
            start = None
    return out


def lufs(path):
    o = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[0-9.]+) LUFS", o)[-1])


# ---------- texte ----------
def f2(t):
    return re.sub(r"[es]+$", "", SV.fold(t)) or SV.fold(t)


def words_of(stt):
    return [(w["word"].strip(), float(w["start"]), float(w["end"])) for w in stt["words"] if w["word"].strip()]


def content_match(spoken, heard):
    ref, hyp = SV.toks(spoken), SV.htoks(heard)
    sm = difflib.SequenceMatcher(None, [f2(t) for t in ref], [f2(h) for h in hyp], autojunk=False)
    matched = set()
    for b in sm.get_matching_blocks():
        matched.update(range(b.a, b.a + b.size))
    content = [i for i, t in enumerate(ref) if t not in SV.NUM and not t.isdigit() and len(t) > 1]
    ratio = sum(i in matched for i in content) / max(1, len(content))
    inserts = [hyp[j1:j2] for op, i1, i2, j1, j2 in sm.get_opcodes()
               if op == "insert" and any(not x.isdigit() and x not in SV.NUM for x in hyp[j1:j2])]
    return ratio, all(i in matched for i in content[-3:]), inserts


def punct_by_word(words, spoken):
    """Ponctuation du texte dit rattachée à chaque mot transcrit par sa position (alignement mot à mot)."""
    sp = []
    for tok in re.findall(r"[A-Za-zÀ-ÿ0-9'’-]+|[.,;:?!]", spoken):
        if re.fullmatch(r"[.,;:?!]", tok):
            if sp:
                kind = "end" if tok in ".?!" else ("colon" if tok in ":;" else "comma")
                if RANK[kind] > RANK[sp[-1][1]]:
                    sp[-1][1] = kind
            continue
        for t in SV.toks(tok):
            sp.append([f2(t), None])
    hy, owner = [], []
    for i, (w, s, e) in enumerate(words):
        for t in SV.htoks(w):
            hy.append(f2(t)); owner.append(i)
    out, matched = [None] * len(words), set()
    sm = difflib.SequenceMatcher(None, [x[0] for x in sp], hy, autojunk=False)
    for b in sm.get_matching_blocks():
        for k in range(b.size):
            j, i = b.a + k, owner[b.b + k]
            matched.add(i)
            if sp[j][1] and RANK[sp[j][1]] > RANK[out[i]]:
                out[i] = sp[j][1]
    for i, (w, s, e) in enumerate(words):
        if i not in matched and out[i] is None:
            out[i] = "end" if PUNCT_END.search(w) else ("comma" if w.endswith(",") else None)
    return out


def gap_silence(sil, e, nxt, pad):
    return max([min(b, nxt + pad) - max(a, e - pad) for a, b in sil if b > e - pad and a < nxt + pad], default=0)


def stray_pauses(y, words, spoken, min_gap, pad):
    marks, sil = punct_by_word(words, spoken), silences(y)
    return [(w, words[k + 1][0], round(g, 2)) for k, (w, s, e) in enumerate(words[:-1])
            if not marks[k] and (g := gap_silence(sil, e, words[k + 1][1], pad)) >= min_gap]


def end_pauses(y, words, spoken):
    marks, sil = punct_by_word(words, spoken), silences(y)
    ends = [k for k in range(len(words) - 1) if marks[k] == "end"]
    ok = sum(gap_silence(sil, words[k][2], words[k + 1][1], 0.12) >= 0.25 for k in ends)
    return ok, len(ends)


def prosody(path):
    out = subprocess.run([sys.executable, PROSODY, path], capture_output=True, text=True, check=True).stdout
    return json.loads(out.strip().splitlines()[-1])


# ---------- ressemblance ----------
def eval_python():
    env = os.environ.get("VOICE_EVAL_PYTHON")
    cands = [env] if env else [os.path.join(os.path.expanduser("~"), p) for p in (
        "Library/Application Support/VoiceStudio/runtime/project/.venv/bin/python",
        ".local/share/VoiceStudio/runtime/project/.venv/bin/python")]
    for c in cands:
        if c and os.path.exists(c) and subprocess.run([c, "-c", "import torch, librosa, speechbrain"], capture_output=True).returncode == 0:
            return c
    sys.exit("Aucun Python avec torch, librosa et speechbrain pour mesurer la ressemblance de voix (essayé : %s). "
             "Définissez VOICE_EVAL_PYTHON vers un tel interpréteur (le Python embarqué de VoiceStudio convient)." % ", ".join(c for c in cands if c))


def similarity(ref, files):
    r = subprocess.run([eval_python(), os.path.join(HERE, "speaker_similarity.py"), ref] + files, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("Mesure de ressemblance impossible : %s" % r.stderr.strip()[-800:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def reference(v, workdir):
    path = os.path.join(workdir, "_reference-%s.wav" % v["profile"])
    if not os.path.exists(path):
        url = "%s/profiles/%s/audio" % (v.get("endpoint", "http://localhost:3900").rstrip("/"), v["profile"])
        try:
            data = urllib.request.urlopen(url, timeout=30).read()
        except Exception as e:  # noqa: BLE001
            sys.exit("Référence du profil %s introuvable sur %s (%s). Lancez VoiceStudio." % (v["profile"], url, e))
        if data[:4] != b"RIFF":
            sys.exit("La référence du profil %s n'est pas un WAV : %r" % (v["profile"], data[:120]))
        open(path, "wb").write(data)
    return path


# ---------- notation ----------
def score(scenes, texts, v, takes_dir):
    ref = reference(v, takes_dir)
    report = {}
    for s in scenes:
        sid, spoken = s["id"], texts[s["id"]]
        wavs = sorted(f for f in os.listdir(takes_dir) if re.fullmatch(re.escape(sid) + r"-s\d+\.wav", f))
        if not wavs:
            sys.exit("Aucune prise pour la scène %s dans %s : lancez tts_scenes.py." % (sid, takes_dir))
        sims = similarity(ref, [os.path.join(takes_dir, f) for f in wavs])
        rows = []
        for f in wavs:
            path = os.path.join(takes_dir, f)
            stt = json.load(open(path[:-4] + ".stt.json")); words = words_of(stt); y = read(path)
            ratio, last_ok, inserts = content_match(spoken, stt["text"])
            stray = stray_pauses(y, words, spoken, 0.35, 0.12)
            ok_ends, n_ends = end_pauses(y, words, spoken)
            pr = prosody(path); sim = sims[path]
            fails = [m for c, m in ((ratio < 0.93, "texte %.0f %%" % (ratio * 100)), (not last_ok, "fin manquante"),
                                    (bool(stray), "pause hors ponctuation %s" % stray), (pr["pitch_std_st"] < 2.5, "intonation plate"),
                                    (sim < 0.85, "voix éloignée %.2f" % sim), (len(inserts) >= 2, "mots ajoutés %s" % inserts)) if c]
            rows.append(dict(take=f, ratio=round(ratio, 3), ecapa=round(sim, 3), f0_std=pr["pitch_std_st"],
                             end_ratio=ok_ends / n_ends if n_ends else 1.0, fails=fails))
        ok = [r for r in rows if not r["fails"]]
        for key in ("ecapa", "f0_std", "end_ratio", "ratio"):
            for rank, r in enumerate(sorted(ok, key=lambda x: x[key], reverse=True)):
                r["rank_" + key] = rank
        for r in ok:
            r["score"] = r["rank_ecapa"] + r["rank_f0_std"] + r["rank_end_ratio"] + 0.5 * r["rank_ratio"]
        best = min(ok, key=lambda r: (r["score"], -r["ecapa"]))["take"] if ok else None
        report[sid] = {"best": best, "takes": rows}
        print("%-14s -> %s   %s" % (sid, best or "AUCUNE", "; ".join("%s %s" % (r["take"][len(sid) + 1:-4], r["fails"] or "ok")
                                                                   for r in rows)), flush=True)
    json.dump(report, open(os.path.join(takes_dir, "report.json"), "w"), ensure_ascii=False, indent=1)
    missing = [k for k, r in report.items() if not r["best"]]
    if missing:
        sys.exit("Aucune prise valable pour %s. Générez d'autres graines : python3 tts_scenes.py <script> <dossier> --scenes %s --seeds 303,304,305"
                 % (", ".join(missing), ",".join(missing)))
    return report


# ---------- respirations ----------
def tile(seg, n):
    xf = int(0.01 * SR)
    if len(seg) < 3 * xf:
        seg = np.zeros(5 * xf, dtype=np.float32)
    ramp = np.linspace(0, 1, xf, dtype=np.float32)
    out = seg.copy()
    while len(out) < n + xf:
        out[-xf:] = out[-xf:] * (1 - ramp) + seg[:xf] * ramp
        out = np.concatenate([out, seg[xf:]])
    return out[:n]


def shape(y, words, spoken):
    marks, sil = punct_by_word(words, spoken), silences(y)
    db, hop = frames_db(y); h = int(SR * hop)
    sm = np.convolve(db, np.ones(5) / 5, mode="same")
    i0 = int(np.argmin(sm[5:-5])) + 5
    tone = y[(i0 - 2) * h:(i0 + 3) * h].copy()
    quiet = np.percentile(db, 95) - 20
    edits, log = [], []
    for k, (w, s, e) in enumerate(words[:-1]):
        target = TARGET.get(marks[k])
        if not target:
            continue
        nxt = words[k + 1][1]
        cand = [(max(a, e - 0.12), min(b, nxt + 0.12)) for a, b in sil if b > e - 0.12 and a < nxt + 0.12]
        best = max(cand, key=lambda ab: ab[1] - ab[0]) if cand else None
        if best and best[1] - best[0] >= 0.06:
            a, b = best
            if b - a < target:
                edits.append(((a + b) / 2, target - (b - a), y[int(a * SR): int(b * SR)].copy()))
                log.append((w, words[k + 1][0], marks[k], round(target - (b - a), 2)))
        elif marks[k] == "end":
            lo, hi = int(max(0, e - 0.1) / hop), int(min(len(db) - 1, nxt + 0.1) / hop)
            if hi > lo:
                i = lo + int(np.argmin(db[lo:hi + 1]))
                if db[i] <= quiet:
                    edits.append((i * hop, target - 0.03, tone))
                    log.append((w, words[k + 1][0], "end (creux)", round(target - 0.03, 2)))
    parts, last, shifts = [], 0, []
    for mid, add, seg in sorted(edits, key=lambda x: x[0]):
        i = int(mid * SR)
        parts += [y[last:i], tile(seg, int(add * SR))]
        last = i; shifts.append((mid, add))
    parts.append(y[last:])
    return np.concatenate(parts), shifts, log


def remap(t, shifts):
    return t + sum(add for mid, add in shifts if mid < t)


def word_times(narration, heard_words):
    ref = SV.toks(narration)
    heard = [(t, s, e) for w, s, e in heard_words for t in SV.htoks(w)]
    sm = difflib.SequenceMatcher(None, [SV.fold(t) for t in ref], [SV.fold(h[0]) for h in heard], autojunk=False)
    times = [None] * len(ref)
    for b in sm.get_matching_blocks():
        for i in range(b.size):
            times[b.a + i] = heard[b.b + i][1:]
    anchors = [i for i in range(len(ref)) if times[i]]
    if not anchors:
        sys.exit("Aucun mot de la narration retrouvé dans la prise : %s" % narration[:80])
    for i in range(len(ref)):
        if times[i]:
            continue
        prev = max([a for a in anchors if a < i], default=None); nxt = min([a for a in anchors if a > i], default=None)
        if prev is None:
            times[i] = (0.0, 0.0)
        elif nxt is None:
            times[i] = (times[prev][1],) * 2
        else:
            t0, t1 = times[prev][1], times[nxt][0]; f = (i - prev) / (nxt - prev)
            times[i] = (t0 + (t1 - t0) * f,) * 2
    return ref, times


def assemble(scenes, texts, report, takes_dir, outdir, audio_json):
    os.makedirs(outdir, exist_ok=True)
    tmp = os.path.abspath(os.path.join(takes_dir, "_shaped")); os.makedirs(tmp, exist_ok=True)
    meta = {}
    for s in scenes:
        sid = s["id"]; path = os.path.join(takes_dir, report[sid]["best"])
        words = words_of(json.load(open(path[:-4] + ".stt.json")))
        y2, shifts, log = shape(read(path), words, texts[sid])
        w2 = [(w, remap(a, shifts), remap(b, shifts)) for w, a, b in words]
        head, tail = max(0.0, w2[0][1] - 0.05), min(len(y2) / SR, w2[-1][2] + 0.15)
        y3 = y2[int(head * SR): int(tail * SR)].copy(); fd = int(0.01 * SR)
        y3[:fd] *= np.linspace(0, 1, fd); y3[-fd:] *= np.linspace(1, 0, fd)
        write_f32(os.path.join(tmp, sid + ".wav"), y3)
        json.dump(log, open(os.path.join(tmp, sid + ".respirations.json"), "w"), ensure_ascii=False)
        meta[sid] = [(w, max(0, a - head), max(0, b - head)) for w, a, b in w2]
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join("file '%s'\n" % os.path.join(tmp, s["id"] + ".wav").replace("'", "'\\''") for s in scenes))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", os.path.join(tmp, "_all.wav")], check=True)
    gain = -16.0 - lufs(os.path.join(tmp, "_all.wav"))
    print("gain unique pour la séquence : %+.2f dB" % gain)
    audio = {"voice": {}}
    for s in scenes:
        sid = s["id"]; dst = os.path.join(outdir, sid + ".wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(tmp, sid + ".wav"), "-af",
                        "volume=%.3fdB,alimiter=limit=0.84:level=false:attack=1:release=50" % gain,
                        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", dst], check=True)
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", dst]).decode())
        ref, times = word_times(s["narration"], meta[sid])
        clean = SV.TAG.sub("", s["narration"]).strip(); cues, used = [], 0
        for c in SV.cues_of(clean):
            first = min(used, len(ref) - 1); used += len(SV.toks(c))
            cues.append({"start": round(max(0.0, times[first][0] - 0.05), 3), "text": c})
        for i, c in enumerate(cues):
            c["end"] = round(cues[i + 1]["start"] if i + 1 < len(cues) else dur + 0.3, 3)
        audio["voice"][sid] = {"file": "voice/%s.wav" % sid, "durationSec": round(dur, 3),
                               "words": [{"t": ref[i], "s": round(times[i][0], 3), "e": round(times[i][1], 3)} for i in range(len(ref))],
                               "cues": cues}
        print("%-14s %-22s %6.2f s" % (sid, report[sid]["best"], dur))
    json.dump(audio, open(audio_json, "w"), ensure_ascii=False, indent=1)


def verify(scenes, texts, v, outdir):
    base = v.get("endpoint", "http://localhost:3900").rstrip("/"); bad = []
    for s in scenes:
        sid = s["id"]; path = os.path.join(outdir, sid + ".wav")
        stt = transcribe(base, path, v["language"]); words = words_of(stt)
        stray = stray_pauses(read(path), words, texts[sid], 0.2, 0.05)
        ratio, last_ok, _ = content_match(texts[sid], stt["text"]); pr = prosody(path)
        fails = [m for c, m in ((bool(stray), "silence hors ponctuation %s" % stray), (ratio < 0.93, "texte %.0f %%" % (ratio * 100)),
                                (not last_ok, "fin manquante"), (pr["pitch_std_st"] < 2.5, "intonation plate")) if c]
        print("contrôle %-14s texte %3.0f %%  F0 %.2f  %s" % (sid, ratio * 100, pr["pitch_std_st"], fails or "OK"), flush=True)
        if fails:
            bad.append(sid)
    if bad:
        sys.exit("Fichiers finaux refusés : %s. Régénérez ces scènes (tts_scenes.py --scenes %s --seeds 303,304,305) puis relancez."
                 % (", ".join(bad), ",".join(bad)))
    print("Voix validée : %d scènes." % len(scenes))


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    script_path, takes_dir, outdir, audio_json = sys.argv[1:5]
    script = json.load(open(script_path)); v = voice_config(script); pron = v.get("pronounce", {})
    scenes = [s for s in script["scenes"] if s.get("narration")]
    texts = {s["id"]: scene_text(s, pron) for s in scenes}
    report = score(scenes, texts, v, takes_dir)
    assemble(scenes, texts, report, takes_dir, outdir, audio_json)
    verify(scenes, texts, v, outdir)


if __name__ == "__main__":
    main()

