"""Routeur du studio Bigup : Valhalla local (graphe Nord-Pas-de-Calais et Picardie), et, seulement pour un trajet qui
sort de ce graphe (une station de ski des Alpes vue depuis l'agence de Lille), une estimation de test à vol d'oiseau
(distance x 1,3 à 80 km/h, tracé droit). Comme les fournisseurs Enrow et FullEnrich de test (studio_enrichment.py), ce
double ne sert qu'au studio : la production calcule sur le graphe de toute la France.

    python3 studio_routing.py <port d'écoute> <port de Valhalla>
"""
import json, math, sys, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN, VALHALLA = int(sys.argv[1]), int(sys.argv[2])
UPSTREAM = f"http://127.0.0.1:{VALHALLA}"


def km(a, b):
    r = 6371.0
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp, dl = p2 - p1, math.radians(b["lon"] - a["lon"])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h)) * 1.3


def polyline6(points):
    out, plat, plon = [], 0, 0
    for lat, lon in points:
        for v, prev in ((round(lat * 1e6), plat), (round(lon * 1e6), plon)):
            d = v - prev
            d = ~(d << 1) if d < 0 else d << 1
            while d >= 0x20:
                out.append(chr((0x20 | (d & 0x1F)) + 63)); d >>= 5
            out.append(chr(d + 63))
        plat, plon = round(lat * 1e6), round(lon * 1e6)
    return "".join(out)


def estimate_route(body):
    locs = body["locations"]
    legs = []
    for a, b in zip(locs, locs[1:]):
        d = km(a, b)
        legs.append({"summary": {"time": d / 80 * 3600, "length": d},
                     "shape": polyline6([(a["lat"], a["lon"]), (b["lat"], b["lon"])]), "maneuvers": []})
    total = {"time": sum(l["summary"]["time"] for l in legs), "length": sum(l["summary"]["length"] for l in legs)}
    return {"trip": {"legs": legs, "summary": total, "status": 0, "units": "kilometers"}}


def estimate_matrix(body, rows=None):
    out = []
    for i, s in enumerate(body["sources"]):
        line = []
        for j, t in enumerate(body["targets"]):
            cell = rows[i][j] if rows else None
            if not cell or cell.get("time") is None:
                d = km(s, t)
                cell = {"time": d / 80 * 3600, "distance": d, "from_index": i, "to_index": j}
            line.append(cell)
        out.append(line)
    return {"sources_to_targets": out, "units": "kilometers"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def forward(self, method, data=None):
        req = urllib.request.Request(UPSTREAM + self.path, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def send(self, status, payload):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def do_GET(self):
        self.send(*self.forward("GET"))

    def do_POST(self):
        data = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        status, raw = self.forward("POST", data)
        path = self.path.split("?")[0]
        try:
            body = json.loads(data)
        except ValueError:
            return self.send(status, raw)
        if path == "/route":
            try:
                value = json.loads(raw)
                ok = status == 200 and all(l.get("shape") for l in value["trip"]["legs"])
            except (ValueError, KeyError, TypeError):
                ok = False
            return self.send(200, raw if ok else estimate_route(body))
        if path == "/sources_to_targets":
            try:
                rows = json.loads(raw)["sources_to_targets"] if status == 200 else None
                if isinstance(rows, dict):
                    return self.send(status, raw)
            except (ValueError, KeyError):
                rows = None
            return self.send(200, estimate_matrix(body, rows))
        self.send(status, raw)


ThreadingHTTPServer(("127.0.0.1", LISTEN), Handler).serve_forever()

