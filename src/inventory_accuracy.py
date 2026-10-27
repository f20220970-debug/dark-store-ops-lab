"""Inventory record accuracy and cycle-count policies (simulation).

Each SKU has a system record and a physical shelf count. Every day, errors open a gap
(system - shelf): mis-picks, unrecorded damage (higher for fresh food) and receiving errors.
Counting a SKU closes its gap. With a fixed daily counting budget, compare three policies:
  uniform          - count SKUs round-robin
  abc              - count fast movers more often (priority = days since count x class weight)
  abc + exceptions - as abc, but first count any SKU a picker flagged as short
Metric: share of daily picks that come from a location whose record is wrong (pick-weighted
inaccuracy), because that is what causes failed picks and phantom stock.
"""
import numpy as np
import pandas as pd

import config as C

WEIGHT = {"A": 6.0, "B": 2.0, "C": 1.0}


def simulate(skus: pd.DataFrame, policy: str, seed: int = C.SEED) -> dict:
    rng = np.random.default_rng(seed)
    n = len(skus)
    demand = skus["daily_demand"].to_numpy()
    dmg = skus["department"].map(C.DAMAGE_RATE).fillna(C.DAMAGE_RATE_DEFAULT).to_numpy()
    w = skus["abc"].map(WEIGHT).to_numpy()
    budget = int(C.COUNT_HOURS_PER_DAY * 3600 / C.COUNT_SECONDS)
    gap = np.zeros(n)
    since = rng.integers(0, 30, n).astype(float)
    flagged = np.zeros(n, dtype=bool)
    cause = {"mis-pick": 0.0, "damage": 0.0, "receiving": 0.0}
    bad_picks = total_picks = 0.0
    rr = 0
    for _ in range(C.SIM_DAYS):
        sold = rng.poisson(demand)
        total_picks += sold.sum()
        bad_picks += sold[gap != 0].sum()
        mis = rng.binomial(sold, C.MISPICK_RATE) * rng.choice([-1, 1], n)
        dam = rng.binomial(sold, dmg)                              # shelf lower than system
        rec = (rng.random(n) < C.RECEIVING_ERROR_RATE * np.minimum(1, demand)) * rng.integers(-3, 4, n)
        gap += mis + dam + rec
        cause["mis-pick"] += np.abs(mis).sum(); cause["damage"] += dam.sum(); cause["receiving"] += np.abs(rec).sum()
        flagged |= (gap > 0) & (sold > 0) & (rng.random(n) < C.SHORT_PICK_FLAG_PROB)
        if policy == "uniform":
            idx = (rr + np.arange(budget)) % n; rr = (rr + budget) % n
        else:
            pri = since * w
            if policy == "abc + exceptions":
                pri = pri + flagged * 1e9                              # flagged SKUs first
            idx = np.argsort(-pri)[:budget]
        gap[idx] = 0; since[idx] = 0; flagged[idx] = False
        since += 1
    by_class = {k: float((gap[skus["abc"].to_numpy() == k] == 0).mean()) for k in "ABC"}
    tot = sum(cause.values())
    return {"policy": policy, "counts_per_day": budget,
            "pick_weighted_inaccuracy": bad_picks / total_picks,
            "record_accuracy_end": float((gap == 0).mean()),
            **{f"accuracy_{k}": v for k, v in by_class.items()},
            **{f"cause_{k}": v / tot for k, v in cause.items()}}


def compare(skus: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([simulate(skus, p) for p in ["uniform", "abc", "abc + exceptions"]])
