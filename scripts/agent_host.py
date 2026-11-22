#!/usr/bin/env python3
"""Poste d'exécution de l'ERP Rossini : prendre les commandes passées à l'agent vidéo et les monter ici.

Règle de l'ERP « commandes entre agents » (rossini-erp 1.20.0, agent-orders.md, critère A25) : un agent de l'ERP
(Apolline en Formation, Margaux aux Appels d'offres) commande une vidéo à Oscar par un bon de commande écrit, validé
par la personne. Ce service, lancé en permanence par launchd (Mac) ou systemd (Linux) sur le poste de montage, prend ces commandes à son tour
avec le jeton du poste, ne reçoit que le paquet de la commande (bon, sources, consignes et skills d'Oscar pour
l'espace), lance Codex dans ce dépôt pour faire la vidéo, garde l'ordinateur éveillé pendant le travail et rend le
résultat mesuré ici, jamais déclaré.

    python3 scripts/agent_host.py serve      # le service (launchd ou systemd : scripts/install_agent_host.sh)
    python3 scripts/agent_host.py status     # configuration, serveurs, places libres
    python3 scripts/agent_host.py report progress --step "Voix" --percent 40 [--eta 1800] [--checkpoint f.json] [--preview img.jpg]
    python3 scripts/agent_host.py report ask --questions questions.json
    python3 scripts/agent_host.py report finish --video out/film.mp4 --mux output/film.mux.json --subtitles work/sous-titres.srt --summary "…" [--check c1="mesure"]
    python3 scripts/agent_host.py report fail --error "raison exacte et ce qu'il faut faire"

Configuration : ~/.config/montage-video/agent-host.json (droits 600), jamais dans le dépôt :
    {"servers": [{"name": "vente", "url": "https://…/leadgenerator-platform", "token": "rah_…"}], "model": "gpt-6.2-sol", "codex_url": "…"}
(model et codex_url facultatifs : par défaut le compte ChatGPT de l'équipe dans Codex, jamais la configuration Codex personnelle du Mac.)
Le jeton d'un poste est donné une seule fois par un administrateur (outil manage_agent_hosts de l'ERP).

« report » se lance depuis Codex, dans le dossier de la commande (projects/commande-<id>/) ou avec
AGENT_HOST_ORDER_DIR : il lit le serveur, l'identifiant et le bail de la commande dans ce dossier. « finish » mesure
lui-même la vidéo (ffprobe), la vérifie image par image (video-frame-review) et lit le lien Mux : le serveur confronte
ces mesures au bon de commande et refuse une fin qui ne le respecte pas. Bibliothèque standard seulement.
"""
from __future__ import annotations

import argparse
import base64
import http.client
import json
import os
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(os.environ.get("AGENT_HOST_CONFIG") or Path.home() / ".config/montage-video/agent-host.json")
LOG = Path.home() / "Library/Logs/rossini-agent-host.log"
VERSION = "1"
POLL_SECONDS = 30
HEARTBEAT_SECONDS = 60
MAX_HOURS = 12
# Which model Oscar works with (Nicolas, 21/11/2026) : the one OpenCodex is set to. agent-host.json says
#   "model": "opencodex"
# and every new order reads, at its start, the model and the proxy address OpenCodex writes in the Codex
# configuration of the Mac (~/.codex/config.toml, « model » and « openai_base_url ») : a model switched in OpenCodex
# is the model of the next order, and the Claude account the proxy picks is the account Oscar uses. An order already
# running keeps the model it started with. A fixed model is still possible ("model" and "codex_url"); without either,
# the team's ChatGPT account.
# A local proxy once sent an order to Anthropic accounts that had reached their limit and the render stopped at
# 74 % (19/11/2026): the computer takes no new order while every account of the model's provider is at its limit
# (provider_quota), and says until when.
DEFAULT_MODEL = "gpt-6.2-sol"
CHATGPT_CODEX_URL = "https://chatgpt.com/backend-api/codex"
CODEX_CONFIG = Path.home() / ".codex/config.toml"
OPENCODEX_QUOTA = Path.home() / ".opencodex/provider-account-quota-cache.json"
QUOTA_LIMIT = 97  # percent of a window used: above it, an account cannot carry a whole render
FRAME_REVIEW = ROOT / "plugins/agent-montage-video/skills/video-frame-review/scripts/detect_inserted.py"


