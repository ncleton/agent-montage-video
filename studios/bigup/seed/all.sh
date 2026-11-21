#!/bin/sh
# Semis complet du studio Bigup, dans l'ordre. Le studio doit tourner (./start.sh).
#   seed/all.sh [--seed N]
set -eu
STUDIO_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$STUDIO_DIR"
data/venv/bin/python -u seed/seed_bigup.py "$@"
node seed/seed_tours.mjs
data/venv/bin/python -u seed/seed_hubspot.py
data/venv/bin/python -u seed/seed_finish.py
echo "Semis du studio Bigup terminé."

