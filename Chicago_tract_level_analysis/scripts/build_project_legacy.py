from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
YEARS = (2014, 2019, 2024)
POSITIVE = {
    "Bach_plus_share",
    "Median_household_income",
    "Median_house_price",
    "Owner_occupied_share",
    "Income_100k_plus_share",
    "HU_Built_2000_Later_E",
}
INDICATORS = [
    {"id": "Bach_plus_share", "label": "Bachelor’s degree or higher", "kind": "share", "direction": "positive", "numerator": "Pop_Edu_BachAbove_E", "denominator": "Total_Pop_25Over_E", "unit": "population share"},
    {"id": "Median_household_income", "label": "Median household income", "kind": "median", "direction": "positive", "source": "HH_Med_Inc_E", "unit": "USD per household"},
    {"id": "Median_house_price", "label": "Median owner-occupied home value (proxy)", "kind": "proxy_median", "direction": "positive", "source": "ACS B25077", "unit": "USD per owner-occupied home"},
    {"id": "Owner_occupied_share", "label": "Owner-occupied households", "kind": "share", "direction": "positive", "numerator": "Total_Own_HH_E.x", "denominator": "Total_HH_E.x", "unit": "household share"},
    {"id": "Income_100k_plus_share", "label": "Households with income $100,000 or more", "kind": "share", "direction": "positive", "numerator": "HH_Inc_100K_More_E", "denominator": "Total_HH_E.x", "unit": "household share"},
    {"id": "HU_Built_2000_Later_E", "label": "Housing units built 2000 or later", "kind": "count", "direction": "positive", "source": "HU_Built_2000_Later_E", "unit": "housing units per tract"},
    {"id": "Age_65_over_share", "label": "Population age 65 or older", "kind": "share", "direction": "negative", "numerator": "Pop_Age_65Over_E", "denominator": "Total_Pop_E", "unit": "population share"},
    {"id": "Age_10_17_share", "label": "Population ages 10–17", "kind": "share", "direction": "negative", "numerator": "Pop_Age_10to17_E", "denominator": "Total_Pop_E", "unit": "population share"},
    {"id": "Poverty_Share", "label": "Population in poverty", "kind": "poverty", "direction": "negative", "unit": "population share"},
    {"id": "HU_Built_1939_Earlier", "label": "Housing units built 1939 or earlier", "kind": "count", "direction": "negative", "source": "HU_Built_1939_Earlier_E", "unit": "housing units per tract"},
    {"id": "Total_Vac_HU_E", "label": "Vacant housing units", "kind": "count", "direction": "negative", "source": "Total_Vac_HU_E", "unit": "housing units per tract"},
    {"id": "HH_Cost_Burden_Share", "label": "Household cost burden", "kind": "share", "direction": "negative", "numerator": "Own_HH_Cost_Burden_E + Rent_HH_Cost_Burden_E", "denominator": "Total_Own_HH_IncComp_E.x + Total_Rent_HH_IncComp_E.x", "unit": "household share"},
]
INDICATOR_BY_ID = {item["id"]: item for item in INDICATORS}
BIN_LABELS = ["Very Low", "Low", "Middle", "High", "Very High"]
COLORS = {"Very Low": "#b23a48", "Low": "#e58b45", "Middle": "#eadc8b", "High": "#86b99a", "Very High": "#26734d"}


def num(row: dict[str, Any], key: str) -> float | None:
    raw = row.get(key)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def weighted_median(pairs: list[tuple[float, float]]) -> float | None:
    valid = [(value, weight) for value, weight in pairs if math.isfinite(value) and math.isfinite(weight) and weight > 0]
    if not valid:
        return None
    valid.sort(key=lambda pair: pair[0])
    cutoff = sum(weight for _, weight in valid) / 2
    cumulative = 0.0
    for value, weight in valid:
        cumulative += weight
        if cumulative >= cutoff:
            return value
    return valid[-1][0]


