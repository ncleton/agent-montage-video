#!/usr/bin/env python3
"""Le client du prospect en or du studio, prêt pour la demande de feu vert (Nicolas, 27/11/2026).

Usage : data/venv/bin/python seed/seed_gold_client.py
Le prospect en or TECOBAT (seed_gold_prospect.py) vend à notre client Dubois Promotion. Pour que la fiche montre le
chargé d'affaires du client, sa photo, la demande de feu vert puis le numéro du client :
- l'entreprise Dubois Promotion et une personne fictive (téléphone de la plage 06 39 98 réservée à la fiction) sont
  créées dans le portail HubSpot de test, jamais dans celui de Rossini ;
- la ligne du client (table des clients de la recherche des relations) est reliée à cette entreprise et à ce contact ;
- data/studio-owners.json nomme Thibaut Gourlin propriétaire de l'entreprise (lu par studio_platform.py).
Remet aussi à zéro les décisions de feu vert du prospect (relançable avant chaque tournage).
"""
from __future__ import annotations

import json
import os
import sys

import psycopg
from psycopg.types.json import Jsonb

from seed_bigup import guard, WORKSPACE
from seed_hubspot import DATA, ROSSINI_PORTAL, Hub, fail

CLIENT, SUPPLIER_SIREN, OWNER = "Dubois Promotion", "419346796", "studio-thibaut"
PERSON = {"firstname": "Sophie", "lastname": "Lemaire", "jobtitle": "Directrice de programmes",
          "email": "sophie.lemaire@example.fr", "mobilephone": "06 39 98 52 14"}


def main():
    guard()
    hub = Hub((DATA / "hubspot-test-token").read_text().strip())
    account = hub.call("GET", "/account-info/v3/details")
    portal = str(account.get("portalId", ""))
    if not portal or portal == str(ROSSINI_PORTAL) or account.get("accountType") != "DEVELOPER_TEST":
        fail("le jeton ne désigne pas un portail développeur de test.")
    if portal != (DATA / "hubspot-test-portal").read_text().strip():
        fail("le portail ne correspond pas à celui vérifié au démarrage du studio.")
    company = hub.upsert("companies", "name", {"name": CLIENT, "city": "Marcq-en-Barœul", "country": "France",
                                                "domain": "dubois-promotion.fr"})
    contact = hub.upsert("contacts", "email", PERSON)
    hub.call("PUT", f"/crm/v4/objects/contacts/{contact}/associations/default/companies/{company}")
    company_url = f"https://app.hubspot.com/contacts/{portal}/record/0-2/{company}"
    person = {
        "id": "hubspot:" + contact, "origin": "hubspot", "hubspot_id": contact,
        "name": PERSON["firstname"] + " " + PERSON["lastname"], "role": PERSON["jobtitle"],
        "phones": [{"value": PERSON["mobilephone"], "label": "Mobile (HubSpot)"}], "email": PERSON["email"],
        "source_url": f"https://app.hubspot.com/contacts/{portal}/record/0-1/{contact}",
        "source_label": "Fiche contact HubSpot du client",
    }
    with psycopg.connect(host="127.0.0.1", port=55810, dbname="studio", user="postgres",
                         password=(DATA / "pg-password").read_text().strip()) as conn:
        rows = conn.execute(
            "SELECT id, data FROM lead_platform.opportunities WHERE workspace_id=%s AND NOT archived "
            "AND data->'values'->>'c1'=%s AND data ? 'position'", (WORKSPACE, CLIENT)).fetchall()
        if len(rows) != 1:
            fail(f"ligne du client {CLIENT} absente ou en double ({len(rows)}) : lancer seed/seed_gold_prospect.py d'abord.")
        row_id, data = rows[0]
        data["client"] = {"entries": [{"id": "studio:" + company, "url": company_url, "label": "Fiche HubSpot du client"}]}
        data["file"] = {"contacts": [person]}
        conn.execute("UPDATE lead_platform.opportunities SET data=%s WHERE id=%s", (Jsonb(data), row_id))
        gone = conn.execute("DELETE FROM lead_platform.colleague_request_events WHERE workspace_id=%s AND siren=%s",
                            (WORKSPACE, SUPPLIER_SIREN)).rowcount
    owners_file = DATA / "studio-owners.json"
    owners = json.loads(owners_file.read_text()) if owners_file.exists() else {"owners": [], "companies": {}}
    if not any(o["id"] == OWNER for o in owners["owners"]):
        fail("Thibaut Gourlin absent de data/studio-owners.json : lancer seed/seed_team.py d'abord.")
    owners["companies"] = {company: OWNER}
    owners_file.write_text(json.dumps(owners, ensure_ascii=False, indent=1) + "\n")
    os.chmod(owners_file, 0o600)
    print(f"{CLIENT} relié à l'entreprise HubSpot de test {company}, contact fictif {person['name']}, "
          f"propriétaire Thibaut Gourlin ; {gone} décision(s) de feu vert remise(s) à zéro.")


if __name__ == "__main__":
    if len(sys.argv) != 1:
        sys.exit(__doc__)
    main()

