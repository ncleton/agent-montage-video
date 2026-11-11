#!/usr/bin/env bash
# Lemo-Opuscar film styles (github.com/lemomo-ai/lemo-opuscar, MIT code, CC BY 4.0 demos).
# Usage:
#   scripts/opuscar.sh setup                 clone the library at the reviewed commit into tools/lemo-opuscar, print LIB=<path>
#   scripts/opuscar.sh deps [voice] [music]  install its packages (core: npm, headless Chrome, Python .venv of the library)
#   scripts/opuscar.sh demo <slug>           add one style's demo source and poster (reference only, read after TREATMENT.md)
#   scripts/opuscar.sh instruments <lib>     download a sample library for sampler.py (freepats, karoryfer, salamander, vcsl, vsco2ce, all)
#   scripts/opuscar.sh path                  print the library path only
# The library stays pinned: change OPUSCAR_COMMIT after reviewing a newer upstream commit.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OPUSCAR_DIR="$ROOT/tools/lemo-opuscar"
OPUSCAR_REPO="https://github.com/lemomo-ai/lemo-opuscar.git"
OPUSCAR_COMMIT="9eb7739a0fca4c6990fe966cb8b87b1930f7193a"
export PATH="$HOME/.local/bin:$PATH"
export LEMO_OPUSCAR_HOME="$OPUSCAR_DIR"

fail() { echo "opuscar.sh: $*" >&2; exit 1; }

ensure_library() {
  command -v git >/dev/null || fail "git is missing: run scripts/setup_linux.sh --check"
  if [ ! -d "$OPUSCAR_DIR/.git" ]; then
    [ ! -e "$OPUSCAR_DIR" ] || fail "$OPUSCAR_DIR exists but is not a git clone; move it away and run again"
    echo "downloading Lemo-Opuscar $OPUSCAR_COMMIT into $OPUSCAR_DIR" >&2
    git clone --quiet --filter=blob:none --sparse --no-checkout "$OPUSCAR_REPO" "$OPUSCAR_DIR" \
      || fail "could not clone $OPUSCAR_REPO (network?)"
    # same checkout as the upstream skill: guides, core/ and every STYLE.md; demo sources come with 'demo <slug>'
    (cd "$OPUSCAR_DIR" && git sparse-checkout set --no-cone '/*' '!/styles/*/demo/' '!/styleboard/' '!/docs/frames/' \
      '!/docs/cover.jpg' '!/docs/opuscar98.jpg' '!/styles/*/poster.jpg')
    git -C "$OPUSCAR_DIR" reset --quiet --hard "$OPUSCAR_COMMIT" 2>/dev/null \
      || { git -C "$OPUSCAR_DIR" fetch --quiet origin "$OPUSCAR_COMMIT" && git -C "$OPUSCAR_DIR" reset --quiet --hard "$OPUSCAR_COMMIT"; } \
      || fail "commit $OPUSCAR_COMMIT not found upstream"
  fi
  if [ "$(git -C "$OPUSCAR_DIR" rev-parse HEAD 2>/dev/null || true)" != "$OPUSCAR_COMMIT" ]; then
    git -C "$OPUSCAR_DIR" cat-file -e "$OPUSCAR_COMMIT^{commit}" 2>/dev/null \
      || git -C "$OPUSCAR_DIR" fetch --quiet origin "$OPUSCAR_COMMIT" \
      || fail "commit $OPUSCAR_COMMIT not found upstream"
    git -C "$OPUSCAR_DIR" checkout --quiet --detach "$OPUSCAR_COMMIT"
  fi
  [ -f "$OPUSCAR_DIR/AGENTS.md" ] && [ -d "$OPUSCAR_DIR/core/render" ] || fail "incomplete checkout in $OPUSCAR_DIR"
}

upstream() { sh "$OPUSCAR_DIR/plugin/skills/lemo-opuscar/scripts/setup.sh" "$@"; }

cmd="${1:-setup}"; [ $# -gt 0 ] && shift
ensure_library
case "$cmd" in
  setup) upstream ;;
  deps) upstream deps "$@" ;;
  demo) [ $# -eq 1 ] || fail "usage: scripts/opuscar.sh demo <slug>  (slugs: $OPUSCAR_DIR/styles/README.md)"; upstream demo "$1" ;;
  instruments) [ $# -ge 1 ] || fail "usage: scripts/opuscar.sh instruments <freepats|karoryfer|salamander|vcsl|vsco2ce|all>"
    cd "$OPUSCAR_DIR" && sh tools/fetch.sh instruments "$@" ;;
  path) echo "$OPUSCAR_DIR" ;;
  *) fail "unknown command '$cmd' (setup, deps, demo, instruments, path)" ;;
esac
