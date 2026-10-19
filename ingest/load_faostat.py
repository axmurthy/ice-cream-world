"""Load worldwide ice cream rows from FAO into local CSVs and BigQuery.

The local CSVs keep FAO's column names. BigQuery cannot store parentheses in
field names, so the load job maps "Area Code (M49)" to Area_Code_M49.
Renaming for analytics, country filters, and dashboard metrics happen in dbt.

FAO publishes item 910, "Ice cream and other edible ice", in the Supply
Utilization Accounts. Population is a separate FAO file that uses the same
area codes, so the mart can join on a code instead of a country name.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import zipfile
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
SEED_PATH = ROOT / "dbt" / "seeds" / "fao_area_iso3.csv"
ISO_PATH = ROOT / "ingest" / "reference" / "iso3166.csv"

ICE_CREAM_ITEM = "910"
POPULATION_ELEMENT = "511"
CHINA_AGGREGATE_AREA = 351

SUA_ZIP = "SUA_Crops_Livestock_E_All_Data_(Normalized).zip"
POPULATION_ZIP = "Population_E_All_Data_(Normalized).zip"
SUA_CSV = "SUA_Crops_Livestock_E_All_Data_(Normalized).csv"
POPULATION_CSV = "Population_E_All_Data_(Normalized).csv"
AREA_CSV = "SUA_Crops_Livestock_E_AreaCodes.csv"

DOWNLOADS = {
    SUA_ZIP: [
        f"https://zenodo.org/records/11602356/files/{SUA_ZIP}?download=1",
        f"https://bulks-faostat.fao.org/production/{SUA_ZIP}",
    ],
    POPULATION_ZIP: [
        f"https://zenodo.org/records/11602356/files/{POPULATION_ZIP}?download=1",
        f"https://bulks-faostat.fao.org/production/{POPULATION_ZIP}",
    ],
}

ICE_CREAM_FIELDS = [
    "Area Code",
    "Area Code (M49)",
    "Area",
    "Item Code",
    "Item Code (CPC)",
    "Item",
    "Element Code",
    "Element",
    "Year Code",
    "Year",
    "Unit",
    "Value",
    "Flag",
    "Note",
]
POPULATION_FIELDS = [
    "Area Code",
    "Area Code (M49)",
    "Area",
    "Item Code",
    "Item",
    "Element Code",
    "Element",
    "Year Code",
    "Year",
    "Unit",
    "Value",
    "Flag",
    "Note",
]


def download(name: str, destination: Path) -> None:
    if destination.exists() and destination.stat().st_size > 0:
        print(f"Using existing file {destination.name}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error = None
    for url in DOWNLOADS[name]:
        print(f"Downloading {url}")
        request = Request(url, headers={"User-Agent": "ice-cream-world-lesson"})
        try:
            with urlopen(request, timeout=120) as response, destination.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
            return
        except HTTPError as exc:
            last_error = exc
            print(f"  {exc.code} from {url}")
            if destination.exists():
                destination.unlink()
    raise SystemExit(f"Could not download {name}: {last_error}")


def open_zip_csv(zip_path: Path, inner_name: str):
    archive = zipfile.ZipFile(zip_path)
    raw = archive.open(inner_name)
    text = (line.decode("utf-8-sig") for line in raw)
    return archive, csv.DictReader(text)


def write_extracts() -> dict:
    """Stream the big FAO files once and keep only the rows this project uses."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ice_cream_path = PROCESSED_DIR / "ice_cream_sua.csv"
    population_path = PROCESSED_DIR / "population.csv"

    element_counts: Counter[tuple[str, str, str]] = Counter()
    years: set[int] = set()
    areas: dict[int, str] = {}
    production_country_rows = 0
    zero_supply_with_trade: set[int] = set()
    trade_by_area: dict[tuple[int, str], float] = {}
    supply_by_area: dict[int, float] = {}

    archive, reader = open_zip_csv(RAW_DIR / SUA_ZIP, SUA_CSV)
    try:
        with ice_cream_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=ICE_CREAM_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for row in reader:
                if row["Item Code"] != ICE_CREAM_ITEM:
                    continue
                writer.writerow(row)
                element_counts[(row["Element Code"], row["Element"], row["Unit"])] += 1
                if row["Year"].isdigit():
                    years.add(int(row["Year"]))
                if not row["Area Code"].isdigit():
                    continue
                area_code = int(row["Area Code"])
                areas[area_code] = row["Area"]
                if row["Value"] in ("", None):
                    continue
                value = float(row["Value"])
                if row["Element Code"] == "5510" and area_code < 5000 and area_code != CHINA_AGGREGATE_AREA:
                    production_country_rows += 1
                if row["Year"] == "2022" and row["Element Code"] in {"5610", "5910"}:
                    trade_by_area[(area_code, row["Element Code"])] = value
                if row["Year"] == "2022" and row["Element Code"] == "5141":
                    supply_by_area[area_code] = value
    finally:
        archive.close()

    for area_code, supply in supply_by_area.items():
        imports = trade_by_area.get((area_code, "5610"), 0)
        exports = trade_by_area.get((area_code, "5910"), 0)
        if supply == 0 and (imports > 0 or exports > 0) and area_code < 5000:
            zero_supply_with_trade.add(area_code)

    population_rows = 0
    archive, reader = open_zip_csv(RAW_DIR / POPULATION_ZIP, POPULATION_CSV)
    try:
        with population_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=POPULATION_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for row in reader:
                if row["Element Code"] != POPULATION_ELEMENT:
                    continue
                writer.writerow(row)
                population_rows += 1
    finally:
        archive.close()

    return {
        "areas": areas,
        "element_counts": element_counts,
        "years": years,
        "production_country_rows": production_country_rows,
        "zero_supply_with_trade": len(zero_supply_with_trade),
        "population_rows": population_rows,
        "ice_cream_path": ice_cream_path,
        "population_path": population_path,
    }


