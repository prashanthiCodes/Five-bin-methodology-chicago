# Private research project notes

The complete research copy is at this project path. The identified Stage 4- Tract level source checkout was left unchanged.

Rebuild prepared renter fields and calculations with:

    python scripts/build_project.py

This runs the renter enrichment against the copied ACS master files, then calculates classifications, summary statistics, internal GEOID audits, and both private/public website data. Run scripts/update_analysis.py directly only after the renter field is already prepared.

Internal outputs are under outputs/tables and outputs/internal. `outputs/tables/indicator_value_extremes_by_year.csv` lists the least and highest valid tract value for each indicator and year. The root index.html is the full research map; it uses local project-relative files. The docs folder is a stripped review package for GitHub Pages and excludes house-price workbook values pending sharing approval.

The exact bachelor-only B15003_022E source field is missing. At the user's direction, the map uses `Pop_Edu_BachAbove_E` as a clearly labeled bachelor's-or-higher measure; it includes graduate degrees, and the source workbook lacks table-ID/codebook provenance. Three 2024 records with a zero 25+ denominator remain invalid. Three 2024 renter counts remain blank because the local master workbook has no matching GEOIDs.

The new project has no Git history. Its .gitignore leaves only docs/, the minimal root README.md, and .gitignore available for future publication. It cannot remove material already committed in the existing public repository.