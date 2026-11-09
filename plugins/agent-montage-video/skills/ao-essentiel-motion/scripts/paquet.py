#!/usr/bin/env python3
"""Paquet « Vidéo de l'essentiel » préparé par Oscar (Rossini Sales Suite, Appels d'offres) : vérifier, préparer le
projet Remotion, faire une maquette à voix estimée, choisir les images de relecture.

  python3 paquet.py verifier <paquet.zip>
  python3 paquet.py preparer <paquet.zip> projects/<projet> [--node-modules <dossier node_modules existant>]
  python3 paquet.py estimer projects/<projet>          # maquette : audio.json estimé, sans son, marqué MAQUETTE
  python3 paquet.py images projects/<projet>           # work/still_frames.txt pour motion/stills.mjs

Le ZIP contient PROMPT.md, storyboard.json (forme du plan.json des vidéos Remotion de l'agent : 60 i/s, 1920 × 1080,
plans déclenchés sur un mot de la voix), sources.json, captures/, avatars/ et charte/. Rien n'est inventé ni complété
ici : un fichier manquant, un mot déclencheur absent de la voix ou une capture sans source arrêtent la commande avec
la raison.
"""
import argparse
import json
import os
import re
import shutil
import sys
import unicodedata
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "template")
MOTS_PAR_SECONDE = 2.6
# Prononciation des sigles des marchés publics pour VoiceStudio ; les sous-titres gardent la graphie normale.
PRONONCE = {
    "DCE": "D-C-E", "CCTP": "C-C-T-P", "CCAP": "C-C-A-P", "RC": "R-C", "DPGF": "D-P-G-F", "BPU": "B-P-U",
    "DQE": "D-Q-E", "AE": "A-E", "DC1": "D-C un", "DC2": "D-C deux", "DC4": "D-C quatre", "DUME": "Dume",
    "IRVE": "I-R-V-E", "VRD": "V-R-D", "PV": "P-V", "kWc": "kilowatts-crête", "kVA": "kilovoltampères",
    "kW": "kilowatts", "MOE": "M-O-E", "SPS": "S-P-S", "PGC": "P-G-C",
}


def norm(t):
    return unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()


def toks(t):
    return re.findall(r"[a-z0-9]+", norm(t))


def mot_present(cle, voix):
    """Même règle que wordAt du gabarit : chaque mot de la clé commence un mot consécutif de la voix."""
    want, words = toks(cle), toks(voix)
    return any(all(i + j < len(words) and words[i + j].startswith(w) for j, w in enumerate(want)) for i in range(len(words)))


def lire_zip(chemin):
    if not zipfile.is_zipfile(chemin):
        sys.exit("%s n'est pas un ZIP lisible." % chemin)
    z = zipfile.ZipFile(chemin)
    noms = set(z.namelist())
    for n in ("PROMPT.md", "storyboard.json", "sources.json", "charte/logo.png", "charte/charte.json"):
        if n not in noms:
            sys.exit("Paquet incomplet : %s manque. Faites refaire la vidéo depuis L'essentiel du dossier." % n)
    return z, noms, json.loads(z.read("storyboard.json"))


