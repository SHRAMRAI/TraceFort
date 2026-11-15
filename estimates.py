"""Estimates for each house: what it's worth, what repairs cost, how risky it is, what's nearby.

Team contract:  add_estimates(df) -> df with est_value, repair_cost, risk_score (0-100)
Extra columns:  store_name, store_miles, job_center, miles_to_job_center, drive_minutes

    .venv/bin/python estimates.py   # self-checks, then writes homes.csv (+ homes_houston.csv) for app.py

Every rate below is a demo assumption. Say so in Q&A, and tune them after talking to Xome.
"""
import csv
import math
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).parent / "data"

# --- value ---------------------------------------------------------------------------------
# est_value = Zillow typical value for that ZIP + bedroom count, adjusted for size.
# Zillow ZHVI is the middle third of homes, so we treat it as "worth once repaired".
TYPICAL_SQFT = {2: 1100, 3: 1550, 4: 2100}
SIZE_EXPONENT = 0.6          # bigger house = more value, but less than proportional
SIZE_CLAMP = (0.85, 1.20)    # never let size move the value more than -15% / +20%

# --- repairs ($ per sqft, by condition) + big-ticket items ---------------------------------
REPAIR_RATE = {"light": 10, "medium": 25, "heavy": 50}
ROOF_COST = 12000          # roof replacement, typical DFW single-family
FOUNDATION_COST = 15000    # pier-and-beam / slab repair on clay soil

# --- risk score (0 safe -> 100 risky): simple points, easy to explain ----------------------
RISK_CONDITION = {"light": 0, "medium": 20, "heavy": 40}
RISK_OLD = [(1970, 20), (1990, 10)]   # built before 1970: +20, before 1990: +10
RISK_OCCUPIED = 20                    # someone still lives there -> possible eviction
RISK_NOT_INSPECTED = 20               # nobody has seen the inside

# --- commute ---------------------------------------------------------------------------------
# ponytail: drive time to the NEAREST major job center, straight line x road factor / avg speed.
# Real version: ask the user's work address and call Google Routes / openrouteservice ahead of time.
JOB_CENTERS = {
    "Downtown Dallas": (32.7767, -96.7970), "Downtown Fort Worth": (32.7555, -97.3308),
    "Las Colinas": (32.8790, -96.9400), "Arlington / UTA": (32.7299, -97.1150), "Legacy (Plano)": (33.0760, -96.8250),
    "Downtown Houston": (29.7604, -95.3698), "Energy Corridor": (29.7838, -95.6420),
    "Texas Medical Center": (29.7072, -95.3967), "The Woodlands": (30.1658, -95.4613),
}
ROAD_FACTOR = 1.3   # roads are ~30% longer than a straight line
AVG_MPH = 35        # mix of highway and local streets


@lru_cache
def zip_values():
    """{(zip, beds): (city, value)} from data/zip_values.csv (made by generate_data.py)."""
    with open(DATA / "zip_values.csv") as f:
        return {(r["zip"], int(r["beds"])): (r["city"], float(r["zhvi"])) for r in csv.DictReader(f)}


def estimate_value(zip_code, beds, sqft):
    beds = min(max(int(beds), 2), 4)                     # Zillow files we use: 2, 3, 4 bedrooms
    _, base = zip_values()[(str(zip_code), beds)]
    lo, hi = SIZE_CLAMP
    factor = min(max((float(sqft) / TYPICAL_SQFT[beds]) ** SIZE_EXPONENT, lo), hi)
    return int(round(base * factor, -3))                # nearest $1,000


def repair_cost(sqft, condition, roof_issue=0, foundation_issue=0):
    cost = float(sqft) * REPAIR_RATE[condition]
    cost += ROOF_COST * int(roof_issue) + FOUNDATION_COST * int(foundation_issue)
    return int(round(cost, -2))


def risk_score(condition, year_built, occupied=0, interior_inspected=1):
    score = RISK_CONDITION[condition]
    score += next((pts for year, pts in RISK_OLD if int(year_built) < year), 0)
    score += RISK_OCCUPIED if int(occupied) else 0
    score += 0 if int(interior_inspected) else RISK_NOT_INSPECTED
    return min(score, 100)


