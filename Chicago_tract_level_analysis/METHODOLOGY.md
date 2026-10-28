# Internal methodology

## Data, years, and geography

The project uses 2014, 2019, and 2024 tract estimates. The source data have 793, 793, and 792 unique valid GEOIDs, with 777 GEOIDs shared by all three. The 2014/2019 ACS datasets and TIGER boundaries use 2010 vintage; 2024 uses 2020 vintage. The private GEOID membership and exception tables list every ID and join.

The price workbook has 789 unique GEOIDs per year. Its 2014, 2019, and 2024 IDs match the 2020 boundary set except that three 2020 boundary tracts have no workbook row. The 2014/2019 price IDs do not match the 2010-vintage ACS tract universe in 12 cases; 16 2010-vintage ACS IDs have no corresponding price row. The workbook does not state a boundary vintage; 2020 is inferred from its GEOID set. House prices are therefore mapped to 2020 polygons for all workbook years, never joined to the 2010 geometry by coincident GEOID. The 2014/2019 ACS indicators remain on 2010 polygons. GEOID equality alone does not prove polygon equality. No crosswalk was applied.

## Classification method

For classified measures:

Relative percentage = (tract value / same-year Chicago benchmark) × 100.

Exact relative bins:
- Below 50%: Very Low
- 50% to below 75%: Low
- 75% through 125%, inclusive: Middle
- Above 125% through 150%, inclusive: High
- Above 150%: Very High

For positive-direction indicators, labels follow that threshold order. For negative-direction indicators, labels are reversed. Population aged 10–17, population aged 65+, and renter share are neutral. Their labels follow the standard threshold order: Very Low, Low, Middle, High, Very High. They have no direction; the bins describe relative levels and do not imply desirability.

Share benchmarks are ratios of summed compatible numerators to summed denominators among valid Chicago tracts. The summary CSV reports the least (minimum) and highest (maximum) valid tract values, unweighted arithmetic mean, and median separately from that pooled rate. `outputs/tables/indicator_value_extremes_by_year.csv` presents the least and highest value for every indicator-year with valid and missing tract counts. Extremes are taken across valid Chicago census tracts, in the indicator's stated unit; share extrema are percentages, counts are raw counts, and monetary measures retain currency units. Counts retain the prior unweighted mean of tract counts as the comparison reference. Median household income retains the prior household-weighted median of tract medians; it is not the official direct ACS estimate for Chicago city. House price uses the workbook's median across valid tract measures; this is not a transaction-level city median. These limitations are recorded with each benchmark.

## Measures and directions

| Indicator | Formula or source | Direction |
|---|---|---|
| Bachelor's Degree or Higher Attainment Share | Pop_Edu_BachAbove_E / Total_Pop_25Over_E × 100 | Positive |
| Median Household Income | Supplied tract median | Positive |
| Median House Price | Workbook's Neighbourhood Median House Value | Positive |
| Owner-Occupied Housing Share | Owner units / total occupied units × 100 | Positive |
| Households with Income $100,000 or More | Count / total households × 100 | Positive |
| Housing Units Built 2000 or Later | Tract count | Positive |
| Population Aged 65 or Older | Count / total population × 100 | Neutral |
| Population Aged 10–17 | Count / total population × 100 | Neutral |
| Population Below Poverty | People below poverty / total tract population × 100 | Negative |
| Housing Units Built 1939 or Earlier | Tract count | Negative |
| Vacant Housing Units | Tract count | Negative |
| Cost-Burdened Households | (owner + renter burdened households) / (owner + renter households with applicable housing-cost/income data) × 100 | Negative |
| Renter-Occupied Housing Share | Renter-occupied units / total occupied units × 100 | Neutral |

The renter count is extracted from the local master workbooks and appended as Total_Rent_HH_E.x. All shared fields match the filtered inputs on every matched GEOID; owner + renter counts equal total occupied units in every matched row. Coverage: 793/793 in 2014, 793/793 in 2019, and 789/792 in 2024. Three unmatched 2024 rows remain blank. The source field labels align with the requested B25003 concepts; the compiler's original table IDs/codebook were not supplied, so field-level lineage remains a review limitation.

Cost burden uses a household denominator, not population. Its component field names distinguish owner and renter counts, but table IDs/codebook for the supplied master workbook are absent; confirm the original mapping before treating source lineage as fully verified.

## Bachelor's degree or higher source mapping

The exact bachelor's-only field B15003_022E was not present in the supplied tract CSVs. At the user's direction, the map now uses the available `Pop_Edu_BachAbove_E` numerator and `Total_Pop_25Over_E` denominator. The numerator is labeled bachelor's degree or higher and includes master's, professional, and doctoral degree holders; it must not be read as bachelor's-only. The source workbook has no ACS table IDs or codebook, so this field mapping remains a provenance review item. The supplied fields are populated for all tract rows. Values pass count bounds (`0 ≤ numerator ≤ denominator`) where the denominator is positive. Three 2024 records have a zero 25+ denominator and remain invalid/unclassified. No values are inferred or copied across years.
## House-price workbook

The workbook Tract_Level_Sales_Weighted_Audit.xlsx contains sheets 2014, 2019, and 2024, each with 789 unique GEOIDs and no duplicates or malformed IDs. The selected field Neighbourhood Median House Value is a sales-count-weighted average of SFH_Median_Hp and TwoFour_Median_Hp. The formula matched all 2,293 valid rows checked. This is the workbook's tract measure, not a pooled median of all sales. The workbook does not state currency or source sharing terms; USD is assumed from context and remains unverified.

Valid price values are 763 (2014), 766 (2019), and 764 (2024); flagged/zero/missing counts are 26, 23, and 25. No year is copied to another. Workbook benchmark medians of valid tract measures are $172,000, $276,833.33, and $378,500. The private audit compares each year's workbook GEOIDs with the ACS files and 2020 boundary; unmatched records remain visible there. Price data are excluded from docs/ pending approval to share derived workbook values.

## Data validity and summary outputs

Share values are exported in percentage points; raw numerator and denominator counts remain separate. Population counts and percentages are both available in map tooltips for child, age-65, poverty, renter-share, and cost-burden measures where source data permit. Monetary values use currency formatting.

Missing inputs stay blank. For shares, missing counts/denominators remain missing; nonpositive denominators, negative counts, or numerator greater than denominator are invalid. Invalid and missing counts are reported separately. No imputation is performed.

outputs/tables/summary_statistics_by_indicator_year.csv has one row per indicator/year, including least/minimum and highest/maximum valid tract values, mean, median, benchmark value and definition, unit, valid/missing/invalid counts, and benchmark coverage. `outputs/tables/indicator_value_extremes_by_year.csv` is the plain-language range view. outputs/tables/city_benchmarks.csv is the benchmark-only view. outputs/tables/classification_*.csv retain every tract-indicator row including missing/unclassified rows. Detailed GEOID and source audits are private under outputs/internal/.

ACS 5-year estimates span five years and include sampling error. This build does not propagate margins of error through derived indicators. The tract years are not a harmonized panel. No composite score, typology, or additional numeric score is created.