def verifier(chemin, bavard=True):
    z, noms, sb = lire_zip(chemin)
    erreurs, notes = [], []
    if (sb.get("fps"), sb.get("width"), sb.get("height")) != (60, 1920, 1080):
        erreurs.append("format attendu 1920 × 1080 à 60 i/s, reçu %s × %s à %s" % (sb.get("width"), sb.get("height"), sb.get("fps")))
    caps = {c["id"]: c for c in sb.get("captures") or []}
    agents = {a["id"]: a for a in sb.get("agents") or []}
    gens = {p["id"]: p for p in sb.get("personnes") or []}
    for c in caps.values():
        if c["fichier"] not in noms:
            erreurs.append("capture %s absente du ZIP (%s)" % (c["id"], c["fichier"]))
        if not (c.get("source") or {}).get("explication"):
            erreurs.append("capture %s sans source" % c["id"])
        b = c.get("boite")
        if b and not (0 <= b[0] < b[2] <= c["largeur"] + 2 and 0 <= b[1] < b[3] <= c["hauteur"] + 2):
            erreurs.append("capture %s : passage surligné hors de l'image %s" % (c["id"], b))
    for a in agents.values():
        if a.get("file") and a["file"] not in noms:
            erreurs.append("portrait de %s absent (%s)" % (a["prenom"], a["file"]))
        if not a.get("file"):
            notes.append("%s n'a pas encore de portrait : pastille à sa couleur avec son initiale" % a["prenom"])
    for p in gens.values():
        if p.get("file") and p["file"] not in noms:
            erreurs.append("photo de %s absente (%s)" % (p["nom"], p["file"]))
    vus = set()
    mots = 0
    for s in sb.get("scenes") or []:
        if s["id"] in vus:
            erreurs.append("scène %s en double" % s["id"])
        vus.add(s["id"])
        if not (s.get("voix") or "").strip():
            erreurs.append("scène %s sans voix off" % s["id"])
        mots += len(toks(s.get("voix")))
        for a in s.get("agents") or []:
            if a not in agents:
                erreurs.append("scène %s : agent %s inconnu du storyboard" % (s["id"], a))
        for p in s.get("personnes") or []:
            if p not in gens:
                erreurs.append("scène %s : personne %s inconnue du storyboard" % (s["id"], p))
        for sh in s.get("shots") or []:
            if sh["capture"] not in caps:
                erreurs.append("scène %s : capture %s inconnue" % (s["id"], sh["capture"]))
            if sh["file"] not in noms:
                erreurs.append("scène %s : fichier %s absent" % (s["id"], sh["file"]))
            for k in [sh.get("at")] + [x.get("at") for x in sh.get("cam") or []] + [x.get("at") for x in sh.get("hl") or []]:
                if k and not mot_present(k, s["voix"]):
                    erreurs.append("scène %s : mot déclencheur « %s » absent de la voix" % (s["id"], k))
    if not sb.get("scenes"):
        erreurs.append("storyboard sans scène")
    if erreurs:
        sys.exit("Paquet refusé :\n- " + "\n- ".join(erreurs))
    if bavard:
        print("Paquet valide : « %s » · %s" % (sb["titre"], sb["dossier"]["titre"]))
        print("%d scènes, %d captures, %d agents, %d personnes ; environ %d s de voix (%d mots)."
              % (len(sb["scenes"]), len(caps), len(agents), len(gens), sb.get("duree_cible_s") or 0, mots))
        for n in notes:
            print("Note : " + n)
    return z, sb


def preparer(chemin, projet, node_modules=None):
    z, sb = verifier(chemin)
    motion = os.path.join(projet, "motion")
    if os.path.exists(motion):
        sys.exit("%s existe déjà : ouvrez ce projet ou choisissez un autre dossier (rien n'est écrasé)." % motion)
    for d in ("sources", "work", "out"):
        os.makedirs(os.path.join(projet, d), exist_ok=True)
    shutil.copy(chemin, os.path.join(projet, "sources", os.path.basename(chemin)))
    paquet = os.path.join(projet, "sources", "paquet")
    z.extractall(paquet)
    shutil.copytree(TEMPLATE, motion, ignore=shutil.ignore_patterns("node_modules"))
    public = os.path.join(motion, "public")
    for sous in ("captures", "avatars"):
        if os.path.isdir(os.path.join(paquet, sous)):
            shutil.copytree(os.path.join(paquet, sous), os.path.join(public, sous))
    os.makedirs(os.path.join(public, "brand"), exist_ok=True)
    shutil.copy(os.path.join(paquet, "charte", "logo.png"), os.path.join(public, "brand", "logo.png"))
    json.dump(sb, open(os.path.join(motion, "src", "storyboard.json"), "w"), ensure_ascii=False, indent=1)
    script = {
        "fps": sb["fps"], "width": sb["width"], "height": sb["height"],
        "voice": {"provider": "voicestudio", "endpoint": "http://localhost:3900", "model": "voxcpm2", "profile": "cc1920f7",
                  "language": "fr", "num_step": 20, "guidance_scale": 1.7, "seeds": [300, 301, 302], "pronounce": PRONONCE},
        "scenes": [{"id": s["id"], "chapter": s["chapitre"], "narration": s["voix"]} for s in sb["scenes"]],
    }
    json.dump(script, open(os.path.join(projet, "work", "script.json"), "w"), ensure_ascii=False, indent=1)
    if node_modules:
        os.symlink(os.path.abspath(node_modules), os.path.join(motion, "node_modules"))
    open(os.path.join(projet, "README.md"), "w").write(
        "# %s\n\nVidéo de l'essentiel du dossier « %s » (%s), paquet préparé par %s le %s.\n\n"
        "Source : `sources/%s` (PROMPT.md, storyboard.json, sources.json). Montage : skill `ao-essentiel-motion`.\n"
        % (sb["titre"], sb["dossier"]["titre"], sb["dossier"].get("acheteur") or "", sb["auteur"]["prenom"], sb["prepare_le"][:16].replace("T", " à "), os.path.basename(chemin)))
    print("Projet prêt : %s" % projet)
    print("Voix : work/script.json (VoiceStudio, profil cc1920f7) ; Remotion : motion/ (%s)." % ("node_modules relié" if node_modules else "lancez npm install dans motion/"))