def log(message: str) -> None:
    line = "[%s] %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message)
    print(line, flush=True)


def fail(message: str) -> None:
    sys.exit("agent_host : " + message)


def load_config() -> dict:
    if not CONFIG.is_file():
        fail(f"configuration absente : {CONFIG}. Un administrateur déclare le poste dans l'ERP (manage_agent_hosts) "
             "et écrit le jeton reçu dans ce fichier, droits 600.")
    if CONFIG.stat().st_mode & 0o077:
        fail(f"{CONFIG} est lisible par d'autres comptes : chmod 600 {CONFIG}")
    data = json.loads(CONFIG.read_text())
    servers = data.get("servers")
    if not isinstance(servers, list) or not servers or not all(
        isinstance(s, dict) and s.get("name") and str(s.get("url", "")).startswith("https://") and str(s.get("token", "")).startswith("rah_")
        for s in servers
    ):
        fail(f"{CONFIG} : servers = [{{name, url https://…, token rah_…}}]")
    return data


def _tls():
    try:
        import certifi  # noqa: PLC0415

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


CONNECT_TIMEOUT = 5


def _connect(host: str, port: int, timeout: float) -> socket.socket:
    """First address that answers within 5 s, IPv4 before IPv6: a Mac without a working IPv6 route otherwise waits
    75 s on each call to a server that has an IPv6 address (the sales server), as the platform's remote.py notes."""
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    infos.sort(key=lambda info: info[0] != socket.AF_INET)
    failure: OSError | None = None
    for family, kind, proto, _, address in infos:
        sock = socket.socket(family, kind, proto)
        try:
            sock.settimeout(min(CONNECT_TIMEOUT, timeout))
            sock.connect(address)
            sock.settimeout(timeout)
            return sock
        except OSError as exc:
            sock.close()
            failure = exc
    raise failure or OSError("aucune adresse pour " + host)


class _Connection(http.client.HTTPSConnection):
    def connect(self) -> None:
        self.sock = self._context.wrap_socket(_connect(self.host, self.port, self.timeout), server_hostname=self.host)


class _Handler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_Connection, req, context=self._context)


def _open(request, timeout):
    return urllib.request.build_opener(_Handler(context=_tls())).open(request, timeout=timeout)


class ServerError(RuntimeError):
    def __init__(self, status, code, message):
        super().__init__(f"{status} {code} : {message}")
        self.status, self.code, self.message = status, code, message


def call(server: dict, op: str, body: dict | None = None, timeout: int = 60) -> dict:
    request = urllib.request.Request(
        server["url"].rstrip("/") + "/v1/agent-host/" + op,
        data=json.dumps(body or {}).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + server["token"],
                 "User-Agent": "rossini-agent-host/" + VERSION},
    )
    try:
        with _open(request, timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            error = json.load(exc).get("error") or {}
        except ValueError:
            error = {}
        raise ServerError(exc.code, error.get("code", "http_error"), error.get("message", exc.reason)) from None


def download(server: dict, order: str, lease: str, index: int, target: Path) -> None:
    url = (server["url"].rstrip("/") + f"/v1/agent-host/source/{order}/{index}?" + urllib.parse.urlencode({"lease": lease}))
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + server["token"]})
    try:
        with _open(request, 600) as response, open(target, "wb") as out:
            shutil.copyfileobj(response, out, 1024 * 1024)
    except urllib.error.HTTPError as exc:
        try:
            error = json.load(exc).get("error") or {}
        except ValueError:
            error = {}
        raise ServerError(exc.code, error.get("code", "http_error"), error.get("message", exc.reason)) from None


