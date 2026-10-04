---
name: video-frame-review
description: Verify a rendered video frame by frame before handing it over - automatic detection of isolated frame jumps over every frame, then a visual review of timestamped contact sheets covering the whole duration, then a requirement-by-requirement check against the client's requests. Use after any render of a final or client-facing MP4 in this workspace (Remotion, HyperFrames, openvid), when the user reports a glitch, saccade or "bug à 0:37", or asks to "revérifier frame par frame".
---

# Video frame review

A render is not ready because it compiled or because a few stills looked right. Logo glitches, a flash between two transitions, an empty card for ten seconds or a counter starting at 0 only show up across the whole timeline. Run this review on the final file, not on stills or an earlier render, before giving an MP4 or a link to the user.

## 1. Check the file

Check the duration, the codecs and the presence of audio, then decode the whole file to catch errors:

    ffprobe -v error -show_entries format=duration -show_entries stream=codec_type,width,height,r_frame_rate -of compact out.mp4
    ffmpeg -v error -i out.mp4 -f null -

## 2. Detect jumps on every frame

    .venv/bin/python .agents/skills/video-frame-review/scripts/detect_jumps.py out.mp4

The script compares each frame with the next one at low resolution. It lists the isolated spikes: a frame that differs much more from its neighbours than the local motion does. Those are cuts, flashes, popping elements or a re-layout. Expected result: no spikes. Look at every reported time with a frame grab (ffmpeg -ss T -frames:v 1). Planned hard cuts are legitimate only if they are intended; a long camera move shows as a smooth run of large differences, not as a spike.

## 3. Look at the whole video

    .venv/bin/python .agents/skills/video-frame-review/scripts/contact_sheets.py out.mp4 /tmp/review --fps 2

This produces timestamped sheets of 16 frames (one every 0.5 s by default). Open every sheet, from the first to the last, and note the times of any defect. Look for:

- text cut, wrapping badly, overflowing a card or hidden by another element (on the frame, not only in the final layout);
- logos and images that blink, shift or get cropped during a camera move or a transition;
- elements shown before the voice mentions them, or cards that stay empty while the voice talks;
- counters or animated numbers going through a wrong value (for example 0 before 16);
- flashes or a blank frame between two scenes, a transition that lands on an empty screen;
- consistency of names, dates and figures with the sources.

To look closer at a passage, rerun with --start/--duration and a higher --fps, or grab one frame at full resolution.

## 4. Check the requests

Write down the list of explicit requests (client audio, user messages) and, for each one, the time where it is visible or heard. Check the voice-over with a transcription of the final mix. A request that is not on screen or in the voice is not done. Names from a transcription must be checked against an authoritative source (the client's website, an official document) before being written on screen.

## 5. Fix and repeat

After any fix, render again and rerun steps 1 to 3 on the new file. Do not reuse the results of an earlier render. Hand over the MP4 only when the jump detection is clean, every sheet has been looked at, and every request is matched to a time. In the handover, state what was checked and list the points that still depend on a choice or on a source that could not be confirmed.

