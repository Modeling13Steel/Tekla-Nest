#!/usr/bin/env python3
"""Music bed: download a Mixkit track, level it, find its bars, write build/music/bed.wav + bed.json.

Mixkit Stock Music Free License (https://mixkit.co/license/#musicFree): free for commercial video,
no attribution; the track may not be redistributed on its own, so it is fetched into build/ (ignored),
never committed. Remotion plays the head of the track, then crossfades on a bar line into the track's
own ending (`outro_at`) so the music resolves exactly on the end card, whatever the cut length.

    uv run --no-project --with numpy --with soundfile --with librosa --with pyloudnorm python video/music.py [--track 33]
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

import librosa
import numpy as np
import pyloudnorm as pyln
import soundfile as sf

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "build" / "cache" / "music"
OUT = ROOT / "build" / "music"
SR = 48_000
LUFS = -20.0  # same loudness as the VO stems; the mix sets the bed level from here
OUTRO = 6.0  # s of the track's own ending kept for the end card
# Instrumental Mixkit tracks checked for vocals with Whisper. Default first.
TRACKS = {
    "33": "Motivating Mornings (corporate, 123 BPM)",
    "440": "Infinity (corporate, 112 BPM)",
    "175": "Digital Clouds (chillout, 129 BPM)",
    "173": "Better Times are Coming (synthpop, 117 BPM)",
    "724": "PlaceIt World 01 (corporate, 123 BPM)",
}


def fetch(track: str) -> Path:
    path = CACHE / f"{track}.mp3"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(f"https://assets.mixkit.co/music/{track}/{track}.mp3", path)
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default=next(iter(TRACKS)), choices=list(TRACKS))
    track = ap.parse_args().track
    y, _ = librosa.load(fetch(track), sr=SR, mono=False)
    y = np.atleast_2d(y).T  # (n, ch)
    mono = y.mean(1)
    # The audible end of the track (Mixkit files carry a few seconds of silence/reverb tail).
    env = librosa.feature.rms(y=mono, hop_length=512)[0]
    audible = np.flatnonzero(20 * np.log10(env / env.max() + 1e-9) > -40)
    end = min(len(mono), (audible[-1] + 1) * 512 + int(1.5 * SR))
    y, mono = y[:end], mono[:end]
    tempo, beats = librosa.beat.beat_track(y=mono, sr=SR, units="time")
    # The tracker can lose lock in sparse sections; these beds hold one tempo, so extend its grid.
    bar = 4 * float(np.median(np.diff(beats)))
    bars = np.arange(beats[0], len(mono) / SR, bar)
    outro_at = float(bars[np.argmin(np.abs(bars - (len(mono) / SR - OUTRO)))])
    y = y * 10 ** ((LUFS - pyln.Meter(SR).integrated_loudness(y)) / 20)
    y = y / max(1.0, np.abs(y).max() / 0.89)
    OUT.mkdir(parents=True, exist_ok=True)
    sf.write(OUT / "bed.wav", y.astype(np.float32), SR, subtype="PCM_16")
    meta = {"track": track, "title": TRACKS[track], "license": "Mixkit Stock Music Free License",
            "bpm": round(float(np.atleast_1d(tempo)[0]), 1), "duration": round(len(y) / SR, 3),
            "bars": [round(float(b), 3) for b in bars], "outro_at": round(outro_at, 3)}
    (OUT / "bed.json").write_text(json.dumps(meta, indent=2))
    print(f"bed {track} {TRACKS[track]}: {meta['duration']} s, {meta['bpm']} BPM, outro at {outro_at:.2f} s")


if __name__ == "__main__":
    main()
