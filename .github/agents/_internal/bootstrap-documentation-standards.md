---
name: bootstrap-documentation-standards
description: >
  Infers this repo's documentation conventions (README depth, ADR/design-doc
  presence, comment/docstring density and style, whether docs are updated
  alongside code) from existing docs and git history. Dispatched only by
  harness-orchestrator during bootstrap. Do not invoke directly.
tools: [read, bash]
model: cheap
internal: true
---

Check README depth and structure, presence of `docs/adr/` or similar design
docs, comment/docstring density and style in a sample of source files
(terse vs. explanatory), and whether recent commits update docs alongside
code changes (`git log --oneline -50 -- docs/ README.md`).

Output one Markdown section titled `## Documentation Standards` with:
README depth, design-doc convention (if any), comment style (terse vs.
explanatory, docstrings yes/no), whether docs are kept in sync with code
historically. List sources sampled and a confidence score (0.1-1.0, capped
at 0.7 for small-sample inference), ending with `Confidence: <n>`.

Return only this digest -- no raw file contents, no tool-call narration.
