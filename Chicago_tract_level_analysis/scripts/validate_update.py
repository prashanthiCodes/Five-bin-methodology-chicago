import csv, json, math, statistics, sys, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from update_analysis import YEARS, SPECS, classify, measure, prices

def close(a,b):
 return a is not None and b is not None and math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=1e-6)
def csvrows(path):
 with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
CHECK_COUNT=0
def check(ok,message):
 global CHECK_COUNT
 if not ok:raise AssertionError(message)
 CHECK_COUNT+=1

def main():
 for value,expected in ((49.999,1),(50,2),(74.999,2),(75,3),(125,3),(125.001,4),(150,4),(150.001,5)):
  raw,label=classify(value,"positive");check(raw==expected,f"Positive threshold {value} -> raw bin {expected}")
 check(classify(50,"negative")[1]=="High","Negative labels reverse")
 check(classify(50,"neutral")[1]=="Low","Neutral labels follow threshold order without a direction suffix")
 price_data,price_audit,price_geos=prices()
 summary={(int(r["year"]),r["indicator"]):r for r in csvrows(ROOT/"outputs/tables/summary_statistics_by_indicator_year.csv")}
 extremes={(int(r["year"]),r["indicator"]):r for r in csvrows(ROOT/"outputs/tables/indicator_value_extremes_by_year.csv")}
 check(len(extremes)==39,"Value range table has one row per indicator and year")
 for key,sr in summary.items():
  er=extremes[key]
  check(close(er["least_valid_tract_value"],sr["minimum_tract_value"]) or (er["least_valid_tract_value"]==sr["minimum_tract_value"]==""),f"{key} least tract value matches summary")
  check(close(er["highest_valid_tract_value"],sr["maximum_tract_value"]) or (er["highest_valid_tract_value"]==sr["maximum_tract_value"]==""),f"{key} highest tract value matches summary")
 all_classes=csvrows(ROOT/"outputs/tables/classification_all_years.csv")
 public_meta=json.loads((ROOT/"docs/assets/data/indicator_metadata.json").read_text(encoding="utf-8"))
 public_ids={x["id"] for x in public_meta["indicators"]}
 check("Median_house_price" not in public_ids,"Public metadata excludes unapproved house-price values")
 check(all("prevalence" not in b["neutral_label"].lower() for b in public_meta["bins"]),"Neutral labels use the plain five-bin names")
 check(len(summary)==39,"Summary has one row per 13 indicators and 3 years")
 for y in YEARS:
  source=csvrows(ROOT/f"data/source/acs_tract_inputs_{y}.csv")
  source_by={r["geoid"]:r for r in source}
  source_ids=set(source_by)
  vintage=2020 if y==2024 else 2010
  geo=json.loads((ROOT/f"data/boundaries/chicago_tracts_{vintage}.geojson").read_text(encoding="utf-8"))
  geo_ids={f["properties"]["GEOID"] for f in geo["features"]}
  check(source_ids==geo_ids,f"{y} ACS IDs exactly match {vintage} boundary IDs")
  public_json=json.loads((ROOT/f"docs/assets/data/classification_{y}.json").read_text(encoding="utf-8"))
  check(set(public_json)==geo_ids,f"{y} public JSON GEOIDs exactly match selected geometry")
  check(all("Median_house_price" not in v for v in public_json.values()),f"{y} public JSON excludes price indicator")
  check(all("quality_note" not in rec for tract in public_json.values() for key,rec in tract.items() if key!="_meta"),f"{y} public JSON omits prose quality notes")
  for spec in SPECS:
   ind=spec["id"]; out=[r for r in all_classes if int(r["year"])==y and r["indicator"]==ind]
   expected_ids=set(price_data[y]) if spec["kind"]=="price" else source_ids
   check(len(out)==len(expected_ids) and {r["geoid"] for r in out}==expected_ids,f"{y} {ind} has one output row per source GEOID")
   sr=summary[(y,ind)]
   check(int(sr["total_source_tract_count"])==len(expected_ids),f"{y} {ind} summary tract denominator matches its data universe")
   if spec["kind"]=="price":
    check(all(int(r["boundary_vintage"])==2020 for r in out),f"{y} price classifications use 2020 geometry vintage")
   values=[]
   for rec in out:
    source_row=source_by.get(rec["geoid"],{})
    pd=price_data[y].get(rec["geoid"]) if spec["kind"]=="price" else None
    val,n,d,aux,st=measure(spec,source_row,pd)
    if st=="valid":
     expected_value=val*100 if spec["kind"]=="share" else val
     check(close(rec["tract_value"],expected_value),f"{y} {ind} GEOID {rec['geoid']} value formula")
     values.append(float(rec["tract_value"]))
     if rec["benchmark_value"] not in (None,""):
      rel=expected_value/float(rec["benchmark_value"])*100
      check(close(rec["relative_percent"],rel),f"{y} {ind} GEOID {rec['geoid']} relative formula")
      if rec["relative_percent"] is not None:
       raw,label=classify(rel,spec["direction"])
       check(int(rec["raw_bin"])==raw and rec["class_label"]==label,f"{y} {ind} GEOID {rec['geoid']} bin/direction")
    else:
     check(rec["tract_value"] in ("",None),f"{y} {ind} GEOID {rec['geoid']} missing/invalid stays blank")
   check(int(sr["valid_tract_count"])==len(values),f"{y} {ind} valid tract count")
   if values:
    check(close(sr["minimum_tract_value"],min(values)),f"{y} {ind} minimum")
    check(close(sr["maximum_tract_value"],max(values)),f"{y} {ind} maximum")
    check(close(sr["unweighted_arithmetic_mean_tract_value"],statistics.fmean(values)),f"{y} {ind} unweighted tract mean")
    check(close(sr["median_tract_value"],statistics.median(values)),f"{y} {ind} tract median")
  bachelor=summary[(y,"Bachelor_or_higher_attainment_share")]
  expected_bachelor_valid=789 if y==2024 else len(source)
  expected_bachelor_invalid=3 if y==2024 else 0
  check(int(bachelor["valid_tract_count"])==expected_bachelor_valid,f"{y} bachelor's-or-higher valid tract count")
  check(int(bachelor["invalid_tract_count"])==expected_bachelor_invalid,f"{y} bachelor's-or-higher zero-denominator records remain invalid")
  check(int(bachelor["valid_tract_count"])+int(bachelor["missing_tract_count"])+int(bachelor["invalid_tract_count"])==len(source),f"{y} bachelor's-or-higher source accounting covers all tracts")
 check(int(summary[(2024,"Renter_Occupied_Share")]["missing_tract_count"])==3,"Three unmatched 2024 renter counts remain blank")
 check([x["weight_formula_mismatches"] for x in price_audit]==[0,0,0],"House-price sales-weight formula matches all valid workbook rows")
 check(all(x["cached_matches_computed"] for x in price_audit),"Workbook citywide median matches computed valid-tract median")
 check(all(price_geos[y] <= {f["properties"]["GEOID"] for f in json.loads((ROOT/"data/boundaries/chicago_tracts_2020.geojson").read_text())["features"]} for y in YEARS),"All workbook price GEOIDs match 2020 boundary geometry")
 geoid=csvrows(ROOT/"outputs/internal/geoid_validation_summary.csv")
 check(all(int(x["shared_by_all_three"])==777 for x in geoid),"ACS GEOID report records 777 shared IDs")
 check(public_ids=={s["id"] for s in SPECS if s["kind"]!="price"},"Public map includes all share-cleared non-price indicators")
 docfiles={p.relative_to(ROOT/"docs").as_posix() for p in (ROOT/"docs").rglob("*") if p.is_file()}
 expected={"index.html","README.md","ATTRIBUTION.txt","assets/data/indicator_metadata.json","data/boundaries/chicago_tracts_2010.geojson","data/boundaries/chicago_tracts_2020.geojson"}
 expected|={f"assets/data/classification_{y}.json" for y in YEARS}
 check(docfiles==expected,"docs contains only website data, boundaries, README, and attribution")
 html=(ROOT/"docs/index.html").read_text(encoding="utf-8")
 check("__METADATA_PATH__" not in html and "C:" not in html and "C:/Users/" not in html,"Public HTML has no unresolved/local-drive paths")
 check("https://unpkg.com/leaflet@1.9.4" in html,"Leaflet assets use HTTPS")
 check("prevalence" not in html.lower() and "relative to benchmark" in html.lower(),"Map uses simple benchmark wording without prevalence")
 check("Neutral (no direction)" in html and "Direction: " in html,"Map displays explicit positive, negative, and neutral direction wording")
 check("Bachelor_or_higher_attainment_share" in html and "No data" in html and "gray polygons mean data are missing" in html,"Map defaults to the populated bachelor's-or-higher indicator and explains blank indicators")
 check("Geography and data notes" not in html and "Indicator definition" not in html and "quality_note" not in html,"Map omits the geography/data card and prose quality notes")
 check("Workbook Measure" not in html and "Median House Price (Workbook Measure)" not in html,"Map uses the short house-price label")
 check(all("formula" in i and "definition" not in i for i in public_meta["indicators"]),"Public indicator metadata contains formulas without prose definitions")
 class Quiet(SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
 server=ThreadingHTTPServer(("127.0.0.1",0),lambda *a,**kw:Quiet(*a,directory=str(ROOT/"docs"),**kw))
 th=threading.Thread(target=server.serve_forever,daemon=True);th.start()
 try:
  base=f"http://127.0.0.1:{server.server_address[1]}/"
  for rel in sorted(expected-{"README.md","ATTRIBUTION.txt"}):
   with urlopen(base+rel,timeout=10) as res:
    check(res.status==200,f"Local deployment HTTP asset {rel}")
    if rel.endswith(".json") or rel.endswith(".geojson"):json.loads(res.read())
 finally:
  server.shutdown();server.server_close();th.join(timeout=3)
 report={"status":"PASS","checks":CHECK_COUNT,"years":list(YEARS),"summary_rows":len(summary),"classification_rows":len(all_classes),"public_files":sorted(docfiles)}
 (ROOT/"outputs/internal/validation_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
 print(json.dumps({"status":report["status"],"checks":CHECK_COUNT,"summary_rows":len(summary),"classification_rows":len(all_classes),"public_files":len(docfiles)},indent=2))
if __name__=="__main__":main()
