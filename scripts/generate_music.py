from __future__ import annotations

import argparse
import math
import wave
from pathlib import Path

from common import AUDIO, WORK, read_json


def frac(value: float) -> float:
    return value - math.floor(value)


def noise(index: int) -> float:
    return frac(math.sin((index + 1) * 12.9898) * 43758.5453) * 2.0 - 1.0


def section_energy(t: float, brief: dict) -> float:
    for section in brief["structure"]:
        if section["start"] <= t <= section["end"]:
            return float(section["energy"])
    return 0.5


def accent_signal(t: float, sample_index: int, accents: list[dict]) -> tuple[float, float]:
    impact = 0.0
    riser = 0.0
    for accent in accents:
        at = float(accent["time"])
        intensity = float(accent.get("intensity", 0.7))
        dt = t - at
        if 0.0 <= dt <= 1.2:
            decay = math.exp(-dt * 4.4)
            impact += intensity * decay * (
                0.7 * math.sin(2 * math.pi * (58 - 20 * dt) * t)
                + 0.22 * noise(sample_index)
            )
        before = at - t
        if 0.0 < before <= 2.6:
            progress = 1.0 - before / 2.6
            sweep_freq = 380 + 1400 * progress * progress
            riser += intensity * progress * 0.22 * (
                math.sin(2 * math.pi * sweep_freq * t) + 0.3 * noise(sample_index)
            )
    return impact, riser


def midi_freq(note: float) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def gentle_accent_signal(t: float, sample_index: int, accents: list[dict]) -> float:
    signal = 0.0
    for accent in accents:
        at = float(accent["time"])
        intensity = float(accent.get("intensity", 0.7))
        before = at - t
        if 0.0 < before <= 0.9:
            progress = 1.0 - before / 0.9
            signal += intensity * progress * 0.028 * math.sin(2 * math.pi * (640 + 180 * progress) * t)

        dt = t - at
        if 0.0 <= dt <= 1.35:
            env = math.exp(-dt * 3.6)
            chime = (
                0.36 * math.sin(2 * math.pi * 880 * t)
                + 0.21 * math.sin(2 * math.pi * 1320 * t + 0.25)
                + 0.13 * math.sin(2 * math.pi * 1760 * t + 0.5)
            )
            signal += intensity * env * chime
    return signal


def synth_serene_pop_sample(t: float, i: int, brief: dict) -> tuple[float, float]:
    bpm = float(brief["bpm"])
    beat_len = 60.0 / bpm
    beat_pos = (t / beat_len) % 4.0
    energy = section_energy(t, brief)
    duration = float(brief["duration"])
    fade_in = min(1.0, t / max(float(brief["mix"]["fade_in"]), 0.1))
    fade_out = min(1.0, max(duration - t, 0.0) / max(float(brief["mix"]["fade_out"]), 0.1))
    master_env = fade_in * fade_out

    chords = [
        (48, (0, 4, 7, 11)),
        (43, (0, 4, 7, 12)),
        (41, (0, 4, 7, 14)),
        (45, (0, 4, 7, 12)),
    ]
    chord_index = int(t / (beat_len * 8)) % len(chords)
    root_midi, intervals = chords[chord_index]
    freqs = [midi_freq(root_midi + interval) for interval in intervals]

    slow = 0.5 + 0.5 * math.sin(2 * math.pi * 0.055 * t)
    pad = (
        0.16 * math.sin(2 * math.pi * freqs[0] * t)
        + 0.10 * math.sin(2 * math.pi * freqs[1] * t + 0.8)
        + 0.09 * math.sin(2 * math.pi * freqs[2] * t + 1.6)
        + 0.07 * math.sin(2 * math.pi * freqs[3] * t + 0.35)
    ) * (0.36 + energy * 0.22) * (0.82 + 0.16 * slow)

    pulse_phase = t % beat_len
    pulse_env = math.exp(-pulse_phase * 5.2)
    bass = 0.09 * (0.65 + energy * 0.35) * pulse_env * math.sin(2 * math.pi * (freqs[0] / 2.0) * t)

    kick = 0.0
    if pulse_phase < 0.105:
        kick_env = math.exp(-pulse_phase * 30.0)
        kick = 0.075 * energy * kick_env * math.sin(2 * math.pi * (78 - 12 * pulse_phase) * t)

    brush = 0.0
    if 1.0 <= beat_pos < 1.08 or 3.0 <= beat_pos < 3.08:
        brush_env = math.exp(-((beat_pos % 1.0) * beat_len) * 28.0)
        brush = 0.028 * energy * brush_env * noise(i)

    note_pool = [72, 74, 76, 79, 81, 84, 86, 88]
    step_len = beat_len / 2.0
    arp_step = int(t / step_len) % len(note_pool)
    arp_phase = t % step_len
    arp_env = math.exp(-arp_phase * 8.5)
    arp = 0.075 * (0.55 + energy * 0.45) * arp_env * math.sin(2 * math.pi * midi_freq(note_pool[arp_step]) * t)

    shaker_phase = t % (beat_len / 4.0)
    shaker = 0.009 * energy * math.exp(-shaker_phase * 34.0) * noise(i)
    chime = 0.13 * gentle_accent_signal(t, i, brief["accents"])

    mono = (pad + bass + kick + brush + arp + shaker + chime) * master_env
    pan = 0.12 * math.sin(2 * math.pi * 0.07 * t)
    left = mono * (0.90 - pan)
    right = mono * (0.90 + pan)
    return max(-1.0, min(1.0, left)), max(-1.0, min(1.0, right))


