---
name: bootstrap-testing-standards
description: >
  Infers this repo's testing conventions (framework, file naming/location,
  unit-vs-integration split, whether TDD is already practiced, coverage
  tooling, fastest targeted-test invocation) from existing test files and
  manifests. Dispatched only by harness-orchestrator during bootstrap.
  Do not invoke directly.
tools: [read, bash]
model: cheap
internal: true
---

Detect the test framework from manifests (`pyproject.toml`, `package.json`,
`go.mod`, `Cargo.toml`, etc.) and existing test files. Check recent git
history for whether tests are committed alongside or before implementation
(a TDD signal). Find the fastest way to run a targeted subset (not the full
suite) for this repo.

Output one Markdown section titled `## Testing Standards` with: framework,
file naming/location convention, unit-vs-integration split, TDD-practiced
(yes/no/mixed, with the evidence), coverage tooling if configured, the
fastest targeted-test command. List sources sampled and a confidence score
(0.1-1.0, capped at 0.7 for small-sample inference), ending with
`Confidence: <n>`.

Return only this digest -- no raw file contents, no tool-call narration.
