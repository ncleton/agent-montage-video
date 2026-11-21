#!/bin/sh
# Arrête le studio de tournage Bigup (relais, Site, plateforme, Postgres). Les données restent dans data/.
STUDIO_DIR=$(cd "$(dirname "$0")" && pwd)
DATA="$STUDIO_DIR/data"
for name in relay-commercial relay-admin site platform drive; do
  if [ -s "$DATA/$name.pid" ]; then kill "$(cat "$DATA/$name.pid")" 2>/dev/null || true; : > "$DATA/$name.pid"; fi
done
"$DATA/pg/bin/pg_ctl" -D "$DATA/pgdata" -m fast stop >/dev/null 2>&1 || true
echo "Studio Bigup arrêté."

