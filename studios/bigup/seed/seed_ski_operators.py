#!/usr/bin/env python3
"""Attache les preuves des exploitants des deux stations filmées au tableur local."""
from __future__ import annotations

import psycopg

from seed_bigup import DATA, WORKSPACE, fail, guard

STATIONS = (
    ("Courchevel Le Praz", "429852668", "https://saison.skipasscourchevel.com/fr/cp"),
    ("La Flégère", "605520584", "https://domaineschamonix.montblancnaturalresort.com/fr/page/mentions-legales"),
)


def main():
    guard()
    with psycopg.connect(host="127.0.0.1", port=55810, dbname="studio", user="postgres",
                         password=(DATA / "pg-password").read_text().strip()) as conn:
        for name, siren, proof in STATIONS:
            rows = conn.execute("""
                UPDATE lead_platform.opportunities
                SET data=jsonb_set(data,'{operator_source_url}',to_jsonb(%s::text)),
                    updated_at=now(),revision=revision+1
                WHERE workspace_id=%s AND NOT archived AND data->>'kind'='ski_station'
                    AND data->>'name'=%s AND data->>'operator_siren'=%s RETURNING id
            """, (proof, WORKSPACE, name, siren)).fetchall()
            if len(rows) != 1:
                fail(f"{name} avec le SIREN {siren} doit être présent une fois dans le tableur de démonstration.")
    for name, siren, proof in STATIONS:
        print(f"{name} — {siren} — {proof}")


if __name__ == "__main__":
    main()
