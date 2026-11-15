"""Download Walmart + Costco locations from OpenStreetMap into data/stores.csv.

Run once per area, before the demo (the app only reads the CSV, never the network):
    python3 fetch_stores.py                      # DFW
    python3 fetch_stores.py 29.4 -95.9 30.2 -94.9 data/stores_houston.csv   # Houston
Args: south west north east [out_csv]. Data (c) OpenStreetMap contributors, ODbL.
"""
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

from estimates import miles

DFW = (32.45, -97.60, 33.30, -96.50)
BRANDS = {"Walmart", "Costco"}
# Only the big store itself. The Walmart study (Pope & Pope) is about full stores, so skip
# Neighborhood Markets, pharmacies, fuel and auto-care points that share the brand tag.
KEEP_SHOPS = {"supermarket", "department_store", "wholesale", "general", "variety_store", "hypermarket"}
SKIP_NAMES = ("Neighborhood Market", "Pharmacy", "Fuel", "Gas", "Auto", "Tire", "Vision", "Optical")


def fetch(bbox):
    s, w, n, e = bbox
    q = f'[out:json][timeout:80];nwr["brand"~"^(Walmart|Costco)$"]({s},{w},{n},{e});out center;'
    # curl, not urllib: python.org Python on macOS often lacks SSL certs until "Install Certificates" is run
    cmd = ["curl", "-sS", "-f", "-m", "120", "-A", "ithaca-hackathon/0.1", "--data-urlencode", f"data={q}",
           "https://overpass-api.de/api/interpreter"]
    for attempt in range(4):  # the free Overpass server rate-limits (HTTP 429) back-to-back calls
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.lstrip().startswith("{"):
            return json.loads(r.stdout)["elements"]
        print(f"Overpass busy ({r.stderr.strip() or 'bad response'}), retrying in {20 * (attempt + 1)}s...")
        time.sleep(20 * (attempt + 1))
    sys.exit("Overpass still failing; data/stores.csv left unchanged. Try again in a few minutes.")


def stores(elements):
    out = []
    for el in elements:
        t = el.get("tags", {})
        name = t.get("name", "")
        if t.get("brand") not in BRANDS or t.get("shop") not in KEEP_SHOPS or any(s in name for s in SKIP_NAMES):
            continue
        lat, lon = el.get("lat") or el["center"]["lat"], el.get("lon") or el["center"]["lon"]
        # OSM often maps one store twice (building + point): drop same brand within 0.25 mi
        if any(s["brand"] == t["brand"] and miles(lat, lon, s["lat"], s["lon"]) < 0.25 for s in out):
            continue
        out.append({"brand": t["brand"], "name": t.get("name", t["brand"]), "lat": round(lat, 6), "lon": round(lon, 6)})
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    bbox = tuple(map(float, a[:4])) if len(a) >= 4 else DFW
    dest = Path(a[4]) if len(a) == 5 else Path(__file__).parent / "data" / "stores.csv"
    rows = stores(fetch(bbox))
    with open(dest, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["brand", "name", "lat", "lon"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} stores -> {dest}", {b: sum(r["brand"] == b for r in rows) for b in BRANDS})
