---
spec: spec-0001
feature: ui-design-system
---

# UX Design Decision Record - UI Design System

## Objective

Define the UX strategy for a lightweight PySide6 design system for Tekla Nest before mockups or implementation begin. This record captures the rationale behind target devices, accessibility strategy, reusable states, loading behavior, current UI evidence, and governance expectations.

## Context

Tekla Nest is a Windows desktop PySide6 application for fabrication planners optimizing stock and cuts and reviewing nesting outputs. This spec does not redesign individual workflows or implement production UI. It establishes the design-system foundation that later implementation specs can use.

No `DESIGN.md`, design-system documentation, or `docs/project/tech-stack.md` content exists. The UX strategy therefore relies on:

- the PM brief;
- the pitch intent;
- current PySide6 source observations;
- user-provided UX decisions gathered during UX Brief;
- WCAG 2.2 AA-aligned accessibility practice;
- Qt accessibility expectations;
- later Figma work in UX Mockups.

## Significant UX Decisions

### Decision: Use Windows desktop as the target design context

The design system targets Windows desktop with a 1440px baseline, 1366px minimum width, and common high-DPI scaling.

Rationale:

- The pitch scope is Windows with Tekla integration.
- Current UI evidence shows a desktop QMainWindow and table-heavy workflow.
- Fabrication planning work benefits from readable density and wide layouts.

Alternatives rejected:

- Mobile-first design: rejected because there is no mobile scope.
- Fully responsive multi-platform system: rejected because expansion beyond Windows is out of scope.

Section 13 reference: Q-018.

### Decision: Use the table-heavy planning path as the primary proof path

The first proof path should cover import, optimize, stock/part review, and report-adjacent surfaces, with dialogs, licensing, and toolbar/status patterns represented as coverage examples.

Rationale:

- The current app is table-heavy.
- Tables expose the most important consistency risks: sorting, search/filtering, selection, batch actions, density, loading, empty, error, and partial-result states.
- Report preview and activation/licensing are important adjacent surfaces but should not turn this design-system spec into a detailed workflow redesign.

Alternatives rejected:

- Starting with activation/licensing only: too narrow for a design system.
- Starting with all workflows in detail: out of scope and too large for this spec.

Section 13 reference: Q-019.

### Decision: Require full reusable-state coverage

Reusable patterns must define default, loading, empty, error, success, disabled/unavailable, validation-error, permission-denied, and partial-result states where applicable.

Rationale:

- The design system must support resilient modernization, not just happy-path visual polish.
- Table-heavy and long-running optimization contexts require robust state handling.
- Explicit states improve QA, accessibility review, and implementation handoff.

Alternatives rejected:

- Happy-path-only component examples: rejected because they leave critical engineering and usability behavior undefined.
- Error/loading-only states: rejected because disabled, permission, validation, empty, success, and partial-result states are equally important in desktop production tools.

Section 13 reference: Q-020.

### Decision: Use context-dependent loading patterns

Blocking work should use progress indicators with clear text. Table/control-level work should use inline busy states. Skeleton-like placeholders should be used only where layout stability helps.

Rationale:

- Optimization, activation, and report generation may block user action and need clear feedback.
- Inline busy states are less disruptive for localized table or control updates.
- Skeletons can reduce layout shift but may be misleading in dense engineering tables if they imply unavailable data structure.

Alternatives rejected:

- One global spinner pattern: too blunt for mixed blocking and non-blocking desktop interactions.
- Skeletons everywhere: too visually noisy and potentially misleading for precise tabular data.

Section 13 reference: Q-021.

### Decision: Treat Tekla Structures as presentation influence, not a palette source yet

Tekla Structures should influence Tekla Nest through professional engineering presentation qualities: clarity, restraint, hierarchy, data density, and trustworthiness. Exact colors and screenshots must be captured later in UX Mockups before palette adoption.

Rationale:

- The PM brief permits public Tekla product imagery/docs and current Tekla Nest UI as inputs.
- Exact screenshots and palette evidence are not yet ready.
- Avoiding direct copying reduces risk of unverified brand or product UI replication.

Alternatives rejected:

- Copy Tekla Structures UI directly: out of scope and not evidence-validated.
- Ignore Tekla Structures entirely: rejected because the pitch explicitly asks for translated influence.

