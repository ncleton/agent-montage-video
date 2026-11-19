#!/usr/bin/env python3
"""Synthesize the narration passages, then transcribe each take with word timestamps.

script.json lists the scenes in order; each scene has an id, a passage letter and its
narration. Scenes sharing a passage are read in one call (300 to 700 characters, as the
voice-intonation skill requires). script.json "voice" chooses the provider:

  voicestudio (local, default): {"provider": "voicestudio", "endpoint": "http://localhost:3900",
      "model": "voxcpm2", "profile": "<VoiceStudio profile id>", "language": "fr", "seed": 300,
      "instruct": "<style instruction>", "pronounce": {"TGBT": "T-G-B-T", ...}}
  elevenlabs: {"provider": "elevenlabs", "id": "<voice id>", "model": "eleven_v3", "stability": 0.5}
      (needs ELEVENLABS_API_KEY; stops before any synthesis if the character budget is short)

  python3 tts_passages.py work/script.json work/voice [--passages A,C] [--take b] [--seed 7] [--dry-run]

Writes work/voice/<passage>-<take>.wav (or .mp3) and .stt.json {"text", "words": [{text,start,end}]}.
"""
import argparse, json, os, re, sys, time, uuid, urllib.error, urllib.request

TAG = re.compile(r"\[[a-zA-Z ]+\]\s*")


def http(url, data=None, headers=None, timeout=900):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data is not None else "GET")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                return json.loads(b) if "json" in r.headers.get("Content-Type", "") else b
        except urllib.error.HTTPError as e:
            msg = e.read()[:600].decode(errors="replace")
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(6 * (attempt + 1))
                continue
            sys.exit("HTTP %s on %s: %s" % (e.code, url, msg))
        except urllib.error.URLError as e:
            sys.exit("Cannot reach %s (%s). Start the voice backend first." % (url, e.reason))


def multipart(fields, file_field, path, mime):
    b = "----" + uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (b, k, v)).encode()
    body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n"
             % (b, file_field, os.path.basename(path), mime)).encode()
    body += open(path, "rb").read() + ("\r\n--%s--\r\n" % b).encode()
    return body, "multipart/form-data; boundary=%s" % b


def passages(script):
    out = {}
    for s in script["scenes"]:
        if s.get("narration"):
            out.setdefault(s["passage"], []).append(s["narration"].strip())
    return {k: " ".join(v) for k, v in out.items()}


def spoken(text, pronounce):
    text = TAG.sub("", text) if pronounce is not None else text
    for k in sorted(pronounce or {}, key=len, reverse=True):
        text = re.sub(r"(?<![\w-])%s(?![\w-])" % re.escape(k), pronounce[k], text)
    return text


def keep_tags(text, pronounce):
    """ElevenLabs: apply voice.pronounce outside the [audio tags], which must stay in English."""
    parts = re.split(r"(\[[a-zA-Z ]+\])", text)
    return "".join(p if p.startswith("[") else spoken(p, pronounce) for p in parts)


def voicestudio(voice, text, out, seed):
    base = voice.get("endpoint", "http://localhost:3900").rstrip("/")
    health = http(base + "/health", timeout=10)
    if not isinstance(health, dict) or health.get("status") != "ok":
        sys.exit("VoiceStudio backend not healthy at %s: %s" % (base, health))
    body = {"model": voice.get("model", "voxcpm2"), "voice": voice["profile"], "input": text,
            "language": voice.get("language", "fr"), "response_format": "wav"}
    if voice.get("instruct"):
        body["instruct"] = voice["instruct"]
    if seed is not None:
        body["seed"] = seed
    audio = http(base + "/v1/audio/speech", json.dumps(body).encode(), {"Content-Type": "application/json"})
    if not isinstance(audio, bytes) or audio[:4] != b"RIFF":
        sys.exit("VoiceStudio returned no audio for %s: %s" % (out, str(audio)[:300]))
    open(out, "wb").write(audio)
    data, ctype = multipart({"model": "whisper-1", "language": voice.get("language", "fr"),
                             "response_format": "verbose_json", "timestamp_granularities[]": "word"}, "file", out, "audio/wav")
    t = http(base + "/v1/audio/transcriptions", data, {"Content-Type": ctype})
    if not isinstance(t, dict) or "words" not in t:
        sys.exit("VoiceStudio transcription failed for %s: %s" % (out, str(t)[:300]))
    return {"text": t.get("text"), "words": [{"text": w["word"], "start": w["start"], "end": w["end"]} for w in t["words"]]}


