#!/usr/bin/env python3
"""Ajoute au studio une fiche de fournisseur et la preuve publique qui la rend « en or ».

Usage : data/venv/bin/python seed/seed_gold_prospect.py <id de ligne d'un livret>
Le prospect doit avoir un logo et une relation fournisseur qualifiée dans Bigup.
"""
from __future__ import annotations

import hashlib
import io
import re
import subprocess
import tarfile
import uuid
from datetime import datetime, timezone

import psycopg
from psycopg.types.json import Jsonb
from leadgenerator.platform.relations_search import quality_reason

from seed_bigup import (
    ADMIN_EMAIL, ADMIN_SUBJECT, COMMERCIAL_EMAIL, DATA, INTERNAL_COLUMNS,
    PERSON_COLUMNS, PROD, PROD_FILES, WORKSPACE, Fiction, Names, fail, guard, prod, q, scrub,
)


def get_records(table, where):
    return prod(f"SELECT row_to_json(r) FROM (SELECT * FROM lead_platform.{table} WHERE {where}) r;")


def copy_logo(workspace, logo_id):
    workspace_hash = hashlib.sha256(workspace.encode()).hexdigest()[:20]
    source = f"{PROD_FILES}/contact-photos/{workspace_hash}/logos"
    meta_file = f"{logo_id}.json"
    meta = subprocess.check_output(["ssh", PROD, f"cat {source}/{meta_file}"], text=True, timeout=30)
    digests = re.findall(r'"([0-9a-f]{64})"', meta)
    images = [f"images/{digest}.png" for digest in set(digests)]
    if not images:
        fail(f"logo sans image pour {logo_id}")
    archive = subprocess.check_output(["ssh", PROD, f"cd {source} && tar cf - {meta_file} " + " ".join(images)], timeout=45)
    local_hash = hashlib.sha256(WORKSPACE.encode()).hexdigest()[:20]
    target = DATA / "documents" / "contact-photos" / local_hash / "logos"
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(target, filter="data")


def replace_private_data(records, workspace, row_id, labels, company):
    fiction = Fiction(int(uuid.UUID(row_id)) % 1_000_000)
    people = Names(fiction)
    people.protect([company, *(r["data"].get("operator_name") for r in records["opportunities"])])
    for row in records["opportunities"]:
        data = row["data"]
        info = data.get("person") or {}
        if data.get("kind") == "imported_row":
            people.add(f"{info.get('first_name') or ''} {info.get('last_name') or ''}", info.get("work_email"))
            people.add((data.get("values") or {}).get("c2"))
        elif isinstance(data.get("found_contact"), dict):
            people.add(data["found_contact"].get("name"), data["found_contact"].get("email"))
    for task in records["tasks"]:
        data = task["data"]
        label = labels.get(data.get("column_id"))
        people.collect(data)
        if label in PERSON_COLUMNS and isinstance(data.get("value"), str):
            people.add(data["value"].split(",")[0])
        if label in INTERNAL_COLUMNS:
            data.update(value=None, detail=None, contacts=[], source_url=None)
    def strip_search_history(data):
        if isinstance(data, dict):
            if data.get("first_name") or data.get("name"):
                for key in ("searched_fields", "auto_technical", "auto_email", "enrichment_status",
                            "enrichment_provider", "enrichment_observed_at", "coordinate_manual"):
                    data.pop(key, None)
            for value in data.values():
                strip_search_history(value)
        elif isinstance(data, list):
            for value in data:
                strip_search_history(value)

    for items in records.values():
        for item in items:
            clean = scrub(people.replace(item["data"]), workspace, fiction, item["id"])
            strip_search_history(clean)
            item["data"] = clean
            item["workspace_id"] = WORKSPACE
            item["owner_id"] = ADMIN_SUBJECT
    if people.map and people.leaks(records):
        fail("des noms réels subsistent dans la fiche fournisseur. Corriger le semis avant tournage.")
    return len(people.map)


def store_record(conn, table, record):
    columns = list(record)
    values = [Jsonb(record[c]) if c == "data" else record[c] for c in columns]
    conn.execute(
        f"INSERT INTO lead_platform.{table} ({','.join(columns)}) VALUES ({','.join(['%s'] * len(columns))}) "
        "ON CONFLICT(id) DO UPDATE SET data=excluded.data, archived=false",
        values,
    )


