---
pitch: pitch-0001
slug: design-refactor
status: Draft
created: 2026-05-16
---

# Pitch: Design Refactor

## 1. Research Evidence

| Source | Finding | Pitch implication |
|---|---|---|
| Nielsen Norman Group - Fresh vs. Familiar: https://www.nngroup.com/articles/fresh-vs-familiar-aggressive-redesign/ | Frequent users prefer familiarity and gradual evolution over aggressive redesigns that break learned workflows. | Preserve Tekla Nest command locations, terminology, task order, and import/optimize/report flow unless a specific usability issue justifies change. |
| Nielsen Norman Group - Design Systems 101: https://www.nngroup.com/articles/design-systems-101/ | Design systems reduce inconsistency through reusable standards, but require guidance and maintenance. | Create a lightweight PySide6 design system spec before or alongside screen redesign work. |
| IBM Carbon - Data table usage: https://carbondesignsystem.com/components/data-table/usage/ | Data tables benefit from sorting, search/filtering, density controls, toolbars, hierarchy, and adequate space. | Table-heavy optimization, stock, part, and report views must explicitly address readability, sorting, filtering/search, selection, and batch actions. |
| W3C WCAG 2.2: https://www.w3.org/TR/WCAG22/ | WCAG provides technology-neutral accessibility criteria that improve accessibility and general usability across desktop devices. | Target WCAG 2.2 AA-aligned outcomes for contrast, keyboard access, focus visibility, labels, error handling, and readable layouts. |
| Qt Accessibility: https://doc.qt.io/qt-6/accessible.html | Qt supports accessible UI through keyboard navigation, contrast, scalable UI, assistive tools, and semantic metadata for custom widgets. | PySide6 screens and shared widgets must include Qt accessibility practices, especially for custom components. |
| Tekla User Assistance: https://support.tekla.com/ | Tekla workflows span model management, fabrication, and collaboration contexts. | Tekla Nest UI language should remain compatible with Tekla ecosystem expectations and fabrication workflow terminology. |
| Tekla Structures: https://www.tekla.com/products/tekla-structures | Tekla Structures supports constructible BIM and reliable creation, combination, management, and sharing of project information. | The redesign must protect confidence in imported Tekla-selected parts and preserve provenance around optimization inputs. |
| Tekla PowerFab: https://www.tekla.com/products/tekla-powerfab | Tekla PowerFab emphasizes steel fabrication management, cut lists, material optimization, production control, traceability, and dashboards. | Generated reports and review screens should support traceability, clear optimization outputs, and fabrication-planning confidence. |
| Martin Fowler - Branch by Abstraction: https://martinfowler.com/bliki/BranchByAbstraction.html | Large-scale changes can be delivered incrementally by introducing abstractions and migrating gradually. | Use incremental screen-by-screen and component-by-component migration rather than a risky big-bang UI rewrite. |

## 2. Pitch PM Brief

**Product**

Tekla Nest is a Python/PySide6 desktop app for 1D steel bar stock cutting optimization. It reads selected parts from Tekla Structures or CSV, generates optimal cut plans, supports live report preview, and produces HTML/PDF reports.

**Pitch owner**

Nelson Almeida.

**Problem**

Tekla Nest needs a workflow-preserving design refactor that modernizes the desktop UI without weakening user confidence in optimization inputs, cut-plan outputs, report provenance, or established fabrication-planning workflows.

**Target users**

Fabrication planners optimizing stock/cuts and reviewing outputs.

**Primary outcome**

Workflow-preserving modernization focused on usability consistency and accessibility.

**Appetite**

Larger multi-cycle redesign.

**Target platform**

Windows with Tekla integration only.

**Solution sketch**

- Create a lightweight PySide6 design system that is modern, clean, accessible, and resilient.
- Create Figma pre-visualization mockups before implementation and extract key visual insights from the Tekla Structures color scheme and presentation style.
- Redesign all app UI, including dialogs and activation/licensing.
- Include live report preview and generated HTML/PDF templates.
- Preserve existing command locations, terminology, task order, and import/optimize/report flow unless a specific usability issue is identified.
- Improve table behavior: sorting, filtering/search, readable density, useful selection, and batch actions.
- Align accessibility outcomes to WCAG 2.2 AA plus Qt accessibility practices.
- Split the work into four specs:
  - `spec-0001` / `ui-design-system`
  - `spec-0002` / `workflow-screens-redesign`
  - `spec-0003` / `report-redesign`
  - `spec-0004` / `ui-architecture-migration`