Section 13 references: Q-002, Q-014.

### Decision: Evaluate two visual direction tracks before production palette adoption

UX Review keeps the current prototype unblocked, but future production visual adoption should compare two explicit tracks:

- **Plan A - Tekla schema dependent:** use exact Tekla screenshots and palette samples supplied through `docs/specs/spec-0001/references/tekla-screenshots/` or attached in the workshop session, then extract semantic token roles and validate accessibility before adoption.
- **Plan B - Modern application UI kit benchmark:** evaluate contemporary desktop/product UI-kit patterns as benchmarks for command bars, tables, dialogs, focus, density, and state feedback without silently adopting a third-party design system or dependency.

Rationale:

- The user asked for both a Tekla-schema-dependent plan and a state-of-the-art modern application UI-kit plan.
- Splitting the tracks keeps Q-025's evidence requirement explicit without blocking UX Review.
- Comparing both tracks gives Product, UX, and Engineering a controlled way to choose Tekla-dependent, modern benchmark, or hybrid direction later.

Alternatives rejected:

- Adopt current prototype tokens directly for production: rejected because exact Tekla evidence is still missing.
- Adopt a modern UI kit silently: rejected because external patterns require Section 13 rationale and PySide6 feasibility review.

Section 13 references: Q-022, Q-025.

### Decision: Refine UX Review prototype toward a modern SaaS/data-product visual direction

The UX Review prototype should move away from the original current-app blue/orange schema and use a modern SaaS/data-product direction for artifact refinement: off-white/slate surfaces, deep blue primary actions, teal/cyan accents, compact rounded controls, strong table readability, and restrained status color use.

Research basis:

- Awwwards' colorful-design guidance recommends a limited 3-5 color set and careful background choice because color changes mood/tone and can become distracting or unprofessional when mixed poorly.
- Awwwards' clean-design guidance emphasizes careful, precise positioning and elegance even when a page contains many elements.
- Awwwards' minimal-design guidance emphasizes balance, alignment, and contrast.
- Awwwards' typography guidance emphasizes consistent type use for readability.
- Awwwards' data-visualization guidance emphasizes making complex data engaging and easier to understand.
- Awwwards' gradient guidance supports vibrant gradients mainly as secondary elements such as hovers, titles, icons, and other accents rather than primary application surfaces.

Rationale:

- The user rejected the previous color schema during UX Review.
- The selected direction better fits dense table-heavy engineering workflows than a colorful or dark-first direction.
- The palette remains independent from final Tekla palette adoption, which still requires Q-025 evidence.

Alternatives rejected:

- Continue with the current-app `#1a73e8` / `#ff6d00` schema: rejected by user feedback.
- Move to a dark-accent premium direction: not chosen because it increases contrast and density risk for long desktop planning sessions.
- Copy an Awwwards site or adopt a web UI kit directly: rejected because the prototype must remain PySide6-feasible and professional for fabrication planning.

Section 13 references: Q-022, Q-025, Q-027.

### Decision: External patterns are candidates, not defaults

External desktop, Qt, or engineering-product patterns may be discussed when they better fit Tekla Nest, but adoption requires later Section 13 decision before production implementation.

Rationale:

- The user requested thorough current-state analysis first.
- External patterns may improve table-heavy workflows, but silent adoption could conflict with product context, accessibility, or implementation constraints.
- Section 13 provides traceability for future adoption decisions.

Alternatives rejected:

- Automatically adopt a third-party design system: not justified without product fit analysis.
- Prohibit external references: unnecessarily limits pattern quality.

Section 13 reference: Q-022.

### Decision: Keep UX Brief strategic; create Figma board in UX Mockups

No Figma component/pattern board exists during UX Brief. The board should be created in UX Mockups and include color, typography, table, dialog, form, toolbar, state, and accessibility examples.

Rationale:

- The current phase is UX Brief.
- The work order says UX Brief should not create or update mockups.
- Figma artifacts are still required before implementation decisions are committed.

Alternatives rejected:

- Create mockups during UX Brief: violates phase boundary.
- Defer Figma until implementation: conflicts with PM requirements.

Section 13 references: Q-003, Q-013.

