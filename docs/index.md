# Tekla Nest — Documentation

Welcome. This site explains how to **install, run, build, deploy and administer** the
Tekla Nest product family.

## The four parts

Everything lives in one repository (`tekla_package/`), split into four folders:

| Part | What it is | Who touches it |
|---|---|---|
| **Nesting app** | The desktop program that optimises steel-bar cutting. | End users; whoever builds the installer. |
| **Admin console** | Desktop tool to issue and revoke software licences. | An administrator. |
| **Infrastructure (license server)** | The small cloud service that checks licences. | An operator, once, to deploy it. |
| **Shared foundation** (`tekla-common`) | Common code, branding, translations. | Nobody directly — used by the apps above. |

## Where to go next

- **Just want to get set up?** → [Getting started](getting-started.md)
- **Using or building the desktop app?** → [Nesting app](nesting-app.md)
- **Managing licences?** → [Admin console](admin-console.md)
- **Deploying the cloud license server?** → [Infrastructure](infrastructure.md)
- **A developer working on the code?** → [For developers](development.md)

!!! note "Not very technical? Start here"
    Read **[Getting started](getting-started.md)** first — it lists exactly which accounts
    and tools you need, in plain language, before anything else.
