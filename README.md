# Ice Cream World

Worldwide ice cream trade, 2010–2023: FAOSTAT into BigQuery, tested dbt marts, Looker Studio dashboard.

**Dashboard (unlisted):** [Scoop the globe](https://lookerstudio.google.com/reporting/b86678c3-10a7-49b9-bf9f-963c5eaec576)

```text
FAO bulk zip
    →  Python load job
    →  BigQuery raw.ice_cream_sua, raw.population
    →  dbt views and tables in analytics
    →  Looker Studio
```

## Snapshot

FAO item **910** is “Ice cream and other edible ice” in the Supply Utilization Accounts. After dropping World and the China aggregate, the warehouse holds **178 countries**.

With the current extract (latest year **2023**):

| Measure | Value |
| --- | --- |
| Imports | ~1.62 million tonnes |
| Exports | ~1.59 million tonnes |
| Largest exporter | Germany, ~201,188 tonnes |

Imports and exports are the complete series. Production is sparse (58 country rows across all years) and often repeated on regional FAO rows, so the dashboard does not sum it. Food-supply kilograms per person are on the mart but a **zero is not consumption** — FAO often balances the account without production (37 countries in 2022, including Germany, France, and Belgium).

## Stack

- **Ingest:** Python, FAOSTAT bulk files (Zenodo, then `bulks-faostat.fao.org`)
- **Warehouse:** BigQuery sandbox (`CREATE OR REPLACE` / load jobs; no `MERGE`)
- **Transform:** dbt (`stg` → `int` → `mart`)
- **BI:** Looker Studio on the marts only

## Setup

1. Create a [BigQuery](https://console.cloud.google.com/bigquery) project. The sandbox needs no billing account. Tables expire after 60 days.
2. Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) and sign in:

   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   export GCP_PROJECT=YOUR_PROJECT_ID
   ```

3. Install Python deps:

   ```bash
   uv venv .venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

4. Copy the dbt profile (`dbt/profiles.yml` is gitignored):

   ```bash
   cp dbt/profiles.yml.example dbt/profiles.yml
   ```

   Loader and profile both use location `US`. Override with `BQ_LOCATION` if the dataset is elsewhere.

## Run

```bash
python ingest/load_faostat.py --project "$GCP_PROJECT"
cd dbt && dbt build
```

The loader writes `data/processed/*.csv` and replaces `raw.ice_cream_sua` and `raw.population`. Omit `--project` to stop after the local CSVs.

`dbt build` loads `dbt/seeds/fao_area_iso3.csv`, builds the models, and runs tests.

| Layer | Model | Grain |
| --- | --- | --- |
| Staging | `stg_ice_cream` | area, year, measure |
| Staging | `stg_population` | area, year |
| Intermediate | `int_ice_cream_country_year` | country, year (pivoted; trade balance = exports − imports) |
| Mart | `mart_ice_cream_country_year` | country, year + ranks and YoY |
| Mart | `mart_ice_cream_latest` | country, newest year only |

World (area 5000) and the China aggregate (351) stay in raw/staging and are excluded from the marts (`is_country` on the seed).

If `dbt build` fails, do not point Looker at the mart. Tests cover grain uniqueness, non-negative tonnes, aggregate exclusion, and ISO3 on every map row.

## Dashboard

Looker reads two tables:

- `mart_ice_cream_latest` — KPIs, map, top exporters, highlight, trade table
- `mart_ice_cream_country_year` — Germany imports vs exports over time

KPI scorecards must use **latest**, not the year table (that would sum 2010–2023). Set `iso3` to Geo → Country code. Rebuild notes are in [dashboard/looker_studio.md](dashboard/looker_studio.md).

## Layout

```text
ice-cream-world/
├── ingest/load_faostat.py      # FAO zip → CSV + BigQuery raw
├── ingest/reference/iso3166.csv
├── dbt/models/staging/
├── dbt/models/intermediate/
├── dbt/models/marts/
├── dbt/seeds/fao_area_iso3.csv
├── dbt/tests/
└── dashboard/looker_studio.md
```

## Limits

No scheduler, no incremental models (`MERGE` is blocked in the sandbox), no second environment.

## Source

FAOSTAT Supply Utilization Accounts and population, item 910 / element 511. FAO data is used under FAO’s statistical terms; this repo does not republish the bulk files.
