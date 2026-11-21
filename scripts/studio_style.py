#!/usr/bin/env python3
"""Prépare l'habillage d'un style pour le kit tuto-interface.

    python3 scripts/studio_style.py <style> <dossier motion du projet>

Lit styles/<style>/kit.json, vérifie ses champs, copie ses images dans <motion>/public/style/ et écrit
<motion>/look.json, à reprendre dans props.json sous la clé "look". Échoue avec ce qui manque.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ("name", "frame", "background", "window", "ink", "muted", "accent", "dialog", "label", "closingLabel")


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    style, motion = sys.argv[1], Path(sys.argv[2])
    folder = ROOT / "styles" / style
    kit = folder / "kit.json"
    if not kit.exists():
        known = sorted(p.name for p in (ROOT / "styles").iterdir() if (p / "kit.json").exists())
        sys.exit(f"Style « {style} » sans habillage : créer {kit} (styles/README.md). Styles prêts : {', '.join(known)}.")
    look = json.loads(kit.read_text())
    missing = [k for k in REQUIRED if k not in look]
    if missing or look["frame"] not in ("rounded", "pixel") or look["name"] != style:
        sys.exit(f"{kit} : champs manquants ou invalides : {', '.join(missing) or 'frame ou name'}.")
    if look["frame"] == "pixel" and "bezel" not in look:
        sys.exit(f"{kit} : un cadre pixel demande « bezel ».")
    target = motion / "public" / "style"
    target.mkdir(parents=True, exist_ok=True)
    for key in ("intro", "introBubble", "outro", "outroBubble"):
        name = (look.get("portraits") or {}).get(key)
        if not name:
            continue
        source = folder / look.get("assets", "assets") / name
        if not source.exists():
            sys.exit(f"{kit} : image {key} absente ({source}).")
        shutil.copy2(source, target / name)
    look.pop("assets", None)
    (motion / "look.json").write_text(json.dumps(look, ensure_ascii=False, indent=2))
    print(f"Style {style} prêt : {motion / 'look.json'}")


if __name__ == "__main__":
    main()

