# M0 · Baseline

> Milestone 0 of the UI refactor. Companion to `docs/ui-mocks/ROADMAP.md` §2.

## What this milestone does

Locks the floor we must not regress below for the rest of the refactor, and
installs the lightweight tooling (ruff, pytest-cov, LOC budget guard) that
keeps later milestones honest.

**Zero behaviour change** in the application. No production code touched
beyond removing one unused local variable in a test.

## Artefacts committed

| Path | Purpose |
|---|---|
| `docs/ui-mocks/baseline/loc.txt` | Lines of code per source file at the start of the refactor. Reviewers diff against this in M2/M9 to confirm `nest_window.py` shrinks from **446 → ≤ 300 LOC**. |
| `docs/ui-mocks/baseline/test-floor.txt` | Test count at start: **240 passed**. Every milestone must grow this number — see §9 of the roadmap for per-milestone targets. |
| `docs/ui-mocks/baseline/coverage.txt` | Total coverage at start: **70 %**. New files added in later milestones must launch ≥ 85 %, and existing-file coverage must not drop. |
| `scripts/check_loc.py` | LOC budget guard. Fails the build when a file exceeds the budgets in `ROADMAP.md` §10.3. Mirrors the table in code so reviewers don't need to memorise it. |
| `pyproject.toml` (updated) | Adds `ruff>=0.6` and `pytest-cov>=5` to `dev`; adds `[tool.ruff]` and `[tool.coverage.*]` config blocks. |

## Tooling decisions explained

### Why ruff (not flake8 / black / isort)
Ruff replaces all three in a single, fast binary with zero config overhead.
We can promote rules incrementally without changing the tool. M0 keeps the
ruleset narrow (`E`, `F`, `W`) to focus on real bugs; M9 promotes to
`E F W I B UP SIM` once the team is used to the workflow.

### Why pytest-cov (not coverage.py directly)
pytest-cov integrates with the existing pytest invocation. No new CLI to
learn — `pytest --cov=tekla_nest` works alongside `pytest -q`.

### Why a custom LOC script instead of a ruff rule
LOC budgets are per-path, not global. Ruff's `max-doc-length` and friends
work line-by-line; they cannot enforce "this file may have at most 300
total lines". A 60-line Python script is simpler than a plugin and lives
in the repo under reviewer control.

## Validation gate (passing at M0 close)

```
.venv/bin/python -m ruff check src tests        # All checks passed!
.venv/bin/python -m pytest -q                   # 240 passed in 2.60s
.venv/bin/python -m pytest --cov=tekla_nest -q  # TOTAL 70%
.venv/bin/python scripts/check_loc.py           # LOC budgets OK.
```

## Notes for reviewers

- **Screenshots are intentionally not captured here.** The roadmap calls
  for capturing on Windows at 100/125/150 % DPI in EN+PT. macOS dev hosts
  cannot reproduce Windows native chrome faithfully, so screenshots are
  delegated to a Windows runner and stored under `docs/ui-mocks/v2.1/`
  during M9 (where they are compared against this M0 floor).
- **One incidental fix**: `tests/unit/test_app_config.py` had an unused
  local `c1 = load_config(...)` flagged by ruff `F841`. Replaced with a
  bare call. No behaviour change.
- **No floor for `nest_window.py` LOC yet.** The LOC guard accepts the
  current 446 lines so M1 doesn't fail. M2 lowers the budget to 320; M9
  to the final 300.

## What unblocks next

Every subsequent milestone consumes M0's tooling, so any branch may now
rely on:

- `ruff check` being green,
- coverage reports being produced,
- the LOC guard being authoritative.
