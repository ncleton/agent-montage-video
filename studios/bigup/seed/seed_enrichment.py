"""Connecteurs Enrow et FullEnrich du studio : mêmes champs et mêmes tarifs que la production (lus le 26/11/2026),
plafonds en crédits à la place du solde du fournisseur (le studio ne lit aucun compte réel). Les clés sont factices
(studio_enrichment.py). Relançable.

    data/venv/bin/python seed/seed_enrichment.py
"""
import uuid
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

DATA = Path(__file__).resolve().parent.parent / "data"
WORKSPACE, ADMIN = "studio-bigup", "studio-admin"
LIMITS = {"per_action_credit_limit": 200, "operator_daily_credit_limit": 2000, "workspace_daily_credit_limit": 10000,
          "spend_mode": "capped"}
CONNECTORS = {
    "enrow": {"label": "Enrow", "allowed_fields": ["work_email"], "pricing": {
        "estimated": True, "tax_basis": "HT", "eur_per_credit": 0.015144766146993317,
        "reference": "Estimation HT de l’abonnement Enrow à 17 USD, converti au taux BCE du 19/10/2026 : 1 EUR = 1,1225 USD. Taux bancaire et frais éventuels non inclus."}},
    "fullenrich": {"label": "FullEnrich", "allowed_fields": ["work_email", "phone"],
                   "field_credit_costs": {"phone": 10, "work_email": 1}, "pricing": {
        "estimated": False, "tax_basis": "HT", "eur_per_credit": 0.058,
        "reference": "Tarif de l’offre FullEnrich : 29 EUR HT, vérifié sur le compte professionnel le 20/10/2026."}},
}
with psycopg.connect(host="127.0.0.1", port=55810, dbname="studio", user="postgres",
                     password=(DATA / "pg-password").read_text().strip()) as conn:
    for provider, fields in CONNECTORS.items():
        data = {"category": "connector", "provider": provider, "enabled": True, **LIMITS, **fields}
        conn.execute(
            "INSERT INTO lead_platform.configurations (id,workspace_id,owner_id,archived,data) VALUES (%s,%s,%s,false,%s) "
            "ON CONFLICT(id) DO UPDATE SET data=excluded.data, archived=false",
            (str(uuid.uuid5(uuid.NAMESPACE_URL, "studio-bigup:connector:" + provider)), WORKSPACE, ADMIN, Jsonb(data)),
        )
print("Connecteurs Enrow et FullEnrich du studio actifs (fournisseur de test, tarifs de production).")
