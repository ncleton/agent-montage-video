from __future__ import annotations

import argparse
from pathlib import Path

from common import WORK, read_json, write_json


def music_brief(timeline: dict, provider: str = "local_procedural") -> dict:
    duration = timeline["source"]["duration"]
    events = timeline["events"]
    density = len(events) / max(duration / 60.0, 0.1)
    bpm = 116 if density < 2.2 else 124 if density < 3.2 else 132
    accents = [
        {
            "time": event["time"],
            "type": event["music_accent"],
            "intensity": event["intensity"],
            "label": event["title"],
        }
        for event in events
    ]
    return {
        "provider": provider,
        "duration": duration,
        "bpm": bpm,
        "mood": "cinematic electronic, focused, accelerating, knowledge graph timelapse",
        "instruments": ["warm sub pulse", "glass arpeggio", "soft impact drums", "rising noise", "wide synth pad"],
        "structure": [
            {"start": 0, "end": round(duration * 0.18, 3), "energy": 0.32, "label": "opening memory"},
            {"start": round(duration * 0.18, 3), "end": round(duration * 0.52, 3), "energy": 0.58, "label": "projects appear"},
            {"start": round(duration * 0.52, 3), "end": round(duration * 0.82, 3), "energy": 0.78, "label": "concept network"},
            {"start": round(duration * 0.82, 3), "end": round(duration, 3), "energy": 0.64, "label": "resolution"},
        ],
        "accents": accents,
        "mix": {
            "music_gain": 0.86,
            "source_audio_gain": 0.22,
            "fade_in": 2.0,
            "fade_out": 5.0,
            "target_lufs": -16,
        },
        "prompt": (
            "Instrumental cinematic electronic soundtrack for a timelapse of an Obsidian knowledge vault growing. "
            "Pulse follows fast visual changes, with clear but elegant peaks on project/concept reveal moments. "
            "No vocals. Modern, focused, expansive, not dark."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeline", default=str(WORK / "timeline.json"))
    parser.add_argument("--provider", default="local_procedural")
    parser.add_argument("--output", default=str(WORK / "music_brief.json"))
    args = parser.parse_args()
    data = music_brief(read_json(Path(args.timeline)), provider=args.provider)
    write_json(Path(args.output), data)
    print(f"Wrote {args.output} at {data['bpm']} BPM using {data['provider']}")


if __name__ == "__main__":
    main()

