# Helsinki Trees Beta (V1)

Standalone, bilingual (FI/EN) map build for Helsinki urban tree data.

## Build

```bash
cd /Users/tkalcan/Codex/HKI\ City\ API/helsinki-trees
make build
```

## Outputs

- `data/processed/trees_clean.json`
- `output/helsinki_trees_beta.html`

## Data rules

- Source: `data/raw/puurekisteri_full.csv`
- Geometry parsed from `geom` WKT (`POINT (lon lat)`).
- `istutusvuosi` is kept only if plausible (`1800..current_year+1`).

## Notes

- The HTML output is a single file that embeds cleaned dataset + UI code.
- Leaflet and MarkerCluster are loaded from CDN at runtime.
