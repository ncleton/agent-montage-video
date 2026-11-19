#!/usr/bin/env bash
# Run one command with the agent's API keys, read from local files (chmod 600) in
# ~/.config/montage-video (or MONTAGE_SECRETS_DIR):
#   mux_tokens          MUX_TOKEN_ID=... and MUX_TOKEN_SECRET=... (Mux Rossini Energy, env Outil AO)
#   elevenlabs_api_key  the ElevenLabs key alone
# Values only reach that process, in memory.
# Usage: scripts/with_secrets.sh python3 scripts/publish_mux.py --video ... --title ...
set -euo pipefail
secrets_dir="${MONTAGE_SECRETS_DIR:-$HOME/.config/montage-video}"
if [[ -f "$secrets_dir/mux_tokens" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$secrets_dir/mux_tokens"
  set +a
fi
if [[ -f "$secrets_dir/elevenlabs_api_key" ]]; then
  ELEVENLABS_API_KEY="$(tr -d '[:space:]' < "$secrets_dir/elevenlabs_api_key")"
  export ELEVENLABS_API_KEY
fi
exec "$@"