**Functional behavior policy**

Functional behavior may change where useful, but every change must be evidence-backed, explicit in specs, and protect optimization confidence/provenance.

**Release strategy**

Incremental screen-by-screen and component-by-component migration.

**Architecture scope**

UI internals, shared widgets, and presenter-view boundaries are in scope. Service interface changes are out of scope unless justified by spec evidence and architecture review.

**Existing UX artifacts**

None.

**Baseline evidence**

None yet. Discovery and audit must happen first.

**Success signals**

- Reduced task completion time for core import/optimize/report flows.
- Reduced observed usability issues after redesign.
- Accessibility checklist pass against WCAG 2.2 AA-aligned and Qt accessibility expectations.
- Improved UI consistency and component reuse.

**Rabbit holes**

- Big-bang rewrite of all screens.
- Cosmetic redesign without workflow evidence.
- Redesign that changes optimization trust cues or report provenance without explicit justification.
- Overbuilding a design system beyond the needs of PySide6 desktop UI.

**No-gos**

- Do not change optimization logic as part of this pitch.
- Do not broaden platform scope beyond Windows with Tekla integration.
- Do not change service interfaces unless justified by architecture review.
- Do not remove established workflow terminology or task order without evidence.

## 3. Open Questions

| ID | Status | Type | Question | Recommendation | User answer | Impact |
|---|---|---|---|---|---|---|
| PQ-001 | Answered | Product ownership | Who is the Pitch owner for `design-refactor`? | Name one accountable owner/team before dispatching spec work. | Nelson Almeida | Pitch header, decision ownership |
| PQ-002 | Answered | Product goal | What is the primary outcome: visual modernization, usability improvement, workflow consistency, accessibility, maintainability, or a ranked combination? | Frame this as workflow-preserving modernization focused on usability consistency and accessibility, not cosmetic reinvention. | Workflow-preserving modernization focused on usability consistency and accessibility | Problem, solution sketch, success signals |
| PQ-003 | Answered | Target users | Which user group should the refactor optimize for first: detailers importing from Tekla Structures, fabrication planners optimizing stock/cuts, report consumers, or internal operators? | Prioritize fabrication planners using optimization results and cut/report outputs, unless the team has stronger evidence. | Fabrication planners optimizing stock/cuts and reviewing outputs | Persona, workflows, success signals |
| PQ-004 | Answered | Appetite | What appetite/time-box should constrain this Pitch? | Set an explicit appetite such as one cycle or small bet / limited to high-value screens. | Larger multi-cycle redesign | Appetite, work-order sizing, no-gos |
| PQ-005 | Answered | Screen scope | Which screens are in scope? Candidate areas: main nest window, parts table, stock table/tabs, optimization results, report preview, toolbar, dialogs, activation/licensing, color dialog. | Scope to main workflow surfaces first: nest window, parts/stock tables, toolbar actions, optimization/report preview states. | All app UI including dialogs and activation/licensing | Spec impacts, UX artifact impact, work orders |
| PQ-006 | Answered | Generated reports | Should the refactor include only the in-app live report preview, or also the generated HTML/PDF report templates? | Include live report preview controls; only include generated HTML/PDF if report readability/auditability is a current pain. | Include live report preview and generated HTML/PDF report templates | Scope, no-gos, affected specs |
| PQ-007 | Answered | Workflow preservation | Should existing command locations, terminology, task order, and import/optimize/report flow be preserved unless a specific usability issue is identified? | Yes. Research supports gentle evolution for experienced users. | Yes, preserve command locations, terminology, task order, and import/optimize/report flow unless a specific usability issue is identified | No-gos, UX AC, work orders |
| PQ-008 | Answered | Functional no-gos | Are optimizer behavior, Tekla import semantics, CSV import/export, stock generation, kerf/scrap rules, and report audit data explicitly out of scope? | Yes; refactor should not change optimization or provenance behavior unless separately specified. | No, redesign may change functional behavior where useful | No-gos, architecture constraints |
| PQ-009 | Answered | Table behavior | Should table improvements include sorting, filtering/search, density options, row selection/batch actions, expandable rows, or only visual cleanup? | Prioritize sorting/filtering/search and readable density; avoid complex nested/expandable tables unless needed. | Sorting, filtering/search, readable density, and useful selection/batch actions | UX flow, spec AC, artifact impact |
| PQ-010 | Answered | Accessibility target | What accessibility bar should be used for desktop PySide6 UI: WCAG 2.2 AA-aligned, Qt accessibility best-practice only, or another internal standard? | Use WCAG 2.2 AA-aligned outcomes plus Qt accessibility practices where applicable. | WCAG 2.2 AA-aligned outcomes plus Qt accessibility practices | UX AC, acceptance criteria, no-gos |
| PQ-011 | Answered | Visual direction | Is there an existing design/brand direction to follow: Tekla/Trimble-aligned styling, current app style refined, custom lightweight system, or existing Figma/mockups? | Use a lightweight app-specific PySide6 design system; do not overbuild a large design system. | Lightweight PySide6 design system that is modern, clean, accessible, and resilient | Solution sketch, UX artifacts |
| PQ-012 | Answered | Existing UX artifacts | Do any mockups, prototypes, screenshots, or design files already exist for this UI? If yes, where? | If none exist, work orders should require new UX artifacts for user-visible changes. | No existing UX artifacts | UX artifact impact, spec-workshop flow |
| PQ-013 | Answered | Success signals | Which measurable signals should define success? Options: reduced task time, fewer import/report errors, improved usability score, fewer support issues, faster UI implementation, accessibility audit pass rate. | Use 2-4 signals: task completion time, usability issue reduction, accessibility checklist pass, and UI consistency/component reuse. | Task completion time, usability issue reduction, accessibility checklist pass, and UI consistency/component reuse | Success Signals |
| PQ-014 | Answered | Baseline evidence | Do we have baseline usability data, support tickets, user complaints, screenshots, or QA findings to anchor the refactor? | If not, add a short discovery/audit step before final design changes. | No baseline evidence yet; include discovery/audit first | Research evidence, dependencies |
| PQ-015 | Answered | Release strategy | Should this be delivered screen-by-screen/component-by-component while preserving the current UI, or as a full replacement? | Engineering should confirm; research/architecture evidence favors incremental migration, not big-bang rewrite. | Incremental screen-by-screen/component-by-component migration | Dependencies, architecture review, work orders |
| PQ-016 | Answered | Architecture boundary | Is changing UI internals, presenter/view boundaries, shared widgets, or service interfaces in scope? | Needs engineering decision. If yes, add architecture review to work orders. | Yes: UI internals/shared widgets/presenter-view boundaries are in scope, but avoid service interface changes unless justified | Required spec-workshop flow, dependencies |
| PQ-017 | Answered | Platform scope | Which runtime environments must be supported by the refactor: Windows with Tekla integration only, cross-platform desktop, specific screen resolutions/scaling, high-DPI? | Confirm before UX/spec work; affects layout/accessibility requirements. | Windows with Tekla integration only | UX AC, technical constraints |
| PQ-018 | Answered | Spec split | With no existing specs, should this Pitch create one new spec or multiple specs? Candidate split: `desktop-ui-refactor`, `ui-component-system`, `report-preview-usability`. | Prefer one new spec unless generated reports or architecture migration need separate specs. | Multiple specs: UX/design system, workflow screens, reports, and architecture migration | Spec Impact Map, work orders |
| PQ-019 | Answered | Spec ID/slug | What target spec ID/slug should be used for the new spec work order(s), given there is no existing `docs/specs/index.md`? | Use the repository's next accepted convention if known; otherwise parent workflow should assign before dispatch. | Auto-assign next spec IDs as `spec-0001` through `spec-0004` with feature slugs `ui-design-system`, `workflow-screens-redesign`, `report-redesign`, `ui-architecture-migration`; spec folders use `docs/specs/spec-NNNN/**`. | Target spec, allowed write paths |
| PQ-020 | Answered | In-flight dependencies | Are there active branches, planned features, or known bugs touching the PySide6 views/presenter/report pipeline that this Pitch must avoid or coordinate with? | Identify before dispatch to avoid conflicting spec work. | No known in-flight dependencies | Dependencies, sequencing |
| PQ-021 | Answered | Acceptance of deferred questions | If any technical or UX inputs are not known now, may they be recorded as explicit follow-up decisions with owner/milestone instead of blocking Pitch finalization? | Only if the user explicitly approves each deferred item and names an owner. | Yes, if each deferred item has an owner and is listed as a follow-up decision | Open Questions, readiness for spec workshops |

