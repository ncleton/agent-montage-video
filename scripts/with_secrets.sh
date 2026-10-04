#!/usr/bin/env bash
# Run one command with the agent's API keys stored in LibreAgent (ELEVENLABS_API_KEY,
# MUX_TOKEN_ID, MUX_TOKEN_SECRET). Values only reach that process, in memory.
# Usage: scripts/with_secrets.sh python3 scripts/publish_mux.py --video ... --title ...
set -euo pipefail
exec "${LIBREAGENT_CONNECT:-$HOME/.local/bin/libreagent-connect}" secrets exec --agent "${LIBREAGENT_AGENT_SLUG:-agent-montage-video}" -- "$@"