def cost_burden_components(row: dict[str, Any]) -> tuple[float | None, float | None]:
    fields = (
        "Own_HH_Cost_Burden_E",
        "Rent_HH_Cost_Burden_E",
        "Total_Own_HH_IncComp_E",
        "Total_Rent_HH_IncComp_E.x",
    )
    values = [num(row, field) for field in fields]
    if any(value is None for value in values):
        return None, None
    return values[0] + values[1], values[2] + values[3]


def classify(relative: float, direction: str) -> tuple[int, str]:
    # Threshold endpoints intentionally follow the source project's validated bins.
    if relative < 50:
        raw_bin = 0
    elif relative < 75:
        raw_bin = 1
    elif relative <= 125:
        raw_bin = 2
    elif relative <= 150:
        raw_bin = 3
    else:
        raw_bin = 4
    display_bin = raw_bin if direction == "positive" else 4 - raw_bin
    return raw_bin + 1, BIN_LABELS[display_bin]


def value_and_weight(indicator_id: str, row: dict[str, str], proxy: dict[str, str] | None) -> tuple[float | None, float | None, str]:
    spec = INDICATOR_BY_ID[indicator_id]
    if indicator_id == "Median_house_price":
        value = num(proxy or {}, "estimate")
        return value, num(row, "Total_Own_HH_E.x"), "ACS B25077 tract median value; proxy for sale price"
    if indicator_id == "Median_household_income":
        value = num(row, "HH_Med_Inc_E")
        return value, num(row, "Total_HH_E.x"), "Direct median estimate from supplied ACS tract workbook"
    if indicator_id == "Poverty_Share":
        if int(row["year"]) in (2014, 2019):
            numerator, denominator = num(row, "Pop_Below_Pov_E"), num(row, "Total_Pop_Pov_E")
            value = numerator / denominator if numerator is not None and denominator is not None and denominator > 0 else None
            return value, denominator, "Pop_Below_Pov_E / Total_Pop_Pov_E"
        value = num(row, "Pop_Below_Pov_Share")
        count = num(row, "Pop_Below_Pov_E")
        inferred_denominator = count / value if count is not None and value is not None and value > 0 else None
        return value, inferred_denominator, "Direct Pop_Below_Pov_Share; 2024 denominator inferred only for benchmark weighting"
    if spec["kind"] == "share":
        if indicator_id == "HH_Cost_Burden_Share":
            numerator, denominator = cost_burden_components(row)
        else:
            numerator, denominator = num(row, spec["numerator"]), num(row, spec["denominator"])
        value = numerator / denominator if numerator is not None and denominator is not None and denominator > 0 else None
        return value, denominator, f"{spec.get('numerator')} / {spec.get('denominator')}"
    value = num(row, spec["source"])
    return value, None, f"Direct source count: {spec['source']}"