## 4. Spec Impact Map

| Impact ID | Spec | Action | Why this spec is affected | UX artifact impact | Required spec-workshop flow | Dependencies | Parallel group | Status |
|---|---|---|---|---|---|---|---|---|
| IMP-001 | New: `spec-0001` / `ui-design-system` | Create | Establishes shared PySide6 components, visual standards, accessibility rules, table patterns, Figma pre-visualization mockups, Tekla Structures color/presentation insights, and reuse guidance for the redesign. | update-mockups | full | n/a | A | Ready |
| IMP-002 | New: `spec-0002` / `workflow-screens-redesign` | Create | Covers workflow-preserving redesign of core import, optimize, stock/cut review, dialogs, activation/licensing, and general application screens. | update-mockups | full | IMP-001 | B | Ready |
| IMP-003 | New: `spec-0003` / `report-redesign` | Create | Covers live report preview and generated HTML/PDF report templates, including output review, readability, and provenance confidence. | update-mockups | full | IMP-001 | B | Ready |
| IMP-004 | New: `spec-0004` / `ui-architecture-migration` | Create | Defines incremental UI internals, shared widgets, and presenter-view migration strategy needed to deliver the redesign safely. | brief-only | full+arch | IMP-001, IMP-002, IMP-003 | C | Ready |

