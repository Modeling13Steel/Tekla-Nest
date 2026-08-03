# Tekla Common

Shared foundation library for the Tekla Nest product family.

Contains code and runtime data used by **both** the Nesting app and the Admin Console:

- `config/` — loads `config.yaml` into a validated singleton
- `design_system/` — colour tokens, palette, accessibility, motion, brand helpers
- `theme.py` — builds the Qt application stylesheet
- `i18n.py` — English/Portuguese translations (from `resources/languages/`)
- `widgets/toolbar.py` — the shared branded toolbar
- `config.yaml` + `resources/` — branding, logos, languages, report template (bundled as package data)

Both `tekla-nest` and `tekla-admin-console` depend on this package via the uv workspace.
Not shipped to end users on its own.
