from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from common import AUDIO, WORK, read_json


def generate(brief: dict, output: Path) -> None:
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")

    duration_ms = int(float(brief["duration"]) * 1000)
    prompt = (
        brief["prompt"]
        + f" Tempo around {brief['bpm']} BPM. Instrumental only. "
        + "Create clear energy lifts around these timestamps: "
        + ", ".join(f"{accent['time']:.1f}s {accent['label']}" for accent in brief["accents"][:10])
        + "."
    )
    params = urllib.parse.urlencode({"output_format": "mp3_44100_128"})
    request = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/music/stream?{params}",
        data=json.dumps(
            {
                "prompt": prompt,
                "music_length_ms": max(3000, min(600000, duration_ms)),
                "model_id": "music_v1",
                "force_instrumental": True,
            }
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        },
        method="POST",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            output.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ElevenLabs music generation failed: HTTP {exc.code}: {body}") from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", default=str(WORK / "music_brief.json"))
    parser.add_argument("--output", default=str(AUDIO / "elevenlabs_music.mp3"))
    args = parser.parse_args()
    generate(read_json(Path(args.brief)), Path(args.output))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()

