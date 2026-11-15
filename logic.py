import math
import pandas as pd

GOAL_MARGIN = {"Live in it": 0.10, "Rent it": 0.20, "Fix and resell": 0.30}
RISK_SHIFT = {"Safe": 0.05, "Balanced": 0.0, "Aggressive": -0.05}
RISK_CAP = {"Safe": 4, "Balanced": 7, "Aggressive": 10}
GOAL_WEIGHTS = {
    "Live in it": (0.30, 0.30, 0.40),
    "Rent it": (0.50, 0.30, 0.20),
    "Fix and resell": (0.70, 0.20, 0.10),
}
TOLERANCES = ["Any repairs", "No roof or foundation work", "Light repairs only (under $30K)"]


def load_homes(path="homes.csv"):
    return pd.read_csv(path)


# Costs on top of the winning bid (Xome): buyer's premium = the greater of 5% or $2,500, plus ~2% closing
# (title, recording, escrow on a Texas cash purchase). Counted against the budget so a walk-away bid never
# pushes the buyer over it. Value side keeps the goal margin (Fix and resell = the investors' 70% rule).
PREMIUM_PCT, PREMIUM_MIN, CLOSING_PCT = 0.05, 2500, 0.02


def auction_fees(bid):
    """Buyer's premium + closing costs paid on top of a winning bid."""
    return max(PREMIUM_PCT * bid, PREMIUM_MIN) + CLOSING_PCT * bid


def max_bid_for_cash(cash):
    """Highest bid whose bid + auction_fees(bid) fits in `cash` (fees switch from $2,500 flat to 5% at $50k)."""
    pct_bid = cash / (1 + PREMIUM_PCT + CLOSING_PCT)
    return pct_bid if PREMIUM_PCT * pct_bid >= PREMIUM_MIN else (cash - PREMIUM_MIN) / (1 + CLOSING_PCT)


REPAIR_BUFFER = {1: 0.10, 0: 0.25}   # repairs run over: +10% if inspected, +25% if nobody has seen inside


def walk_away_bid(est_value, repair_cost, budget, goal, risk, inspected=1):
    margin = GOAL_MARGIN[goal] + RISK_SHIFT[risk]
    # Never pay more in total (bid + fees + repairs with a buffer) than the home is worth. Only bites for
    # Live in it at higher risk, whose small cushion is less than the fees; rent and flip margins already cover it.
    worth_it = max_bid_for_cash(est_value - repair_cost * (1 + REPAIR_BUFFER[int(inspected)]))
    raw = min(max_bid_for_cash(budget - repair_cost), est_value * (1 - margin) - repair_cost, worth_it)
    return max(0, int(math.floor(raw / 500.0) * 500))


def screen_homes(homes, budget, goal, risk, min_beds, tolerance, max_drive):
    frame = homes.copy()
    can_open = frame.opening_bid + frame.opening_bid.map(auction_fees) + frame.repair_cost <= budget
    frame = frame[can_open & (frame.beds >= min_beds) & (frame.drive_minutes <= max_drive)]
    frame = frame[frame.risk_score <= RISK_CAP[risk]]
    if tolerance == TOLERANCES[1]:
        frame = frame[(frame.roof_issue == 0) & (frame.foundation_issue == 0)]
    elif tolerance == TOLERANCES[2]:
        frame = frame[frame.repair_cost < 30000]
    return frame.reset_index(drop=True)


def rank_homes(frame, budget, goal, risk, max_drive):
    if frame.empty:
        return frame.assign(walk_away=[], score=[], viable=[])
    wd, wr, wl = GOAL_WEIGHTS[goal]
    out = frame.copy()
    out["walk_away"] = [walk_away_bid(r.est_value, r.repair_cost, budget, goal, risk, getattr(r, "interior_inspected", 1))
                        for r in out.itertuples()]
    gap = ((out.est_value - out.repair_cost - out.opening_bid) / out.est_value).clip(0, 1)
    safety = 1 - out.risk_score / 10.0
    nearness = 1 - out.drive_minutes / max(max_drive, 1)
    out["score"] = (100 * (wd * gap / 0.5 + wr * safety + wl * nearness)).clip(0, 100).round(0).astype(int)
    out["viable"] = out.walk_away >= out.opening_bid
    return out.sort_values(["viable", "score"], ascending=[False, False]).reset_index(drop=True)


