#!/usr/bin/env python3
"""Transcribe the final mix in short chunks (long files degrade recognition) with VoiceStudio.

  python3 transcribe_mix.py out/video.mp4 work/final.stt.json [--chunk 60] [--endpoint http://localhost:3900]

Writes {"text": ..., "chunks": [{"start", "text"}]} for check_coverage.py --final-transcript.
Chunks overlap by 2 s so that no word is lost at a boundary.
"""
import argparse, json, os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tts_passages import http, multipart  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--chunk", type=float, default=60.0)
    ap.add_argument("--endpoint", default="http://localhost:3900")
    a = ap.parse_args()
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", a.video]).decode())
    chunks, t = [], 0.0
    with tempfile.TemporaryDirectory() as tmp:
        while t < dur:
            wav = os.path.join(tmp, "c.wav")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.2f" % t, "-t", "%.2f" % (a.chunk + 2), "-i", a.video,
                            "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
            data, ctype = multipart({"model": "whisper-1", "language": "fr", "response_format": "json"}, "file", wav, "audio/wav")
            r = http(a.endpoint.rstrip("/") + "/v1/audio/transcriptions", data, {"Content-Type": ctype})
            if not isinstance(r, dict) or "text" not in r:
                sys.exit("Transcription failed at %.0f s: %s" % (t, str(r)[:300]))
            chunks.append({"start": round(t, 2), "text": r["text"]})
            print("%6.0f s  %s" % (t, r["text"][:80]), flush=True)
            t += a.chunk
    json.dump({"text": " ".join(c["text"] for c in chunks), "chunks": chunks}, open(a.out, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
