# ChronosRefine: Design Requirements

**Purpose:** UX design, design system, and accessibility requirements  
**Audience:** UX designers, front-end developers  
**Companion Document:** No separate design-system companion specification is checked in on `main`; this file is the canonical design-system source of truth.  
**Last Updated:** February 2026

**Repo Note:** Test-file references for requirements not yet implemented on `main` are canonical target mappings and may not exist until the corresponding phase lands.

**Change Note (February 2026):** Applied 7-patch accuracy/completeness pack:
1. DS-007 structural fix: moved before "End of Design Requirements" marker (was placed after)
2. DS-007 Related Requirements corrected: DS-001 title fixed + DS-003/DS-006 added
3. DS-007 Implementation Guidance file paths corrected: real navigable paths instead of internal tool-specific references
4. DS-004 color contrast verification language tightened: "must be verified" instead of "have been verified"
5. DS-002 keyboard shortcuts made safe: Cmd/Ctrl+Shift combos to avoid browser/OS collisions
6. Accessibility phases made referential: note added to align with Implementation Plan
7. Color palette made explicit: primary/semantic colors enumerated here; neutral token details must stay aligned with repo-local design-token implementation until this file expands them further
8. Phase 4 accessibility journey aligned to the implemented upload/configuration/launch/progress/export surfaces; preview-review obligations remain with Phase 5 `FR-006`

---

## Design Philosophy (Jony Ive Aesthetic)

Inspired by the design philosophy of Jony Ive, the ChronosRefine user experience is guided by principles of minimalism, clarity, and functional beauty. The design system is not merely a visual style but a framework for creating an intuitive, unobtrusive, and emotionally resonant tool.

### Core Design Principles

- **Minimalism and Simplicity**: The interface is clean, straightforward, and free of unnecessary clutter. Every element must justify its existence through its function.

- **Clarity and Understandability**: The design makes complex technology feel intuitive and accessible, guiding the user without explicit instructions.

- **Functional Beauty**: The aesthetic appeal of the interface is derived from how well it works. Form follows function, and beauty emerges from the precision of the execution.

- **Unobtrusiveness**: The design is inconspicuous and seamlessly integrates into the user's workflow. The tool fades into the background, allowing the user's content to be the hero.

---

## Design System Overview

**Canonical status:** This file is the design-system source of truth. Any future companion design-system specification must derive from and remain aligned with this file.

The full design system includes:

### Color Palette

