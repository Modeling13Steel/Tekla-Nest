# Demo video pipeline — Nest, by M13S

Generates demo videos automatically from code. Nobody screen-records anything and nobody edits by hand.
`script-master.md` is the only file a person writes; every other step reads from it.

```
script-master.md ──► review loop (4 reviewer agents) ──► FAIL → revise script from findings, re-review
        │ PASS
        ▼
scenes.py ─► build/scenes.json
sample model (model.py): 4-storey steel frame, 556 members ─► build/model.json
   ├─► 3D render inside Remotion (@remotion/three)
   └─► part list ─► mock Tekla provider ─► real app, headless (capture.py; widget.grab())
tts.py: one voice id per language (+ variants) ─► build/audio/<voice>/ ─► vo_check.py (Whisper QA, trims tails)
sfx.py: Mixkit whooshes / hit / click / pop, filtered, levels baked in ─► build/sfx/
music.py: Mixkit bed, levelled to -20 LUFS, bar grid + outro point ─► build/music/bed.{wav,json}
        ▼
Remotion assembly ─► master: measured gain + peak limiter (-2.5 dBFS), re-measured once ─► build/out/<cut>-<voice>.mp4
        ▼
audio_report.py: VO/SFX/music stem histograms + timeline + LUFS/true peak
                (gates: SFX p95 and ducked music p50 ≤ VO p50 − 12 dB; -14 ±1 LUFS; ≤ -1 dBTP)
        ▼
review loop again on the rendered video (frames + Whisper transcript + measured durations + audio report)
```

**Rollout:** first one pilot (full cut, EN). Once it passes review, render all six: 3 cuts × pt/en.

## Brand identity (taken from the repo)

| | Value | Source |
|---|---|---|
| Product name | **Nest, by M13S** (en: "Nest. By M thirteen S."; pt: "Nest. Da Éme treze ésse."). Tekla Structures is only the compatible host ("Works with Tekla Structures 2021–2026"), never the product. "Tekla Nest" is only the repo name, so never use it on screen. | user brief, `config.yaml` |
| Company | M13S | `config.yaml` report.company_name |
| Primary / strong | `#1d4ed8` / `#173b6c` (dark theme: `#3b82f6` / `#1d4ed8`) | `src/tekla_nest/design_system/tokens.py` |
| Accent / cyan | `#0f766e` / `#0891b2` (dark: `#14b8a6` / `#22d3ee`), the same three colours as the logo bars | tokens.py, `resources/logo_horizontal.svg` |
| Dark bg / light bg | `#0b1220` / `#f6f8fb` | tokens.py, `config.yaml` |
| Video palette | The app's dark identity: navy `#0b1220` → `#070b14` canvas with slow drifting glows in blue `#3b82f6`, teal `#14b8a6` and cyan `#22d3ee`, a faint blueprint grid and a vignette; light scenes on `#f6f8fb`. Text `#f8fafc` / muted `#94a3b8`; key words in a blue→cyan gradient. Teal = your own stock, blue/cyan = market stock and general. The app itself keeps its shipped theme. | tokens.py |
| Type | The app UI renders in its shipped font (Segoe UI, from `config.yaml`). Video type is **Geist** (OFL; 600 headlines, tracking −0.03 em) with **Geist Mono** for numbers. | config.yaml |
| Motion | `cubic-bezier(0.16,1,0.3,1)`; 0.4 s overlapping push / wipe / zoom transitions; words spring in from a blur; app windows enter in 3D and float with depth, shadow and a glow; numbered step chips (01 Import … 07 Export) | styles.css, `video/remotion/src/root.tsx` |
| Logo | The configured logo `config.yaml` → `resources/logo_outline.png`, traced to `resources/logo_outline.svg` from the white letter fill (upscaled 8×, potrace; the old alpha trace merged the outline into the letters and blobbed the small text). On the navy canvas it is filled soft off-white `#dbe4f0` (`build/brand/logo_soft.svg`), with a subtle cyan sweep. The intro and the end card use the same layout, so the film opens and closes on the same card. | `config.yaml`, `resources/` |
| Languages | pt-PT (default), en | `resources/languages/` |
| UI labels | Renders come from the real app only (the `docs/ui-mocks/` have different labels and a placeholder "TN" mark). Labels to quote: **Load Tekla**, **Client Stock**, **Auto Stock**, **Calculate**, **Purchase** / *Stock to purchase*, **Export PDF**, **Excel** (pt: *Carregar Tekla*, *Calcular*, *Exportar PDF*) | `resources/languages/*.yaml` |

**Sound identity.** Energetic but clean: a music bed carries the pace, the voice always on top.
- Music: "Motivating Mornings" (Mixkit, 123 BPM), ducked about 16 dB under the VO (6-frame attack,
  12-frame release), spliced on a downbeat into the track's own ending so it resolves on the end card.
- SFX (all Mixkit): a soft whoosh on every transition (two alternating, timed so the peak lands mid-transition),
  an impact on the logo and the big number, UI clicks on real clicks, light pops on cards. No beeps or chimes.
