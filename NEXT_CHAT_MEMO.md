# Next Chat Memo - Helsinki Trees Project

## Objective
Start a new public map project (similar to traffic beta) using Helsinki tree open data.

## Current state
Step 1 (data viability gate) is completed.

- Report: `docs/step1-data-viability.md`
- Metrics JSON: `data/processed/step1_gate_summary.json`
- Dataset selected: `helsingin-kaupungin-puurekisteri` (Helsinki urban tree database / Puuatlas)
- Data source: WFS layer `avoindata:Puurekisteri_piste`
- License: `CC BY 4.0`

## Gate outcome
PASS for Beta V1 tree map.

Why:
- Scale is solid (`58,561` trees, full export available).
- Geometry is complete and map-ready.
- Species/location fields are strong.
- Multiple export formats available (CSV/JSON/GeoJSON).

Known caveats to carry forward:
- `istutusvuosi` is mostly missing (~73.76%) and has a small number of implausible values.
- Street/park name fields are complementary (`kadunnimi` vs `puistonnimi`), not both expected per row.
- Source itself warns data is not systematically updated in all parts.

## Proposed next step (Step 2)
Define Beta V1 scope + output contract before coding:

1. Build target: single standalone HTML map for WordPress embedding.
2. Core filters:
- `paatyyppi` (Katu/Puisto/Täydennys)
- species (`suomenknimi`, optional `suku`)
- optional `kokoluokka`
3. Details panel fields:
- display name fallback (`kadunnimi` -> `puistonnimi` -> coords)
- species (Finnish + scientific)
- size class
- planting year (only if plausible)
4. Data cleaning rules:
- drop/blank implausible `istutusvuosi` (<1800 or >current_year+1)
5. First output file naming (beta convention):
- `output/helsinki_trees_beta.html`

## Reuse from traffic project
- Keep same deployment model: build local -> upload static HTML -> iframe into WordPress page.
- Keep same accessibility mindset from traffic beta (keyboard/touch-friendly panels, clear legend/explainer).
