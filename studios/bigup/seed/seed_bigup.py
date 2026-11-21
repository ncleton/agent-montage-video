#!/usr/bin/env python3
"""Semis du studio de tournage Bigup : de vraies entreprises, des personnes fictives.

Lit en production, en lecture seule (transaction read only, par SSH), un échantillon tiré au hasard des
entreprises vertes (palier A) d'un livret du mois : la ligne, ses réponses sourcées, son parking, son cadastre,
son score et son logo. Chaque personne est remplacée par une personne fictive, chaque contact et chaque lien
HubSpot est retiré, les collègues deviennent l'administrateur du studio. Le tout est écrit dans la base du studio
(127.0.0.1 seulement), puis partagé au commercial de démonstration comme ses prospects du mois.

    data/venv/bin/python seed/seed_bigup.py [--owner luca@rossinienergy.com] [--month 2026-11] [--count 20] [--seed N]

Refuse de tourner si une variable d'un service extérieur est présente dans l'environnement.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import random
import re
import subprocess
import sys
import tarfile
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

STUDIO = Path(__file__).resolve().parent.parent
DATA = STUDIO / "data"
PROD = "contabo-leadgen"
PROD_DB = "docker exec -i leadgenerator-platform-postgres-1 psql -U lead_platform_owner -d lead_platform -At -v ON_ERROR_STOP=1"
PROD_FILES = "/opt/leadgenerator-platform/state/files"
WORKSPACE = "studio-bigup"
ADMIN_SUBJECT, ADMIN_EMAIL = "studio-admin", "studio.admin@rossinienergy.com"
COMMERCIAL_EMAIL, COMMERCIAL_NAME = "camille.martin@rossinienergy.com", "Camille"
FORBIDDEN_ENV = re.compile(r"^(HUBSPOT|GOOGLE|SLACK|NEXTCLOUD|FULLENRICH|KASPR|LUSHA|DROPCONTACT|PAPPERS|OPENAI|ANTHROPIC|MUX|THREECX|CX3|LINKEDIN)_|^LEADGENERATOR_(DATABASE_URL|GATEWAY_SECRET)$")

# Colonnes qui parlent de personnes ou de nos échanges : leur réponse devient fictive.
PERSON_COLUMNS = {
    "Dirigeant (registre)", "Chargé d’affaires", "Directeur de site", "Responsable technique ou SG",
    "Responsable immobilier", "Responsable RSE", "DAF ou responsable flotte", "Coordonnées directes vérifiées",
}
# Questions que la fiche d'un prospect affiche : une entreprise n'entre au studio que si chacune a sa réponse finale.
FICHE_COLUMNS = ["Bornes exigées par la loi", "Loi APER ombrières", "Bornes publiques à moins de 300 m", "Bornes sur le parking",
                 "Bornes cartographiées (OSM)", "Bornes de l’entreprise", "Bornes Chargemap", "Ce que fait l’entreprise",
                 "Actualité récente", "Responsable technique ou SG", "Site web", "Effectif", "Chiffre d’affaires", "Propriété du parking"]
INTERNAL_COLUMNS = {"Retour d’appel", "Commentaire d’appel", "Décision commerciale", "Message d’approche"}
FIRST = ["Claire", "Julien", "Sophie", "Thomas", "Élodie", "Marc", "Nathalie", "Hugo", "Laure", "Antoine", "Isabelle",
         "Pierre", "Céline", "Vincent", "Aurélie", "Olivier", "Manon", "Benoît", "Agathe", "Damien"]
LAST = ["Moreau", "Lefèvre", "Garnier", "Roux", "Fontaine", "Girard", "Bonnet", "Mercier", "Chevalier", "Faure",
        "Lambert", "Rousseau", "Blanc", "Gauthier", "Perrin", "Robin", "Masson", "Renard", "Brunet", "Caron"]
ROLES = {
    "Dirigeant (registre)": "Président", "Directeur de site": "Directeur de site",
    "Responsable technique ou SG": "Responsable des services généraux", "Responsable immobilier": "Responsable immobilier",
    "Responsable RSE": "Responsable RSE", "DAF ou responsable flotte": "Directrice administrative et financière",
    "Chargé d’affaires": "Chargé d’affaires", "Coordonnées directes vérifiées": "Responsable des services généraux",
}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MOBILE = re.compile(r"(?:\+33\s?|0)[67](?:[\s.-]?\d{2}){4}")
GENERIC_MAILBOX = re.compile(r"^(contact|info|infos|accueil|bonjour|hello|commercial|service|secretariat|direction|rh|recrutement|compta|comptabilite|sav|support|admin|office)[@.]", re.I)


def fail(message: str) -> None:
    sys.exit("Semis du studio Bigup : " + message)


def guard() -> None:
    present = sorted(k for k in os.environ if FORBIDDEN_ENV.search(k))
    if present:
        fail("variables d'un service extérieur présentes dans l'environnement (" + ", ".join(present) + "). Le studio ne reçoit aucun accès de production : relancer sans elles.")


def prod(sql: str) -> list[dict]:
    """Lecture seule en production : une ligne JSON par enregistrement."""
    script = "SET default_transaction_read_only = on;\n" + sql
    done = subprocess.run(["ssh", PROD, PROD_DB], input=script, capture_output=True, text=True, timeout=300)
    if done.returncode:
        fail("lecture de production refusée : " + done.stderr.strip()[:500])
    return [json.loads(line) for line in done.stdout.splitlines() if line.startswith("{")]


def q(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def arr(values) -> str:
    return "ARRAY[" + ",".join(q(v) for v in values) + "]::text[]" if values else "ARRAY[]::text[]"


class Fiction:
    """Une personne fictive stable par clé (ligne, colonne)."""

    def __init__(self, seed: int):
        self.seed = seed

    def person(self, key: str) -> dict:
        h = int(hashlib.sha256(f"{self.seed}:{key}".encode()).hexdigest(), 16)
        first, last = FIRST[h % len(FIRST)], LAST[(h // 97) % len(LAST)]
        slug = lambda s: re.sub(r"[^a-z]", "", s.lower().translate(str.maketrans("éèêëàâîïôöûüç", "eeeeaaiioouuc")))
        return {"first_name": first, "last_name": last, "name": f"{first} {last}",
                "email": f"{slug(first)}.{slug(last)}@example.fr", "phone": f"01 99 00 {h % 90 + 10:02d} {(h // 7) % 90 + 10:02d}"}


class Names:
    """Table des vraies personnes et de leur double fictif, appliquée à tout le texte d'un enregistrement.

    Une personne est reconnue sans tenir compte des accents ni de la casse, sous toutes ses formes : « Prénom Nom »,
    « Nom Prénom », les champs first_name et last_name, et l'identifiant « prenom-nom » d'un profil."""

    def __init__(self, fiction: Fiction):
        self.fiction, self.map, self.surfaces, self.emails, self.used = fiction, {}, {}, {}, set()
        self.companies: list[str] = []

    def protect(self, names) -> None:
        """Noms d'entreprise gardés tels quels : « ETABLISSEMENTS GUY MARIN » reste le nom de la société."""
        self.companies = sorted({n.strip() for n in names if n and len(n.strip()) > 3}, key=len, reverse=True)
        self._protect = re.compile("|".join(self.fuzzy(self.plain(n)) for n in self.companies), re.I) if self.companies else None

    @staticmethod
    def plain(text: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFKD", str(text)) if not unicodedata.combining(c)).lower()

    def add(self, name, email=None) -> None:
        name = re.sub(r"\s+", " ", str(name or "")).strip(" ,;.")
        words = name.split(" ")
        if len(words) < 2 or len(words) > 4 or len(name) > 60 or any(ch.isdigit() for ch in name) or "@" in name:
            return
        key = self.plain(name)
        if key not in self.map:
            n = 0
            while True:
                fake = self.fiction.person(f"{key}:{n}")
                if fake["name"] not in self.used:
                    break
                n += 1
            self.used.add(fake["name"])
            self.map[key] = fake
        self.surfaces.setdefault(key, set()).add(name)
        if email and "@" in str(email):
            self.emails[str(email).lower()] = self.map[key]["email"]

    def collect(self, value) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("name"), str) and any(k in value for k in ("role", "linkedin_url", "email", "identity_status", "first_name")):
                self.add(value["name"], value.get("email"))
            if isinstance(value.get("first_name"), str) and isinstance(value.get("last_name"), str):
                self.add(value["first_name"] + " " + value["last_name"], value.get("email") or value.get("work_email"))
            for v in value.values():
                self.collect(v)
        elif isinstance(value, list):
            for v in value:
                self.collect(v)

    ACCENTS = {"a": "aàâäáã", "e": "eéèêë", "i": "iîïíì", "o": "oôöóò", "u": "uùûüú", "c": "cç", "y": "yÿ", "n": "nñ"}

    @classmethod
    def fuzzy(cls, plain: str) -> str:
        """Motif d'une forme sans accents qui reconnaît aussi ses formes accentuées."""
        return "".join("[" + cls.ACCENTS[ch] + "]" if ch in cls.ACCENTS else re.escape(ch) for ch in plain)

    def _compile(self):
        variants = {}
        for key, fake in self.map.items():
            first, last = key.split(" ", 1)
            for form in (key, f"{last} {first}"):
                variants[form] = fake["name"]
        self._variants = variants
        names = sorted(variants, key=len, reverse=True)
        self._names = re.compile(r"(?<![\w])(" + "|".join(self.fuzzy(n) for n in names) + r")(?![\w])", re.I) if names else None
        slugs = {key.replace(" ", "-"): self.plain(fake["name"]).replace(" ", "-") + "-fictif" for key, fake in self.map.items()}
        self._slugs = slugs
        self._slug = re.compile("|".join(self.fuzzy(k) for k in sorted(slugs, key=len, reverse=True)), re.I) if slugs else None
        mails = sorted(self.emails, key=len, reverse=True)
        self._mails = re.compile("|".join(re.escape(m) for m in mails), re.I) if mails else None

    def _text(self, text: str) -> str:
        if not hasattr(self, "_variants"):
            self._compile()
        kept = []
        if getattr(self, "_protect", None):
            def hold(m):
                kept.append(m.group(0))
                return "\x00" + str(len(kept) - 1) + "\x00"
            text = self._protect.sub(hold, text)
        text = self._replace_people(text)
        return re.sub("\x00(\\d+)\x00", lambda m: kept[int(m.group(1))], text) if kept else text

    def _replace_people(self, text: str) -> str:
        if self._names:
            text = self._names.sub(lambda m: self._variants.get(self.plain(m.group(0)), m.group(0)), text)
        if self._slug:
            text = self._slug.sub(lambda m: self._slugs.get(self.plain(m.group(0)), m.group(0)), text)
        if self._mails:
            text = self._mails.sub(lambda m: self.emails[m.group(0).lower()], text)
        if "linkedin.com/in/" in text:
            text = re.sub(r"https?://([a-z]{2,3}\.)?linkedin\.com/in/[^\s\"')]+",
                          lambda m: "https://www.linkedin.com/in/studio-fictif-" + hashlib.sha256(m.group(0).encode()).hexdigest()[:10], text)
        return text

    def replace(self, value):
        if isinstance(value, dict):
            out = {k: self.replace(v) for k, v in value.items()}
            first, last = value.get("first_name"), value.get("last_name")
            if isinstance(first, str) and isinstance(last, str):
                fake = self.map.get(self.plain(re.sub(r"\s+", " ", f"{first} {last}").strip()))
                if fake:
                    out["first_name"], out["last_name"] = fake["first_name"], fake["last_name"]
            return out
        if isinstance(value, list):
            return [self.replace(v) for v in value]
        return self._text(value) if isinstance(value, str) else value

    def leaks(self, records) -> list[str]:
        """Vraies personnes encore présentes dans les données copiées (sans accents, sans casse)."""
        text = self.plain(json.dumps(records, ensure_ascii=False))
        for company in self.companies:
            text = text.replace(self.plain(company), " ")
        forms = {}
        for key in self.map:
            first, last = key.split(" ", 1)
            for form in (key, f"{last} {first}", key.replace(" ", "-")):
                forms[form] = key
        pattern = re.compile(r"(?<![a-z])(" + "|".join(re.escape(f) for f in sorted(forms, key=len, reverse=True)) + r")(?![a-z])")
        found = sorted({forms[m.group(0)] for m in pattern.finditer(text)})
        return found


