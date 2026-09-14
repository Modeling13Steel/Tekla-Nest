# Tekla Nest — Documentation

Welcome. This site explains how to **install, run, build, deploy and administer** the
Tekla Nest product family.

## The three parts

Everything lives in **one repository**, split into three parts:

| Part | What it is | Who touches it | Lives in |
|---|---|---|---|
| **Nesting app** | The desktop program that optimises steel-bar cutting. | End users; whoever builds the installer. | `src/tekla_nest/` (single Python package) |
| **Admin console** | Desktop tool to issue, revoke and delete software licences. | An administrator. | `src/tekla_nest/admin/` (submodule of the same package) |
| **Infrastructure (license server)** | The small cloud service that checks licences. | An operator, once, to deploy it. | `license-server/` (Firebase Functions + Terraform) |

There is no separate `tekla-common`/`tekla-admin-console` package — the nesting app and the
admin console share code by living in the same `tekla_nest` package (config, i18n,
branding, resources are shared modules under `src/tekla_nest/`).

## Where to go next

- **Just want to get set up?** → [Getting started](getting-started.md)
- **Using or building the desktop app?** → [Nesting app](nesting-app.md)
- **Managing licences?** → [Admin console](admin-console.md)
- **Deploying the cloud license server?** → [Infrastructure](infrastructure.md)
- **A developer working on the code?** → [For developers](development.md)

!!! note "Not very technical? Start here"
    Read **[Getting started](getting-started.md)** first — it lists exactly which accounts
    and tools you need, in plain language, before anything else.
