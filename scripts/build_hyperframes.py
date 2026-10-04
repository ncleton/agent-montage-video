from __future__ import annotations

import argparse
import html
from pathlib import Path

from common import HYPERFRAMES, WORK, read_json


def event_html(event: dict) -> str:
    start = float(event["time"])
    duration = float(event["duration"])
    title = html.escape(event["title"])
    subtitle = html.escape(event["subtitle"])
    cue_id = html.escape(event["id"])
    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""
    return f"""
      <section id="{cue_id}" class="cue clip" data-start="{start:.3f}" data-duration="{duration:.3f}">
        <div class="copy">
          <h1>{title}</h1>
          {subtitle_html}
        </div>
      </section>
    """


def build(timeline: dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    source = timeline["source"]
    duration = float(source["duration"])
    width = int(source["width"])
    height = int(source["height"])
    cues = "\n".join(event_html(event) for event in timeline["events"])
    html_doc = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Obsidian Vault Overlay</title>
  <style>
    html, body {{
      width: 100%;
      height: 100%;
      margin: 0;
      overflow: hidden;
      background: #00ff00;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    #stage {{
      position: relative;
      width: {width}px;
      height: {height}px;
      overflow: hidden;
      background: #00ff00;
    }}
    .cue {{
      position: absolute;
      left: 7%;
      right: 7%;
      bottom: 9%;
      display: flex;
      align-items: center;
      opacity: 0;
      transform: translate3d(0, 10px, 0);
      color: #172033;
      text-shadow: 0 1px 0 rgba(255,255,255,0.96), 0 8px 22px rgba(31,41,55,0.13);
    }}
    .copy {{
      max-width: 820px;
      padding: 14px 20px 16px;
      border-left: 5px solid rgba(14, 165, 233, 0.72);
      background: linear-gradient(90deg, rgba(255,255,255,0.86), rgba(255,255,255,0.58), rgba(255,255,255,0));
      backdrop-filter: blur(3px);
    }}
    h1 {{
      margin: 0;
      font-size: 52px;
      line-height: 0.98;
      letter-spacing: 0;
      font-weight: 760;
    }}
    p {{
      margin: 0;
      max-width: 720px;
      font-size: 24px;
      line-height: 1.2;
      letter-spacing: 0;
      color: rgba(31, 41, 55, 0.86);
    }}
  </style>
</head>
<body>
  <main id="stage" data-composition-id="obsidian-overlay" data-start="0" data-duration="{duration:.3f}" data-width="{width}" data-height="{height}">
    {cues}
  </main>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js"></script>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    document.querySelectorAll('.cue').forEach((cue, index) => {{
      const start = Number(cue.dataset.start || 0);
      const duration = Number(cue.dataset.duration || 5);
      tl.to(cue, {{ opacity: 1, y: 0, duration: 0.28, ease: 'power1.out' }}, start);
      tl.to(cue, {{ opacity: 0, y: -6, duration: 0.28, ease: 'power1.in' }}, start + duration - 0.28);
    }});
    window.__timelines = window.__timelines || {{}};
    window.__timelines['obsidian-overlay'] = tl;
  </script>
</body>
</html>
"""
    path = output_dir / "index.html"
    path.write_text(html_doc, encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeline", default=str(WORK / "timeline.json"))
    parser.add_argument("--output-dir", default=str(HYPERFRAMES))
    args = parser.parse_args()
    path = build(read_json(Path(args.timeline)), Path(args.output_dir))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