def m49_number(value: str) -> int | None:
    cleaned = value.strip().lstrip("'")
    if not cleaned.isdigit():
        return None
    return int(cleaned)


def load_iso_by_m49() -> dict[int, tuple[str, str]]:
    mapping: dict[int, tuple[str, str]] = {}
    with ISO_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            number = m49_number(row["country-code"])
            if number is None:
                continue
            mapping[number] = (row["alpha-2"], row["alpha-3"])
    return mapping


def load_area_names() -> dict[int, tuple[str, str]]:
    archive, reader = open_zip_csv(RAW_DIR / SUA_ZIP, AREA_CSV)
    areas: dict[int, tuple[str, str]] = {}
    try:
        for row in reader:
            if not row["Area Code"].isdigit():
                continue
            areas[int(row["Area Code"])] = (row["Area"], row["M49 Code"])
    finally:
        archive.close()
    return areas


def write_area_seed(ice_cream_areas: dict[int, str]) -> tuple[int, list[tuple[int, str]]]:
    iso_by_m49 = load_iso_by_m49()
    catalog = load_area_names()
    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    unmapped: list[tuple[int, str]] = []
    country_count = 0
    with SEED_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["area_code", "area_name", "m49_code", "iso2", "iso3", "is_country"])
        for area_code in sorted(ice_cream_areas):
            area_name, m49_code = catalog.get(area_code, (ice_cream_areas[area_code], ""))
            iso = iso_by_m49.get(m49_number(m49_code) or -1)
            iso2, iso3 = iso if iso else ("", "")
            is_country = area_code < 5000 and area_code != CHINA_AGGREGATE_AREA and bool(iso3)
            if area_code < 5000 and area_code != CHINA_AGGREGATE_AREA and not iso3:
                unmapped.append((area_code, area_name))
            if is_country:
                country_count += 1
            writer.writerow([area_code, area_name, m49_code, iso2, iso3, "true" if is_country else "false"])
    return country_count, unmapped


