#!/bin/sh
# Met le studio Bigup au code en production, puis le relance.
#   lockf -k data/tournage.lock ./update.sh <commit du Site RossiniERP> <commit de sales-marketplace>
# Le verrou est partagé par toutes les commandes qui utilisent le studio (README du studio).
set -eu
[ $# -eq 2 ] || { echo "usage : ./update.sh <commit du Site> <commit de la plateforme>" >&2; exit 2; }
SITE_COMMIT=$1 PLATFORM_COMMIT=$2
STUDIO_DIR=$(cd "$(dirname "$0")" && pwd)
DATA="$STUDIO_DIR/data"
fail() { echo "Studio Bigup : $1" >&2; exit 1; }

cd "$DATA/platform"
git fetch -q origin || fail "sales-marketplace injoignable (git fetch)."
git cat-file -e "$PLATFORM_COMMIT^{commit}" 2>/dev/null || fail "commit $PLATFORM_COMMIT absent de sales-marketplace."
cd "$DATA/site"
git fetch -q origin || fail "RossiniERP injoignable (git fetch)."
git cat-file -e "$SITE_COMMIT^{commit}" 2>/dev/null || fail "commit $SITE_COMMIT absent de RossiniERP."

"$STUDIO_DIR/stop.sh"

cd "$DATA/platform"
git checkout -q --detach "$PLATFORM_COMMIT"
uv pip install -q --python "$DATA/venv/bin/python" -e plugins/leadgenerator > "$DATA/update-platform.log" 2>&1 ||
  fail "installation de la plateforme refusée (journal : $DATA/update-platform.log)."

cd "$DATA/site"
git checkout -q --detach "$SITE_COMMIT"
npm ci --no-audit --no-fund > "$DATA/update-site.log" 2>&1 || fail "npm ci du Site refusé (journal : $DATA/update-site.log)."
npm run build >> "$DATA/update-site.log" 2>&1 || fail "construction du Site refusée (journal : $DATA/update-site.log)."

"$STUDIO_DIR/start.sh"
echo "Studio Bigup au Site $(git -C "$DATA/site" rev-parse --short HEAD) et à la plateforme $(git -C "$DATA/platform" rev-parse --short HEAD)."
