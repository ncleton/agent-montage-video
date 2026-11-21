#!/usr/bin/env python3
"""Plan de caméra d'un tutoriel d'interface : zoomer là où la personne agit, puis revenir à l'écran entier.

Entrée : le journal d'un tournage au format TimelineData de webreel (fps, width, height, zoom, frames[].cursor,
events[] click|key avec timeMs), celui que le studio de tournage enregistre. Les positions du curseur y sont en
pixels CSS ; la vidéo fait width x height pixels (zoom = densité, 2 pour la 4K).

Sortie : camera.json, des images clés {frame, scale, x, y} (x, y = centre visé en pixels de la vidéo) que la
composition Remotion du kit tuto-interface interpole avec un amorti. Règles (skill studio-de-tournage) :
- une action (clic, frappe) groupée avec ses voisines proches dans le temps et l'espace forme un plan ;
- le zoom arrive avant l'action (le spectateur voit où l'on va cliquer) et reste tant que l'action dure ;
- il sort quand l'écran entier redevient utile, ou glisse directement vers le plan suivant s'il est proche ;
- le cadre ne sort jamais de l'image et montre en entier l'élément touché et ce qu'il ouvre (panneau, fenêtre,
  fiche, enregistrés par studio_record.mjs) ; au-delà des deux tiers de l'écran, pas de zoom.

    python3 scripts/studio_camera.py timeline.json camera.json [--scale 1.6] [--lead 0.9] [--hold 1.1]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path


def cluster_events(events, cursor, fps, gap_s, near_px):
    """Actions voisines dans le temps (gap_s) et dans l'espace (near_px, pixels CSS) : un seul plan."""
    groups = []
    for e in sorted((e for e in events if e.get("type") in ("click", "key")), key=lambda e: e["timeMs"]):
        f = min(len(cursor) - 1, max(0, round(e["timeMs"] / 1000 * fps)))
        x, y = cursor[f]["x"], cursor[f]["y"]
        if x < 0 or y < 0:
            continue
        point = (f, x, y)
        if groups:
            last = groups[-1][-1]
            if (f - last[0]) / fps <= gap_s and abs(x - last[1]) <= near_px and abs(y - last[2]) <= near_px:
                groups[-1].append(point)
                continue
        groups.append([point])
    return groups


def plan(timeline: dict, scale: float, lead_s: float, hold_s: float, ease_s: float) -> dict:
    fps, width, height, zoom = timeline["fps"], timeline["width"], timeline["height"], timeline.get("zoom", 1)
    cursor = [f["cursor"] for f in timeline["frames"]]
    total = len(cursor)
    if not total:
        sys.exit("studio_camera : le journal ne contient aucune image (frames vide) : refaire le tournage.")
    css_w, css_h = width / zoom, height / zoom
    groups = cluster_events(timeline.get("events", []), cursor, fps, gap_s=1.8, near_px=0.3 * css_w)
    ease, lead, hold = round(ease_s * fps), round(lead_s * fps), round(hold_s * fps)

    events = timeline.get("events", [])
    boxes = [(round(e["timeMs"] / 1000 * fps), e["box"]) for e in events if e.get("box")]
    views = [(round(e["timeMs"] / 1000 * fps), e.get("box")) for e in events if e.get("type") == "view"]

    def shot(group):
        """Le cadre montre en entier ce que le geste touche et ce qu'il ouvre ; jamais un élément coupé."""
        xs, ys = [p[1] for p in group], [p[2] for p in group]
        first, last = group[0][0], group[-1][0] + hold
        region = [(min(xs), min(ys), max(xs), max(ys))]
        region += [(b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]) for f, b in boxes if first - 2 <= f <= last]
        region += [(b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]) for f, b in views if b and first <= f <= last]
        x0, y0 = min(r[0] for r in region), min(r[1] for r in region)
        x1, y1 = max(r[2] for r in region), max(r[3] for r in region)
        span_w, span_h = max(x1 - x0, 0.25 * css_w), max(y1 - y0, 0.25 * css_h)
        if span_w > 0.66 * css_w or span_h > 0.66 * css_h:
            s = 1.0  # une fiche, une fenêtre ou un panneau qui prend l'écran se montre en entier, sans zoom
        else:
            s = max(1.0, min(scale, 0.86 * css_w / span_w, 0.86 * css_h / span_h))
        cx, cy = (x0 + x1) / 2 * zoom, (y0 + y1) / 2 * zoom
        half_w, half_h = width / (2 * s), height / (2 * s)
        cx = min(max(cx, half_w), width - half_w)
        cy = min(max(cy, half_h), height - half_h)
        start = max(0, group[0][0] - lead)
        end = min(total - 1, group[-1][0] + hold)
        return {"start": start, "end": end, "scale": round(s, 3), "x": round(cx, 1), "y": round(cy, 1)}

    shots = [shot(g) for g in groups]
    full = {"scale": 1.0, "x": width / 2, "y": height / 2}
    keys = [{"frame": 0, **full}]
    for i, s in enumerate(shots):
        arrive = s["start"] + ease
        prev = keys[-1]
        if s["start"] <= prev["frame"]:
            # Suite directe du plan précédent : glisser vers ce plan sans repasser par l'écran entier.
            s["start"] = prev["frame"]
            arrive = s["start"] + ease
        else:
            keys.append({"frame": s["start"], **{k: prev[k] for k in ("scale", "x", "y")}})
        keys.append({"frame": min(arrive, total - 1), "scale": s["scale"], "x": s["x"], "y": s["y"]})
        keys.append({"frame": max(min(s["end"], total - 1), keys[-1]["frame"]), "scale": s["scale"], "x": s["x"], "y": s["y"]})
        nxt = shots[i + 1] if i + 1 < len(shots) else None
        if nxt and nxt["start"] - s["end"] <= round(1.5 * fps):
            nxt["start"] = keys[-1]["frame"]
            continue
        out = min(keys[-1]["frame"] + ease, total - 1)
        if out > keys[-1]["frame"]:
            keys.append({"frame": out, **full})
    if keys[-1]["frame"] < total - 1:
        keys.append({"frame": total - 1, **{k: keys[-1][k] for k in ("scale", "x", "y")}})
    # Images clés strictement croissantes (Remotion l'exige pour interpoler).
    clean = []
    for k in keys:
        if clean and k["frame"] <= clean[-1]["frame"]:
            clean[-1] = k if k["frame"] == clean[-1]["frame"] else clean[-1]
            continue
        clean.append(k)
    return {"fps": fps, "width": width, "height": height, "frames": total, "shots": len(shots), "keyframes": clean}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("timeline", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--scale", type=float, default=1.6, help="zoom maximal sur une action (1.6 par défaut)")
    ap.add_argument("--lead", type=float, default=0.9, help="secondes de zoom avant l'action")
    ap.add_argument("--hold", type=float, default=1.1, help="secondes gardées après la dernière action du plan")
    ap.add_argument("--ease", type=float, default=0.6, help="durée d'un mouvement de caméra en secondes")
    a = ap.parse_args()
    if not a.timeline.is_file():
        sys.exit(f"studio_camera : journal introuvable : {a.timeline}")
    result = plan(json.loads(a.timeline.read_text()), a.scale, a.lead, a.hold, a.ease)
    a.output.write_text(json.dumps(result, indent=1))
    print(f"{result['shots']} plan(s), {len(result['keyframes'])} images clés, {result['frames']} images -> {a.output}")


if __name__ == "__main__":
    main()

