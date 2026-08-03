# Tekla Package

Monorepo for the **Tekla Nest** product family, ready to ship to the client.

## What's inside

| Folder | What it is | Ships to |
|---|---|---|
| [`tekla-nest/`](tekla-nest/) | Desktop **Nesting** application (1D steel-bar cutting optimisation) | Customer PCs (Windows installer) |
| [`tekla-admin-console/`](tekla-admin-console/) | **Admin Console** — issue / revoke / manage licences | Administrators (Windows installer) |
| [`tekla-common/`](tekla-common/) | **Shared** foundation (config, design system, theme, i18n, resources) | Used by the two apps above |
| [`tekla-iac/`](tekla-iac/) | **Infrastructure** — Firebase Functions + Terraform (license server) | Cloud (deployed by an operator) |

> `tekla-nest`, `tekla-admin-console` and `tekla-common` form a **uv workspace**.
> `tekla-iac` is independent (Firebase Functions with their own `requirements.txt`).

## Documentation

Full, non-technical documentation (accounts to create, build & deploy roadmap, Makefile
commands) is published to **GitHub Pages** and also lives in [`docs/`](docs/).

## Quick start (developers)

```bash
make bootstrap     # install everything (uv)
make lint          # ruff lint
make test          # run tests (offscreen Qt)
make docs-serve    # preview the docs site
make help          # list all commands
```

## Notes

- The Windows installers are built on **Windows** (or in CI) — they need `pythonnet`,
  PyInstaller and Inno Setup. Development, linting and tests run on any OS.
- `tekla-iac` deployment (Firebase / Terraform) is a **manual, operator-run** step — see
  the docs for the exact accounts to create and commands to run.