def synth_serene_ambient_sample(t: float, i: int, brief: dict) -> tuple[float, float]:
    duration = float(brief["duration"])
    fade_in = min(1.0, t / max(float(brief["mix"]["fade_in"]), 0.1))
    fade_out = min(1.0, max(duration - t, 0.0) / max(float(brief["mix"]["fade_out"]), 0.1))
    master_env = fade_in * fade_out

    chord_len = 6.0
    chords = [
        (48, (0, 7, 12, 16)),
        (53, (0, 7, 12, 16)),
        (55, (0, 7, 11, 14)),
        (52, (0, 7, 12, 16)),
    ]
    root_midi, intervals = chords[int(t / chord_len) % len(chords)]
    freqs = [midi_freq(root_midi + interval) for interval in intervals]

    breathe = 0.72 + 0.28 * math.sin(2 * math.pi * 0.045 * t)
    pad = (
        0.115 * math.sin(2 * math.pi * freqs[0] * t)
        + 0.075 * math.sin(2 * math.pi * freqs[1] * t + 0.7)
        + 0.060 * math.sin(2 * math.pi * freqs[2] * t + 1.4)
        + 0.045 * math.sin(2 * math.pi * freqs[3] * t + 0.2)
    ) * breathe

    pulse_len = 1.5
    pulse_phase = t % pulse_len
    pulse_env = math.exp(-pulse_phase * 3.5)
    note_pool = [72, 76, 79, 84, 81, 79, 76, 72]
    note = midi_freq(note_pool[int(t / pulse_len) % len(note_pool)])
    felt_piano = 0.052 * pulse_env * math.sin(2 * math.pi * note * t)

    lift = 0.0
    for accent in brief["accents"]:
        at = float(accent["time"])
        dt = t - at
        if 0.0 <= dt <= 2.4:
            env = math.exp(-dt * 1.8)
            lift += 0.070 * env * (
                math.sin(2 * math.pi * 659.25 * t)
                + 0.55 * math.sin(2 * math.pi * 987.77 * t + 0.3)
            )

    air = 0.004 * noise(i) * (0.6 + 0.4 * math.sin(2 * math.pi * 0.03 * t))
    mono = (pad + felt_piano + lift + air) * master_env
    pan = 0.10 * math.sin(2 * math.pi * 0.035 * t)
    left = mono * (0.93 - pan)
    right = mono * (0.93 + pan)
    return max(-1.0, min(1.0, left)), max(-1.0, min(1.0, right))


