#!/usr/bin/env python3
"""Tableur partagé du studio Bigup : une liste complète de production, partagée en lecture au commercial de démonstration.

Nicolas génère sur demande la liste complète et classée d'un type de prospects (stations de ski, magasins Weldom…) ;
elle apparaît dans le Tableur du commercial, en lecture seule (table_shares.py), et ouvre la fiche de chaque ligne.
Ce semis lit cette liste en production, en lecture seule (par SSH), avec ses colonnes, ses réponses sourcées, ses
parkings et ses logos. Chaque vraie personne devient une personne fictive (mêmes règles et même contrôle de fuite que
seed_bigup.py), nos notes internes sont vidées, puis la liste est écrite dans la base du studio et partagée au
commercial de démonstration. Seule sa propre campagne est remplacée dans le studio.

    data/venv/bin/python seed/seed_shared_table.py [--campaign 34eeb41f-935b-48ad-bdf3-5d7acc3cdd1f] [--seed N]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import uuid
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seed_bigup as sb  # noqa: E402

SKI = "34eeb41f-935b-48ad-bdf3-5d7acc3cdd1f"  # « Stations de ski France · recharge et ombrières »
TASK_KINDS = ("research_cell", "site_parking", "site_land", "aper_exemption", "cell_override")
CONFIG_KINDS = ("campaign_table", "table_column", "table_priority", "table_research_column", "table_view", "table_lookup")


def main() -> None:
    sb.guard()
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", default=SKI, help="campagne de production à partager (par défaut les stations de ski)")
    parser.add_argument("--seed", type=int, default=20261121)
    args = parser.parse_args()
    cid = args.campaign
    q, base = sb.q, "SELECT row_to_json(r) FROM (SELECT * FROM lead_platform.{t} WHERE {w}) r;"
    records: dict[str, list[dict]] = {}
    records["campaigns"] = sb.prod(base.format(t="campaigns", w=f"id={q(cid)} AND NOT archived"))
    if not records["campaigns"]:
        sb.fail(f"campagne {cid} introuvable ou archivée en production.")
    prod_workspace = records["campaigns"][0]["workspace_id"]
    kinds = ",".join(q(k) for k in CONFIG_KINDS)
    records["configurations"] = sb.prod(base.format(t="configurations", w=f"campaign_id={q(cid)} AND NOT archived AND data->>'category' IN ({kinds})"))
    records["opportunities"] = sb.prod(base.format(t="opportunities", w=f"campaign_id={q(cid)} AND NOT archived"))
    tkinds = ",".join(q(k) for k in TASK_KINDS)
    records["tasks"] = sb.prod(base.format(t="tasks", w=f"campaign_id={q(cid)} AND NOT archived AND data->>'kind' IN ({tkinds})"))
    rows = [o["id"] for o in records["opportunities"] if o["data"].get("kind") != "imported_row"]
    sirens = sorted({o["data"].get("operator_siren") for o in records["opportunities"] if o["data"].get("operator_siren")})
    records["companies"] = sb.prod(base.format(t="companies", w=f"siren=ANY({sb.arr(sirens)}) AND NOT archived")) if sirens else []
    name = records["campaigns"][0]["data"].get("name")
    print(f"Production : « {name} », {len(rows)} lignes, {len(records['tasks'])} réponses, {len(records['companies'])} entreprises.")

    # Les vraies personnes deviennent des personnes fictives, partout et toujours les mêmes (règles de seed_bigup.py).
    fiction = sb.Fiction(args.seed)
    labels = {c["id"]: c["data"].get("label") for c in records["configurations"] if c["data"].get("category") == "table_research_column"}
    people = sb.Names(fiction)
    people.protect([r["data"].get(k) for r in records["opportunities"] for k in ("name", "operator_name")]
                   + [(r["data"].get("values") or {}).get("c1") for r in records["opportunities"]]
                   + [(r["data"].get("person") or {}).get("company_legal_name") for r in records["opportunities"]]
                   + [c["data"].get("name") for c in records["companies"]])
    for row in records["opportunities"]:
        data = row["data"]
        info = data.get("person") or {}
        if data.get("kind") == "imported_row":
            people.add(f"{info.get('first_name') or ''} {info.get('last_name') or ''}", info.get("work_email"))
            people.add((data.get("values") or {}).get("c2"))
        elif isinstance(data.get("found_contact"), dict):
            people.add(data["found_contact"].get("name"), data["found_contact"].get("email"))
        # Le contact d'une ligne de liste (contact_name des stations de ski, magasins…).
        if data.get("contact_name"):
            people.add(data["contact_name"], data.get("work_email"))
    for task in records["tasks"]:
        people.collect(task["data"])
        label = labels.get(task["data"].get("column_id"))
        if task["data"].get("kind") == "research_cell" and label in sb.PERSON_COLUMNS and isinstance(task["data"].get("value"), str):
            people.add(task["data"]["value"].split(",")[0])
    for company in records["companies"]:
        people.collect(company["data"])
    # Un lieu n'est pas une personne : une réponse « Les Belleville » d'une colonne de personnes désigne le domaine skiable.
    places = sb.Names.plain(" ".join(str(o["data"].get(k) or "") for o in records["opportunities"] for k in ("name", "operator_name", "address", "commune", "city"))
                            + " " + " ".join(str(v) for o in records["opportunities"] for v in (o["data"].get("values") or {}).values() if isinstance(v, str) and len(v) < 120))
    for key in [k for k in people.map if re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", places)]:
        people.map.pop(key)
        people.surfaces.pop(key, None)
    for task in records["tasks"]:
        data = task["data"]
        if data.get("kind") == "research_cell" and labels.get(data.get("column_id")) in sb.INTERNAL_COLUMNS:
            data.update({"value": None, "detail": None, "contacts": [], "source_url": None})
    for row in records["opportunities"]:
        info = row["data"].get("person") or {}
        real = sb.Names.plain(re.sub(r"\s+", " ", f"{info.get('first_name') or ''} {info.get('last_name') or ''}").strip())
        if real in people.map:
            fake = people.map[real]
            info.update({"first_name": fake["first_name"], "last_name": fake["last_name"]})
            for gone in ("phone", "mobile_phone", "photo"):
                info.pop(gone, None)
            sb.complete_contact(info, fake)
    for items in records.values():
        for item in items:
            item["data"] = people.replace(item["data"])
    # Seconde passe : un nom de famille réel resté seul (« M. Vignon ») prend le nom fictif de sa personne, et une adresse
    # de profil LinkedIn (qui porte le nom de la personne) est ramenée à linkedin.com.
    surnames = {}
    for key, fake in people.map.items():
        for surface in people.surfaces.get(key, {key}):
            last = surface.split(" ", 1)[-1].strip()
            if len(last) >= 4 and sb.Names.plain(last) not in places and sb.Names.plain(last) not in {sb.Names.plain(x) for x in sb.LAST}:
                surnames[last] = fake["last_name"]
    glued_names = {surface.replace(" ", ""): fake["name"].replace(" ", "")
                   for key, fake in people.map.items() for surface in people.surfaces.get(key, {key}) if " " in surface and len(surface) > 8}
    surname_re = re.compile(r"(?<![\w-])(" + "|".join(re.escape(x) for x in sorted(surnames, key=len, reverse=True)) + r")(?![\w-])", re.I) if surnames else None
    profile_re = re.compile("https?://[A-Za-z.]*linkedin\\.com/in/[^\\s\"'<>)\\]]+", re.I)
    lowered = {k.lower(): v for k, v in surnames.items()}
    def tidy(value):
        if isinstance(value, dict):
            return {k: tidy(v) for k, v in value.items()}
        if isinstance(value, list):
            return [tidy(v) for v in value]
        if isinstance(value, str):
            value = profile_re.sub("https://www.linkedin.com/", value)
            for glued, fake_glued in glued_names.items():
                if glued in value:
                    value = value.replace(glued, fake_glued)
            if surname_re:
                value = surname_re.sub(lambda m: lowered.get(m.group(1).lower(), m.group(1)), value)
        return value
    for items in records.values():
        for item in items:
            item["data"] = tidy(item["data"])
    rest = surname_re.findall(json.dumps(records, ensure_ascii=False)) if surname_re else []
    rest += [g for g in glued_names if g in json.dumps(records, ensure_ascii=False)]
    if rest or profile_re.search(json.dumps(records, ensure_ascii=False)):
        sb.fail(f"noms de famille réels ou profils LinkedIn encore présents ({sorted(set(rest))[:5]}) : rien n'est écrit dans le studio.")
    linkedin_profile = re.compile(r"linkedin\.com/in/", re.I)
    for row in records["opportunities"]:
        data = row["data"]
        data.pop("contact_linkedin_url", None)
        if linkedin_profile.search(str(data.get("contact_source_url") or "")):
            data["contact_source_url"] = None
        fakes = {sb.Names.plain(f["name"]) for f in people.map.values()}
        if data.get("contact_name") and sb.Names.plain(data["contact_name"]) not in fakes:
            # Une forme que Names.add ne retient pas (un seul mot, plus de quatre) : la ligne reçoit sa propre personne fictive.
            data["contact_name"] = fiction.person("contact:" + row["id"])["name"]
        if data.get("contact_name") and sb.Names.plain(data["contact_name"]) not in fakes | {sb.Names.plain(fiction.person("contact:" + row["id"])["name"])}:
            sb.fail(f"contact de ligne non remplacé : {data.get('name')!r} : rien n'est écrit dans le studio.")
    leaks = people.leaks(records)
    if leaks:
        sb.fail(f"{len(leaks)} vraies personnes restent après remplacement ({leaks[:6]!r}) : rien n'est écrit dans le studio.")
    print(f"{len(people.map)} personnes réelles remplacées par des personnes fictives, aucune ne reste.")
    for table, items in records.items():
        for item in items:
            item["data"] = sb.scrub(item["data"], prod_workspace, fiction, item["id"])
            item["workspace_id"] = sb.WORKSPACE
            if item.get("owner_id"):
                item["owner_id"] = sb.ADMIN_SUBJECT

    share_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"studio-bigup:table-share:{cid}"))
    password = (sb.DATA / "pg-password").read_text().strip()
    with psycopg.connect(host="127.0.0.1", port=55810, dbname="studio", user="postgres", password=password) as conn:
        if conn.info.host not in ("127.0.0.1", "localhost"):
            sb.fail("la base du studio doit être locale.")
        conn.execute("DELETE FROM lead_platform.row_scores WHERE workspace_id=%s AND campaign_id=%s", (sb.WORKSPACE, cid))
        for table in ("tasks", "opportunities", "configurations"):
            conn.execute(f"DELETE FROM lead_platform.{table} WHERE workspace_id=%s AND campaign_id=%s", (sb.WORKSPACE, cid))
        conn.execute("DELETE FROM lead_platform.campaigns WHERE workspace_id=%s AND id=%s", (sb.WORKSPACE, cid))
        known = {r[0] for r in conn.execute("SELECT siren FROM lead_platform.companies WHERE workspace_id=%s AND NOT archived", (sb.WORKSPACE,))}
        records["companies"] = [c for c in records["companies"] if c.get("siren") not in known]
        def links(table):
            # Les liens vers des enregistrements que le studio n'a pas (contacts, établissements, demandes de production) sont retirés.
            if table not in ("opportunities", "tasks", "configurations"):
                return
            companies = {r[0] for r in conn.execute("SELECT id FROM lead_platform.companies WHERE workspace_id=%s", (sb.WORKSPACE,))}
            for item in records[table]:
                for key in ("contact_id", "establishment_id", "request_id"):
                    if item.get(key):
                        item[key] = None
                if item.get("company_id") and item["company_id"] not in companies:
                    item["company_id"] = None
        for table in ("campaigns", "configurations", "companies", "opportunities", "tasks"):
            links(table)
            generated = {r[0] for r in conn.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='lead_platform' AND table_name=%s AND (is_generated='ALWAYS' OR column_name IN ('created_at','updated_at'))", (table,))}
            for item in records[table]:
                item = {k: v for k, v in item.items() if k not in generated}
                columns = list(item)
                values = [Jsonb(v) if c == "data" else v for c, v in item.items()]
                conn.execute(
                    f"INSERT INTO lead_platform.{table} ({','.join(columns)}) VALUES ({','.join(['%s'] * len(columns))}) "
                    "ON CONFLICT (id) DO UPDATE SET data=EXCLUDED.data, workspace_id=EXCLUDED.workspace_id, owner_id=EXCLUDED.owner_id, archived=false",
                    values)
        conn.execute("INSERT INTO lead_platform.configurations (id,workspace_id,campaign_id,owner_id,revision,data,archived) VALUES (%s,%s,%s,%s,1,%s,false)",
                     (share_id, sb.WORKSPACE, cid, sb.ADMIN_SUBJECT, Jsonb({"emails": [sb.COMMERCIAL_EMAIL], "category": "table_share", "table_id": "main", "updated_by": sb.ADMIN_EMAIL})))

    # Logos des lignes qui en ont un en production, rangés sous l'espace du studio.
    logo_dir = f"{sb.PROD_FILES}/contact-photos/{hashlib.sha256(prod_workspace.encode()).hexdigest()[:20]}/logos"
    local_logos = sb.DATA / "documents" / "contact-photos" / hashlib.sha256(sb.WORKSPACE.encode()).hexdigest()[:20] / "logos"
    (local_logos / "images").mkdir(parents=True, exist_ok=True)
    keys = sorted(set(rows) | {c["id"] for c in records["companies"]})
    listing = subprocess.run(["ssh", sb.PROD, f"cd {logo_dir} && ls"], capture_output=True, text=True, timeout=120).stdout.split()
    present = sorted({f"{k}.json" for k in keys} & set(listing))
    if present:
        metas = subprocess.run(["ssh", sb.PROD, f"cd {logo_dir} && cat " + " ".join(present)], capture_output=True, text=True, timeout=300)
        digests = set(re.findall(r"[0-9a-f]{64}", metas.stdout))
        files = present + [f"images/{d}.png" for d in digests]
        archive = subprocess.run(["ssh", sb.PROD, f"cd {logo_dir} && tar cf - --ignore-failed-read " + " ".join(files) + " 2>/dev/null"], capture_output=True, timeout=600)
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            tar.extractall(local_logos, filter="data")
    print(f"Tableur partagé : « {name} » ({len(rows)} lignes, {len(present)} logos) partagé en lecture à {sb.COMMERCIAL_EMAIL}.")


if __name__ == "__main__":
    main()
