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

import uvicorn

from leadgenerator.platform import google_agenda, sales_documents

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
google_agenda.FIELDS = google_agenda.FIELDS.replace("items(id,", "items(id,extendedProperties,")
google_agenda.normalize = studio_event_only
google_agenda.insert_event = insert_marked

uvicorn.run("leadgenerator.platform.app:app", host="127.0.0.1", port=platform_port, access_log=False, timeout_keep_alive=120)
