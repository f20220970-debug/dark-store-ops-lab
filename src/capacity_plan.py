"""Peak-hour throughput and new-store sizing.

Throughput limits per hour: pickers (pickers x 3600 / pick seconds), packing stations
(stations x 3600 / pack seconds). The binding constraint is the lower one. Storage limit:
SKUs carried vs slots. New-store sizing uses the Erlang C staffing model at the peak hour.
"""
import math

import capacity as Q
import config as C


def throughput(pick_seconds: float, pickers: int = C.PICKERS_ON_SHIFT, stations: int = C.PACK_STATIONS) -> dict:
    pick_cap = pickers * 3600 / pick_seconds
    pack_cap = stations * 3600 / C.PACK_SECONDS
    return {"picker_capacity_per_h": pick_cap, "packing_capacity_per_h": pack_cap,
            "max_orders_per_h": min(pick_cap, pack_cap),
            "binding": "pickers" if pick_cap < pack_cap else "packing"}


def size_store(daily_orders: float, peak_hour_share: float, peak_day_factor: float, pick_seconds: float) -> dict:
    peak_orders = daily_orders * peak_day_factor * peak_hour_share
    pickers = Q.pickers_needed(peak_orders, pick_seconds)
    stations = math.ceil(peak_orders * C.PACK_SECONDS / 3600 / 0.85)          # keep stations under 85% busy
    return {"daily_orders": daily_orders, "peak_hour_orders": round(peak_orders, 1),
            "pickers_at_peak": pickers, "pack_stations": stations}
