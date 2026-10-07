# Review loop

Four reviewer agents run in parallel at two gates:
- **Script gate:** reviews `script-master.md`, before anything is rendered.
- **Render gate:** reviews the rendered video. Each reviewer gets frames at 2 fps, the Whisper
  transcript, and the measured scene durations.

If any reviewer's verdict doesn't match the intent below, the findings go back into a regeneration and
**all four reviewers run again**. Re-running all of them catches a fix that breaks something another
reviewer checks.

## Intent (what "pass" means)

> A 15–70 s, lively launch-style product pitch (brisk pace on a ducked music bed, attention beats, rich brand motion and
> transitions, bright non-deep voices that never clip a word, native pt-PT copy, no watermark) that makes a steel fabricator's estimator or production manager
> want a demo of **Nest, by M13S**. It must say plainly what Nest is and who it is for, and every scene must be about a
> customer gain (less steel bought, no re-typing, own stock first, a ready purchase list, files for the shop). Tekla
> appears only as the source of the parts and as "works with", never as the subject. Show only real UI and real brand
> assets, in pt-PT and en; the PT film must be as polished as the EN one (no caption collisions or cramped wraps).

## Reviewers

| Reviewer | Checks | Hard fail if |
|---|---|---|
| **quality-brand** | Name, colours, type, logos and motion match the README brand table. UI labels are the real ones. Nothing is invented or off-brand. Each scene has a single clear visual idea. | "Tekla Nest" appears anywhere on screen; a UI label doesn't exist in `resources/languages/*.yaml`; Tekla's UI is recreated |
| **delivery** | VO reads naturally aloud. Transitions and SFX follow the beats. Captions are legible. The narrative flows (hook → problem → reveal → payoff → CTA). **Every cut still makes sense on its own.** | A cut contains a dangling reference, e.g. "them" with no antecedent; a line is hard to say aloud (for TTS or for a person) |
| **customer-response** | Plays the target buyer (estimator or production manager at a steel fabricator) and asks: would I book a demo? Is every VO line traceable to the README value list? Are claims provable? Is there a clear CTA? Will it land in pt-PT? | A claim can't be backed by the product; there's no CTA; a business value is missing from the full cut |
| **duration** | Words per scene against the budget (EN 2.6 words/s, PT ×1.25). Each cut against its ceiling, **measured in PT** (the longer language). Pacing is brisk (the user asked for a livelier film): scenes 2–7 s, about 0.4 s of air after each VO line, the music carries the rhythm. | Any cut's measured PT length goes over its ceiling (teaser 15 s, short 30 s, full 70 s) |

## Reviewer output contract (YAML only)

```yaml
reviewer: <name>
iteration: <n>
verdict: pass | fail        # fail if any hard-fail rule triggers OR score < 7
score: <0-10>
matches_intent: true | false
findings:
  - scene: <# or "global" or cut name>
    severity: blocker | major | minor
    issue: <what is wrong>
    fix: <a concrete rewrite: new VO text, new priority, new duration, etc.>
```

## Loop rules

1. Run all 4 reviewers in parallel on the current artifact.
2. **All four pass and `matches_intent: true`** → move to the next stage.
3. **Otherwise** → apply every blocker and major `fix`. Minors are optional.
   - Bump the script version and record the changes in `review-log.md`.
   - Go back to step 1 with a fresh set of reviewers. Each one gets the previous iteration's findings so
     it can check that they were fixed.
4. **Budget: 3 iterations.** If the script still fails after the third, stop and escalate the
   remaining blockers to a human. Never loop silently past the budget.
5. If two reviewers' fixes contradict each other (for example, delivery wants more words and duration
   wants fewer), the hard ceilings win: **duration > brand/legal > customer > delivery**. Log the
   trade-off.
