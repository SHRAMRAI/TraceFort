"""Make sample auction houses on top of real ZIP-code home values.

    python3 generate_data.py            # DFW     -> listings.csv
    python3 generate_data.py houston    # Houston -> listings_houston.csv (trial area)

Real:      home value by ZIP + bedrooms (Zillow ZHVI, Sep 2026), ZIP locations (Census 2025 Gazetteer).
Generated: the houses themselves and their auction details (no public source has those).
Same seed (42) -> same file every run.

Raw downloads live in data/raw/ (~250 MB, not in git). They are boiled down to
data/zip_values.csv (small, in git), so teammates don't need the raw files.
"""
import csv
import math
import random
import sys
from pathlib import Path

from estimates import estimate_value, repair_cost

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
ZIP_TABLE = ROOT / "data" / "zip_values.csv"

# Each market: every metro ZIP that Zillow prices for 2, 3 and 4 bedrooms and that sits inside the map's box.
# 7 homes per ZIP + extra in Arlington (the demo city). New market = one line here + a box in app.py MARKETS.
METROS = {   # area: (Zillow metro name contains, (south, north, west, east)) — boxes match app.py
    "dfw": ("Dallas-Fort Worth", (32.45, 33.30, -97.60, -96.50)),
    "houston": ("Houston-The Woodlands", (29.40, 30.20, -95.90, -94.90)),
}
HOMES_PER_ZIP = 7
DEMO_BOOST = {"76010": 25, "76013": 13, "76017": 13}   # Arlington (76010 = cheapest, most foreclosures)

TEAM_COLUMNS = ["id", "address", "city", "zip", "beds", "baths", "sqft", "year_built",
                "condition", "opening_bid", "auction_date", "lat", "lon"]
EXTRA_COLUMNS = ["occupied", "interior_inspected", "roof_issue", "foundation_issue"]  # auction facts the app uses
# Chance of a roof / foundation problem by condition. DFW: hail hits roofs, clay soil moves foundations.
ROOF_CHANCE = {"light": 0.0, "medium": 0.25, "heavy": 0.60}
FOUNDATION_CHANCE = {"light": 0.0, "medium": 0.10, "heavy": 0.40}

# Texas foreclosure sales happen on the first Tuesday of the month.
AUCTION_DATES = ["2026-12-01", "2027-01-05", "2027-02-02"]
# Opening bid as % of est. value. Team spec said 55-80%; widened at the low end so ~1 in 4 homes is a
# workable flip under the 70% rule (value x 0.70 - repairs), otherwise Investor Mode is always empty.
# Distressed auction homes really do open far below market, heavy-repair ones most of all.
OPENING_PCT = {"light": (0.58, 0.80), "medium": (0.48, 0.72), "heavy": (0.32, 0.62)}
STREETS = ["Odyssey Ln", "Ithaca Ct", "Penelope Dr", "Argos Way", "Athena Blvd", "Mentor St",
           "Telemachus Ave", "Aegean Trl", "Calypso Cir", "Laurel Bow Rd", "Phaeacia Pkwy", "Olive Tree Ln"]
SQFT = {2: (850, 1300), 3: (1150, 1950), 4: (1700, 2700)}
BATHS = {2: ([1, 1.5, 2], [5, 2, 3]), 3: ([1, 1.5, 2, 2.5], [15, 15, 55, 15]), 4: ([2, 2.5, 3], [45, 25, 30])}
SPREAD_MILES = 1.2   # ponytail: houses scattered in a circle around the ZIP's center; can spill past the ZIP edge


def in_box(box, lat, lon):
    s, n, w, e = box
    return s <= lat <= n and w <= lon <= e


def market_of(metro, lat, lon):
    """Which market a Zillow ZIP belongs to, or None."""
    return next((a for a, (name, box) in METROS.items() if name in metro and in_box(box, lat, lon)), None)


