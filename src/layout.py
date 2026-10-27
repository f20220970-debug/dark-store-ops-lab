"""Dark-store layout model, slotting policies and pick-path distance.

Layout: AISLES parallel aisles with a front cross-aisle; the packing station sits at the
front of aisle 0. A slot is (aisle, bay, side, level). Distance uses RETURN routing, a common
and simple policy: walk along the front to each aisle that has items, go in to the deepest
item, come back out; finish at the packing station.
"""
import numpy as np
import pandas as pd

import config as C


def slots() -> pd.DataFrame:
    """All slots, ordered from the cheapest to reach (front of near aisles) to the dearest."""
    rows = [(a, b, s, l) for a in range(C.AISLES) for b in range(C.BAYS_PER_SIDE)
            for s in (0, 1) for l in range(C.LEVELS)]
    df = pd.DataFrame(rows, columns=["aisle", "bay", "side", "level"])
    # one-way walking cost to a slot from the packing station, plus a small penalty for
    # top and bottom shelves (slower to pick)
    df["walk_m"] = df["aisle"] * C.AISLE_PITCH_M + (df["bay"] + 0.5) * C.BAY_WIDTH_M
    df["ergonomic"] = df["level"].map({0: 1.0, 1: 0.0, 2: 0.0, 3: 1.0})
    return df


def slot_by_category(skus: pd.DataFrame, rng=None) -> pd.DataFrame:
    """Baseline: departments fill aisles in order (like a supermarket); random within department."""
    rng = rng or np.random.default_rng(C.SEED)
    s = slots().sort_values(["aisle", "bay", "side", "level"]).reset_index(drop=True)
    order = (skus.assign(r=rng.random(len(skus)))
                 .sort_values(["department", "r"]).reset_index(drop=True))
    return pd.concat([order[["product_id", "department", "picks"]], s.iloc[: len(order)].reset_index(drop=True)], axis=1)


def slot_velocity_within_category(skus: pd.DataFrame) -> pd.DataFrame:
    """Practical change: keep each department in its aisles, but put its fastest movers at the
    front of those aisles and at waist height."""
    base = slot_by_category(skus)
    out = []
    for dept, grp in base.groupby("department", sort=False):
        ranked_slots = grp[["aisle", "bay", "side", "level", "walk_m", "ergonomic"]].sort_values(["walk_m", "ergonomic"]).reset_index(drop=True)
        ranked_skus = grp[["product_id", "department", "picks"]].sort_values("picks", ascending=False).reset_index(drop=True)
        out.append(pd.concat([ranked_skus, ranked_slots], axis=1))
    return pd.concat(out, ignore_index=True)


def slot_by_velocity(skus: pd.DataFrame) -> pd.DataFrame:
    """Upper bound: ignore departments; the fastest movers take the nearest, easiest slots."""
    s = slots().sort_values(["walk_m", "ergonomic"]).reset_index(drop=True)
    ranked = skus.sort_values("picks", ascending=False).reset_index(drop=True)
    return pd.concat([ranked[["product_id", "department", "picks"]], s.iloc[: len(ranked)].reset_index(drop=True)], axis=1)


def route_metres(aisles: np.ndarray, bays: np.ndarray) -> float:
    """Return-routing distance for one order given the aisle and bay of each item."""
    if len(aisles) == 0:
        return 0.0
    df = pd.DataFrame({"a": aisles, "b": bays})
    deepest = df.groupby("a")["b"].max()
    cross = 2 * deepest.index.max() * C.AISLE_PITCH_M                 # front aisle out and back
    in_out = (2 * (deepest + 1) * C.BAY_WIDTH_M).sum()                # into each aisle and back
    return float(cross + in_out)


def pick_seconds(metres: float, lines: int) -> float:
    return metres / C.WALK_SPEED_MPS + lines * C.SECONDS_PER_LINE + C.SECONDS_PER_ORDER


def measure(layout: pd.DataFrame, order_lines: pd.DataFrame) -> pd.DataFrame:
    """Pick distance and time for each sample order under a slotting layout."""
    loc = layout.set_index("product_id")[["aisle", "bay"]]
    j = order_lines.join(loc, on="product_id", how="inner")
    res = j.groupby("order_id").apply(lambda g: pd.Series({
        "lines": len(g), "metres": route_metres(g["aisle"].to_numpy(), g["bay"].to_numpy())}),
        include_groups=False)
    res["seconds"] = res["metres"] / C.WALK_SPEED_MPS + res["lines"] * C.SECONDS_PER_LINE + C.SECONDS_PER_ORDER
    return res
