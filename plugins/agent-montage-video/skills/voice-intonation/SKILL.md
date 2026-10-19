---
name: voice-intonation
description: Make every ElevenLabs voice-over sound human, not robotic - Eleven v3 with sparse audio tags, takes written as long passages, best-of-N takes, and a mandatory intonation measurement before any render. Use for every voice-over, narration, voix off or TTS line in this workspace, when a voice sounds flat, monotone, robotic or "on dirait un robot", and before replacing or re-recording a voice.
---

# Voice-over intonation

A voice-over is not finished when the words are right. It must sound like a person
talking to a colleague. This check is mandatory for every voice-over, before the
render and again on the final mix.

## 1. Write for Eleven v3

- Model: `eleven_v3`. Do not use `eleven_multilingual_v2` with a high stability to
  remove hesitations: above about 0.5 it flattens the voice (measured 1.8 to 2.2
  semitones, judged robotic by Nicolas).
- Stability: 0.5 (Natural). 0.0 (Creative) is more expressive but less consistent;
  1.0 (Robust) ignores audio tags. Never use Robust for narration.
- Generate long passages of 300 to 700 characters (two or three scenes together),
  never one short line per call: v3 is unstable on short prompts. Split the passage
  into scenes afterwards from the Scribe word timestamps.
- Audio tags in English, in square brackets, one per change of tone, never on every
  sentence: `[warmly]`, `[cheerfully]`, `[confidently]`, `[calmly]`, `[curious]`,
  `[seriously]`, `[firmly]`, `[lightly]`. Use commas, ellipses and full stops to
  shape rhythm and emphasis. Remove tags from the subtitle text.
- Spell out what the voice must read naturally (`cent places`, not `100 places`).

## 2. Choose the voice by measuring it

Test the first passage with the requested voice before generating the rest. Cloned
voices often stay flat even on v3: Nicolas's instant clone measured 2.0 to 2.7
semitones and failed on 4 of 6 passages. Professional clones need a Creator plan;
the account is Starter. When the requested voice cannot reach the threshold, use the
best measured French voice of the library and say so: Victoire
(`O31r762Gb3WFygrEOGh0`, female, narration) measured 2.5 to 3.4 semitones with 100 %
text fidelity on the Lead Generator demo.

## 3. Measure every take

    .venv/bin/python plugins/agent-montage-video/skills/voice-intonation/scripts/prosody.py take.mp3 [...]

Accept a take only if all of these hold:

- `pitch_std_st` at least 2.5 semitones and `pitch_range_st` at least 8 (flat reads
  sit around 1.8 to 2.2 and 6 to 7);
- Scribe transcript matches the script (singular/plural homophones aside), no tag
  read aloud, no hesitation such as "euh", no silence over 1.2 s inside a sentence;
- consistent voice and level across passages.

Otherwise generate another take of that passage (new seed) and keep the best one.
Budget the retakes against the remaining ElevenLabs characters (`/v1/user/subscription`)
before starting.

## 4. Sync and final check

Time subtitles on the spoken words. When the voice describes an action after it
appears on screen, freeze the picture before the action rather than speeding the
capture. On the final render, transcribe the mix, run `prosody.py` on it, and
report the measured values with the voice used.

