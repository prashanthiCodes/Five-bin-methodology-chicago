"""Prepare renter counts from the copied master workbooks."""
import shutil
from pathlib import Path
from enrich_renter_counts import run as enrich

ROOT=Path(__file__).resolve().parents[1]

def run():
    source=ROOT/"data/source"
    baseline=source/"legacy"
    for year in (2014,2019,2024):
        backup=baseline/f"acs_tract_inputs_{year}_before_renter.csv"
        if backup.exists():
            shutil.copy2(backup,source/f"acs_tract_inputs_{year}.csv")
    enrich()

if __name__=="__main__":
    run()