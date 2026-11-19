#!/usr/bin/env python3
"""Voix off VoiceStudio (VoxCPM2) : une génération par scène, plusieurs graines, transcription de chaque prise.

  python3 tts_scenes.py work/script.json work/voice-scenes [--scenes intro,dc] [--seeds 303,304] [--dry-run]

script.json "voice" :
  {"provider": "voicestudio", "endpoint": "http://localhost:3900", "model": "voxcpm2", "profile": "<id>",
   "language": "fr", "num_step": 20, "guidance_scale": 1.7, "seeds": [300, 301, 302], "pronounce": {"TGBT": "T-G-B-T"}}

Chaque scène est lue d'après scene["spoken"] (texte dirigé pour l'oreille) ou, à défaut, scene["narration"].
"spoken" garde exactement les mots de "narration" (après "pronounce") : seule la ponctuation change, pour que
les animations déclenchées sur un mot et les sous-titres restent calés.
Pas de consigne de ton ("instruct") ni de ralentissement ("tempo") : la consigne fait quitter à VoxCPM2 le
clonage fidèle (mélodie aplatie, voix moins ressemblante) et l'étirement temporel abîme la parole.
Écrit <scène>-s<graine>.wav et <scène>-s<graine>.stt.json (texte transcrit, mots horodatés, texte dit).
"""
import argparse, json, os, re, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from split_voice import toks  # noqa: E402
from tts_passages import http, multipart, spoken as apply_pronounce  # noqa: E402

DEFAULTS = {"model": "voxcpm2", "language": "fr", "num_step": 20, "guidance_scale": 1.7, "seeds": [300, 301, 302]}


def voice_config(script):
    v = dict(DEFAULTS, **script.get("voice", {}))
    if v.get("provider", "voicestudio") != "voicestudio":
        sys.exit("tts_scenes.py ne sert que VoiceStudio. Pour ElevenLabs, utiliser tts_passages.py (voir SKILL.md).")
    if not v.get("profile"):
        sys.exit("script.json voice.profile manque : id du profil VoiceStudio (GET /profiles).")
    if (v.get("instruct") or "").strip():
        sys.exit("script.json voice.instruct est rempli : retirez-le. Avec une consigne, VoxCPM2 quitte le clonage fidèle "
                 "(mélodie aplatie, voix moins ressemblante). Le ton se dirige par le texte de scene.spoken.")
    if float(v.get("tempo", 1.0)) != 1.0:
        sys.exit("script.json voice.tempo vaut %s : retirez-le. Le ralentissement par étirement abîme la parole ; "
                 "le rythme vient de la ponctuation de scene.spoken et des respirations ajoutées par voice_scenes.py." % v["tempo"])
    return v


def scene_text(scene, pronounce):
    """Texte envoyé au moteur. Échoue si le texte dirigé ne garde pas les mots de la narration."""
    narration = scene["narration"].strip()
    text = (scene.get("spoken") or narration).strip()
    if re.search(r"[()\[\]]", text):
        sys.exit("Scène %s : pas de parenthèses ni de crochets dans le texte dit (VoxCPM2 lit une parenthèse initiale "
                 "comme une consigne et quitte le clonage fidèle)." % scene["id"])
    said, ref = toks(apply_pronounce(text, pronounce)), toks(apply_pronounce(narration, pronounce))
    if said != ref:
        i = next((k for k in range(min(len(said), len(ref))) if said[k] != ref[k]), min(len(said), len(ref)))
        sys.exit("Scène %s : spoken ne garde pas les mots de narration (écart au mot %d : %r au lieu de %r). "
                 "Changez seulement la ponctuation, ou ajoutez la forme orale dans voice.pronounce."
                 % (scene["id"], i, " ".join(said[i:i + 4]), " ".join(ref[i:i + 4])))
    return apply_pronounce(text, pronounce)


def transcribe(base, path, language):
    """Transcription horodatée par VoiceStudio. Le moteur renvoie parfois une suite de <unk> sur un fichier
    pourtant correct : la réponse est alors redemandée, jusqu'à 5 fois, puis le script s'arrête."""
    data, ctype = multipart({"model": "whisper-1", "language": language, "response_format": "verbose_json",
                             "timestamp_granularities[]": "word"}, "file", path, "audio/wav")
    last = None
    for _ in range(5):
        t = http(base + "/v1/audio/transcriptions", data, {"Content-Type": ctype})
        if isinstance(t, dict) and t.get("words") and "<unk>" not in (t.get("text") or ""):
            return t
        last = t
    sys.exit("Transcription VoiceStudio inexploitable pour %s après 5 essais (réponse : %s). "
             "Vérifiez le moteur de transcription dans VoiceStudio, puis relancez." % (path, str(last)[:300]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("outdir")
    ap.add_argument("--scenes", help="ids séparés par des virgules (défaut : toutes les scènes narrées)")
    ap.add_argument("--seeds", help="graines séparées par des virgules (défaut : voice.seeds)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    script = json.load(open(a.script))
    v = voice_config(script)
    pron = v.get("pronounce", {})
    seeds = [int(x) for x in a.seeds.split(",")] if a.seeds else [int(x) for x in v["seeds"]]
    scenes = [s for s in script["scenes"] if s.get("narration")]
    if a.scenes:
        wanted = a.scenes.split(",")
        missing = [x for x in wanted if x not in {s["id"] for s in scenes}]
        if missing:
            sys.exit("Scènes inconnues : %s" % ", ".join(missing))
        scenes = [s for s in scenes if s["id"] in wanted]
    todo = [(s["id"], scene_text(s, pron)) for s in scenes]
    for sid, text in todo:
        print("%-14s %4d car.  %s" % (sid, len(text), text[:90]))
    print("%d scènes x %d graines = %d générations (%d pas, guidage %.2f)" % (len(todo), len(seeds), len(todo) * len(seeds), v["num_step"], v["guidance_scale"]))
    if a.dry_run:
        return
    base = v.get("endpoint", "http://localhost:3900").rstrip("/")
    health = http(base + "/health", timeout=10)
    if not isinstance(health, dict) or health.get("status") != "ok":
        sys.exit("VoiceStudio ne répond pas correctement sur %s : %s. Lancez l'application VoiceStudio." % (base, health))
    os.makedirs(a.outdir, exist_ok=True)
    for sid, text in todo:
        for seed in seeds:
            out = os.path.join(a.outdir, "%s-s%d.wav" % (sid, seed))
            if os.path.exists(out) and os.path.exists(out[:-4] + ".stt.json"):
                continue
            body = {"model": v["model"], "voice": v["profile"], "input": text, "language": v["language"], "response_format": "wav",
                    "seed": seed, "num_step": int(v["num_step"]), "guidance_scale": float(v["guidance_scale"])}
            t0 = time.time()
            audio = http(base + "/v1/audio/speech", json.dumps(body).encode(), {"Content-Type": "application/json"})
            if not isinstance(audio, bytes) or audio[:4] != b"RIFF":
                sys.exit("VoiceStudio n'a pas renvoyé d'audio pour %s graine %d : %s" % (sid, seed, str(audio)[:300]))
            open(out, "wb").write(audio)
            stt = transcribe(base, out, v["language"])
            stt["spoken"] = text
            json.dump(stt, open(out[:-4] + ".stt.json", "w"), ensure_ascii=False)
            print("%s graine %d : %.0f s" % (sid, seed, time.time() - t0), flush=True)


if __name__ == "__main__":
    main()

