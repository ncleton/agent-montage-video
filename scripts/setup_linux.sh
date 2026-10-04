#!/usr/bin/env bash
# Prepare a Linux (or macOS) computer for the Montage vidéo agent, without sudo.
# Installs into ~/.local and ./.venv: ffmpeg/ffprobe, Node.js 22, Python Pillow + numpy.
# Usage: scripts/setup_linux.sh          install what is missing, then check
#        scripts/setup_linux.sh --check  only check
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$HOME/.local/bin"
mkdir -p "$BIN"
export PATH="$BIN:$PATH"
OS="$(uname -s)"
ARCH="$(uname -m)"

node_major() { command -v node >/dev/null 2>&1 && node -p 'process.versions.node.split(".")[0]' || echo 0; }

install_ffmpeg() {
  command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1 && return
  [ "$OS" = Linux ] || { echo "ffmpeg missing: install it with the system package manager" >&2; return 1; }
  case "$ARCH" in x86_64) a=amd64 ;; aarch64|arm64) a=arm64 ;; *) echo "No static ffmpeg for $ARCH" >&2; return 1 ;; esac
  tmp="$(mktemp -d)"
  curl -fsSL "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-$a-static.tar.xz" -o "$tmp/ffmpeg.tar.xz"
  tar -xJf "$tmp/ffmpeg.tar.xz" -C "$tmp"
  install -m 755 "$tmp"/ffmpeg-*-static/ffmpeg "$tmp"/ffmpeg-*-static/ffprobe "$BIN/"
}

install_node() {
  [ "$(node_major)" -ge 20 ] && return
  [ "$OS" = Linux ] || { echo "Node.js 20+ missing: install it from nodejs.org" >&2; return 1; }
  case "$ARCH" in x86_64) a=x64 ;; aarch64|arm64) a=arm64 ;; *) echo "No Node.js build for $ARCH" >&2; return 1 ;; esac
  base="https://nodejs.org/dist/latest-v22.x"
  file="$(curl -fsSL "$base/SHASUMS256.txt" | awk -v s="linux-$a.tar.xz" '$2 ~ s"$" {print $2; exit}')"
  [ -n "$file" ] || { echo "Could not find the Node.js 22 archive" >&2; return 1; }
  dest="$HOME/.local/node"
  rm -rf "$dest" && mkdir -p "$dest"
  curl -fsSL "$base/$file" | tar -xJ -C "$dest" --strip-components=1
  for b in node npm npx corepack; do ln -sf "$dest/bin/$b" "$BIN/$b"; done
}

install_python() {
  command -v python3 >/dev/null 2>&1 || { echo "python3 missing" >&2; return 1; }
  if [ ! -x "$ROOT/.venv/bin/python" ]; then
    python3 -m venv "$ROOT/.venv" 2>/dev/null || {
      python3 -m venv --without-pip "$ROOT/.venv"
      curl -fsSL https://bootstrap.pypa.io/get-pip.py | "$ROOT/.venv/bin/python"
    }
  fi
  "$ROOT/.venv/bin/python" -m pip install --quiet --upgrade pillow numpy
}

check() {
  ok=1
  for c in ffmpeg ffprobe node npx python3 git curl; do
    if command -v "$c" >/dev/null 2>&1; then echo "ok  $c"; else echo "MISSING $c"; ok=0; fi
  done
  if [ "$(node_major)" -ge 20 ]; then echo "ok  node $(node -v)"; else echo "MISSING node >= 20"; ok=0; fi
  if "$ROOT/.venv/bin/python" -c 'import PIL, numpy' 2>/dev/null; then echo "ok  .venv (Pillow, numpy)"; else echo "MISSING .venv with Pillow and numpy"; ok=0; fi
  if [ "$OS" = Linux ] && command -v ldconfig >/dev/null 2>&1; then
    for lib in libnss3.so libatk-1.0.so libgbm.so libasound.so; do
      if ldconfig -p 2>/dev/null | grep -q "$lib"; then echo "ok  $lib (headless Chrome)"
      else echo "WARN $lib not found: Remotion/HyperFrames Chrome may not start; an administrator must install it"; fi
    done
  fi
  if [ "$ok" = 1 ]; then echo "READY"; else echo "INCOMPLETE"; return 1; fi
}

if [ "${1:-}" != "--check" ]; then
  install_ffmpeg
  install_node
  install_python
fi
check
