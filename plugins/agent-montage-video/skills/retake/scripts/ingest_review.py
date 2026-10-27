#!/usr/bin/env python3
"""Reçoit une revue exportée par l'application Retake et prépare la liste de corrections de l'agent.

Étapes : retrouve le rendu exact grâce à l'empreinte SHA-256, extrait la revue dans
projects/<projet>/work/reviews/, vérifie chaque image du relecteur contre le rendu avec ffmpeg,
transcrit les commentaires vocaux en local (commande « transcrire ») et relie chaque commentaire
à la scène et à la voix off du projet Remotion quand work/layout.json existe.

Usage :
    .venv/bin/python plugins/agent-montage-video/skills/retake/scripts/ingest_review.py REVUE.zip
        [--video RENDU.mp4] [--vocabulaire "IRVE, Rossini"] [--sans-transcription]
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageStat
except ImportError:
    sys.exit("Pillow manque : lance ce script avec .venv/bin/python (voir scripts/setup_linux.sh).")

ROOT = Path(__file__).resolve().parents[5]
SHAPES = {"rect": "zone", "pin": "point", "ellipse": "cercle", "arrow": "flèche", "pen": "tracé"}
STATUS = {"corrige": "corrigé", "pas_corrige": "pas corrigé", "a_verifier": "non vérifié", "nouvelle": "nouveau"}


def fail(msg):
    sys.exit("ERREUR : " + msg)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fmt(sec):
    if sec is None:
        return "?"
    ms = round(sec * 1000)
    h, m, s = ms // 3600000, ms // 60000 % 60, ms // 1000 % 60
    return (f"{h}:{m:02d}" if h else f"{m:02d}") + f":{s:02d}.{ms % 1000:03d}"


def extract(review_path, dest):
    """Copie la revue (zip ou dossier) dans dest, sans le dossier racine de l'archive."""
    if review_path.is_dir():
        shutil.copytree(review_path, dest, dirs_exist_ok=True)
        return
    with zipfile.ZipFile(review_path) as z:
        for info in z.infolist():
            parts = Path(info.filename).parts
            if info.is_dir() or len(parts) < 2 or ".." in parts:
                continue
            target = dest / Path(*parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)


def find_render(report, explicit):
    want = report["video"]["sha256"]
    if explicit:
        p = Path(explicit).resolve()
        if not p.is_file():
            fail(f"vidéo introuvable : {p}")
        got = sha256(p)
        if got != want:
            fail(f"{p.name} n'est pas la version relue (SHA-256 {got[:12]}… au lieu de {want[:12]}…). "
                 "Les instants de la revue ne correspondraient pas : retrouve le rendu exact envoyé au relecteur.")
        return p
    size = report["video"].get("sizeBytes")
    candidates = {p.resolve() for pat in ("projects/*/out/**/*", "projects/*/work/renders/*", "projects/*/motion/out/*", "output/*")
                  for p in ROOT.glob(pat) if p.suffix.lower() in (".mp4", ".mov", ".m4v", ".webm") and p.is_file()}
    for p in sorted(candidates, key=lambda x: x.stat().st_mtime, reverse=True):
        if size and p.stat().st_size != size:
            continue
        if sha256(p) == want:
            return p
    fail(f"aucun rendu du dépôt n'a l'empreinte {want} ({report['video']['fileName']}, {size} octets). "
         "Passe le fichier avec --video, ou récupère la version exacte envoyée au relecteur.")


def check_frame(video, raw_jpg, frame, fps):
    """Compare l'image du relecteur aux images frame-2..frame+2 du rendu."""
    start = max(0, frame - 2)
    with tempfile.TemporaryDirectory() as d:
        seek = ["-ss", f"{(start - 0.25) / fps:.6f}"] if start else []
        subprocess.run(["ffmpeg", "-v", "error", *seek, "-i", str(video), "-frames:v", str(frame + 3 - start),
                        "-vf", "scale=480:270", "-fps_mode", "passthrough", os.path.join(d, "f%d.png")], check=True)
        files = sorted(Path(d).glob("f*.png"), key=lambda p: int(p.stem[1:]))
        raw = Image.open(raw_jpg).convert("RGB").resize((480, 270))
        diffs = {start + i: sum(ImageStat.Stat(ImageChops.difference(raw, Image.open(p).convert("RGB"))).mean) / 3
                 for i, p in enumerate(files)}
    best = min(diffs, key=diffs.get)
    return {"frame": frame, "bestFrame": best, "diff": round(diffs.get(frame, 999), 2),
            "neighbours": {k: round(v, 2) for k, v in diffs.items()},
            "ok": frame in diffs and diffs[frame] <= diffs[best] + 0.05}


