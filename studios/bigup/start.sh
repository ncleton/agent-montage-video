#!/bin/sh
# Démarre le studio de tournage Bigup sur ce poste : Postgres du studio, plateforme, Site local et relais d'identité.
# Tout écoute sur 127.0.0.1. Aucune variable d'un service extérieur n'est passée (règle 4 du studio).
set -eu
STUDIO_DIR=$(cd "$(dirname "$0")" && pwd)
DATA="$STUDIO_DIR/data"
PG_PORT=55810 PLATFORM_PORT=55811 SITE_PORT=55812 COMMERCIAL_PORT=55813 ADMIN_PORT=55814 DRIVE_PORT=55815
# Chaque service tourne dans sa propre session : il survit au terminal qui a lancé le studio.
detach() { exec python3 -c 'import os,sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' "$@"; }
fail() { echo "Studio Bigup : $1" >&2; exit 1; }
[ -d "$DATA/pgdata" ] && [ -x "$DATA/venv/bin/uvicorn" ] && [ -d "$DATA/site/dist/server" ] || fail "studio non construit ($DATA). Suivre references/studio-erp.md du skill studio-de-tournage."
for secret in gateway-secret runtime-password; do [ -s "$DATA/$secret" ] || fail "secret $DATA/$secret absent."; done

up() { curl -s -m 3 -o /dev/null -w '%{http_code}' "$1" 2>/dev/null || true; }
wait_for() { i=0; while [ "$(up "$1")" = "000" ]; do i=$((i+1)); [ $i -gt "$2" ] && fail "$3 ne répond pas sur $1 (journal : $4)."; sleep 1; done; }

cd "$DATA"
if ! pg/bin/pg_ctl -D pgdata status >/dev/null 2>&1; then
  pg/bin/pg_ctl -D pgdata -o "-p $PG_PORT -k /tmp -c listen_addresses=127.0.0.1" -l pg.log -w start >/dev/null || fail "Postgres ne démarre pas (journal : $DATA/pg.log)."
fi

# Drive du studio : l'instantané en lecture seule du Drive partagé « Bigup · Documents communs ».
[ -s drive-snapshot.json ] || fail "instantané du Drive absent ($DATA/drive-snapshot.json) : le lire avec le connecteur Google Drive (README du studio)."
if [ "$(up http://127.0.0.1:$DRIVE_PORT/drive/v3/files/x)" = "000" ]; then
  detach python3 "$STUDIO_DIR/drive_double.py" $DRIVE_PORT "$DATA/drive-snapshot.json" > drive.log 2>&1 &
  echo $! > drive.pid
  wait_for http://127.0.0.1:$DRIVE_PORT/drive/v3/files/x 20 "Le Drive du studio" "$DATA/drive.log"
fi

