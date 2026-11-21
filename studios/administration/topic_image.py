
"""Image du sujet de démonstration de la Formation du studio : jamais une couverture vide à l'écran (règle 6)."""
import hashlib, json, sys
from pathlib import Path
import psycopg
from psycopg.types.json import Jsonb

DATA = Path(__file__).resolve().parent / "data"
WORKSPACE = "studio-administration"
# Image servie en https par la Formation du studio elle-même (le Site n'affiche que les images https, le studio n'a
# pas internet) : assets/studio-sujet-outils-erp.jpg, copiée par start.sh, générée avec ChatGPT image.
IMAGE = "https://learning.rossinienergy.com/studio-sujet-outils-erp.jpg"

def main():
    pw = (DATA / "pg-password").read_text().strip()
    key = "learning_topic_images-" + hashlib.sha256(WORKSPACE.encode()).hexdigest()[:40]
    with psycopg.connect(host="127.0.0.1", port=55820, dbname="studio_administration", user="lead_platform_app", password=pw) as conn:
        row = conn.execute("SELECT data FROM lead_platform.configurations WHERE workspace_id=%s AND id=%s", (WORKSPACE, key)).fetchone()
        topics = sys.argv[1:]
        if not topics:
            sys.exit("studio : donner l'identifiant du sujet (tag ClassroomIO) dont la couverture est vide.")
        images = dict(((row[0] if row else None) or {}).get("images") or {})
        for t in topics:
            images[t] = IMAGE
        conn.execute(
            "INSERT INTO lead_platform.configurations(id,workspace_id,owner_id,data) VALUES(%s,%s,%s,%s)"
            " ON CONFLICT(id) DO UPDATE SET data=EXCLUDED.data, revision=lead_platform.configurations.revision+1, updated_at=now(), archived=false",
            (key, WORKSPACE, "studio-admin", Jsonb({"category": "learning_topic_images", "images": images})),
        )
    print("Couverture posée pour", ", ".join(topics))

if __name__ == "__main__":
    main()

