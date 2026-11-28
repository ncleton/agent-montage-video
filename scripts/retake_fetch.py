"""Récupère le dossier d'une revue terminée dans Retake en ligne.

Quand le relecteur clique sur « Terminé », le dossier de sa revue (rapport.md, rapport.json, rapport.html, images
annotées et brutes, commentaires vocaux WAV) part sur le Site. Ce script le télécharge, avec la même configuration
que scripts/retake_link.py, puis il se traite avec ingest_review.py du skill retake.

Usage :
    python3 scripts/retake_fetch.py out/<film>.mux.json        # la revue du rendu (ou son identifiant rv_…)
    python3 scripts/retake_fetch.py rv_… --attendre 60         # attendre jusqu'à 60 minutes que la revue soit terminée
    python3 scripts/retake_fetch.py --liste                    # les revues terminées, les plus récentes d'abord
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from retake_link import load_config, site_request  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
POLL_SECONDS = 30


def review_id(target: str) -> str:
    if target.startswith("rv_"):
        return target
    meta = json.loads(Path(target).read_text())
    if not meta.get("retake", {}).get("id"):
        raise SystemExit(f"{target} n'a pas de lien Retake : lancez d'abord scripts/retake_link.py --mux {target}.")
    return meta["retake"]["id"]


def finished_review(config: dict, rid: str, wait_minutes: float) -> dict:
    deadline = time.monotonic() + wait_minutes * 60
    while True:
        try:
            return json.loads(site_request(config, f"/api/revues/{rid}/termine"))
        except RuntimeError as exc:
            if "HTTP 404" not in str(exc) or time.monotonic() >= deadline:
                raise SystemExit(f"{exc}" + ("" if "HTTP 404" not in str(exc) else " (le relecteur n'a pas encore cliqué sur Terminé)"))
        time.sleep(POLL_SECONDS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("revue", nargs="?", help="fichier .mux.json du rendu relu, ou identifiant rv_… de la revue")
    parser.add_argument("--attendre", type=float, default=0, help="minutes d'attente si la revue n'est pas terminée")
    parser.add_argument("--dossier", type=Path, default=ROOT / "output/retake", help="où écrire le dossier de la revue")
    parser.add_argument("--liste", action="store_true", help="lister les revues terminées")
    args = parser.parse_args()
    config = load_config()

    if args.liste:
        for item in json.loads(site_request(config, "/api/revues"))["revues"]:
            print(f"{item['id']}  {item.get('termineLe', '')}  {item.get('relecteur', '')}  "
                  f"{item.get('commentaires', '?')} commentaire(s)  {item.get('titre', '')}")
        return
    if not args.revue:
        parser.error("indiquez le .mux.json du rendu ou l'identifiant rv_… de la revue, ou --liste")

    rid = review_id(args.revue)
    finished = finished_review(config, rid, args.attendre)
    folder = args.dossier / finished["dossier"]
    base = f"/api/revues/{rid}/envois/{finished['envoi']}/fichiers/"
    for item in finished["fichiers"]:
        target = folder / item["chemin"]
        target.parent.mkdir(parents=True, exist_ok=True)
        data = site_request(config, base + item["chemin"])
        if len(data) != item["octets"]:
            raise SystemExit(f"{item['chemin']} incomplet ({len(data)} octets au lieu de {item['octets']}) : relancez.")
        target.write_bytes(data)
    print(f"Revue de {finished.get('relecteur') or 'relecteur inconnu'}, terminée le {finished['termineLe']} : "
          f"{finished['commentaires']} commentaire(s), {len(finished['fichiers'])} fichier(s).")
    print(f"Dossier : {folder}")
    print("Suite : .venv/bin/python plugins/agent-montage-video/skills/retake/scripts/ingest_review.py "
          f"\"{folder}\" --vocabulaire \"<noms propres du projet>\"")


if __name__ == "__main__":
    main()