## 5. Per-Spec Work Orders

### IMP-001 - Create `spec-0001` / `ui-design-system`

- **Target spec**: `New: ui-design-system` assigned to `docs/specs/spec-0001/**`
- **Action**: Create
- **Allowed write paths**:
  - `docs/specs/spec-0001/**`
- **Forbidden write paths**:
  - `docs/pitches/**`
  - `docs/specs/index.md`
  - `docs/specs/_template.md`
  - `docs/specs/_mockups_template.md`
  - `docs/specs/_prototype-shell.html`
  - `docs/specs/spec-0002/**`
  - `docs/specs/spec-0003/**`
  - `docs/specs/spec-0004/**`
  - `src/**`
  - `tests/**`
  - `resources/**`
  - `services/**`
  - `license-server/**`
- **Pitch intent**: Define the lightweight PySide6 design system that enables modern, clean, accessible, resilient, and consistent UI modernization.
- **In scope**:
  - Core visual principles for Windows PySide6 desktop UI.
  - Shared component guidance for buttons, forms, dialogs, tables, navigation, status messaging, and report-adjacent UI.
  - Table behavior standards: sorting, filtering/search, readable density, useful selection, and batch actions.
  - Figma pre-visualization mockups used to refine visual direction before implementation.
  - Tekla Structures color scheme and presentation analysis translated into appropriate Tekla Nest visual principles.
  - WCAG 2.2 AA-aligned outcomes and Qt accessibility practices.
  - Component reuse expectations and consistency checks.
  - Discovery/audit-first approach for baseline UI inconsistencies.
- **Out of scope**:
  - Redesigning individual product workflows in detail.
  - Changing optimization logic.
  - Changing service interfaces.
  - Expanding beyond Windows with Tekla integration.
