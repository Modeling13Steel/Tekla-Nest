---
name: bootstrap-coding-standards
description: >
  Infers this repo's coding conventions (naming, module boundaries,
  error-handling idioms, dependency preferences, commit message style) from
  existing lint/format configs, a representative file sample, and recent
  git log. Dispatched only by harness-orchestrator during bootstrap.
  Do not invoke directly.
tools: [read, bash]
model: cheap
internal: true
---

Read (do not full-scan): `.eslintrc*`, `pyproject.toml`/`ruff.toml`,
`.editorconfig`, `rustfmt.toml`, or equivalent for the detected language(s)
in `.metaharness/repo.json`; a handful of source files chosen for recency
and size diversity, not the whole tree; any existing `CONTRIBUTING.md`,
`AGENTS.md`, or `CLAUDE.md`; `git log --oneline -50` for commit style.

Output one Markdown section titled `## Coding Standards` with: naming
conventions, module boundaries, error-handling idioms, dependency
preferences (stdlib-first vs. framework-heavy), commit message convention.
List every file actually read under `Sources sampled:`. Assign a confidence
0.1-1.0 (cap at 0.7 for inference from a small sample) and
end with `Confidence: <n>`.

Return only this digest -- no raw file contents, no tool-call narration.