# --- location helpers ----------------------------------------------------------------------
def miles(lat1, lon1, lat2, lon2):
    """Straight-line distance in miles (haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(a))


@lru_cache
def load_stores():
    """All data/stores*.csv files (DFW, Houston, ...). Missing files -> no stores, never a crash."""
    out = []
    for path in sorted(DATA.glob("stores*.csv")):
        with open(path) as f:
            out += [(r["name"], float(r["lat"]), float(r["lon"])) for r in csv.DictReader(f)]
    return tuple(out)


MAX_STORE_MILES = 25   # farther than this = we have no store data for that area (e.g. Houston file missing)


def nearest_store(lat, lon, stores=None):
    stores = load_stores() if stores is None else stores
    if not stores:
        return None
    d, name = min((miles(lat, lon, s_lat, s_lon), name) for name, s_lat, s_lon in stores)
    return {"name": name, "miles": round(d, 2)} if d <= MAX_STORE_MILES else None


def nearest_job_center(lat, lon):
    d, name = min((miles(lat, lon, *pt), name) for name, pt in JOB_CENTERS.items())
    return name, round(d, 1), int(round(d * ROAD_FACTOR / AVG_MPH * 60))


def _row_estimates(r):
    occupied = r.get("occupied", 0)
    inspected = r.get("interior_inspected", 1)
    store = nearest_store(float(r["lat"]), float(r["lon"]))
    center, center_mi, minutes = nearest_job_center(float(r["lat"]), float(r["lon"]))
    return {
        "est_value": estimate_value(r["zip"], r["beds"], r["sqft"]),
        "repair_cost": repair_cost(r["sqft"], r["condition"], r.get("roof_issue", 0), r.get("foundation_issue", 0)),
        "risk_score": risk_score(r["condition"], r["year_built"], occupied, inspected),
        "store_name": store["name"] if store else "",
        "store_miles": store["miles"] if store else None,
        "job_center": center,
        "miles_to_job_center": center_mi,
        "drive_minutes": minutes,
    }


def add_estimates(df):
    """pandas DataFrame from listings.csv -> same rows plus the estimate columns."""
    est = df.apply(lambda r: _row_estimates(r), axis=1, result_type="expand")
    return df.join(est)


# Prashna's app.py / logic.py read homes.csv with these columns (risk 0-10). Extras ride along at the end.
APP_COLUMNS = ["listing_id", "neighborhood", "city", "opening_bid", "est_value", "repair_cost", "roof_issue",
               "foundation_issue", "risk_score", "beds", "baths", "sqft", "drive_minutes"]


def to_app_table(df):
    """add_estimates() output -> the homes.csv layout app.py expects."""
    out = df.rename(columns={"id": "listing_id", "risk_score": "risk_score_100"})
    out["neighborhood"] = out["address"]                       # card title: "#1 9774 Telemachus Ave, Arlington"
    out["risk_score"] = (out["risk_score_100"] / 10).round().astype(int)
    return out[APP_COLUMNS + [c for c in out.columns if c not in APP_COLUMNS and c != "address"]]


if __name__ == "__main__":
    import pandas as pd

    root = Path(__file__).parent
    for src, dest in (("listings.csv", "homes.csv"), ("listings_houston.csv", "homes_houston.csv")):
        if (root / src).exists():
            app = to_app_table(add_estimates(pd.read_csv(root / src, dtype={"zip": str})))
            assert app["risk_score"].between(0, 10).all() and app["listing_id"].is_unique
            app.to_csv(root / dest, index=False)
            print(f"{src} -> {dest} ({len(app)} homes)")

    df = add_estimates(pd.read_csv(root / "listings.csv", dtype={"zip": str}))

    # Self-checks
    assert {"est_value", "repair_cost", "risk_score"} <= set(df.columns)
    assert df["risk_score"].between(0, 100).all()
    assert (df["opening_bid"] <= 0.80 * df["est_value"] + 500).all()          # opening bid 32-80% of value
    assert (df["opening_bid"] >= 0.32 * df["est_value"] - 500).all()
    assert risk_score("heavy", 1950, 1, 0) == 100 and risk_score("light", 2010, 0, 1) == 0
    assert estimate_value("76010", 3, 1550) == round(zip_values()[("76010", 3)][1], -3)
    print("self-checks passed\n")
    assert repair_cost(1000, "light", 1, 1) == 10 * 1000 + ROOF_COST + FOUNDATION_COST
    cols = ["id", "city", "beds", "sqft", "condition", "opening_bid", "est_value", "repair_cost",
            "risk_score", "store_miles", "job_center", "drive_minutes"]
    print(df[cols].head(8).to_string(index=False))