## Current UI Audit Evidence Used

Observed source-grounded UI evidence:

- Main window uses PySide6 `QMainWindow`, resized to 1500x800.
- Layout uses a three-panel horizontal splitter: Parts Table, Stock Tabs, and Report Preview.
- Commands are grouped under File, Stock, Nesting, and View menus.
- A fixed-height branded toolbar shows optional logo and app title.
- Parts and stock tables use `QTableView` / `QAbstractTableModel` with stretched columns and editable cells.
- Current table evidence does not show explicit sorting, filtering, search, density, selection, or batch-action affordances.
- Report preview uses `QTextBrowser` for HTML rendering, including custom `reorder://` links and embedded images.
- Activation dialog is modal and simple, with license-key input, Activate/Quit buttons, disabled state during activation, text change during activation, and message-box success/error feedback.
- Color schema dialog exposes primary, accent, and background color buttons with Apply/Cancel.
- Current theme defaults are primary `#1a73e8`, accent `#ff6d00`, background `#f5f5f5`, font stack Segoe UI / Helvetica Neue / Arial, and font size 10.
- Stylesheet generation derives foreground, input, border, and alternate-row colors from background luminance and uses primary/accent roles across headers, tabs, buttons, menus, and hover states.

UX implication:

The current UI provides useful evidence for shell, table, report, activation, and color surfaces, but it is not yet a governed design system. The next UX artifact must convert this evidence into reusable patterns and tested visual direction.

## Accessibility Strategy

The design system should align with WCAG 2.2 AA outcomes and Qt accessibility practices.

Required coverage:

- keyboard-only operation;
- visible focus;
- logical tab order;
- accessible names, roles, states, and descriptions;
- Windows high contrast support;
- scalable text and high-DPI behavior;
- reduced-motion-safe feedback;
- non-color-only status communication;
- validation recovery;
- table header, sort, filter, selection, and row/column semantics;
- disabled and permission-unavailable explanations;
- loading, empty, error, success, validation, and partial-result announcements where applicable.

Rationale:

Fabrication planners work in dense desktop workflows where speed and trust matter. Accessibility requirements must support both assistive technology users and general usability under production pressure.

Section 13 reference: Q-015.

## Trade-offs

- Density vs readability: compact desktop tables are appropriate, but only if focus, selection, row height, contrast, and text scaling remain usable.
- Familiarity vs modernization: the existing three-panel shell may remain useful, but it should not prevent better table, toolbar, or status patterns if audit and Figma exploration show a better fit.
- Brand influence vs evidence: Tekla Structures should guide professional presentation, but palette adoption waits for captured evidence.
- Reuse vs flexibility: shared PySide6 patterns should reduce inconsistency, but future workflow-specific specs may justify exceptions with recorded rationale.
- Strategy vs artifact detail: UX Brief defines direction; UX Mockups creates the visual board.

## Constraints

- No production code changes in this spec.
- No service interface changes.
- No detailed workflow redesign.
- No existing design-system documentation.
- No existing Figma component/pattern board.
- Exact Tekla screenshots and palette samples are not yet captured.
- Architecture validation is still needed for PySide6 styling, shared widgets, presenter-view boundaries, performance, and security implications.

## UX Handoff Expectations for UX Mockups

UX Mockups should create the Figma component and pattern board with:

- foundation color, typography, spacing, border, radius, separation, focus, and semantic status examples;
- table examples for default, loading, empty, filtered-empty, error, partial-result, selected, sorted, searched, and batch-action states;
- dialog examples for activation, validation, blocking progress, success, and error;
- form examples for required fields, validation, disabled state, and help text;
- toolbar/menu examples for command grouping and unavailable actions;
- report-adjacent examples for preview links, reorder actions, and status feedback;
- accessibility examples for keyboard focus, high contrast, scalable text, screen-reader naming, and reduced-motion-safe feedback;
- selected visual direction and rejected alternatives.

## Governance Implications

Future UI work should be checked for:

- consistency with token roles;
- reuse of approved components or documented exception;
- complete state coverage;
- keyboard and screen-reader behavior;
- high contrast and high-DPI behavior;
- Figma alignment;
- audit traceability;
- Section 13 resolution for external pattern adoption or unresolved UX decisions.
