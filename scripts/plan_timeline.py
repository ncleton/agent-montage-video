from __future__ import annotations

import argparse
from pathlib import Path

from common import ANALYSIS, WORK, read_json, write_json


OVERLAYS = [
    ("La mémoire s'ouvre", "Le vault devient un espace de travail vivant"),
    ("Un gros projet arrive", "Les premières structures prennent forme"),
    ("Les concepts se connectent", "Les liens créent une carte exploitable"),
    ("Nouveaux chantiers", "Chaque cluster devient une piste d'action"),
    ("Architecture mentale", "Les idées se rangent, se croisent, se répondent"),
    ("Projets en collision", "La densité augmente sans perdre le fil"),
    ("Système de décision", "La connaissance commence à guider l'exécution"),
    ("Vision consolidée", "Le graphe raconte ce qui compte maintenant"),
    ("Vault opérationnel", "Mémoire, concepts et projets avancent ensemble"),
]


def plan(motion: dict, request: str) -> dict:
    duration = motion["source"]["duration"]
    peaks = motion.get("peaks", [])
    if not peaks:
        fallback_times = [duration * ratio for ratio in (0.08, 0.2, 0.34, 0.5, 0.66, 0.82)]
        peaks = [{"time": round(time, 3), "score": 1.0, "diff": 0.0} for time in fallback_times]

    events = []
    first_time = max(2.0, min(5.0, duration * 0.03))
    event_times = [first_time] + [peak["time"] for peak in peaks]
    final_time = max(duration - 14.0, duration * 0.88)
    event_times.append(final_time)

    deduped: list[float] = []
    for time in sorted(event_times):
        if 2.0 <= time <= duration - 3.0 and all(abs(time - old) > 6.0 for old in deduped):
            deduped.append(time)

    for index, time in enumerate(deduped[: len(OVERLAYS)]):
        title, subtitle = OVERLAYS[index]
        intensity = 0.6
        matching_peak = min(peaks, key=lambda peak: abs(peak["time"] - time)) if peaks else None
        if matching_peak and abs(matching_peak["time"] - time) < 2.0:
            intensity = min(1.0, 0.55 + float(matching_peak.get("score", 1.0)) * 0.12)
        events.append(
            {
                "id": f"cue_{index + 1:02d}",
                "time": round(time, 3),
                "duration": 5.2 if index else 4.4,
                "title": title,
                "subtitle": subtitle,
                "visual_style": "kinetic_obsidian_overlay",
                "music_accent": "impact" if intensity > 0.78 else "lift",
                "intensity": round(intensity, 3),
            }
        )

    return {
        "request": request,
        "source": motion["source"],
        "route": "text_overlay_music",
        "events": events,
        "notes": [
            "Text is synchronized to detected motion peaks.",
            "Music accents should land on event timestamps.",
            "Keep final mix energetic but not aggressive.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--motion", default=str(ANALYSIS / "motion_analysis.json"))
    parser.add_argument("--request", default="")
    parser.add_argument("--output", default=str(WORK / "timeline.json"))
    args = parser.parse_args()
    data = plan(read_json(Path(args.motion)), args.request)
    write_json(Path(args.output), data)
    print(f"Wrote {args.output} with {len(data['events'])} timeline events")


if __name__ == "__main__":
    main()

