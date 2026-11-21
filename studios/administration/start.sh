#!/bin/sh
# Démarre les services préparés pour le tournage sur le Mac mini de montage.
set -eu

studio=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
data="$studio/data"
bigup="$studio/../bigup/data"
node_path=$(command -v node)
umask 077

fail() { printf 'Studio Administration : %s\n' "$*" >&2; exit 1; }
alive() { curl -fsS -m 2 "$1" >/dev/null 2>&1; }
listen() { lsof -n -t -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }
detach() {
  python3 -c 'import os,sys; os.setsid(); os.execvp(sys.argv[1],sys.argv[1:])' "$@"
}
wait_for() {
  remaining=90
  until alive "$1"; do
    remaining=$((remaining - 1))
    if [ "$remaining" -eq 0 ]; then fail "$1 ne répond pas. Consulter $2."; fi
    sleep 1
  done
}

test -f "$data/pgdata/PG_VERSION" || fail "base locale absente. Consulter le README."
for site in admin learning; do
  test -s "$data/$site/dist/server/.dev.vars" || fail "configuration locale du Site $site absente."
done
for name in gateway-secret pg-password plane-secret crm-secret learning.json tls-ca-bundle.pem; do
  test -s "$data/$name" || fail "$name manquant dans data/."
done

hubspot_test=$("$bigup/venv/bin/python" - "$bigup/hubspot-test-token" <<'PY'
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

token = Path(sys.argv[1]).read_text().strip()
request = Request("https://api.hubapi.com/account-info/v3/details", headers={"Authorization": "Bearer " + token})
with urlopen(request, timeout=15) as answer:
    account = json.load(answer)
if account.get("accountType") != "DEVELOPER_TEST" or account.get("portalId") == 6053297:
    sys.exit("Le jeton HubSpot doit appartenir au portail de test du studio.")
print(token)
PY
) || fail "le portail HubSpot de test n’a pas pu être confirmé."

if ! "$bigup/pg/bin/pg_ctl" -D "$data/pgdata" status >/dev/null 2>&1; then
  "$bigup/pg/bin/pg_ctl" -D "$data/pgdata" -o "-p 55820 -k /tmp -c listen_addresses=127.0.0.1" -l "$data/pg.log" -w start >/dev/null
fi

for service in db redis postgrest plane classroom; do
  docker start "oscar-administration-$service" >/dev/null || fail "démarrage Docker refusé pour $service."
done
wait_for http://127.0.0.1:55836/ "docker logs oscar-administration-classroom"
wait_for http://127.0.0.1:55831/rossini_crm_access "docker logs oscar-administration-postgrest"

if ! listen 55829; then
  detach env -i PATH="$(dirname "$node_path"):/usr/bin:/bin" HOME="$data/state/home" "$node_path" \
    --import "$data/crm/mcp-server/node_modules/tsx/dist/loader.mjs" "$studio/crm.mjs" >"$data/crm.log" 2>&1 &
  echo "$!" >"$data/crm.pid"
fi
if ! alive http://127.0.0.1:55823/health; then
  detach env -i PATH=/usr/bin:/bin HOME="$data/state/home" PYTHONPATH="$data/platform/plugins/leadgenerator/src" \
    SSL_CERT_FILE="$data/tls-ca-bundle.pem" LEADGENERATOR_HOME="$data/state/home" \
    LEADGENERATOR_DOCUMENT_ROOT="$data/state/documents" LEADGENERATOR_AO_DATA="$data/state/ao" \
    LEADGENERATOR_DATABASE_URL="postgresql://lead_platform_app:$(cat "$data/pg-password")@127.0.0.1:55820/studio_administration" \
    LEADGENERATOR_GATEWAY_SECRET="$(cat "$data/gateway-secret")" LEADGENERATOR_WORKSPACE_ID=studio-administration \
    LEADGENERATOR_SITE_ID=studio-admin LEADGENERATOR_LINKED_SITE_IDS=studio-learning LEADGENERATOR_ADMIN_SUBJECT=studio-admin \
    LEADGENERATOR_CRM_URL=https://127.0.0.1:55827 LEADGENERATOR_CRM_ADMIN_SECRET="$(cat "$data/crm-secret")" \
    LEADGENERATOR_PLANE_URL=https://127.0.0.1:55826 LEADGENERATOR_PLANE_WORKSPACE=studio \
    LEADGENERATOR_PLANE_ADMIN_SECRET="$(cat "$data/plane-secret")" HUBSPOT_ACCESS_TOKEN="$hubspot_test" \
    "$bigup/venv/bin/python" "$studio/run_platform.py" >"$data/platform-studio.log" 2>&1 &
  echo "$!" >"$data/platform.pid"
fi
wait_for http://127.0.0.1:55823/health "$data/platform-studio.log"

for site in admin learning; do
  port=55821
  [ "$site" != learning ] || port=55822
  # Couverture du sujet de démonstration de la Formation, servie par le Site lui-même (le studio n'a pas internet) :
  # jamais une couverture vide à l'écran (règle 6 du studio de tournage).
  if [ "$site" = learning ]; then
    cp "$studio/assets/studio-sujet-outils-erp.jpg" "$data/learning/dist/client/studio-sujet-outils-erp.jpg"
  fi
  if ! listen "$port"; then
    (
      cd "$data/$site"
      detach env -i PATH="$(dirname "$node_path"):/usr/bin:/bin" HOME="$data/state/home" "$node_path" \
        --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js dev \
        --config dist/server/wrangler.json --local --persist-to .wrangler/state --ip 127.0.0.1 --port "$port" --inspector-port 0 \
        >"$data/site-$site.log" 2>&1 &
      echo "$!" >"$data/site-$site.pid"
    )
  fi
done
if ! listen 55824; then
  detach "$node_path" "$studio/relay.mjs" >"$data/relay.log" 2>&1 &
  echo "$!" >"$data/relay.pid"
fi

for spec in 'ad.rossinienergy.com 55824' 'learning.rossinienergy.com 55825'; do
  set -- $spec
  curl -fsS --retry 12 --retry-connrefused --retry-delay 1 --max-time 5 --cacert "$data/studio-cert.pem" \
    --connect-to "$1:443:127.0.0.1:$2" "https://$1/" >/dev/null || fail "le Site $1 ne répond pas sur le relais local."
done
curl -fsS --max-time 5 --cacert "$data/studio-cert.pem" --connect-to "learning.rossinienergy.com:443:127.0.0.1:55825" \
  -o /dev/null "https://learning.rossinienergy.com/studio-sujet-outils-erp.jpg" || fail "la couverture du sujet n'est pas servie par la Formation du studio."
topic=$(docker exec oscar-administration-db psql -U postgres -d studio_learning -At -c "SELECT id FROM tag WHERE name='Outils de l’ERP'") \
  || fail "sujet « Outils de l’ERP » introuvable dans la Formation du studio."
"$bigup/venv/bin/python" "$studio/topic_image.py" "$topic" >/dev/null || fail "couverture du sujet non posée."
printf '%s\n' 'Studio Administration prêt. Le scénario Playwright doit porter localNetwork.'
