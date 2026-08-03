# Nesting app

The **Nesting app** is the desktop program your team uses day-to-day. It takes a list of
steel parts and works out how to cut them from stock bars with the least waste, then
produces a printable cutting plan.

## What it does

- Reads the parts to cut from **Tekla Structures** (directly, on Windows) or from a **CSV** file.
- Calculates an optimal 1D cutting plan (which pieces come from which bar).
- Exports the plan as **HTML, PDF or Excel**.

## For end users

### Install

1. Get the installer file **`tekla-nest-setup.exe`** (from your maintainer, or the GitHub
   *Releases* page).
2. Double-click it and follow the prompts.
3. Launch **Tekla Nest** from the Start menu.

### Use it (in a nutshell)

1. **Load parts** — click *Import from Tekla* (Windows + Tekla running) **or** *Load CSV*.
2. Add or auto-generate the **stock** bars you cut from.
3. Click **Calculate**.
4. **Export** the plan as PDF, Excel or CSV.

!!! note "Licence"
    On first use the app may ask for a licence key (issued by an administrator — see the
    [Admin console](admin-console.md)). Once activated it keeps working offline.

## For maintainers (running from source)

Prerequisites: **Python 3.12**, **uv**, **Git** (see [Getting started](getting-started.md)).

```bash
# from the tekla_package/ folder
make bootstrap     # one-time: install everything
make run           # launch the Nesting app  (= uv run tekla-nest)
```

| Command | Does |
|---|---|
| `make bootstrap` | Install all parts + tools. |
| `make run` | Launch the Nesting app. |
| `make test` | Run the tests. |
| `make lint` | Check code style. |

## Building the Windows installer

The installer is **built on Windows** (it needs PyInstaller + Inno Setup + a bundled Python
with `pythonnet`). The easy, supported way is **GitHub Actions** — you don't need a Windows
PC yourself:

1. Push a version tag, e.g. `git tag v2.1.0 && git push --tags` — **or** open the repo on
   GitHub → *Actions* → **Build Windows Packages** → *Run workflow*.
2. When it finishes, download **`tekla-nest-setup.exe`** from the workflow's *Artifacts*
   (a tagged run also attaches it to the GitHub *Release*).

!!! warning
    The installer **cannot** be built on macOS or Linux. Use the GitHub Action (or a
    Windows machine with Inno Setup). This workflow is a port of the original build and
    should be validated once on a Windows runner — see [For developers](development.md).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| *Import from Tekla* is greyed out | Tekla integration needs **Windows + Tekla Structures (2021–2026)** running. On other systems, use **Load CSV**. |
| App won't start after building from source | Run `make bootstrap` again; confirm Python 3.12. |
| Asks for a licence | Get a key from an administrator ([Admin console](admin-console.md)). |