def print_profile(profile: dict, country_count: int, unmapped: list[tuple[int, str]]) -> None:
    years = profile["years"]
    print()
    print("Extract profile")
    print(f"  Ice cream rows (item {ICE_CREAM_ITEM}): {sum(profile['element_counts'].values())}")
    print(f"  Years: {min(years)}-{max(years)}" if years else "  Years: none")
    print(f"  Population rows (element {POPULATION_ELEMENT}, total, both sexes): {profile['population_rows']}")
    print(f"  Country codes that will enter the mart: {country_count}")
    print(f"  Production rows for countries, all years: {profile['production_country_rows']}")
    print(
        "  Countries in 2022 whose food supply is 0 while imports or exports are not: "
        f"{profile['zero_supply_with_trade']}"
    )
    print("  Measures:")
    for (code, name, unit), count in sorted(profile["element_counts"].items()):
        print(f"    {code} {name} ({unit}): {count}")
    if unmapped:
        print("  Area codes under 5000 with no ISO country code:")
        for area_code, area_name in unmapped:
            print(f"    {area_code} {area_name}")
    else:
        print("  Every country area code mapped to an ISO code.")
    print()
    print("FAO production covers only a few reporting countries, and regional rows repeat them.")
    print("Food supply is 0 for many countries that import and export ice cream.")
    print("The dashboard therefore charts imports and exports. Food supply stays on the mart")
    print("so you can see the gap instead of charting it as consumption.")


def bigquery_field_name(name: str) -> str:
    """BigQuery rejects spaces and parentheses. FAO headers keep those in the CSV."""
    return name.replace("(", "").replace(")", "").replace(" ", "_")


def bigquery_schema(fields: list[str], integer_fields: set[str]):
    from google.cloud import bigquery

    schema = []
    for name in fields:
        if name in integer_fields:
            field_type = "INTEGER"
        elif name == "Value":
            field_type = "FLOAT"
        else:
            field_type = "STRING"
        schema.append(bigquery.SchemaField(bigquery_field_name(name), field_type))
    return schema


def load_bigquery(project: str, ice_cream_path: Path, population_path: Path) -> None:
    from google.cloud import bigquery

    location = os.environ.get("BQ_LOCATION", "US")
    client = bigquery.Client(project=project)
    dataset_id = f"{project}.raw"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = location
    client.create_dataset(dataset, exists_ok=True)
    print(f"Dataset {dataset_id} is in {location}")

    integer_fields = {"Area Code", "Item Code", "Element Code", "Year Code", "Year"}
    jobs = [
        ("ice_cream_sua", ice_cream_path, ICE_CREAM_FIELDS),
        ("population", population_path, POPULATION_FIELDS),
    ]
    for table_name, path, fields in jobs:
        table_id = f"{dataset_id}.{table_name}"
        job_config = bigquery.LoadJobConfig(
            schema=bigquery_schema(fields, integer_fields),
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            allow_quoted_newlines=True,
        )
        with path.open("rb") as handle:
            job = client.load_table_from_file(handle, table_id, job_config=job_config)
        job.result()
        table = client.get_table(table_id)
        print(f"Loaded {table.num_rows} rows into {table_id}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract FAO ice cream data and load BigQuery raw tables.")
    parser.add_argument(
        "--project",
        default=os.environ.get("GCP_PROJECT"),
        help="GCP project id. Defaults to the GCP_PROJECT environment variable. Omit it to only write local files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    download(SUA_ZIP, RAW_DIR / SUA_ZIP)
    download(POPULATION_ZIP, RAW_DIR / POPULATION_ZIP)
    profile = write_extracts()
    country_count, unmapped = write_area_seed(profile["areas"])
    print_profile(profile, country_count, unmapped)
    print(f"Wrote {profile['ice_cream_path']}")
    print(f"Wrote {profile['population_path']}")
    print(f"Wrote {SEED_PATH}")
    if not args.project:
        print()
        print("No GCP project set, so BigQuery was not loaded.")
        print("Re-run with GCP_PROJECT=your-project-id or --project your-project-id after you authenticate.")
        return
    try:
        load_bigquery(args.project, profile["ice_cream_path"], profile["population_path"])
    except Exception as exc:  # surface auth and API errors without a traceback wall
        print(f"BigQuery load failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