def machine_info() -> dict:
    info = {"version": VERSION, "hostname": socket.gethostname(), "cpu": os.cpu_count()}
    if sys.platform == "darwin":
        try:
            page = int(subprocess.run(["sysctl", "-n", "hw.pagesize"], capture_output=True, text=True).stdout.strip())
            stats = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
            pages = 0
            for line in stats.splitlines():
                key, _, value = line.partition(":")
                if key.strip() in ("Pages free", "Pages inactive", "Pages speculative", "Pages purgeable"):
                    pages += int(value.strip().rstrip("."))
            info["free_memory_bytes"] = pages * page
            info["gpu"] = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
        except (OSError, ValueError):
            pass
    else:
        # Linux (the agents' VPS, 22/11/2026): memory the kernel can hand out now, and the processor's name (no GPU,
        # software rendering).
        try:
            meminfo = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines() if ":" in line)
            info["free_memory_bytes"] = int(meminfo["MemAvailable"].split()[0]) * 1024
            cpuinfo = Path("/proc/cpuinfo").read_text()
            names = [line.split(":", 1)[1].strip() for line in cpuinfo.splitlines() if line.startswith("model name")]
            if names:
                info["gpu"] = names[0] + " (CPU, rendu logiciel)"
        except (OSError, ValueError, KeyError):
            pass
    # The server takes no order for a computer without room for one more render (a full disk stops it halfway).
    try:
        info["free_disk_bytes"] = shutil.disk_usage(ROOT).free
    except OSError:
        pass
    return info


# --------------------------------------------------------------------------- the service


QUIET_SECONDS = 600


def last_report(folder: Path, started: float) -> float:
    """When Oscar last reported its progress itself (report progress), or when the work started."""
    try:
        return max(started, float((folder / ".progress-at").read_text()))
    except (OSError, ValueError):
        return started


def narration(folder: Path) -> str:
    """Oscar's latest sentence of work in its Codex log (the text after the last « codex » line), 200 characters."""
    try:
        with open(folder / "work/codex.log", "rb") as log_file:
            log_file.seek(0, os.SEEK_END)
            log_file.seek(max(0, log_file.tell() - 200_000))
            text = log_file.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    at = text.rfind("\ncodex\n")
    if at < 0:
        return ""
    lines = []
    for line in text[at + 7 :].splitlines():
        if not line.strip() or line.strip() in ("exec", "codex", "tokens used") or line.startswith("/bin/"):
            break
        lines.append(line.strip())
    said = " ".join(lines).strip().strip("*")
    return (said[:197] + "…") if len(said) > 200 else said


def engine(config: dict) -> tuple[str, str]:
    """The model and the Codex endpoint of the next order: OpenCodex's current choice when the computer follows it."""
    if config.get("model") == "opencodex":
        try:
            codex = tomllib.loads(CODEX_CONFIG.read_text())
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise RuntimeError(f"configuration Codex illisible ({CODEX_CONFIG}) : {exc}") from None
        model, url = codex.get("model"), codex.get("openai_base_url")
        if not isinstance(model, str) or not model or not isinstance(url, str) or not url:
            raise RuntimeError(
                f"OpenCodex n'a pas réglé Codex sur ce Mac ({CODEX_CONFIG} sans model ou openai_base_url) : "
                "relancer OpenCodex, ou fixer model et codex_url dans agent-host.json."
            )
        return model, url
    return config.get("model") or DEFAULT_MODEL, config.get("codex_url") or CHATGPT_CODEX_URL