def build_zip_table():
    """Raw Zillow + Census files -> data/zip_values.csv (zip, city, beds, zhvi, as_of, lat, lon).
    Keeps every ZIP of every market in METROS that sits inside its map box and is priced for 2, 3 and 4 beds."""
    centers = {}
    with open(next(RAW.glob("*Gaz_zcta_national.txt"))) as f:
        for r in csv.DictReader(f, delimiter="|"):
            r = {k.strip(): v.strip() for k, v in r.items()}
            centers[r["GEOID"]] = (float(r["INTPTLAT"]), float(r["INTPTLONG"]))
    rows = []
    for beds in (2, 3, 4):
        with open(RAW / f"zhvi_{beds}bed.csv") as f:
            reader = csv.reader(f)
            head = next(reader)
            for r in reader:
                z, metro = r[2], r[7]
                if z not in centers or not market_of(metro, *centers[z]):
                    continue
                # latest month that has a value
                i, v = next(((i, x) for i, x in reversed(list(enumerate(r))) if x and i >= 9), (None, None))
                if v:
                    lat, lon = centers[z]
                    rows.append({"zip": z, "city": r[6], "beds": beds, "zhvi": round(float(v)),
                                 "as_of": head[i], "lat": lat, "lon": lon})
    beds_by_zip = {}
    for r in rows:
        beds_by_zip.setdefault(r["zip"], set()).add(r["beds"])
    rows = [r for r in rows if beds_by_zip[r["zip"]] == {2, 3, 4}]   # all three sizes
    with open(ZIP_TABLE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["zip", "city", "beds", "zhvi", "as_of", "lat", "lon"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["zip"], r["beds"])))
    print(f"{len(rows)} ZIP x bedroom values -> {ZIP_TABLE}")


ZIP_CENTERS = ROOT / "data" / "zip_centers_tx.csv"


def build_tx_zip_centers():
    """Census ZIP centers for every Texas ZIP (750xx-799xx, 885xx) -> data/zip_centers_tx.csv.
    Lets a buyer type their work ZIP so drive times start from there (we store the ZIP, never GPS)."""
    with open(next(RAW.glob("*Gaz_zcta_national.txt"))) as f, open(ZIP_CENTERS, "w", newline="") as out:
        w = csv.writer(out)
        w.writerow(["zip", "lat", "lon"])
        n = 0
        for r in csv.DictReader(f, delimiter="|"):
            r = {k.strip(): v.strip() for k, v in r.items()}
            z = r["GEOID"]
            if "75000" <= z <= "79999" or z.startswith("885"):
                w.writerow([z, round(float(r["INTPTLAT"]), 5), round(float(r["INTPTLONG"]), 5)])
                n += 1
    print(f"{n} Texas ZIP centers -> {ZIP_CENTERS}")


def load_zip_table():
    with open(ZIP_TABLE) as f:
        rows = list(csv.DictReader(f))
    beds_by_zip, info = {}, {}
    for r in rows:
        beds_by_zip.setdefault(r["zip"], []).append(int(r["beds"]))
        info[r["zip"]] = (r["city"], float(r["lat"]), float(r["lon"]))
    return beds_by_zip, info


def condition_for(rng, year):
    if year < 1970:
        weights = [25, 40, 35]
    elif year < 1995:
        weights = [40, 40, 20]
    else:
        weights = [60, 30, 10]
    return rng.choices(["light", "medium", "heavy"], weights)[0]


