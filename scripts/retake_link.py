"""Lien de relecture Retake d'un rendu publié sur Mux.

Retake en ligne (https://retake.rossini-ener-0158.chatgpt.site, espace Rossini Energy) montre le rendu Mux au
relecteur, qui commente à l'image près puis clique sur « Terminé » : le dossier de la revue part sur le Site, où
scripts/retake_fetch.py le récupère. Ce script déclare la revue au Site et écrit son lien court dans le fichier .mux.json du rendu (clé
« retake »). scripts/publish_mux.py l'appelle à chaque publication.

Configuration : ~/.config/montage-video/retake.json (droits 600), jamais dans le dépôt :
    {"url": "https://retake.rossini-ener-0158.chatgpt.site", "secret": "<RETAKE_SECRET du Site>",
     "sites_token": "<jeton de service du Site, en-tête OAI-Sites-Authorization>"}

Usage :
    python3 scripts/retake_link.py --mux out/<film>.mux.json [--precedente out/<version précédente>.mux.json | rv_…]
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CONFIG = Path(os.environ.get("MONTAGE_SECRETS_DIR", Path.home() / ".config/montage-video")) / "retake.json"
ORDER_ID = re.compile(r"^ord_[0-9a-f]{20}$")


def current_order() -> str | None:
    """La commande de l'ERP en cours (dossier donné par agent_host.py) : Terminé dans Retake lui passera les corrections."""
    folder = os.environ.get("AGENT_HOST_ORDER_DIR")
    order_file = Path(folder) / "order.json" if folder else None
    if not order_file or not order_file.is_file():
        return None
    order_id = str(json.loads(order_file.read_text()).get("id", ""))
    return order_id if ORDER_ID.match(order_id) else None


def load_config() -> dict:
    if not CONFIG.is_file():
        raise SystemExit(f"{CONFIG} manque : il donne l'adresse et le secret de Retake en ligne (voir le skill retake).")
    config = json.loads(CONFIG.read_text())
    for key in ("url", "secret", "sites_token"):
        if not config.get(key):
            raise SystemExit(f"{CONFIG} : la clé « {key} » manque.")
    return config


def site_request(config: dict, path: str, body: dict | None = None) -> bytes:
    """Appel signé au Site : x-retake-agent prouve qu'Oscar parle, OAI-Sites-Authorization passe la connexion ChatGPT."""
    seconds = str(int(time.time()))
    signature = hmac.new(config["secret"].encode(), f"agent:{seconds}".encode(), hashlib.sha256).digest()
    headers = {
        "x-retake-agent": seconds + "." + base64.urlsafe_b64encode(signature).decode().rstrip("="),
        "OAI-Sites-Authorization": "Bearer " + config["sites_token"],
        "Accept": "application/json",
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, ensure_ascii=False).encode()
    request = urllib.request.Request(config["url"].rstrip("/") + path, data=data, headers=headers,
                                     method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        try:
            message = json.loads(exc.read(4096)).get("erreur", "")
        except (ValueError, AttributeError):
            message = ""
        raise RuntimeError(f"Retake en ligne HTTP {exc.code} sur {path}" + (f" : {message}" if message else "")) from None


def probe(video: Path) -> dict:
    ffprobe = shutil.which("ffprobe") or str(Path.home() / ".local/bin/ffprobe")
    out = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate,nb_frames:format=duration", "-of", "json", str(video)],
        check=True, capture_output=True, text=True).stdout
    info = json.loads(out)
    stream, duration = info["streams"][0], float(info["format"]["duration"])
    num, den = (int(x) for x in stream["r_frame_rate"].split("/"))
    fps = round(num / den, 3)
    frames = int(stream.get("nb_frames") or round(duration * fps))
    return {"ips": fps, "images": frames, "largeur": stream["width"], "hauteur": stream["height"], "duree": round(duration, 3)}


def previous_review_id(previous: str | None) -> str | None:
    if not previous:
        return None
    if previous.startswith("rv_"):
        return previous
    meta = json.loads(Path(previous).read_text())
    if not meta.get("retake", {}).get("id"):
        raise SystemExit(f"{previous} n'a pas de revue Retake : donnez l'identifiant rv_… de la revue précédente.")
    return meta["retake"]["id"]


def create_review(mux_json: Path, previous: str | None = None, video: Path | None = None) -> dict:
    """Déclare la revue du rendu publié dans mux_json et y écrit son lien. Garde le lien existant s'il y en a un."""
    meta = json.loads(mux_json.read_text())
    previous_id = previous_review_id(previous)
    existing = meta.get("retake")
    if existing and existing.get("precedente") == previous_id:
        return existing
    source = (video or Path(meta["source_file"])).resolve()
    if not source.is_file():
        raise SystemExit(f"Rendu local introuvable : {source}. Passez le MP4 publié avec --video.")
    config = load_config()
    declared = {
        "v": 1, "id": "rv_" + secrets.token_hex(10), "titre": meta.get("title", source.stem), "fichier": source.name,
        "mux": meta["playback_id"], "sha256": meta["source_sha256"], "octets": source.stat().st_size,
        **probe(source), "prec": previous_id, "cree": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commande": current_order(),
    }
    answer = json.loads(site_request(config, "/api/revues", declared))
    meta["retake"] = {"id": answer["id"], "url": answer["url"], "precedente": previous_id, "cree": declared["cree"]}
    mux_json.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    return meta["retake"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mux", type=Path, required=True, help="fichier .mux.json écrit par publish_mux.py")
    parser.add_argument("--precedente", help=".mux.json de la version précédente, ou identifiant rv_… de sa revue")
    parser.add_argument("--video", type=Path, help="MP4 publié, si source_file du .mux.json n'est pas sur ce poste")
    args = parser.parse_args()
    review = create_review(args.mux.resolve(), args.precedente, args.video)
    print(f"Lien de relecture Retake : {review['url']}")


if __name__ == "__main__":
    main()