def provider_quota(model: str) -> str | None:
    """None when the model can take an order now; otherwise why not and until when (every account of the model's
    provider in the OpenCodex proxy at its limit). A stale or unreadable quota record never blocks: the proxy itself
    then decides."""
    if "/" not in model:
        return None
    provider = model.split("/", 1)[0]
    try:
        rows = json.loads(OPENCODEX_QUOTA.read_text()).get("rows", {})
    except (OSError, ValueError):
        return None
    now = time.time() * 1000
    accounts, resets = 0, []
    for key, row in rows.items():
        if key.split("\x00", 1)[0] != provider or not isinstance(row, dict):
            continue
        if now - float(row.get("updatedAt") or 0) > 3 * 3600 * 1000:
            return None
        accounts += 1
        full = [
            float(row[f + "ResetAt"])
            for f in ("fiveHour", "weekly")
            if float(row.get(f + "Percent") or 0) >= QUOTA_LIMIT and float(row.get(f + "ResetAt") or 0) > now
        ]
        if not full:
            return None
        resets.append(max(full))
    if not accounts:
        return None
    until = datetime.fromtimestamp(min(resets) / 1000).strftime("%d/%m à %H h %M")
    return f"comptes {provider} d'OpenCodex à leur limite pour {model} jusqu'au {until} : la commande attend en file"


def order_dir(order_id: str) -> Path:
    return ROOT / "projects" / ("commande-" + order_id)


def _codex_alive(pid: int) -> bool:
    """True while pid is still a Codex started by this service (its own process group, never a reused pid)."""
    try:
        os.kill(pid, 0)
        if os.getpgid(pid) != pid:
            return False
    except (ProcessLookupError, PermissionError):
        return False
    command = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True).stdout
    return "codex" in command and "exec" in command


class _Adopted:
    """A Codex started before the service restarted: still followed (heartbeat, end) instead of left running blind."""

    def __init__(self, pid: int):
        self.pid = pid

    def poll(self):
        return None if _codex_alive(self.pid) else "inconnu"


def prompt(order: dict, folder: Path, resumed: bool) -> str:
    space = order["space"]
    style = order["brief"].get("style", "pixel-rpg")
    lines = [
        f"Tu es {order['to_agent']['name']}, l'agent vidéo de Rossini Energy, sur le poste de montage. "
        f"{order['from_agent']['name']} t'a passé la commande {order['id']} (espace {space}), validée par la personne.",
        f"Le bon de commande, tes consignes et tes skills pour cet espace sont dans {folder}/order.json ; les sources "
        f"téléchargées dans {folder}/sources/. Travaille dans {folder} (work/, out/).",
        "Suis l'AGENTS.md de ce dépôt (voix VoiceStudio, rendu par tranches, 4K, vérification image par image) et, "
        f"pour le style, styles/{style}/README.md s'il existe. Pour une vidéo pédagogique, le skill motion-explainer "
        "(et meet-video-pedagogique pour une réunion enregistrée) ; aux Appels d'offres, le skill d'Oscar fourni dans "
        "order.json.",
        "Règles de la commande : " + order.get("rules", ""),
        "Applique chaque valeur par défaut listée dans order.json (defaults) et cite-la dans le résumé final.",
        "À chaque étape (script, voix, maquette, rendu, vérification), et au moins toutes les 10 minutes, la personne "
        "suit ta carte d'avancement : python3 scripts/agent_host.py report progress --step \"une phrase simple de ce "
        "que tu fais\" --percent N [--eta secondes] [--checkpoint work/checkpoint.json] [--preview une-image.jpg].",
        "Une seule série de questions bloquantes au plus, à la personne, seulement si aucune valeur par défaut ne règle "
        "la décision : écris-les dans work/questions.json ([{text, why, choices:[…]}]) puis python3 scripts/agent_host.py "
        "report ask --questions work/questions.json, et arrête-toi : la commande reprendra avec les réponses.",
        "Publication : une fois la vidéo rendue et vérifiée, scripts/with_secrets.sh python3 scripts/publish_mux.py "
        "--video out/<film>.mp4 --title \"<titre du bon>\" --metadata-output out/<film>.mux.json.",
        "Fin : python3 scripts/agent_host.py report finish --video out/<film>.mp4 --mux out/<film>.mux.json "
        "--subtitles work/<sous-titres>.srt --summary \"ce qui a été fait, les valeurs par défaut appliquées, les sources "
        "utilisées\" [--check c1=\"mesure\" pour chaque critère ajouté]. Le script mesure la vidéo lui-même ; si le "
        "serveur refuse la fin, corrige et recommence. Si la commande ne peut pas aboutir : report fail --error "
        "\"raison exacte et ce qu'il faut faire\".",
        "Ne pose jamais de question à un autre agent. N'invente aucun chiffre, aucun nom, aucune date absents des sources.",
    ]
    if resumed:
        lines.insert(1, "Reprise : la commande avait été interrompue ou attendait une réponse. Lis order.json "
                        "(answers, checkpoint) et le dossier : ne refais pas ce qui est déjà fait.")
    return "\n\n".join(lines)


