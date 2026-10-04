from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
ANALYSIS = WORK / "analysis"
AUDIO = WORK / "audio"
RENDER = WORK / "render"
OUTPUT = ROOT / "output"
HYPERFRAMES = ROOT / "hyperframes-project"


def ensure_dirs() -> None:
    for path in (WORK, ANALYSIS, AUDIO, RENDER, OUTPUT, HYPERFRAMES):
        path.mkdir(parents=True, exist_ok=True)


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd or ROOT, check=check, text=True)


def capture_json(cmd: list[str]) -> dict:
    result = subprocess.run(cmd, cwd=ROOT, check=True, text=True, capture_output=True)
    return json.loads(result.stdout)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ffprobe(path: Path) -> dict:
    return capture_json(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,duration",
            "-of",
            "json",
            str(path),
        ]
    )


def video_metadata(path: Path) -> dict:
    probe = ffprobe(path)
    video = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    audio = next((stream for stream in probe["streams"] if stream["codec_type"] == "audio"), None)
    return {
        "path": str(path),
        "duration": float(probe["format"]["duration"]),
        "width": int(video["width"]),
        "height": int(video["height"]),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name") if audio else None,
        "has_audio": audio is not None,
    }

