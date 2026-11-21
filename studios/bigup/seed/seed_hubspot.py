#!/usr/bin/env python3
"""Semis HubSpot du studio Bigup : faux leads et faux rendez-vous, dans le portail de test du studio seulement.

Lit le jeton de data/hubspot-test-token, vérifie que le portail est un compte de test développeur (jamais le
portail de Rossini, 6053297), puis crée ou met à jour, sans doublon :
- l'utilisatrice fictive Camille Martin (propriétaire HubSpot du commercial de démonstration), sans e-mail d'invitation ;
- les pipelines « Pipeline Bornes » et « Pipeline Ombrières » avec les étapes de Rossini ;
- des entreprises réelles (données publiques lues en production, en lecture seule) avec des interlocuteurs fictifs ;
- des transactions en cours à Camille, et six rendez-vous de la semaine (trois prospects, deux leads, un prescripteur).

    data/venv/bin/python seed/seed_hubspot.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

STUDIO = Path(__file__).resolve().parent.parent
DATA = STUDIO / "data"
API = "https://api.hubapi.com"
ROSSINI_PORTAL = 6053297
OWNER = {"email": "camille.martin@rossinienergy.com", "firstName": "Camille", "lastName": "Martin"}
PARIS = ZoneInfo("Europe/Paris")
PIPELINES = {
    "Pipeline Bornes": ["Projet", "Visite technique", "Devis envoyé", "Négociation", "Gagné", "Perdu", "No bid"],
    "Pipeline Ombrières": ["Projet", "Étude de faisabilité", "Devis envoyé", "Négociation", "Gagné", "Perdu", "No bid"],
}
PEOPLE = [("Claire", "Moreau", "Responsable des services généraux"), ("Julien", "Lefèvre", "Directeur de site"),
          ("Sophie", "Garnier", "Responsable immobilier"), ("Thomas", "Roux", "Directeur technique"),
          ("Élodie", "Fontaine", "Directrice administrative et financière"), ("Marc", "Girard", "Responsable énergie"),
          ("Nathalie", "Bonnet", "Responsable RSE"), ("Hugo", "Mercier", "Directeur général")]


def fail(message: str) -> None:
    sys.exit("Semis HubSpot du studio : " + message)


class Hub:
    def __init__(self, token: str):
        self.http = httpx.Client(base_url=API, headers={"Authorization": "Bearer " + token}, timeout=30)

    def call(self, method: str, path: str, **kw) -> dict:
        r = self.http.request(method, path, **kw)
        if r.status_code >= 400:
            fail(f"{method} {path} : HTTP {r.status_code} {r.text[:400]}")
        return r.json() if r.content else {}

    def search(self, obj: str, prop: str, value: str) -> dict | None:
        found = self.call("POST", f"/crm/v3/objects/{obj}/search", json={
            "filterGroups": [{"filters": [{"propertyName": prop, "operator": "EQ", "value": value}]}], "limit": 1})
        return (found.get("results") or [None])[0]

    def upsert(self, obj: str, prop: str, properties: dict) -> str:
        current = self.search(obj, prop, properties[prop])
        if current:
            self.call("PATCH", f"/crm/v3/objects/{obj}/{current['id']}", json={"properties": properties})
            return current["id"]
        return self.call("POST", f"/crm/v3/objects/{obj}", json={"properties": properties})["id"]

    def associate(self, a: str, a_id: str, b: str, b_id: str) -> None:
        self.call("PUT", f"/crm/v4/objects/{a}/{a_id}/associations/default/{b}/{b_id}")


def companies_from_production(count: int, exclude: set[str]) -> list[dict]:
    """Entreprises vertes ou bleues du livret de production, données publiques seulement (lecture seule)."""
    sql = """SET default_transaction_read_only = on;
