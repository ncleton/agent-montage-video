#!/usr/bin/env python3
"""Relie une fiche du studio à une entreprise du portail HubSpot de test.

Usage : data/venv/bin/python seed/seed_book_hubspot.py <id de ligne du livret local>
Le rapprochement par SIRET est lu par la fiche comme dans Qualité HubSpot.
"""
from __future__ import annotations

import re
import sys
import uuid

import psycopg
from psycopg.types.json import Jsonb

from seed_bigup import guard, WORKSPACE
from seed_hubspot import DATA, OWNER, ROSSINI_PORTAL, Hub, fail


def main(row_id):
    guard()
    hub = Hub((DATA / "hubspot-test-token").read_text().strip())
    account = hub.call("GET", "/account-info/v3/details")
    portal = str(account.get("portalId", ""))
    if not portal or portal == str(ROSSINI_PORTAL) or account.get("accountType") != "DEVELOPER_TEST":
        fail("le jeton ne désigne pas un portail développeur de test.")
    if portal != (DATA / "hubspot-test-portal").read_text().strip():
        fail("le portail ne correspond pas à celui vérifié au démarrage du studio.")

    with psycopg.connect(host="127.0.0.1", port=55810, dbname="studio", user="postgres",
                         password=(DATA / "pg-password").read_text().strip()) as conn:
        site = conn.execute("""
            SELECT o.data->>'name',o.data->>'address',o.data->>'commune',t.data->>'value',t.data->>'source_url'
            FROM lead_platform.opportunities o
            JOIN lead_platform.tasks t ON t.campaign_id=o.campaign_id AND t.data->>'row_id'=o.id::text
            JOIN lead_platform.configurations k ON k.id::text=t.data->>'column_id'
            WHERE o.workspace_id=%s AND o.id=%s AND NOT o.archived AND NOT t.archived
              AND k.data->>'label'='SIRET' AND t.data->>'state'='done'
        """, (WORKSPACE, row_id)).fetchall()
        if len(site) != 1:
            fail("la fiche locale doit avoir un SIRET sourcé et unique.")
        name, address, city, siret, source = site[0]
        siret = re.sub(r"\D", "", siret or "")
        if len(siret) != 14 or not source:
            fail("le SIRET sourcé de la fiche est incomplet.")
        owners = hub.call("GET", "/crm/v3/owners", params={"email": OWNER["email"]}).get("results") or []
        if len(owners) != 1:
            fail("le propriétaire fictif n’est pas configuré dans le portail de test.")
        props = {"name": name, "address": address, "city": city, "country": "France",
                 "hubspot_owner_id": owners[0]["id"], "hs_lead_status": "OPEN"}
        company_id = hub.upsert("companies", "name", props)
        contact = conn.execute("""
            SELECT data->'person'->>'first_name',data->'person'->>'last_name',data->'person'->>'work_email'
            FROM lead_platform.opportunities
            WHERE workspace_id=%s AND NOT archived AND data->'source_row_ids' ? %s
              AND right(data->'person'->>'work_email', 11)='@example.fr'
            ORDER BY id LIMIT 1
        """, (WORKSPACE, row_id)).fetchone()
        if contact:
            first, last, email = contact
            contact_id = hub.upsert("contacts", "email", {
                "firstname": first, "lastname": last, "email": email, "hubspot_owner_id": owners[0]["id"],
            })
            hub.associate("contacts", contact_id, "companies", company_id)
        returned = hub.call("GET", f"/crm/v3/objects/companies/{company_id}", params={"properties": ",".join(props)})
        conn.execute("""
            INSERT INTO lead_platform.crm_records
              (workspace_id,object,hubspot_id,properties,removed,status,match,siren,siret,matched_at)
            VALUES (%s,'companies',%s,%s,false,'chosen',%s,%s,%s,now())
            ON CONFLICT (workspace_id,object,hubspot_id) DO UPDATE
              SET properties=excluded.properties,removed=false,status='chosen',match=excluded.match,
                  siren=excluded.siren,siret=excluded.siret,matched_at=now(),updated_at=now()
        """, (WORKSPACE, company_id, Jsonb(returned["properties"]),
              Jsonb({"method": "siret", "source_url": source}), siret[:9], siret))
    print(f"{name} rapprochée par le SIRET {siret} dans le portail HubSpot de test {portal}.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        fail("indiquez l’identifiant de la ligne du livret du studio.")
    main(str(uuid.UUID(sys.argv[1])))
