# Script: Nest, by M13S — master scene list (v12 — benefit-led, explicit context)

The only hand-written video file. All cuts and languages render from this one table.

- **Focus (v12):** the product is **Nest** and what it gains the customer: less steel bought, no re-typing,
  own stock used first, a ready purchase list, files for the shop. Say plainly what Nest is and who it is for
  (cut optimization for steel fabricators). Tekla appears only as where the parts come from and as
  "works with", never as the subject of a scene.
- **Tone:** a confident product launch with energy. Short declaratives, one idea per line, a quick
  rhythm carried by the music: cold open, a rhetorical question, "Introducing…", a fast product tour,
  one big number, a triad payoff, and a tagline that answers the opening line. Voices are bright and
  brisk, never deep (EN ≈ 2.6 words/s); sentence endings ring out, never clipped (`vo_check.py` gate).
- **Cuts** filter on `P` (priority): teaser ≤15 s = P1 · short ≤30 s = P1+P2 · full ≤70 s = all (raised from 60 s in v12 to give the benefits room).
- **Renders** come from the **real app** run headless (`widget.grab()`), loaded with the generated frame.
  Never use `docs/ui-mocks/`. On-screen app labels are whatever the app shows in that language.
- **Look (brand):** the app's own identity on a deep navy canvas `#0b1220` with soft moving glows in brand
  blue `#3b82f6`, teal `#14b8a6` (your own stock) and cyan `#22d3ee`, a faint blueprint grid, and light
  scenes on `#f6f8fb`. App renders float in a framed window with depth, shadow and a glow, placed left,
  right or centre so the composition moves. Type is **Geist** (600, tracking −0.03 em), numbers in
  **Geist Mono**, key words in a blue→cyan gradient. Step chips (01 Import … 07 Export) mark the tour.
  Logo = `resources/logo_outline.svg`.
- **Motion:** overlapping transitions (0.4 s) named in *Transition in*: `fade`, `slide-left`,
  `slide-up`, `wipe`, `zoom`, `cut`. Every transition gets a soft whoosh (alternating two sounds),
  added automatically. Brand ease `cubic-bezier(0.16,1,0.3,1)`; words spring in with a blur-to-sharp.
- **Music:** "Motivating Mornings" (Mixkit, free licence, 123 BPM) under the whole film, ducked about
  15 dB under the VO, and edited on a bar line into its own ending so it resolves on the end card.
- **Scene length** = max(`~s`, 0.25 s lead + VO + 0.55 s); the next transition overlaps the tail.
  In the CTA the VO starts at 0.7 s, after the logo hit, and the end card holds 1.2 s after it.
- **VO** is written as spoken ("M thirteen S"); **Caption** as read ("M13S"). Voice is `narrator`.
- **SFX** tokens are `name@t` (t = fraction of the scene where the sound *peaks*) from `click`, `pop`, `hit`; `—` means none.
- `*words*` in a caption are set in the blue→cyan brand gradient.
  All SFX sit ≥ 12 dB under the VO (checked by `video/audio_report.py`).
- The demo-booking URL is still to be supplied. Until then the end card shows only "Book a demo" — never a placeholder.
- No third-party trademark notice or watermark on screen.

## Scenes

