#!/usr/bin/env python3
"""Build a bilingual Helsinki trees beta map as a single embeddable HTML file."""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "puurekisteri_full.csv"
PROCESSED_JSON = ROOT / "data" / "processed" / "trees_clean.json"
OUTPUT_HTML = ROOT / "output" / "helsinki_trees_beta.html"

MIN_YEAR = 1800
GEOM_RE = re.compile(r"POINT\s*\(\s*([-+0-9.]+)\s+([-+0-9.]+)\s*\)")


def normalize(value: str | None) -> str:
    return (value or "").strip()


def parse_year(raw: str, current_year: int) -> tuple[int | None, bool]:
    raw = normalize(raw)
    if not raw:
        return None, False
    try:
        year = int(float(raw))
    except ValueError:
        return None, True
    if year < MIN_YEAR or year > (current_year + 1):
        return None, True
    return year, False


def parse_point_wkt(raw_geom: str) -> tuple[float, float] | None:
    match = GEOM_RE.search(raw_geom or "")
    if not match:
        return None
    lon = float(match.group(1))
    lat = float(match.group(2))
    return lat, lon


def sort_filter_counter(counter: Counter[str]) -> list[dict[str, object]]:
    entries = [{"value": key, "count": count} for key, count in counter.items() if key]
    entries.sort(key=lambda rec: (-int(rec["count"]), str(rec["value"]).casefold()))
    return entries


def build_payload() -> dict[str, object]:
    current_year = dt.date.today().year
    rows: list[list[object]] = []

    invalid_geom_rows = 0
    invalid_year_rows = 0
    total_rows = 0

    types = Counter()
    species = Counter()
    genus = Counter()
    size_classes = Counter()

    updated_dates: set[str] = set()

    with RAW_CSV.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for record in reader:
            total_rows += 1
            point = parse_point_wkt(record.get("geom", ""))
            if point is None:
                invalid_geom_rows += 1
                continue
            lat, lon = point

            kind = normalize(record.get("paatyyppi"))
            finnish_species = normalize(record.get("suomenknimi"))
            genus_name = normalize(record.get("suku"))
            scientific_species = normalize(record.get("laji"))
            size_class = normalize(record.get("kokoluokka"))
            street_name = normalize(record.get("kadunnimi"))
            park_name = normalize(record.get("puistonnimi"))
            updated_date = normalize(record.get("paivitetty_tietopalveluun"))

            year, year_invalid = parse_year(record.get("istutusvuosi", ""), current_year)
            if year_invalid:
                invalid_year_rows += 1

            rows.append(
                [
                    round(lat, 6),
                    round(lon, 6),
                    kind,
                    finnish_species,
                    genus_name,
                    scientific_species,
                    size_class,
                    year,
                    street_name,
                    park_name,
                ]
            )

            if kind:
                types[kind] += 1
            if finnish_species:
                species[finnish_species] += 1
            if genus_name:
                genus[genus_name] += 1
            if size_class:
                size_classes[size_class] += 1
            if updated_date:
                updated_dates.add(updated_date)

    payload = {
        "meta": {
            "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "source_csv": str(RAW_CSV.relative_to(ROOT)),
            "total_rows": total_rows,
            "clean_rows": len(rows),
            "invalid_geom_rows": invalid_geom_rows,
            "invalid_year_rows": invalid_year_rows,
            "year_min_allowed": MIN_YEAR,
            "year_max_allowed": current_year + 1,
            "source_updated_dates": sorted(updated_dates),
        },
        "filters": {
            "paatyyppi": sort_filter_counter(types),
            "suomenknimi": sort_filter_counter(species),
            "suku": sort_filter_counter(genus),
            "kokoluokka": sort_filter_counter(size_classes),
        },
        "rows": rows,
    }
    return payload


