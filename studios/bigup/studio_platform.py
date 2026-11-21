#!/usr/bin/env python3
"""Plateforme du studio Bigup : le code de production, avec Google Drive servi par le Drive du studio.

Seules deux choses changent, et seulement dans ce processus : l'adresse de l'API Google Drive (le Drive du studio,
drive_double.py, sur 127.0.0.1) et le jeton Google (aucune clé de l'entreprise n'est donnée au studio).

    python studio_platform.py <port de la plateforme> <port du Drive du studio>
"""
import sys

import uvicorn

from leadgenerator.platform import sales_documents

platform_port, drive_port = int(sys.argv[1]), int(sys.argv[2])
sales_documents.DRIVE = f"http://127.0.0.1:{drive_port}/drive/v3"
sales_documents.token = lambda email: "studio-drive"
sales_documents.add_member = lambda organizer, drive_id, email, role="writer": None

uvicorn.run("leadgenerator.platform.app:app", host="127.0.0.1", port=platform_port, access_log=False, timeout_keep_alive=120)