Design tokens are defined in this canonical design requirements document, including:
- Near Black (#1A1A1A), Pure White (#FFFFFF)
- Accent Blue (#0066FF), Success Green (#00C853), Warning Amber (#FFB300), Error Red (#D32F2F)
- Neutral Gray 100, Neutral Gray 300, Neutral Gray 600 (repo-local design-token implementation must remain aligned with this palette)

### Typography
8-level type scale using Inter font family:
- H1 (32px), H2 (24px), H3 (20px)
- Body Primary (16px), Body Secondary (14px), Caption (12px)
- Button Text (16px), Code (SF Mono 14px)

### Spacing System
8-token spacing system based on 8px grid:
- xs (4px), sm (8px), md (16px), lg (24px), xl (32px), 2xl (48px), 3xl (64px), 4xl (96px)

### Component Library
5 core components with complete specifications:
- **Button (Primary & Secondary):** Height, padding, border radius, all interactive states
- **Input Field:** Height, padding, border, focus/error/success states
- **Card:** Background, border, padding, elevation, hover state
- **Progress Bar:** Height, colors, border radius, animation timing
- **Modal/Dialog:** Background, padding, max width, elevation, backdrop, animations

### Animation Specifications
5 timing categories with Material Design Standard Easing:
- Micro-interaction (150ms), Component Transition (250ms), Page Transition (300ms), Complex Animation (400ms), Progress Indicator (600ms)

### Elevation System
5 elevation levels with box shadow specifications:
- Level 0 (none), Level 1 (cards), Level 2 (hover), Level 3 (dropdowns), Level 4 (modals)

**For implementation:** Refer to the complete Design System Specification for pixel-perfect specifications, CSS code, and usage guidelines.

---

## Accessibility Standards Compliance

**Target Standard:** WCAG 2.1 Level AA  
**Status:** Phase 4 exit criterion (GA-ready)  
**Verification:** Third-party accessibility audit before GA

> **Note:** Phase numbers in this table refer to the canonical Implementation Plan phases. If the plan changes, update this table to match the plan.

**Compliance Scope:**

| Component | WCAG 2.1 AA Requirement | Implementation Status | Verification Method |
|---|---|---|---|
| **Web UI** | Full compliance | Phase 4 | Automated testing (axe-core) + manual audit |
| **Transformation Manifests** | N/A (machine-readable JSON) | N/A | N/A |
| **Deletion Proofs (PDF)** | Accessible PDF/UA standard | Phase 5 | PDF accessibility checker |
| **Email Notifications** | Semantic HTML with alt text | Phase 3 | Email accessibility testing |
| **Documentation** | Full compliance | Phase 6 | Manual audit |

---

## Design Requirements

### DS-001: Fidelity Configuration UX

**Description:** System must provide intuitive UI for selecting Fidelity Tier and overriding era classification with appropriate warnings.

**Acceptance Criteria:**
- AC-DS-001-01: Three Fidelity Tiers (Enhance, Restore, Conserve) selectable via dropdown or radio button group
- AC-DS-001-02: Each tier has descriptive label and tooltip explaining use case:
  - **Enhance**: "Best for family videos. Reduces grain for a cleaner look."
  - **Restore**: "Best for documentaries. Preserves era-accurate texture."
  - **Conserve**: "Best for archival work. Maximum authenticity with full audit trail."
- AC-DS-001-03: Default tier is persona-specific (Archivist→Conserve, Filmmaker→Restore, Prosumer→Enhance)
- AC-DS-001-04: Era override available when confidence <0.70 via "Override Era" button
- AC-DS-001-05: Override triggers warning modal: "AI confidence is X%. Confirm override to [selected era]?"
- AC-DS-001-06: Warning modal includes "Learn More" link explaining confidence scoring
- AC-DS-001-07: User selection persists for job execution (displayed in confirmation screen)
- AC-DS-001-08: Grain intensity presets (Matched/Subtle/Heavy) available as secondary controls
- AC-DS-001-09: UI follows Jony Ive aesthetic: minimal, clear, unobtrusive
- AC-DS-001-10: All interactive elements meet WCAG 2.1 AA contrast requirements

**Definition of Done:**
- DoD-DS-001-01: UI mockups approved by design team with 8+ iterations and stakeholder sign-off
- DoD-DS-001-02: Figma prototype tested with 8+ users (3 prosumer, 3 filmmaker, 2 archivist personas) with >85% task completion rate
- DoD-DS-001-03: Implementation matches design specifications with <2px deviation (verified by Percy visual regression testing with 20+ snapshots)
- DoD-DS-001-04: All 5 interactive states implemented and tested (default, hover, active, disabled, focus) with 30+ Playwright assertions
- DoD-DS-001-05: Keyboard navigation tested with 15+ scenarios (Tab, Shift+Tab, Enter, Escape, Arrow keys) covering all user flows
- DoD-DS-001-06: Screen reader compatibility tested with JAWS, NVDA, VoiceOver (12+ test scenarios, 100% announcement accuracy)
- DoD-DS-001-07: Color contrast verified with axe-core (100% pass rate, all elements meet 4.5:1 for text, 3:1 for interactive)
- DoD-DS-001-08: Responsive design tested on 6+ breakpoints (320px, 768px, 1024px, 1440px, 1920px, 2560px) with Playwright
- DoD-DS-001-09: Code review approved by 2+ engineers with UX checklist (accessibility, responsiveness, error handling, performance)
- DoD-DS-001-10: Storybook documentation created with 12+ component stories covering all states and variants
- DoD-DS-001-11: Code quality: ESLint passes, no accessibility violations (axe-core), bundle size <50KB for component

**Verification Method:** UI Validation (Playwright tests + manual accessibility audit)

**Test Files:**
- `tests/ui/test_fidelity_tier_selector.spec.ts`
- `tests/ui/test_era_override_modal.spec.ts`
- `tests/accessibility/test_fidelity_config_a11y.spec.ts`

**Related Requirements:** FR-003 (Fidelity Tier Selection), FR-002 (Era Detection), DS-002 (Keyboard Navigation), DS-004 (Color Contrast)

---

### DS-002: Keyboard Navigation

**Description:** All interactive elements in the implemented Phase 4 ChronosRefine web UI must be fully operable via keyboard without requiring a mouse.

**Phase 4 scope note:** Preview-review keyboard obligations remain attached to Phase 5 `FR-006`; Phase 4 evidence is limited to the implemented upload, detection, configuration, launch review, processing/progress, and export/delivery journey.

**Acceptance Criteria:**
- AC-DS-002-01: All interactive elements (buttons, links, form fields, dropdowns, modals) are reachable via Tab key
- AC-DS-002-02: Tab order follows logical visual flow (left-to-right, top-to-bottom)
- AC-DS-002-03: Focus indicators are visible with 2px outline and 3:1 contrast ratio against background
- AC-DS-002-04: Enter key activates buttons and links
- AC-DS-002-05: Escape key closes modals and dropdowns
- AC-DS-002-06: Arrow keys navigate within dropdowns and radio button groups
- AC-DS-002-07: Space key toggles checkboxes and activates buttons
- AC-DS-002-08: 100% of the implemented Phase 4 journey (Upload → Detection → Configure → Launch Review → Processing/Progress → Export/Delivery) completable via keyboard only
- AC-DS-002-09: No keyboard traps (user can always navigate away from any element)
- AC-DS-002-10: Skip navigation link provided to bypass repetitive navigation elements
- AC-DS-002-11: Keyboard shortcuts documented in Help > Keyboard Shortcuts
- AC-DS-002-12: Keyboard shortcuts MUST NOT override standard browser/OS shortcuts; conflicts are resolved by using Cmd/Ctrl+Shift combos and documenting them in Help > Keyboard Shortcuts.

**Keyboard Shortcuts:**

| Shortcut | Action | Context |
|---|---|---|
| **Tab** | Move focus to next interactive element | Global |
| **Shift + Tab** | Move focus to previous interactive element | Global |
| **Enter** | Activate button, link, or submit form | Interactive elements |
| **Escape** | Close modal, dropdown, or cancel action | Modals, dropdowns |
| **Space** | Toggle checkbox or activate button | Checkboxes, buttons |
| **Arrow Up/Down** | Navigate dropdown options or radio buttons | Dropdowns, radio groups |
| **Cmd/Ctrl + Shift + U** | Focus the file-selection control | Global |
| **Cmd/Ctrl + Shift + S** | Focus the save-configuration action | After upload + detection |
| **Cmd/Ctrl + Shift + L** | Focus the launch-cost review action | After saved configuration |
| **Cmd/Ctrl + Shift + E** | Jump to the primary delivery/export action | After job completion |

**Definition of Done:**
- DoD-DS-002-01: All 50+ interactive elements tested with keyboard-only navigation (100% reachable, 0 keyboard traps)
- DoD-DS-002-02: Tab order verified across the implemented Phase 4 sections (Upload, Detection, Configure, Launch Review, Processing/Progress, Export/Delivery) with logical flow (left-to-right, top-to-bottom)
- DoD-DS-002-03: Focus indicators visible with 2px outline and meet 3:1 contrast ratio (verified with axe-core, 100% pass rate on 50+ elements)
- DoD-DS-002-04: The Packet 4G keyboard shortcut set is implemented and tested for activation, conflict avoidance, and Help-surface documentation
- DoD-DS-002-05: Skip navigation link tested with 8+ scenarios (jumps to main content, visible on focus, works with screen readers)
- DoD-DS-002-06: No keyboard traps detected in 40+ manual audit scenarios (modals, dropdowns, forms, dynamic content)
- DoD-DS-002-07: Keyboard shortcuts documentation is available in Help > Keyboard Shortcuts and covered by rendered accessibility tests
- DoD-DS-002-08: Code review approved by 2+ engineers with accessibility checklist (WCAG 2.1 AA, ARIA best practices, focus management)
- DoD-DS-002-09: Third-party accessibility audit passed for the implemented Phase 4 journey (0 critical issues, <5 minor issues, all remediated)
- DoD-DS-002-10: Code quality: ESLint passes, rendered accessibility suites pass, and no focus-management bugs remain in the shared modal, form, and delivery flows

**Verification Method:** UI Validation (Playwright tests + manual keyboard navigation audit)

**Test Files:**
- `tests/accessibility/test_keyboard_navigation.spec.ts`
- `tests/accessibility/test_focus_indicators.spec.ts`
- `tests/accessibility/test_keyboard_shortcuts.spec.ts`

**Related Requirements:** DS-001 (Fidelity Configuration UX), DS-003 (Screen Reader Support), DS-005 (Focus Indicators)

---

### DS-003: Screen Reader Support

**Description:** All content and functionality in the implemented Phase 4 ChronosRefine web UI must be accessible to users of screen readers (JAWS, NVDA, VoiceOver).

**Phase 4 scope note:** Preview-review screen-reader obligations remain attached to Phase 5 `FR-006`; Phase 4 screen-reader evidence stops at the shipped launch/progress/export experience.

**Acceptance Criteria:**
- AC-DS-003-01: All images have descriptive alt text (not "image" or "icon")
- AC-DS-003-02: All form fields have associated labels (not placeholder-only)
- AC-DS-003-03: All buttons have descriptive text or aria-label (not icon-only)
- AC-DS-003-04: All interactive elements have appropriate ARIA roles (button, link, dialog, alert)
- AC-DS-003-05: All dynamic content updates announced via aria-live regions
- AC-DS-003-06: All error messages associated with form fields via aria-describedby
- AC-DS-003-07: All modals have aria-modal="true" and aria-labelledby
- AC-DS-003-08: Screen reader announces all page elements in logical order
- AC-DS-003-09: Screen reader announces all state changes (job started, job completed, error occurred)
- AC-DS-003-10: Screen reader announces all form validation errors
- AC-DS-003-11: Screen reader announces all Uncertainty Callouts with full context
- AC-DS-003-12: Screen reader users can complete the implemented Phase 4 journey without sighted assistance

**ARIA Labels for Key Components:**

| Component | ARIA Role | ARIA Label Example |
|---|---|---|
| **Upload Button** | button | "Upload media files for restoration" |
| **Era Dropdown** | combobox | "Select media era (currently: 1960s Kodachrome)" |
| **Fidelity Tier Selector** | radiogroup | "Select restoration intensity: Conserve, Restore, or Enhance" |
| **Launch Review Button** | button | "Review cost and start processing" |
| **Launch Cost Modal** | dialog | "Launch cost review with estimate, overage approval, and start processing actions" |
| **Progress Bar** | progressbar | "Processing: 45% complete (9 of 20 segments)" |
| **Uncertainty Callout** | alert | "Low confidence warning: Frame 145 - Historical uniform color ambiguous" |
| **Export Button** | button | "Download AV1 package for the completed job" |

**Definition of Done:**
- DoD-DS-003-01: All 100+ images have descriptive alt text (manual audit, 0 generic alt text like "image" or "icon")
- DoD-DS-003-02: All 30+ form fields have associated labels (automated test with axe-core, 100% pass rate)
- DoD-DS-003-03: All 40+ buttons have descriptive text or aria-label (automated test, 100% pass rate)
- DoD-DS-003-04: All 25+ ARIA roles implemented correctly (automated test with axe-core, 100% pass rate)
- DoD-DS-003-05: All implemented aria-live regions tested with JAWS, NVDA, and VoiceOver (manual audit, 100% announcement accuracy)
- DoD-DS-003-06: All current Phase 4 form and delivery error messages announced correctly with full context (manual audit with 3 screen readers)
- DoD-DS-003-07: Full implemented Phase 4 journey tested with screen reader (Upload → Detection → Configure → Launch Review → Processing/Progress → Export/Delivery) with 3 screen readers (JAWS, NVDA, VoiceOver), 100% task completion
- DoD-DS-003-08: Code review approved by 2+ engineers with ARIA best practices checklist (semantic HTML, ARIA roles, live regions, labels)
- DoD-DS-003-09: Third-party accessibility audit passed for the implemented Phase 4 journey (0 critical issues, <3 minor issues, all remediated)
- DoD-DS-003-10: Code quality: ESLint passes, rendered accessibility suites pass, no ARIA misuse remains, and semantic HTML is verified

**Verification Method:** UI Validation (automated tests with axe-core + manual screen reader audit)

**Test Files:**
- `tests/accessibility/test_screen_reader_support.spec.ts`
- `tests/accessibility/test_aria_labels.spec.ts`
- `tests/accessibility/test_aria_live_regions.spec.ts`

**Related Requirements:** DS-002 (Keyboard Navigation), DS-005 (Focus Indicators), DS-006 (Error Messages Accessibility)

---

### DS-004: Color Contrast

**Description:** All text and interactive elements must meet WCAG 2.1 AA contrast ratio requirements.

**Acceptance Criteria:**
- AC-DS-004-01: Normal text (< 18pt): 4.5:1 contrast ratio minimum
- AC-DS-004-02: Large text (>= 18pt or 14pt bold): 3:1 contrast ratio minimum
- AC-DS-004-03: Interactive elements (buttons, links, form borders): 3:1 contrast ratio minimum
- AC-DS-004-04: Focus indicators: 3:1 contrast ratio against background
- AC-DS-004-05: All color combinations in design system pass automated contrast checker (axe-core, WAVE)
- AC-DS-004-06: All text on colored backgrounds meets 4.5:1 ratio
- AC-DS-004-07: All button states (default, hover, active, disabled) meet 3:1 ratio
- AC-DS-004-08: All form field borders meet 3:1 ratio
- AC-DS-004-09: All focus indicators meet 3:1 ratio
- AC-DS-004-10: Color is not the only means of conveying information (use icons + text)
- AC-DS-004-11: Contrast verification artifacts stored (contrast matrix + axe-core runs) and linked from the Design System Specification.

**Design System Color Contrast Requirements & Verification:**

All color pairs used in product UI **must be verified** to meet WCAG 2.1 AA before GA. Verification evidence is the contrast matrix in the Design System Specification (or test output artifacts).

- **Text on White Background:** All text colors (Charcoal #2C2C2C, Slate #4A5568) meet 4.5:1 ratio
- **Text on Dark Background:** White text (#FFFFFF) on Near Black (#1A1A1A) meets 4.5:1 ratio
- **Interactive Elements:** Accent Blue (#0066FF), Success Green (#00C853), Warning Amber (#FFB300), Error Red (#D32F2F) all meet 3:1 ratio against white background
- **Focus Indicators:** 2px outline with 3:1 contrast ratio against all backgrounds

**Definition of Done:**
- DoD-DS-004-01: All 50+ color combinations tested with axe-core (100% pass rate, all meet 4.5:1 for text, 3:1 for interactive)
- DoD-DS-004-02: All 20+ text on colored backgrounds verified with manual audit (4.5:1 minimum, measured with WebAIM contrast checker)
- DoD-DS-004-03: All 15+ button states verified (default, hover, active, disabled, focus) with 3:1 minimum contrast (75+ combinations tested)
- DoD-DS-004-04: All 12+ form field borders verified with 3:1 contrast ratio (default, focus, error, success states)
- DoD-DS-004-05: All 50+ focus indicators verified with 2px outline and 3:1 contrast ratio (automated test with axe-core)
- DoD-DS-004-06: Color contrast documentation created in the design system with contrast ratio matrix (9 colors × 9 colors = 81 combinations)
- DoD-DS-004-07: Code review approved by 2+ engineers with WCAG 2.1 AA checklist (contrast ratios, color independence, visual clarity)
- DoD-DS-004-08: Third-party accessibility audit passed (0 contrast violations)
- DoD-DS-004-09: Code quality: all CSS color values remain documented with contrast ratios, status/error states include non-color-only cues, and shared CSS variables stay the source of truth

**Verification Method:** Automated (axe-core contrast checker) + Manual (visual audit)

**Test Files:**
- `tests/accessibility/test_color_contrast.spec.ts`
- `tests/accessibility/test_button_contrast.spec.ts`
- `tests/accessibility/test_focus_contrast.spec.ts`

**Related Requirements:** DS-001 (Fidelity Configuration UX), DS-002 (Keyboard Navigation), DS-005 (Focus Indicators)

---

### DS-005: Focus Indicators

**Description:** Focus must be managed appropriately during navigation and dynamic content updates to ensure keyboard and screen reader users maintain context.

**Phase 4 scope note:** Preview-review focus obligations remain attached to Phase 5 `FR-006`; Phase 4 focus verification stops at the shipped launch/progress/export surfaces.

**Acceptance Criteria:**
- AC-DS-005-01: Focus moves to modal when opened
- AC-DS-005-02: Focus returns to trigger element when modal closed
- AC-DS-005-03: Focus moves to first error field when form validation fails
- AC-DS-005-04: Focus moves to terminal success, failure, or delivery-error messages when those updates require immediate user attention
- AC-DS-005-05: Focus does not jump unexpectedly during page updates
- AC-DS-005-06: Opening the era-override, launch-cost-review, or keyboard-shortcuts modal moves focus to the first actionable control inside the dialog
- AC-DS-005-07: Closing a modal returns focus to the control that opened it
- AC-DS-005-08: Form validation error moves focus to first invalid field with error message announced
- AC-DS-005-09: Terminal completion and delivery retry states can receive focus with the current outcome announced
- AC-DS-005-10: Processing progress, cost-estimate refreshes, and delivery updates do not steal focus from the current element
- AC-DS-005-11: All focus indicators are visible with 2px outline and 3:1 contrast ratio

**Definition of Done:**
- DoD-DS-005-01: Focus management tested for the implemented Phase 4 modals (era override, launch cost review, keyboard shortcuts) with rendered and manual keyboard coverage
- DoD-DS-005-02: Focus return tested when closing modals (returns to trigger element, handles repeated opens, handles trigger disablement)
- DoD-DS-005-03: Focus movement tested for form validation errors covering missing file, missing persona, missing tier/configuration, and retry states
- DoD-DS-005-04: Focus movement tested for terminal notifications and delivery errors covering success, partial, retryable delivery errors, and blocking alerts
- DoD-DS-005-05: Focus stability tested during processing progress, cost-estimate refresh, and delivery-status updates with no unexpected focus jumps
- DoD-DS-005-06: Focus indicators visible with 2px outline and meet 3:1 contrast ratio on all shared interactive elements (verified by automated contrast coverage)
- DoD-DS-005-07: Code review approved by 2+ engineers with focus-management checklist (modal focus, focus return, focus stability, focus indicators)
- DoD-DS-005-08: Third-party accessibility audit passed for the implemented Phase 4 journey (0 focus-management issues)
- DoD-DS-005-09: Code quality: no focus-jump regressions in shared modal, form, progress, and delivery flows, and focus trap behavior is verified across the current Phase 4 dialogs

**Verification Method:** UI Validation (Playwright tests + manual keyboard navigation audit)

**Test Files:**
- `tests/accessibility/test_focus_management.spec.ts`
- `tests/accessibility/test_modal_focus.spec.ts`
- `tests/accessibility/test_form_focus.spec.ts`

**Related Requirements:** DS-002 (Keyboard Navigation), DS-003 (Screen Reader Support), DS-004 (Color Contrast)

---

### DS-006: Error Messages Accessibility

**Description:** All error messages must be accessible to keyboard and screen reader users with clear, actionable guidance.

**Acceptance Criteria:**
- AC-DS-006-01: All error messages associated with form fields via aria-describedby
- AC-DS-006-02: All error messages announced by screen readers
- AC-DS-006-03: All error messages have clear, actionable guidance (not just "Error" or "Invalid")
- AC-DS-006-04: All error messages include recovery path (e.g., "Please upload a valid MP4, AVI, or MOV file")
- AC-DS-006-05: All error messages meet color contrast requirements (Error Red #D32F2F meets 3:1 ratio)
- AC-DS-006-06: All error messages use icon + text (not color-only)
- AC-DS-006-07: All error messages persist until user takes corrective action
- AC-DS-006-08: All error messages are dismissible (Escape key or close button)
- AC-DS-006-09: Uncertainty Callouts announced with full context (frame range, issue description, recovery path)
- AC-DS-006-10: Form validation errors move focus to first invalid field

**Error Message Examples:**

| Error Scenario | Error Message | Recovery Path |
|---|---|---|
| **Invalid File Format** | "Invalid file format. Please upload a valid MP4, AVI, MOV, or MKV file." | User selects valid file format |
| **File Too Large** | "File size exceeds 10GB limit. Please compress or split the file." | User compresses or splits file |
| **Upload Interrupted** | "Upload interrupted. Click 'Resume' to continue from where you left off." | User clicks "Resume" button |
| **Low-Confidence Era** | "We're not confident about this media's era (confidence: 45%). Please confirm or select from our best guesses." | User manually selects era |
| **E_HF Violation** | "Frames 145-180 may appear softer to preserve original texture. You can accept this change or manually adjust the Fidelity Slider." | User accepts or adjusts fidelity |
| **Hallucination Limit Exceeded** | "Segment 3 exceeded the authenticity threshold for Conserve mode and requires manual review. Click 'Review Segment' to approve or reject the restoration." | User reviews and approves/rejects |
| **Monthly Limit Reached** | "You've used 60/60 minutes this month. Approve overage at $0.50/min to continue or wait until next billing cycle." | User approves overage or waits |

**Definition of Done:**
- DoD-DS-006-01: All 30+ error messages associated with form fields via aria-describedby (automated test with axe-core, 100% pass rate)
- DoD-DS-006-02: All 30+ error messages announced by screen readers with full context (manual audit with JAWS, NVDA, VoiceOver, 100% announcement accuracy)
- DoD-DS-006-03: All 30+ error messages have clear, actionable guidance (manual audit, 0 generic messages like "Error" or "Invalid")
- DoD-DS-006-04: All 30+ error messages meet 3:1 color contrast requirements (automated test with axe-core, Error Red #D32F2F verified)
- DoD-DS-006-05: All 30+ error messages use icon + text (manual audit, 0 color-only indicators)
- DoD-DS-006-06: All 30+ error messages tested for persistence (remain until corrective action) and dismissibility (Escape key or close button) with 60+ scenarios
- DoD-DS-006-07: Form validation errors tested for focus movement to first invalid field (15+ scenarios, 100% success rate)
- DoD-DS-006-08: Code review approved by 2+ engineers with error UX checklist (clarity, actionability, accessibility, recovery path)
- DoD-DS-006-09: Third-party accessibility audit passed (0 error message accessibility issues)
- DoD-DS-006-10: Code quality: All error messages templated (no hardcoded strings), error recovery tested (15+ scenarios)

**Verification Method:** UI Validation (automated tests with axe-core + manual screen reader audit)

**Test Files:**
- `tests/accessibility/test_error_messages.spec.ts`
- `tests/accessibility/test_error_announcements.spec.ts`
- `tests/accessibility/test_uncertainty_callouts_a11y.spec.ts`

**Related Requirements:** DS-003 (Screen Reader Support), DS-004 (Color Contrast), DS-005 (Focus Indicators), FR-001 (Video Upload and Validation), FR-004 (Processing and Restoration)

---

### DS-007: Design System Implementation

**Description:** All UI components must be implemented according to the complete Design System Specification, ensuring consistency, maintainability, and adherence to Jony Ive-inspired aesthetic principles across the entire application.

**Acceptance Criteria:**
- AC-DS-007-01: All colors use design system tokens (no hardcoded hex values in component code)
- AC-DS-007-02: All typography uses design system type scale (Inter font family, 8-level scale)
- AC-DS-007-03: All spacing uses design system tokens (8px grid, 8-token system)
- AC-DS-007-04: All components implement complete specifications from Design System Specification
- AC-DS-007-05: All interactive states defined (default, hover, active, disabled, focus) for all components
- AC-DS-007-06: All components responsive across breakpoints (mobile 320px, tablet 768px, desktop 1440px)
- AC-DS-007-07: Design system tokens exported as CSS variables and TypeScript constants
- AC-DS-007-08: Component library documented with Storybook (all components, all states, all variants)
- AC-DS-007-09: Design QA checklist passed for all screens (color, typography, spacing, component usage)
- AC-DS-007-10: Design system governance process established (token change approval, component addition process)

**Definition of Done:**
- DoD-DS-007-01: Design system tokens implemented: 9 colors, 8 typography levels, 8 spacing tokens exported as CSS variables (`src/styles/tokens.css`) and TypeScript constants (`src/styles/tokens.ts`)
- DoD-DS-007-02: Component library implemented with 5 core components (Button, Input Field, Card, Modal, Progress Bar) matching Design System Specification pixel-perfectly (visual regression testing with Chromatic, 0 unintended changes)
- DoD-DS-007-03: All interactive states implemented for all components: default, hover, active, disabled, focus (tested with 100+ Playwright scenarios covering all state transitions)
- DoD-DS-007-04: Responsive design implemented for 3 breakpoints: mobile (320px-767px), tablet (768px-1439px), desktop (1440px+) with fluid scaling (tested with 50+ responsive scenarios)
- DoD-DS-007-05: Storybook documentation complete: all 5 core components documented with all variants, all states, usage guidelines, code examples (30+ stories total)
- DoD-DS-007-06: Design QA checklist created and applied to all 15+ screens: color token usage (100% compliance), typography scale usage (100% compliance), spacing token usage (100% compliance), component specification adherence (100% compliance)
- DoD-DS-007-07: Visual regression testing implemented with Chromatic: baseline screenshots captured for all components and screens, automated visual diff on every PR (0 unintended visual changes)
- DoD-DS-007-08: Design system governance documented: token change approval process (requires design + engineering review), component addition process (requires design spec + accessibility audit), breaking change policy (major version bump, migration guide required)
- DoD-DS-007-09: Design system audit passed: all hardcoded colors replaced with tokens (0 hardcoded hex values), all hardcoded spacing replaced with tokens (0 magic numbers), all fonts use Inter family (0 fallback font usage in production)
- DoD-DS-007-10: Code review approved by 2+ engineers + 1 designer with design system checklist (token usage, component adherence, responsive behavior, accessibility)
- DoD-DS-007-11: Design system documentation published: token reference, component library, usage guidelines, governance process (accessible to all team members)
- DoD-DS-007-12: Code quality: Design system tokens tested (50+ unit tests), component library tested (100+ Playwright tests), visual regression coverage 100% (all components, all states)

**Verification Method:** Automated (visual regression testing + unit tests + Playwright tests) + Manual (design QA audit)

**Test Files:**
- `tests/design_system/test_tokens.spec.ts`
- `tests/design_system/test_component_library.spec.ts`
- `tests/visual_regression/test_all_components.spec.ts`
- `tests/visual_regression/test_all_screens.spec.ts`

**Related Requirements:** DS-001 (Fidelity Configuration UX), DS-002 (Keyboard Navigation), DS-003 (Screen Reader Support), DS-004 (Color Contrast), DS-005 (Focus Indicators), DS-006 (Error Messages Accessibility)

**Implementation Guidance:**
- 📄 **Design Requirements (canonical):** `docs/specs/chronosrefine_design_requirements.md`
- 📄 **Implementation Plan (phases & checkpoints):** `docs/specs/chronosrefine_implementation_plan.md`
- 📄 **Coverage Matrix (requirement placement):** `docs/specs/ChronosRefine Requirements Coverage Matrix.md`

---

## References

- WCAG 2.1 Level AA: https://www.w3.org/WAI/WCAG21/quickref/?versions=2.1&levels=aa
- ARIA Authoring Practices Guide: https://www.w3.org/WAI/ARIA/apg/
- Jony Ive Design Philosophy: Minimalism, Clarity, Functional Beauty

---

**End of Design Requirements**
