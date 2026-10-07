# Review log

## Iteration 1: script v1 → **FAIL**

| Reviewer | Verdict | Score |
|---|---|---|
| quality-brand | fail | 4 |
| delivery | fail | 6 |
| customer-response | fail | 5 |
| duration | fail | 6 |

### Blockers and majors, and what v2 changed

**quality-brand**
- **Scenes 4, 5, 7, 8 (blockers).** The UI mocks show labels the app doesn't have (`Load Parts`,
  `Auto-Stock`, `⇩ PDF`, `cle…`) and an invented "TN" logo mark.
  → **All renders now come from the real app run headless.** The mocks are not used. The real app
  already has the Insights panel, Overall waste, dark theme and command palette.
- **Scene 6 (major).** "Utilization" isn't a real stat. → Uses the real **Overall waste** stat and the
  Insights warnings.
- **Scene 9 (major).** Dark mode has no payoff chips. → They're now an explicit brand overlay on a
  blurred app background.
- **Scene 10 (major).** The inverse logo uses lightened bar tints. → Not changed. It's the existing
  dark-background variant, so the README brand table now documents it.

**delivery**
- **Scene 1 (blocker).** The em dash is a TTS hazard. → "Every cut becomes a part, or scrap."
- **Teaser (major).** It reads as an importer, not a cut-plan tool. → Scene 4 VO is now "…turns Tekla
  parts into a cut plan", and its render ends with cut bars.
- **pt-PT hazards (major).** → Added a pt-PT VO and caption table, using European Portuguese terms
  ("oficina", "folhas de cálculo"). The brand name is spoken as "Eme treze esse".
- **Minor.** Scene 3 → 4 is now a match cut instead of a whoosh, and scene 9's caption is split over
  three lines.

**customer-response**
- **CTA (blocker).** There was none. → "Book a demo" plus `{cta_url}`.
- **Scene 5 (blocker).** "Least waste" overclaims. → "compares strategies and picks the lowest-waste
  plan".
- **Scenes 2, 6, 9 (majors).** These were unprovable claims. Changes:
  - The market claim is gone.
  - "Matches your saw" became "your kerf and scrap rules".
  - "Minutes, not hours" became "No spreadsheet work".
- **Scene 7 (major).** "Keystroke" wasn't a business value. → It's now the Tekla 2021–2026
  compatibility and offline scene (value 6).
- **Unused strengths (major).** → Scene 6 now shows the high-waste and add-stock warnings.
- **Minor.** Scene 8 now includes CSV.

**duration**
- **Teaser (blocker).** It was 15.9–16.3 s in PT. → Now 14.0 s: the CTA VO is "Book a demo." and the
  logo speaks the name.
- **Short (major).** It had a margin of only 0.37 s. → Now 28.5 s.
- **Scene 6 (minor).** → VO shortened to 11 words.

### Conflicts resolved (priority: duration > brand/legal > customer > delivery)

- **Scene 5.** Delivery wanted no UI labels in the VO. Customer and duration were fine with them, and
  the labels match what's on screen. → Kept the labels.
- **Scene 10.** Customer wanted a "20-minute demo, use your Tekla model" CTA. → Rejected: it's a promise
  we can't verify, and it costs teaser time.

## Iteration 2: script v2 → **FAIL** (findings narrowed from 30 to 9)

| Reviewer | Verdict | Score |
|---|---|---|
| quality-brand | fail | 6 |
| delivery | fail | 6 |
| customer-response | fail | 7 |
| duration | fail | 6 |

### What v3 changed

- **delivery, scene 8 (blocker).** Piper may misread "PDF" and "CSV". → The VO now spells them out:
  "P D F" / "C S V" in EN, "Pê Dê Éfe" / "Cê Ésse Vê" in pt-PT. The captions are unchanged.
- **delivery, scene 7 pt (major).** "offline" is a loanword. → "sem Internet".
- **delivery, scene 3 pt (major).** The pt-PT voice may mispronounce "Structures". → The VO says
  "no Tekla". The caption keeps the full name.
