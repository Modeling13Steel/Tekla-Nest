# Getting started

This page is the **starting point**. It lists the accounts and tools you need, then points
you to the right place for each task. No prior experience assumed.

## 1. What do you want to do?

| Goal | Go to |
|---|---|
| Use the desktop app to plan steel cuts | [Nesting app](nesting-app.md) |
| Build the app installer (`.exe`) | [Nesting app → building](nesting-app.md) |
| Issue, revoke, release or delete customer licences | [Admin console](admin-console.md) |
| Set up the cloud license server (one time) | [Infrastructure](infrastructure.md) |
| Work on the source code | [For developers](development.md) |

## 2. Accounts you may need

| Account | Needed for | Cost |
|---|---|---|
| **GitHub account** | Getting the code; running the automated builds. | Free |
| **Google / Firebase account** | *Only* if you deploy the cloud license server. | Free tier (a payment card is required, but usage is ~€0 at this scale). |

!!! note
    End users of the desktop app need **no accounts** — they just run the installer.

## 3. Tools to install (for maintainers/developers)

You only need these if you will run the code from source or build/deploy it — **not** for
end users. The table below is the short version; see [§4](#4-windows-notes-path-shims-venvs)
for Windows-specific gotchas (PATH, the Python launcher, venv activation).

| Tool | Why | Where |
|---|---|---|
| **Python 3.12** | Runs the apps and the tooling. The project supports `>=3.9`, but 3.12 is what CI, the Windows build and the license-server scripts use — install 3.12 unless you have a specific reason not to. | <https://www.python.org/downloads/> |
| **uv** | Installs dependencies and manages the virtual environment in one step. | <https://docs.astral.sh/uv/> |
| **Git** | Get and manage the code. | <https://git-scm.com/> |

Only needed if you will **deploy or work on the license server** (`license-server/`):

| Tool | Why | Where |
|---|---|---|
| **Node.js (includes npm)** | The Firebase CLI is distributed as an npm package. | <https://nodejs.org> (LTS) |
| **Firebase CLI** | Deploys the Cloud Functions, manages secrets. Installed with `npm install -g firebase-tools` once Node/npm is present. | <https://firebase.google.com/docs/cli> |
| **Google Cloud CLI (`gcloud`)** | One-time project setup (enable APIs, create the Firestore database, IAM fixes) and auth. | <https://cloud.google.com/sdk/docs/install> |
| **Terraform** *(optional)* | Alternative, scripted way to do the one-time cloud setup instead of manual `gcloud`/Console steps. | <https://developer.hashicorp.com/terraform/install> |

Only needed if you will **build the Windows installer** (see [Nesting app → building](nesting-app.md)):

| Tool | Why | Where |
|---|---|---|
| **Inno Setup** (`iscc` on PATH) | Packages the PyInstaller build into `tekla-nest-setup.exe`. | <https://jrsoftware.org/isinfo.php> |
| **Visual C++ Redistributable** | Bundled with the installer for the target machine; not needed on the *build* machine. | Downloaded automatically by CI. |

The easiest path for the Windows installer is to let **GitHub Actions** build it for you
(push a version tag, or trigger the *Build Windows Packages* workflow manually) — see
[Nesting app](nesting-app.md). Building it locally is only needed if you can't use CI.

## 4. Windows notes: PATH, shims, venvs

These are the gotchas that trip people up on Windows specifically.

### The Python "shim" — two different things share that name here

1. **The `py` launcher**, installed alongside Python from python.org. Windows does **not**
   create a `python3.12.exe`/`python3.exe` the way macOS/Linux package managers do — only
   `python.exe` plus the launcher `py.exe`. Anywhere these docs (or `license-server/GUIDE.md`)
   say `python3.12 <script>`, on Windows use:

    ```powershell
    py -3.12 <script>
    ```

    Check the launcher can see 3.12 with `py -0p` (lists installed versions and paths).

2. **The bundled/portable Python** built by `make python-embed`
   (`scripts/prepare-python-embed.ps1`, Windows only). This downloads the official Python
   *embeddable* package, enables `site-packages`, and installs `pythonnet` into it. It is
   **not** for running project scripts — it is copied into the installer so the frozen
   `tekla-nest.exe` has a real Python + `pythonnet`/CLR bridge available at runtime for the
   Tekla Structures Open API integration (PyInstaller-frozen apps can't load `pythonnet`
   directly). You do not need to run this yourself unless building the installer locally —
   CI does it automatically.

### PATH

After installing each tool above, confirm it's on `PATH` in a **new** terminal (PATH
changes don't apply to already-open shells):

```powershell
py -0p                 # Python launcher sees your installs
uv --version
git --version
node --version && npm --version
firebase --version
gcloud --version
iscc /?                # Inno Setup (only if building the installer locally)
```

If a tool was "installed" via `winget`/`choco` but still isn't found, open a new terminal —
these installers update the *system* `PATH`, which existing shells don't pick up.

### Virtual environments

`uv sync` / `uv run` create and use a `.venv/` automatically — you generally don't need to
activate it manually. If you do (e.g. to run a plain `python` command inside it):

```powershell
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

If PowerShell refuses to run the activation script ("running scripts is disabled on this
system"), that's the execution policy — either use `uv run <command>` instead of activating
at all, or run PowerShell scripts for this repo with:

```powershell
powershell -ExecutionPolicy Bypass -File <script>.ps1
```

(this is exactly how `make python-embed` invokes `prepare-python-embed.ps1`).

## 5. One-time setup (developers/maintainers)

From the repository root:

```bash
make install       # or: uv sync                — runtime dependencies
make install-dev    # + dev tools (pytest, pytest-qt, ruff)
make run            # launches the Nesting app
make run-admin       # launches the Admin console
make help            # shows every available command
```

On Windows without `make` (e.g. plain Command Prompt), run the underlying `uv`/`uv run`
commands shown after each target directly, or use Git Bash/WSL where `make` works normally.

That's it — you now have a working environment. Continue on the page for your task. Setting
up the **license server** or building the **Windows installer** need the extra tools listed
in [§3](#3-tools-to-install-for-maintainersdevelopers) — see
[Infrastructure](infrastructure.md) and [Nesting app](nesting-app.md) respectively.
