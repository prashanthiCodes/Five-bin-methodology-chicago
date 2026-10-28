from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


PROJECT_ROOT = Path(__file__).resolve().parents[1]
YEARS = (2014, 2019, 2024)
YEAR_SPECS = {
    2014: {
        "pattern": "ACS_5YR_2014_*.xlsx",
        "sheet": "Selected tracts",
        "geoid_column": "GEOID",
        "boundary_vintage": 2010,
    },
    2019: {
        "pattern": "ACS_5YR_2019_*.xlsx",
        "sheet": "Sheet1",
        "geoid_column": "GEOID",
        "boundary_vintage": 2010,
    },
    2024: {
        "pattern": "ACS_5YR_2024_*.xlsx",
        "sheet": "Tracts",
        # The supplied workbook contains valid 11-digit GEOIDs under this
        # malformed Excel header. Preserve the source column in the audit CSV.
        "geoid_column": "#NUM!",
        "boundary_vintage": 2020,
    },
}
SOURCE_COLUMNS = (
    "Pop_Edu_BachAbove_E",
    "Total_Pop_25Over_E",
    "HH_Med_Inc_E",
    "Total_Own_HH_E.x",
    "Total_HH_E.x",
    "HH_Inc_100K_More_E",
    "HU_Built_2000_Later_E",
    "Pop_Age_65Over_E",
    "Total_Pop_E",
    "Pop_Age_10to17_E",
    "Pop_Below_Pov_E",
    "Total_Pop_Pov_E",
    "Pop_Below_Pov_Share",
    "HU_Built_1939_Earlier_E",
    "Total_Vac_HU_E",
    "Own_HH_Cost_Burden_E",
    "Rent_HH_Cost_Burden_E",
    "Total_Own_HH_IncComp_E",
    "Total_Rent_HH_IncComp_E.x",
)
BASE_COLUMNS = (
    "year",
    "geoid",
    "tract_name",
    "community_area",
    "community_area_id",
    "source_geoid_column",
    "source_workbook",
)

RAW_FILES = {
    "acs_2014_lookup.txt": "https://www2.census.gov/programs-surveys/acs/summary_file/2014/documentation/user_tools/ACS_5yr_Seq_Table_Number_Lookup.txt",
    "20145il0105000.zip": "https://www2.census.gov/programs-surveys/acs/summary_file/2014/data/5_year_seq_by_state/Illinois/Tracts_Block_Groups_Only/20145il0105000.zip",
    "g20145il.csv": "https://www2.census.gov/programs-surveys/acs/summary_file/2014/data/5_year_seq_by_state/Illinois/Tracts_Block_Groups_Only/g20145il.csv",
    "acsdt5y2019-b25077.dat": "https://www2.census.gov/programs-surveys/acs/summary_file/2019/prototype/5YRData/acsdt5y2019-b25077.dat",
    "acsdt5y2024-b25077.dat": "https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b25077.dat",
    "tl_2010_17031_tract10.zip": "https://www2.census.gov/geo/tiger/TIGER2010/TRACT/2010/tl_2010_17031_tract10.zip",
    "tl_2020_17_tract.zip": "https://www2.census.gov/geo/tiger/TIGER2020/TRACT/tl_2020_17_tract.zip",
}


def normalize_geoid(value: Any) -> str:
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if not text.isdigit() or len(text) != 11:
        raise ValueError(f"Expected an 11-digit census GEOID; found {value!r}")
    if not text.startswith("17031"):
        raise ValueError(f"Expected a Cook County GEOID beginning 17031; found {text}")
    return text


def find_unique_file(folder: Path, pattern: str) -> Path:
    matches = sorted(folder.glob(pattern))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected exactly one input matching {pattern!r} in {folder}; found {len(matches)}"
        )
    return matches[0]