- **customer, scene 5 (blocker).** "lowest-waste plan" still overclaims, because the engine ranks
  unfit pieces and stock priority before waste. → "compares strategies to reduce waste".
- **brand, scene 5 pt (major).** The VO didn't use the app's real label. → "Auto stock, depois
  Calcular".
- **brand, global (major).** The README tokens (from the mocks) didn't match the shipped app.
  → **Rejected the suggested fix of re-theming the app**, because the video would then misrepresent the
  shipped product. Instead the README brand table now uses the shipped tokens from `tokens.py` and
  `config.yaml` (light background `#f6f8fb`, Segoe UI in the app). Captions use Inter (OFL), since
  Segoe UI can't be freely used for rendering on Linux/macOS.
- **duration (major and minor).** → Scene 10 is now 3.3 s and scene 2 is 6.1 s. Scene 5 is 7.0 s
  after its VO got shorter.
- **New totals:** teaser 14.3 s, short 28.3 s, full 55.4 s (sums checked by script).

## Iteration 3: script v3 → **2 pass / 2 fail** (budget reached)

| Reviewer | Verdict | Score |
|---|---|---|
| quality-brand | fail | 6.5 |
| delivery | **pass** | 9 |
| customer-response | **pass** | 9 |
| duration | fail | 6 |

### What v4 changed (no blockers left, 3 majors and 1 minor fixed)

- **duration, scene 8 (major).** Spelling out "P D F" and "C S V" made the line 15 spoken words long,
  which needs 8.75 s. → "Export to P D F, Excel or C S V, shop-floor ready." (12 words), and the scene is
  now 7.2 s. The pt-PT VO drops "o plano".
- **duration, scene 7 (minor).** → 5.6 s.
- **brand, scene 1 (major).** The dark-theme cyan is `#22d3ee`, not `#0891b2`. → Fixed, and the README
  table now includes it.
- **brand, scene 7 (major).** The "Offline" chip was hard-coded in English. → The chip now uses each
  language's caption text.
- **Check.** The duration rule was re-run by script on v4: every scene passes. Teaser 14.3 s, short
  28.5 s, full 55.7 s.

**Budget status.** All three iterations are used. v4's remaining fixes are mechanical, were checked
deterministically, and don't conflict with each other. A fourth agent review round needs a human
decision.

**Open inputs needed before rendering:**
- `{cta_url}`
- The legal wording for the trademark line
- Confirming the Piper voices by listening

## Iteration 4: script v4, a human-approved confirmation round → **PASS**