| # | Beat | Render | Interaction / motion | Transition in | SFX | VO (EN, spoken) | Caption (EN) | P | ~s |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Cold open | Navy canvas, glows. A bright steel bar sweeps across the frame | The saw cut flashes; the offcut drops away and fades | fade | pop@0.30 | "Steel is expensive. Scrap costs even more." | Steel is expensive. *Scrap* costs even more. | 3 | 3.2 |
| 2 | Pain | Navy. Three short pains set word by word, big | Words spring in on the VO; the last pain in the gradient | slide-up | — | "Cut lists by hand. Parts typed twice. Offcuts forgotten." | Cut lists by hand. Parts typed twice. *Offcuts forgotten.* | 3 | 3.4 |
| 3 | Introducing | Mirrors the end card: navy, glow, the soft-white logo at end-card size, "Nest" in the tagline slot and what it is, muted, in the button slot | Logo lands on the hit exactly like the end card; light sweep; "Nest", then the subline, spring in as spoken | zoom | hit@0.10 | "Introducing Nest, by M thirteen S. Cut optimization for steel fabricators." | *Nest* · Cut optimization for steel fabricators | 1 | 4.2 |
| 4 | Straight in | 3D render of the generated frame on `#f6f8fb`, chip "Tekla Structures" (the source) | Orbit; a selection sweep lights members in blue | wipe | — | "Parts come straight from your Tekla model. No re-typing." | Straight from your model. *No re-typing.* | 3 | 3.4 |
| 5 | Import | Real app, light theme, window right, headline left, chip 01 | Window glides in; punch-in on **Load Tekla** click → parts table fills | slide-left | click@0.34 | "One click. Every part, grouped." | One click. *Every part.* | 3 | 2.8 |
| 6 | Your stock first | Real app: **Client Stock** CSV fills the Client tab; window left, headline right, teal, chip 02 | Punch-in on **Client Stock** → the Client tab fills | slide-left | click@0.26 | "Your own stock is used first. You only buy what's missing." | Your stock. *Used first.* | 2 | 3.8 |
| 7 | Market fills the gaps | Real app: **Auto Stock** fills the Market tab; window centred, blue, chip 03 | Punch-in on **Auto Stock** → the Market tab fills | slide-left | click@0.24 | "Market lengths fill the gaps, automatically." | Market stock *fills the gaps.* | 2 | 2.8 |
| 8 | Best plan wins | Navy: a huge "6" counts up in Geist Mono, "strategies", then "1 plan"; then the real result, chip 04, punch-in on **Overall waste** | Number lands on the hit; push into the app on "best plan" | wipe | hit@0.10 click@0.62 | "Six strategies, in seconds. The best plan wins." | 6 strategies. 1 plan. | 1 | 3.4 |
| 9 | Your rules | Real app result + Suggestions; window right, chip 05 | Punch-in on Suggestions, then on the high-waste warning (roof-canopy RHS) | slide-left | pop@0.55 | "Your kerf, your scrap rules, and a warning before a costly cut." | Your rules. *Warned in time.* | 3 | 4.0 |
| 10 | Purchase list | Real app **Purchase** tab, window centred, chip 06 | Punch-in on the table, then the total | slide-left | — | "A purchase list: what you have, and what to order." | Yours, or *to order.* | 3 | 3.4 |
| 11 | Export | Real app report → **Export PDF**, **Excel**, **CSV**; window left, chip 07 | Three cards pop out (labels exactly PDF, Excel, CSV) | slide-left | pop@0.30 pop@0.52 pop@0.74 | "Export cut plans to P D F, Excel, or C S V." | PDF · Excel · CSV | 3 | 3.4 |
| 12 | Fit | Light `#f6f8fb`: small eyebrow "Works with", then "Tekla Structures 2021–2026", Windows, offline lines | Lines slide up one after the other | slide-up | — | "Works with Tekla Structures, 2021 to 2026." | Works with: Tekla Structures 2021–2026 · Windows installer · Offline once activated | 3 | 3.2 |
| 13 | Payoff | Navy. Three lines, one at a time, big; the previous line dims | Each line springs in on its VO beat | fade | — | "Less steel wasted. Less time on paperwork. More margin on every job." | Less steel wasted. / Less paperwork. / More margin. | 3 | 4.0 |
| 14 | Tagline + CTA | Navy, glow. Logo (soft white), the tagline, then "Book a demo" as a button | Logo lands on the hit, tagline follows, button pops on the CTA | zoom | hit@0.05 | "Every cut, planned. Book a demo." | Every cut, *planned.* · Book a demo | 1 | 3.5 |

## pt-PT VO and captions

Written natively in European Portuguese, not translated (sources and vocabulary table in
`review-log.md`, "v10 pt-PT research"): *ficheiro*, *oficina*, *stock*, *sobras*, *largura de corte*,
*sem Internet*, *agendar*, possessives always with the article (*as suas*), and the app's real labels.

| # | VO (pt-PT, spoken) | Caption (pt-PT) |
|---|---|---|
| 1 | "O aço é caro. O desperdício custa mais." | O aço é caro. O *desperdício* custa mais. |
| 2 | "Listas à mão. Peças escritas duas vezes. Sobras esquecidas." | Listas à mão. Peças escritas duas vezes. *Sobras esquecidas.* |
| 3 | "Apresentamos o Nest, da Éme treze ésse. Otimização de corte para a metalomecânica." | *Nest* · Otimização de corte para a metalomecânica |
| 4 | "As peças vêm direto do modelo Tekla. Sem copiar à mão." | Direto do modelo. *Sem copiar à mão.* |
| 5 | "Um clique. Todas as peças." | Um clique. *Todas as peças.* |
| 6 | "O seu stock é usado primeiro. Só compra o que falta." | O seu stock. *Sempre primeiro.* |
| 7 | "O stock de mercado completa o resto." | O mercado *completa o resto.* |
| 8 | "Seis estratégias, em segundos. Fica o melhor plano." | 6 estratégias. 1 plano. |
| 9 | "A sua largura de corte, as suas regras. E um alerta antes do corte." | As suas regras. *Alertas a tempo.* |
| 10 | "Uma lista de compras: o que já tem, e o que tem de encomendar." | Em stock, ou *a encomendar.* |
| 11 | "Exporte os planos de corte em PDF, Excel ou CSV." | PDF · Excel · CSV |
| 12 | "Compatível com o Tekla Structures, de 2021 a 2026." | Compatível com: Tekla Structures 2021–2026 · Instalador Windows · Sem Internet depois de ativado |
| 13 | "Menos aço desperdiçado. Menos papelada. Mais margem em cada obra." | Menos aço desperdiçado. / Menos papelada. / Mais margem. |
| 14 | "Cada corte, planeado. Peça uma demonstração." | Cada corte, *planeado.* · Pedir demonstração |

## Cuts

| Cut | Scenes | Measured s (EN / PT) | Ceiling |
|---|---|---|---|
| Teaser | 3, 8, 14 | 12.0 / 14.9 | 15 |
| Short | 3, 6, 7, 8, 14 | 20.0 / 23.6 | 30 |
| Full | 1–14 | 54.8 / 66.0 | 70 |