def scrub(value, prod_workspace: str, fiction: Fiction, key: str):
    """Retire de toute valeur les personnes réelles, les liens HubSpot et l'espace de production."""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k in ("hubspot_coordinates", "hubspot", "hubspot_id", "hubspot_url", "enrichment_job_id"):
                continue
            if k in ("run_as", "requested_by", "refreshed_by", "updated_by", "created_by", "selected_by", "by", "reported_by", "decided_by"):
                out[k] = ADMIN_EMAIL if isinstance(v, str) and "@" in v else (ADMIN_SUBJECT if isinstance(v, str) else v)
                continue
            out[k] = scrub(v, prod_workspace, fiction, key)
        return out
    if isinstance(value, list):
        return [scrub(v, prod_workspace, fiction, key) for v in value]
    if isinstance(value, str):
        if "hubspot.com" in value:
            return ""
        text = value.replace(prod_workspace, WORKSPACE)
        def mail(m):
            address = m.group(0)
            if address.lower().endswith("@rossinienergy.com"):
                return ADMIN_EMAIL
            if GENERIC_MAILBOX.match(address) or address.lower().endswith("@example.fr"):
                return address
            return fiction.person(key + address)["email"]
        text = EMAIL.sub(mail, text)
        text = MOBILE.sub(lambda m: fiction.person(key + m.group(0))["phone"], text)
        return text
    return value