- SFX and ducked music sit at least 12 dB under the voice, verified by `video/audio_report.py` (level histograms).
- **Licence:** Mixkit Stock Music / Sound Effects Free License: free for commercial use, no attribution, but
  the files may not be redistributed on their own. They are downloaded into `video/build/cache/` (git-ignored), never committed.

**Tone.**
- Short declaratives, one idea per line, a brisk rhythm on the music; confident and warm, never hyped.
- Attention beats: cold open, a rhetorical question, "Introducing…", one huge number, a triad payoff,
  a tagline that answers the opening line.
- Talk about the benefit, not the feature. No jargon on screen, no claims we can't prove.
- pt-PT copy is written natively (see `review-log.md`, "v10 pt-PT research"), never translated from EN.
- No third-party trademark notice or watermark on screen.

## Voices

| Persona | Voice | Notes |
|---|---|---|
| `narrator` | en: Kokoro (Apache-2.0) `af_heart` at 1.05× (bright, not deep). pt-PT default `pt`: edge-tts `pt-PT-RaquelNeural` at +18 % rate (native pt-PT accent; chosen in round 4 after the user rejected the cloned voice). Every take gets the same voice EQ (90 Hz high-pass, −3 dB at 220 Hz, +2.5 dB at 3.8 kHz); `vo_check.py` trims from the untouched `<n>.raw.wav` with a natural decay and fails any take whose last 20 ms are louder than −45 dB (a chopped ending). | One persona per video. **Variants** (full cut, `tts.py` `VOICES`): `pt-heart` (Raquel converted with ChatterboxVC (MIT) to the EN narrator's timbre, reference `build/voices/en_narrator_ref.wav` built from the EN takes; same narrator in both languages, slightly less clear), `pt-user` (Duarte converted to the consented speaker in `build/voices/pt_ref_clean.wav`), `pt-duarte` (stock Duarte), en `en-bella`, `en-emma` (British), `en-puck` (lighter male). Deep voices such as `am_michael` are excluded. Never clone a voice without that person's consent. Chatterbox Multilingual alone drifted to pt-BR; Piper `tugão` was unintelligible to Whisper on 4/10 lines (see `build/voice-lab/index.md`). **Licensing:** edge-tts uses an unofficial free endpoint; for commercial distribution switch to the Azure Speech free tier (same voice). |

## Business value (every VO line must trace to one of these)

1. **Less scrap:** the optimizer beats hand nesting, and steel is expensive.
2. **Minutes, not hours:** from Tekla model to cut plan without spreadsheet work.
3. **No re-entry errors:** parts come straight in from Tekla Structures.
4. **Real-world accurate:** kerf and scrap threshold are configurable.
5. **Shop-floor ready:** PDF, Excel or CSV output.
6. **Fits the existing workflow:** sits next to Tekla, works offline once activated, Windows installer.
7. **Your stock first:** import your own stock (CSV); it is always consumed before market stock, which fills the gaps.
8. **Know what's yours and what to order:** the Purchase tab lists every bar the plan uses, by source (Client / Market), with bar count and linear metres.
9. **Best of six:** the optimizer tries six strategies and keeps the best plan.

## Tekla visuals

The sample model is generated. Real Tekla import needs Windows and a licensed copy of Tekla, so for now
the same part list is fed to the app through a mock provider. That keeps the model and the app's numbers
consistent.

**Never recreate Tekla's own UI.** Real Tekla screenshots will come from one Windows session: import the
same IFC into Tekla and capture it there.

## Review loop

The loop is defined in `review-loop.md`. Each iteration's findings go to `review-log.md`.

## How to run

```sh
python3 video/scenes.py                                    # script-master.md -> build/scenes.json
uv run python video/model.py                               # sample frame -> build/model.json
for l in en pt; do for t in light dark; do uv run python video/capture.py --lang $l --theme $t; done; done
uv run --no-project --python 3.11 --with "kokoro>=0.9.4" --with "transformers>=4.44" --with soundfile --with scipy --with pip python video/tts.py --lang en
uv run --no-project --python 3.11 --with chatterbox-tts --with edge-tts --with soundfile --with scipy python video/tts.py --lang pt
uvx --from faster-whisper --with soundfile python video/vo_check.py --lang en pt   # Whisper match + chop gate
cd video/remotion && npm ci && npm run audio-assets       # SFX + music bed (downloads from Mixkit once)
for c in teaser short full; do for l in en pt; do npm run render -- --props="{\"lang\":\"$l\",\"cut\":\"$c\",\"cta_url\":\"\"}"; done; done
cd ../.. && uv run --no-project --with numpy --with soundfile --with matplotlib --with pyloudnorm --with scipy --with imageio-ffmpeg python video/audio_report.py --cut full --lang en pt
```

Outputs go to `video/build/out/<cut>-<voice>.mp4`, which is git-ignored. Voice variants: run `tts.py`/`vo_check.py` with `--lang pt-heart pt-user pt-duarte en-bella en-emma en-puck`, then render with `"voice":"pt-heart"` in the props. Pass a real `cta_url` once it's known.