class Service:
    def __init__(self, config: dict):
        self.config = config
        self.jobs: dict[str, dict] = {}
        self.stop = False

    def start(self, server: dict, order: dict, lease: str) -> None:
        folder = order_dir(order["id"])
        resumed = folder.exists()
        # A Codex left by an earlier service on this order (restart, then pause and claim again) stops first:
        # one order never runs twice on the same folder.
        old = folder / ".pid"
        if old.is_file() and old.read_text().strip().isdigit() and _codex_alive(int(old.read_text())):
            log(f"{order['id']} : arrêt du Codex précédent (pid {old.read_text().strip()}) avant la reprise")
            os.killpg(int(old.read_text()), signal.SIGTERM)
            time.sleep(3)
        for sub in ("sources", "work", "out"):
            (folder / sub).mkdir(parents=True, exist_ok=True)
        (folder / "order.json").write_text(json.dumps({**order, "server": server["name"]}, ensure_ascii=False, indent=2))
        state = folder / ".lease"
        state.write_text(json.dumps({"server": server["name"], "id": order["id"], "lease": lease}))
        state.chmod(0o600)
        (folder / ".report").unlink(missing_ok=True)
        for source in order["sources"]:
            if source["kind"] != "file":
                continue
            target = folder / "sources" / f"{source['index']:02d}-{Path(source['filename'] or 'fichier').name}"
            if target.is_file() and target.stat().st_size == source.get("size"):
                continue
            log(f"{order['id']} : téléchargement de {target.name}")
            download(server, order["id"], lease, source["index"], target)
        codex = shutil.which("codex") or str(Path.home() / ".local/bin/codex")
        # macOS: caffeinate keeps the Mac awake during the work. A Linux server never sleeps: Codex runs as is.
        awake = ["caffeinate", "-i", "-s"] if shutil.which("caffeinate") else []
        command = awake + [codex, "exec", "-C", str(ROOT), "--skip-git-repo-check",
                           "--dangerously-bypass-approvals-and-sandbox", "-o", str(folder / "work/derniere-reponse.txt")]
        model, url = engine(self.config)
        command += ["-m", model, "-c", 'openai_base_url="%s"' % url]
        command.append(prompt(order, folder, resumed))
        env = {**os.environ, "AGENT_HOST_ORDER_DIR": str(folder), "AGENT_HOST_CONFIG": str(CONFIG),
               "PATH": str(Path.home() / ".local/bin") + ":/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")}
        out = open(folder / "work/codex.log", "a")
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
        (folder / ".pid").write_text(str(process.pid))
        self.jobs[order["id"]] = {"server": server, "lease": lease, "process": process, "folder": folder,
                                  "started": time.time(), "beat": time.time(), "log": out}
        (folder / "work/modele.txt").write_text(f"{model} par {url}\n")
        log(f"{order['id']} : pris par ce poste ({'reprise' if resumed else 'nouvelle commande'}), "
            f"modèle {model}, Codex pid {process.pid}")

    def adopt(self) -> None:
        """At start: the Codex still running from before the restart keep their order (heartbeat, end reported)."""
        servers = {s["name"]: s for s in self.config["servers"]}
        for folder in sorted((ROOT / "projects").glob("commande-*")):
            lease_file, pid_file, report = folder / ".lease", folder / ".pid", folder / ".report"
            if not (lease_file.is_file() and pid_file.is_file()) or report.is_file():
                continue
            try:
                state, pid = json.loads(lease_file.read_text()), int(pid_file.read_text().strip())
            except (ValueError, OSError):
                continue
            if state.get("server") not in servers or not _codex_alive(pid):
                continue
            self.jobs[state["id"]] = {"server": servers[state["server"]], "lease": state["lease"],
                                      "process": _Adopted(pid), "folder": folder, "started": time.time(),
                                      "beat": 0.0, "log": open(os.devnull, "a")}
            log(f"{state['id']} : travail en cours repris après le redémarrage du service (Codex pid {pid})")

    def tend(self) -> None:
        for ident, job in list(self.jobs.items()):
            code = job["process"].poll()
            folder = job["folder"]
            if code is None:
                if time.time() - job["started"] > MAX_HOURS * 3600:
                    os.killpg(job["process"].pid, signal.SIGTERM)
                    continue
                if time.time() - job["beat"] >= HEARTBEAT_SECONDS:
                    lease = json.loads((folder / ".lease").read_text())["lease"]
                    beat = {"id": ident, "lease": lease}
                    # The person follows the order on its card: when Oscar has said nothing for 10 minutes, its own
                    # latest sentence of work becomes the step shown (the percentage stays), never a frozen card.
                    said = narration(folder)
                    if said and said != job.get("said") and time.time() - last_report(folder, job["started"]) >= QUIET_SECONDS:
                        beat["step"] = said
                        job["said"] = said
                    try:
                        call(job["server"], "progress", beat)
                    except ServerError as exc:
                        if exc.code == "lease_mismatch":
                            log(f"{ident} : la commande a été annulée ou reprise ailleurs, arrêt du travail")
                            os.killpg(job["process"].pid, signal.SIGTERM)
                    except OSError as exc:
                        log(f"{ident} : serveur injoignable ({exc}), le travail continue")
                    job["beat"] = time.time()
                continue
            job["log"].close()
            del self.jobs[ident]
            reported = (folder / ".report").read_text().strip() if (folder / ".report").exists() else ""
            if reported in ("finish", "fail", "ask"):
                log(f"{ident} : Codex a fini ({reported})")
                continue
            tail = (folder / "work/codex.log").read_text(errors="replace")[-1200:] if (folder / "work/codex.log").exists() else ""
            error = (f"Le travail s'est arrêté sans résultat (Codex, code {code}) sur le poste de montage. "
                     "Fin du journal : " + " ".join(tail.split())[-900:])
            lease = json.loads((folder / ".lease").read_text())["lease"]
            try:
                call(job["server"], "fail", {"id": ident, "lease": lease, "error": error})
                log(f"{ident} : échec rendu au serveur")
            except (ServerError, OSError) as exc:
                log(f"{ident} : échec non rendu ({exc}) ; la commande passera en pause puis reprendra")

    def poll(self) -> None:
        info = machine_info()
        try:
            waiting = provider_quota(engine(self.config)[0])
        except RuntimeError as exc:
            waiting = str(exc)
        if waiting and waiting != getattr(self, "_waiting", None):
            log("poste de montage : " + waiting)
        self._waiting = waiting
        for server in self.config["servers"]:
            try:
                hello = call(server, "hello", {"info": info})
            except (ServerError, OSError) as exc:
                log(f"{server['name']} : {exc}")
                continue
            if hello.get("slots", 0) <= 0 or waiting:
                continue
            try:
                claimed = call(server, "claim")
            except (ServerError, OSError) as exc:
                log(f"{server['name']} : prise impossible ({exc})")
                continue
            if claimed.get("order"):
                try:
                    self.start(server, claimed["order"], claimed["lease"])
                except (ServerError, OSError, RuntimeError) as exc:
                    log(f"{claimed['order']['id']} : départ impossible ({exc})")
                    try:
                        call(server, "fail", {"id": claimed["order"]["id"], "lease": claimed["lease"],
                                              "error": f"Le poste de montage n'a pas pu préparer la commande : {exc}"})
                    except (ServerError, OSError):
                        pass

    def serve(self) -> None:
        signal.signal(signal.SIGTERM, lambda *_: setattr(self, "stop", True))
        log("poste de montage : service démarré (" + ", ".join(s["name"] for s in self.config["servers"]) + ")")
        self.adopt()
        last = 0.0
        while not self.stop:
            self.tend()
            if time.time() - last >= POLL_SECONDS:
                self.poll()
                last = time.time()
            time.sleep(5)
        log("poste de montage : arrêt demandé ; les travaux en cours continuent et seront suivis au redémarrage")


