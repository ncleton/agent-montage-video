#!/bin/sh
# Semis complet du studio Bigup, dans l'ordre. Le studio doit tourner (./start.sh).
#   seed/all.sh [--seed N]
set -eu
STUDIO_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$STUDIO_DIR"
data/venv/bin/python -u seed/seed_bigup.py --campaign 44ef777d-7624-4180-8f90-f4d4c4fa7b16,045dda50-1c77-4fcc-8f62-a802fbc69774,adb3adc6-d736-4cad-8e5b-66a4cf0c464e "$@"
node seed/seed_tours.mjs
data/venv/bin/python -u seed/seed_hubspot.py
data/venv/bin/python -u seed/seed_finish.py
echo "Semis du studio Bigup terminé."

