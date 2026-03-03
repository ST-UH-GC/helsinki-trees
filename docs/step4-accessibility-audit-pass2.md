# Step 4 - Accessibility Audit (Pass 2)

Date: 2026-03-03
Target: `output/helsinki_trees_beta.html`

## Audit approach
- Static code audit of generated HTML/CSS/JS for WCAG 2.2 AA baseline risks.
- Keyboard and semantics review against current map-first + overlay UI.
- Implemented fixes directly in source generator (`src/build_tree_beta.py`) and rebuilt output.

## What was fixed now
1. Overlay clarity and mode awareness
- Settings now includes a background scrim so users can clearly perceive overlay mode.
- Benefit: stronger visual context change and less accidental interaction ambiguity.

2. Focus management for overlays
- Added focus entry and return logic:
  - Opening settings moves focus inside the settings drawer.
  - Closing settings returns focus to the previously focused control.
  - Intro modal follows the same pattern.
- Benefit: keyboard users do not lose context.

3. Focus containment while overlays are open
- Added Tab/Shift+Tab focus trapping for:
  - Intro modal
  - Settings drawer
- Benefit: keyboard traversal stays within active dialog/panel.

4. Dialog semantics
- Settings drawer now has dialog semantics:
  - `role="dialog"`
  - `aria-modal="true"`
  - `aria-labelledby` bound to drawer title
- Benefit: better assistive tech interpretation of active overlay.

5. Localized accessibility labels
- Added bilingual localized ARIA labels for:
  - Left control panel container
  - Top-right map toolbar
- Benefit: screen reader labels follow selected language.

6. Reduced motion support
- Added `@media (prefers-reduced-motion: reduce)` fallback to minimize animations/transitions.
- Benefit: better support for motion sensitivity preferences.

7. Readability and visual refresh
- Updated background/typography tokens to a cleaner modern style.
- Kept high-contrast mode and theme switching intact.

## Current status after this pass
- Keyboard basics: improved and stable for overlays.
- Semantics: improved for settings dialog and labelled regions.
- Contrast tooling: high-contrast mode present; visual tokens still need formal contrast verification in-browser.

## Remaining checks (manual)
1. Screen reader smoke test
- VoiceOver/NVDA: confirm drawer and modal are announced with clear labels and expected focus order.

2. Full keyboard walkthrough
- Verify tab order for all controls in both FI and EN.
- Confirm Escape behavior for intro modal, settings drawer, and mobile panel collapse.

3. Contrast verification (automated)
- Run axe/Lighthouse on day, night, and high-contrast combinations.
- Check text contrast in legend, muted helper text, and disabled-looking states.

4. Mobile assistive checks
- iOS/Android viewport test for drawer sizing, focus visibility, and touch targets.

## Notes
- Map marker rendering and Leaflet canvas internals are still constrained by third-party map accessibility limits.
- The non-map list remains available as the keyboard/screen-reader friendly selection path.
