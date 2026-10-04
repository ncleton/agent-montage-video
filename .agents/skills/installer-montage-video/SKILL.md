---
name: installer-montage-video
description: Prepare or check the computer that runs the Montage vidéo agent (ffmpeg, Node.js, Python with Pillow and numpy, headless Chrome libraries) without sudo. Use at the first task of a session, when a render fails because a tool is missing, or when asked to install, repair or check the agent's tools.
---

# Installer les outils du montage vidéo

1. Run `scripts/setup_linux.sh --check` from the agent folder. `READY` means nothing is missing.
2. Otherwise run `scripts/setup_linux.sh`. It installs, without sudo:
   - ffmpeg and ffprobe (static build from johnvansickle.com) into `~/.local/bin`;
   - Node.js 22 (official nodejs.org archive) into `~/.local/node`, linked in `~/.local/bin`;
   - a `.venv` with Pillow and numpy for the `video-frame-review` scripts.
3. Run the check again and report its output as is.

Each later command puts `$HOME/.local/bin` first in `PATH`. Remotion and HyperFrames download
their own headless Chrome on first use (`npx remotion browser ensure` inside a Remotion
project). A `WARN` line about libnss3, libatk, libgbm or libasound means that browser cannot
start: give the exact library name to an administrator of the computer; do not try sudo.

Check command: `scripts/setup_linux.sh --check` must print `READY`.
