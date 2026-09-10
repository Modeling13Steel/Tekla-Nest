---
name: mh-harness-trace
description: >
  Invoke when the user runs /harness-trace on|off|show, or asks why the
  harness made a decision (tier, model choice, quorum vote). Works even
  on hosts with no custom slash-command support (e.g. terminal Copilot
  CLI) -- treat "/harness-trace" as a natural-language trigger, not a
  real registered command, there.
---

# /harness-trace -- toggle or inspect the decision trace log

Trigger: the user says `/harness-trace on|off|show [task-id]` or asks why
a decision was made. An append-only, opt-in, per-session log of *why*
the harness decided what it decided -- classifier tier, router model
choice, proposal + approval, quorum votes, review findings, evolution
promotions. Off by default; never re-read into the model's own context
automatically.

## `on` / `off`

Toggle for this repo:

```
python3 bin/metaharness_setup.py set config.trace_log on
python3 bin/metaharness_setup.py set config.trace_log off
```

For a single debugging session without changing the repo default, tell
the user you'll emit trace lines for this session only by passing
`--session <this session id>` explicitly to `metaharness_state.py trace`
calls this session, without flipping the repo config.

## Emitting a trace line (any stage, as a side effect of work already done)

After a classifier/router/proposal/quorum/review/evolution decision,
append one line -- this call is always safe to make (it no-ops when
`trace_log` is off, so don't gate it yourself):

```
python3 bin/metaharness_state.py trace --session <id> --stage <classifier|router|proposal|quorum|review|evolution> \
    --task-id <t> --fields '{"tier": "complex", "reason": "..."}'
```

## `show <task-id>` (or no task-id for the whole session)

Render matching lines for the user, human-readable, without loading them
into your own working context beyond quoting the relevant lines back:

```
python3 bin/metaharness_state.py trace-show --session <id> [--task-id <t>]
```

If asked "why did it pick sonnet for that rename" or similar, this is the
command to run -- don't guess from memory.