SELECT row_to_json(r) FROM (
  SELECT o.id, o.data->>'name' AS name, o.data->>'address' AS address, o.data->>'commune' AS city,
         (SELECT t.data->>'value' FROM lead_platform.tasks t JOIN lead_platform.configurations c ON c.campaign_id=t.campaign_id
            AND c.data->>'category'='table_research_column' AND c.id=t.data->>'column_id'
          WHERE t.campaign_id=o.campaign_id AND t.data->>'row_id'=o.id AND c.data->>'label'='Site web' LIMIT 1) AS website
  FROM lead_platform.opportunities o JOIN lead_platform.row_scores s ON s.campaign_id=o.campaign_id AND s.row_id=o.id
  WHERE o.campaign_id=(SELECT campaign_id FROM lead_platform.monthly_books WHERE owner_email='luca@rossinienergy.com' AND month='2026-11')
    AND o.data->>'kind'='site' AND NOT o.archived AND s.tier IN ('A','B')
  ORDER BY md5(o.id) LIMIT 60) r;"""
    done = subprocess.run(["ssh", "contabo-leadgen", "docker exec -i leadgenerator-platform-postgres-1 psql -U lead_platform_owner -d lead_platform -At"],
                          input=sql, capture_output=True, text=True, timeout=120)
    if done.returncode:
        fail("lecture de production refusée : " + done.stderr[:300])
    rows = [json.loads(l) for l in done.stdout.splitlines() if l.startswith("{")]
    rows = [r for r in rows if r["id"] not in exclude and r.get("name")]
    if len(rows) < count:
        fail(f"{len(rows)} entreprises disponibles, {count} demandées.")
    return rows[:count]


def main() -> None:
    token = (DATA / "hubspot-test-token").read_text().strip() if (DATA / "hubspot-test-token").exists() else ""
    if not token:
        fail("data/hubspot-test-token absent : créer le portail de test (studios/bigup/README.md).")
    hub = Hub(token)
    account = hub.call("GET", "/account-info/v3/details")
    if int(account.get("portalId") or 0) == ROSSINI_PORTAL or account.get("accountType") != "DEVELOPER_TEST":
        fail(f"portail {account.get('portalId')} ({account.get('accountType')}) refusé : seul un compte de test développeur est accepté.")

    # Propriétaire : l'utilisatrice fictive Camille Martin, sans e-mail d'invitation.
    owners = hub.call("GET", "/crm/v3/owners", params={"email": OWNER["email"]}).get("results") or []
    if not owners:
        hub.call("POST", "/settings/v3/users", json={**OWNER, "sendWelcomeEmail": False})
        for _ in range(20):
            owners = hub.call("GET", "/crm/v3/owners", params={"email": OWNER["email"]}).get("results") or []
            if owners:
                break
            import time; time.sleep(3)
    if not owners:
        fail("Camille Martin n'apparaît pas comme propriétaire HubSpot après sa création.")
    owner_id = owners[0]["id"]

    # Pipelines de Rossini.
    stages: dict[str, dict[str, str]] = {}
    existing = {p["label"]: p for p in hub.call("GET", "/crm/v3/pipelines/deals").get("results") or []}
    for order, (label, names) in enumerate(PIPELINES.items(), start=1):
        if label not in existing:
            spec = []
            for i, name in enumerate(names):
                closed = name in ("Gagné", "Perdu", "No bid")
                spec.append({"label": name, "displayOrder": i,
                             "metadata": {"isClosed": "true" if closed else "false",
                                          "probability": "1.0" if name == "Gagné" else ("0.0" if closed else str(round(0.2 + 0.2 * i, 1)))}})
            existing[label] = hub.call("POST", "/crm/v3/pipelines/deals", json={"label": label, "displayOrder": order, "stages": spec})
        stages[label] = {s["label"]: s["id"] for s in existing[label]["stages"]}

    # Entreprises réelles, interlocuteurs fictifs.
    rows = companies_from_production(8, exclude=set())
    created = []
    for i, row in enumerate(rows):
        domain = ""
        if row.get("website"):
            domain = row["website"].split("//")[-1].split("/")[0].removeprefix("www.")
        company = hub.upsert("companies", "name", {"name": row["name"], "address": row.get("address") or "", "city": row.get("city") or "",
                                                     "domain": domain, "country": "France", "hubspot_owner_id": owner_id})
        first, last, role = PEOPLE[i % len(PEOPLE)]
        slug = lambda s: s.lower().translate(str.maketrans("éèêëàâîïôöûüç", "eeeeaaiioouuc"))
        email = f"{slug(first)}.{slug(last)}@example.fr"
        contact = hub.upsert("contacts", "email", {"email": email, "firstname": first, "lastname": last, "jobtitle": role,
                                                     "phone": f"01 99 00 {20 + i:02d} {40 + i:02d}", "hubspot_owner_id": owner_id})
        hub.associate("contacts", contact, "companies", company)
        created.append({"row": row, "company": company, "contact": contact, "person": f"{first} {last}"})

    # Transactions en cours de Camille : cinq bornes, trois ombrières.
    now = datetime.now(timezone.utc)
    plan = [("Pipeline Bornes", "Devis envoyé", 38000), ("Pipeline Bornes", "Projet", 24000), ("Pipeline Bornes", "Visite technique", 52000),
            ("Pipeline Bornes", "Négociation", 31000), ("Pipeline Bornes", "Projet", 18000), ("Pipeline Ombrières", "Étude de faisabilité", 240000),
            ("Pipeline Ombrières", "Devis envoyé", 410000), ("Pipeline Ombrières", "Projet", 180000)]
    for item, (pipeline, stage, amount) in zip(created, plan):
        kind = "Bornes" if pipeline == "Pipeline Bornes" else "Ombrières"
        deal = hub.upsert("deals", "dealname", {"dealname": f"{item['row']['name']} · {kind}", "pipeline": existing[pipeline]["id"],
                                                 "dealstage": stages[pipeline][stage], "amount": str(amount), "hubspot_owner_id": owner_id,
                                                 "closedate": (now + timedelta(days=45)).strftime("%Y-%m-%d")})
        hub.associate("deals", deal, "companies", item["company"])
        hub.associate("deals", deal, "contacts", item["contact"])

    # Six rendez-vous de la semaine en cours, sur les entreprises ci-dessus.
    monday = (datetime.now(PARIS) - timedelta(days=datetime.now(PARIS).weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    if datetime.now(PARIS).weekday() >= 5:
        monday += timedelta(days=7)
    slots = [(0, 9, 30), (0, 14, 0), (1, 10, 0), (2, 11, 0), (3, 9, 0), (3, 15, 30)]
    for (day, hour, minute), item in zip(slots, created):
        start = monday + timedelta(days=day, hours=hour, minutes=minute)
        end = start + timedelta(hours=1)
        title = f"Rendez-vous · {item['row']['name']}"
        meeting = hub.upsert("meetings", "hs_meeting_title", {
            "hs_meeting_title": title, "hs_timestamp": start.astimezone(timezone.utc).isoformat(),
            "hs_meeting_start_time": start.astimezone(timezone.utc).isoformat(), "hs_meeting_end_time": end.astimezone(timezone.utc).isoformat(),
            "hs_meeting_location": ", ".join(x for x in (item["row"].get("address"), item["row"].get("city")) if x),
            "hs_meeting_body": f"Présentation des bornes et ombrières à {item['person']} (studio de tournage, rendez-vous fictif).",
            "hs_meeting_outcome": "SCHEDULED", "hubspot_owner_id": owner_id})
        hub.associate("meetings", meeting, "companies", item["company"])
        hub.associate("meetings", meeting, "contacts", item["contact"])
    print(f"Portail de test {account['portalId']} semé : propriétaire Camille Martin ({owner_id}), {len(created)} entreprises,"
          f" {len(plan)} transactions, {len(slots)} rendez-vous de la semaine du {monday:%d/%m}.")


if __name__ == "__main__":
    main()

