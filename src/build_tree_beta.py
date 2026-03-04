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
  <style>
    :root {{
      --bg-top: #e8f8f3;
      --bg-bottom: #b9e5d8;
      --panel: #ffffff;
      --panel-soft: #eefaf5;
      --ink: #162033;
      --muted: #5a6780;
      --line: #b7dacc;
      --primary: #1f5eff;
      --primary-2: #1847c8;
      --warn: #975004;
      --street: #1f5eff;
      --park: #1ea85f;
      --supplement: #d97706;
      --shadow: 0 18px 36px rgba(12, 35, 78, 0.14);
    }}

    html[data-theme=\"night\"] {{
      --bg-top: #1d293c;
      --bg-bottom: #121c2b;
      --panel: #1b2738;
      --panel-soft: #243347;
      --ink: #e7f0ff;
      --muted: #b4c5e2;
      --line: #3a4f6f;
      --primary: #7ea8ff;
      --primary-2: #9fbeff;
      --warn: #f1b66d;
      --shadow: 0 20px 38px rgba(2, 6, 12, 0.45);
    }}

    html[data-contrast=\"high\"] {{
      --line: #000;
      --ink: #000;
      --muted: #1f1f1f;
      --primary: #0036d1;
    }}

    html[data-theme=\"night\"][data-contrast=\"high\"] {{
      --line: #fff;
      --ink: #fff;
      --muted: #f1f5ff;
    }}

    * {{ box-sizing: border-box; }}

    html, body {{
      height: 100%;
      margin: 0;
      font-family: \"Avenir Next\", \"Manrope\", \"Segoe UI\", sans-serif;
      color: var(--ink);
      background: linear-gradient(165deg, var(--bg-top), var(--bg-bottom));
    }}

    body {{
      position: relative;
    }}

    body::before,
    body::after {{
      content: "";
      position: fixed;
      pointer-events: none;
      z-index: 0;
      border-radius: 999px;
      filter: blur(2px);
    }}

    body::before {{
      width: 44vw;
      height: 44vw;
      top: -18vw;
      right: -10vw;
      background: radial-gradient(circle at center, rgba(46, 174, 151, 0.18), rgba(46, 174, 151, 0));
    }}

    body::after {{
      width: 38vw;
      height: 38vw;
      bottom: -17vw;
      left: -12vw;
      background: radial-gradient(circle at center, rgba(29, 138, 176, 0.16), rgba(29, 138, 176, 0));
    }}

    :focus-visible {{
      outline: 3px solid #0b5fff;
      outline-offset: 2px;
    }}

    .visually-hidden {{
      border: 0 !important;
      clip: rect(0 0 0 0) !important;
      height: 1px !important;
      margin: -1px !important;
      overflow: hidden !important;
      padding: 0 !important;
      position: absolute !important;
      white-space: nowrap !important;
      width: 1px !important;
    }}

    .skip-link {{
      position: absolute;
      top: -52px;
      left: 8px;
      z-index: 1200;
      background: #142a5c;
      color: #fff;
      border-radius: 8px;
      padding: 10px 12px;
      text-decoration: none;
      font-size: 0.86rem;
      font-weight: 700;
    }}

    .skip-link:focus {{
      top: 8px;
    }}

    .app {{
      position: fixed;
      inset: 0;
      padding: 12px;
      z-index: 1;
    }}

    #map-wrap {{
      position: absolute;
      inset: 12px;
      border-radius: 16px;
      overflow: hidden;
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      background: #98cfc1;
    }}

    #map {{
      position: absolute;
      inset: 0;
    }}

    .panel {{
      position: absolute;
      top: 12px;
      left: 12px;
      bottom: 12px;
      width: min(380px, calc(100vw - 24px));
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: var(--shadow);
      overflow: hidden;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      z-index: 830;
      transition: transform 220ms ease, box-shadow 220ms ease;
    }}

    .panel.is-collapsed {{
      transform: translateX(calc(-100% - 18px));
      box-shadow: none;
    }}

    .panel-head {{
      padding: 14px 14px 12px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, var(--panel-soft) 0%, var(--panel) 100%);
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

    .meta {{
      display: grid;
      gap: 5px;
      font-size: 0.82rem;
      color: var(--muted);
    }}

    .controls {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
    }}

    .controls-card {{
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px;
      background: var(--panel-soft);
    }}

    .control-label {{
      display: block;
      font-size: 0.8rem;
      margin-bottom: 4px;
      color: var(--muted);
      font-weight: 600;
    }}

    input, select, button {{
      width: 100%;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 9px;
      padding: 9px 10px;
      color: var(--ink);
      font-size: 0.9rem;
      min-height: 44px;
    }}

    button {{
      cursor: pointer;
      background: linear-gradient(180deg, #edf3ff, #e5eeff);
      border-color: #bed1ff;
      font-weight: 700;
    }}

    html[data-theme=\"night\"] button {{
      background: linear-gradient(180deg, #1e3157, #1a2b4e);
      border-color: #395894;
      color: var(--ink);
    }}

    input::placeholder {{
      color: var(--muted);
      opacity: 0.9;
    }}

    .status {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 0.84rem;
      min-height: 1.1rem;
    }}

    .assist-text {{
      margin: 0;
      color: var(--muted);
      font-size: 0.78rem;
      line-height: 1.35;
    }}

    .range-wrap {{
      display: grid;
      gap: 5px;
    }}

    input[type="range"] {{
      min-height: 36px;
      padding: 0;
      accent-color: var(--primary);
      border: 0;
      background: transparent;
    }}

    .panel-body {{
      min-height: 0;
      overflow-y: auto;
      overflow-x: hidden;
      padding: 12px 14px 14px;
      display: grid;
      gap: 10px;
      align-content: start;
      overscroll-behavior: contain;
      -webkit-overflow-scrolling: touch;
    }}

    .detail-card {{
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px;
      background: var(--panel-soft);
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
      background: #fff7e7;
      color: #5e3f0e;
      font-size: 0.81rem;
      border-radius: 4px;
    }}

    .list-wrap {{
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: hidden;
      background: var(--panel);
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

    .top-list li + li {{ border-top: 1px solid var(--line); }}

    .top-item-btn {{
      text-align: left;
      padding: 11px 10px;
      width: 100%;
      border: 0;
      border-radius: 0;
      background: var(--panel);
      cursor: pointer;
      font-size: 0.83rem;
      color: var(--ink);
      font-weight: 600;
    }}

    .top-item-btn:hover,
    .top-item-btn:focus-visible {{
      background: #eef4ff;
      outline: 3px solid #0b5fff;
      outline-offset: -2px;
    }}

    .map-toolbar {{
      position: absolute;
      top: 22px;
      right: 22px;
      z-index: 1080;
      display: flex;
      gap: 8px;
    }}

    .toolbar-btn {{
      width: 42px;
      min-width: 42px;
      min-height: 42px;
      padding: 0;
      border-radius: 10px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 1.1rem;
      line-height: 1;
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
    }}

    .toolbar-btn.active {{
      background: var(--primary);
      color: #fff;
      border-color: var(--primary);
    }}

    .settings-drawer {{
      position: absolute;
      top: 72px;
      right: 12px;
      width: min(360px, calc(100vw - 24px));
      max-height: calc(100vh - 84px);
      overflow-y: auto;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--panel);
      box-shadow: var(--shadow);
      padding: 12px;
      display: none;
      gap: 10px;
      z-index: 1100;
    }}

    .settings-drawer.open {{
      display: grid;
    }}

    .settings-scrim {{
      position: absolute;
      inset: 0;
      border: 0;
      margin: 0;
      padding: 0;
      background: rgba(8, 18, 38, 0.18);
      opacity: 0;
      pointer-events: none;
      transition: opacity 160ms ease;
      z-index: 1090;
    }}

    .settings-scrim.open {{
      opacity: 1;
      pointer-events: auto;
    }}

    html[data-theme=\"night\"] .settings-scrim {{
      background: rgba(6, 10, 20, 0.28);
    }}

    .settings-drawer-head {{
      position: sticky;
      top: -12px;
      margin: -12px -12px 0;
      padding: 10px 12px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      z-index: 2;
    }}

    .settings-drawer-head h2 {{
      margin: 0;
      font-size: 0.95rem;
      line-height: 1.2;
    }}

    .settings-group {{
      display: grid;
      gap: 6px;
    }}

    .settings-title {{
      margin: 0;
      font-size: 0.8rem;
      color: var(--muted);
      font-weight: 700;
    }}

    .settings-copy {{
      margin: 0;
      font-size: 0.79rem;
      color: var(--muted);
      line-height: 1.35;
    }}

    .legend {{
      position: absolute;
      right: 12px;
      bottom: 12px;
      z-index: 500;
      background: var(--panel);
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

    .intro-modal {{
      position: fixed;
      inset: 0;
      z-index: 1300;
      background: rgba(3, 8, 18, 0.58);
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px 14px;
    }}

    .intro-modal.open {{
      display: flex;
    }}

    .intro-card {{
      width: min(720px, 100%);
      max-height: 88vh;
      overflow: auto;
      border-radius: 16px;
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      padding: 16px 16px 14px;
      display: grid;
      gap: 12px;
    }}

    .intro-card h2 {{
      margin: 0;
      font-size: 1.1rem;
    }}

    .intro-card p {{
      margin: 0;
      color: var(--muted);
      font-size: 0.88rem;
      line-height: 1.45;
    }}

    .intro-actions {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}

    .check-line {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.84rem;
      color: var(--muted);
    }}

    @media (max-width: 1199px) {{
      .panel {{
        width: min(340px, calc(100vw - 24px));
      }}
    }}

    @media (max-width: 900px) {{
      .app {{
        padding: 0;
      }}

      #map-wrap {{
        inset: 0;
        border-radius: 0;
      }}

      .panel {{
        top: 0;
        bottom: 0;
        left: 0;
        border-radius: 0;
        width: min(86vw, 360px);
      }}

      .panel.is-collapsed {{
        transform: translateX(-100%);
      }}

      .map-toolbar {{
        top: 8px;
        right: 8px;
      }}

      .settings-drawer {{
        top: 56px;
        right: 8px;
        width: min(92vw, 360px);
        max-height: calc(100vh - 64px);
      }}

      .settings-scrim {{
        background: rgba(8, 18, 38, 0.3);
      }}

      .legend {{
        max-width: 180px;
        right: 8px;
        bottom: 8px;
      }}

      .intro-card {{
        padding: 14px;
      }}
    }}

    @media (prefers-reduced-motion: reduce) {{
      *,
      *::before,
      *::after {{
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
      }}
    }}
  </style>
