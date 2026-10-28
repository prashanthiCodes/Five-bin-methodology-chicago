# Methodology

## Scope and inputs

This project classifies 12 tract-level indicators for Chicago for 2014, 2019, and 2024. The 2014 and 2019 workbook inputs refer to 2010 census tracts; 2024 refers to 2020 census tracts. The project does not crosswalk the two vintages, so tract-to-tract changes across all three years are not a fixed-geography panel.

The tract estimate fields come from the locally supplied ACS tract workbooks documented in `data/source/acs_tract_inputs_YEAR.csv`. The original workbooks are not copied into this project. The 2024 workbook labels its valid 11-digit GEOID field `#NUM!`; that source header is retained as metadata and validated GEOID values are used for joins. Home-value proxy estimates are extracted from the Census ACS Summary Files. Boundaries are official Census TIGER/Line tract polygons.

## Indicators and directions

| Indicator | Tract value | Direction |
| --- | --- | --- |
| `Bach_plus_share` | `Pop_Edu_BachAbove_E / Total_Pop_25Over_E` | Positive |
| `Median_household_income` | `HH_Med_Inc_E` | Positive |
| `Median_house_price` | ACS B25077 tract median owner-occupied housing value; proxy for sale price | Positive |
| `Owner_occupied_share` | `Total_Own_HH_E.x / Total_HH_E.x` | Positive |
| `Income_100k_plus_share` | `HH_Inc_100K_More_E / Total_HH_E.x` | Positive |
| `HU_Built_2000_Later_E` | Direct tract count | Positive |
| `Age_65_over_share` | `Pop_Age_65Over_E / Total_Pop_E` | Negative |
| `Age_10_17_share` | `Pop_Age_10to17_E / Total_Pop_E` | Negative |
| `Poverty_Share` | 2014/2019: `Pop_Below_Pov_E / Total_Pop_Pov_E`; 2024: direct `Pop_Below_Pov_Share` | Negative |
| `HU_Built_1939_Earlier` | Direct tract count (`HU_Built_1939_Earlier_E`) | Negative |
| `Total_Vac_HU_E` | Direct tract count | Negative |
| `HH_Cost_Burden_Share` | (`Own_HH_Cost_Burden_E` + `Rent_HH_Cost_Burden_E`) / (`Total_Own_HH_IncComp_E` + `Total_Rent_HH_IncComp_E.x`) | Negative |

Shares remain fractions in the CSV outputs and are displayed as percentages in the website. Counts are not normalized by tract area or population; their benchmark is the mean count per Chicago tract.

## Chicago benchmark for each year

Each tract is compared with a benchmark calculated from that same year’s Chicago tract inputs:

- Share indicators: sum of the source numerator divided by sum of the source denominator across valid tracts. Cost burden uses summed burden counts over summed income-complete household counts.
- Median household income: weighted median of tract median estimates, weighted by total households (`Total_HH_E.x`). This is a tract-estimate summary, not a pooled microdata median.
- Home value: weighted median of tract ACS B25077 medians, weighted by owner-occupied households (`Total_Own_HH_E.x`). It is a proxy benchmark, not a pooled city sale price.
- Count indicators: arithmetic mean across Chicago tracts with valid counts.
- Poverty in 2014 and 2019: sum of persons below poverty divided by sum of the source poverty population denominator.
- Poverty in 2024: the denominator field `Total_Pop_Pov_E` is absent. Tract estimates use the supplied `Pop_Below_Pov_Share` directly. For the incomplete city benchmark only, a denominator is inferred as `Pop_Below_Pov_E / Pop_Below_Pov_Share` for positive valid shares with a usable count. Missing, zero, or out-of-range shares cannot provide a benchmark weight. No missing tract share is imputed.

Dollar estimates are nominal and are not adjusted for inflation. ACS 5-year estimates summarize overlapping five-year periods (2010–2014, 2015–2019, and 2020–2024), not point-in-time observations.

## Relative percentages and bins

`relative_percent = tract_value / same_year_Chicago_benchmark * 100`.

The exact raw ranges are:

1. below 50%;
2. 50% to below 75%;
3. 75% through 125%, inclusive;
4. above 125% through 150%, inclusive;
5. above 150%.

For positive-direction indicators, those ranges are labeled Very Low, Low, Middle, High, and Very High, in order. Negative-direction indicators reverse those labels. Missing or invalid tract values and unavailable benchmarks remain unclassified. The CSV retains both the raw bin number and the direction-adjusted category.

## Validation and limits

The pipeline checks that GEOIDs are unique 11-digit Cook County tract identifiers beginning `17031`, that each source tract set joins one-to-one with its matching TIGER/Line geometry, and that there are no duplicate boundary GEOIDs. The 2010/2020 boundary vintage is selected by year. See `outputs/tables/data_quality_report.csv` for counts and warnings and `outputs/tables/city_benchmarks.csv` for every benchmark and its method.

The source workbooks do not provide MOEs for most selected fields in the extracted schema; their sampling uncertainty is not propagated through the ratios, weighted medians, or bins. ACS B25077 MOEs are retained in the tract classification output, but they are not used to alter bins. Bins therefore describe point estimates and do not test whether estimates differ significantly. Tract population, household counts, land area, and boundary changes can affect count comparisons. The 2024 poverty city benchmark is explicitly incomplete. These constraints should accompany interpretation and any public release.