# HubSpot : seulement un portail de test développeur (faux leads et rendez-vous), jamais le portail de Rossini.
HUBSPOT_TEST_TOKEN=""
if [ -s hubspot-test-token ]; then
  HUBSPOT_TEST_TOKEN=$(tr -d '[:space:]' < hubspot-test-token)
  account=$(curl -s -m 20 -H "Authorization: Bearer $HUBSPOT_TEST_TOKEN" https://api.hubapi.com/account-info/v3/details) || fail "HubSpot ne répond pas pour vérifier le portail de test."
  printf '%s' "$account" | python3 -c '
import json, sys
a = json.load(sys.stdin)
portal, kind = a.get("portalId"), a.get("accountType")
if portal is None: sys.exit("jeton de test refusé par HubSpot : " + json.dumps(a)[:300])
if int(portal) == 6053297 or kind != "DEVELOPER_TEST":
    sys.exit("le jeton appartient au portail %s (%s) : le studio n accepte qu un compte de test développeur, jamais le portail de Rossini." % (portal, kind))
open("hubspot-test-portal", "w").write(str(portal))
' || fail "portail HubSpot refusé (voir ci-dessus) ; retirer $DATA/hubspot-test-token."
fi

# Schéma de la plateforme au commit du studio, comme deploy.sh le fait avant chaque version (service provision).
env -i PATH=/usr/bin:/bin HOME="$HOME"   LEADGENERATOR_DATABASE_URL="postgresql://postgres:$(cat pg-password)@127.0.0.1:$PG_PORT/studio"   LEADGENERATOR_RUNTIME_PASSWORD="$(cat runtime-password)"   venv/bin/leadgenerator-platform-provision > provision.log 2>&1 || fail "migration de la plateforme refusée (journal : $DATA/provision.log)."

if [ "$(up http://127.0.0.1:$PLATFORM_PORT/health)" = "000" ]; then
  routing=""
  if [ -s "$DATA/valhalla-enabled" ]; then
    ROUTING_PORT=55816
    curl -fsS -m 5 "http://127.0.0.1:$ROUTING_PORT/status" >/dev/null ||
      fail "Valhalla ne répond pas sur 127.0.0.1:$ROUTING_PORT. Lancez ./routing.sh et attendez la fin de la construction du graphe."
    # Le routeur du studio (studio_routing.py) transmet à Valhalla et estime seulement les trajets hors du graphe.
    if [ "$(up http://127.0.0.1:55817/status)" = "000" ]; then
      detach python3 "$STUDIO_DIR/studio_routing.py" 55817 $ROUTING_PORT > routing-proxy.log 2>&1 &
      echo $! > routing-proxy.pid
      wait_for http://127.0.0.1:55817/status 20 "Le routeur du studio" "$DATA/routing-proxy.log"
    fi
    routing="LEADGENERATOR_ROUTING_URL=http://127.0.0.1:55817"
  fi
  # Agenda Google : celui de Nicolas, par la délégation Google Workspace de Bigup (studio_platform.py, Nicolas 22/11/2026).
  google_agenda=""
  [ -s "$DATA/google-agenda-delegation.json" ] && google_agenda="LEADGENERATOR_GOOGLE_AGENDA_KEY=$DATA/google-agenda-delegation.json"
  detach env -i PATH=/usr/bin:/bin HOME="$HOME" \
    ${HUBSPOT_TEST_TOKEN:+HUBSPOT_ACCESS_TOKEN=$HUBSPOT_TEST_TOKEN} \
    ${routing:+"$routing"} \
    ${google_agenda:+"$google_agenda"} \
    ENROW_API_KEY=studio-double FULLENRICH_API_KEY=studio-double \
    LEADGENERATOR_DATABASE_URL="postgresql://lead_platform_app:$(cat runtime-password)@127.0.0.1:$PG_PORT/studio" \
    LEADGENERATOR_GATEWAY_SECRET="$(cat gateway-secret)" \
    LEADGENERATOR_WORKSPACE_ID=studio-bigup LEADGENERATOR_SITE_ID=studio-bigup-site \
    LEADGENERATOR_ADMIN_SUBJECT=studio-admin \
    LEADGENERATOR_HOME="$DATA/home" LEADGENERATOR_DOCUMENT_ROOT="$DATA/documents" \
    venv/bin/python "$STUDIO_DIR/studio_platform.py" $PLATFORM_PORT $DRIVE_PORT > platform.log 2>&1 &
  echo $! > platform.pid
  wait_for http://127.0.0.1:$PLATFORM_PORT/health 60 "La plateforme" "$DATA/platform.log"
fi

# Demandes d'email et de téléphone : l'ouvrier de production, servi par un Enrow de test (studio_enrichment.py).
if ! { [ -s enrichment.pid ] && kill -0 "$(cat enrichment.pid)" 2>/dev/null; }; then
  detach env -i PATH=/usr/bin:/bin HOME="$HOME" ENROW_API_KEY=studio-double FULLENRICH_API_KEY=studio-double \
    LEADGENERATOR_DATABASE_URL="postgresql://lead_platform_app:$(cat runtime-password)@127.0.0.1:$PG_PORT/studio" \
    LEADGENERATOR_GATEWAY_SECRET="$(cat gateway-secret)" \
    LEADGENERATOR_WORKSPACE_ID=studio-bigup LEADGENERATOR_SITE_ID=studio-bigup-site \
    LEADGENERATOR_ADMIN_SUBJECT=studio-admin \
    LEADGENERATOR_HOME="$DATA/home" LEADGENERATOR_DOCUMENT_ROOT="$DATA/documents" \
    venv/bin/python "$STUDIO_DIR/studio_enrichment.py" > enrichment.log 2>&1 &
  echo $! > enrichment.pid
fi

cd "$DATA/site"
umask 077
printf 'LEADGENERATOR_SERVICE_URL=http://127.0.0.1:%s\nLEADGENERATOR_GATEWAY_SECRET=%s\nLEADGENERATOR_WORKSPACE_ID=studio-bigup\nLEADGENERATOR_SITE_ID=studio-bigup-site\n' \
  "$PLATFORM_PORT" "$(cat "$DATA/gateway-secret")" > dist/server/.dev.vars
# Base locale du Site (D1) : ses tables, posées une fois.
if [ ! -f .wrangler/state/studio-d1-ready ]; then
  for migration in drizzle/*.sql; do
    node --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js d1 execute DB --local --persist-to .wrangler/state       --config dist/server/wrangler.json --file "$migration" >/dev/null 2>&1 || fail "migration D1 $migration refusée."
  done
  : > .wrangler/state/studio-d1-ready
fi
if [ "$(up http://127.0.0.1:$SITE_PORT/)" = "000" ]; then
  detach env -i PATH="$(dirname "$(command -v node)"):/usr/bin:/bin" HOME="$HOME" \
    node --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js dev --config dist/server/wrangler.json \
    --local --persist-to .wrangler/state --ip 127.0.0.1 --port $SITE_PORT --inspector-port 0 > "$DATA/site.log" 2>&1 &
  echo $! > "$DATA/site.pid"
  wait_for http://127.0.0.1:$SITE_PORT/ 120 "Le Site" "$DATA/site.log"
fi

cd "$STUDIO_DIR"
for pair in "commercial $COMMERCIAL_PORT" "admin $ADMIN_PORT"; do
  set -- $pair
  if [ "$(up http://127.0.0.1:$2/)" = "000" ]; then
    detach node relay.mjs "$2" "$SITE_PORT" "$1" > "$DATA/relay-$1.log" 2>&1 &
    echo $! > "$DATA/relay-$1.pid"
    wait_for http://127.0.0.1:$2/ 20 "Le relais $1" "$DATA/relay-$1.log"
  fi
done
# Le score de chaque prospect est calculé par le serveur (row_scores) : clients gagnés puis passage de score.
"$STUDIO_DIR/score.sh" > "$DATA/score.log" 2>&1 || fail "score des prospects non calculé (journal : $DATA/score.log)."
echo "Studio Bigup prêt : commercial de démonstration http://127.0.0.1:$COMMERCIAL_PORT (réglage : http://127.0.0.1:$ADMIN_PORT)"

