"""TTS: scenes.json -> build/audio/<lang>/<n>.raw.wav (untrimmed; vo_check.py writes <n>.wav + durations.json).

One engine per language, each in an isolated env so the app's deps stay untouched:
    uv run --no-project --python 3.11 --with "kokoro>=0.9.4" --with "transformers>=4.44" --with soundfile --with scipy --with pip python video/tts.py --lang en
    uv run --no-project --python 3.11 --with chatterbox-tts --with edge-tts --with soundfile --with scipy python video/tts.py --lang pt
en: Kokoro-82M (Apache-2.0) `af_heart`, a bright, warm voice at a brisk pace (user: "too deep" for this product).
pt-PT: a native pt-PT neural voice (edge-tts, Microsoft pt-PT-DuarteNeural, +8 % rate, +15 Hz) for the
European accent, converted to the consented reference speaker with ChatterboxVC (MIT). edge-tts is an
unofficial free endpoint; for commercial production use the same voice through an Azure Speech key.
Every take gets the same promo-voice EQ (_eq): less boom, a little more presence.
"""
import argparse
import asyncio
import json
import tempfile
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
# Persona `narrator`, one fixed voice per language (README "Voices").
# Keys are voice ids: the language, optionally "-<variant>". Output goes to build/audio/<id>/.
# "en" and "pt" are the defaults used for every cut; variants are rendered as extra full cuts to compare.
VOICES = {
    "en": ("kokoro", "af_heart", 1.05),  # speed > 1 = brisker
    "en-bella": ("kokoro", "af_bella", 1.05),
    "en-emma": ("kokoro", "bf_emma", 1.05),  # British
    "en-puck": ("kokoro", "am_puck", 1.05),  # lighter male
    "pt": ("edge", "pt-PT-RaquelNeural", ("+18%", "+0Hz")),  # rate, pitch
    # Raquel's pt-PT delivery converted to the EN narrator's timbre: one narrator across languages.
    "pt-heart": ("edge_vc", "pt-PT-RaquelNeural", ("+15%", "+0Hz", "en_narrator_ref.wav")),
    "pt-user": ("edge_vc", "pt-PT-DuarteNeural", ("+8%", "+15Hz", "pt_ref_clean.wav")),  # the owner's consented voice
    "pt-duarte": ("edge", "pt-PT-DuarteNeural", ("+8%", "+10Hz")),  # stock voice, no conversion
}
# Pronunciation fixes applied only to the TTS input; captions and vo_check keep the real words.
LEXICON = {
    "en": {"Tekla": "[Tekla](/tˈɛklə/)"},  # Kokoro inline phonemes
    "pt": {"Tekla": "Tékla", "Structures": "Strátchures"},
}


def _kokoro(voice: str, speed: float):
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    pipe = KPipeline(lang_code=voice[0], repo_id="hexgrad/Kokoro-82M")

    def say(text: str, path: Path) -> None:
        audio = np.concatenate([a.numpy() for _, _, a in pipe(text, voice=voice, speed=speed)])
        sf.write(path, audio, 24_000, subtype="PCM_16")

    return say


def _edge(voice: str, prosody: tuple[str, ...], convert: bool = False):
    """edge-tts take; with ``convert``, ChatterboxVC to build/voices/<prosody[2]>."""
    import edge_tts
    import soundfile as sf

    if convert:
        import torch
        from chatterbox.vc import ChatterboxVC

        vc = ChatterboxVC.from_pretrained(device="mps" if torch.backends.mps.is_available() else "cpu")
        ref = BUILD / "voices" / prosody[2]

    def say(text: str, path: Path) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mp3, src = Path(tmp) / "src.mp3", Path(tmp) / "src.wav"
            rate, pitch = prosody[:2]
            for attempt in range(4):  # the free endpoint drops the odd request
                try:
                    asyncio.run(edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch).save(str(mp3)))
                    break
                except edge_tts.exceptions.NoAudioReceived:
                    if attempt == 3:
                        raise
                    time.sleep(2 + 3 * attempt)
            audio, sr = sf.read(mp3)
            if not convert:
                sf.write(path, audio, sr, subtype="PCM_16")
                return
            sf.write(src, audio, sr)
            wav = vc.generate(str(src), target_voice_path=str(ref))
        sf.write(path, wav.squeeze(0).cpu().numpy(), vc.sr, subtype="PCM_16")

    return say


