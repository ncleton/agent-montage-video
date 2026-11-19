#!/usr/bin/env bash
# Local, pinned HyperFrames CLI. No implicit npx download or engine substitution.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE="$ROOT/tools/hyperframes"
CLI="$ENGINE/node_modules/hyperframes/bin/hyperframes.mjs"

command -v node >/dev/null || { echo 'Node.js absent : lancer scripts/setup_linux.sh.' >&2; exit 1; }
node -e 'if (Number(process.versions.node.split(".")[0]) < 22) { console.error("HyperFrames nécessite Node.js 22 ou plus : lancer scripts/setup_linux.sh."); process.exit(1); }'

if [[ "${1:-}" == "--install" ]]; then
  command -v npm >/dev/null || { echo 'npm absent : lancer scripts/setup_linux.sh.' >&2; exit 1; }
  npm ci --prefix "$ENGINE" --no-fund --no-audit
  node "$CLI" browser ensure
  exit 0
fi

[[ -f "$CLI" ]] || { echo 'HyperFrames absent : lancer scripts/hyperframes.sh --install.' >&2; exit 1; }
node - "$ENGINE" <<'JS'
const fs = require('node:fs');
const path = require('node:path');
const root = process.argv[2];
const deps = JSON.parse(fs.readFileSync(path.join(root, 'package.json'))).dependencies;
for (const [name, expected] of Object.entries(deps)) {
  const file = path.join(root, 'node_modules', name, 'package.json');
  if (!fs.existsSync(file) || JSON.parse(fs.readFileSync(file)).version !== expected) {
    console.error(`Dépendance ${name} absente ou version différente de ${expected} : lancer scripts/hyperframes.sh --install.`);
    process.exit(1);
  }
}
JS
exec node "$CLI" "$@"
