#!/usr/bin/env python3
"""Plateforme du studio Bigup : le code de production, avec Google Drive servi par le Drive du studio.

Seules deux choses changent, et seulement dans ce processus : l'adresse de l'API Google Drive (le Drive du studio,
drive_double.py, sur 127.0.0.1) et le jeton Google (aucune clé de l'entreprise n'est donnée au studio).

Agenda Google (Nicolas, 22/11/2026 : « mets le mien ») : quand start.sh trouve data/google-agenda-delegation.json,
la délégation Google Workspace de Bigup sert l'agenda de nicolas@rossinienergy.com à la place de celui de chaque
compte du studio. Le studio n'y lit que les rendez-vous qu'il a lui-même créés (aucun rendez-vous réel à l'image)
et les y écrit privés et marqués disponibles, pour qu'ils ne bloquent pas l'agenda de Nicolas.

    python studio_platform.py <port de la plateforme> <port du Drive du studio>
"""
import sys
import json
from pathlib import Path

import uvicorn

from leadgenerator.platform import google_agenda, sales_documents
from leadgenerator.integrations import hubspot as hubspot_api
from leadgenerator.platform import colleague_requests

platform_port, drive_port = int(sys.argv[1]), int(sys.argv[2])
sales_documents.DRIVE = f"http://127.0.0.1:{drive_port}/drive/v3"
sales_documents.token = lambda email: "studio-drive"
sales_documents.add_member = lambda organizer, drive_id, email, role="writer": None

AGENDA_OWNER = "nicolas@rossinienergy.com"
STUDIO_MARK = {"private": {"studio": "bigup"}}
production_token = google_agenda.access_token
production_normalize = google_agenda.normalize
production_insert = google_agenda.insert_event


def owner_token(key, email, client=None, scope=google_agenda.SCOPE):
    return production_token(key, AGENDA_OWNER, client, scope)


def studio_event_only(event, email):
    if (event.get("extendedProperties") or {}).get("private", {}).get("studio") != "bigup":
        return None
    item = production_normalize(event, email)
    if item:
        item["busy"] = True  # disponible dans l'agenda de Nicolas, occupé pour Camille
    return item


def insert_marked(email, body):
    return production_insert(
        email, {**body, "extendedProperties": STUDIO_MARK, "transparency": "transparent", "visibility": "private"}
    )


google_agenda.access_token = owner_token

# Heure des journées de tournée (commande ord_fd3fd5ca38edbe264faa, 27/11/2026) : le navigateur filmé vit à l'heure du
# scénario (scenario.now, par exemple vendredi 27 novembre 2026 à 8 h 40). Sans cela, un passage ajouté le jour même
# après 18 h (heure réelle du poste) laissait la journée vide (« ne tient pas dans une journée de 0 min »). Quand
# data/studio-clock existe, le calcul des journées (route_planner.now) suit cette heure-là.
_clock = Path(__file__).resolve().parent / "data" / "studio-clock"
if _clock.exists():
    from datetime import datetime
    from leadgenerator.platform import route_planner
    _fixed = datetime.fromisoformat(_clock.read_text().strip())
    route_planner.now = lambda: _fixed.astimezone(route_planner.PARIS)
google_agenda.FIELDS = google_agenda.FIELDS.replace("items(id,", "items(id,extendedProperties,")
google_agenda.normalize = studio_event_only
google_agenda.insert_event = insert_marked

# Chargés d'affaires du studio (Nicolas, 27/11/2026 : photos et noms de vrais collègues pour le prospect en or et la
# fenêtre Transférer). Ajouter un collègue réel comme utilisateur du portail HubSpot de test lui enverrait une
# invitation : le studio le déclare donc dans data/studio-owners.json, lu ici à chaque appel. L'annuaire des
# propriétaires HubSpot (list_owners) reçoit ces collègues, et une entreprise du portail de test listée dans
# « companies » a pour propriétaire celui qu'il nomme. Rien n'est écrit dans HubSpot.
STUDIO_OWNERS = Path(__file__).resolve().parent / "data" / "studio-owners.json"
production_list_owners = hubspot_api.list_owners
production_owner_ids = colleague_requests._owner_ids


def studio_owners():
    if not STUDIO_OWNERS.exists():
        return {"owners": [], "companies": {}}
    return json.loads(STUDIO_OWNERS.read_text())


def list_owners_with_studio(*, timeout: int = 30):
    owners = production_list_owners(timeout=timeout)
    known = {o.id for o in owners}
    return owners + [
        hubspot_api.HubSpotOwner(id=o["id"], email=o["email"], first_name=o["first_name"], last_name=o["last_name"], teams=[])
        for o in studio_owners()["owners"] if o["id"] not in known
    ]


def owner_ids_with_studio(company_ids):
    ids = production_owner_ids(company_ids)
    for company, owner in studio_owners()["companies"].items():
        if company in {str(c) for c in company_ids}:
            ids[company] = owner
    return ids


hubspot_api.list_owners = list_owners_with_studio
colleague_requests._owner_ids = owner_ids_with_studio

uvicorn.run("leadgenerator.platform.app:app", host="127.0.0.1", port=platform_port, access_log=False, timeout_keep_alive=120)