def main() -> None:
    source_dir = ROOT / "data" / "source"
    boundaries_dir = ROOT / "data" / "boundaries"
    outputs_dir = ROOT / "outputs" / "tables"
    class_dir = ROOT / "data" / "classifications"
    website_data_dir = ROOT / "website" / "assets" / "data"
    for folder in (outputs_dir, class_dir, website_data_dir):
        folder.mkdir(parents=True, exist_ok=True)

    all_records: list[dict[str, Any]] = []
    all_quality: list[dict[str, Any]] = []
    all_boundaries: dict[int, dict[str, Any]] = {}
    for vintage in (2010, 2020):
        path = boundaries_dir / f"chicago_tracts_{vintage}.geojson"
        geojson = json.loads(path.read_text(encoding="utf-8"))
        geos = [feature["properties"].get("GEOID") for feature in geojson.get("features", [])]
        if any(not isinstance(g, str) or len(g) != 11 or not g.isdigit() or not g.startswith("17031") for g in geos):
            raise ValueError(f"{path.name} has malformed or non-Cook County GEOIDs")
        if len(geos) != len(set(geos)):
            raise ValueError(f"{path.name} has duplicate GEOIDs")
        all_boundaries[vintage] = geojson
        all_quality.append({"year": "all", "check": f"{vintage} boundary GEOIDs", "status": "PASS", "count": len(geos), "details": f"Official Census TIGER/Line tract geometry; unique 11-digit Cook County GEOIDs."})

    source_by_year: dict[int, list[dict[str, str]]] = {}
    proxy_by_year: dict[int, dict[str, dict[str, str]]] = {}
    geoids_by_year: dict[int, set[str]] = {}
    for year in YEARS:
        rows = read_csv(source_dir / f"acs_tract_inputs_{year}.csv")
        proxies = {row["geoid"]: row for row in read_csv(source_dir / f"acs_median_value_proxy_{year}.csv")}
        geoid_list = [row["geoid"] for row in rows]
        if len(geoid_list) != len(set(geoid_list)):
            raise ValueError(f"{year} input has duplicate GEOIDs")
        if any(len(g) != 11 or not g.isdigit() or not g.startswith("17031") for g in geoid_list):
            raise ValueError(f"{year} input has malformed or non-Cook County GEOIDs")
        vintage = 2020 if year == 2024 else 2010
        geometry_geoids = {feature["properties"]["GEOID"] for feature in all_boundaries[vintage]["features"]}
        missing_geometry = set(geoid_list) - geometry_geoids
        extra_geometry = geometry_geoids - set(geoid_list)
        if missing_geometry or extra_geometry:
            raise ValueError(f"{year}: boundary join mismatch; missing={len(missing_geometry)}, extra={len(extra_geometry)}")
        source_by_year[year] = rows
        proxy_by_year[year] = proxies
        geoids_by_year[year] = set(geoid_list)
        all_quality.append({"year": year, "check": "Input GEOID validation and boundary join", "status": "PASS", "count": len(rows), "details": f"Unique 11-digit GEOIDs; all match the official {vintage} TIGER/Line geometry exactly."})
        all_quality.append({"year": year, "check": "Input data records", "status": "INFO", "count": len(rows), "details": f"Source workbook rows; geography vintage {vintage}. 2024 source GEOID header is preserved as #NUM! in metadata."})
        missing_proxy = sum(num(row, "estimate") is None for row in proxies.values())
        all_quality.append({"year": year, "check": "B25077 home-value proxy missing estimates", "status": "WARN" if missing_proxy else "PASS", "count": missing_proxy, "details": "ACS median owner-occupied housing value; this is not a sale-price estimate."})
        for indicator in INDICATORS:
            indicator_id = indicator["id"]
            missing_count = 0
            invalid_share_count = 0
            for row in rows:
                proxy = proxies.get(row["geoid"])
                value, _, _ = value_and_weight(indicator_id, row, proxy)
                if value is None:
                    missing_count += 1
                elif indicator["kind"] in {"share", "poverty"} and not 0 <= value <= 1:
                    invalid_share_count += 1
            all_quality.append({"year": year, "check": f"{indicator_id}: missing tract values", "status": "WARN" if missing_count else "PASS", "count": missing_count, "details": f"Of {len(rows)} input tracts; missing values remain unclassified."})
            if indicator["kind"] in {"share", "poverty"}:
                all_quality.append({"year": year, "check": f"{indicator_id}: outside [0,1]", "status": "WARN" if invalid_share_count else "PASS", "count": invalid_share_count, "details": "Invalid shares are excluded from benchmarks and classifications."})

    if geoids_by_year[2014] != geoids_by_year[2019]:
        all_quality.append({"year": "2014/2019", "check": "2010 geography ID set comparison", "status": "WARN", "count": len(geoids_by_year[2014] ^ geoids_by_year[2019]), "details": "The two years use the same nominal tract vintage, but the GEOID sets differ; inspect before treating as a panel."})
    else:
        all_quality.append({"year": "2014/2019", "check": "2010 geography ID set comparison", "status": "PASS", "count": len(geoids_by_year[2014]), "details": "2014 and 2019 use identical 2010-vintage tract GEOIDs."})
    all_quality.append({"year": "2024", "check": "Poverty denominator limitation", "status": "WARN", "count": 1, "details": "2024 workbook lacks Total_Pop_Pov_E. Tract values use the supplied Pop_Below_Pov_Share directly. A city benchmark weight is inferred as Pop_Below_Pov_E / share only for positive valid shares; missing, zero, or out-of-range shares cannot supply a weight."})
    poverty_2024 = source_by_year[2024]
    zero_poverty_shares = sum(num(row, "Pop_Below_Pov_Share") == 0 for row in poverty_2024)
    missing_poverty_shares = sum(num(row, "Pop_Below_Pov_Share") is None for row in poverty_2024)
    all_quality.append({"year": "2024", "check": "Poverty direct-share values without inferable benchmark weight", "status": "INFO", "count": zero_poverty_shares, "details": f"Zero direct poverty shares retained as tract values but excluded from inferred denominator weights. Missing direct shares: {missing_poverty_shares}; they remain unclassified."})
    all_quality.append({"year": "all", "check": "ACS uncertainty and geography comparability", "status": "WARN", "count": "", "details": "ACS 5-year estimates overlap calendar years and include sampling error. MOEs are carried only for B25077; uncertainty is not propagated through the other workbook-derived indicators. 2014/2019 use 2010 tracts; 2024 uses 2020 tracts without a crosswalk."})
    all_quality.append({"year": "all", "check": "User workbook publication provenance", "status": "REVIEW", "count": "", "details": "Input workbook schema appears to contain aggregate tract ACS estimates, but no workbook-level source citation, codebook, or license was supplied. Confirm provenance/sharing rights before a public GitHub release."})
    all_quality.append({"year": "2020", "check": "City boundary export versus TIGER input coverage", "status": "WARN", "count": 3, "details": "The inspected City of Chicago 2020 tract export contained 789 features and omitted 3 source GEOIDs (17031010400, 17031081202, 17031081402). It is not used. Official Census TIGER/Line 2020 geometry covers all 792 input tracts."})
    all_quality.append({"year": "all", "check": "Excluded community-area home-value workbook", "status": "INFO", "count": "", "details": "Not used: community-area values cannot support tract-level classification, and its provenance/license was not established. B25077 is used as a clearly labeled proxy."})

    benchmark_values: dict[tuple[int, str], float | None] = {}
    benchmarks_rows: list[dict[str, Any]] = []
    for year in YEARS:
        rows = source_by_year[year]
        proxies = proxy_by_year[year]
        year_values: dict[str, list[tuple[dict[str, str], float, float | None]]] = defaultdict(list)
        for indicator in INDICATORS:
            indicator_id = indicator["id"]
            for row in rows:
                value, weight, method = value_and_weight(indicator_id, row, proxies.get(row["geoid"]))
                if value is None or not math.isfinite(value):
                    continue
                if indicator["kind"] in {"share", "poverty"} and not 0 <= value <= 1:
                    continue
                if indicator["kind"] in {"count", "median", "proxy_median"} and value < 0:
                    continue
                year_values[indicator_id].append((row, value, weight))
            valid = year_values[indicator_id]
            if indicator["kind"] == "share":
                numerator_sum = 0.0
                denominator_sum = 0.0
                valid_weighted = 0
                for row, _, _ in valid:
                    if indicator_id == "HH_Cost_Burden_Share":
                        numerator, denominator = cost_burden_components(row)
                    else:
                        numerator = num(row, indicator["numerator"])
                        denominator = num(row, indicator["denominator"])
                    if numerator is not None and denominator is not None and numerator >= 0 and denominator > 0 and numerator <= denominator:
                        numerator_sum += numerator
                        denominator_sum += denominator
                        valid_weighted += 1
                benchmark = numerator_sum / denominator_sum if denominator_sum > 0 else None
                method = "Ratio of summed source numerators to summed denominators across valid Chicago tracts"
                n_for_benchmark = valid_weighted
            elif indicator["kind"] == "poverty" and year in (2014, 2019):
                numerator_sum = sum(num(row, "Pop_Below_Pov_E") or 0 for row, _, _ in valid)
                denominator_sum = sum(num(row, "Total_Pop_Pov_E") or 0 for row, _, _ in valid)
                benchmark = numerator_sum / denominator_sum if denominator_sum > 0 else None
                method = "Ratio of summed Pop_Below_Pov_E to summed Total_Pop_Pov_E across valid Chicago tracts"
                n_for_benchmark = len(valid)
            elif indicator["kind"] == "poverty":
                numerator_sum = 0.0
                denominator_sum = 0.0
                n_for_benchmark = 0
                for row, value, weight in valid:
                    count = num(row, "Pop_Below_Pov_E")
                    if value > 0 and count is not None and count >= 0 and weight is not None and weight > 0:
                        numerator_sum += count
                        denominator_sum += weight
                        n_for_benchmark += 1
                benchmark = numerator_sum / denominator_sum if denominator_sum > 0 else None
                method = "Incomplete: sum of Pop_Below_Pov_E / inferred denominators (count / direct share) for positive valid shares"
            elif indicator["kind"] == "count":
                benchmark = statistics.fmean(value for _, value, _ in valid) if valid else None
                method = "Arithmetic mean of tract counts across Chicago tracts"
                n_for_benchmark = len(valid)
            else:
                pairs = [(value, weight) for _, value, weight in valid if weight is not None and weight > 0]
                benchmark = weighted_median(pairs)
                method = "Weighted median of tract medians, using total households or owner-occupied households; not a pooled city median"
                n_for_benchmark = len(pairs)
            if benchmark is not None and (not math.isfinite(benchmark) or benchmark <= 0):
                benchmark = None
            benchmark_values[(year, indicator_id)] = benchmark
            benchmarks_rows.append({"year": year, "indicator": indicator_id, "label": indicator["label"], "direction": indicator["direction"], "benchmark_value": benchmark, "benchmark_unit": indicator["unit"], "n_tracts_with_valid_value": len(valid), "n_tracts_used_in_benchmark": n_for_benchmark, "method": method, "limitation": "2024 poverty benchmark is incomplete; it uses only positive direct shares with an inferable denominator." if indicator_id == "Poverty_Share" and year == 2024 else ""})

    out_fields = ["year", "geoid", "tract_name", "community_area", "boundary_vintage", "indicator", "indicator_label", "direction", "unit", "tract_value", "benchmark_value", "relative_percent", "raw_bin", "class_label", "status", "source_fields", "benchmark_method", "moe", "quality_note"]
    all_records = []
    for year in YEARS:
        rows = source_by_year[year]
        proxies = proxy_by_year[year]
        vintage = 2020 if year == 2024 else 2010
        lookup = {row["geoid"]: row for row in rows}
        year_records: list[dict[str, Any]] = []
        year_web: dict[str, dict[str, dict[str, Any]]] = {}
        for row in rows:
            geoid = row["geoid"]
            year_web[geoid] = {"_meta": {"community_area": row.get("community_area", ""), "tract_name": row.get("tract_name", "")}}
            for indicator in INDICATORS:
                indicator_id = indicator["id"]
                value, weight, source_fields = value_and_weight(indicator_id, row, proxies.get(geoid))
                benchmark = benchmark_values[(year, indicator_id)]
                valid = value is not None and math.isfinite(value)
                if valid and indicator["kind"] in {"share", "poverty"} and not 0 <= value <= 1:
                    valid = False
                if valid and indicator["kind"] in {"count", "median", "proxy_median"} and value < 0:
                    valid = False
                relative = (value / benchmark * 100) if valid and benchmark is not None and benchmark > 0 else None
                if relative is not None:
                    raw_bin, label = classify(relative, indicator["direction"])
                    status = "classified"
                else:
                    raw_bin, label = None, None
                    status = "missing_value" if not valid else "missing_benchmark"
                proxy = proxies.get(geoid, {})
                quality_note = ""
                if indicator_id == "Median_house_price":
                    quality_note = "ACS B25077 median value for owner-occupied housing; proxy only, not sale price."
                elif indicator_id == "Poverty_Share" and year == 2024:
                    if value is None:
                        quality_note = "2024 supplied poverty share is missing; no substitute used."
                    elif value == 0:
                        quality_note = "Zero source share retained as a tract value; it cannot supply the inferred benchmark denominator."
                    else:
                        quality_note = "2024 direct share used; benchmark denominator inferred because Total_Pop_Pov_E is absent."
                record = {"year": year, "geoid": geoid, "tract_name": row.get("tract_name", ""), "community_area": row.get("community_area", ""), "boundary_vintage": vintage, "indicator": indicator_id, "indicator_label": indicator["label"], "direction": indicator["direction"], "unit": indicator["unit"], "tract_value": value, "benchmark_value": benchmark, "relative_percent": relative, "raw_bin": raw_bin, "class_label": label, "status": status, "source_fields": source_fields, "benchmark_method": next(b["method"] for b in benchmarks_rows if b["year"] == year and b["indicator"] == indicator_id), "moe": num(proxy, "margin_of_error") if indicator_id == "Median_house_price" else None, "quality_note": quality_note}
                year_records.append(record)
                all_records.append(record)
                year_web[geoid][indicator_id] = {"value": value, "benchmark": benchmark, "relative_percent": relative, "raw_bin": raw_bin, "class_label": label, "status": status, "moe": record["moe"], "quality_note": quality_note}
        with (outputs_dir / f"classification_{year}.csv").open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=out_fields)
            writer.writeheader()
            writer.writerows(year_records)
        (class_dir / f"classification_{year}.json").write_text(json.dumps(year_web, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
        all_quality.append({"year": year, "check": "Classification coverage", "status": "INFO", "count": sum(item["status"] == "classified" for item in year_records), "details": f"Classified indicator-tract cells out of {len(year_records)}; missing cells are retained as unclassified."})
    with (outputs_dir / "classification_all_years.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(all_records)
    with (outputs_dir / "city_benchmarks.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(benchmarks_rows[0]))
        writer.writeheader()
        writer.writerows(benchmarks_rows)
    with (outputs_dir / "data_quality_report.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=("year", "check", "status", "count", "details"))
        writer.writeheader()
        writer.writerows(all_quality)

    (website_data_dir / "indicator_metadata.json").write_text(json.dumps({"indicators": INDICATORS, "bins": [{"raw_bin": i + 1, "range": ["< 50%", "50% to < 75%", "75% to 125% inclusive", "> 125% to 150% inclusive", "> 150%"][i], "positive_label": BIN_LABELS[i], "negative_label": BIN_LABELS[4 - i], "color_by_label": COLORS} for i in range(5)]}, indent=2, ensure_ascii=False), encoding="utf-8")
    for year in YEARS:
        (website_data_dir / f"classification_{year}.json").write_text((class_dir / f"classification_{year}.json").read_text(encoding="utf-8"), encoding="utf-8")
    prep_report = json.loads((ROOT / "data" / "source_preparation_report.json").read_text(encoding="utf-8"))
    prep_report["classification_output"] = "outputs/tables/classification_all_years.csv"
    prep_report["benchmark_output"] = "outputs/tables/city_benchmarks.csv"
    prep_report["quality_report"] = "outputs/tables/data_quality_report.csv"
    (ROOT / "data" / "source_preparation_report.json").write_text(json.dumps(prep_report, indent=2), encoding="utf-8")
    print(json.dumps({"classification_rows": len(all_records), "years": {str(y): len(source_by_year[y]) for y in YEARS}, "indicators": len(INDICATORS), "benchmarks": len(benchmarks_rows), "quality_checks": len(all_quality)}, indent=2))


if __name__ == "__main__":
    main()
