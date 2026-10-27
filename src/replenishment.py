"""Store min/max replenishment from DC, by ABC class.

daily demand (units) = SKU's share of pick lines x store's daily pick lines
min (reorder point) = demand x lead time + safety stock, safety stock = z x sigma x sqrt(lead time)
max (order-up-to)   = min + demand x review period
sigma comes from an assumed coefficient of variation per ABC class (replace with real daily sales).
"""
import math

import pandas as pd

import config as C


def abc(skus: pd.DataFrame) -> pd.DataFrame:
    s = skus.sort_values("picks", ascending=False).copy()
    cum = s["picks"].cumsum() / s["picks"].sum()
    s["abc"] = ["A" if c <= 0.80 else "B" if c <= 0.95 else "C" for c in cum]
    s.iloc[0, s.columns.get_loc("abc")] = "A"
    return s


def min_max(skus: pd.DataFrame, daily_lines: float) -> pd.DataFrame:
    s = skus.copy()
    s["daily_demand"] = s["picks"] / s["picks"].sum() * daily_lines
    s["sigma"] = s["abc"].map(C.CV_BY_CLASS) * s["daily_demand"]
    s["safety_stock"] = C.SERVICE_Z * s["sigma"] * math.sqrt(C.LEAD_TIME_DAYS)
    s["min_units"] = (s["daily_demand"] * C.LEAD_TIME_DAYS + s["safety_stock"]).apply(math.ceil)
    s["max_units"] = (s["min_units"] + s["daily_demand"] * C.REVIEW_DAYS).apply(math.ceil)
    return s