- **Affected existing scopes**: n/a; new spec.
- **UX artifact impact**: update-mockups
- **UX Artifact Impact Analysis**:

  | Question | Answer | Consequence |
  |---|---|---|
  | Does this impact alter a user-visible flow? | No | Design system rules support flows but do not directly change task order. |
  | Does it add, remove, or change screens? | No | Component and pattern mockups are expected, not full workflow screens. |
  | Does it alter layout, hierarchy, components, or visual states? | Yes | Mockups must define reusable component hierarchy and visual states. |
  | Does it alter interactions, navigation, validation, loading, empty, error, success, permission, or partial-result states? | Yes | Component/state guidance must cover these reusable patterns. |
  | Does it affect accessibility behavior, focus, keyboard support, or screen-reader output? | Yes | Spec must include Qt accessibility and WCAG 2.2 AA-aligned rules. |
  | Does it require mockups? | Yes | Create Figma component and pattern mockups before implementation. |
  | Does it require prototypes? | No | Prototype work is not required at design-system level unless later specs request it. |
  | Can existing mockups remain valid unchanged? | n/a | No existing UX artifacts. |
  | Can existing prototypes remain valid unchanged? | n/a | No existing UX artifacts. |

- **Expected spec changes**:
  - Create the spec with problem, goals, non-goals, scope, UX requirements, accessibility requirements, and acceptance criteria.
  - Define reusable PySide6 component/pattern requirements.
  - Define Figma mockup requirements for pre-visualization and visual refinement before implementation.
  - Capture key Tekla Structures color scheme and presentation insights, then state how they should or should not influence Tekla Nest UI.
  - Include table pattern requirements.
  - Include discovery/audit activities before finalizing detailed component decisions.
  - Include success measures for UI consistency and component reuse.
  - Add Section 13 follow-up decisions with owners where unknowns remain.
  - Add a Spec Revision Log entry for initial creation under IMP-001.
- **Required spec-workshop flow**: full
- **Amendment strategy**:
  - Create a new spec without modifying other specs or pitch files.
  - Preserve pitch intent and reference IMP-001 in the spec revision log.
  - Record any deferred unknowns as owned follow-up decisions.
- **Dependencies**: n/a
- **Open question references**: PQ-003, PQ-005, PQ-011, PQ-012, PQ-013, PQ-014, PQ-016, PQ-021
- **Completion output required**:
  - Files changed
  - Spec Revision Log entry
  - Section 13 updates
  - Figma mockup handoff or explicit artifact references
  - Tekla Structures color/presentation insight summary
  - Blocking questions, if any
  - Cross-spec concerns for pitch reconciliation

### IMP-002 - Create `spec-0002` / `workflow-screens-redesign`

- **Target spec**: `New: workflow-screens-redesign` assigned to `docs/specs/spec-0002/**`
- **Action**: Create
- **Allowed write paths**:
  - `docs/specs/spec-0002/**`
- **Forbidden write paths**:
  - `docs/pitches/**`
  - `docs/specs/index.md`
  - `docs/specs/_template.md`
  - `docs/specs/_mockups_template.md`
  - `docs/specs/_prototype-shell.html`
  - `docs/specs/spec-0001/**`
  - `docs/specs/spec-0003/**`
  - `docs/specs/spec-0004/**`
  - `src/**`
  - `tests/**`
  - `resources/**`
  - `services/**`
  - `license-server/**`
- **Pitch intent**: Redesign the core Tekla Nest application screens while preserving familiar fabrication-planning workflows.
- **In scope**:
  - Core import/optimize/report workflow screens.
  - CSV and Tekla-selected-parts entry points.
  - Stock, part, cut-plan, and optimization result review screens.
  - Dialogs and activation/licensing UI.
  - Command locations, terminology, task order, and flow preservation unless evidence supports change.
  - Table usability: sorting, filtering/search, readable density, selection, and batch actions.
  - Accessibility requirements for keyboard navigation, focus, labels, contrast, and assistive semantics.
  - Discovery/audit of current usability issues before detailed redesign decisions.
- **Out of scope**:
  - Generated HTML/PDF report templates, except handoff points to report preview.
  - Optimization algorithm changes.
  - Service interface changes unless separately justified.
  - Platform expansion beyond Windows with Tekla integration.
