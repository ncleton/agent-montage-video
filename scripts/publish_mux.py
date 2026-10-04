"""Publish a local video to Mux.

Credentials come from MUX_TOKEN_ID and MUX_TOKEN_SECRET, injected by LibreAgent:
run it through scripts/with_secrets.sh. They are never printed or written to disk.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API = "https://api.mux.com/video/v1"


def credential(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is missing: run this command through scripts/with_secrets.sh")
    return value


def request_json(path: str, auth: str, body: dict | None = None) -> dict:
    headers = {"Authorization": f"Basic {auth}", "Accept": "application/json"}
    data = None
    method = "GET"
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
        method = "POST"
    request = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Mux API HTTP {exc.code} on {path}") from None


def upload_file(url: str, path: Path) -> None:
    request = urllib.request.Request(
        url,
        data=path.read_bytes(),
        headers={"Content-Type": "video/mp4"},
        method="PUT",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            if response.status not in (200, 201, 204):
                raise RuntimeError(f"Mux upload HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Mux upload HTTP {exc.code}") from None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--metadata-output", type=Path, help="Defaults to output/<video name>.mux.json")
    parser.add_argument("--check-auth", action="store_true")
    args = parser.parse_args()
    video = args.video.resolve()
    if args.metadata_output is None:
        args.metadata_output = ROOT / "output" / f"{video.stem}.mux.json"
    if not video.is_file() or video.stat().st_size < 1_000_000:
        raise SystemExit(f"Video missing or too small: {video}")

    token_id = credential("MUX_TOKEN_ID")
    token_secret = credential("MUX_TOKEN_SECRET")
    auth = base64.b64encode(f"{token_id}:{token_secret}".encode()).decode()
    del token_id, token_secret

    request_json("/assets?limit=1", auth)
    print("Mux credentials verified.", flush=True)
    if args.check_auth:
        return

    print(f"Creating public Mux upload for {video.name}...", flush=True)
    upload = request_json(
        "/uploads",
        auth,
        {
            "new_asset_settings": {
                "playback_policies": ["public"],
                "video_quality": "basic",
                "static_renditions": [{"resolution": "highest"}],
                "meta": {"title": args.title},
            },
            "timeout": 3600,
        },
    )["data"]
    upload_id = upload["id"]
    print(f"Uploading {video.stat().st_size / 1_000_000:.1f} MB...", flush=True)
    upload_file(upload["url"], video)
    print("Upload complete. Waiting for Mux processing...", flush=True)

    asset_id = None
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        state = request_json(f"/uploads/{upload_id}", auth)["data"]
        if state.get("status") in ("errored", "timed_out", "cancelled"):
            raise RuntimeError(f"Mux upload failed: {state['status']}")
        asset_id = state.get("asset_id")
        if asset_id:
            break
        time.sleep(5)
    if not asset_id:
        raise RuntimeError("Mux did not create an asset before the timeout")

    last_status = None
    asset = None
    while time.monotonic() < deadline:
        asset = request_json(f"/assets/{asset_id}", auth)["data"]
        status = asset.get("status")
        if status != last_status:
            print(f"Mux asset: {status}", flush=True)
            last_status = status
        if status == "errored":
            raise RuntimeError("Mux asset processing failed")
        renditions = asset.get("static_renditions") or {}
        files = renditions.get("files") or []
        static = next((item for item in files if item.get("name") == "highest.mp4"), None)
        if status == "ready" and static and static.get("status") == "ready":
            break
        time.sleep(8)
    else:
        raise RuntimeError("Mux processing did not finish before the timeout")

    playback = next((p["id"] for p in asset.get("playback_ids", []) if p.get("policy") == "public"), None)
    if not playback:
        raise RuntimeError("Mux asset has no public playback ID")
    result = {
        "asset_id": asset_id,
        "upload_id": upload_id,
        "playback_id": playback,
        "policy": "public",
        "hls_url": f"https://stream.mux.com/{playback}.m3u8",
        "mp4_url": f"https://stream.mux.com/{playback}/highest.mp4",
        "thumbnail_url": f"https://image.mux.com/{playback}/thumbnail.jpg?time=1",
        "title": args.title,
        "source_file": str(video),
        "source_sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    output = args.metadata_output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Public MP4: {result['mp4_url']}")
    print(f"Public HLS: {result['hls_url']}")
    print(f"Saved metadata: {output}")


if __name__ == "__main__":
    main()