</head>
<body>
  <a href=\"#control-panel\" class=\"skip-link\" id=\"skip-controls\"></a>
  <a href=\"#map-wrap\" class=\"skip-link\" id=\"skip-map\"></a>
  <div id=\"sr-announcer\" class=\"visually-hidden\" aria-live=\"polite\" aria-atomic=\"true\"></div>
  <section class=\"intro-modal\" id=\"intro-modal\" role=\"dialog\" aria-modal=\"true\" aria-labelledby=\"intro-title\">
    <div class=\"intro-card\">
      <h2 id=\"intro-title\"></h2>
      <p id=\"intro-explainer\"></p>
      <p id=\"intro-disclaimer\"></p>
      <label class=\"check-line\" for=\"intro-hide-next\">
        <input id=\"intro-hide-next\" type=\"checkbox\" />
        <span id=\"intro-hide-label\"></span>
      </label>
      <div class=\"intro-actions\">
        <button id=\"intro-open-settings\" type=\"button\"></button>
        <button id=\"intro-close\" type=\"button\"></button>
      </div>
    </div>
  </section>
  <div class=\"app\">
    <aside class=\"panel\" id=\"control-panel\" tabindex=\"-1\" aria-label=\"Controls and details\">
      <div class=\"panel-head\">
        <div class=\"title-row\">
          <h1 id=\"title\"></h1>
        </div>

        <div class=\"meta\">
          <div id=\"meta-total\"></div>
          <div id=\"meta-updated\"></div>
        </div>
      </div>

      <div class=\"panel-body\">
        <section class=\"controls controls-card\">
          <label for=\"filter-type\">
            <span class=\"control-label\" id=\"label-type\"></span>
          </label>
          <select id=\"filter-type\"></select>
          <label for=\"filter-species-search\">
            <span class=\"control-label\" id=\"label-species-search\"></span>
          </label>
          <input id=\"filter-species-search\" type=\"search\" />
          <label for=\"filter-species\">
            <span class=\"control-label\" id=\"label-species\"></span>
          </label>
          <select id=\"filter-species\"></select>
          <label for=\"filter-genus\">
            <span class=\"control-label\" id=\"label-genus\"></span>
          </label>
          <select id=\"filter-genus\"></select>
          <label for=\"filter-size\">
            <span class=\"control-label\" id=\"label-size\"></span>
          </label>
          <select id=\"filter-size\"></select>
          <div class=\"range-wrap\">
            <label for=\"filter-year\">
              <span class=\"control-label\" id=\"label-year\"></span>
            </label>
            <input id=\"filter-year\" type=\"range\" min=\"0\" max=\"0\" step=\"1\" value=\"0\" />
            <p id=\"year-readout\" class=\"assist-text\"></p>
          </div>
          <button id=\"btn-reset\" type=\"button\"></button>
          <div id=\"status\" class=\"status\" role=\"status\" aria-live=\"polite\"></div>
          <p id=\"map-help\" class=\"assist-text\"></p>
        </section>

        <section class=\"detail-card\" aria-live=\"polite\" id=\"detail-card\">
          <h2 class=\"detail-title\" id=\"detail-title\"></h2>
          <dl class=\"detail-grid\" id=\"detail-grid\"></dl>
        </section>

        <section class=\"list-wrap\" aria-labelledby=\"top-list-title\">
          <div class=\"list-head\" id=\"top-list-title\"></div>
          <ul id=\"top-list\" class=\"top-list\"></ul>
        </section>

        <section class=\"note\" id=\"quality-note\"></section>
      </div>
    </aside>

    <section id=\"settings-drawer\" class=\"settings-drawer\" role=\"dialog\" aria-modal=\"true\" aria-labelledby=\"settings-drawer-title\">
      <div class=\"settings-drawer-head\">
        <h2 id=\"settings-drawer-title\"></h2>
      </div>
      <div class=\"settings-group\">
        <h3 class=\"settings-title\" id=\"settings-language-label\"></h3>
        <select id=\"settings-language\" aria-labelledby=\"settings-language-label\">
          <option value=\"fi\">Suomi</option>
          <option value=\"en\">English</option>
        </select>
      </div>
      <div class=\"settings-group\">
        <h3 class=\"settings-title\" id=\"settings-theme-label\"></h3>
        <select id=\"settings-theme\" aria-labelledby=\"settings-theme-label\">
          <option value=\"system\"></option>
          <option value=\"day\"></option>
          <option value=\"night\"></option>
        </select>
      </div>
      <label class=\"check-line\" for=\"settings-contrast\">
        <input id=\"settings-contrast\" type=\"checkbox\" />
        <span id=\"settings-contrast-label\"></span>
      </label>
      <div class=\"settings-group\">
        <h3 class=\"settings-title\" id=\"settings-explainer-title\"></h3>
        <p class=\"settings-copy\" id=\"settings-explainer-copy\"></p>
      </div>
      <div class=\"settings-group\">
        <h3 class=\"settings-title\" id=\"settings-disclaimer-title\"></h3>
        <p class=\"settings-copy\" id=\"settings-disclaimer-copy\"></p>
      </div>
      <div class=\"settings-group\">
        <h3 class=\"settings-title\" id=\"settings-debug-title\"></h3>
        <div class=\"intro-actions\" style=\"justify-content:flex-start;\">
          <button id=\"settings-download-log\" type=\"button\"></button>
          <button id=\"settings-clear-log\" type=\"button\"></button>
        </div>
      </div>
    </section>
    <button id=\"settings-scrim\" class=\"settings-scrim\" type=\"button\" tabindex=\"-1\" aria-label=\"Close settings\"></button>

    <div class=\"map-toolbar\" id=\"map-toolbar\" aria-label=\"Map controls\">
      <button id=\"panel-toggle\" class=\"toolbar-btn\" type=\"button\" aria-controls=\"control-panel\" aria-expanded=\"true\">&#9776;</button>
      <button id=\"settings-btn\" class=\"toolbar-btn\" type=\"button\" aria-controls=\"settings-drawer\" aria-expanded=\"false\">&#9881;</button>
    </div>

    <main id=\"map-wrap\" tabindex=\"-1\" aria-label=\"Helsinki trees map\">
      <div id=\"map\"></div>
      <div class=\"legend\" id=\"legend\"></div>
    </main>
  </div>

  <script src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\" integrity=\"sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=\" crossorigin=\"\"></script>
  <script>
    const DEBUG_LOG_KEY = "helsinkiTreesBetaRuntimeLogV1";
    const debugLog = [];

    function appendLog(level, message, details = null) {{
      const stamp = new Date().toISOString();
      let line = `${{stamp}} [${{level}}] ${{message}}`;
      if (details !== null && details !== undefined) {{
        try {{
          line += ` | ${{JSON.stringify(details)}}`;
        }} catch (_err) {{
          line += ` | ${{String(details)}}`;
        }}
      }}
      debugLog.push(line);
      if (debugLog.length > 800) {{
        debugLog.splice(0, debugLog.length - 800);
      }}
      try {{
        window.localStorage.setItem(DEBUG_LOG_KEY, debugLog.join("\\n"));
      }} catch (_err) {{
        // Ignore storage errors.
      }}
    }}

    function loadPreviousLog() {{
      try {{
        const raw = window.localStorage.getItem(DEBUG_LOG_KEY);
        if (!raw) return;
        const lines = raw.split("\\n").filter(Boolean);
        debugLog.push(...lines.slice(-400));
      }} catch (_err) {{
        // Ignore storage errors.
      }}
    }}

    function showBootError(message) {{
      appendLog("ERROR", "boot_error", {{ message }});
      const statusEl = document.getElementById("status");
      if (statusEl) {{
        statusEl.textContent = `Init error: ${{message}}`;
      }}
      const titleEl = document.getElementById("title");
      if (titleEl && !titleEl.textContent) {{
        titleEl.textContent = "Helsinki Trees (beta)";
      }}
      console.error(message);
    }}

    loadPreviousLog();
    appendLog("INFO", "script_loaded");

    window.addEventListener("error", (event) => {{
      const msg = event && event.message ? event.message : "Unknown runtime error";
      const file = event && event.filename ? event.filename : "";
      const line = event && event.lineno ? String(event.lineno) : "";
      const pos = file ? `${{file}}${{line ? `:${{line}}` : \"\"}}` : "";
      appendLog("ERROR", "window_error", {{ msg, file, line, col: event && event.colno ? event.colno : null }});
      showBootError(pos ? `${{msg}} @ ${{pos}}` : msg);
    }});

    window.addEventListener("unhandledrejection", (event) => {{
      const reason = event && event.reason ? String(event.reason) : "Unhandled promise rejection";
      appendLog("ERROR", "unhandled_rejection", {{ reason }});
      showBootError(reason);
    }});

    const TREE_DATA = {data_json};

    const I18N = {{
      fi: {{
        title: "Helsingin puut (beta)",
        total: "Puut yhteensa: {{count}}",
        updated: "Lahde paivitetty: {{date}}",
        settingsButton: "Asetukset",
        settingsOpen: "Avaa asetukset",
        settingsClose: "Sulje asetukset",
        settingsPanelTitle: "Asetukset",
        settingsLanguage: "Kieli",
        settingsTheme: "Teema",
        settingsThemeSystem: "Jarjestelman mukaan",
        settingsThemeDay: "Paivateema",
        settingsThemeNight: "Yoteema",
        settingsContrast: "Korkea kontrasti",
        settingsExplainerTitle: "Datasta",
        settingsDisclaimerTitle: "Vastuuvapaus",
        settingsDebugTitle: "Diagnostiikka",
        settingsDownloadLog: "Lataa loki",
        settingsClearLog: "Tyhjenna loki",
        explainerCopy: "Katu kuvaa katualueiden puita, Puisto puistoalueiden puita ja Taydennys kohteita, jotka taydentavat rekisteria. Kaikkia Helsingin puita ei ole mukana; esimerkiksi laajat metsaalueet voivat puuttua aineistosta. Rungon paksuusluokka kuvaa kokoa mittaushetkella, ei puun ika-arviota.",
        disclaimerCopy: "Data pohjautuu kaupungin avoimeen aineistoon, mutta tulkinta, suodatus ja esitystapa ovat tekijan omia. Tayttta kattavuutta tai virheettomyytta ei taata. Tyokalua ei tule kayttaa virallisiin, oikeudellisiin tai turvallisuuskriittisiin paatoksiin.",
        introTitle: "Tietoa ennen kartan kayttoa",
        introHideLabel: "Ala nayta tata uudelleen",
        introOpenSettings: "Avaa asetukset",
        introClose: "Jatka karttaan",
        labelType: "Tyyppi",
        labelSpeciesSearch: "Hae lajia",
        speciesSearchPlaceholder: "Kirjoita lajin nimi...",
        labelSpecies: "Laji (suomi)",
        labelGenus: "Suku",
        labelSize: "Rungon paksuusluokka",
        labelYear: "Istutusvuoden aikajana",
        yearReadout: "Nayta kohteet vuoteen {{year}} asti. Tuntemattomat vuodet sisaltyvat aina.",
        yearUnavailable: "Istutusvuosidata puuttuu aikajanaliukuria varten.",
        reset: "Tyhjenna suodattimet",
        all: "Kaikki",
        status: "Nakyvissa: {{count}} / {{total}}",
        statusRendering: "Paivitetaan karttaa...",
        mapHelp: "Vinkki: valitse kohde listalta, jos karttamerkkien klikkaus on vaikeaa.",
        panelShow: "Avaa suodattimet",
        panelHide: "Piilota suodattimet",
        skipControls: "Siirry suodattimiin",
        skipMap: "Siirry karttaan",
        panelAria: "Suodattimet ja tiedot",
        mapToolbarAria: "Kartan painikkeet",
        announceSelected: "Valittu: {{name}}",
        detailsPlaceholder: "Valitse puu kartalta tai listalta",
        detailType: "Tyyppi",
        detailSpecies: "Laji",
        detailScientific: "Tieteellinen",
        detailSize: "Rungon paksuusluokka",
        detailYear: "Istutusvuosi",
        detailLocation: "Sijainti",
        detailCoordinates: "Koordinaatit",
        missing: "Ei tietoa",
        topListTitle: "Esimerkkikohteet (ensimmaiset 30)",
        topListEmpty: "Ei kohteita nykyisilla suodattimilla.",
        qualityNote: "Datalaatuhuomio: istutusvuosi on usein puutteellinen. Epaloogiset vuosiluvut on poistettu. Rungon paksuusluokka on mittaushetken kokotieto, ei ian arvio.",
        legendTitle: "Puun tyyppi",
        typeKatu: "Katu",
        typePuisto: "Puisto",
        typeTaydennys: "Taydennys",
      }},
      en: {{
        title: "Helsinki Trees (beta)",
        total: "Total trees: {{count}}",
        updated: "Source updated: {{date}}",
        settingsButton: "Settings",
        settingsOpen: "Open settings",
        settingsClose: "Close settings",
        settingsPanelTitle: "Settings",
        settingsLanguage: "Language",
        settingsTheme: "Theme",
        settingsThemeSystem: "Follow system",
        settingsThemeDay: "Day mode",
        settingsThemeNight: "Night mode",
        settingsContrast: "High contrast",
        settingsExplainerTitle: "About data",
        settingsDisclaimerTitle: "Disclaimer",
        settingsDebugTitle: "Diagnostics",
        settingsDownloadLog: "Download log",
        settingsClearLog: "Clear log",
        explainerCopy: "Street refers to street trees, Park refers to park trees, and Supplement contains complementary registry records. Not all Helsinki trees are included; for example, large woodland areas may be outside this dataset. Trunk diameter class describes size at measurement time, not a direct age estimate.",
        disclaimerCopy: "While the data comes from official municipal sources, interpretation, filtering and presentation are my own. No guarantee is made for completeness or accuracy, and this tool should not be used for official, legal or safety-critical decisions.",
        introTitle: "Before using the map",
        introHideLabel: "Do not show this again",
        introOpenSettings: "Open settings",
        introClose: "Continue to map",
        labelType: "Type",
        labelSpeciesSearch: "Search species",
        speciesSearchPlaceholder: "Type a species name...",
        labelSpecies: "Species (Finnish)",
        labelGenus: "Genus",
        labelSize: "Trunk diameter class",
        labelYear: "Planting year timeline",
        yearReadout: "Show items up to year {{year}}. Unknown years are always included.",
        yearUnavailable: "No planting-year data available for timeline slider.",
        reset: "Reset filters",
        all: "All",
        status: "Visible: {{count}} / {{total}}",
        statusRendering: "Updating map...",
        mapHelp: "Tip: use the list if selecting map markers is difficult.",
        panelShow: "Open filters",
        panelHide: "Hide filters",
        skipControls: "Skip to filters",
        skipMap: "Skip to map",
        panelAria: "Filters and details",
        mapToolbarAria: "Map controls",
        announceSelected: "Selected: {{name}}",
        detailsPlaceholder: "Select a tree from map or list",
        detailType: "Type",
        detailSpecies: "Species",
        detailScientific: "Scientific",
        detailSize: "Trunk diameter class",
        detailYear: "Planting year",
        detailLocation: "Location",
        detailCoordinates: "Coordinates",
        missing: "Not available",
        topListTitle: "Sample locations (first 30)",
        topListEmpty: "No rows with current filters.",
        qualityNote: "Data quality note: planting year is frequently missing. Implausible years are removed. Trunk diameter class is a snapshot size field, not a direct age estimate.",
        legendTitle: "Tree type",
        typeKatu: "Street",
        typePuisto: "Park",
        typeTaydennys: "Supplement",
      }},
    }};

    const TYPE_COLORS = {{
      Katu: "#1f5eff",
      Puisto: "#1ea85f",
      "Taydennys": "#d97706",
      "Täydennys": "#d97706",
      default: "#5f6f88"
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
    const plantingYears = rows
      .map((row) => Number(row[7]))
      .filter((year) => Number.isInteger(year) && year > 1000);
    const yearRange = plantingYears.length > 0
      ? {{ min: Math.min(...plantingYears), max: Math.max(...plantingYears) }}
      : null;

    const STORAGE_KEY = "helsinkiTreesBetaPrefsV1";
    const defaultLang = (navigator.language || "").toLowerCase().startsWith("fi") ? "fi" : "en";
    const matchMediaSafe = (query) => {{
      if (typeof window.matchMedia === "function") {{
        return window.matchMedia(query);
      }}
      return {{
        matches: false,
        addEventListener: null,
        removeEventListener: null,
        addListener: null,
        removeListener: null,
      }};
    }};
    const prefersDark = matchMediaSafe("(prefers-color-scheme: dark)");
    const mobileQuery = matchMediaSafe("(max-width: 1100px)");

    function readPrefs() {{
      try {{
        const raw = window.localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : {{}};
      }} catch (_err) {{
        return {{}};
      }}
    }}

    function writePrefs(nextPrefs) {{
      try {{
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextPrefs));
      }} catch (_err) {{
        // Ignore storage errors.
      }}
    }}

    const savedPrefs = readPrefs();
    let lang = (savedPrefs.lang === "fi" || savedPrefs.lang === "en") ? savedPrefs.lang : defaultLang;

    const state = {{
      visibleRows: [],
      hasFitBounds: false,
      selectedRow: null,
      panelCollapsed: false,
      settingsOpen: false,
      renderToken: 0,
      speciesSearch: "",
      yearCutoff: yearRange ? yearRange.max : null,
      themeMode: (savedPrefs.theme === "day" || savedPrefs.theme === "night" || savedPrefs.theme === "system") ? savedPrefs.theme : "system",
      contrastHigh: Boolean(savedPrefs.contrastHigh),
      hideIntro: Boolean(savedPrefs.hideIntro),
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

    const lightTileLayer = L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }});

    const nightTileLayer = L.tileLayer("https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png", {{
      maxZoom: 19,
      subdomains: "abcd",
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    }});

    let activeTileLayer = null;

    let clusterLayer = null;
    const speciesSearchCache = new Map();

    const dom = {{
      title: document.getElementById("title"),
      metaTotal: document.getElementById("meta-total"),
      metaUpdated: document.getElementById("meta-updated"),
      labelType: document.getElementById("label-type"),
      labelSpeciesSearch: document.getElementById("label-species-search"),
      labelSpecies: document.getElementById("label-species"),
      labelGenus: document.getElementById("label-genus"),
      labelSize: document.getElementById("label-size"),
      labelYear: document.getElementById("label-year"),
      btnReset: document.getElementById("btn-reset"),
      status: document.getElementById("status"),
      mapHelp: document.getElementById("map-help"),
      filterSpeciesSearch: document.getElementById("filter-species-search"),
      filterYear: document.getElementById("filter-year"),
      yearReadout: document.getElementById("year-readout"),
      detailTitle: document.getElementById("detail-title"),
      detailGrid: document.getElementById("detail-grid"),
      qualityNote: document.getElementById("quality-note"),
      topListTitle: document.getElementById("top-list-title"),
      topList: document.getElementById("top-list"),
      legend: document.getElementById("legend"),
      settingsBtn: document.getElementById("settings-btn"),
      settingsDrawer: document.getElementById("settings-drawer"),
      settingsDrawerTitle: document.getElementById("settings-drawer-title"),
      settingsScrim: document.getElementById("settings-scrim"),
      mapToolbar: document.getElementById("map-toolbar"),
      settingsLanguageLabel: document.getElementById("settings-language-label"),
      settingsThemeLabel: document.getElementById("settings-theme-label"),
      settingsLanguage: document.getElementById("settings-language"),
      settingsTheme: document.getElementById("settings-theme"),
      settingsContrast: document.getElementById("settings-contrast"),
      settingsContrastLabel: document.getElementById("settings-contrast-label"),
      settingsExplainerTitle: document.getElementById("settings-explainer-title"),
      settingsExplainerCopy: document.getElementById("settings-explainer-copy"),
      settingsDisclaimerTitle: document.getElementById("settings-disclaimer-title"),
      settingsDisclaimerCopy: document.getElementById("settings-disclaimer-copy"),
      settingsDebugTitle: document.getElementById("settings-debug-title"),
      settingsDownloadLog: document.getElementById("settings-download-log"),
      settingsClearLog: document.getElementById("settings-clear-log"),
      panel: document.getElementById("control-panel"),
      panelToggle: document.getElementById("panel-toggle"),
      skipControls: document.getElementById("skip-controls"),
      skipMap: document.getElementById("skip-map"),
      srAnnouncer: document.getElementById("sr-announcer"),
      mapWrap: document.getElementById("map-wrap"),
      introModal: document.getElementById("intro-modal"),
      introTitle: document.getElementById("intro-title"),
      introExplainer: document.getElementById("intro-explainer"),
      introDisclaimer: document.getElementById("intro-disclaimer"),
      introHideNext: document.getElementById("intro-hide-next"),
      introHideLabel: document.getElementById("intro-hide-label"),
      introOpenSettings: document.getElementById("intro-open-settings"),
      introClose: document.getElementById("intro-close"),
    }};

    let settingsFocusReturn = null;
    let introFocusReturn = null;

    function t(key) {{
      return I18N[lang][key] || key;
    }}

    function format(msg, vars) {{
      return Object.entries(vars).reduce(
        (out, [key, value]) => out.replace(`{{${{key}}}}`, String(value)),
        msg
      );
    }}

    function announce(message) {{
      dom.srAnnouncer.textContent = "";
      window.setTimeout(() => {{
        dom.srAnnouncer.textContent = message;
      }}, 10);
    }}

    function getFocusableElements(container) {{
      if (!container) return [];
      return [...container.querySelectorAll(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )].filter((el) => !el.hasAttribute("hidden") && el.getAttribute("aria-hidden") !== "true");
    }}

    function focusFirstElement(container, fallbackEl = null) {{
      const focusable = getFocusableElements(container);
      if (focusable.length > 0) {{
        focusable[0].focus();
        return;
      }}
      if (fallbackEl && typeof fallbackEl.focus === "function") {{
        fallbackEl.focus();
      }}
    }}

    function trapFocusInside(event, container) {{
      if (event.key !== "Tab") return false;
      const focusable = getFocusableElements(container);
      if (focusable.length === 0) return false;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;

      if (event.shiftKey && active === first) {{
        event.preventDefault();
        last.focus();
        return true;
      }}
      if (!event.shiftKey && active === last) {{
        event.preventDefault();
        first.focus();
        return true;
      }}
      return false;
    }}

    function syncPanelState() {{
      if (!dom.panel || !dom.panelToggle) return;
      dom.panel.classList.toggle("is-collapsed", state.panelCollapsed);
      dom.panelToggle.setAttribute("aria-expanded", String(!state.panelCollapsed));
      const label = state.panelCollapsed ? t("panelShow") : t("panelHide");
      dom.panelToggle.setAttribute("aria-label", label);
      dom.panelToggle.setAttribute("title", label);
      dom.panelToggle.classList.toggle("active", !state.panelCollapsed);
      dom.panel.setAttribute("aria-hidden", String(state.panelCollapsed));
    }}

    function persistPrefs() {{
      writePrefs({{
        lang,
        theme: state.themeMode,
        contrastHigh: state.contrastHigh,
        hideIntro: state.hideIntro,
      }});
    }}

    function resolveTheme() {{
      if (state.themeMode === "system") {{
        return prefersDark.matches ? "night" : "day";
      }}
      return state.themeMode;
    }}

    function applyTheme() {{
      const resolved = resolveTheme();
      document.documentElement.setAttribute("data-theme", resolved);
      document.documentElement.setAttribute("data-contrast", state.contrastHigh ? "high" : "normal");

      const targetLayer = resolved === "night" ? nightTileLayer : lightTileLayer;
      if (activeTileLayer !== targetLayer) {{
        if (activeTileLayer && map.hasLayer(activeTileLayer)) {{
          map.removeLayer(activeTileLayer);
        }}
        if (targetLayer) {{
          targetLayer.addTo(map);
        }}
        activeTileLayer = targetLayer;
      }}
    }}

    function syncYearFilterUi() {{
      if (!dom.filterYear || !dom.yearReadout || !dom.labelYear) return;
      dom.labelYear.textContent = t("labelYear");

      if (!yearRange) {{
        dom.filterYear.disabled = true;
        dom.filterYear.value = "0";
        dom.filterYear.setAttribute("aria-label", t("yearUnavailable"));
        dom.yearReadout.textContent = t("yearUnavailable");
        return;
      }}

      if (!Number.isInteger(state.yearCutoff)) {{
        state.yearCutoff = yearRange.max;
      }}
      if (state.yearCutoff < yearRange.min) state.yearCutoff = yearRange.min;
      if (state.yearCutoff > yearRange.max) state.yearCutoff = yearRange.max;

      dom.filterYear.disabled = false;
      dom.filterYear.min = String(yearRange.min);
      dom.filterYear.max = String(yearRange.max);
      dom.filterYear.step = "1";
      dom.filterYear.value = String(state.yearCutoff);
      dom.filterYear.setAttribute("aria-label", t("labelYear"));
      dom.filterYear.setAttribute("aria-valuemin", String(yearRange.min));
      dom.filterYear.setAttribute("aria-valuemax", String(yearRange.max));
      dom.filterYear.setAttribute("aria-valuenow", String(state.yearCutoff));
      dom.filterYear.setAttribute("aria-valuetext", String(state.yearCutoff));
      dom.yearReadout.textContent = format(t("yearReadout"), {{ year: state.yearCutoff }});
    }}

    function syncSettingsDrawerState() {{
      if (!dom.settingsDrawer || !dom.settingsBtn) return;
      const wasOpen = dom.settingsDrawer.classList.contains("open");
      dom.settingsDrawer.classList.toggle("open", state.settingsOpen);
      dom.settingsDrawer.setAttribute("aria-hidden", String(!state.settingsOpen));
      if (dom.settingsScrim) {{
        dom.settingsScrim.classList.toggle("open", state.settingsOpen);
        dom.settingsScrim.setAttribute("aria-hidden", String(!state.settingsOpen));
      }}
      dom.settingsBtn.setAttribute("aria-expanded", String(state.settingsOpen));
      const label = state.settingsOpen ? t("settingsClose") : t("settingsOpen");
      dom.settingsBtn.setAttribute("aria-label", label);
      dom.settingsBtn.setAttribute("title", label);
      if (dom.settingsScrim) {{
        dom.settingsScrim.setAttribute("aria-label", label);
      }}
      dom.settingsBtn.classList.toggle("active", state.settingsOpen);

      if (state.settingsOpen && !wasOpen) {{
        if (!settingsFocusReturn && document.activeElement instanceof HTMLElement) {{
          settingsFocusReturn = document.activeElement;
        }}
        window.setTimeout(() => focusFirstElement(dom.settingsDrawer, dom.settingsBtn), 0);
      }} else if (!state.settingsOpen && wasOpen && settingsFocusReturn && typeof settingsFocusReturn.focus === "function") {{
        settingsFocusReturn.focus();
        settingsFocusReturn = null;
      }}
      if (!state.settingsOpen && !wasOpen) {{
        settingsFocusReturn = null;
      }}
    }}

    function syncSettingsControls() {{
      if (dom.settingsLanguage) dom.settingsLanguage.value = lang;
      if (dom.settingsTheme) dom.settingsTheme.value = state.themeMode;
      if (dom.settingsContrast) dom.settingsContrast.checked = state.contrastHigh;
    }}

    function showIntroModal() {{
      if (!dom.introModal || !dom.introHideNext) return;
      if (state.hideIntro) {{
        dom.introModal.classList.remove("open");
        return;
      }}
      if (!introFocusReturn && document.activeElement instanceof HTMLElement) {{
        introFocusReturn = document.activeElement;
      }}
      dom.introHideNext.checked = false;
      dom.introModal.classList.add("open");
      window.setTimeout(() => focusFirstElement(dom.introModal, dom.introClose), 0);
    }}

    function closeIntroModal() {{
      if (!dom.introModal || !dom.introHideNext) return;
      state.hideIntro = Boolean(dom.introHideNext.checked);
      persistPrefs();
      dom.introModal.classList.remove("open");
      if (introFocusReturn && typeof introFocusReturn.focus === "function") {{
        introFocusReturn.focus();
      }}
      introFocusReturn = null;
    }}

    function downloadDebugLog() {{
      const body = debugLog.join("\\n");
      const blob = new Blob([body || "No log entries"], {{ type: "text/plain;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `helsinki_trees_debug_${{Date.now()}}.log`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    }}

    function buildPointLayer() {{
      if (typeof L.markerClusterGroup === "function") {{
        try {{
          return L.markerClusterGroup({{
            chunkedLoading: true,
            chunkInterval: 120,
            chunkDelay: 20,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            disableClusteringAtZoom: 17,
            maxClusterRadius: 45,
          }});
        }} catch (err) {{
          const message = (err && err.message) ? err.message : "marker cluster init failed";
          showBootError(`Cluster disabled: ${{message}}`);
        }}
      }}
      return L.layerGroup();
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

    function normalizeSearch(value) {{
      return (value || "")
        .toString()
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\\u0300-\\u036f]/g, "")
        .trim();
    }}

    function speciesSearchText(row) {{
      let cached = speciesSearchCache.get(row);
      if (cached) return cached;
      cached = normalizeSearch([row[3], row[4], row[5]].filter(Boolean).join(" "));
      speciesSearchCache.set(row, cached);
      return cached;
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
      document.documentElement.setAttribute("lang", lang);
      dom.title.textContent = t("title");
      dom.labelType.textContent = t("labelType");
      dom.labelSpeciesSearch.textContent = t("labelSpeciesSearch");
      dom.labelSpecies.textContent = t("labelSpecies");
      dom.labelGenus.textContent = t("labelGenus");
      dom.labelSize.textContent = t("labelSize");
      dom.labelYear.textContent = t("labelYear");
      dom.btnReset.textContent = t("reset");
      dom.mapHelp.textContent = t("mapHelp");
      dom.qualityNote.textContent = t("qualityNote");
      dom.topListTitle.textContent = t("topListTitle");
      dom.skipControls.textContent = t("skipControls");
      dom.skipMap.textContent = t("skipMap");
      dom.settingsDrawerTitle.textContent = t("settingsPanelTitle");
      dom.panel.setAttribute("aria-label", t("panelAria"));
      if (dom.mapToolbar) dom.mapToolbar.setAttribute("aria-label", t("mapToolbarAria"));
      dom.mapWrap.setAttribute("aria-label", t("title"));
      document.getElementById("filter-type").setAttribute("aria-label", t("labelType"));
      dom.filterSpeciesSearch.setAttribute("aria-label", t("labelSpeciesSearch"));
      dom.filterSpeciesSearch.setAttribute("placeholder", t("speciesSearchPlaceholder"));
      document.getElementById("filter-species").setAttribute("aria-label", t("labelSpecies"));
      document.getElementById("filter-genus").setAttribute("aria-label", t("labelGenus"));
      document.getElementById("filter-size").setAttribute("aria-label", t("labelSize"));
      if (dom.filterYear) dom.filterYear.setAttribute("aria-label", t("labelYear"));
      dom.settingsLanguageLabel.textContent = t("settingsLanguage");
      dom.settingsThemeLabel.textContent = t("settingsTheme");
      if (dom.settingsTheme && dom.settingsTheme.options.length >= 3) {{
        dom.settingsTheme.options[0].textContent = t("settingsThemeSystem");
        dom.settingsTheme.options[1].textContent = t("settingsThemeDay");
        dom.settingsTheme.options[2].textContent = t("settingsThemeNight");
      }}
      dom.settingsContrastLabel.textContent = t("settingsContrast");
      dom.settingsExplainerTitle.textContent = t("settingsExplainerTitle");
      dom.settingsExplainerCopy.textContent = t("explainerCopy");
      dom.settingsDisclaimerTitle.textContent = t("settingsDisclaimerTitle");
      dom.settingsDisclaimerCopy.textContent = t("disclaimerCopy");
      dom.settingsDebugTitle.textContent = t("settingsDebugTitle");
      dom.settingsDownloadLog.textContent = t("settingsDownloadLog");
      dom.settingsClearLog.textContent = t("settingsClearLog");
      dom.introTitle.textContent = t("introTitle");
      dom.introExplainer.textContent = t("explainerCopy");
      dom.introDisclaimer.textContent = t("disclaimerCopy");
      dom.introHideLabel.textContent = t("introHideLabel");
      dom.introOpenSettings.textContent = t("introOpenSettings");
      dom.introClose.textContent = t("introClose");

      const updatedDates = (meta.source_updated_dates || []).join(", ") || t("missing");
      dom.metaTotal.textContent = format(t("total"), {{ count: Number(meta.clean_rows).toLocaleString() }});
      dom.metaUpdated.textContent = format(t("updated"), {{ date: updatedDates }});

      dom.legend.innerHTML = `
        <div><strong>${{t("legendTitle")}}</strong></div>
        <div class=\"legend-row\"><span class=\"swatch\" style=\"background:${{TYPE_COLORS.Katu}}\"></span>${{t("typeKatu")}}</div>
        <div class=\"legend-row\"><span class=\"swatch\" style=\"background:${{TYPE_COLORS.Puisto}}\"></span>${{t("typePuisto")}}</div>
        <div class=\"legend-row\"><span class=\"swatch\" style=\"background:${{TYPE_COLORS["Täydennys"]}}\"></span>${{t("typeTaydennys")}}</div>
      `;

      syncSettingsControls();
      syncSettingsDrawerState();
      syncPanelState();
      syncYearFilterUi();

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
      if (yearRange && Number.isInteger(state.yearCutoff)) {{
        const plantingYear = Number(row[7]);
        if (Number.isInteger(plantingYear) && plantingYear > state.yearCutoff) return false;
      }}
      if (state.speciesSearch && !speciesSearchText(row).includes(state.speciesSearch)) return false;
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
      announce(format(t("announceSelected"), {{ name: location }}));
    }}

    function renderTopList() {{
      dom.topList.innerHTML = "";
      if (state.visibleRows.length === 0) {{
        const li = document.createElement("li");
        li.textContent = t("topListEmpty");
        li.style.padding = "8px 10px";
        li.style.color = "var(--muted)";
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

    function buildMarkersAsync(rowsToRender, token) {{
      const markers = [];
      const chunkSize = 1200;
      let index = 0;

      return new Promise((resolve) => {{
        const runChunk = () => {{
          if (token !== state.renderToken) {{
            resolve([]);
            return;
          }}

          const end = Math.min(index + chunkSize, rowsToRender.length);
          for (; index < end; index += 1) {{
            const row = rowsToRender[index];
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

          if (index < rowsToRender.length) {{
            const pct = Math.round((index / rowsToRender.length) * 100);
            dom.status.textContent = `${{t("statusRendering")}} (${{pct}}%)`;
            window.setTimeout(runChunk, 0);
            return;
          }}
          resolve(markers);
        }};
        runChunk();
      }});
    }}

    function addMarkersToPointLayer(markers) {{
      if (!clusterLayer || !markers || markers.length === 0) return;
      if (typeof clusterLayer.addLayers === "function") {{
        clusterLayer.addLayers(markers);
        return;
      }}
      for (const marker of markers) {{
        clusterLayer.addLayer(marker);
      }}
    }}

    function applyFiltersAndRender() {{
      if (!clusterLayer) return;
      state.renderToken += 1;
      const token = state.renderToken;
      updateStatus(true);
      window.requestAnimationFrame(() => {{
        const nextVisibleRows = rows.filter(rowMatches);
        state.visibleRows = nextVisibleRows;
        renderTopList();

        clusterLayer.clearLayers();
        buildMarkersAsync(nextVisibleRows, token).then((markers) => {{
          if (token !== state.renderToken) return;
          addMarkersToPointLayer(markers);

          if (!state.hasFitBounds && state.visibleRows.length > 0) {{
            const bounds = L.latLngBounds(state.visibleRows.map((row) => [row[0], row[1]]));
            map.fitBounds(bounds.pad(0.05));
            state.hasFitBounds = true;
          }}

          if (state.selectedRow && !rowMatches(state.selectedRow)) {{
            showDetails(null);
          }}

          updateStatus(false);
        }});
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
        state.speciesSearch = "";
        if (dom.filterSpeciesSearch) {{
          dom.filterSpeciesSearch.value = "";
        }}
        if (yearRange) {{
          state.yearCutoff = yearRange.max;
          syncYearFilterUi();
        }}
        state.filterValues = {{
          paatyyppi: "",
          suomenknimi: "",
          suku: "",
          kokoluokka: "",
        }};
        fillFilters();
        applyFiltersAndRender();
      }});

      if (dom.filterSpeciesSearch) {{
        dom.filterSpeciesSearch.addEventListener("input", (event) => {{
          state.speciesSearch = normalizeSearch(event.target.value);
          applyFiltersAndRender();
        }});
      }}

      if (dom.filterYear) {{
        dom.filterYear.addEventListener("input", (event) => {{
          state.yearCutoff = Number(event.target.value);
          syncYearFilterUi();
        }});
        dom.filterYear.addEventListener("change", (event) => {{
          state.yearCutoff = Number(event.target.value);
          syncYearFilterUi();
          applyFiltersAndRender();
        }});
      }}

      if (dom.settingsBtn) {{
        dom.settingsBtn.addEventListener("click", () => {{
          state.settingsOpen = !state.settingsOpen;
          syncSettingsDrawerState();
        }});
      }}

      if (dom.settingsLanguage) {{
        dom.settingsLanguage.addEventListener("change", (event) => {{
          lang = event.target.value === "en" ? "en" : "fi";
          appendLog("INFO", "settings_language_change", {{ lang }});
          persistPrefs();
          updateStaticTexts();
        }});
      }}

      if (dom.settingsTheme) {{
        dom.settingsTheme.addEventListener("change", (event) => {{
          const nextTheme = event.target.value;
          state.themeMode = (nextTheme === "day" || nextTheme === "night" || nextTheme === "system") ? nextTheme : "system";
          appendLog("INFO", "settings_theme_change", {{ themeMode: state.themeMode }});
          applyTheme();
          persistPrefs();
        }});
      }}

      if (dom.settingsContrast) {{
        dom.settingsContrast.addEventListener("change", (event) => {{
          state.contrastHigh = Boolean(event.target.checked);
          appendLog("INFO", "settings_contrast_change", {{ contrastHigh: state.contrastHigh }});
          applyTheme();
          persistPrefs();
        }});
      }}

      if (dom.settingsDownloadLog) {{
        dom.settingsDownloadLog.addEventListener("click", () => {{
          appendLog("INFO", "download_log_clicked");
          downloadDebugLog();
        }});
      }}

      if (dom.settingsClearLog) {{
        dom.settingsClearLog.addEventListener("click", () => {{
          debugLog.length = 0;
          appendLog("INFO", "log_cleared");
        }});
      }}

      if (dom.settingsScrim) {{
        dom.settingsScrim.addEventListener("click", () => {{
          state.settingsOpen = false;
          syncSettingsDrawerState();
        }});
      }}

      if (dom.introOpenSettings) {{
        dom.introOpenSettings.addEventListener("click", () => {{
          state.settingsOpen = true;
          syncSettingsDrawerState();
          closeIntroModal();
        }});
      }}

      if (dom.introClose) {{
        dom.introClose.addEventListener("click", () => {{
          closeIntroModal();
        }});
      }}

      if (dom.introModal) {{
        dom.introModal.addEventListener("click", (event) => {{
          if (event.target === dom.introModal) {{
            closeIntroModal();
          }}
        }});
      }}

      dom.panelToggle.addEventListener("click", () => {{
        state.panelCollapsed = !state.panelCollapsed;
        syncPanelState();
        window.setTimeout(() => map.invalidateSize(), 120);
      }});

      document.addEventListener("click", (event) => {{
        if (!state.settingsOpen) return;
        const target = event.target;
        if (dom.settingsDrawer && dom.settingsDrawer.contains(target)) return;
        if (dom.settingsBtn && dom.settingsBtn.contains(target)) return;
        if (dom.settingsScrim && dom.settingsScrim.contains(target)) return;
        state.settingsOpen = false;
        syncSettingsDrawerState();
      }});

      const handleMediaChange = (event) => {{
        state.panelCollapsed = event.matches;
        syncPanelState();
        map.invalidateSize();
      }};
      if (mobileQuery.addEventListener) {{
        mobileQuery.addEventListener("change", handleMediaChange);
      }} else if (mobileQuery.addListener) {{
        mobileQuery.addListener(handleMediaChange);
      }}

      const handleThemeMediaChange = () => {{
        if (state.themeMode === "system") {{
          applyTheme();
        }}
      }};
      if (prefersDark.addEventListener) {{
        prefersDark.addEventListener("change", handleThemeMediaChange);
      }} else if (prefersDark.addListener) {{
        prefersDark.addListener(handleThemeMediaChange);
      }}

      document.addEventListener("keydown", (event) => {{
        if (dom.introModal.classList.contains("open") && trapFocusInside(event, dom.introModal)) {{
          return;
        }}
        if (state.settingsOpen && trapFocusInside(event, dom.settingsDrawer)) {{
          return;
        }}
        if (event.key === "Escape" && dom.introModal.classList.contains("open")) {{
          closeIntroModal();
          return;
        }}
        if (event.key === "Escape" && state.settingsOpen) {{
          state.settingsOpen = false;
          syncSettingsDrawerState();
          return;
        }}
        if (event.key === "Escape" && mobileQuery.matches && !state.panelCollapsed) {{
          state.panelCollapsed = true;
          syncPanelState();
        }}
      }});
    }}

    function boot() {{
      try {{
        appendLog("INFO", "boot_start");
        state.panelCollapsed = mobileQuery.matches;
        state.settingsOpen = false;
        appendLog("INFO", "state_initialized", {{ panelCollapsed: state.panelCollapsed }});
        clusterLayer = buildPointLayer();
        appendLog("INFO", "point_layer_ready", {{ clustered: typeof L.markerClusterGroup === "function" }});
        clusterLayer.addTo(map);
        appendLog("INFO", "point_layer_added");
        applyTheme();
        appendLog("INFO", "theme_applied", {{ theme: resolveTheme(), mode: state.themeMode }});
        syncPanelState();
        appendLog("INFO", "panel_state_synced");
        setupEvents();
        appendLog("INFO", "events_bound");
        updateStaticTexts();
        appendLog("INFO", "texts_updated", {{ lang }});
        showDetails(null);
        appendLog("INFO", "details_placeholder_set");
        applyFiltersAndRender();
        appendLog("INFO", "first_render_triggered");
        showIntroModal();
        appendLog("INFO", "intro_checked", {{ hideIntro: state.hideIntro }});
      }} catch (err) {{
        console.error(err);
        if (dom.status) {{
          const message = (err && err.message) ? err.message : String(err);
          dom.status.textContent = `Init error: ${{message}}`;
        }}
      }}
    }}

    boot();
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