# --------------------------------------------------------------------------- report (called by Codex)


def current() -> tuple[dict, dict, Path]:
    folder = Path(os.environ.get("AGENT_HOST_ORDER_DIR") or Path.cwd())
    state_file = folder / ".lease"
    if not state_file.is_file():
        fail(f"aucune commande dans {folder} : lancez report depuis projects/commande-<id>/ ou avec AGENT_HOST_ORDER_DIR")
    state = json.loads(state_file.read_text())
    config = load_config()
    server = next((s for s in config["servers"] if s["name"] == state["server"]), None)
    if not server:
        fail(f"serveur {state['server']} absent de {CONFIG}")
    return state, server, folder


def probe(video: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:format=duration", "-of", "json", str(video)],
                         capture_output=True, text=True)
    if out.returncode:
        fail("ffprobe ne lit pas " + str(video) + " : " + out.stderr.strip()[:300])
    data = json.loads(out.stdout)
    stream = (data.get("streams") or [{}])[0]
    return {"width": stream.get("width"), "height": stream.get("height"),
            "duration_s": round(float(data["format"]["duration"]), 2)}


def frame_review(video: Path, folder: Path) -> dict:
    python = ROOT / ".venv/bin/python"
    target = folder / "work/frame-review.json"
    run = subprocess.run([str(python if python.exists() else sys.executable), str(FRAME_REVIEW), str(video), "--json", str(target)],
                         capture_output=True, text=True)
    if not target.is_file():
        fail("vérification image par image impossible : " + (run.stderr or run.stdout).strip()[-400:])
    data = json.loads(target.read_text())
    return {"frames": data["frames"], "isolated_jumps": len(data["flagged"]), "defects": len(data["flagged"]),
            "flagged": data["flagged"][:50]}


