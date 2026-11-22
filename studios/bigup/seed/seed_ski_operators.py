#!/usr/bin/env python3
"""Prépare les deux fiches de ski filmées dans le tableur local."""
from __future__ import annotations

import json
import os
from urllib.parse import quote

import psycopg
from psycopg.types.json import Jsonb
from leadgenerator.platform import contact_photos

from seed_bigup import DATA, WORKSPACE, Fiction, Names, fail, guard

STATIONS = (
    ("Courchevel Le Praz", "429852668", "https://saison.skipasscourchevel.com/fr/cp", "https://www.s3v.com/"),
    ("La Flégère", "605520584", "https://domaineschamonix.montblancnaturalresort.com/fr/page/mentions-legales",
     "https://www.montblancnaturalresort.com/"),
)



def replace_people(conn, campaign, names):
    people = Names(Fiction(2311))
    for name in names:
        people.add(name)
    for table in ("opportunities", "tasks"):
        entries = conn.execute(
            f"SELECT id,data FROM lead_platform.{table} WHERE workspace_id=%s AND campaign_id=%s "
            "AND NOT archived AND data::text ILIKE ANY(%s)",
            (WORKSPACE, campaign, [f"%{name.split()[-1]}%" for name in names]),
        )
        for row_id, data in entries.fetchall():
            cleaned = people.replace(data)
            if people.leaks(cleaned):
                fail("un nom de personne réelle a subsisté dans le tableur du studio.")
            if cleaned != data:
                conn.execute(
                    f"UPDATE lead_platform.{table} SET data=%s,updated_at=now(),revision=revision+1 WHERE workspace_id=%s AND id=%s",
                    (Jsonb(cleaned), WORKSPACE, row_id),
                )


def main():
    guard()
    exclusions = DATA / "stations-noms-a-anonymiser.json"
    if not exclusions.is_file():
        fail(f"renseigner les noms à anonymiser dans {exclusions}, au format liste JSON.")
    names = json.loads(exclusions.read_text())
    if not isinstance(names, list) or not names or not all(isinstance(name, str) and len(name.split()) >= 2 for name in names):
        fail("la liste d’anonymisation doit contenir des noms complets.")
    os.environ["LEADGENERATOR_WORKSPACE_ID"] = WORKSPACE
    runtime = quote((DATA / "runtime-password").read_text().strip(), safe="")
    os.environ["LEADGENERATOR_DATABASE_URL"] = f"postgresql://lead_platform_app:{runtime}@127.0.0.1:55810/studio"
    logos = contact_photos.logo_root(str(DATA / "documents"), WORKSPACE)
    campaigns = set()
    with psycopg.connect(host="127.0.0.1", port=55810, dbname="studio", user="postgres",
                         password=(DATA / "pg-password").read_text().strip()) as conn:
        for name, siren, proof, website in STATIONS:
            rows = conn.execute("""
                UPDATE lead_platform.opportunities
                SET data=jsonb_set(data,'{operator_source_url}',to_jsonb(%s::text)),
                    updated_at=now(),revision=revision+1
                WHERE workspace_id=%s AND NOT archived AND data->>'kind'='ski_station'
                    AND data->>'name'=%s AND data->>'operator_siren'=%s RETURNING id,campaign_id
            """, (proof, WORKSPACE, name, siren)).fetchall()
            if len(rows) != 1:
                fail(f"{name} avec le SIREN {siren} doit être présent une fois dans le tableur de démonstration.")
            row_id, campaign = rows[0]
            campaigns.add(campaign)
            present = contact_photos.read_meta(logos, row_id)
            if not contact_photos.logo_view(present):
                result = contact_photos.fetch_logo(logos, row_id, website, {"website_proof": proof})
                if result not in ("found", "kept"):
                    fail(f"logo officiel de {name} indisponible sur {website} ({result}).")
            print(f"{name} — {siren} — {proof}")
        for campaign in campaigns:
            replace_people(conn, campaign, names)


if __name__ == "__main__":
    main()
