#!/usr/bin/env python3
"""Semis du studio Bigup : une recherche de contact terminée dans l'historique de Camille (Prospection › Un contact).

Sans elle, la page montre « Mes recherches de contacts · Aucune recherche pour le moment », un état vide interdit à
l'image (règle 6 du studio). La recherche est écrite par les fonctions mêmes de Bigup (quick_contact._ensure_table,
_ensure_column, research_columns._upsert), au nom de Camille, comme start_quick_contact l'écrirait, sans lancer de
recherche : le studio n'a ni internet ni fournisseur. Ses valeurs reprennent la fiche SI GROUP- BETHUNE du studio :
Marc Perrin (personne fictive du semis), son poste prouvé par son profil fictif, le site de l'entreprise ; son
entreprise est déjà dans les prospects du mois de Camille. Relançable : la recherche existante est remplacée.

    data/venv/bin/python seed/seed_quick_contact.py
"""
import sys
from pathlib import Path

STUDIO = Path(__file__).resolve().parent.parent
DATA = STUDIO / "data"
WS, SUBJECT, EMAIL = "studio-bigup", "studio-commercial", "camille.martin@rossinienergy.com"
COMPANY, SITE_NAME = "SI GROUP- BETHUNE", "SI GROUP- BETHUNE"
# Adresse du Site que la plateforme de production écrit dans la source d'un indice saisi (start_quick_contact).
SITE_URL = "https://bigup.rossinienergy.com"
ASKED_AT = "2026-11-18T09:42:00+00:00"
CONTACT = {"first_name": "Marc", "last_name": "Perrin", "company": COMPANY}
ANSWERS = {
    "job_title": {
        "state": "done", "value": "Planificateur maintenance", "method": "web_research",
        "source_url": "https://www.linkedin.com/in/marc-perrin-fictif-b2a85a14a",
        "detail": "Poste actuel sur le profil LinkedIn : « Planificateur maintenance » chez SI Group, depuis février 2021.",
        "observed_at": "2026-11-16",
    },
    "website": {
        "state": "done", "value": "siigroup.com", "method": "web_research",
        "source_url": "https://www.siigroup.com",
        "detail": "Site de SI Group, l'entreprise de l'établissement SI GROUP- BETHUNE dans l'annuaire des entreprises.",
        "observed_at": "2026-11-16",
    },
}


def fail(message):
    sys.exit("Semis du studio Bigup (recherche de contact) : " + message)


def main():
    from leadgenerator.platform import quick_contact as qc, research_columns as rc
    from leadgenerator.platform.auth import Actor, Settings
    from leadgenerator.platform.service import Service
    from leadgenerator.platform.store import Store, connect

    runtime = (DATA / "runtime-password").read_text().strip()
    url = f"postgresql://lead_platform_app:{runtime}@127.0.0.1:55810/studio"
    settings = Settings(database_url=url, gateway_secret=(DATA / "gateway-secret").read_text().strip(), workspace_id=WS,
                        site_id="studio-bigup-site", admin_subject="studio-admin", document_root=str(DATA / "documents"))
    actor = Actor(subject=SUBJECT, email=EMAIL, workspace=WS, surface="site")
    with connect(url) as conn:
        conn.execute("SELECT set_config('lead_platform.workspace',%s,true)", (WS,))
        service = Service(Store(conn, WS, SUBJECT), actor, settings)
        site = conn.execute("SELECT id::text AS id, data->>'siren' AS siren FROM lead_platform.opportunities WHERE workspace_id=%s AND data->>'kind'='site' AND data->>'name'=%s AND NOT archived", (WS, SITE_NAME)).fetchone()
        book = conn.execute("SELECT selection_id::text AS selection_id, month FROM lead_platform.monthly_books WHERE workspace_id=%s AND owner_email=%s", (WS, EMAIL)).fetchone()
        if not site or not book:
            fail("la fiche « " + SITE_NAME + " » ou le livret du mois de Camille manque : lancer d'abord seed/all.sh.")
        table = qc._ensure_table(service)
        service.own_campaign(table["campaign_id"])
        for old in conn.execute("SELECT id::text AS id FROM lead_platform.opportunities WHERE workspace_id=%s AND data->>'table_id'=%s AND data ? %s AND NOT archived", (WS, table["id"], qc.PURPOSE)).fetchall():
            conn.execute("UPDATE lead_platform.opportunities SET archived=true WHERE id=%s", (old["id"],))
        columns = {k: qc._ensure_column(service, table, k, *spec) for k, spec in qc.FIELDS.items()}
        requested = list(ANSWERS)
        from leadgenerator.platform import monthly_books
        row = service.store.create("opportunities", {
            "kind": "imported_row", "table_id": table["id"], "position": -1,
            "values": {"c1": "Marc Perrin", "c2": ASKED_AT, "c3": ", ".join(columns[k]["data"]["label"] for k in requested)},
            qc.PURPOSE: {
                "contact": CONTACT, "selected_columns": [], "requested": requested, "author": EMAIL, "requested_at": ASKED_AT,
                "prospect": {"state": "added", "at": ASKED_AT, "row_id": site["id"], "name": SITE_NAME, "siren": site["siren"],
                             "selection_id": book["selection_id"], "month": book["month"],
                             "month_label": monthly_books.month_label(book["month"]), "already": True,
                             "contact": "Marc Perrin", "coordinates": []},
            },
        }, campaign_id=table["campaign_id"])
        source = SITE_URL + "/api/platform/quick-contact?id=" + row["id"]
        for key, value in CONTACT.items():
            rc._upsert(service, columns[key], row["id"], {"state": "review", "value": value, "method": "manual", "source_url": source,
                       "detail": "Indice saisi par " + EMAIL + ". À vérifier ; conservé sans remplacement.", "observed_at": ASKED_AT[:10]})
        for key, cell in ANSWERS.items():
            rc._upsert(service, columns[key], row["id"], cell)
        history = qc._history(service, table)
        conn.commit()
    shown = [h for h in history if h["id"] == row["id"]]
    if not shown or [a["state"] for a in shown[0]["answers"]] != ["done", "done"] or (shown[0]["prospect"] or {}).get("state") != "added":
        fail("la recherche relue n'a pas l'état attendu : " + repr(shown)[:600])
    print("Recherche de contact semée pour Camille : Marc Perrin (" + ", ".join(a["label"] + " : " + a["value"] for a in shown[0]["answers"]) + ")")


if __name__ == "__main__":
    main()