def _sb(projet):
    return json.load(open(os.path.join(projet, "motion", "src", "storyboard.json")))


def estimer(projet):
    sb = _sb(projet)
    voix = {}
    for s in sb["scenes"]:
        mots = s["voix"].split()
        pas = 1 / MOTS_PAR_SECONDE
        voix[s["id"]] = {"file": None, "durationSec": round(len(mots) * pas + 0.3, 2),
                         "words": [{"t": m, "s": round(i * pas, 2), "e": round((i + 0.8) * pas, 2)} for i, m in enumerate(mots)], "cues": []}
    json.dump({"estime": True, "voice": voix}, open(os.path.join(projet, "motion", "src", "audio.json"), "w"), ensure_ascii=False, indent=1)
    print("Maquette : audio.json estimé (%d scènes, %.0f s). Chaque image porte « MAQUETTE » : refaites la voix avant le rendu final."
          % (len(voix), sum(v["durationSec"] for v in voix.values())))


def images(projet):
    sb = _sb(projet)
    audio = json.load(open(os.path.join(projet, "motion", "src", "audio.json")))
    fps, t, lignes = sb["fps"], 0.0, []
    for i, s in enumerate(sb["scenes"]):
        v = audio["voice"][s["id"]]
        lead = sb["leadSec"] if i == 0 else 0.15
        dur = lead + v["durationSec"] + (sb["tailSec"] if i == len(sb["scenes"]) - 1 else sb["gapSec"])
        instants = {round(t + dur * 0.55, 2)}
        for sh in s.get("shots") or []:
            k = sh.get("at")
            if not k:
                continue
            want = toks(k)
            for j, w in enumerate(v["words"]):
                if all(j + n < len(v["words"]) and "".join(toks(v["words"][j + n]["t"])).startswith(x) for n, x in enumerate(want)):
                    instants.add(round(t + lead + w["s"] + 1.4, 2))
                    break
        lignes += ["%s %d" % (s["id"], round(x * fps)) for x in sorted(instants)]
        t += dur
    open(os.path.join(projet, "work", "still_frames.txt"), "w").write("\n".join(lignes) + "\n")
    print("%d images de relecture dans work/still_frames.txt (durée totale %.1f s)." % (len(lignes), t))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("verifier").add_argument("zip")
    q = sp.add_parser("preparer")
    q.add_argument("zip")
    q.add_argument("projet")
    q.add_argument("--node-modules")
    sp.add_parser("estimer").add_argument("projet")
    sp.add_parser("images").add_argument("projet")
    a = p.parse_args()
    if a.cmd == "verifier":
        verifier(a.zip)
    elif a.cmd == "preparer":
        preparer(a.zip, a.projet, a.node_modules)
    elif a.cmd == "estimer":
        estimer(a.projet)
    else:
        images(a.projet)


if __name__ == "__main__":
    main()

