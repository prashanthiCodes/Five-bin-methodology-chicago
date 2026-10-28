"""Build the internal and relative-path public review pages."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TEMPLATE=ROOT/"scripts/map_template.html"

def build():
    source=TEMPLATE.read_text(encoding="utf-8-sig")
    internal=(source.replace("__METADATA_PATH__","website/assets/data/indicator_metadata.json")
        .replace("__CLASS_PATH__","website/assets/data/classification___YEAR__.json")
        .replace("__BOUNDARY_PATH__","data/boundaries/chicago_tracts___VINTAGE__.geojson")
        .replace("__REVIEW_NOTE__","Internal research preview. Bachelor's indicator uses the available bachelor's-or-higher population field and includes postgraduate degrees."))
    public=(source.replace("__METADATA_PATH__","assets/data/indicator_metadata.json")
        .replace("__CLASS_PATH__","assets/data/classification___YEAR__.json")
        .replace("__BOUNDARY_PATH__","data/boundaries/chicago_tracts___VINTAGE__.geojson")
        .replace("__REVIEW_NOTE__","Local review build only. House-price workbook values are withheld pending approval to share derived data. Supplied ACS-derived field provenance also needs confirmation."))
    (ROOT/"index.html").write_text(internal,encoding="utf-8")
    (ROOT/"docs/index.html").write_text(public,encoding="utf-8")

if __name__=="__main__":
    build()