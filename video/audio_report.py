"""Audio QA: VO vs SFX vs music level histograms, mix timeline, loudness of the master.

Usage (from repo root, after `npm run render` for the cut/lang):
    uv run --no-project --with numpy --with soundfile --with matplotlib \
        --with pyloudnorm --with scipy --with imageio-ffmpeg \
        python video/audio_report.py --cut full --lang en pt

Renders missing VO/SFX/music stems through Remotion, writes PNG + JSON to
video/build/out/audio/ and exits 1 when the SFX are not clearly under the
voice (SFX p95 > VO p50 - 12 dB), the music is not ducked under the voice
(music p50 while VO speaks > VO p50 - 12 dB), or the master misses
-14 LUFS / -1 dBTP. Delete stale stems after changing the edit.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pyloudnorm  # noqa: E402
import soundfile as sf  # noqa: E402
from scipy.signal import resample_poly  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "build" / "out"
AUDIO = OUT / "audio"
SR = 48000
WIN = 0.1
SILENT = -70.0
GAP_DB = 12.0


def _read(path: Path) -> np.ndarray:
    """Stereo float64 samples (n, 2)."""
    if path.suffix == ".wav":
        data, sr = sf.read(path, always_2d=True)
        assert sr == SR, f"{path} is {sr} Hz"
        return data
    raw = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(path), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64).reshape(-1, 2)


def _stem(cut: str, lang: str, stem: str) -> Path:
    path = AUDIO / f"{cut}-{lang}-{stem}.wav"
    if not path.exists():
        props = json.dumps({"lang": lang.split("-")[0], "voice": lang, "cut": cut, "cta_url": "", "stem": stem})  # lang may be a voice id
        subprocess.run(["npm", "run", "--silent", "render", "--", f"--props={props}"], cwd=ROOT / "remotion", check=True)
    return path


def _rms_db(x: np.ndarray) -> np.ndarray:
    x = x.mean(axis=1)
    n = int(SR * WIN)
    frames = x[: len(x) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((frames**2).mean(axis=1)) + 1e-12)


def _true_peak_db(x: np.ndarray) -> float:
    return float(20 * np.log10(np.abs(resample_poly(x, 4, 1, axis=0)).max() + 1e-12))


def report(cut: str, lang: str) -> bool:
    vo, sfx, music = (_read(_stem(cut, lang, x)) for x in ("vo", "sfx", "music"))
    master = _read(OUT / f"{cut}-{lang}.mp4")
    vo_db, sfx_db, mix_db = _rms_db(vo), _rms_db(sfx), _rms_db(master)
    vo_on, sfx_on = vo_db[vo_db > SILENT], sfx_db[sfx_db > SILENT]
    mu_db = _rms_db(music)[: len(vo_db)]
    speaking = vo_db[: len(mu_db)] > -45
    mu_under = mu_db[speaking & (mu_db > SILENT)]
    mu_open = mu_db[~speaking & (mu_db > SILENT)]
    mu_p50 = float(np.percentile(mu_under, 50)) if mu_under.size else SILENT
    mu_open_p50 = float(np.percentile(mu_open, 50)) if mu_open.size else SILENT
    vo_p50 = float(np.percentile(vo_on, 50)) if vo_on.size else SILENT
    sfx_p95 = float(np.percentile(sfx_on, 95)) if sfx_on.size else SILENT
    lufs = float(pyloudnorm.Meter(SR).integrated_loudness(master))
    tp = _true_peak_db(master)
    stats = {
        "cut": cut, "lang": lang, "seconds": round(len(master) / SR, 2),
        "integrated_lufs": round(lufs, 2), "true_peak_dbtp": round(tp, 2),
        "vo_rms_p50_dbfs": round(vo_p50, 1), "sfx_rms_p95_dbfs": round(sfx_p95, 1),
        "sfx_under_vo_db": round(vo_p50 - sfx_p95, 1),
        "music_under_vo_p50_dbfs": round(mu_p50, 1), "music_open_p50_dbfs": round(mu_open_p50, 1),
        "music_under_vo_db": round(vo_p50 - mu_p50, 1),
        "checks": {
            "sfx_under_vo": vo_p50 - sfx_p95 >= GAP_DB,
            "music_ducked": vo_p50 - mu_p50 >= GAP_DB,
            "loudness": abs(lufs + 14) <= 1.0,
            "true_peak": tp <= -1.0,
        },
    }
    stats["pass"] = all(stats["checks"].values())

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), gridspec_kw={"height_ratios": [1, 1.2]})
    bins = np.arange(-70, 1, 2)
    ax1.hist(vo_on, bins=bins, alpha=0.65, label=f"VO (p50 {vo_p50:.1f} dBFS)", color="#0071e3")
    ax1.hist(sfx_on, bins=bins, alpha=0.65, label=f"SFX (p95 {sfx_p95:.1f} dBFS)", color="#ff9f0a")
    ax1.hist(mu_under, bins=bins, alpha=0.5, label=f"music under VO (p50 {mu_p50:.1f} dBFS)", color="#14b8a6")
    ax1.axvline(vo_p50 - GAP_DB, color="#1d1d1f", ls="--", lw=1, label=f"SFX ceiling (VO p50 − {GAP_DB:.0f} dB)")
    ax1.set(xlabel="100 ms RMS (dBFS)", ylabel="windows", title=f"{cut}-{lang}: level histogram")
    ax1.legend()
    t = np.arange(len(mix_db)) * WIN
    ax2.plot(t, mix_db, color="#86868b", lw=0.8, label="master")
    ax2.plot(np.arange(len(vo_db)) * WIN, vo_db, color="#0071e3", lw=0.8, label="VO stem")
    ax2.plot(np.arange(len(sfx_db)) * WIN, sfx_db, color="#ff9f0a", lw=0.8, label="SFX stem")
    ax2.plot(np.arange(len(mu_db)) * WIN, mu_db, color="#14b8a6", lw=0.8, label="music stem")
    ax2.set(ylim=(-70, 0), xlabel="seconds", ylabel="dBFS",
            title=f"timeline · {lufs:.1f} LUFS · {tp:.1f} dBTP")
    ax2.legend(loc="lower right")
    fig.tight_layout()
    AUDIO.mkdir(parents=True, exist_ok=True)
    fig.savefig(AUDIO / f"{cut}-{lang}-report.png", dpi=110)
    plt.close(fig)
    (AUDIO / f"{cut}-{lang}-report.json").write_text(json.dumps(stats, indent=2) + "\n")
    print(json.dumps(stats))
    return stats["pass"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cut", nargs="+", default=["full"])
    parser.add_argument("--lang", nargs="+", default=["en", "pt"])
    args = parser.parse_args()
    ok = [report(c, lang) for c in args.cut for lang in args.lang]
    sys.exit(0 if all(ok) else 1)


if __name__ == "__main__":
    main()