def subtitles(path: Path | None) -> tuple[bool, str]:
    if not path:
        return False, "aucun fichier de sous-titres"
    if not path.is_file() or path.stat().st_size == 0:
        fail(f"fichier de sous-titres absent ou vide : {path}")
    text = path.read_text(errors="replace")
    count = sum(1 for line in text.splitlines() if "-->" in line)
    if count == 0:
        fail(f"{path} ne contient aucune réplique (lignes « --> »)")
    return True, f"{path.name}, {count} répliques"


def report(args) -> None:
    state, server, folder = current()
    body = {"id": state["id"], "lease": state["lease"]}
    if args.op == "progress":
        (folder / ".progress-at").write_text(str(time.time()))
        body.update({k: v for k, v in (("step", args.step), ("percent", args.percent), ("eta_s", args.eta)) if v is not None})
        if args.checkpoint:
            body["checkpoint"] = json.loads(Path(args.checkpoint).read_text())
        if args.preview:
            body["preview_base64"] = base64.b64encode(Path(args.preview).read_bytes()).decode()
    elif args.op == "ask":
        body["questions"] = json.loads(Path(args.questions).read_text())
        checkpoint = folder / "work/checkpoint.json"
        if checkpoint.is_file():
            body["checkpoint"] = json.loads(checkpoint.read_text())
    elif args.op == "fail":
        body["error"] = args.error
    elif args.op == "finish":
        order = json.loads((folder / "order.json").read_text())
        video = Path(args.video).resolve()
        mux = json.loads(Path(args.mux).read_text())
        if mux.get("source_sha256") and mux.get("source_file") and Path(mux["source_file"]).resolve() != video:
            fail(f"{args.mux} publie {mux['source_file']}, pas {video} : publiez la vidéo rendue.")
        measured = probe(video)
        review = frame_review(video, folder)
        has_subtitles, subtitle_note = subtitles(Path(args.subtitles) if args.subtitles else None)
        url = mux.get("mp4_url") or mux.get("hls_url")
        target = order["brief"]["duration_s"]
        checks = [
            {"id": "duree", "label": "Durée", "ok": abs(measured["duration_s"] - target) <= 0.15 * target,
             "measured": f"{measured['duration_s']} s pour {target} s visées"},
            {"id": "resolution", "label": "Résolution", "ok": True, "measured": f"{measured['width']} × {measured['height']}"},
            {"id": "sous-titres", "label": "Sous-titres", "ok": has_subtitles, "measured": subtitle_note},
            {"id": "verification-image", "label": "Vérification image par image", "ok": review["isolated_jumps"] == 0,
             "measured": f"{review['frames']} images, {review['isolated_jumps']} isolée(s)"},
        ]
        extra = dict(item.split("=", 1) for item in args.check or [])
        for criterion in order["brief"]["acceptance"]:
            if criterion["id"] in ("duree", "resolution", "sous-titres", "verification-image"):
                continue
            if criterion["id"] not in extra:
                fail(f"critère « {criterion['label']} » sans mesure : --check {criterion['id']}=\"ce qui a été constaté\"")
            checks.append({"id": criterion["id"], "label": criterion["label"], "ok": True, "measured": extra[criterion["id"]]})
        body["result"] = {
            "summary": args.summary,
            "video": {"url": url, "playback_id": mux.get("playback_id"), "thumbnail_url": mux.get("thumbnail_url"),
                      **measured, "subtitles": has_subtitles, "frame_review": review},
            "checks": checks,
        }
    try:
        answer = call(server, args.op, body, timeout=120)
    except ServerError as exc:
        fail(f"le serveur refuse ({exc.code}) : {exc.message}")
    if args.op in ("finish", "fail", "ask"):
        (folder / ".report").write_text(args.op)
    print(json.dumps(answer, ensure_ascii=False))