def synth_sample(t: float, i: int, brief: dict) -> tuple[float, float]:
    if brief.get("mood_profile") == "serene_ambient":
        return synth_serene_ambient_sample(t, i, brief)
    if brief.get("mood_profile") == "serene_pop":
        return synth_serene_pop_sample(t, i, brief)

    bpm = float(brief["bpm"])
    beat_len = 60.0 / bpm
    beat_pos = (t / beat_len) % 4.0
    energy = section_energy(t, brief)
    duration = float(brief["duration"])
    fade_in = min(1.0, t / max(float(brief["mix"]["fade_in"]), 0.1))
    fade_out = min(1.0, max(duration - t, 0.0) / max(float(brief["mix"]["fade_out"]), 0.1))
    master_env = fade_in * fade_out

    chord_roots = [48, 43, 46, 41, 51, 46, 39, 43]
    chord_index = int(t / (beat_len * 8)) % len(chord_roots)
    root_midi = chord_roots[chord_index]
    root = 440.0 * 2 ** ((root_midi - 69) / 12)
    third = root * 2 ** (3 / 12)
    fifth = root * 2 ** (7 / 12)
    octave = root * 2.0

    pad = (
        0.20 * math.sin(2 * math.pi * root * t)
        + 0.14 * math.sin(2 * math.pi * third * t + 0.8)
        + 0.12 * math.sin(2 * math.pi * fifth * t + 1.7)
        + 0.08 * math.sin(2 * math.pi * octave * t + 0.4)
    ) * (0.45 + energy * 0.35)

    pulse_phase = (t % beat_len)
    pulse_env = math.exp(-pulse_phase * 5.0)
    bass_freq = root / 2.0
    bass = 0.42 * pulse_env * math.sin(2 * math.pi * bass_freq * t)

    kick = 0.0
    if pulse_phase < 0.16:
        kick_env = math.exp(-pulse_phase * 28.0)
        kick = 0.72 * energy * kick_env * math.sin(2 * math.pi * (62 - 32 * pulse_phase) * t)

    clap = 0.0
    if 1.0 <= beat_pos < 1.12 or 3.0 <= beat_pos < 3.12:
        clap_env = math.exp(-((beat_pos % 1.0) * beat_len) * 34.0)
        clap = 0.14 * energy * clap_env * noise(i)

    arp_notes = [root * 2, fifth * 2, octave * 2, third * 4, fifth * 4, octave * 4]
    arp_step = int(t / (beat_len / 2.0)) % len(arp_notes)
    arp_phase = (t % (beat_len / 2.0))
    arp_env = math.exp(-arp_phase * 8.0)
    arp = 0.16 * energy * arp_env * math.sin(2 * math.pi * arp_notes[arp_step] * t)

    impact, riser = accent_signal(t, i, brief["accents"])
    shimmer = 0.035 * energy * noise(i) if beat_pos < 0.08 and energy > 0.5 else 0.0

    mono = (pad + bass + kick + clap + arp + impact + riser + shimmer) * master_env
    pan = 0.18 * math.sin(2 * math.pi * 0.045 * t)
    left = mono * (0.88 - pan)
    right = mono * (0.88 + pan)
    return max(-1.0, min(1.0, left)), max(-1.0, min(1.0, right))


def generate(brief: dict, output: Path, sample_rate: int = 24000) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    duration = float(brief["duration"])
    total_samples = int(duration * sample_rate)
    chunk_size = sample_rate
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        written = 0
        while written < total_samples:
            count = min(chunk_size, total_samples - written)
            frames = bytearray()
            for offset in range(count):
                i = written + offset
                t = i / sample_rate
                left, right = synth_sample(t, i, brief)
                frames += int(left * 32767).to_bytes(2, "little", signed=True)
                frames += int(right * 32767).to_bytes(2, "little", signed=True)
            wav.writeframesraw(bytes(frames))
            written += count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", default=str(WORK / "music_brief.json"))
    parser.add_argument("--output", default=str(AUDIO / "music.wav"))
    args = parser.parse_args()
    brief = read_json(Path(args.brief))
    if brief.get("provider") != "local_procedural":
        raise SystemExit(f"Unsupported provider in local workflow: {brief.get('provider')}")
    generate(brief, Path(args.output))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
