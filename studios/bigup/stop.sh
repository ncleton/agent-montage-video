#!/bin/sh
# Arrête le studio de tournage Bigup (relais, Site, plateforme, Postgres). Les données restent dans data/.
STUDIO_DIR=$(cd "$(dirname "$0")" && pwd)
DATA="$STUDIO_DIR/data"
for name in relay-commercial relay-admin site platform drive enrichment routing-proxy; do
  if [ -s "$DATA/$name.pid" ]; then kill "$(cat "$DATA/$name.pid")" 2>/dev/null || true; : > "$DATA/$name.pid"; fi
done
# Un fichier .pid périmé ne laisse pas un service tourner : arrêter aussi ce qui écoute encore sur les ports du studio
# (wrangler et son workerd compris).
for port in 55811 55812 55813 55814 55815; do
  for pid in $(lsof -nP -tiTCP:$port -sTCP:LISTEN 2>/dev/null); do kill "$pid" 2>/dev/null || true; done
done
pkill -f "wrangler.js dev --config dist/server/wrangler.json --local --persist-to .wrangler/state --ip 127.0.0.1 --port 55812" 2>/dev/null || true
"$DATA/pg/bin/pg_ctl" -D "$DATA/pgdata" -m fast stop >/dev/null 2>&1 || true
echo "Studio Bigup arrêté."

