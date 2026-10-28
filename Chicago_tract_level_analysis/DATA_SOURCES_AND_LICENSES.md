# Internal data sources, license, and sharing review

## Supplied ACS-derived tract data

The analysis checkout contained prepared tract CSVs but not a complete field-level source inventory or codebook. I copied the corresponding local ACS master workbooks into data/raw/acs_master_inputs for the fields used here. The 2014 and 2019 master workbook values match all existing filtered fields on all 793 GEOIDs; the 2024 workbook matches 789 of 792 rows. Three 2024 IDs have no corresponding master-workbook row. These are left blank for the renter count.

The files appear to contain aggregate ACS estimates. The Census statistics are public, but the compiler workbook does not provide table IDs, a codebook, or a workbook-level license. Keep these inputs and derived files private until source lineage and sharing terms are confirmed. The exact bachelor-only B15003_022E field is absent. At the user's direction the map uses the supplied `Pop_Edu_BachAbove_E` field for a clearly labeled bachelor's-or-higher measure; it includes postgraduate degrees and remains subject to source-lineage review.

Official ACS table metadata:
- [2014 ACS 5-year Table B15003](https://api.census.gov/data/2014/acs/acs5/groups/B15003.html)
- [2019 ACS 5-year Table B15003](https://api.census.gov/data/2019/acs/acs5/groups/B15003.html)
- [2024 ACS 5-year Table B15003](https://api.census.gov/data/2024/acs/acs5/groups/B15003.html)
- [ACS 5-year release and tract availability](https://www.census.gov/data/developers/data-sets/acs-5year.html)

B25003 is the tenure table used for renter share: B25003_003E is renter-occupied housing units, and B25003_001E is total occupied housing units. The imported field names Total_Rent_HH_E.x and Total_HH_E.x have been checked against the source workbook and the owner + renter sum identity. The source workbook itself lacks official variable IDs, so this mapping still needs lineage confirmation.
- [2014 ACS 5-year Table B25003](https://api.census.gov/data/2014/acs/acs5/groups/B25003.html)
- [2019 ACS 5-year Table B25003](https://api.census.gov/data/2019/acs/acs5/groups/B25003.html)
- [2024 ACS 5-year Table B25003](https://api.census.gov/data/2024/acs/acs5/groups/B25003.html)

ACS B25106 covers tenure by housing costs as a percentage of household income. The project combines owner and renter cost-burdened household counts and divides by owner and renter households with applicable/income-complete cost data. The local source files do not include table IDs/codebook for the component fields; source lineage remains a review item.
- [2024 ACS 5-year Table B25106](https://api.census.gov/data/2024/acs/acs5/groups/B25106.html)

The Census Bureau says ACS 5-year estimates are available at tract level and current API data queries require a key. No ACS API data were downloaded for the missing bachelor-only field. The user-approved bachelor's-or-higher measure uses the existing compiler field; it is not represented as an exact B15003_022E estimate.

## House-price workbook

The provided Tract_Level_Sales_Weighted_Audit.xlsx is stored only under data/source and private derived summaries under outputs/. It has three year sheets, numeric values and sales counts, and no declared currency, source system, boundary vintage, license, or public-sharing terms. All its GEOIDs match 2020 TIGER boundaries; 2020 vintage is inferred because the workbook does not state it. The sales-weighted field is not a pooled transaction median. Values are excluded from docs/ pending explicit sharing approval.

## TIGER/Line geometry and attribution

2010 TIGER/Line tract polygons are used for 2014/2019 ACS data, and 2020 TIGER/Line polygons for 2024 ACS data. Price workbook values use 2020 boundaries for every workbook year based on exact GEOID set membership. Retain Census attribution and the statistical-geography/accuracy disclaimer.
- [Census TIGER/Line files and documentation](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html)
- [Census citation policy](https://www.census.gov/about/policies/citation.html)

## Existing public repository status

The inspected source checkout is associated with the public repository Five-Bins-Tract-level-Chicago. It already exposes research scripts, detailed methodology and data-quality reports, and tract-level ACS CSVs. The source checkout was left unchanged in this task. The separate project created here has no Git history; its .gitignore excludes local research data, scripts, outputs, and the full internal map, leaving docs/ as the review package.

.gitignore does not remove already committed files from another repository. A new deletion commit only removes the current branch version; previous Git history remains. No remote deletion, history rewrite, push, or Pages configuration was performed.