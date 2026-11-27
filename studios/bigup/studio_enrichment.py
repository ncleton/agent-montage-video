"""Ouvrier d'enrichissement du studio Bigup : le vrai code des demandes d'email et de téléphone
(contact_enrichment_worker.jobs_forever), avec un fournisseur Enrow de test à la place d'api.enrow.io.

Règle 4 du studio : aucune clé de fournisseur payant. La clé vaut « studio-double », et chaque appel vers Enrow est
servi ici, sans réseau : un email fictif sur example.fr et un numéro de la plage 06 39 98 réservée par l'ARCEP aux
œuvres de fiction. Les autres boucles de l'ouvrier de production (livrets du mois, zones, HubSpot) ne tournent pas.

    python studio_enrichment.py
"""
import hashlib
import itertools
import os
import unicodedata
import uuid
from urllib.parse import parse_qs, urlparse

from leadgenerator.integrations import enrichment
from leadgenerator.platform import contact_enrichment_worker
from leadgenerator.platform.auth import Settings

for key in ("ENROW_API_KEY", "FULLENRICH_API_KEY"):
    if os.environ.get(key) != "studio-double":
        raise SystemExit(f"Studio Bigup : l'ouvrier d'enrichissement n'accepte que la clé factice studio-double ({key}).")

JOBS: dict[str, dict] = {}
COUNTER = itertools.count(1)


def _slug(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if c.isalnum() or c in " -").strip().replace(" ", ".")


def _phone(seed: str) -> str:
    n = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % 10000
    return f"+33 6 39 98 {n // 100:02d} {n % 100:02d}"


def double(url, *, method, headers, payload=None, timeout=30):
    if url.startswith(enrichment.FULLENRICH_BASE):
        if method == "POST":
            job = str(uuid.uuid4())
            row = ((payload or {}).get("data") or [{}])[0]
            JOBS[job] = {"path": "fullenrich", **row}
            return {"enrichment_id": job}
        job = urlparse(url).path.rsplit("/", 1)[-1]
        asked = JOBS.get(job)
        if not asked:
            return {"status": "UNKNOWN", "data": []}
        name = f"{asked.get('first_name', '')} {asked.get('last_name', '')}".strip()
        info = {}
        if "contact.work_emails" in asked.get("enrich_fields", []):
            info["most_probable_work_email"] = {"email": _slug(name) + "@example.fr", "status": "DELIVERABLE"}
        if "contact.phones" in asked.get("enrich_fields", []):
            info["most_probable_phone"] = {"number": _phone(name), "region": "FR", "line_type": "mobile"}
        return {"status": "FINISHED", "data": [{"contact_info": info}], "cost": {"credits": 10 if "most_probable_phone" in info else 1}}
    if not url.startswith(enrichment.ENROW_BASE):
        raise RuntimeError("Studio Bigup : seuls Enrow et FullEnrich ont un fournisseur de test ; " + (urlparse(url).hostname or "?") + " refusé.")
    if method == "POST":
        job = str(uuid.uuid4())
        JOBS[job] = {"path": urlparse(url).path, **(payload or {})}
        return {"id": job, "credits_used": 0}
    job = parse_qs(urlparse(url).query).get("id", [""])[0]
    asked = JOBS.get(job)
    if not asked:
        return {"qualification": "not_found"}
    if asked["path"].endswith("/email/find/single"):
        return {"qualification": "valid", "email": _slug(asked.get("fullname", "contact")) + "@example.fr", "credits_used": 1}
    return {"qualification": "valid", "number": _phone(asked.get("linkedin_url", job)), "credits_used": 40}


enrichment._request_json = double
contact_enrichment_worker.jobs_forever(Settings.load())
