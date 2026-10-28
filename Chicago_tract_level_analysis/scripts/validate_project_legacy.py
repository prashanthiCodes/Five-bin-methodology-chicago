from __future__ import annotations

import csv
import json
from pathlib import Path

from build_project import INDICATORS, YEARS, classify


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    checks = 0
    source_geoids = {}
    for year in YEARS:
        source = read_csv(ROOT / "data" / "source" / f"acs_tract_inputs_{year}.csv")
        source_ids = [row["geoid"] for row in source]
        require(len(source_ids) == len(set(source_ids)), f"{year}: duplicate source GEOID")
        require(all(len(g) == 11 and g.isdigit() and g.startswith("17031") for g in source_ids), f"{year}: malformed GEOID")
        source_geoids[year] = set(source_ids)
        checks += 2

        vintage = 2020 if year == 2024 else 2010
        geometry = json.loads((ROOT / "data" / "boundaries" / f"chicago_tracts_{vintage}.geojson").read_text(encoding="utf-8"))
        geometry_ids = [feature["properties"].get("GEOID") for feature in geometry["features"]]
        require(len(geometry_ids) == len(set(geometry_ids)), f"{vintage}: duplicate geometry GEOID")
        require(set(source_ids) == set(geometry_ids), f"{year}: data-to-geometry GEOID mismatch")
        checks += 2

        rows = read_csv(ROOT / "outputs" / "tables" / f"classification_{year}.csv")
        require(len(rows) == len(source) * len(INDICATORS), f"{year}: incorrect classification row count")
        require(len({(r["geoid"], r["indicator"]) for r in rows}) == len(rows), f"{year}: duplicate tract-indicator row")
        require({r["indicator"] for r in rows} == {i["id"] for i in INDICATORS}, f"{year}: indicator set mismatch")
        for row in rows:
            if row["status"] != "classified":
                require(not row["relative_percent"] and not row["raw_bin"] and not row["class_label"], f"{year}: unclassified record has a bin")
                continue
            relative = float(row["relative_percent"])
            raw_bin, label = classify(relative, row["direction"])
            require(int(row["raw_bin"]) == raw_bin and row["class_label"] == label, f"{year}: incorrect bin for {row['geoid']} {row['indicator']}")
        checks += 4

        web_data = json.loads((ROOT / "website" / "assets" / "data" / f"classification_{year}.json").read_text(encoding="utf-8"))
        require(set(web_data) == set(source_ids), f"{year}: website GEOID set mismatch")
        require(all("_meta" in item and "community_area" in item["_meta"] for item in web_data.values()), f"{year}: missing tract metadata")
        require(all(set(item) == {"_meta", *[i["id"] for i in INDICATORS]} for item in web_data.values()), f"{year}: website indicator keys mismatch")
        checks += 3

    require(source_geoids[2014] == source_geoids[2019], "2014 and 2019 do not share the same GEOID set")
    checks += 1
    benchmarks = read_csv(ROOT / "outputs" / "tables" / "city_benchmarks.csv")
    require(len(benchmarks) == len(YEARS) * len(INDICATORS), "benchmark table does not contain 36 rows")
    require(all(row["benchmark_value"] and float(row["benchmark_value"]) > 0 for row in benchmarks), "missing or nonpositive city benchmark")
    checks += 2

    cases = [(49.999, 1), (50, 2), (74.999, 2), (75, 3), (125, 3), (125.001, 4), (150, 4), (150.001, 5)]
    for relative, raw_bin in cases:
        require(classify(relative, "positive")[0] == raw_bin, f"positive bin edge failure at {relative}")
        require(classify(relative, "negative")[0] == raw_bin, f"negative bin edge failure at {relative}")
    require(classify(49.999, "negative")[1] == "Very High", "negative-direction labels are not reversed")
    require(classify(150.001, "negative")[1] == "Very Low", "negative-direction labels are not reversed")
    checks += len(cases) * 2 + 2

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    require("C:\\" not in html and "file:///" not in html, "website contains an absolute local path")
    for rel in ("website/assets/data/indicator_metadata.json", "website/assets/data/classification_${year}.json", "data/boundaries/chicago_tracts_${vintage}.geojson"):
        require(rel in html, f"website is missing relative asset reference {rel}")
    require('id="year"' in html and 'id="indicator"' in html and 'id="legend"' in html, "website selectors or legend are missing")
    checks += 6

    report = read_csv(ROOT / "outputs" / "tables" / "data_quality_report.csv")
    require(any(row["check"] == "Poverty denominator limitation" and row["year"] == "2024" for row in report), "2024 poverty limitation is undocumented")
    require(any(row["check"] == "User workbook publication provenance" and row["status"] == "REVIEW" for row in report), "workbook publication review is undocumented")
    checks += 2
    print(json.dumps({"status": "PASS", "checks": checks, "classification_rows": sum(len(read_csv(ROOT / "outputs" / "tables" / f"classification_{year}.csv")) for year in YEARS), "tract_counts": {str(year): len(source_geoids[year]) for year in YEARS}, "indicator_count": len(INDICATORS), "benchmark_count": len(benchmarks)}, indent=2))


if __name__ == "__main__":
    main()
