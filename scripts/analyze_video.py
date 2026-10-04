from __future__ import annotations

import argparse
import math
import statistics
import subprocess
from pathlib import Path

from common import ANALYSIS, ensure_dirs, video_metadata, write_json


def read_raw_gray_frames(video: Path, *, sample_fps: float, width: int, height: int) -> list[bytes]:
    frame_size = width * height
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video),
        "-vf",
        f"fps={sample_fps},scale={width}:{height},format=gray",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "gray",
        "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    assert proc.stdout is not None
    frames: list[bytes] = []
    while True:
        chunk = proc.stdout.read(frame_size)
        if not chunk:
            break
        if len(chunk) == frame_size:
            frames.append(chunk)
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg frame sampling failed with exit code {proc.returncode}")
    return frames


def mean_abs_diff(a: bytes, b: bytes) -> float:
    total = 0
    for left, right in zip(a, b):
        total += abs(left - right)
    return total / len(a)


def pick_peaks(samples: list[dict], *, max_peaks: int = 10, min_gap: float = 9.0) -> list[dict]:
    diffs = [sample["diff"] for sample in samples if sample["index"] > 0]
    if not diffs:
        return []
    mean = statistics.mean(diffs)
    stdev = statistics.pstdev(diffs) or 1.0
    threshold = max(mean + stdev * 0.9, statistics.quantiles(diffs, n=4)[2])
    candidates = []
    for i in range(1, len(samples) - 1):
        here = samples[i]["diff"]
        if here >= threshold and here >= samples[i - 1]["diff"] and here >= samples[i + 1]["diff"]:
            score = (here - mean) / stdev
            candidates.append({**samples[i], "score": round(score, 3)})
    candidates.sort(key=lambda item: item["score"], reverse=True)
    selected: list[dict] = []
    for candidate in candidates:
        if all(abs(candidate["time"] - other["time"]) >= min_gap for other in selected):
            selected.append(candidate)
        if len(selected) >= max_peaks:
            break
    selected.sort(key=lambda item: item["time"])
    return selected


def analyze(video: Path, sample_fps: float = 1.0) -> dict:
    meta = video_metadata(video)
    width = 96
    height = max(54, int(round(width * meta["height"] / meta["width"])))
    frames = read_raw_gray_frames(video, sample_fps=sample_fps, width=width, height=height)
    samples = []
    previous = None
    for index, frame in enumerate(frames):
        diff = 0.0 if previous is None else mean_abs_diff(previous, frame)
        samples.append(
            {
                "index": index,
                "time": round(index / sample_fps, 3),
                "diff": round(diff, 4),
            }
        )
        previous = frame
    diffs = [sample["diff"] for sample in samples if sample["index"] > 0]
    peaks = pick_peaks(samples)
    return {
        "source": meta,
        "sample_fps": sample_fps,
        "analysis_frame_size": {"width": width, "height": height},
        "summary": {
            "sample_count": len(samples),
            "mean_diff": round(statistics.mean(diffs), 4) if diffs else 0,
            "max_diff": round(max(diffs), 4) if diffs else 0,
            "motion_density": round(sum(1 for diff in diffs if diff > (statistics.mean(diffs) if diffs else math.inf)) / max(len(diffs), 1), 3),
        },
        "peaks": peaks,
        "samples": samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--output", default=str(ANALYSIS / "motion_analysis.json"))
    parser.add_argument("--sample-fps", type=float, default=1.0)
    args = parser.parse_args()
    ensure_dirs()
    data = analyze(Path(args.video), sample_fps=args.sample_fps)
    write_json(Path(args.output), data)
    print(f"Wrote {args.output} with {len(data['peaks'])} motion peaks")


if __name__ == "__main__":
    main()

