#!/usr/bin/env python3
"""Drive du studio Bigup : l'instantané en lecture seule du Drive partagé « Bigup · Documents communs ».

Le studio ne reçoit pas la clé Google de l'entreprise (règle 4 du studio). Ce serveur local répond aux lectures que
Bigup fait dans Google Drive (liste d'un dossier, fiche d'un fichier) à partir de data/drive-snapshot.json, lu dans
le vrai Drive par le connecteur Google Drive : mêmes noms, mêmes dossiers, mêmes liens. Toute écriture est refusée.

    python3 drive_double.py <port> <instantané.json>
"""
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

port, path = int(sys.argv[1]), sys.argv[2]
snapshot = json.load(open(path, encoding="utf-8"))
DRIVE = snapshot["drive_id"]
FILES = {f["id"]: f for f in snapshot["files"]}
MINE = {"id": "studio-mes-documents", "name": "Mes documents Bigup", "mimeType": "application/vnd.google-apps.folder",
        "parents": ["root"], "webViewLink": "https://drive.google.com/drive/my-drive", "appProperties": {"bigup": "mes-documents"}}
FOLDER = "application/vnd.google-apps.folder"


def view(item):
    out = {k: v for k, v in item.items() if v is not None}
    out.setdefault("trashed", False)
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(url.query).items()}
        if url.path == "/drive/v3/files":
            q = query.get("q", "")
            parent = re.search(r"'([^']+)' in parents", q)
            if parent:
                pid = parent.group(1)
                kids = [f for f in FILES.values() if pid in (f.get("parents") or [])] if pid != MINE["id"] else []
                kids.sort(key=lambda f: (f["mimeType"] != FOLDER, f["name"].lower()))
                return self.reply(200, {"files": [view(f) for f in kids]})
            # Recherche du dossier « Mes documents Bigup » du membre (propriété d'application).
            return self.reply(200, {"files": [view(MINE)]})
        match = re.fullmatch(r"/drive/v3/files/([^/]+)", url.path)
        if match:
            fid = match.group(1)
            if fid == DRIVE:
                return self.reply(200, {"id": DRIVE, "name": snapshot["drive_name"], "mimeType": FOLDER, "driveId": DRIVE, "trashed": False})
            if fid == MINE["id"]:
                return self.reply(200, view(MINE))
            if fid in FILES:
                return self.reply(200, view(FILES[fid]))
            return self.reply(404, {"error": {"code": 404, "message": "Fichier absent de l'instantané du studio.", "errors": [{"reason": "notFound"}]}})
        return self.reply(404, {"error": {"code": 404, "message": "Lecture inconnue du Drive du studio.", "errors": [{"reason": "notFound"}]}})

    def refuse(self):
        self.reply(403, {"error": {"code": 403, "message": "Le Drive du studio est en lecture seule : rien n'est écrit dans Google Drive.",
                                   "errors": [{"reason": "insufficientFilePermissions"}]}})

    do_POST = do_PATCH = do_PUT = do_DELETE = refuse


ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()

