# Map source, data, and references

This is a private source inventory for the Chicago tract map. The map was assembled from the project files below; there was no single prompt or outside map-generation text. The HTML, CSS, and JavaScript source is in `scripts/map_template.html`.

## Map code

- `scripts/map_template.html` — complete page markup, inline CSS, and inline JavaScript. Leaflet creates the map, loads the static classification JSON and tract GeoJSON, colors polygons, builds selectors and legends, and shows tooltips.
- `scripts/build_site.py` — substitutes relative data paths and review notices into the template and writes the private root `index.html` and public-review `docs/index.html`.
- `scripts/build_project.py` — runs input preparation, analysis, and site generation.
- `scripts/prepare_inputs.py` and `scripts/enrich_renter_counts.py` — use the locally supplied ACS-derived master workbooks to prepare the tract inputs.
- `scripts/update_analysis.py` — indicator definitions, formulas, benchmarks, bin thresholds, and year-specific output generation.
- `scripts/validate_update.py` — formula, GEOID, bin, and deployment-file checks.

The summary outputs include `outputs/tables/summary_statistics_by_indicator_year.csv` and `outputs/tables/indicator_value_extremes_by_year.csv`. The latter reports the least and highest valid tract value across all Chicago tracts for every indicator and year, with units and valid/missing/invalid counts.

The page uses Leaflet 1.9.4 CSS and JavaScript from `https://unpkg.com/leaflet@1.9.4/`. It uses Leaflet's GeoJSON polygon support. There is no external basemap tile layer; the polygons are drawn over the plain page background. Runtime data are local relative-path files, so the browser does not call Census APIs or require Python.

## Files loaded by the review website

- `docs/assets/data/indicator_metadata.json`
- `docs/assets/data/classification_2014.json`, `classification_2019.json`, and `classification_2024.json`
- `docs/data/boundaries/chicago_tracts_2010.geojson` for 2014/2019 ACS map data
- `docs/data/boundaries/chicago_tracts_2020.geojson` for 2024 ACS data
- Leaflet CSS/JavaScript from the HTTPS CDN above

These classification files contain the filtered tract values used by the website. The full research inputs, workbook, analysis scripts, internal reports, and house-price values are not part of `docs/`.

## Local inputs used to prepare map data

- `data/source/acs_tract_inputs_2014.csv`, `acs_tract_inputs_2019.csv`, and `acs_tract_inputs_2024.csv` — supplied ACS-derived tract fields. Their originating workbook lacks complete table-ID/codebook lineage; keep the source files and derived research outputs private pending source-sharing review.
- `data/raw/acs_master_inputs/acs_5yr_2014_master.xlsx`, `acs_5yr_2019_master.xlsx`, and `acs_5yr_2024_master.xlsx` — local master workbooks used to enrich renter counts. These remain private because the workbook's source/license metadata is incomplete.
- `data/raw/tl_2010_17031_tract10.zip` and `data/raw/tl_2020_17_tract.zip` — local Census TIGER/Line tract geometry inputs, converted to the private and website GeoJSON files.
- `data/source/Tract_Level_Sales_Weighted_Audit.xlsx` — user-provided house-price workbook. Its derived price measure is withheld from the public review package pending sharing approval.

## Bachelor's degree or higher source field

The exact bachelor-only formula `B15003_022E / B15003_001E × 100` cannot be calculated from the supplied fields because the exact `_022E` column is absent. At the user's direction, the map instead uses `Pop_Edu_BachAbove_E / Total_Pop_25Over_E × 100`, a source field labeled bachelor's degree or higher. It includes master's, professional, and doctoral degrees, so the map label and tooltip state ‘Bachelor's Degree or Higher Attainment Share.’ The supplied master workbook contains these fields and their values match the prepared tract inputs; however, the workbook has no ACS table-ID/codebook lineage. Count bounds pass where denominator is positive. Three 2024 records with a zero 25+ denominator are invalid and remain unclassified; values are not inferred. The measure is not bachelor-only.

A missing `class_label` is drawn gray (`#b8c0c2`). The map now starts with Bachelor's Degree or Higher Attainment Share; it has classified values in 2014, 2019, and 2024 where the 25+ denominator is positive. Three 2024 tracts remain unclassified because that denominator is zero. Other indicators with no classified values show a `No data` legend explanation.

## References

- ACS 2014 Table B15003 variable metadata: <https://api.census.gov/data/2014/acs/acs5/groups/B15003.html>
- ACS 2019 Table B15003 variable metadata: <https://api.census.gov/data/2019/acs/acs5/groups/B15003.html>
- ACS 2024 Table B15003 variable metadata: <https://api.census.gov/data/2024/acs/acs5/groups/B15003.html>
- ACS 5-year products and tract coverage: <https://www.census.gov/data/developers/data-sets/acs-5year.html>
- Census TIGER/Line files and documentation: <https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html>
- Leaflet 1.9.4 API reference: <https://leafletjs.com/reference.html>
- Project data lineage and license/sharing notes: `DATA_SOURCES_AND_LICENSES.md`
- Five-bin definitions and geography methodology: `METHODOLOGY.md`

The public review page retains Census TIGER/Line attribution in `docs/ATTRIBUTION.txt`. No files were pushed or published by this update.
