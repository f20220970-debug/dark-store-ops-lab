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