def import_workbook(year: int, workbook: Path, out_dir: Path) -> tuple[set[str], dict[str, Any]]:
    spec = YEAR_SPECS[year]
    book = load_workbook(workbook, read_only=True, data_only=True)
    try:
        if spec["sheet"] not in book.sheetnames:
            raise ValueError(f"{workbook.name} is missing worksheet {spec['sheet']!r}")
        sheet = book[spec["sheet"]]
        headers = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
        geoid_col = spec["geoid_column"]
        source_columns = tuple(field for field in SOURCE_COLUMNS if not (year == 2024 and field == "Total_Pop_Pov_E"))
        required = {
            geoid_col,
            "NAME",
            "COMMUNITY_NM",
            "COMMUNITY_NBR",
            "CHICAGO_IND",
            *source_columns,
        }
        missing = sorted(required - set(headers))
        if missing:
            raise ValueError(f"{workbook.name} is missing required columns: {missing}")

        indexes = {name: headers.index(name) for name in required}
        columns = (*BASE_COLUMNS, *source_columns)
        out_dir.mkdir(parents=True, exist_ok=True)
        output = out_dir / f"acs_tract_inputs_{year}.csv"
        geoid_set: set[str] = set()
        duplicate_geoids: list[str] = []
        malformed_ids: list[str] = []
        selected_rows = 0

        # Some supplied XLSX dimensions extend to a million formatted rows.
        # Reset the declared range and iterate only rows actually stored in XML.
        sheet.reset_dimensions()
        with output.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            for row in sheet.iter_rows(min_row=2, max_col=len(headers), values_only=True):
                if not row or all(value is None for value in row):
                    continue
                flag = row[indexes["CHICAGO_IND"]]
                if str(flag).strip().upper() != "Y":
                    continue
                selected_rows += 1
                source_geoid = row[indexes[geoid_col]]
                try:
                    geoid = normalize_geoid(source_geoid)
                except ValueError:
                    malformed_ids.append(str(source_geoid))
                    continue
                if geoid in geoid_set:
                    duplicate_geoids.append(geoid)
                geoid_set.add(geoid)
                area_id = row[indexes["COMMUNITY_NBR"]]
                record = {
                    "year": year,
                    "geoid": geoid,
                    "tract_name": row[indexes["NAME"]],
                    "community_area": row[indexes["COMMUNITY_NM"]],
                    "community_area_id": (
                        int(float(area_id)) if area_id not in (None, "") else ""
                    ),
                    "source_geoid_column": geoid_col,
                    "source_workbook": workbook.name,
                }
                record.update({field: row[indexes[field]] for field in source_columns})
                writer.writerow(record)

        if malformed_ids or duplicate_geoids:
            raise ValueError(
                f"{year}: malformed GEOIDs={malformed_ids[:10]}; "
                f"duplicate GEOIDs={duplicate_geoids[:10]}"
            )
        return geoid_set, {
            "year": year,
            "source_workbook": workbook.name,
            "worksheet": spec["sheet"],
            "source_geoid_column": geoid_col,
            "selected_rows": selected_rows,
            "unique_geoids": len(geoid_set),
            "output": output.name,
        }
    finally:
        book.close()


def download_sources(raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    for filename, url in RAW_FILES.items():
        target = raw_dir / filename
        if target.exists() and target.stat().st_size:
            print(f"Using existing source file: {target.name}")
            continue
        print(f"Downloading {filename}")
        request = urllib.request.Request(
            url, headers={"User-Agent": "ChicagoTractAnalysis/1.0 (research reproducibility)"}
        )
        with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)


def parse_estimate(value: Any) -> float | None:
    text = str(value).strip()
    if not text or text in {".", "-666666666", "-999999999"}:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def write_proxy(year: int, geoid_values: dict[str, tuple[float | None, float | None]], out_dir: Path) -> dict[str, Any]:
    output = out_dir / f"acs_median_value_proxy_{year}.csv"
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("year", "geoid", "acs_table", "estimate", "margin_of_error", "proxy_description"),
        )
        writer.writeheader()
        for geoid in sorted(geoid_values):
            estimate, moe = geoid_values[geoid]
            writer.writerow(
                {
                    "year": year,
                    "geoid": geoid,
                    "acs_table": "B25077",
                    "estimate": "" if estimate is None else estimate,
                    "margin_of_error": "" if moe is None else moe,
                    "proxy_description": "ACS median value (dollars) for owner-occupied housing units; proxy for market house price",
                }
            )
    return {"year": year, "rows": len(geoid_values), "missing_estimate": sum(v[0] is None for v in geoid_values.values()), "output": output.name}