| Reviewer | Verdict | Score |
|---|---|---|
| quality-brand | **pass** | 9 |
| duration | **pass** | 9 |
| delivery | **pass** (iteration 3; v4's changes to it were mechanical) | 9 |
| customer-response | **pass** (iteration 3) | 9 |

**The script gate is closed.** Next is the pilot render (full cut, EN), followed by the render-gate
review.

# Render gate

## R1: pilot `full-en.mp4` (script v4, 56.7 s) → **FAIL**

| Reviewer | Verdict | Score | Key findings |
|---|---|---|---|
| quality-brand | fail | 4 | Raw i18n key `report.filter.all` on screen (app bug); UI too small to read (no punch-ins); tint washes out the UI; caption covers content; scene 2 rows over the headline; internal label in scene 3; small scene 7 card with an inconsistent logo; "XLS" instead of "Excel"; `{cta_url}` placeholder visible |
| delivery | fail | 6 | Scene 8 VO drops "ready"; "Less scrap" heard as "Let's scrap"; 2–3.6 s dead air per scene; CTA VO too short and early |
| customer-response | fail | 6 | No on-screen proof of less waste; kerf/scrap rules said but not shown; 39.89 % high-waste number sits next to "Less waste" |
| duration | fail | 6 | Teaser measured at 15.3 s (> 15); slack pacing |

**Fixes (v5):**
- App: merged the duplicate `report:` key in `en.yaml`/`pt.yaml`, plus a regression test.
- Script: scene lengths tightened (full 48.6 s, teaser 13.7 s est.). VO 8 is now "Export P D F, Excel, and C S V files, ready for the shop floor."; VO 9 is now "Reduce scrap…"; VO 10 is now "Book your M thirteen S Nest demo.", delayed 1 s.
- Scene 5 ends on a readable Overall waste punch-in (the proof).
- Scene 6 is captured with kerf 3 mm and scrap 2 000 mm, shown as a chip; 39.89 % appears only inside the warning beat.
- Composition: per-target punch-ins, a caption-safe gutter, tint reduced, scene 2 clipped, label removed, horizontal logo in scene 7, "Excel" label, URL omitted while it's a placeholder, scene 9 chips used as the captions.

**Separate finding:** the pt-PT Piper voice (`tugão`) isn't intelligible; Whisper large-v3 garbles 4 of 10 lines. Switching pt-PT to Chatterbox Multilingual (MIT).

## User feedback round → script v7–v8 (Apple-style rewrite)

The user asked for: quieter, professional SFX; own-stock import plus the market top-up in the pitch; pt-PT (not pt-BR)
in the user's cloned voice; the configured logo as SVG; Geist type; a clean Apple intro; and slower attention-beat
delivery. Changes: Kenney CC0 SFX baked low and checked by `video/audio_report.py` (≥12 dB under the VO); a 14-scene
Apple structure (cold open → question → "Introducing" → triad → tagline); pt-PT via Edge Duarte + ChatterboxVC to
the reference voice; `logo_outline.svg`. The script gate passed at iteration 2 (v8).

## R3: script v8, iteration 1 → **FAIL** (all 4)

| Reviewer | Key findings |
|---|---|
| quality-brand | S5 ring on Load CSV, not Load Tekla; S4 model overlaps the caption; S11 ring vs. cards out of sync |
| delivery | PT CTA "Marque" heard as "Mas com" (blocker); PT diction lines 1, 2, 5–7, 9, 10, 12–14; Tekla pronunciation; music bed wanted; CTA too small |
| customer | "Stock to buy" overclaims, since the Purchase tab lists all bars used (blocker); 14.8 % overall and 39.4 % warning undercut the pitch |
| duration | PT S12 8.6 s (> 8); PT S2 too fast; PT teaser margin 0.3 s |

**Fixes (v9):** the capture settles the toolbar before measuring; demo client CHS stock 84 × 8000 gives 7.3 % overall waste,
with one real high-waste warning on a small roof-canopy RHS; S10 now reads "yours, or to order"; PT rewrites; a TTS-only
pronunciation lexicon; model scale 5.6; S11 phases 0.52/0.74; CTA +25 % and synced to the VO.
App bugs fixed along the way: Purchase source shown as "Cliente/Mercado" in EN; an unrounded insight percentage;
EN stock headers "Quant." / "Comp. (mm)".

**Trade-offs:** the PT CTA is spoken as "Agende uma demo." and the caption says "Agendar demonstração", because the spoken
long form pushed the PT teaser past 15 s (duration > delivery). Music bed: escalated to the user, since it needs a licensed source
(MusicGen weights are non-commercial). "Less scrap" kept: 7.3 % waste is on screen and best-of-six keeps the lowest-waste plan.

## R3: script v9, iteration 2 → **PASS** (all 4, after a delivery-only 2b)

| Reviewer | Verdict | Score | Notes |
|---|---|---|---|
| quality-brand | pass | 9 | S5, S4 and S11 all resolved |
| duration | pass | 8.8 | EN 13.10 / 24.40 / 75.50 s; PT 13.43 / 25.13 / 80.67 s; PT S12 7.93 s (≤ 8) |
| customer | pass | 8 | Minor: no market-only "to order" subtotal in the app; "Less scrap" has no manual baseline |
| delivery | fail → pass (2b) | 8.1 | PT S4 → "Dentro do Tekla", PT S10 → "Mostra as barras que já tem. E as que tem de encomendar." (picked by A/B through the voice chain + Whisper) |

Open minors: music bed (escalated); a market-only subtotal in the Purchase tab (app feature idea); PT "Sem Internet" is
sometimes heard as "Sem interesse" by Whisper, while the caption is clear.

## User feedback round 2 → script v10 (lively, music, native pt-PT)

The user preferred the earlier, livelier pace and graphics over the Apple-calm v9 and asked for:
- a music bed;
- richer transitions, positioning and sound design;
- lighter voices that don't chop sentence endings;
- pt-PT written from real Portuguese copy, not translated;
- no Tekla trademark line on the end card.

**Changes (v10):**
- **Script:** rewritten from native pt-PT research (the voice of Portuguese PME and industry sites):
  - "O seu stock", "Stock de mercado", "ficheiro", "Prontos para a oficina", "Agende uma demo".
  - `*word*` gradient highlights.
  - Full-cut ceiling lowered to 60 s.
- **Visuals:**
  - Dark brand canvas with drifting blue/teal/cyan glows, a grid and a vignette.
  - Kinetic words that spring in from a blur.
  - App windows enter in 3D and float.
  - Numbered step chips.
  - Overlapping 0.4 s push, wipe and zoom transitions.
  - End card with no legal line.
- **Sound:**
  - Mixkit music bed, ducked by about 16 dB under the VO and spliced on a downbeat into the track's own ending.
  - Mixkit whooshes timed so they peak mid-transition, plus an impact, UI clicks and pops.
  - Short cuts skip the track's quiet intro.
- **Voices:**
  - EN Kokoro `af_heart` at 1.05×.
  - PT edge DuarteNeural at +8 % / +15 Hz, then ChatterboxVC.
  - Shared voice EQ (cuts the low-mid "boom", adds presence).
  - `vo_check` trims from the raw take and fails any take with a non-silent tail; every tail is now ≤ −72 dB.
- **Master:** two-pass loudness with a re-measure.
- **`audio_report`:** gains a music stem and a `music_ducked` gate.

## R4: script v10, iteration 1 → **2 pass / 2 fail**

| Reviewer | Verdict | Score | Findings |
|---|---|---|---|
| quality-brand | pass | 9 | none |
| duration | pass | 8.6 | Minor: EN S10 at 2.7 words/s; measured lengths missing from the script's Cuts table |
| customer | fail | 6.5 | Major: PT S4 "Dentro do Tekla" overclaims a plugin, since the app sits next to Tekla. Minors: no market-only subtotal; get a native PT listen before publishing |
| delivery | fail | 6.6 | Majors: PT CTA "Agende uma demo" heard as "Dajendo/Na agenda"; PT S6 own-stock line garbled. Minors: PT S5 and S9 wording |

**Fixes (v10.1).** Only the PT lines 4, 5, 6, 9 and 14 and EN line 10 were re-synthesized:

| Scene | Before | After |
|---|---|---|
| PT 4 | "Dentro do Tekla." | "No Tekla." |
| PT 5 | "Um clique. Todas as peças, agrupadas." | "Um clique. Todas as peças." |
| PT 6 | "Traga o seu stock num ficheiro CSV…" | "Importe o seu stock em CSV…" |
| PT 9 | "…um alerta antes de cortar." | "…Um alerta antes do corte." |
| PT 14 | "Agende uma demo." (caption "Agendar demonstração") | "Peça uma demonstração." (caption "Pedir demonstração") |
| EN 10 | "See which bars are yours, and which to order." | "See what's yours, and what to order." |

The market-only subtotal is an app feature idea, not a video fix.

## User feedback round 3 → v11

Feedback: liked the PT version, the music, the transitions and the ending. Asked for:

- PT opening "O aço é caro. O desperdício custa mais."
- The product is **Nest, by M13S**; Tekla is only the compatible host.
- The intro should look like the ending.
- A line break after each sentence in the Suggestions tab.
- PDF, Excel and CSV export stated, replacing "pronto para a oficina".
- A crisper, softer logo.
- Several voice versions.

| Change | Where |
|---|---|
| PT 1 "O aço é caro. O desperdício custa mais." | script-master.md |
| PT 3 "Apresentamos o Nest. Da Éme treze ésse." / EN 3 "Introducing Nest. By M thirteen S." (caption *Nest*) | script-master.md |
| PT 11 "Exporte em PDF, Excel e CSV." / EN 11 "Export to PDF, Excel, and CSV." | script-master.md |
| PT/EN 12 "Compatível com o Tekla, de 2021 a 2026…" / "Works with Tekla, 2021 to 2026…" (on-screen eyebrow "Compatível com" / "Works with") | script-master.md, `Fit` in root.tsx |
| The intro (scene 3) uses the end card's layout: same logo size and position, bloom and sweep, with "Nest" in the tagline slot | `Introducing` in root.tsx |
| Logo re-traced from the white letter fill (upscaled 8×, potrace). On the navy canvas it is drawn in off-white `#dbe4f0`, with the bloom capped at 0.75 and the sweep at 0.6 | `resources/logo_outline.svg`, prepare-assets.mjs, style.css |
| Suggestions: newline after each ". " (test first) | `insight_sidebar.py`, `test_insight_sidebar.py` |
| Voice variants (full cut): en-bella, en-emma, en-puck, pt-raquel (+18 % rate to stay under 60 s), pt-duarte (no VC) | tts.py `VOICES`, `voice` prop |

VO QA: all takes had no chop and a match of at least 0.88. The LOW flags were Whisper artefacts:

- en-puck S8: Whisper wrote "6 Strategies 1 Best Plan" in digits.
- PT S6 and S7: Whisper heard pt-BR "estoque".

## User feedback round 4 → v12

Feedback: the video was not explicit enough and needed more context. The focus should move from Tekla to Nest (the plugin) and what it gains the customer. EN was almost picture-perfect; PT was not. The user liked the EN voice and disliked the PT voice.

| Change | Where |
|---|---|
| Script rewritten benefit-led. S2 names the pain (hand lists, parts typed twice, offcuts forgotten). S3 says what Nest is ("Cut optimization for steel fabricators" / "…para a metalomecânica"). Every app scene states a gain. S13 sums up: less steel wasted, less paperwork, more margin. Tekla appears only as the source (S4) and "works with" (S12). | script-master.md v12 |
| Full ceiling raised from 60 s to 70 s so the benefits have room | script-master.md, review-loop.md |
| Intro: the name goes in the tagline slot; a 56 px subline explains what Nest is | `Introducing` in root.tsx, style.css |
| PT layout: headlines and questions break one sentence per line; the 3D model moved right so its caption never collides | `Words`, `ModelScene` |
| PT voice: the default is now edge `pt-PT-RaquelNeural` at +18 %. Variant `pt-heart`: Raquel voice-converted to the EN narrator's timbre. The old cloned voice is kept as `pt-user`. | tts.py `VOICES` |
| Teaser only: shorter breath and end-card hold, so teaser-pt fits 15 s | `buildTimeline` |

### Render gate R5

Quality-brand, delivery and duration passed. Customer failed on one point: S8 "The least waste wins" overclaims, because Nest ranks plans by unfit parts first, then client stock, then waste.

| Fix (v12.2) | Where |
|---|---|
| S8 → "Six strategies, in seconds. The best plan wins." / "Seis estratégias, em segundos. Fica o melhor plano." | script-master.md |
| App chrome title "M13S Nest" → "Nest" | root.tsx |
| S12 support lines enlarged (62 px, darker) | style.css `.fitSub` |
| Teaser end-card hold 0.6 s → 0.45 s (duration reviewer) | `buildTimeline` |

`pt-heart` stays comparison-only: it is less clear than Raquel.

Deferred: a "to order" subtotal overlay on the purchase table (S10).

R5 iteration 2: customer PASS. All four reviewers pass. Measured (EN / PT): teaser 12.0 / 14.9 s, short 20.0 / 23.6 s, full 54.8 / 66.0 s (pt-heart 67.4 s); every audio gate passes.
