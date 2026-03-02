# Step 1 - Data Viability Gate (Helsinki Trees Beta)

## Goal
Assess whether Helsinki's open tree dataset is viable for a map-first beta similar to the traffic project.

## Dataset used
- Dataset: `helsingin-kaupungin-puurekisteri` (Helsingin kaupungin puurekisteri / Puuatlas)
- CKAN API: `https://www.opendata.fi/data/api/3/action/package_show?id=helsingin-kaupungin-puurekisteri`
- WFS endpoint: `https://kartta.hel.fi/ws/geoserver/avoindata/wfs`
- Layer: `avoindata:Puurekisteri_piste`
- License: `CC BY 4.0`

## Gate checks

### 1) Access + format support
- `GetCapabilities` and `DescribeFeatureType` are reachable.
- `GetFeature` supports practical outputs for app work (`csv`, `application/json`, `application/geo+json`, etc.).
- Full CSV export was retrieved successfully in EPSG:4326.

Result: PASS

### 2) Scale and coverage
- WFS `resultType=hits` returns `numberMatched=58561`.
- Full CSV rows downloaded: `58561` (matches hits).
- WGS84 coordinate envelope from data:
  - lat: `60.141081...` to `60.288373...`
  - lon: `24.833407...` to `25.198375...`

Result: PASS

### 3) Schema usefulness (for map UX)
Main usable fields are present:
- `id`, `tunnus`
- location context: `kadunnimi`, `puistonnimi`, `paatyyppi`
- species: `suomenknimi`, `suku`, `laji`
- size/age-ish: `kokoluokka`, `istutusvuosi`
- freshness marker: `paivitetty_tietopalveluun`
- geometry: `geom`

Result: PASS

### 4) Data quality snapshot (full dataset)
Missingness:
- `id`: 0.0%
- `tunnus`: 0.0%
- `paatyyppi`: 0.0%
- `suomenknimi`: 0.01%
- `laji`: ~0.0%
- `kokoluokka`: 14.60%
- `istutusvuosi`: 73.76% missing
- `kadunnimi`: 55.12% missing
- `puistonnimi`: 45.76% missing
- `geom`: 0.0%
- `paivitetty_tietopalveluun`: 0.0%

Notable caveats:
- `istutusvuosi` contains implausible values (e.g. `0`, `5`, `10`, `239`, `1716`, `20100`) in 14 rows.
- As expected, `kadunnimi` and `puistonnimi` are complementary (street trees vs park trees).

Result: PASS with caveats

### 5) Recency signal
- `paivitetty_tietopalveluun` is populated for all rows and currently `2026-02-27` in the export used.

Result: PASS

## Gate decision
PASS for Beta V1 tree map.

The dataset is strong enough for a public map beta with filtering and summary panels.
Main constraint is the high missingness/noise in `istutusvuosi`, so age-based features should be optional and quality-labeled.

## Recommended constraints for next step
- Treat `istutusvuosi` as optional; discard implausible years (<1800 or >current year+1).
- Build a display label fallback chain:
  1. `kadunnimi`
  2. `puistonnimi`
  3. nearest area/district (later)
  4. coordinates
- Prefer species filters from `suomenknimi` and `suku`; keep raw scientific `laji` available in details.
- Include an explicit “data quality note” in UI (park tree completeness varies).

## Repro artifacts
- Summary JSON: `data/processed/step1_gate_summary.json`
- Raw files:
  - `data/raw/package_puurekisteri.json`
  - `data/raw/wfs_getcapabilities.xml`
  - `data/raw/wfs_describe_puurekisteri.xsd`
  - `data/raw/wfs_hits.xml`
  - `data/raw/puurekisteri_full.csv`
