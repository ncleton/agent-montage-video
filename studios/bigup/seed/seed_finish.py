#!/usr/bin/env python3
"""Dernière étape du semis du studio Bigup : la case Prospects montre toujours 25 prospects, dont au moins 4 ajoutés à la main.

1. Configuration des documents communs : le Drive partagé « Bigup · Documents communs » (servi par drive_double.py).
2. Accueil ouvert comme Camille : Bigup note les entreprises dans le navigateur, comme en production.
3. Jusqu'à 21 entreprises vertes gardées (les meilleures notes), les autres sortent du studio ; des entreprises non
   vertes complètent à 25 comme ajouts manuels de Camille (« Ajouté par moi »), 4 au moins.
4. Accueil rouvert : il doit montrer 25 prospects, sinon le semis échoue avec l'écart.

    data/venv/bin/python seed/seed_finish.py
"""
import json
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

STUDIO = Path(__file__).resolve().parent.parent
DATA = STUDIO / "data"
WS, COMMERCIAL = "studio-bigup", "camille.martin@rossinienergy.com"
TOTAL, GREEN_MAX, MANUAL_MIN = 25, 21, 4
DRIVE_ID, DRIVE_NAME = json.load(open(DATA / "drive-snapshot.json"))["drive_id"], "Bigup · Documents communs"


def fail(message):
    sys.exit("Semis du studio Bigup : " + message)


def open_home(expected=None):
    out = DATA / "open-home.json"
    done = subprocess.run(["node", str(STUDIO / "seed" / "open_home.mjs"), str(out)] + ([str(expected)] if expected else []), capture_output=True, text=True, timeout=300)
    if done.returncode:
        fail("accueil illisible : " + (done.stderr or done.stdout)[-600:])
    print(done.stdout.strip())
    return json.loads(out.read_text())


def main():
    password = (DATA / "pg-password").read_text().strip()
    conn = psycopg.connect(host="127.0.0.1", port=55810, dbname="studio", user="postgres", password=password, autocommit=True)
    current = conn.execute("SELECT id FROM lead_platform.configurations WHERE workspace_id=%s AND NOT archived AND data->>'category'='sales_documents'", (WS,)).fetchone()
    body = Jsonb({"category": "sales_documents", "drive_id": DRIVE_ID, "name": DRIVE_NAME, "organizer": "studio.admin@rossinienergy.com", "updated_by": "studio.admin@rossinienergy.com"})
    if current:
        conn.execute("UPDATE lead_platform.configurations SET data=%s WHERE id=%s", (body, current[0]))
    else:
        conn.execute("INSERT INTO lead_platform.configurations (id,workspace_id,owner_id,revision,data,archived) VALUES (%s,%s,'studio-admin',1,%s,false)", (str(uuid.uuid4()), WS, body))

    book = conn.execute("SELECT selection_id FROM lead_platform.monthly_books WHERE workspace_id=%s AND owner_email=%s", (WS, COMMERCIAL)).fetchone()
    if not book:
        fail("aucun livret du mois pour Camille : lancer d'abord seed/seed_bigup.py.")
    sel_id = book[0]
    before = conn.execute("SELECT revision FROM lead_platform.selections WHERE id=%s", (sel_id,)).fetchone()[0]
    first = open_home()
    data, after = conn.execute("SELECT data, revision FROM lead_platform.selections WHERE id=%s", (sel_id,)).fetchone()
    sites = conn.execute("SELECT count(*) FROM lead_platform.opportunities WHERE workspace_id=%s AND data->>'kind'='site' AND NOT archived", (WS,)).fetchone()[0]
    # Bigup a déjà recalculé le livret si sa liste n'est plus celle du semis (toutes les entreprises).
    synced = after != before or len(data.get("row_ids") or []) < sites
    rule = data.get("rule") or {}
    # Notes calculées par Bigup dans le navigateur, telles que la case les affiche (verte à partir de 60).
    shown_rows = [r for r in first.get("rows") or [] if r.get("id")]
    scores = {r["id"]: {"score": r["score"], "technical": True} for r in shown_rows}
    forced_ids = {f.get("row_id") for f in rule.get("forced") or []}
    if synced:
        # La liste verte que Bigup vient d'enregistrer en recalculant le livret : elle fait foi.
        green = [r for r in data.get("row_ids") or [] if r not in forced_ids]
    else:
        green = [r["id"] for r in sorted(shown_rows, key=lambda r: -r["score"]) if r["score"] >= 60 and r["id"] not in forced_ids]
    kept, extra = green[:GREEN_MAX], green[GREEN_MAX:]
    manual_count = TOTAL - len(kept)
    if manual_count > TOTAL - 15:
        fail(f"{len(kept)} entreprises vertes seulement : relancer seed/seed_bigup.py avec un --count plus grand.")
    rows = {r[0]: r for r in conn.execute("SELECT id, data->>'name', data->>'operator_siren' FROM lead_platform.opportunities WHERE workspace_id=%s AND data->>'kind'='site' AND NOT archived", (WS,)).fetchall()}
    others = [i for i in rows if i not in green]
    # Ajouts manuels : des entreprises non vertes dont le responsable technique est nommé, les mieux notées d'abord.
    others.sort(key=lambda i: (not (scores.get(i) or {}).get("technical"), -((scores.get(i) or {}).get("score") or 0)))
    if len(others) < manual_count:
        fail(f"{len(others)} entreprises non vertes pour {manual_count} ajouts manuels.")
    manual = others[:manual_count]
    if extra:
        conn.execute("UPDATE lead_platform.opportunities SET archived=true WHERE workspace_id=%s AND id=ANY(%s)", (WS, extra))
    now = datetime.now(timezone.utc)
    rule["forced"] = [{"at": (now - timedelta(days=3 - k)).isoformat(timespec="seconds"), "by": COMMERCIAL, "name": rows[i][1], "siren": rows[i][2], "row_id": i}
                      for k, i in enumerate(manual)]
    rule.setdefault("entered", {}).update({f["row_id"]: f["at"] for f in rule["forced"]})
    data.update({"rule": rule, "row_ids": manual + kept})
    conn.execute("UPDATE lead_platform.selections SET data=%s, revision=revision+1 WHERE id=%s", (Jsonb(data), sel_id))
    second = open_home(TOTAL)
    shown = (second.get("shown") or "").strip()
    if shown != str(TOTAL):
        fail(f"l'accueil montre {shown or 'aucun'} prospects au lieu de {TOTAL} : voir data/open-home.json.")
    print(f"Case Prospects : {shown} prospects, dont {len(manual)} ajoutés par Camille ; documents communs : {DRIVE_NAME}.")


if __name__ == "__main__":
    main()