def status() -> None:
    config = load_config()
    print(f"configuration : {CONFIG}")
    info = machine_info()
    print("poste :", json.dumps(info, ensure_ascii=False))
    for server in config["servers"]:
        try:
            hello = call(server, "hello", {"info": info})
            print(f"{server['name']} : {hello['host']['name']}, agents {', '.join(hello['host']['agents'])}, "
                  f"{hello['slots']} place(s) libre(s), {hello['running']} en cours. {hello['reason']}")
        except (ServerError, OSError) as exc:
            print(f"{server['name']} : {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serve")
    sub.add_parser("status")
    rep = sub.add_parser("report")
    rep.add_argument("op", choices=["progress", "ask", "finish", "fail"])
    rep.add_argument("--step")
    rep.add_argument("--percent", type=int)
    rep.add_argument("--eta", type=int)
    rep.add_argument("--checkpoint")
    rep.add_argument("--preview")
    rep.add_argument("--questions")
    rep.add_argument("--video")
    rep.add_argument("--mux")
    rep.add_argument("--subtitles")
    rep.add_argument("--summary")
    rep.add_argument("--check", action="append")
    rep.add_argument("--error")
    args = parser.parse_args()
    if args.command == "serve":
        Service(load_config()).serve()
    elif args.command == "status":
        status()
    else:
        needed = {"ask": ["questions"], "fail": ["error"], "finish": ["video", "mux", "summary"]}.get(args.op, [])
        missing = [n for n in needed if not getattr(args, n)]
        if missing:
            fail("report " + args.op + " : " + ", ".join("--" + m for m in missing) + " requis")
        report(args)


if __name__ == "__main__":
    main()