def main() -> None:
    guard()
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", default="luca@rossinienergy.com", help="livret de production d'où tirer les entreprises")
    parser.add_argument("--month", default="2026-11")
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--seed", type=int, default=None, help="tirage reproductible")
    args = parser.parse_args()
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(1, 10**6)
    fiction = Fiction(seed)
    studio_month = datetime.now(timezone.utc).strftime("%Y-%m")

    book = prod(f"SELECT row_to_json(b) FROM (SELECT campaign_id, selection_id, share_id, data FROM lead_platform.monthly_books WHERE owner_email={q(args.owner)} AND month={q(args.month)}) b;")
    if not book:
        fail(f"aucun livret de {args.owner} pour {args.month} en production.")
    book = book[0]
    campaign = book["campaign_id"]
    prod_workspace = prod(f"SELECT row_to_json(c) FROM (SELECT workspace_id FROM lead_platform.campaigns WHERE id={q(campaign)}) c;")[0]["workspace_id"]

    candidates = prod(f"""SELECT row_to_json(c) FROM (
      SELECT o.id, o.data->>'operator_siren' AS siren, o.data->>'name' AS name, s.score,
        (SELECT co.id FROM lead_platform.companies co WHERE co.workspace_id=o.workspace_id AND co.siren=o.data->>'operator_siren' AND NOT co.archived LIMIT 1) AS company_id
      FROM lead_platform.opportunities o JOIN lead_platform.row_scores s ON s.campaign_id=o.campaign_id AND s.row_id=o.id
      WHERE o.campaign_id={q(campaign)} AND o.data->>'kind'='site' AND NOT o.archived AND s.tier IN ('A','B')
        AND EXISTS (SELECT 1 FROM lead_platform.tasks t WHERE t.campaign_id=o.campaign_id AND t.data->>'row_id'=o.id AND t.data->>'kind'='site_parking')
        -- Recherche terminée sur tout ce que la fiche montre (règle 6 du studio : ni « Calcul… » ni « Recherche… »).
        AND NOT EXISTS (SELECT 1 FROM lead_platform.configurations k WHERE k.campaign_id=o.campaign_id AND NOT k.archived
              AND k.data->>'category'='table_research_column' AND k.data->>'label' = ANY({arr(FICHE_COLUMNS)})
              AND NOT EXISTS (SELECT 1 FROM lead_platform.tasks t WHERE t.campaign_id=o.campaign_id AND t.data->>'row_id'=o.id
                              AND t.data->>'column_id'=k.id AND t.data->>'state' IN ('done','not_found','skipped','review')))) c;""")
    logo_dir = f"{PROD_FILES}/contact-photos/{hashlib.sha256(prod_workspace.encode()).hexdigest()[:20]}/logos"
    ids = [c["company_id"] or c["id"] for c in candidates]
    listing = subprocess.run(["ssh", PROD, f"cd {logo_dir} && ls " + " ".join(f"{i}.json" for i in ids) + " 2>/dev/null"],
                             capture_output=True, text=True, timeout=120).stdout.split()
    with_logo = [c for c in candidates if f"{c['company_id'] or c['id']}.json" in listing]
    if len(with_logo) < 30:
        fail(f"{len(with_logo)} entreprises vertes ou bleues à la recherche terminée, avec logo et parking, dans ce livret :"
             " au moins 30 sont nécessaires pour 25 prospects. Choisir un autre livret (--owner, --month).")
    chosen = random.Random(seed).sample(with_logo, min(args.count, len(with_logo)))
    rows = [c["id"] for c in chosen]
    print(f"Tirage {seed} : {len(chosen)} entreprises sur {len(with_logo)} candidates — " + ", ".join(c["name"] for c in chosen))

    records: dict[str, list[dict]] = {}
    base = "SELECT row_to_json(r) FROM (SELECT * FROM lead_platform.{t} WHERE {w}) r;"
    records["campaigns"] = prod(base.format(t="campaigns", w=f"id={q(campaign)}"))
    records["configurations"] = prod(base.format(t="configurations", w=f"campaign_id={q(campaign)} AND NOT archived AND data->>'category' IN ('campaign_table','table_column','table_priority','table_research_column')"))
    records["opportunities"] = prod(base.format(t="opportunities", w=f"campaign_id={q(campaign)} AND NOT archived AND (id=ANY({arr(rows)}) OR (data->>'kind'='imported_row' AND data->'source_row_ids' ?| {arr(rows)}))"))
    records["tasks"] = prod(base.format(t="tasks", w=f"campaign_id={q(campaign)} AND NOT archived AND data->>'row_id'=ANY({arr(rows)}) AND data->>'kind' IN ('research_cell','site_parking','site_land','aper_exemption')"))
    records["companies"] = prod(base.format(t="companies", w=f"siren=ANY({arr([c['siren'] for c in chosen if c['siren']])}) AND NOT archived"))
    scores = prod(base.format(t="row_scores", w=f"campaign_id={q(campaign)} AND row_id=ANY({arr(rows)})"))

    # Une réponse désigne sa question par l'identifiant de l'enregistrement de la question.
    labels = {c["id"]: c["data"].get("label") for c in records["configurations"] if c["data"].get("category") == "table_research_column"}
    # Les vraies personnes deviennent des personnes fictives, partout et toujours les mêmes : le format des réponses,
    # leurs pages sources (pages publiques de l'entreprise) et donc le score restent ceux de la production.
    people = Names(fiction)
    people.protect([r["data"].get(k) for r in records["opportunities"] for k in ("name", "operator_name")]
                   + [(r["data"].get("values") or {}).get("c1") for r in records["opportunities"]]
                   + [(r["data"].get("person") or {}).get("company_legal_name") for r in records["opportunities"]])
    for row in records["opportunities"]:
        data = row["data"]
        info = data.get("person") or {}
        if data.get("kind") == "imported_row":
            people.add(f"{info.get('first_name') or ''} {info.get('last_name') or ''}", info.get("work_email"))
            people.add((data.get("values") or {}).get("c2"))
        elif isinstance(data.get("found_contact"), dict):
            people.add(data["found_contact"].get("name"), data["found_contact"].get("email"))
    for task in records["tasks"]:
        people.collect(task["data"])
        label = labels.get(task["data"].get("column_id"))
        if task["data"].get("kind") == "research_cell" and label in PERSON_COLUMNS and isinstance(task["data"].get("value"), str):
            people.add(task["data"]["value"].split(",")[0])
    for task in records["tasks"]:
        data = task["data"]
        if data.get("kind") == "research_cell" and labels.get(data.get("column_id")) in INTERNAL_COLUMNS:
            # Nos notes d'appel et décisions internes ne sortent pas de la production.
            data.update({"value": None, "detail": None, "contacts": [], "source_url": None})
    for row in records["opportunities"]:
        info = row["data"].get("person") or {}
        real = Names.plain(re.sub(r"\s+", " ", f"{info.get('first_name') or ''} {info.get('last_name') or ''}").strip())
        if real in people.map:
            fake = people.map[real]
            info.update({"first_name": fake["first_name"], "last_name": fake["last_name"]})
            for gone in ("phone", "mobile_phone", "photo"):
                info.pop(gone, None)
    for table, items in records.items():
        for item in items:
            item["data"] = people.replace(item["data"])
    leaks = people.leaks(records)
    if leaks:
        text = Names.plain(json.dumps(records, ensure_ascii=False))
        where = []
        for key in leaks[:8]:
            at = text.find(key) if key in text else text.find(key.replace(" ", "-"))
            if at < 0:
                first, last = key.split(" ", 1)
                at = text.find(f"{last} {first}")
            where.append(text[max(0, at - 90):at + 40].replace(chr(10), " "))
        fail(f"{len(leaks)} vraies personnes restent dans les données copiées après remplacement : rien n'est écrit dans le studio."
             " Corriger Names.collect pour la forme où elles apparaissent :" + "".join(chr(10) + "  … " + w for w in where))
    print(f"{len(people.map)} personnes réelles remplacées par des personnes fictives, aucune ne reste.")
    for table, items in records.items():
        for item in items:
            item["data"] = scrub(item["data"], prod_workspace, fiction, item["id"])
            item["workspace_id"] = WORKSPACE
            if item.get("owner_id"):
                item["owner_id"] = ADMIN_SUBJECT
    campaign_data = records["campaigns"][0]["data"]
    campaign_data["name"] = f"Livret · {COMMERCIAL_NAME}"

    # Livret du mois du commercial de démonstration : la règle du livret de production, limitée à l'échantillon.
    selection = prod(base.format(t="selections", w=f"id={q(book['selection_id'])}"))[0]["data"]
    rule = selection.get("rule") or {}
    entered_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rule.update({"forced": [], "deferred": {}, "excluded": [], "reserve": [], "conflicts": [], "waiting": {},
                 "scores": {r: s["score"] for s in scores for r in [s["row_id"]]},
                 "entered": {r: entered_at for r in rows}, "refreshed_at": entered_at, "refreshed_by": ADMIN_EMAIL})
    rule["counts"] = {"green": len(rows), "scope": len(rows), "reserve": 0, "deferred": 0, "set_aside": 0}
    rule = scrub(rule, prod_workspace, fiction, "rule")
    selection_data = {**scrub(selection, prod_workspace, fiction, "selection"), "rule": rule, "row_ids": sorted(rows, key=lambda r: -(rule["scores"].get(r) or 0)), "lead_ids": [], "contact_ids": [],
                      "name": f"Livret du mois · {COMMERCIAL_NAME}", "month": studio_month}
    selection_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"studio-bigup:selection:{studio_month}"))
    share_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"studio-bigup:share:{studio_month}"))
    book_data = scrub(book["data"], prod_workspace, fiction, "book")
    book_data["name"] = f"Livret du mois · {COMMERCIAL_NAME}"

    password = (DATA / "pg-password").read_text().strip()
    with psycopg.connect(host="127.0.0.1", port=55810, dbname="studio", user="postgres", password=password) as conn:
        if conn.info.host not in ("127.0.0.1", "localhost"):
            fail("la base du studio doit être locale.")
        conn.execute("DELETE FROM lead_platform.row_scores WHERE workspace_id=%s", (WORKSPACE,))
        for table in ("tasks", "opportunities", "configurations", "campaigns", "selections"):
            conn.execute(f"DELETE FROM lead_platform.{table} WHERE workspace_id=%s AND (campaign_id IS NOT NULL OR id=ANY(%s))", (WORKSPACE, [selection_id, share_id]))
        conn.execute("DELETE FROM lead_platform.configurations WHERE workspace_id=%s AND data->>'category'='book_share'", (WORKSPACE,))
        conn.execute("DELETE FROM lead_platform.monthly_books WHERE workspace_id=%s", (WORKSPACE,))
        for table, items in records.items():
            for item in items:
                columns = list(item)
                values = [Jsonb(v) if c == "data" else v for c, v in item.items()]
                conn.execute(
                    f"INSERT INTO lead_platform.{table} ({','.join(columns)}) VALUES ({','.join(['%s'] * len(columns))}) ON CONFLICT (id) DO UPDATE SET data=EXCLUDED.data, workspace_id=EXCLUDED.workspace_id, owner_id=EXCLUDED.owner_id, archived=false",
                    values)
        for s in scores:
            conn.execute("INSERT INTO lead_platform.row_scores (workspace_id,campaign_id,table_key,row_id,score,tier,method,reported_by,reported_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                         (WORKSPACE, s["campaign_id"], s["table_key"], s["row_id"], s["score"], s["tier"], s["method"], ADMIN_EMAIL, s["reported_at"]))
        conn.execute("INSERT INTO lead_platform.selections (id,workspace_id,owner_id,revision,data,archived) VALUES (%s,%s,%s,1,%s,false)",
                     (selection_id, WORKSPACE, ADMIN_SUBJECT, Jsonb(selection_data)))
        conn.execute("INSERT INTO lead_platform.configurations (id,workspace_id,owner_id,revision,data,archived) VALUES (%s,%s,%s,1,%s,false)",
                     (share_id, WORKSPACE, ADMIN_SUBJECT, Jsonb({"emails": [COMMERCIAL_EMAIL], "category": "book_share", "updated_by": "Livrets du mois", "selection_id": selection_id})))
        conn.execute("INSERT INTO lead_platform.monthly_books (workspace_id,owner_email,month,campaign_id,selection_id,share_id,status,data) VALUES (%s,%s,%s,%s,%s,%s,'imported',%s)",
                     (WORKSPACE, COMMERCIAL_EMAIL, studio_month, campaign, selection_id, share_id, Jsonb(book_data)))

    # Logos : fiche de logo et image de chaque entreprise retenue, rangées sous l'espace du studio.
    local_logos = DATA / "documents" / "contact-photos" / hashlib.sha256(WORKSPACE.encode()).hexdigest()[:20] / "logos"
    (local_logos / "images").mkdir(parents=True, exist_ok=True)
    wanted = [c["company_id"] or c["id"] for c in chosen]
    metas = subprocess.run(["ssh", PROD, f"cd {logo_dir} && cat " + " ".join(f"{i}.json" for i in wanted) + " | python3 -c 'import sys,json; d=json.JSONDecoder(); s=sys.stdin.read(); i=0\nwhile i<len(s):\n  s2=s[i:].lstrip()\n  if not s2: break\n  o,n=d.raw_decode(s2); i=len(s)-len(s2)+n; print(json.dumps(o))'"],
                           capture_output=True, text=True, timeout=120)
    digests = set(re.findall(r"[0-9a-f]{64}", metas.stdout))
    files = [f"{i}.json" for i in wanted] + [f"images/{d}.png" for d in digests]
    archive = subprocess.run(["ssh", PROD, f"cd {logo_dir} && tar cf - --ignore-failed-read " + " ".join(files) + " 2>/dev/null"], capture_output=True, timeout=300)
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        tar.extractall(local_logos, filter="data")
    found = sum((local_logos / f"{i}.json").exists() for i in wanted)
    if found != len(wanted):
        fail(f"{len(wanted) - found} logos n'ont pas été copiés.")
    print(f"Studio semé : {len(rows)} prospects pour {COMMERCIAL_EMAIL} ({studio_month}), {len(records['tasks'])} réponses, {found} logos, tirage {seed}.")


if __name__ == "__main__":
    main()

