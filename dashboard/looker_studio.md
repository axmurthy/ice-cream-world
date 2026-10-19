# Looker Studio dashboard

Live report (unlisted, Viewer): https://lookerstudio.google.com/reporting/b86678c3-10a7-49b9-bf9f-963c5eaec576

Charts read the marts only — never `raw` or the FAO zip.

| Table | Used for |
| --- | --- |
| `mart_ice_cream_latest` | KPIs, map, top exporters, highlight table, trade table |
| `mart_ice_cream_country_year` | Line chart over time |

`mart_ice_cream_latest` is one row per country for the newest year (2023 in the current extract). KPI scorecards on `mart_ice_cream_country_year` will sum every year.

## Data sources

1. [Looker Studio](https://lookerstudio.google.com/) → **Create** → **Data source**.
2. BigQuery connector → project → `analytics` → `mart_ice_cream_latest` → **Connect**.
3. Set `iso3` to **Geo** → **Country code**. Leave `area_name` as text (`Viet Nam`, `China, mainland` do not always match Google’s country list).
4. **Create report**.
5. **Resource** → **Manage added data sources** → add `mart_ice_cream_country_year` the same way, including the `iso3` geo type.

Do not use **Resource → Manage field names and IDs** (Field overrides). Those can break the editor. Rename on the chart: Setup tab, field chip, **Display name**. Chart titles: Style → Show title + Hide field name, then Enter.

## Theme

**File → Theme and layout → Customize.** Do not click a preset after customizing; that resets the palette.

| Token | Value |
| --- | --- |
| Theme | Custom |
| Page | 1200 × 1100 |
| Background | vanilla `#FFECB3` |
| Primary font | Quicksand, dark berry `#880E4F` |
| Chart titles | berry `#AD1457` |
| Palette | strawberry `#F06292`, mint `#81C784` |
| Cards | white, radius 16, shadow on |
| Share | Unlisted, Viewer |

## Charts

1. **Header** — text `Scoop the globe`, 28px bold, no card shadow.
2. **KPIs** on `mart_ice_cream_latest`, compact numbers, comparison **None**, labels ~28px:
   - **Imports** — `import_tonnes` Sum (~1.6M)
   - **Exports** — `export_tonnes` Sum (~1.6M)
   - **Year** — `year` Max (2023)
3. **Highlight** — one-row table for Germany (~201,188 export tonnes). Display names: Country / Exports / Imports.
4. **Top exporters** — horizontal bar, `area_name` × `export_tonnes`, Top N 10, Others off, legend off, data labels on.
5. **Map** — geo, `iso3` × `import_tonnes`, World. Title: Imports by country.
6. **Germany over time** — line on `mart_ice_cream_country_year`, filter `area_name` = Germany. Exports stay above imports.
7. **Trade table** — country, imports, exports, trade balance, sort imports descending, compact numbers, grand-total row (~1.6M / 1.6M / +15k). Positive balance is a net exporter. The United Kingdom is a large net importer.
8. **Footnote** — Source: FAOSTAT SUA item 910. Values in tonnes. World and China aggregates excluded. Production omitted (sparse coverage).

If scorecards are far from 1.62M / 1.59M, the data source is probably the year table or World was left in the mart.

## Fields left off the report

They stay on the mart so the source gaps are visible.

- `production_tonnes` is null for most countries. Summing it double-counts regional FAO rows.
- `kg_per_person_year` is FAO grams/person/day × 365 / 1000. Treat zero as “FAO did not balance this account,” especially when `food_supply_estimated_zero` is true.
- `import_tonnes_yoy` / `export_tonnes_yoy` are null in 2010.
- A country dropdown on `mart_ice_cream_country_year` can drive the line chart.