def elevenlabs(voice, text, out, seed):
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("ELEVENLABS_API_KEY is missing: run through scripts/with_secrets.sh.")
    h = {"xi-api-key": key, "Content-Type": "application/json"}
    body = {"text": text, "model_id": voice.get("model", "eleven_v3"), "voice_settings": {"stability": voice.get("stability", 0.5)}}
    if seed is not None:
        body["seed"] = seed
    audio = http("https://api.elevenlabs.io/v1/text-to-speech/%s?output_format=mp3_44100_128" % voice["id"], json.dumps(body).encode(), h)
    open(out, "wb").write(audio)
    data, ctype = multipart({"model_id": "scribe_v1", "language_code": "fra"}, "file", out, "audio/mpeg")
    t = http("https://api.elevenlabs.io/v1/speech-to-text", data, {"xi-api-key": key, "Content-Type": ctype})
    return {"text": t.get("text"), "words": [{"text": w["text"], "start": w["start"], "end": w["end"]} for w in t.get("words", []) if w.get("type") == "word"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("outdir")
    ap.add_argument("--passages", help="comma-separated passage letters (default: all)")
    ap.add_argument("--take", default="a")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--dry-run", action="store_true", help="print passages and character cost only")
    a = ap.parse_args()

    script = json.load(open(a.script))
    voice = script["voice"]
    provider = voice.get("provider", "voicestudio")
    todo = passages(script)
    if a.passages:
        todo = {k: v for k, v in todo.items() if k in a.passages.split(",")}
    pron = voice.get("pronounce", {}) if provider == "voicestudio" else None
    el_pron = voice.get("pronounce", {}) if provider == "elevenlabs" else {}
    cost = 0
    for k, t in todo.items():
        st = spoken(t, pron)
        cost += len(st)
        flag = "" if 300 <= len(t) <= 700 else "  <-- outside 300-700"
        print("passage %s: %d chars%s" % (k, len(t), flag))
    print("total: %d characters (%s)" % (cost, provider))
    if a.dry_run:
        return
    if provider == "elevenlabs":
        key = os.environ.get("ELEVENLABS_API_KEY")
        if not key:
            sys.exit("ELEVENLABS_API_KEY is missing: run through scripts/with_secrets.sh.")
        sub = http("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": key})
        left = sub["character_limit"] - sub["character_count"]
        if cost > left:
            sys.exit("Not enough ElevenLabs characters: %d needed, %d left (plan %s). No voice was generated."
                     % (cost, left, sub.get("tier")))
    os.makedirs(a.outdir, exist_ok=True)
    ext = "wav" if provider == "voicestudio" else "mp3"
    for i, (k, text) in enumerate(todo.items()):
        out = os.path.join(a.outdir, "%s-%s.%s" % (k, a.take, ext))
        seed = a.seed if a.seed is not None else voice.get("seed")
        seed = None if seed is None else seed + sum(ord(c) for c in k)
        t0 = time.time()
        said = spoken(text, pron) if provider == "voicestudio" else keep_tags(text, el_pron)
        stt = (voicestudio if provider == "voicestudio" else elevenlabs)(voice, said, out, seed)
        stt["passage"] = k
        stt["spoken_text"] = said
        json.dump(stt, open(os.path.join(a.outdir, "%s-%s.stt.json" % (k, a.take)), "w"), ensure_ascii=False)
        print("done %s (%d/%d, %.0f s)" % (out, i + 1, len(todo), time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