def _edge_vc(voice: str, prosody: tuple[str, ...]):
    return _edge(voice, prosody, convert=True)


def _peaking(fc: float, gain_db: float, q: float, sr: int):
    """RBJ cookbook peaking biquad (b, a)."""
    import numpy as np

    a_ = 10 ** (gain_db / 40)
    w = 2 * np.pi * fc / sr
    alpha = np.sin(w) / (2 * q)
    b = np.array([1 + alpha * a_, -2 * np.cos(w), 1 - alpha * a_])
    a = np.array([1 + alpha / a_, -2 * np.cos(w), 1 - alpha / a_])
    return b / a[0], a / a[0]


def _eq(a, sr: int):
    """Promo voice EQ: high-pass the rumble, dip the boom, lift presence (lighter, not thinner)."""
    from scipy.signal import butter, lfilter, sosfilt

    a = sosfilt(butter(2, 90, "highpass", fs=sr, output="sos"), a)
    for fc, g, q in ((220, -3.0, 0.9), (3800, 2.5, 0.8)):
        a = lfilter(*_peaking(fc, g, q, sr), a)
    return a


def _level(path: Path, rms_db: float = -20.0, peak_db: float = -1.0) -> None:
    """EQ and the same VO loudness for every engine/language. No trimming here: vo_check.py trims from the raw take."""
    import numpy as np

    with wave.open(str(path), "rb") as wav:
        params = wav.getparams()
        a = _eq(np.frombuffer(wav.readframes(params.nframes), np.int16).astype(np.float64) / 32768, params.framerate)
    gain = min(10 ** (rms_db / 20) / max(np.sqrt(np.mean(a**2)), 1e-6), 10 ** (peak_db / 20) / max(np.abs(a).max(), 1e-6))
    with wave.open(str(path), "wb") as wav:
        wav.setparams(params)
        wav.writeframes((np.clip(a * gain, -1, 1) * 32767).astype(np.int16).tobytes())


def synth(voice_id: str, only: set[int] | None = None) -> dict[str, float]:
    engine, voice, opt = VOICES[voice_id]
    lang = voice_id.split("-")[0]
    say = {"kokoro": _kokoro, "edge": _edge, "edge_vc": _edge_vc}[engine](voice, opt)
    out = BUILD / "audio" / voice_id
    out.mkdir(parents=True, exist_ok=True)
    dpath = out / "durations.json"
    durations = json.loads(dpath.read_text()) if only and dpath.exists() else {}
    for scene in json.loads((BUILD / "scenes.json").read_text(encoding="utf-8"))["scenes"]:
        if only and scene["n"] not in only:
            continue
        path = out / f"{scene['n']}.raw.wav"  # vo_check.py derives <n>.wav from this
        text = scene["vo"][lang]
        for word, spoken in LEXICON.get(lang, {}).items():
            text = text.replace(word, spoken)
        say(text, path)
        _level(path)
        with wave.open(str(path), "rb") as wav:
            durations[str(scene["n"])] = round(wav.getnframes() / wav.getframerate(), 3)
    dpath.write_text(json.dumps(durations, indent=2))
    return durations


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", nargs="+", default=["en", "pt"], choices=list(VOICES), help="voice ids (see VOICES)")
    ap.add_argument("--scenes", nargs="+", type=int, help="re-synthesize only these scene numbers")
    args = ap.parse_args()
    for lang in args.lang:
        d = synth(lang, set(args.scenes or []))
        assert len(d) == 14 and all(v > 0.3 for v in d.values()), d
        print(lang, d)