def build_html(data_json: str) -> str:
    return f"""<!doctype html>
<html lang=\"fi\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Helsinki Trees Beta</title>
  <link
    rel=\"stylesheet\"
    href=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css\"
    integrity=\"sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=\"
    crossorigin=\"\"
  />
  <link
    rel=\"stylesheet\"
    href=\"https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css\"
  />
  <link
    rel=\"stylesheet\"
    href=\"https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css\"
  />
  <style>
    :root {{
      --bg-top: #d9f3dd;
      --bg-bottom: #f7fff3;
      --panel: #ffffff;
      --ink: #152318;
      --muted: #4f6755;
      --line: #d6e3d4;
      --primary: #146c2e;
      --primary-2: #1f8f40;
      --warn: #975004;
      --street: #1293a8;
      --park: #1d8b45;
      --supplement: #c96a11;
      --shadow: 0 16px 32px rgba(15, 38, 20, 0.12);
    }}

    * {{ box-sizing: border-box; }}

    html, body {{
      height: 100%;
      margin: 0;
      font-family: \"Trebuchet MS\", \"Avenir Next\", \"Segoe UI\", sans-serif;
      color: var(--ink);
      background: linear-gradient(165deg, var(--bg-top), var(--bg-bottom));
    }}

    .app {{
      position: fixed;
      inset: 0;
      display: grid;
      grid-template-columns: minmax(280px, 380px) 1fr;
      gap: 12px;
      padding: 12px;
    }}

    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: var(--shadow);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      min-height: 0;
    }}

    .panel-head {{
      padding: 14px 14px 10px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, #f7fff7 0%, #ffffff 100%);
    }}

    .title-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 8px;
    }}

    h1 {{
      margin: 0;
      font-size: 1.08rem;
      line-height: 1.2;
      letter-spacing: 0.01em;
    }}

    .lang-switch {{
      display: inline-flex;
      border: 1px solid var(--line);
      border-radius: 999px;
      overflow: hidden;
    }}

    .lang-btn {{
      border: 0;
      background: #fff;
      color: var(--muted);
      cursor: pointer;
      padding: 5px 9px;
      font-size: 0.78rem;
      font-weight: 700;
      min-width: 42px;
    }}

    .lang-btn.active {{
      background: var(--primary);
      color: #fff;
    }}

    .meta {{
      display: grid;
      gap: 5px;
      font-size: 0.82rem;
      color: var(--muted);
      margin-bottom: 10px;
    }}

    .controls {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
    }}

    .control-label {{
      display: block;
      font-size: 0.8rem;
      margin-bottom: 4px;
      color: var(--muted);
      font-weight: 600;
    }}

    select, button {{
      width: 100%;
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 9px;
      padding: 8px 10px;
      color: var(--ink);
      font-size: 0.9rem;
    }}

    button {{
      cursor: pointer;
      background: linear-gradient(180deg, #e9f8eb, #dcf2df);
      border-color: #b8d6be;
      font-weight: 700;
    }}

    .status {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 0.84rem;
      min-height: 1.1rem;
    }}

    .panel-body {{
      min-height: 0;
      overflow: auto;
      padding: 12px 14px 14px;
      display: grid;
      gap: 10px;
      align-content: start;
    }}

    .detail-card {{
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px;
      background: #fbfefb;
      display: grid;
      gap: 7px;
    }}

    .detail-title {{
      margin: 0;
      font-size: 0.95rem;
      line-height: 1.2;
    }}

    .detail-grid {{
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 5px 9px;
      font-size: 0.82rem;
    }}

    .detail-grid dt {{
      color: var(--muted);
      font-weight: 700;
      margin: 0;
    }}

    .detail-grid dd {{
      margin: 0;
      word-break: break-word;
    }}

    .note {{
      border-left: 4px solid #e8b150;
      padding: 8px 10px;
      background: #fff9eb;
      color: #6d4b11;
      font-size: 0.81rem;
      border-radius: 4px;
    }}

    .list-wrap {{
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: hidden;
      background: #fff;
    }}

    .list-head {{
      padding: 8px 10px;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.8rem;
      font-weight: 700;
    }}

    .top-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      max-height: 200px;
      overflow: auto;
    }}

    .top-list li + li {{ border-top: 1px solid #edf3ed; }}

    .top-item-btn {{
      text-align: left;
      padding: 8px 10px;
      width: 100%;
      border: 0;
      border-radius: 0;
      background: #fff;
      cursor: pointer;
      font-size: 0.83rem;
      color: var(--ink);
      font-weight: 600;
    }}

    .top-item-btn:hover,
    .top-item-btn:focus-visible {{
      background: #f0f8f0;
      outline: 2px solid #bbdfc3;
      outline-offset: -2px;
    }}

    #map-wrap {{
      border-radius: 16px;
      overflow: hidden;
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      position: relative;
      min-height: 0;
      background: #e3f3e7;
    }}

    #map {{
      position: absolute;
      inset: 0;
    }}

    .legend {{
      position: absolute;
      right: 12px;
      bottom: 12px;
      z-index: 500;
      background: rgba(255, 255, 255, 0.94);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 8px 10px;
      font-size: 0.78rem;
      color: var(--muted);
      box-shadow: var(--shadow);
      max-width: 220px;
    }}

    .legend-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 5px;
    }}

    .swatch {{
      width: 11px;
      height: 11px;
      border-radius: 999px;
      border: 1px solid rgba(0, 0, 0, 0.25);
      display: inline-block;
      flex: 0 0 auto;
    }}

    @media (max-width: 960px) {{
      .app {{
        grid-template-columns: 1fr;
        grid-template-rows: auto 1fr;
      }}

      .panel {{
        max-height: 46vh;
      }}
    }}
  </style>
</head>
<body>
  <div class=\"app\">
    <aside class=\"panel\" aria-label=\"Controls and details\">
      <div class=\"panel-head\">
        <div class=\"title-row\">
          <h1 id=\"title\"></h1>
          <div class=\"lang-switch\" role=\"group\" aria-label=\"Language\">
            <button id=\"lang-fi\" class=\"lang-btn\" type=\"button\" data-lang=\"fi\">FI</button>
            <button id=\"lang-en\" class=\"lang-btn\" type=\"button\" data-lang=\"en\">EN</button>
          </div>
        </div>

        <div class=\"meta\">
          <div id=\"meta-total\"></div>
          <div id=\"meta-updated\"></div>
        </div>

        <div class=\"controls\">
          <label>
            <span class=\"control-label\" id=\"label-type\"></span>
            <select id=\"filter-type\"></select>
          </label>
          <label>
            <span class=\"control-label\" id=\"label-species\"></span>
            <select id=\"filter-species\"></select>
          </label>
          <label>
            <span class=\"control-label\" id=\"label-genus\"></span>
            <select id=\"filter-genus\"></select>
          </label>
          <label>
            <span class=\"control-label\" id=\"label-size\"></span>
            <select id=\"filter-size\"></select>
          </label>
          <button id=\"btn-reset\" type=\"button\"></button>
          <div id=\"status\" class=\"status\"></div>
        </div>
      </div>

      <div class=\"panel-body\">
        <section class=\"detail-card\" aria-live=\"polite\" id=\"detail-card\">
          <h2 class=\"detail-title\" id=\"detail-title\"></h2>
          <dl class=\"detail-grid\" id=\"detail-grid\"></dl>
        </section>

        <section class=\"list-wrap\">
          <div class=\"list-head\" id=\"top-list-title\"></div>
          <ul id=\"top-list\" class=\"top-list\"></ul>
        </section>

        <section class=\"note\" id=\"quality-note\"></section>
      </div>
    </aside>

    <main id=\"map-wrap\" aria-label=\"Helsinki trees map\">
      <div id=\"map\"></div>
      <div class=\"legend\" id=\"legend\"></div>
    </main>
  </div>

  <script src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\" integrity=\"sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=\" crossorigin=\"\"></script>
  <script src=\"https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js\"></script>
  <script>
    const TREE_DATA = {data_json};

    const I18N = {{
      fi: {{
        title: "Helsingin puut (beta)",
        total: "Puut yhteensa: {{count}}",
        updated: "Lahde paivitetty: {{date}}",
        labelType: "Tyyppi",
        labelSpecies: "Laji (suomi)",
        labelGenus: "Suku",
        labelSize: "Kokoluokka",
        reset: "Tyhjenna suodattimet",
        all: "Kaikki",
        status: "Nakyvissa: {{count}} / {{total}}",
        statusRendering: "Paivitetaan karttaa...",
        detailsPlaceholder: "Valitse puu kartalta tai listalta",
        detailType: "Tyyppi",
        detailSpecies: "Laji",
        detailScientific: "Tieteellinen",
        detailSize: "Kokoluokka",
        detailYear: "Istutusvuosi",
        detailLocation: "Sijainti",
        detailCoordinates: "Koordinaatit",
        missing: "Ei tietoa",
        topListTitle: "Esimerkkikohteet (ensimmaiset 30)",
        topListEmpty: "Ei kohteita nykyisilla suodattimilla.",
        qualityNote: "Datalaatuhuomio: istutusvuosi on usein puutteellinen. Epaloogiset vuosiluvut on poistettu.",
        legendTitle: "Puun tyyppi",
        typeKatu: "Katu",
        typePuisto: "Puisto",
        typeTaydennys: "Taydennys",
      }},
      en: {{
        title: "Helsinki Trees (beta)",
        total: "Total trees: {{count}}",
        updated: "Source updated: {{date}}",
        labelType: "Type",
        labelSpecies: "Species (Finnish)",
        labelGenus: "Genus",
        labelSize: "Size class",
        reset: "Reset filters",
        all: "All",
        status: "Visible: {{count}} / {{total}}",
        statusRendering: "Updating map...",
        detailsPlaceholder: "Select a tree from map or list",
        detailType: "Type",
        detailSpecies: "Species",
        detailScientific: "Scientific",
        detailSize: "Size class",
        detailYear: "Planting year",
        detailLocation: "Location",
        detailCoordinates: "Coordinates",
        missing: "Not available",
        topListTitle: "Sample locations (first 30)",
        topListEmpty: "No rows with current filters.",
        qualityNote: "Data quality note: planting year is frequently missing. Implausible years are removed.",
        legendTitle: "Tree type",
        typeKatu: "Street",
        typePuisto: "Park",
        typeTaydennys: "Supplement",
      }},
    }};

    const TYPE_COLORS = {{
      Katu: "#1293a8",
      Puisto: "#1d8b45",
      "Taydennys": "#c96a11",
      "Täydennys": "#c96a11",
      default: "#6a7f71"
    }};

    const SELECT_FIELDS = [
      {{ key: "paatyyppi", selectId: "filter-type", idx: 2 }},
      {{ key: "suomenknimi", selectId: "filter-species", idx: 3 }},
      {{ key: "suku", selectId: "filter-genus", idx: 4 }},
      {{ key: "kokoluokka", selectId: "filter-size", idx: 6 }},
    ];

    const meta = TREE_DATA.meta;
    const rows = TREE_DATA.rows;
    const filters = TREE_DATA.filters;

    const defaultLang = (navigator.language || "").toLowerCase().startsWith("fi") ? "fi" : "en";
    let lang = defaultLang;

    const state = {{
      visibleRows: [],
      hasFitBounds: false,
      selectedRow: null,
      filterValues: {{
        paatyyppi: "",
        suomenknimi: "",
        suku: "",
        kokoluokka: "",
      }},
    }};

    const map = L.map("map", {{
      center: [60.192059, 24.945831],
      zoom: 12,
      minZoom: 10,
      preferCanvas: true,
      zoomControl: true,
    }});

    L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }}).addTo(map);

    const clusterLayer = L.markerClusterGroup({{
      chunkedLoading: true,
      chunkInterval: 120,
      chunkDelay: 20,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      disableClusteringAtZoom: 17,
      maxClusterRadius: 45,
    }});
    map.addLayer(clusterLayer);

    const dom = {{
      title: document.getElementById("title"),
      metaTotal: document.getElementById("meta-total"),
      metaUpdated: document.getElementById("meta-updated"),
      labelType: document.getElementById("label-type"),
      labelSpecies: document.getElementById("label-species"),
      labelGenus: document.getElementById("label-genus"),
      labelSize: document.getElementById("label-size"),
      btnReset: document.getElementById("btn-reset"),
      status: document.getElementById("status"),
      detailTitle: document.getElementById("detail-title"),
      detailGrid: document.getElementById("detail-grid"),
      qualityNote: document.getElementById("quality-note"),
      topListTitle: document.getElementById("top-list-title"),
      topList: document.getElementById("top-list"),
      legend: document.getElementById("legend"),
      langFi: document.getElementById("lang-fi"),
      langEn: document.getElementById("lang-en"),
    }};

    function t(key) {{
      return I18N[lang][key] || key;
    }}

    function format(msg, vars) {{
      return Object.entries(vars).reduce(
        (out, [key, value]) => out.replace(`{{${{key}}}}`, String(value)),
        msg
      );
    }}

    function typeLabel(rawType) {{
      if (!rawType) return t("missing");
      if (rawType === "Katu") return t("typeKatu");
      if (rawType === "Puisto") return t("typePuisto");
      if (rawType === "Täydennys" || rawType === "Taydennys") return t("typeTaydennys");
      return rawType;
    }}

    function optionLabel(fieldKey, rawValue) {{
      if (!rawValue) return t("missing");
      if (fieldKey === "paatyyppi") return typeLabel(rawValue);
      return rawValue;
    }}

    function displayName(row) {{
      const street = row[8];
      const park = row[9];
      if (street) return street;
      if (park) return park;
      return `${{row[0].toFixed(5)}}, ${{row[1].toFixed(5)}}`;
    }}

    function scientificName(row) {{
      return [row[4], row[5]].filter(Boolean).join(" ");
    }}

    function markerColor(row) {{
      const raw = row[2] || "";
      return TYPE_COLORS[raw] || TYPE_COLORS.default;
    }}

    function updateStaticTexts() {{
      dom.title.textContent = t("title");
      dom.labelType.textContent = t("labelType");
      dom.labelSpecies.textContent = t("labelSpecies");
      dom.labelGenus.textContent = t("labelGenus");
      dom.labelSize.textContent = t("labelSize");
      dom.btnReset.textContent = t("reset");
      dom.qualityNote.textContent = t("qualityNote");
      dom.topListTitle.textContent = t("topListTitle");

      const updatedDates = (meta.source_updated_dates || []).join(", ") || t("missing");
      dom.metaTotal.textContent = format(t("total"), {{ count: Number(meta.clean_rows).toLocaleString() }});
      dom.metaUpdated.textContent = format(t("updated"), {{ date: updatedDates }});

      dom.legend.innerHTML = `
        <div><strong>${{t("legendTitle")}}</strong></div>
        <div class=\"legend-row\"><span class=\"swatch\" style=\"background:${{TYPE_COLORS.Katu}}\"></span>${{t("typeKatu")}}</div>
        <div class=\"legend-row\"><span class=\"swatch\" style=\"background:${{TYPE_COLORS.Puisto}}\"></span>${{t("typePuisto")}}</div>
        <div class=\"legend-row\"><span class=\"swatch\" style=\"background:${{TYPE_COLORS["Täydennys"]}}\"></span>${{t("typeTaydennys")}}</div>
      `;

      dom.langFi.classList.toggle("active", lang === "fi");
      dom.langEn.classList.toggle("active", lang === "en");

      fillFilters();
      if (state.selectedRow) {{
        showDetails(state.selectedRow);
      }} else {{
        showDetails(null);
      }}
      renderTopList();
      updateStatus();
    }}

    function fillFilters() {{
      for (const field of SELECT_FIELDS) {{
        const select = document.getElementById(field.selectId);
        const oldValue = state.filterValues[field.key] || "";
        const options = filters[field.key] || [];

        select.innerHTML = "";
        const allOption = document.createElement("option");
        allOption.value = "";
        allOption.textContent = `${{t("all")}}`;
        select.appendChild(allOption);

        for (const option of options) {{
          const el = document.createElement("option");
          el.value = option.value;
          const count = Number(option.count || 0).toLocaleString();
          el.textContent = `${{optionLabel(field.key, option.value)}} (${{count}})`;
          select.appendChild(el);
        }}

        if ([...select.options].some((opt) => opt.value === oldValue)) {{
          select.value = oldValue;
        }} else {{
          select.value = "";
          state.filterValues[field.key] = "";
        }}
      }}
    }}

    function rowMatches(row) {{
      if (state.filterValues.paatyyppi && row[2] !== state.filterValues.paatyyppi) return false;
      if (state.filterValues.suomenknimi && row[3] !== state.filterValues.suomenknimi) return false;
      if (state.filterValues.suku && row[4] !== state.filterValues.suku) return false;
      if (state.filterValues.kokoluokka && row[6] !== state.filterValues.kokoluokka) return false;
      return true;
    }}

    function updateStatus(isRendering = false) {{
      if (isRendering) {{
        dom.status.textContent = t("statusRendering");
        return;
      }}
      dom.status.textContent = format(t("status"), {{
        count: Number(state.visibleRows.length).toLocaleString(),
        total: Number(meta.clean_rows).toLocaleString(),
      }});
    }}

    function showDetails(row) {{
      state.selectedRow = row;
      if (!row) {{
        dom.detailTitle.textContent = t("detailsPlaceholder");
        dom.detailGrid.innerHTML = "";
        return;
      }}

      const scientific = scientificName(row) || t("missing");
      const year = row[7] || t("missing");
      const location = displayName(row);
      const coords = `${{row[0].toFixed(5)}}, ${{row[1].toFixed(5)}}`;

      dom.detailTitle.textContent = location;
      dom.detailGrid.innerHTML = `
        <dt>${{t("detailType")}}</dt><dd>${{typeLabel(row[2])}}</dd>
        <dt>${{t("detailSpecies")}}</dt><dd>${{row[3] || t("missing")}}</dd>
        <dt>${{t("detailScientific")}}</dt><dd>${{scientific}}</dd>
        <dt>${{t("detailSize")}}</dt><dd>${{row[6] || t("missing")}}</dd>
        <dt>${{t("detailYear")}}</dt><dd>${{year}}</dd>
        <dt>${{t("detailLocation")}}</dt><dd>${{location}}</dd>
        <dt>${{t("detailCoordinates")}}</dt><dd>${{coords}}</dd>
      `;
    }}

    function renderTopList() {{
      dom.topList.innerHTML = "";
      if (state.visibleRows.length === 0) {{
        const li = document.createElement("li");
        li.textContent = t("topListEmpty");
        li.style.padding = "8px 10px";
        li.style.color = "#4f6755";
        dom.topList.appendChild(li);
        return;
      }}

      const rowsForList = state.visibleRows.slice(0, 30);
      for (const row of rowsForList) {{
        const li = document.createElement("li");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "top-item-btn";
        const label = `${{displayName(row)}} - ${{row[3] || t("missing")}}`;
        btn.textContent = label;
        btn.addEventListener("click", () => {{
          map.setView([row[0], row[1]], Math.max(map.getZoom(), 16), {{ animate: true }});
          showDetails(row);
        }});
        li.appendChild(btn);
        dom.topList.appendChild(li);
      }}
    }}

    function buildMarkersForVisibleRows() {{
      const markers = [];
      for (const row of state.visibleRows) {{
        const marker = L.circleMarker([row[0], row[1]], {{
          radius: 4,
          color: markerColor(row),
          weight: 1,
          fillColor: markerColor(row),
          fillOpacity: 0.86,
        }});
        marker.bindTooltip(`${{displayName(row)}}`, {{ direction: "top", offset: [0, -4] }});
        marker.on("click", () => showDetails(row));
        markers.push(marker);
      }}
      return markers;
    }}

    function applyFiltersAndRender() {{
      updateStatus(true);
      window.requestAnimationFrame(() => {{
        state.visibleRows = rows.filter(rowMatches);

        clusterLayer.clearLayers();
        const markers = buildMarkersForVisibleRows();
        clusterLayer.addLayers(markers);

        if (!state.hasFitBounds && state.visibleRows.length > 0) {{
          const bounds = L.latLngBounds(state.visibleRows.map((row) => [row[0], row[1]]));
          map.fitBounds(bounds.pad(0.05));
          state.hasFitBounds = true;
        }}

        if (state.selectedRow && !rowMatches(state.selectedRow)) {{
          showDetails(null);
        }}

        renderTopList();
        updateStatus(false);
      }});
    }}

    function setupEvents() {{
      for (const field of SELECT_FIELDS) {{
        const select = document.getElementById(field.selectId);
        select.addEventListener("change", (event) => {{
          state.filterValues[field.key] = event.target.value;
          applyFiltersAndRender();
        }});
      }}

      dom.btnReset.addEventListener("click", () => {{
        state.filterValues = {{
          paatyyppi: "",
          suomenknimi: "",
          suku: "",
          kokoluokka: "",
        }};
        fillFilters();
        applyFiltersAndRender();
      }});

      dom.langFi.addEventListener("click", () => {{
        lang = "fi";
        updateStaticTexts();
      }});

      dom.langEn.addEventListener("click", () => {{
        lang = "en";
        updateStaticTexts();
      }});
    }}

    setupEvents();
    updateStaticTexts();
    showDetails(null);
    applyFiltersAndRender();
  </script>
</body>
</html>
"""


def main() -> None:
    payload = build_payload()

    PROCESSED_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)

    processed_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    PROCESSED_JSON.write_text(processed_text + "\n", encoding="utf-8")

    safe_data_json = processed_text.replace("</", "<\\/")
    html = build_html(safe_data_json)
    OUTPUT_HTML.write_text(html, encoding="utf-8")

    print(f"Wrote {PROCESSED_JSON}")
    print(f"Wrote {OUTPUT_HTML}")
    print(f"Rows: {payload['meta']['clean_rows']} (from {payload['meta']['total_rows']})")


if __name__ == "__main__":
    main()
