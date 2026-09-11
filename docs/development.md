# For developers

Technical reference for people working on the source code.

## Repository layout

```
tekla_package/                 uv workspace (monorepo)
├── tekla-nest/                desktop nesting app        (package: tekla_nest)
├── tekla-admin-console/       admin console              (package: tekla_admin)
├── tekla-common/              shared foundation          (package: tekla_common)
│   └── src/tekla_common/{config, design_system, theme.py, i18n.py,
│                          widgets/, config.yaml, resources/}
├── tekla-iac/                 Firebase Functions + Terraform (license server)
├── tests/                     test suite (all packages)
├── docs/ + mkdocs.yml         this documentation site
├── Makefile                   task runner
├── pyproject.toml             workspace root + ruff/pytest config
└── .pre-commit-config.yaml
```

- `tekla-nest` and `tekla-admin-console` **both depend on `tekla-common`** (shared config,
  branding, translations, design system) via a uv **workspace** path dependency.
- `tekla-iac` is independent (Firebase Functions manage their own `requirements.txt`).

## Commands

| Command | What it does |
|---|---|
| `make bootstrap` | Install all packages + dev tools (`uv sync`). |
| `make run` / `make run-admin` | Launch the Nesting app / Admin console. |
| `make lint` | Ruff lint (`ruff check`). |
| `make format` | Ruff auto-format. |
| `make test` | Run the test suite (offscreen Qt). |
| `make docs-serve` | Preview this docs site locally. |
| `make docs-build` | Build the static docs site (`--strict`). |
| `make clean` | Remove caches/build artifacts. |
| `make help` | List everything. |

## Tests

```bash
make test          # QT_QPA_PLATFORM=offscreen uv run pytest
```

- Runs headless (offscreen Qt). A top-level `tests/conftest.py` stubs modal dialogs so the
  suite never blocks in CI.
- Windows/Tekla-specific tests are marked `windows_only` and skipped off Windows:
  `uv run pytest -m "not windows_only"`.

## Code quality

```bash
uv run pre-commit install     # enable hooks on every commit
uv run pre-commit run --all-files
```

Hooks: **ruff** (lint + format), file hygiene, **detect-private-key**, and **terraform fmt**
for `tekla-iac`.

## Continuous integration (GitHub Actions)

| Workflow | Runs on | Does |
|---|---|---|
| `ci.yml` | Ubuntu | Ruff lint + format check + tests. |
| `iac.yml` | Ubuntu | `terraform fmt`/`validate` + Functions syntax check. **Never deploys.** |
| `build-windows.yml` | Windows | Builds the `.exe` installers + infra zip; attaches to a `v*` release. |
| `docs.yml` | Ubuntu | Builds this site and deploys it to GitHub Pages. |

!!! warning "Windows build not yet validated on-runner"
    `build-windows.yml` is a faithful port of the original build, adapted to the monorepo,
    but it has **not** been executed on a Windows runner yet. Validate it once on GitHub's
    `windows-latest` before relying on it for a release.

## Shared runtime data

`config.yaml` and the `resources/` tree (logos, translations, report template) are bundled
**inside `tekla-common`**. At runtime the base directory resolves to the `tekla_common`
package (or `sys._MEIPASS` in a frozen build) — see `tekla_common/config/app_config.py`.
Re-brand by editing `tekla-common/src/tekla_common/config.yaml`, not code.
