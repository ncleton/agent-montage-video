from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from common import (
    AUDIO,
    HYPERFRAMES,
    OUTPUT,
    RENDER,
    ROOT,
    WORK,
    ensure_dirs,
    run,
)


def choose_route(request: str) -> str:
    lowered = request.lower()
    if any(token in lowered for token in ("texte", "concept", "projet", "overlay", "vault", "obsidian", "timeline")):
        return "text_overlay_music"
    if any(token in lowered for token in ("musique", "soundtrack", "audio", "rythme")):
        return "music_only"
    if any(token in lowered for token in ("monte", "cut", "coupe", "short", "resume")):
        return "full_edit"
    return "text_overlay_music"


def choose_music_provider(requested: str, music_file: Path | None) -> str:
    """The music source is chosen with the user for each video (see AGENTS.md)."""
    if requested == "elevenlabs" and not os.environ.get("ELEVENLABS_API_KEY"):
        raise SystemExit("ELEVENLABS_API_KEY is missing: run this command through scripts/with_secrets.sh")
    if requested == "file" and (music_file is None or not music_file.is_file()):
        raise SystemExit("--music-provider file needs an existing --music-file")
    return requested


def render_hyperframes_overlay() -> bool:
    overlay = RENDER / "overlay.webm"
    cmd = [
        "npx",
        "--yes",
        "hyperframes",
        "render",
        str(HYPERFRAMES),
        "--format",
        "webm",
        "--fps",
        "24",
        "--quality",
        "draft",
        "--workers",
        "4",
        "--no-low-memory-mode",
        "--browser-timeout",
        "180",
        "--player-ready-timeout",
        "180000",
        "--protocol-timeout",
        "600000",
        "-o",
        str(overlay),
    ]
    try:
        run(cmd)
    except subprocess.CalledProcessError as exc:
        print(f"HyperFrames render failed, falling back to FFmpeg subtitles: {exc}")
        return False
    return overlay.exists() and overlay.stat().st_size > 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--music-provider", choices=["local_procedural", "elevenlabs", "file"], required=True)
    parser.add_argument("--music-file", type=Path, help="Audio file supplied by the user (with --music-provider file)")
    parser.add_argument("--skip-hyperframes", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    video = (ROOT / args.video).resolve()
    if not video.exists():
        raise SystemExit(f"Video not found: {video}")

    route = choose_route(args.request)
    music_file = args.music_file.resolve() if args.music_file else None
    provider = choose_music_provider(args.music_provider, music_file)
    print(f"Route: {route}")
    print(f"Music provider: {provider}")

    run(["python3", "scripts/analyze_video.py", "--video", str(video), "--sample-fps", "1"])
    run(["python3", "scripts/plan_timeline.py", "--request", args.request])
    run(["python3", "scripts/plan_music.py", "--provider", "local_procedural" if provider == "file" else provider])

    music_path = AUDIO / "music.wav"
    if provider == "file":
        run(["ffmpeg", "-y", "-i", str(music_file), "-ar", "48000", "-ac", "2", str(music_path)])
    elif provider == "elevenlabs":
        mp3_path = AUDIO / "elevenlabs_music.mp3"
        run(["python3", "scripts/generate_elevenlabs_music.py", "--output", str(mp3_path)])
        run(["ffmpeg", "-y", "-i", str(mp3_path), "-ar", "48000", "-ac", "2", str(music_path)])
    else:
        run(["python3", "scripts/generate_music.py", "--output", str(music_path)])

    run(["python3", "scripts/build_hyperframes.py"])
    overlay_ok = False if args.skip_hyperframes else render_hyperframes_overlay()
    overlay_arg = str(RENDER / "overlay.webm") if overlay_ok else str(RENDER / "missing-overlay.webm")
    final = OUTPUT / "final.mp4"
    run(
        [
            "python3",
            "scripts/mix_final.py",
            "--video",
            str(video),
            "--music",
            str(music_path),
            "--overlay",
            overlay_arg,
            "--output",
            str(final),
        ]
    )
    run(["python3", "scripts/verify_output.py", "--source", str(video), "--output", str(final)])
    print(f"Done: {final}")


if __name__ == "__main__":
    main()