def why_it_fits(row, goal):
    save = int(row.est_value - row.repair_cost - row.opening_bid)
    tone = "low" if row.risk_score <= 3 else "moderate" if row.risk_score <= 6 else "high"
    return (
        f"{int(row.beds)} bd / {int(row.baths)} ba in {row.neighborhood}, {row.city}, {int(row.drive_minutes)} min away. "
        f"Opens at ${int(row.opening_bid):,} against ~${int(row.est_value):,} value, about ${save:,} of room after repairs. "
        f"{tone.capitalize()} risk for a {goal.lower()} plan."
    )


def bid_checklist(row):
    steps = [
        "Register and verify your identity on Xome before auction day",
        "Confirm how your deposit is paid and when it is due",
        "Read the full listing terms and any title notes on Xome",
        f"Set your hard stop at ${int(row.walk_away):,} and do not move it live",
        "Confirm how you will pay the balance and the closing deadline",
        "Get a contractor quote to check the ${:,} repair estimate".format(int(row.repair_cost)),
    ]
    if row.roof_issue:
        steps.append("Have the roof inspected before bidding")
    if row.foundation_issue:
        steps.append("Have a structural engineer check the foundation")
    return steps


# Investor mode (Prajita's design): always planned as flips, average risk capped, no single home over half the
# money, every cost counted. `ranked` should come from rank_homes(..., goal="Fix and resell", ...).
INVESTOR_RISK_CAP = {"Safe": 3.5, "Balanced": 5.0, "Aggressive": 7.0}   # max AVERAGE risk (0-10) of the set
MAX_SHARE = 0.50          # one home may use at most half the capital
EXPECTED_MARKUP = 1.10    # plan to win at ~10% over the opening bid, never above the walk-away bid
FLIP_SELL_HOLD = 0.10     # selling (~8%: agents + closing) + holding (~2%: taxes, insurance, utilities) of value


def plan_portfolio(ranked, budget, risk="Balanced"):
    pool = ranked[ranked.viable].copy()
    if pool.empty:
        return pool.assign(bid=[], capital=[], profit=[])
    expected = (pool.opening_bid * EXPECTED_MARKUP / 500).apply(math.floor) * 500
    pool["bid"] = expected.where(expected < pool.walk_away, pool.walk_away).astype(int)
    pool["capital"] = (pool.bid + pool.bid.map(auction_fees) + pool.repair_cost).round(-2).astype(int)
    pool["profit"] = (pool.est_value * (1 - FLIP_SELL_HOLD) - pool.capital).round(-2).astype(int)
    pool = pool[(pool.capital <= MAX_SHARE * budget) & (pool.profit > 0)].reset_index(drop=True)
    if pool.empty:
        return pool
    # Riskier homes are less likely to earn the full profit, so the solver weighs profit by risk.
    weighted = (pool.profit * (1 - pool.risk_score / 20.0)).tolist()
    risk_room = (pool.risk_score - INVESTOR_RISK_CAP[risk]).tolist()   # sum(risk - cap) <= 0  ==  average <= cap
    chosen = solve_knapsack(weighted, pool.capital.tolist(), budget, risk_room)
    return pool.iloc[chosen].sort_values("profit", ascending=False).reset_index(drop=True)


def solve_knapsack(profits, costs, cap, risk_room=None):
    """Pick items (0/1) for the most profit with sum(costs) <= cap and, if given, sum(risk_room) <= 0.
    Gurobi when installed; otherwise SciPy's exact MILP solver (same answer, no license needed)."""
    n = len(profits)
    rows, highs = [costs], [cap]
    if risk_room is not None:
        rows, highs = rows + [risk_room], highs + [0]
    try:
        import gurobipy as gp
        from gurobipy import GRB
        model = gp.Model()
        model.Params.OutputFlag = 0
        picks = model.addVars(n, vtype=GRB.BINARY)
        model.setObjective(gp.quicksum(profits[i] * picks[i] for i in range(n)), GRB.MAXIMIZE)
        for row, high in zip(rows, highs):
            model.addConstr(gp.quicksum(row[i] * picks[i] for i in range(n)) <= high)
        model.optimize()
        return [i for i in range(n) if picks[i].X > 0.5]
    except Exception:
        import numpy as np
        from scipy.optimize import milp, LinearConstraint, Bounds
        res = milp(
            c=-np.array(profits, dtype=float),
            constraints=LinearConstraint(np.array(rows, dtype=float), -np.inf, np.array(highs, dtype=float)),
            integrality=np.ones(n),
            bounds=Bounds(0, 1),
        )
        return [i for i, v in enumerate(res.x) if v > 0.5] if res.x is not None else []