def extract_2014_proxy(geoids: set[str], raw_dir: Path) -> dict[str, tuple[float | None, float | None]]:
    table_sequence = None
    start_position = None
    with (raw_dir / "acs_2014_lookup.txt").open(encoding="cp1252", newline="") as stream:
        for row in csv.reader(stream):
            if len(row) > 4 and row[1].strip() == "B25077" and row[2].strip().isdigit():
                table_sequence = row[2].strip().zfill(4)
                start_position = int(row[4].strip())
                break
    if table_sequence is None or start_position is None:
        raise ValueError("Could not locate B25077 in the 2014 ACS sequence lookup file")

    logrecno_to_geoid: dict[str, str] = {}
    with (raw_dir / "g20145il.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.reader(stream):
            if len(row) < 50 or row[2].strip() != "140":
                continue
            geoid = row[48].strip()
            if geoid.startswith("14000US"):
                geoid = geoid.removeprefix("14000US")
            if geoid in geoids:
                logrecno_to_geoid[row[4].strip()] = geoid
    if set(logrecno_to_geoid.values()) != geoids:
        raise ValueError(
            f"2014 geography file missed {len(geoids - set(logrecno_to_geoid.values()))} Chicago GEOIDs"
        )

    archive = raw_dir / f"20145il{table_sequence}000.zip"
    if not archive.exists():
        raise FileNotFoundError(f"Missing 2014 ACS sequence archive {archive.name}")
    values: dict[str, list[float | None]] = {geoid: [None, None] for geoid in geoids}
    with zipfile.ZipFile(archive) as zf:
        for file_prefix, position_index in (("e", 0), ("m", 1)):
            name = next(
                (n for n in zf.namelist() if Path(n).name.lower().startswith(file_prefix + "20145il")),
                None,
            )
            if name is None:
                raise FileNotFoundError(f"{archive.name} has no {file_prefix} estimate file")
            with zf.open(name) as binary, __import__("io").TextIOWrapper(binary, encoding="latin-1", newline="") as text:
                for row in csv.reader(text):
                    if len(row) <= max(5, start_position - 1):
                        continue
                    geoid = logrecno_to_geoid.get(row[5].strip())
                    if geoid is None:
                        continue
                    values[geoid][position_index] = parse_estimate(row[start_position - 1])
    return {geoid: (pair[0], pair[1]) for geoid, pair in values.items()}


def extract_table_based_proxy(year: int, geoids: set[str], raw_dir: Path) -> dict[str, tuple[float | None, float | None]]:
    source = raw_dir / f"acsdt5y{year}-b25077.dat"
    values: dict[str, tuple[float | None, float | None]] = {}
    with source.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="|")
        for row in reader:
            geo_id = (row.get("GEO_ID") or "").strip()
            if not geo_id.startswith("1400000US"):
                continue
            geoid = geo_id[-11:]
            if geoid not in geoids:
                continue
            if geoid in values:
                raise ValueError(f"{year}: duplicate B25077 geography GEOID {geoid}")
            values[geoid] = (
                parse_estimate(row.get("B25077_E001")),
                parse_estimate(row.get("B25077_M001")),
            )
    missing_geos = geoids - set(values)
    if missing_geos:
        raise ValueError(f"{year}: B25077 file lacks {len(missing_geos)} tract GEOIDs: {sorted(missing_geos)[:10]}")
    return values


def load_pyshp(project_root: Path):
    local_deps = project_root / ".build_deps"
    if str(local_deps) not in sys.path:
        sys.path.insert(0, str(local_deps))
    try:
        import shapefile
    except ImportError as exc:
        raise RuntimeError(
            "PyShp is required to convert TIGER geometry. Install project dependencies with "
            "python -m pip install -r requirements.txt."
        ) from exc
    return shapefile


def tiger_features(
    zip_path: Path,
    wanted_geoids: set[str],
    *,
    geoid_candidates: tuple[str, ...],
    name_candidates: tuple[str, ...],
    vintage: int,
    shapefile_module: Any,
) -> list[dict[str, Any]]:
    with zipfile.ZipFile(zip_path) as zf:
        members = {Path(name).suffix.lower(): name for name in zf.namelist() if Path(name).suffix.lower() in {".shp", ".shx", ".dbf"}}
        missing = {".shp", ".shx", ".dbf"} - set(members)
        if missing:
            raise ValueError(f"{zip_path.name} lacks required shapefile components: {sorted(missing)}")
        reader = shapefile_module.Reader(
            shp=__import__("io").BytesIO(zf.read(members[".shp"])),
            shx=__import__("io").BytesIO(zf.read(members[".shx"])),
            dbf=__import__("io").BytesIO(zf.read(members[".dbf"])),
        )
        field_names = [field[0] for field in reader.fields[1:]]
        geoid_field = next((field for field in geoid_candidates if field in field_names), None)
        name_field = next((field for field in name_candidates if field in field_names), None)
        if geoid_field is None or name_field is None:
            raise ValueError(
                f"{zip_path.name} is missing GEOID/name fields; available fields: {field_names}"
            )
        geoid_index = field_names.index(geoid_field)
        name_index = field_names.index(name_field)
        features = []
        seen: set[str] = set()
        for shape_record in reader.iterShapeRecords():
            values = shape_record.record
            geoid = str(values[geoid_index]).strip()
            if geoid not in wanted_geoids:
                continue
            if geoid in seen:
                raise ValueError(f"{vintage} TIGER file has duplicate GEOID {geoid}")
            seen.add(geoid)
            geometry = shape_record.shape.__geo_interface__
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "GEOID": geoid,
                        "tract_name": str(values[name_index]).strip(),
                        "boundary_vintage": vintage,
                        "boundary_source": "U.S. Census Bureau TIGER/Line",
                    },
                    "geometry": geometry,
                }
            )
        if seen != wanted_geoids:
            raise ValueError(
                f"{vintage} TIGER geometry missing {len(wanted_geoids - seen)} input GEOIDs: "
                f"{sorted(wanted_geoids - seen)[:12]}"
            )
        reader.close()
        return features


