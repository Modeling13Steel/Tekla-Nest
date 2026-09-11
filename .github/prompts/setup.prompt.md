---
name: mh-setup
description: >
  Invoke when the user runs /setup, or asks in plain language to view or
  change meta-harness policy for this repo (persona, trace log, quorum,
  model tiers, loop budgets). Works even on hosts with no custom
  slash-command support (e.g. terminal Copilot CLI) -- treat "/setup" as
  a natural-language trigger, not a real registered command, there.
---

# /setup -- edit this repo's meta-harness policy

Trigger: the user runs `/setup`, or says something like "run setup",
"change the harness config", "what's the persona set to". Do the
following, conversationally, in the user's own words -- do not just dump
JSON at them.

1. Run `python3 bin/metaharness_setup.py list` and read the five policy
   files back to yourself (classifier tiers/rules, model-tiers mapping,
   quorum trigger/strategy/voters, loop-budgets ceilings, config
   trace_log/persona).
2. Summarize the current settings in plain language, grouped by what they
   control (task classification, model cost, when a quorum kicks in, loop
   ceilings, session logging/persona). Keep it short -- a few lines per
   file, not a JSON dump.
3. Ask the user what they want to change. Common asks: turn trace_log
   on/off, change persona (ponytail/caveman/none), raise or lower
   quorum voters, change which paths are high-stakes, adjust loop budgets.
4. For each change, call:
   `python3 bin/metaharness_setup.py set <file>.<field> <value>`
   Use `<file>` in {classifier, model-tiers, quorum, loop-budgets, config}
   and `<field>` matching a top-level JSON key in that file. Values that
   look like JSON (numbers, booleans, arrays, objects) are parsed as JSON;
   anything else is stored as a plain string.
5. After applying changes, run `list` again and confirm back to the user
   in plain language what changed (old value -> new value), not raw JSON.
6. Never hand-edit the JSON files directly -- always go through
   `bin/metaharness_setup.py` so changes are validated against known keys.
