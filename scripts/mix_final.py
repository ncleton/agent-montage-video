from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from common import OUTPUT, RENDER, WORK, read_json, run


def ass_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"


def write_ass(timeline: dict, output: Path) -> Path:
    width = int(timeline["source"]["width"])
    height = int(timeline["source"]["height"])
    title_size = max(42, int(height * 0.040))
    sub_size = max(24, int(height * 0.023))
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Title,Arial,{title_size},&H002E1F11,&H00FFFFFF,&H00FFFFFF,&H55000000,-1,0,0,0,100,100,0,0,1,5,0,1,115,80,120,1",
        f"Style: Sub,Arial,{sub_size},&H00423831,&H00FFFFFF,&H00FFFFFF,&H55000000,0,0,0,0,100,100,0,0,1,4,0,1,118,90,76,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for event in timeline["events"]:
        start = float(event["time"])
        end = start + float(event["duration"])
        title = str(event["title"]).replace("\n", " ").replace(",", "\\,")
        subtitle = str(event["subtitle"]).replace("\n", " ").replace(",", "\\,")
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Title,,0,0,0,,{{\\fad(160,180)}}{title}")
        if subtitle:
            lines.append(f"Dialogue: 1,{ass_time(start + 0.15)},{ass_time(end)},{'Sub'},,0,0,0,,{{\\fad(180,180)}}{subtitle}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def filter_path(path: Path) -> str:
    value = str(path.resolve())
    return (
        value.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(" ", "\\ ")
        .replace(",", "\\,")
    )


def has_audio(video: Path) -> bool:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            str(video),
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    return bool(result.stdout.strip())


def mix(video: Path, music: Path, timeline: dict, output: Path, overlay: Path | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    duration = float(timeline["source"]["duration"])
    fade_out_start = max(0.0, duration - float(timeline["music_mix"]["fade_out"]))
    source_gain = float(timeline["music_mix"]["source_audio_gain"])
    music_gain = float(timeline["music_mix"]["music_gain"])
    overlay_key_color = str(timeline.get("overlay_key_color", "0x000000"))
    overlay_key_similarity = float(timeline.get("overlay_key_similarity", 0.045))
    overlay_key_blend = float(timeline.get("overlay_key_blend", 0.08))
    ass_path = write_ass(timeline, RENDER / "fallback_overlays.ass")

    if overlay and overlay.exists():
        if has_audio(video):
            filter_complex = (
                f"[2:v]format=rgba,colorkey={overlay_key_color}:{overlay_key_similarity}:{overlay_key_blend}[ov];"
                "[0:v][ov]overlay=0:0:format=auto:eof_action=pass[v];"
                f"[0:a]volume={source_gain}[a0];"
                f"[1:a]volume={music_gain},afade=t=in:st=0:d=2,afade=t=out:st={fade_out_start:.3f}:d={timeline['music_mix']['fade_out']}[a1];"
                "[a0][a1]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-16:TP=-1.5:LRA=11[a]"
            )
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(video),
                "-i",
                str(music),
                "-i",
                str(overlay),
                "-filter_complex",
                filter_complex,
                "-map",
                "[v]",
                "-map",
                "[a]",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                str(output),
            ]
        else:
            filter_complex = (
                f"[2:v]format=rgba,colorkey={overlay_key_color}:{overlay_key_similarity}:{overlay_key_blend}[ov];"
                "[0:v][ov]overlay=0:0:format=auto:eof_action=pass[v];"
                f"[1:a]volume={music_gain},afade=t=in:st=0:d=2,afade=t=out:st={fade_out_start:.3f}:d={timeline['music_mix']['fade_out']},loudnorm=I=-16:TP=-1.5:LRA=11[a]"
            )
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(video),
                "-i",
                str(music),
                "-i",
                str(overlay),
                "-filter_complex",
                filter_complex,
                "-map",
                "[v]",
                "-map",
                "[a]",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                str(output),
            ]
    else:
        video_filter = f"subtitles=filename={filter_path(ass_path)}"
        if has_audio(video):
            filter_complex = (
                f"[0:v]{video_filter}[v];"
                f"[0:a]volume={source_gain}[a0];"
                f"[1:a]volume={music_gain},afade=t=in:st=0:d=2,afade=t=out:st={fade_out_start:.3f}:d={timeline['music_mix']['fade_out']}[a1];"
                "[a0][a1]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-16:TP=-1.5:LRA=11[a]"
            )
        else:
            filter_complex = (
                f"[0:v]{video_filter}[v];"
                f"[1:a]volume={music_gain},afade=t=in:st=0:d=2,afade=t=out:st={fade_out_start:.3f}:d={timeline['music_mix']['fade_out']},loudnorm=I=-16:TP=-1.5:LRA=11[a]"
            )
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-i",
            str(music),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output),
        ]
    run(cmd)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--music", required=True)
    parser.add_argument("--timeline", default=str(WORK / "timeline.json"))
    parser.add_argument("--music-brief", default=str(WORK / "music_brief.json"))
    parser.add_argument("--overlay", default=str(RENDER / "overlay.webm"))
    parser.add_argument("--output", default=str(OUTPUT / "final.mp4"))
    args = parser.parse_args()
    timeline = read_json(Path(args.timeline))
    music_brief = read_json(Path(args.music_brief))
    timeline["music_mix"] = music_brief["mix"]
    overlay = Path(args.overlay)
    mix(Path(args.video), Path(args.music), timeline, Path(args.output), overlay if overlay.exists() else None)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
