"""VO QA: Whisper each raw take, trim it with a natural tail, score intelligibility.

    uvx --from faster-whisper --with soundfile python video/vo_check.py [--lang en pt]

Reads build/audio/<lang>/<n>.raw.wav (from tts.py) and writes <n>.wav, durations.json and vo_check.json.
Idempotent: every run starts again from the raw take, so re-running never shortens a line.
The end is the last word plus the voice's own decay (energy above END_DB), plus a short pad and a
raised-cosine fade, so sentence endings ring out instead of being cut.
Exits 1 if a line's word match falls below MIN_MATCH or its last 20 ms are louder than MAX_TAIL_DB.
"""
import argparse
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

BUILD = Path(__file__).resolve().parent / "build"
MIN_MATCH = 0.8
END_DB = -42.0  # decay below this (re peak) counts as silence
DECAY_MAX = 0.6  # s after the last word in which the voice may still be decaying
PAD, FADE_OUT, FADE_IN = 0.12, 0.10, 0.012  # s
MAX_TAIL_DB = -45.0  # last 20 ms re peak; louder means an audible chop


# Spoken brand forms -> one token. Whisper (pt) writes "eme treze esse" as "M3S" even for a literal
# "M13S" input to a native pt-PT voice, so that form is accepted too; the ear check in review-log covers it.
BRAND = re.compile(r"\b(m ?thirteen ?s|eme ?treze ?esse|m ?13 ?s|m ?3 ?s)\b")


def _words(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    text = BRAND.sub("m13s", re.sub(r"[^a-z0-9]+", " ", text))
    return re.findall(r"[a-z0-9]+", text)


def _env_db(x: np.ndarray, sr: int) -> np.ndarray:
    w = max(1, int(0.01 * sr))
    rms = np.sqrt(np.convolve(x**2, np.ones(w) / w, mode="same"))
    return 20 * np.log10(rms / max(np.abs(x).max(), 1e-9) + 1e-12)


def trim(audio: np.ndarray, sr: int, first_word: float | None, last_word: float | None) -> np.ndarray:
    """Cut engine silence/artifacts but keep the voice's natural attack and decay, with fades."""
    mono = audio if audio.ndim == 1 else audio.mean(1)
    env = _env_db(mono, sr)
    loud = np.flatnonzero(env > END_DB)
    if not loud.size:
        return audio
    start = loud[0]
    if first_word is not None:  # never start later than the first word; never more than 0.3 s before it
        start = max(min(start, int(first_word * sr)), int((first_word - 0.3) * sr), 0)
    end = loud[-1]
    if last_word is not None:  # keep the decay of the last word, drop anything later (breaths, clicks)
        limit = int((last_word + DECAY_MAX) * sr)
        after = loud[(loud >= int(last_word * sr)) & (loud <= limit)]
        end = after[-1] if after.size else int(last_word * sr)
    start = max(0, start - int(0.04 * sr))
    end = min(len(mono), end + int(PAD * sr))
    out = audio[start:end].copy()
    ramp = lambda n: 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, min(n, len(out))))  # noqa: E731
    w_in, w_out = ramp(int(FADE_IN * sr)), ramp(int(FADE_OUT * sr))[::-1]
    out[: len(w_in)] *= w_in if out.ndim == 1 else w_in[:, None]
    out[len(out) - len(w_out):] *= w_out if out.ndim == 1 else w_out[:, None]
    return out


def tail_db(audio: np.ndarray, sr: int) -> float:
    mono = audio if audio.ndim == 1 else audio.mean(1)
    w = int(0.02 * sr)
    return float(20 * np.log10(np.sqrt(np.mean(mono[-w:] ** 2)) / max(np.abs(mono).max(), 1e-9) + 1e-12))


def check(model: WhisperModel, voice_id: str) -> list[dict]:
    scenes = json.loads((BUILD / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    out = BUILD / "audio" / voice_id
    lang = voice_id.split("-")[0]
    durations, report = {}, []
    for scene in scenes:
        raw = out / f"{scene['n']}.raw.wav"
        audio, sr = sf.read(raw, dtype="float32")
        mono = audio if audio.ndim == 1 else audio.mean(1)
        idx = np.arange(0, len(mono), sr / 16000)
        segs, _ = model.transcribe(np.interp(idx, np.arange(len(mono)), mono).astype(np.float32),
                                   language=lang, beam_size=5, word_timestamps=True)
        words = [w for s in segs for w in s.words]
        heard = "".join(w.word for w in words).strip()
        audio = trim(audio, sr, words[0].start if words else None, words[-1].end if words else None)
        sf.write(out / f"{scene['n']}.wav", audio, sr, subtype="PCM_16")
        # Brand respellings ("Eme-treze-ésse", "P D F") are heard as M13S/PDF; compare letters only.
        match = difflib.SequenceMatcher(None, "".join(_words(scene["vo"][lang])), "".join(_words(heard))).ratio()
        durations[str(scene["n"])] = round(len(audio) / sr, 3)
        report.append({"n": scene["n"], "heard": heard, "match": round(match, 2), "tail_db": round(tail_db(audio, sr), 1)})
    (out / "durations.json").write_text(json.dumps(durations, indent=2))
    (out / "vo_check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", nargs="+", default=["en", "pt"], help="voice ids, e.g. en pt pt-raquel")
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")
    bad = []
    for lang in ap.parse_args().lang:
        for row in check(model, lang):
            flag = ("" if row["match"] >= MIN_MATCH else "  <-- LOW") + ("" if row["tail_db"] <= MAX_TAIL_DB else "  <-- CHOP")
            bad += [f"{lang}:{row['n']}"] if flag else []
            print(f"{lang} {row['n']:>2} {row['match']:.2f} tail {row['tail_db']:6.1f} dB {row['heard']}{flag}")
    sys.exit(1 if bad else 0)
