import itertools
from logic import *

homes = load_homes()
combos = itertools.product([60000, 120000, 180000, 300000], GOAL_MARGIN, RISK_SHIFT, [2, 3, 4], TOLERANCES, [15, 25, 40])
count = 0
for budget, goal, risk, beds, tol, drive in combos:
    ranked = rank_homes(screen_homes(homes, budget, goal, risk, beds, tol, drive), budget, goal, risk, drive)
    top = ranked.head(3)
    for row in top.itertuples():
        assert row.walk_away >= 0
        if row.viable:   # winning at the walk-away bid, with every fee, still fits the budget
            assert row.walk_away + auction_fees(row.walk_away) + row.repair_cost <= budget
            buffer = REPAIR_BUFFER[int(row.interior_inspected)]   # and never costs more than it's worth
            assert row.walk_away + auction_fees(row.walk_away) + row.repair_cost * (1 + buffer) <= row.est_value
        why_it_fits(row, goal)
        bid_checklist(row)
    flips = rank_homes(screen_homes(homes, budget, "Fix and resell", risk, 1, TOLERANCES[0], 60), budget, "Fix and resell", risk, 60)
    plan = plan_portfolio(flips, budget, risk)
    assert plan.empty or (plan.capital.sum() <= budget and (plan.capital <= MAX_SHARE * budget).all()
                          and plan.risk_score.mean() <= INVESTOR_RISK_CAP[risk] + 1e-9 and (plan.profit > 0).all())
    count += 1
print("combos ok:", count)
demo = rank_homes(screen_homes(homes, 180000, "Live in it", "Balanced", 3, TOLERANCES[1], 30), 180000, "Live in it", "Balanced", 30)
print(demo[["neighborhood", "opening_bid", "est_value", "repair_cost", "walk_away", "score", "viable"]].head(5).to_string())
print(plan_portfolio(rank_homes(screen_homes(homes, 300000, "Fix and resell", "Balanced", 2, TOLERANCES[0], 40), 300000, "Fix and resell", "Balanced", 40), 300000, "Balanced")[["neighborhood", "bid", "capital", "profit"]].to_string())
