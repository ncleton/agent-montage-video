#!/usr/bin/env python3
"""Filtres « Leads entrants », « Projets » et « Partenaires » d'À caler (Tournées), dans le portail HubSpot de test du studio.

En production, À caler montre aussi les transactions au stade « Lead entrant » ou « Projet » et les entreprises au
statut de lead « Partenaire » du secteur (tour_sector.leads_cache). Le portail de test n'avait ni l'étape
« Lead entrant », ni l'option « Partenaire », ni code postal sur ses entreprises : ces filtres n'apparaissaient pas.
Ce semis, relançable sans doublon (commande ord_fd3fd5ca38edbe264faa, 27/11/2026) :
- ajoute l'étape « Lead entrant » en tête du Pipeline Bornes et l'option « Partenaire » du statut de lead ;
- pose le code postal (lu dans l'adresse publique) sur les entreprises du portail qui n'en ont pas ;
- prend trois entreprises réelles du Nord dans un livret de production (lecture seule, seed_hubspot.py) et crée :
  une transaction « Lead entrant » sans propriétaire, une transaction « Projet » à Camille, une entreprise
  « Partenaire » ; interlocuteurs fictifs.

    data/venv/bin/python seed/seed_tournees_filtres.py
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seed_hubspot import DATA, OWNER, ROSSINI_PORTAL, Hub, companies_from_production, fail  # noqa: E402

PEOPLE = [("Aurélie", "Delmas", "Responsable des services généraux"), ("Romain", "Vasseur", "Directeur d'exploitation"),
          ("Pauline", "Carré", "Gérante")]


def postcode(address: str) -> str:
    found = re.findall(r"\b(\d{5})\b", address or "")
    return found[-1] if found else ""


def main() -> None:
    hub = Hub((DATA / "hubspot-test-token").read_text().strip())
    account = hub.call("GET", "/account-info/v3/details")
    if int(account.get("portalId") or 0) == ROSSINI_PORTAL or account.get("accountType") != "DEVELOPER_TEST":
        fail(f"portail {account.get('portalId')} ({account.get('accountType')}) refusé : seul un compte de test développeur est accepté.")
    owner_id = (hub.call("GET", "/crm/v3/owners", params={"email": OWNER["email"]}).get("results") or [{}])[0].get("id")
    if not owner_id:
        fail("Camille Martin n'est pas propriétaire dans le portail : lancer d'abord seed_hubspot.py.")

    pipes = {p["label"]: p for p in hub.call("GET", "/crm/v3/pipelines/deals").get("results") or []}
    bornes, ombrieres = pipes.get("Pipeline Bornes"), pipes.get("Pipeline Ombrières")
    if not bornes or not ombrieres:
        fail("Pipelines Bornes et Ombrières absents : lancer d'abord seed_hubspot.py.")
    lead_stage = next((s for s in bornes["stages"] if s["label"] == "Lead entrant"), None)
    if not lead_stage:
        lead_stage = hub.call("POST", f"/crm/v3/pipelines/deals/{bornes['id']}/stages",
                              json={"label": "Lead entrant", "displayOrder": 0, "metadata": {"isClosed": "false", "probability": "0.1"}})
    project_stage = next(s for s in ombrieres["stages"] if s["label"] == "Projet")

    prop = hub.call("GET", "/crm/v3/properties/companies/hs_lead_status")
    if not any(o["value"] == "Partenaire" for o in prop.get("options") or []):
        options = prop["options"] + [{"label": "Partenaire", "value": "Partenaire", "displayOrder": len(prop["options"]), "hidden": False}]
        hub.call("PATCH", "/crm/v3/properties/companies/hs_lead_status", json={"options": options})

    # Code postal des entreprises qui n'en ont pas (lu dans leur adresse publique).
    after, fixed = None, 0
    while True:
        page = hub.call("POST", "/crm/v3/objects/companies/search", json={"limit": 100, "properties": ["address", "zip"], **({"after": after} if after else {})})
        for c in page.get("results") or []:
            p = c["properties"]
            if not p.get("zip") and postcode(p.get("address") or ""):
                hub.call("PATCH", f"/crm/v3/objects/companies/{c['id']}", json={"properties": {"zip": postcode(p["address"])}})
                fixed += 1
        after = (page.get("paging") or {}).get("next", {}).get("after")
        if not after:
            break

    rows = [r for r in companies_from_production(60, exclude=set()) if postcode(r.get("address") or "").startswith("59")]
    existing = set()
    for c in hub.call("POST", "/crm/v3/objects/companies/search", json={"limit": 100, "properties": ["name"]}).get("results") or []:
        existing.add(c["properties"]["name"])
    rows = [r for r in rows if r["name"] not in existing][:3] if len([r for r in rows if r["name"] not in existing]) >= 3 else rows[:3]
    if len(rows) < 3:
        fail(f"{len(rows)} entreprises du Nord trouvées dans le livret de production, 3 attendues.")
    now = datetime.now(timezone.utc)
    made = []
    for i, (row, role) in enumerate(zip(rows, ("lead", "projet", "partenaire"))):
        domain = (row.get("website") or "").split("//")[-1].split("/")[0].removeprefix("www.")
        props = {"name": row["name"], "address": row.get("address") or "", "city": row.get("city") or "", "zip": postcode(row.get("address") or ""),
                 "domain": domain, "country": "France", "hubspot_owner_id": owner_id}
        if role == "partenaire":
            props["hs_lead_status"] = "Partenaire"
        company = hub.upsert("companies", "name", props)
        first, last, job = PEOPLE[i]
        slug = lambda s: s.lower().translate(str.maketrans("éèêëàâîïôöûüç", "eeeeaaiioouuc"))
        contact = hub.upsert("contacts", "email", {"email": f"{slug(first)}.{slug(last)}@example.fr", "firstname": first, "lastname": last,
                                                     "jobtitle": job, "phone": f"01 99 00 {60 + i:02d} {70 + i:02d}", "hubspot_owner_id": owner_id})
        hub.associate("contacts", contact, "companies", company)
        if role in ("lead", "projet"):
            pipeline, stage = (bornes, lead_stage) if role == "lead" else (ombrieres, project_stage)
            kind = "Bornes" if role == "lead" else "Ombrières"
            deal_props = {"dealname": f"{row['name']} · {kind}", "pipeline": pipeline["id"], "dealstage": stage["id"],
                          "amount": "26000" if role == "lead" else "190000", "closedate": (now + timedelta(days=60)).strftime("%Y-%m-%d")}
            deal_props["hubspot_owner_id"] = "" if role == "lead" else owner_id
            deal = hub.upsert("deals", "dealname", deal_props)
            hub.associate("deals", deal, "companies", company)
            hub.associate("deals", deal, "contacts", contact)
        made.append(f"{role} : {row['name']} ({props['zip']})")
    print(f"Portail {account['portalId']} : étape Lead entrant, option Partenaire, {fixed} codes postaux posés ; " + " ; ".join(made))


if __name__ == "__main__":
    main()