def seed(row_id, relation_campaign, relation_config, company, siren):
    candidates = get_records("opportunities", f"id={q(row_id)} AND NOT archived AND data->>'kind'='site'")
    if len(candidates) != 1:
        fail(f"site introuvable pour la ligne source {row_id}")
    site = candidates[0]
    workspace, source_campaign = site["workspace_id"], site["campaign_id"]
    source_configs = get_records("configurations", f"campaign_id={q(source_campaign)} AND NOT archived")
    labels = {r["id"]: r["data"].get("label") for r in source_configs if r["data"].get("category") == "table_research_column"}
    people_tables = {r["id"] for r in source_configs if r["data"].get("category") == "campaign_table"}
    source_people = [config["data"] for config in source_configs if config["id"] in people_tables]
    search_rows = [
        row
        for config in source_people
        for row in (config.get("people_search") or {}).get("rows", [])
        if row.get("row_id") == row_id
    ]
    if len(search_rows) != 1:
        fail(f"rattachement à la recherche de contacts absent ou ambigu pour {company}")
    records = {
        "source_search": [{"id": row_id, "data": search_rows[0]}],
        "opportunities": [site] + get_records(
            "opportunities", f"campaign_id={q(source_campaign)} AND NOT archived AND data->>'kind'='imported_row' AND data->'source_row_ids' ? {q(row_id)}"
        ),
        "tasks": get_records("tasks", f"campaign_id={q(source_campaign)} AND NOT archived AND data->>'row_id'={q(row_id)} "
                            "AND data->>'kind' IN ('research_cell','site_parking','site_land','aper_exemption')"),
    }
    for item in records["opportunities"][1:]:
        item["data"]["source_row_ids"] = [row_id]
        if item["data"].get("person", {}).get("principal_for"):
            item["data"]["person"]["principal_for"] = [row_id]

    relation_rows = prod(f"""SELECT row_to_json(r) FROM (
      SELECT o.data FROM lead_platform.opportunities o
      JOIN lead_platform.configurations c ON c.campaign_id=o.campaign_id AND c.id::text=o.data->>'table_id'
      WHERE o.workspace_id={q(workspace)} AND NOT o.archived AND NOT c.archived AND c.data ? 'relations_search'
        AND o.data->'values'->>'c10'={q(siren)} AND o.data->'relation'->>'nature'='fournisseur'
      ORDER BY o.updated_at DESC) r;""")
    relation = next((r["data"] for r in relation_rows if quality_reason(r["data"]) is None), None)
    if relation is None:
        fail(f"aucune preuve qualifiée de relation fournisseur pour le SIREN {siren}")
    public_values = {key: relation["values"][key] for key in ("c1", "c2", "c4", "c5", "c6", "c10")}
    public_relation = {key: relation["relation"][key] for key in ("nature", "level")}
    public_relation.update(
        interest={"value": "introduction"},
        registry={"category": relation["relation"]["registry"]["category"]},
        client_row_id=str(uuid.uuid5(uuid.NAMESPACE_URL, "studio-bigup:client:" + public_values["c1"])),
    )
    data = {"kind": "imported_row", "table_id": relation_config, "values": public_values, "relation": public_relation}
    people_count = replace_private_data(records, workspace, row_id, labels, company)

    source_search = records.pop("source_search")[0]["data"]
    copy_logo(workspace, row_id)
    with psycopg.connect(host="127.0.0.1", port=55810, dbname="studio", user="postgres",
                         password=(DATA / "pg-password").read_text().strip()) as conn:
        book = conn.execute(
            "SELECT b.campaign_id,b.selection_id,s.data FROM lead_platform.monthly_books b "
            "JOIN lead_platform.selections s ON s.id=b.selection_id WHERE b.workspace_id=%s AND b.owner_email=%s "
            "ORDER BY b.month DESC LIMIT 1 FOR UPDATE OF s", (WORKSPACE, COMMERCIAL_EMAIL),
        ).fetchone()
        if not book:
            fail("livret du mois du commercial absent. Lancer le semis Bigup.")
        campaign, selection_id, selection = book
        target = conn.execute(
            "SELECT id,data FROM lead_platform.configurations WHERE workspace_id=%s AND campaign_id=%s AND NOT archived",
            (WORKSPACE, campaign),
        ).fetchall()
        columns = {c["label"]: cid for cid, c in target if c.get("category") == "table_research_column"}
        people_table = next(((cid, config) for cid, config in target if config.get("category") == "campaign_table" and config.get("people_search")), None)
        if not people_table:
            fail("table d’interlocuteurs absente du livret local.")
        target_people, table_data = people_table
        people_search = table_data["people_search"]
        people_search["rows"] = [r for r in people_search["rows"] if r.get("row_id") != row_id] + [source_search]
        conn.execute(
            "UPDATE lead_platform.configurations SET data=%s,revision=revision+1 WHERE workspace_id=%s AND id=%s",
            (Jsonb(table_data), WORKSPACE, target_people),
        )
        for table, rows in records.items():
            for record in rows:
                record["campaign_id"] = campaign
                body = record["data"]
                if table == "opportunities":
                    for field in ("table_id", "person_table_id"):
                        if body.get(field) in people_tables:
                            body[field] = target_people
                if body.get("kind") == "research_cell":
                    column = columns.get(labels.get(body.get("column_id")))
                    if not column:
                        continue
                    body["column_id"] = column
                store_record(conn, table, record)

        common = {"workspace_id": WORKSPACE, "owner_id": ADMIN_SUBJECT, "archived": False}
        store_record(conn, "campaigns", common | {
            "id": relation_campaign, "data": {"name": "Relations de nos clients", "status": "active"},
        })
        # Depuis le 26/11/2026 (sales-marketplace 231f1add), la lecture d'une fiche lit la table des clients de la
        # recherche des relations (relations_search.clients_table_id) : sans elle, « Chargés d'affaires indisponibles ».
        clients_config = str(uuid.uuid5(uuid.NAMESPACE_URL, "studio-bigup:relations:clients"))
        store_record(conn, "configurations", common | {
            "id": clients_config, "campaign_id": relation_campaign,
            "data": {"category": "campaign_table", "name": "Clients", "relations_clients": {"relations_table_id": relation_config}},
        })
        store_record(conn, "configurations", common | {
            "id": relation_config, "campaign_id": relation_campaign,
            "data": {"category": "campaign_table", "name": "Relations",
                     "relations_search": {"status": "done", "clients_table_id": clients_config}},
        })
        # Le client qui présente le fournisseur : sa ligne dans la table des clients (nom de l'entreprise cliente tiré
        # de la preuve publique de la relation, c5), sans aucune personne.
        client_name = relation["values"]["c1"].split(" Romances ")[0] if "linkedin.com/company/" in public_values["c5"] else relation["values"]["c1"]
        store_record(conn, "opportunities", common | {
            "id": public_relation["client_row_id"], "campaign_id": relation_campaign,
            "data": {"kind": "imported_row", "table_id": clients_config, "position": 0, "values": {"c1": client_name}},
        })
        store_record(conn, "opportunities", common | {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "studio-bigup:relation:" + siren)),
            "campaign_id": relation_campaign, "data": data,
        })
        rule = selection.setdefault("rule", {})
        forced = rule.setdefault("forced", [])
        if not any(entry.get("row_id") == row_id for entry in forced):
            ids = selection["row_ids"]
            if row_id not in ids and len(ids) >= 25:
                forced_ids = {entry["row_id"] for entry in forced}
                replaced = next((candidate for candidate in reversed(ids) if candidate not in forced_ids), None)
                if not replaced:
                    fail("aucun prospect automatique à remplacer dans le livret.")
                ids.remove(replaced)
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            forced.append({"row_id": row_id, "name": company, "siren": siren, "at": now, "by": COMMERCIAL_EMAIL})
            if row_id not in ids:
                ids.append(row_id)
            rule.setdefault("entered", {})[row_id] = now
            conn.execute(
                "UPDATE lead_platform.selections SET data=%s,revision=revision+1 WHERE workspace_id=%s AND id=%s",
                (Jsonb(selection), WORKSPACE, selection_id),
            )
    print(f"{company} ajouté au studio, {people_count} personnes remplacées. Preuve : {public_values['c5']}")


if __name__ == "__main__":
    import sys
    guard()
    if len(sys.argv) != 2:
        fail("indiquez l’identifiant de la ligne fournisseur source")
    row_id = str(uuid.UUID(sys.argv[1]))
    row = get_records("opportunities", f"id={q(row_id)} AND NOT archived AND data->>'kind'='site'")
    if not row or not row[0]["data"].get("operator_siren"):
        fail("la ligne doit désigner un site actif et contenir un SIREN")
    relation_campaign = str(uuid.uuid5(uuid.NAMESPACE_URL, "studio-bigup:relations:campaign"))
    relation_config = str(uuid.uuid5(uuid.NAMESPACE_URL, "studio-bigup:relations:table"))
    seed(row_id, relation_campaign, relation_config, row[0]["data"]["name"], row[0]["data"]["operator_siren"])
