import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import capacity as Q  # noqa: E402
import config as C  # noqa: E402
import layout as L  # noqa: E402
import replenishment as R  # noqa: E402


def test_route_return_policy():
    # items in aisle 0 bay 4 and aisle 2 bay 1: cross 2*2*3=12, aisle0 in/out 2*5*1.2=12, aisle2 2*2*1.2=4.8
    assert L.route_metres([0, 2], [4, 1]) == pytest.approx(12 + 12 + 4.8)
    assert L.route_metres([], []) == 0


def test_velocity_slotting_puts_fast_movers_closer():
    skus = pd.DataFrame({"product_id": range(1, 401), "department": ["a"] * 200 + ["b"] * 200,
                         "picks": list(range(400, 0, -1))})
    v = L.slot_by_velocity(skus).set_index("product_id")
    assert v.loc[1, "walk_m"] <= v.loc[400, "walk_m"]
    vc = L.slot_velocity_within_category(skus)
    for _, g in vc.groupby("department"):
        assert g.sort_values("picks", ascending=False)["walk_m"].is_monotonic_increasing


def test_erlang_c_known_value():
    # classic example: 2 Erlangs on 3 servers -> P(wait) = 4/9
    assert Q.erlang_c(2 / 100, 100, 3) == pytest.approx(4 / 9, abs=1e-6)


def test_more_load_needs_more_pickers():
    assert Q.pickers_needed(120, 180) > Q.pickers_needed(30, 180)


def test_min_max_ordering():
    skus = R.abc(pd.DataFrame({"product_id": [1, 2, 3], "department": "x", "picks": [900, 90, 10]}))
    mm = R.min_max(skus, 1000).set_index("product_id")
    assert (mm["max_units"] >= mm["min_units"]).all() and mm.loc[1, "abc"] == "A"


import capacity_plan as CP  # noqa: E402
import inventory_accuracy as IA  # noqa: E402


def _skus():
    df = pd.DataFrame({"product_id": range(1, 301), "department": ["produce"] * 100 + ["pantry"] * 200,
                       "picks": list(range(300, 0, -1))})
    return R.min_max(R.abc(df), 3000)


def test_abc_counting_beats_uniform_with_same_budget():
    acc = IA.compare(_skus()).set_index("policy")
    assert acc.loc["abc + exceptions", "pick_weighted_inaccuracy"] <= acc.loc["uniform", "pick_weighted_inaccuracy"]
    assert abs(acc.filter(like="cause_").iloc[0].sum() - 1) < 1e-9


def test_throughput_binding_constraint():
    t = CP.throughput(pick_seconds=300, pickers=8, stations=3)     # pickers 96/h, packing 240/h
    assert t["binding"] == "pickers" and t["max_orders_per_h"] == 96
    s = CP.size_store(2000, 0.08, 1.2, 240)
    assert s["pickers_at_peak"] >= 1 and s["pack_stations"] >= 1
