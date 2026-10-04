#!/usr/bin/env bash
# Start the openvid editor (screen-recording demos, zooms, device mockups).
# Usage: scripts/openvid.sh [port]   then open http://localhost:<port>/en/editor
# The first run clones openvid at the reviewed commit into tools/openvid.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OPENVID_DIR="$ROOT/tools/openvid"
OPENVID_COMMIT="03ea5ae"
OPENVID_PORT="${1:-3077}"
export PATH="$HOME/.local/bin:$PATH"
if [ ! -d "$OPENVID_DIR/.git" ]; then
  git clone --quiet https://github.com/CristianOlivera1/openvid "$OPENVID_DIR"
  git -C "$OPENVID_DIR" checkout --quiet "$OPENVID_COMMIT"
  printf 'NEXT_PUBLIC_SITE_URL=http://localhost:%s\nNEXT_TELEMETRY_DISABLED=1\n' "$OPENVID_PORT" > "$OPENVID_DIR/.env.local"
fi
cd "$OPENVID_DIR"
if [ ! -d node_modules ]; then
  COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm install
fi
if (exec 3<>"/dev/tcp/127.0.0.1/$OPENVID_PORT") 2>/dev/null; then
  echo "openvid already running: http://localhost:$OPENVID_PORT/en/editor"
  exit 0
fi
echo "openvid: http://localhost:$OPENVID_PORT/en/editor"
exec env NEXT_TELEMETRY_DISABLED=1 COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm exec next dev -p "$OPENVID_PORT"
