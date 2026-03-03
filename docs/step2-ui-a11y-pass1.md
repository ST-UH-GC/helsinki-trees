# Step 2 - UI + Accessibility Pass 1

## Scope
Baseline usability/accessibility improvements without architecture refactor.

## Changes implemented
- Added keyboard skip links to jump between filters and map.
- Added explicit label binding for all filter selects.
- Added ARIA live regions for status and selected-item announcements.
- Added screen-reader announcer for selected tree updates.
- Added language toggle ARIA state (`aria-pressed`) and synced document `lang` attribute.
- Increased touch target size for buttons/selects/list items.
- Improved focus visibility across interactive elements.
- Added mobile panel toggle (`Open filters` / `Hide filters`) with `aria-expanded` state.
- Added mobile layout behavior where map stays full-screen and panel can collapse.
- Added assistive usage hint text in both Finnish and English.

## Outputs
- `output/helsinki_trees_beta.html` rebuilt from updated source.

## Manual checks for next session
1. Keyboard-only flow:
- Tab to skip links.
- Reach filters, reset, list buttons, language toggle.
- Ensure visible focus ring throughout.
2. Screen reader smoke test:
- Verify selected tree announcement.
- Verify status updates are announced appropriately.
3. Mobile view (iPhone width + Android width):
- Panel toggle open/close behavior.
- Touch target comfort for filters and list buttons.
- Map remains usable with panel open and collapsed.
4. Contrast review:
- Focus ring and control text against backgrounds.

## Out of scope in this pass
- Deeper code modularization/refactor.
- Full WCAG audit report and issue matrix.