def build_boundaries(project_root: Path, geoid_sets: dict[int, set[str]]) -> list[dict[str, Any]]:
    raw_dir = project_root / "data" / "raw"
    out_dir = project_root / "data" / "boundaries"
    out_dir.mkdir(parents=True, exist_ok=True)
    shapefile_module = load_pyshp(project_root)
    specs = (
        (2010, geoid_sets[2014], raw_dir / "tl_2010_17031_tract10.zip", ("GEOID10",), ("NAMELSAD10", "NAME10"), "chicago_tracts_2010.geojson"),
        (2020, geoid_sets[2024], raw_dir / "tl_2020_17_tract.zip", ("GEOID", "GEOID20"), ("NAMELSAD", "NAMELSAD20", "NAME"), "chicago_tracts_2020.geojson"),
    )
    reports = []
    for vintage, geoids, source, geoid_candidates, name_candidates, filename in specs:
        features = tiger_features(
            source,
            geoids,
            geoid_candidates=geoid_candidates,
            name_candidates=name_candidates,
            vintage=vintage,
            shapefile_module=shapefile_module,
        )
        output = out_dir / filename
        output.write_text(
            json.dumps(
                {"type": "FeatureCollection", "name": f"Chicago Census tracts, {vintage} geography", "features": features},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        reports.append({"vintage": vintage, "features": len(features), "file": filename})
    return reports


def run(project_root: Path, workbook_dir: Path | None, fetch_sources: bool) -> None:
    source_dir = project_root / "data" / "source"
    raw_dir = project_root / "data" / "raw"
    source_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    if fetch_sources:
        download_sources(raw_dir)

    geoid_sets: dict[int, set[str]] = {}
    workbook_reports = []
    if workbook_dir is not None:
        for year in YEARS:
            workbook = find_unique_file(workbook_dir, YEAR_SPECS[year]["pattern"])
            geoid_sets[year], report = import_workbook(year, workbook, source_dir)
            workbook_reports.append(report)
    else:
        for year in YEARS:
            input_csv = source_dir / f"acs_tract_inputs_{year}.csv"
            if not input_csv.exists():
                raise FileNotFoundError(
                    f"Missing {input_csv.name}. Supply --workbook-dir to extract the local ACS workbooks."
                )
            with input_csv.open(encoding="utf-8-sig", newline="") as stream:
                geoid_sets[year] = {normalize_geoid(row["geoid"]) for row in csv.DictReader(stream)}

    proxy_reports = []
    for year in YEARS:
        if year == 2014:
            proxy_values = extract_2014_proxy(geoid_sets[year], raw_dir)
        else:
            proxy_values = extract_table_based_proxy(year, geoid_sets[year], raw_dir)
        proxy_reports.append(write_proxy(year, proxy_values, source_dir))

    boundary_reports = build_boundaries(project_root, geoid_sets)
    report = {
        "input_workbooks": workbook_reports,
        "acs_median_value_proxy": proxy_reports,
        "boundaries": boundary_reports,
        "selected_tract_counts": {str(year): len(geoid_sets[year]) for year in YEARS},
        "source_note": (
            "2014 and 2019 use 2010 census tract GEOIDs; 2024 uses 2020 census tract GEOIDs. "
            "The supplied 2024 workbook labels GEOID as #NUM!; valid 11-digit values are preserved."
        ),
    }
    (project_root / "data" / "source_preparation_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract supplied ACS workbook inputs, official ACS B25077 proxy estimates, and TIGER tract geometry."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Project directory (defaults to this script's parent).",
    )
    parser.add_argument(
        "--workbook-dir",
        type=Path,
        help="Directory containing the three local ACS workbooks; omit to reuse prepared CSV inputs.",
    )
    parser.add_argument(
        "--download-sources",
        action="store_true",
        help="Download the documented Census Summary File and TIGER source files into data/raw/.",
    )
    args = parser.parse_args()
    run(args.project_root.resolve(), args.workbook_dir.resolve() if args.workbook_dir else None, args.download_sources)


if __name__ == "__main__":
    main()



