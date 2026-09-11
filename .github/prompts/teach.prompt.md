---
name: mh-teach
description: >
  Invoke when the user runs /teach, or gives an in-the-moment correction
  that reads as a standing preference ("don't use X", "always do Y").
  Works even on hosts with no custom slash-command support (e.g.
  terminal Copilot CLI) -- treat "/teach" as a natural-language trigger,
  not a real registered command, there.
---

# /teach -- record a taught preference for this repo

Trigger: the user says `/teach <text>` or similar, OR you (the host
model) detect an in-the-moment correction mid-task that reads as a
standing instruction rather than a one-off request -- patterns like
"don't use X", "always do Y", "for Z use W instead", "stop doing X".
This is the same rule-based-first, cheap-tier-fallback approach as task
classification: if the pattern is obvious, don't ask; if ambiguous, ask.

1. Extract the actionable rule(s) from the user's text and a short topic
   slug (kebab-case, e.g. `typing-conventions`, `docstrings`). This is a
   small-language-understanding step -- do it yourself, don't regex it.
2. Confirm back to the user before writing, unless they used the explicit
   `/teach` command (already unambiguous):
   "Teaching: <rule> -- for this repo, going forward. Confirm? [y/N]"
3. On confirmation, write it:
   ```
   python3 bin/metaharness_teach.py add <topic> "<rule 1>" "<rule 2>" ...
   ```
   If a prior entry already exists for the same topic, this supersedes it
   (kept, marked superseded) rather than silently duplicating or dropping
   it -- same discipline as the constitution's inferred entries.
4. Run `python3 bin/metaharness_sync.py` so the change is live for the
   *next* subagent dispatch immediately -- no separate "apply" step.
5. `preferences.md` is always-loaded (like the constitution), not
   searched-on-demand -- treat every entry in it as binding for every
   implementation-tier task in this repo, unless the user later
   supersedes it again.

Never write a taught preference into `constitution.md` (that file is
*inferred* from the codebase, re-inferable, and would conflate the two).
Never store it only in conversation memory -- it must persist across
sessions via `preferences.md`.
