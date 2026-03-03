# Step 3 - UI Pass 2 (Onboarding + Settings + Theme)

## Scope
Implement product-facing onboarding and settings controls based on review notes.

## Implemented
- First-visit modal with:
  - data explainer (Street/Park/Supplement + coverage caveat)
  - full disclaimer text
  - "Do not show again" preference
  - direct action to open settings
- Collapsible settings menu with:
  - language selector (FI/EN)
  - theme selector (System / Day / Night)
  - high contrast toggle
  - explainer + disclaimer sections
- Preference persistence using local storage:
  - language
  - theme
  - high contrast
  - hide intro modal
- Visual refresh:
  - updated color tokens and modernized panel styling
  - stronger color separation between Street (blue) and Park (green)
  - Supplement remains amber
- Theme-aware basemap behavior:
  - day/system-light: OSM standard tiles
  - night/system-dark: CARTO dark tiles

## Output
- Rebuilt `output/helsinki_trees_beta.html`

## Next validation focus
1. Verify modal copy clarity and legal tone.
2. Verify settings persistence after hard refresh.
3. Verify day/night contrast on desktop + mobile.
4. Re-run accessibility audit on this pass-2 UI.