def transcribe(files, outdir, vocab):
    exe = shutil.which("transcrire")
    if not exe:
        fail("la commande « transcrire » est introuvable sur cette machine (voir le skill transcription-audio-fr). "
             "Installe-la, lance le script sur le Mac mini de Tony, ou relance avec --sans-transcription "
             "et écoute toi-même les fichiers audio/*.wav.")
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "--sortie", str(outdir)] + (["--vocabulaire", vocab] if vocab else []) + [str(f) for f in files]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        fail("la transcription a échoué :\n" + (r.stderr or r.stdout)[-2000:])
    texts = {}
    for f in files:
        t = outdir / (Path(f).stem + ".txt")
        if not t.exists():
            fail(f"transcription manquante pour {Path(f).name} (attendue : {t}).")
        texts[Path(f).name] = t.read_text(encoding="utf-8").strip()
    return texts


def load_scenes(project):
    """Plan des scènes d'un projet Remotion maison : work/layout.json, motion/src/script.json et audio.json."""
    layout_p = project / "work" / "layout.json"
    script_p = project / "motion" / "src" / "script.json"
    if not layout_p.exists() or not script_p.exists():
        return None
    layout = json.loads(layout_p.read_text())
    script = json.loads(script_p.read_text())
    audio_p = project / "motion" / "src" / "audio.json"
    voice = json.loads(audio_p.read_text()).get("voice", {}) if audio_p.exists() else {}
    scenes = {s["id"]: s for s in script.get("scenes", [])}
    chapters = {c["id"]: c for c in script.get("chapters", [])}
    out = []
    for i, entry in enumerate(layout):
        sid, start, dur = entry[0], entry[1], entry[2]
        lead = script.get("leadSec", 0) if i == 0 else 0.15  # même décalage que FormationVideo.tsx
        sc = scenes.get(sid, {})
        words = [(start + lead + w["s"], w["t"]) for w in voice.get(sid, {}).get("words", [])]
        out.append({"id": sid, "start": start, "end": start + dur, "narration": sc.get("narration", ""),
                    "chapter": chapters.get(sc.get("chapter"), {}).get("title"), "words": words})
    return out


