#!/bin/sh
# Score du studio Bigup : depuis le 21/11/2026, le serveur calcule seul le score de chaque prospect (row_scores,
# score_engine). Comme en production, il lui faut la liste des clients gagnés (ici le portail HubSpot de test) puis
# un passage de score (score_run). Lancé par start.sh après la plateforme ; relançable à la main.
set -eu
STUDIO_DIR=$(cd "$(dirname "$0")" && pwd)
DATA="$STUDIO_DIR/data"
cd "$DATA"
fail() { echo "Studio Bigup (score) : $1" >&2; exit 1; }
[ -s hubspot-test-token ] || fail "jeton du portail HubSpot de test absent ($DATA/hubspot-test-token) : la liste des clients gagnés ne peut pas être lue."
[ "$(cat hubspot-test-portal 2>/dev/null)" != "6053297" ] || fail "le portail HubSpot du studio est celui de Rossini : refusé."
NODE_BIN=$(command -v node) || fail "Node introuvable : le moteur de score (score_engine.mjs) en a besoin."
run() {
  env -i PATH=/usr/bin:/bin:"$(dirname "$NODE_BIN")" HOME="$HOME" \
    HUBSPOT_ACCESS_TOKEN="$(tr -d '[:space:]' < hubspot-test-token)" \
    LEADGENERATOR_NODE="$NODE_BIN" \
    LEADGENERATOR_DATABASE_URL="postgresql://lead_platform_app:$(cat runtime-password)@127.0.0.1:55810/studio" \
    LEADGENERATOR_GATEWAY_SECRET="$(cat gateway-secret)" \
    LEADGENERATOR_WORKSPACE_ID=studio-bigup LEADGENERATOR_SITE_ID=studio-bigup-site \
    LEADGENERATOR_ADMIN_SUBJECT=studio-admin \
    LEADGENERATOR_HOME="$DATA/home" LEADGENERATOR_DOCUMENT_ROOT="$DATA/documents" \
    venv/bin/python "$@"
}
run -c "
from leadgenerator.platform.auth import Settings
from leadgenerator.platform import won_clients
s = Settings.load()
path = won_clients.cache_path(s.document_root, s.workspace_id)
won_clients._ask(path)
won_clients.refresh_once(s, s.workspace_id)
failure = won_clients._failure(path)
if failure: raise SystemExit('HubSpot de test : ' + str(failure.get('message')))
cache = won_clients.kept(path)
print('Clients gagnés lus dans le portail de test :', len(cache.get('clients') or []), 'le', cache.get('refreshed_at'))
" || fail "lecture des clients gagnés refusée (voir ci-dessus)."
run -m leadgenerator.platform.score_run once || fail "passage de score refusé (voir ci-dessus)."
run -m leadgenerator.platform.score_run measure
