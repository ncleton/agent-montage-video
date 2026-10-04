from __future__ import annotations

import argparse
from pathlib import Path

from common import OUTPUT, ffprobe, run, video_metadata, write_json


def verify(video: Path, source: Path, expected_duration: float | None = None, max_duration: float | None = None) -> dict:
    meta = video_metadata(video)
    source_meta = video_metadata(source)
    probe = ffprobe(video)
    has_video = any(stream["codec_type"] == "video" for stream in probe["streams"])
    has_audio = any(stream["codec_type"] == "audio" for stream in probe["streams"])
    reference_duration = expected_duration if expected_duration is not None else source_meta["duration"]
    duration_delta = abs(meta["duration"] - reference_duration)
    poster = OUTPUT / "preview.jpg"
    run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(max(1, meta["duration"] * 0.45)),
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-update",
            "1",
            "-q:v",
            "2",
            str(poster),
        ]
    )
    duration_ok = duration_delta < 3.0
    if max_duration is not None:
        duration_ok = duration_ok and meta["duration"] <= max_duration
    return {
        "output": str(video),
        "preview": str(poster),
        "size_bytes": video.stat().st_size,
        "duration": meta["duration"],
        "source_duration": source_meta["duration"],
        "reference_duration": reference_duration,
        "duration_delta": duration_delta,
        "has_video": has_video,
        "has_audio": has_audio,
        "passed": video.exists() and video.stat().st_size > 1_000_000 and has_video and has_audio and duration_ok,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT / "final.mp4"))
    parser.add_argument("--source", required=True)
    parser.add_argument("--report", default=str(OUTPUT / "verification.json"))
    parser.add_argument("--expected-duration", type=float)
    parser.add_argument("--max-duration", type=float)
    args = parser.parse_args()
    report = verify(Path(args.output), Path(args.source), args.expected_duration, args.max_duration)
    write_json(Path(args.report), report)
    if not report["passed"]:
        raise SystemExit(f"Verification failed: {report}")
    print(f"Verification passed: {args.output}")


if __name__ == "__main__":
    main()