def scene_at(scenes, t):
    for s in scenes or []:
        if s["start"] <= t < s["end"]:
            near = [w for (a, w) in s["words"] if t - 2.5 <= a <= t + 1.0]
            return {"id": s["id"], "chapter": s["chapter"], "start": round(s["start"], 3), "end": round(s["end"], 3),
                    "narration": s["narration"], "voiceAround": " ".join(near)}
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("revue", help="archive .zip (ou dossier) exportée par l'application Retake")
    ap.add_argument("--video", help="rendu relu, si le script ne le retrouve pas seul dans projects/")
    ap.add_argument("--vocabulaire", default="", help="noms propres attendus dans les commentaires vocaux")
    ap.add_argument("--sans-transcription", action="store_true", help="ne pas transcrire les commentaires vocaux")
    args = ap.parse_args()

    src = Path(args.revue).resolve()
    if not src.exists():
        fail(f"revue introuvable : {src}")
    with tempfile.TemporaryDirectory() as tmp:
        extract(src, Path(tmp))
        rp = Path(tmp) / "rapport.json"
        if not rp.exists():
            fail("rapport.json absent : ce n'est pas une revue exportée par l'application Retake.")
        report = json.loads(rp.read_text(encoding="utf-8"))
        if report.get("schema") != "revue-video/1":
            fail(f"schéma inconnu : {report.get('schema')}")
        video = find_render(report, args.video)
        project = next((p for p in [video.parent, *video.parents] if p.parent.name == "projects"), None)
        if project is None:
            fail(f"le rendu {video} n'est pas dans un dossier projects/<projet>/.")
        name = src.stem if src.is_file() else src.name
        dest = project / "work" / "reviews" / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(tmp, dest)

    fps = report["video"].get("fps")
    clips = [dest / c["file"] for n in report["notes"] for c in n["clips"]]
    texts = {}
    if clips and not args.sans_transcription:
        print(f"Transcription de {len(clips)} commentaire(s) vocal(aux)…", flush=True)
        texts = transcribe(clips, dest / "transcriptions", args.vocabulaire)
    scenes = load_scenes(project)

    items = []
    for n in report["notes"]:
        check = check_frame(video, dest / n["images"]["raw"], n["frame"], fps) if fps and n.get("frame") is not None else None
        for c in n["clips"]:
            c["transcript"] = texts.get(Path(c["file"]).name)
        items.append({**n, "frameCheck": check, "scene": scene_at(scenes, n["time"])})

    rel = lambda p: str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
    (dest / "corrections.json").write_text(json.dumps({
        "review": name, "reviewer": report.get("reviewer"), "video": rel(video), "sha256": report["video"]["sha256"],
        "sceneMapping": bool(scenes), "items": items}, ensure_ascii=False, indent=2), encoding="utf-8")

    bad = [i for i in items if i["frameCheck"] and not i["frameCheck"]["ok"]]
    md = [f"# Corrections demandées par {report.get('reviewer') or 'le relecteur'}", "",
          f"Rendu relu : `{rel(video)}` (empreinte SHA-256 vérifiée). {len(items)} commentaire(s). "
          f"Revue extraite dans `{rel(dest)}`.", ""]
    if bad:
        md += [f"**Attention : {len(bad)} image(s) ne correspondent pas au rendu à l'image près. Vérifie ces commentaires à la main.**", ""]
    if not scenes:
        md += ["Pas de correspondance avec les scènes : ce projet n'a pas de `work/layout.json` au format Remotion maison.", ""]
    for i in items:
        sc = i["scene"]
        title = f"## {i['number']}. {fmt(i['time'])} (image {i['frame']})"
        if sc:
            title += f" · scène « {sc['id']} »" + (f", chapitre « {sc['chapter']} »" if sc["chapter"] else "")
        md += [title, ""]
        if i.get("origin"):
            line = f"- Revue précédente, point {i['origin']['number']} : **{STATUS.get(i['status'], i['status'])}**"
            if i["origin"].get("text"):
                line += f" (« {i['origin']['text']} »)"
            md.append(line)
        if i["text"]:
            md.append(f"- Écrit : « {i['text']} »")
        for c in i["clips"]:
            if c.get("transcript"):
                md.append(f"- Dit ({c['file']}, {c['duration']:.1f} s) : « {c['transcript']} »")
            else:
                md.append(f"- Commentaire vocal à écouter : `{c['file']}` ({c['duration']:.1f} s)")
        for k, s in enumerate(i["shapes"]):
            b = s["boundsPx"]
            md.append(f"- Repère {k + 1} ({SHAPES.get(s['type'], s['type'])}, {s['place']}) : x {b['x']} à {b['x'] + b['w']}, y {b['y']} à {b['y'] + b['h']} px")
        if i.get("lookback"):
            md.append(f"- Dit pendant la lecture : regarde aussi de {fmt(i['lookback']['from'])} à {fmt(i['lookback']['to'])}")
        if sc:
            if sc["voiceAround"]:
                md.append(f"- Voix off à cet instant : « … {sc['voiceAround']} … »")
            md.append(f"- Scène de {fmt(sc['start'])} à {fmt(sc['end'])}, narration : « {sc['narration'][:300]} »")
        ck = i["frameCheck"]
        if ck:
            md.append("- Contrôle image : " + ("identique au rendu" if ck["ok"] else f"ÉCART, image la plus proche {ck['bestFrame']}") + f" (écart {ck['diff']})")
        md += [f"- Image annotée : `{i['images']['annotated']}`", ""]
    (dest / "corrections.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Corrections : {dest / 'corrections.md'}")
    if bad:
        print(f"ATTENTION : {len(bad)} image(s) ne correspondent pas au rendu, voir corrections.md")


if __name__ == "__main__":
    main()
