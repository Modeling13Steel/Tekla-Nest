#!/usr/bin/env python3
"""Demo-video SFX: Mixkit sounds (free for commercial use, no attribution), tamed and levelled.

Each sound is fetched into build/cache/sfx (never committed: the license forbids redistributing the
files on their own), trimmed to its audible part, softened with a low-pass, faded, and written with
its peak baked in, so the Remotion mix plays every cue at volume 1 and it still sits well under the
VO (-20 dBFS RMS, -1 dBFS peak). `audio_report.py` verifies the balance on every render.

    whoosh_a/whoosh_b  scene transitions (alternated so no two in a row are the same file)
    hit                logo and big-number reveals (whoosh into a soft impact)
    click              UI clicks on app buttons
    pop                cards and chips appearing
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "build" / "cache" / "sfx"
OUT = ROOT / "build" / "sfx"
SR = 48_000
# name: (Mixkit id, peak dBFS, low-pass Hz)
SOUNDS = {
    "whoosh_a": ("168", -27.0, 9000),   # Fast air sweep
    "whoosh_b": ("1468", -27.0, 9000),  # Cinematic transition wind swoosh
    "hit": ("2903", -24.0, 7000),       # Movie whoosh impact presentation
    "click": ("3124", -26.0, 8000),     # Modern technology select
    "pop": ("3005", -29.0, 6000),       # Explainer video light pop
}


def _fetch(mixkit_id: str) -> Path:
    path = CACHE / f"{mixkit_id}.wav"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(f"https://assets.mixkit.co/active_storage/sfx/{mixkit_id}/{mixkit_id}.wav", path)
    return path


def _prepare(mixkit_id: str, peak_db: float, lowpass_hz: float) -> np.ndarray:
    x, sr = sf.read(_fetch(mixkit_id), dtype="float64")
    x = x.mean(axis=1) if x.ndim > 1 else x
    if sr != SR:
        x = np.interp(np.arange(0, len(x) * SR / sr) * sr / SR, np.arange(len(x)), x)
    env = np.sqrt(np.convolve(x**2, np.ones(480) / 480, mode="same"))
    on = np.flatnonzero(env > env.max() * 10 ** (-45 / 20))
    x = x[max(on[0] - 240, 0): on[-1] + 2400]
    x = sosfiltfilt(butter(2, lowpass_hz, fs=SR, output="sos"), x)  # take the edge off
    fade = int(0.03 * SR)
    x[-fade:] *= np.linspace(1, 0, fade) ** 2
    x[:96] *= np.linspace(0, 1, 96)
    return x / max(1e-9, np.abs(x).max()) * 10 ** (peak_db / 20)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.wav"):
        old.unlink()
    for name, (mixkit_id, peak_db, lowpass_hz) in SOUNDS.items():
        sf.write(OUT / f"{name}.wav", _prepare(mixkit_id, peak_db, lowpass_hz).astype(np.float32), SR, subtype="PCM_16")
    print(f"wrote {sorted(p.stem for p in OUT.glob('*.wav'))} to {OUT.relative_to(ROOT.parent)}")


if __name__ == "__main__":
    main()