def make_house(rng, hid, zip_code, beds_ok, city, c_lat, c_lon, used_addresses):
    beds = rng.choices([b for b in (2, 3, 4) if b in beds_ok],
                       [w for b, w in ((2, 20), (3, 55), (4, 25)) if b in beds_ok])[0]
    sqft = round(rng.randint(*SQFT[beds]), -1)
    year = rng.randint(1948, 2018)
    condition = condition_for(rng, year)
    value = estimate_value(zip_code, beds, sqft)
    opening = int(round(value * rng.uniform(*OPENING_PCT[condition]) / 500) * 500)
    occupied = int(rng.random() < (0.35 if condition == "heavy" else 0.20))
    inspected = 0 if occupied else int(rng.random() < 0.6)

    r, t = SPREAD_MILES * math.sqrt(rng.random()), rng.uniform(0, 2 * math.pi)   # uniform in a disk
    lat = c_lat + r * math.cos(t) / 69.0
    lon = c_lon + r * math.sin(t) / (69.0 * math.cos(math.radians(c_lat)))

    address = None
    while address is None or address in used_addresses:
        address = f"{rng.randint(100, 9899)} {rng.choice(STREETS)}"
    used_addresses.add(address)
    baths, auction_date = rng.choices(*BATHS[beds])[0], rng.choice(AUCTION_DATES)

    # Separate random stream so adding these columns didn't change any of the houses above.
    issues = random.Random(f"issues-{zip_code}-{hid}")
    roof = int(issues.random() < ROOF_CHANCE[condition])
    foundation = int(issues.random() < FOUNDATION_CHANCE[condition])

    return {"id": hid, "address": address, "city": city, "zip": zip_code, "beds": beds,
            "baths": baths, "sqft": sqft, "year_built": year,
            "condition": condition, "opening_bid": opening, "auction_date": auction_date,
            "lat": round(lat, 5), "lon": round(lon, 5), "occupied": occupied, "interior_inspected": inspected,
            "roof_issue": roof, "foundation_issue": foundation}


def area_counts(area, info):
    """{zip: houses to make}: every ZIP in the table inside the market's box (no raw files needed)."""
    box = METROS[area][1]
    zips = sorted(z for z, (_, lat, lon) in info.items() if in_box(box, lat, lon))
    return {z: DEMO_BOOST.get(z, HOMES_PER_ZIP) for z in zips}


def generate(area):
    rng = random.Random(42)
    beds_by_zip, info = load_zip_table()
    houses, used = [], set()
    for zip_code, n in area_counts(area, info).items():
        if zip_code not in info:
            print(f"skipping {zip_code}: no Zillow data")
            continue
        city, c_lat, c_lon = info[zip_code]
        for _ in range(n):
            houses.append(make_house(rng, len(houses) + 1, zip_code, beds_by_zip[zip_code], city, c_lat, c_lon, used))
    return houses


def demo_matches(houses, city="Arlington", budget=180000, min_beds=3, ok=("light", "medium")):
    """Prajita's example prefs. Strict = opening bid + repairs must fit the budget."""
    base = [h for h in houses if h["city"] == city and h["beds"] >= min_beds and h["condition"] in ok]
    loose = [h for h in base if h["opening_bid"] <= budget]
    strict = [h for h in loose if h["opening_bid"] + repair_cost(h["sqft"], h["condition"], h["roof_issue"],
                                                                h["foundation_issue"]) <= budget]
    return loose, strict


if __name__ == "__main__":
    area = sys.argv[1] if len(sys.argv) > 1 else "dfw"
    if RAW.exists() and any(RAW.glob("zhvi_*bed.csv")):
        build_zip_table()
        build_tx_zip_centers()
    houses = generate(area)
    out = ROOT / ("listings.csv" if area == "dfw" else f"listings_{area}.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TEAM_COLUMNS + EXTRA_COLUMNS)
        w.writeheader()
        w.writerows(houses)
    print(f"{len(houses)} houses -> {out}")

    # Self-checks
    assert len({h["address"] for h in houses}) == len(houses)
    assert all(h["condition"] in OPENING_PCT for h in houses)
    if area == "dfw":
        # Real-world finding: $180k cash rarely covers opening bid + repairs on an Arlington 3-bed
        # (typical value ~$225k). So the demo needs >=5 by opening bid at $180k, and >=5 strict at $200k.
        print("demo case (Arlington, 3+ beds, light/medium):")
        for budget in (180000, 200000, 220000):
            loose, strict = demo_matches(houses, budget=budget)
            print(f"  ${budget:,}: {len(loose)} by opening bid, {len(strict)} if repairs must fit too")
        assert len(demo_matches(houses, budget=180000)[0]) >= 5, "too few demo matches at $180k"
        assert len(demo_matches(houses, budget=200000)[1]) >= 5, "too few strict demo matches at $200k"
    print("self-checks passed")
