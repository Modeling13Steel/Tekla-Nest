# Getting started

This page is the **starting point**. It lists the accounts and tools you need, then points
you to the right place for each task. No prior experience assumed.

## 1. What do you want to do?

| Goal | Go to |
|---|---|
| Use the desktop app to plan steel cuts | [Nesting app](nesting-app.md) |
| Build the app installer (`.exe`) | [Nesting app → building](nesting-app.md) |
| Issue or revoke customer licences | [Admin console](admin-console.md) |
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
end users.

| Tool | Why | Where |
|---|---|---|
| **Python 3.12** | Runs the apps. | <https://www.python.org/downloads/> |
| **uv** | Installs everything in one step. | <https://docs.astral.sh/uv/> |
| **Git** | Get and manage the code. | <https://git-scm.com/> |

For **building the Windows installer** you also need Windows with PyInstaller + Inno Setup —
but the easiest path is to let **GitHub Actions** build it for you (see the
[Nesting app](nesting-app.md) page). For **deploying the license server** you need extra
cloud tools — see [Infrastructure](infrastructure.md).

## 4. One-time setup (developers/maintainers)

From the `tekla_package/` folder:

```bash
make bootstrap    # installs all four parts + the developer tools (via uv)
make run          # launches the Nesting app
make run-admin    # launches the Admin console
make help         # shows every available command
```

That's it — you now have a working environment. Continue on the page for your task.