- **Affected existing scopes**: n/a; new spec.
- **UX artifact impact**: update-mockups
- **UX Artifact Impact Analysis**:

  | Question | Answer | Consequence |
  |---|---|---|
  | Does this impact alter a user-visible flow? | Yes | Flow review is required, but preservation is the default. |
  | Does it add, remove, or change screens? | Yes | Workflow screen mockups must be created or updated. |
  | Does it alter layout, hierarchy, components, or visual states? | Yes | Mockups must reflect hierarchy, component use, and states. |
  | Does it alter interactions, navigation, validation, loading, empty, error, success, permission, or partial-result states? | Yes | UX AC must cover interaction and state behavior. |
  | Does it affect accessibility behavior, focus, keyboard support, or screen-reader output? | Yes | Accessibility behavior must be specified for each affected workflow. |
  | Does it require mockups? | Yes | Create workflow screen mockups. |
  | Does it require prototypes? | No | Prototype requirement is deferred unless usability risk requires it. |
  | Can existing mockups remain valid unchanged? | n/a | No existing UX artifacts. |
  | Can existing prototypes remain valid unchanged? | n/a | No existing UX artifacts. |

- **Expected spec changes**:
  - Create the spec with workflow-preserving requirements and non-goals.
  - Define screen-level requirements for import, optimize, review, dialogs, and licensing.
  - Include evidence-backed policy for any functional behavior changes.
  - Include accessibility requirements aligned to WCAG 2.2 AA and Qt accessibility practices.
  - Include task-completion and usability-issue success signals.
  - Add Section 13 follow-up decisions with owners where unknowns remain.
  - Add a Spec Revision Log entry for initial creation under IMP-002.
- **Required spec-workshop flow**: full
- **Amendment strategy**:
  - Create a new spec without modifying pitch or other specs.
  - Reference IMP-002 in the spec revision log.
  - Treat workflow changes as exceptions requiring evidence and explicit rationale.
- **Dependencies**: IMP-001
- **Open question references**: PQ-004, PQ-005, PQ-006, PQ-007, PQ-009, PQ-010, PQ-011, PQ-012, PQ-014, PQ-016, PQ-020, PQ-021
- **Completion output required**:
  - Files changed
  - Spec Revision Log entry
  - Section 13 updates
  - Blocking questions, if any
  - Cross-spec concerns for pitch reconciliation

### IMP-003 - Create `spec-0003` / `report-redesign`

- **Target spec**: `New: report-redesign` assigned to `docs/specs/spec-0003/**`
- **Action**: Create
- **Allowed write paths**:
  - `docs/specs/spec-0003/**`
- **Forbidden write paths**:
  - `docs/pitches/**`
  - `docs/specs/index.md`
  - `docs/specs/_template.md`
  - `docs/specs/_mockups_template.md`
  - `docs/specs/_prototype-shell.html`
  - `docs/specs/spec-0001/**`
  - `docs/specs/spec-0002/**`
  - `docs/specs/spec-0004/**`
  - `src/**`
  - `tests/**`
  - `resources/**`
  - `services/**`
  - `license-server/**`
- **Pitch intent**: Redesign live report preview and generated HTML/PDF templates so fabrication planners can confidently review optimization outputs and provenance.
- **In scope**:
  - Live report preview UI.
  - Generated HTML report template.
  - Generated PDF report template.
  - Readability, hierarchy, provenance, optimization confidence, and traceability cues.
  - Report table behavior where applicable.
  - Accessibility and readable output expectations.
  - Incremental migration of report UI/templates.
- **Out of scope**:
  - Optimization algorithm changes.
  - Workflow screen redesign outside report preview handoff points.
  - Service interface changes unless justified.
  - Platform expansion beyond Windows with Tekla integration.
- **Affected existing scopes**: n/a; new spec.
- **UX artifact impact**: update-mockups
- **UX Artifact Impact Analysis**:

  | Question | Answer | Consequence |
  |---|---|---|
  | Does this impact alter a user-visible flow? | Yes | Report review and export flow must be reviewed. |
  | Does it add, remove, or change screens? | Yes | Live preview and report template mockups are required. |
  | Does it alter layout, hierarchy, components, or visual states? | Yes | Report hierarchy, tables, and output states must be specified. |
  | Does it alter interactions, navigation, validation, loading, empty, error, success, permission, or partial-result states? | Yes | Preview, generation, and output states must be covered. |
  | Does it affect accessibility behavior, focus, keyboard support, or screen-reader output? | Yes | Preview accessibility and readable generated outputs must be specified. |
  | Does it require mockups? | Yes | Create report preview and generated output mockups. |
  | Does it require prototypes? | No | Prototype requirement is deferred unless validation identifies report-review risk. |
  | Can existing mockups remain valid unchanged? | n/a | No existing UX artifacts. |
  | Can existing prototypes remain valid unchanged? | n/a | No existing UX artifacts. |

