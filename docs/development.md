# For developers

Technical reference for people working on the source code.

## Repository layout

```
src/tekla_nest/                single Python package (project name: tekla-nest)
├── admin/                     admin console (submodule, not a separate package)
├── config/                    YAML configuration loader
├── models/                    dataclasses (CutPiece, StockBar, BarResult, NestResult)
├── presenters/                MVP presenter (providers/services ↔ views)
├── providers/                 part sources (Tekla, CSV, manual entry)
├── services/                  business logic (nest engine, CSV, Tekla API bridge, PDF report)
└── views/                     PySide6 GUI widgets
license-server/                Firebase Functions + Terraform (license server)
├── functions/                 Python Cloud Functions (main.py, requirements.txt)
├── scripts/                   admin_cli.py, deploy.py, generate_keys.py, ...
└── terraform/                 optional IaC for one-time cloud project setup
resources/                     logos, translations (languages/*.yaml), report template
tests/                         test suite (nesting app + admin console)
docs/ + mkdocs.yml              this documentation site
Makefile                        task runner
pyproject.toml                   single package config + ruff/pytest config
```

There is **no `tekla_package/` monorepo and no `tekla-common`/`tekla-admin-console`/`tekla-iac`
sub-packages** — that is an older/aspirational layout that a previous docs pass described but
was never actually built. The nesting app and the admin console share code by both living
inside the one `tekla_nest` package; the license server is its own top-level `license-server/`
folder (not a uv workspace member — it has its own Python dependencies via
`functions/requirements.txt` and is driven by the Firebase CLI, not `uv`).

## Commands

| Command | What it does |
|---|---|
| `make install` | Install runtime dependencies (`uv sync`). |
| `make install-dev` | Install project + dev extras (pytest, pytest-qt, ruff). |
| `make install-all` | Install dev extras + the Windows-only `tekla` extra (pythonnet). |
| `make run` / `make run-admin` | Launch the Nesting app / Admin console. |
| `make demo` | Run the CLI demo with sample data (`CSV=parts.csv` to use your own file). |
| `make lint` / `make format` | Ruff lint / auto-format. |
| `make test` / `make test-fast` / `make test-cov` | Run the test suite (offscreen Qt), a fast subset, or with coverage. |
| `make check` | Lint + test. |
| `make build` | Build wheel + sdist. |
| `make binary` / `make binary-admin` | Standalone PyInstaller executables. |
| `make installer` / `make installer-admin` | Windows installers (needs Inno Setup, `iscc` on PATH). |
| `make installers` | Both installers in one step. |
| `make python-embed` | Windows only: prepare the bundled Python + pythonnet used inside the installer (see [Getting started](getting-started.md#4-windows-notes-path-shims-venvs)). |
| `make infrastructure-package` | Zip `license-server/` (minus secrets/venv) for distribution. |
| `make deploy-infrastructure` | Deploy the license-server Firebase infrastructure — see [Infrastructure](infrastructure.md). Runs `python3.12 scripts/deploy.py`; on Windows run that script directly with `py -3.12 scripts\deploy.py`. |
| `make clean` / `make clean-all` | Remove caches/build artifacts. |
| `make help` | List everything. |

There is **no `make bootstrap` target.** Use `make install` (or `make install-dev` /
`make install-all`) instead.

## Tests

```bash
make test          # QT_QPA_PLATFORM=offscreen uv run pytest
```

- Runs headless (offscreen Qt). `tests/conftest.py` stubs modal dialogs so the suite doesn't
  block waiting for a click.
- Windows/Tekla-specific tests are marked `windows_only` and skipped off Windows:
  `uv run pytest -m "not windows_only"`.

## Code quality

```bash
uv run ruff check .
uv run ruff format .
```

There is currently no `.pre-commit-config.yaml` in this repo — linting/formatting is run
manually (or via CI) with the commands above, not through pre-commit hooks.

## Continuous integration (GitHub Actions)

| Workflow | Runs on | Does |
|---|---|---|
| `build-windows.yml` | Windows | Builds both `.exe` installers + the infra zip; attaches them to a `v*` release, or runs on manual dispatch/push to `main`. |
| `docs.yml` | Ubuntu | Builds this MkDocs site (`mkdocs build --strict`) and deploys it to GitHub Pages on push to `main`. |

There is currently **no lint/test CI workflow** (`ci.yml`) and **no Terraform-validation
workflow** (`iac.yml`) in `.github/workflows/` — run `make check` locally before pushing.
`build-windows.yml` builds on `windows-latest` on every push to `main` and on tags, so it is
exercised regularly (not just before a release).

## Shared runtime data

`config.yaml` and the `resources/` tree (logos, translations, report template) live at the
project root and are bundled with the package. At runtime the base directory resolves next
to the installed package (or `sys._MEIPASS` in a frozen PyInstaller build). Re-brand by
editing the root `config.yaml` and `resources/`, not code.
