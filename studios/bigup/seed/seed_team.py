#!/usr/bin/env python3
"""Photos Slack et annuaire des propriétaires HubSpot des collègues réels du studio (Nicolas, 27/11/2026).

Usage : data/venv/bin/python seed/seed_team.py
Lit data/team.json (hors Git : noms, e-mails, adresses des photos Slack). Chaque photo est téléchargée puis posée par
le code du serveur des photos de l'ERP (ao/photos.py) dans la plateforme du studio, qui la sert à /ao-api/photos.
Écrit la liste « owners » de data/studio-owners.json, lue par studio_platform.py (annuaire des propriétaires).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

STUDIO = Path(__file__).resolve().parents[1]
DATA = STUDIO / "data"


def fail(message):
    sys.exit("Semis de l'équipe du studio : " + message)


team = json.loads((DATA / "team.json").read_text())["members"]
os.environ.update(
    LEADGENERATOR_WORKSPACE_ID="studio-bigup",
    LEADGENERATOR_DATABASE_URL="postgresql://lead_platform_app:%s@127.0.0.1:55810/studio" % (DATA / "runtime-password").read_text().strip(),
    LEADGENERATOR_AO_DATA=str(DATA / "ao"),
    LEADGENERATOR_DOCUMENT_ROOT=str(DATA / "documents"),
)
from leadgenerator.platform.ao import photos  # noqa: E402  (après l'environnement du studio)

for person in team:
    request = urllib.request.Request(person["photo"], headers={"User-Agent": "studio-bigup"})
    try:
        with urllib.request.urlopen(request, timeout=30) as answer:
            data = answer.read()
    except OSError as error:
        fail("photo Slack de %s illisible (%s) : %s" % (person["first_name"], person["photo"], error))
    extension = {b"\x89PNG": ".png", b"RIFF": ".webp"}.get(data[:4], ".jpg")
    current = photos.index().get(person["email"]) or {}
    if current.get("origine") == person["photo"] and current.get("fichier") and (photos.config.AGENTS / current["fichier"]).is_file():
        print("Photo déjà posée :", person["first_name"], person["last_name"])
        continue
    path = photos.chemin_neuf(person["email"], extension)
    path.write_bytes(data)
    photos.enregistrer(person["email"], path, photos.SLACK, "studio.admin@rossinienergy.com", person["photo"])
    print("Photo Slack posée :", person["first_name"], person["last_name"])

owners_file = DATA / "studio-owners.json"
owners = json.loads(owners_file.read_text()) if owners_file.exists() else {"owners": [], "companies": {}}
owners["owners"] = [
    {"id": person["sub"], "email": person["email"], "first_name": person["first_name"], "last_name": person["last_name"]}
    for person in team
]
owners_file.write_text(json.dumps(owners, ensure_ascii=False, indent=1) + "\n")
os.chmod(owners_file, 0o600)
print("Annuaire des propriétaires du studio :", ", ".join(o["first_name"] + " " + o["last_name"] for o in owners["owners"]))

# L'annuaire de l'équipe (ao_personnes) donne leur nom complet, accents compris, partout dans Bigup (Transférer,
# feu vert) : sans lui, la fenêtre Transférer affiche le début de l'e-mail (« Amouric »).
import psycopg  # noqa: E402

with psycopg.connect(host="127.0.0.1", port=55810, dbname="studio", user="postgres",
                     password=(DATA / "pg-password").read_text().strip()) as conn:
    for person in team:
        conn.execute(
            "INSERT INTO lead_platform.ao_personnes (workspace_id,id,nom,email,fonction,actif,source,maj_par,maj_le) "
            "VALUES ('studio-bigup',%s,%s,%s,%s,1,'studio','studio.admin@rossinienergy.com',now()::text) "
            "ON CONFLICT (workspace_id,id) DO UPDATE SET nom=excluded.nom,email=excluded.email,fonction=excluded.fonction,actif=1",
            (person["sub"], person["first_name"] + " " + person["last_name"], person["email"], person.get("fonction", "")),
        )
print("Annuaire de l'équipe du studio :", len(team), "collègues.")