- **Expected spec changes**:
  - Create the spec with live preview and HTML/PDF report redesign requirements.
  - Define report readability, hierarchy, provenance, and traceability requirements.
  - Include accessibility expectations for preview and generated outputs.
  - Include evidence-backed policy for functional output changes.
  - Include success measures for review confidence and usability issue reduction.
  - Add Section 13 follow-up decisions with owners where unknowns remain.
  - Add a Spec Revision Log entry for initial creation under IMP-003.
- **Required spec-workshop flow**: full
- **Amendment strategy**:
  - Create a new spec without modifying pitch or other specs.
  - Reference IMP-003 in the spec revision log.
  - Keep report changes explicit and protect optimization confidence/provenance.
- **Dependencies**: IMP-001
- **Open question references**: PQ-005, PQ-006, PQ-008, PQ-010, PQ-011, PQ-012, PQ-014, PQ-016, PQ-020, PQ-021
- **Completion output required**:
  - Files changed
  - Spec Revision Log entry
  - Section 13 updates
  - Blocking questions, if any
  - Cross-spec concerns for pitch reconciliation

### IMP-004 - Create `spec-0004` / `ui-architecture-migration`

- **Target spec**: `New: ui-architecture-migration` assigned to `docs/specs/spec-0004/**`
- **Action**: Create
- **Allowed write paths**:
  - `docs/specs/spec-0004/**`
- **Forbidden write paths**:
  - `docs/pitches/**`
  - `docs/specs/index.md`
  - `docs/specs/_template.md`
  - `docs/specs/_mockups_template.md`
  - `docs/specs/_prototype-shell.html`
  - `docs/specs/spec-0001/**`
  - `docs/specs/spec-0002/**`
  - `docs/specs/spec-0003/**`
  - `src/**`
  - `tests/**`
  - `resources/**`
  - `services/**`
  - `license-server/**`
- **Pitch intent**: Define how Tekla Nest can migrate UI internals, shared widgets, and presenter-view boundaries incrementally while preserving workflows and avoiding unnecessary service interface changes.
- **In scope**:
  - Incremental UI migration strategy.
  - Shared widgets and UI composition boundaries.
  - Presenter-view boundary clarification.
  - Screen-by-screen/component-by-component rollout approach.
  - Architecture constraints that protect optimization logic and service interfaces.
  - Coordination requirements with design system and screen/report specs.
- **Out of scope**:
  - Implementing code.
  - Changing optimization logic.
  - Changing service interfaces unless justified by architecture review.
  - Defining database schemas or data models.
  - Creating visual mockups beyond architecture brief needs.
- **Affected existing scopes**: n/a; new spec.
- **UX artifact impact**: brief-only
- **UX Artifact Impact Analysis**:

  | Question | Answer | Consequence |
  |---|---|---|
  | Does this impact alter a user-visible flow? | No | Architecture migration must preserve user-visible flows. |
  | Does it add, remove, or change screens? | No | Screen changes belong to IMP-002 and IMP-003. |
  | Does it alter layout, hierarchy, components, or visual states? | No | Visual changes belong to the design system and screen/report specs. |
  | Does it alter interactions, navigation, validation, loading, empty, error, success, permission, or partial-result states? | No | Interaction behavior should remain governed by UX specs unless architecture review identifies a justified need. |
  | Does it affect accessibility behavior, focus, keyboard support, or screen-reader output? | No direct change | Architecture should enable accessibility but not define user-facing accessibility behavior independently. |
  | Does it require mockups? | No | Architecture brief only. |
  | Does it require prototypes? | No | No prototype impact expected. |
  | Can existing mockups remain valid unchanged? | n/a | No existing UX artifacts. |
  | Can existing prototypes remain valid unchanged? | n/a | No existing UX artifacts. |

- **Expected spec changes**:
  - Create the spec with architecture migration goals, constraints, non-goals, and rollout strategy.
  - Define how shared widgets and presenter-view boundaries support incremental migration.
  - Explicitly state that service interface changes are avoided unless justified.
  - Include dependency handling for IMP-001, IMP-002, and IMP-003.
  - Include architecture review requirements.
  - Add Section 13 follow-up decisions with owners where unknowns remain.
  - Add a Spec Revision Log entry for initial creation under IMP-004.
- **Required spec-workshop flow**: full+arch
- **Amendment strategy**:
  - Create a new spec without modifying pitch or other specs.
  - Reference IMP-004 in the spec revision log.
  - Keep migration guidance incremental and compatible with screen-by-screen rollout.
- **Dependencies**: IMP-001, IMP-002, IMP-003
- **Open question references**: PQ-003, PQ-004, PQ-010, PQ-012, PQ-017, PQ-018, PQ-019, PQ-020, PQ-021
- **Completion output required**:
  - Files changed
  - Spec Revision Log entry
  - Section 13 updates
  - Blocking questions, if any
  - Cross-spec concerns for pitch reconciliation

## 6. Pitch Reconciliation

Pitch reconciliation is pending returned spec work from IMP-001 through IMP-004.

| Check | Result | Evidence / notes |
|---|---|---|
| Every pitch goal maps to at least one spec | Pending | Validate after spec work returns. |
| Every changed spec maps back to the pitch | Pending | Expected impact IDs: IMP-001, IMP-002, IMP-003, IMP-004. |
| No no-go entered a spec | Pending | Confirm no optimization logic, unjustified service interface, or platform expansion entered scope. |
| UX language and patterns are consistent | Pending | Confirm IMP-001 patterns are reflected by IMP-002 and IMP-003. |
| Architecture assumptions are consistent | Pending | Confirm IMP-004 supports incremental migration and does not contradict UX specs. |
| Cross-spec dependencies are explicit | Pending | Confirm dependency chain: IMP-001 before/with IMP-002 and IMP-003; IMP-004 coordinates migration. |
| All open questions were answered through ask_user | Pending | All PQ rows currently marked Answered; validate no new blocking questions were introduced by spec workshops. |
| UX artifact impact decisions are satisfied | Pending | Confirm update-mockups for IMP-001, IMP-002, IMP-003 and brief-only for IMP-004. |
| Work stayed inside allowed write paths | Pending | Confirm each worker only changed its assigned `docs/specs/spec-NNNN/**` path. |

## 7. Pitch Workshop Log

| Step | Agent | Output | Completed |
|---|---|---|---|
| Research gate | Drake | Research evidence captured from NN/g, IBM Carbon, W3C WCAG 2.2, Qt Accessibility, Tekla sources, and Martin Fowler. | 2026-05-16T09:24:26Z |
| Drake question identification | Drake | 21 pitch-shaping questions identified across product, UX, accessibility, delivery, and architecture boundaries. | 2026-05-16T09:24:26Z |
| User question gate | User / Drake | All 21 questions answered and reflected in the pitch. | 2026-05-16T09:24:26Z |
| Pitch draft generation | Drake | Draft pitch generated with four actionable spec impacts and matching per-spec work orders. | 2026-05-16T09:24:26Z |
| IMP-001 approval change | User / Drake | IMP-001 updated to require Figma pre-visualization mockups and Tekla Structures color/presentation insight extraction before implementation. | 2026-05-16T09:24:26Z |
| Impact map approval | User / Drake | IMP-001 through IMP-004 approved one by one; impact map marked Ready. | 2026-05-16T09:24:26Z |
| Spec-workshop gate correction | Drake | Work orders updated to use `docs/specs/spec-NNNN/**` folders and forbid shared spec templates explicitly. | 2026-05-16T12:10:21Z |
| Spec template bootstrap | Drake | Added `docs/specs/_template.md` before dispatch so spec-workshop workers do not need to modify forbidden shared template paths. | 2026-05-16T12:10:21Z |
| Corrected impact map approval | User / Drake | IMP-001 through IMP-004 re-approved one by one after work-order path corrections. | 2026-05-16T12:10:21Z |

PITCH-SIGNED: agent=Drake; completed=2026-05-16T09:24:26Z
