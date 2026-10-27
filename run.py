"""Run the dark-store study on Instacart data.

    python run.py --data ../qcommerce-retention-sql/data      # folder with the Instacart CSVs
Outputs: results/*.csv, results/summary.md, charts/*.png
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import duckdb  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import capacity as Q  # noqa: E402
import capacity_plan as CP  # noqa: E402
import inventory_accuracy as IA  # noqa: E402
import config as C  # noqa: E402
import layout as L  # noqa: E402
import replenishment as R  # noqa: E402


def load(data: Path):
    con = duckdb.connect()
    p = lambda f: (data / f).as_posix()
    for f in ["orders.csv", "order_products__prior.csv", "products.csv", "departments.csv"]:
        if not (data / f).exists():
            raise SystemExit(f"Missing {data / f}. Point --data at the Instacart CSV folder.")
    skus = con.execute(f"""
        SELECT op.product_id, d.department, COUNT(*) AS picks
        FROM read_csv_auto('{p('order_products__prior.csv')}') op
        JOIN read_csv_auto('{p('products.csv')}') pr USING (product_id)
        JOIN read_csv_auto('{p('departments.csv')}') d USING (department_id)
        GROUP BY 1, 2 ORDER BY picks DESC LIMIT {C.SKUS_CARRIED}""").df()
    total_lines = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{p('order_products__prior.csv')}')").fetchone()[0]
    con.register("carried", skus[["product_id"]])
    lines = con.execute(f"""
        WITH sample AS (
            SELECT order_id FROM read_csv_auto('{p('orders.csv')}')
            WHERE eval_set = 'prior' ORDER BY hash(order_id) LIMIT {C.SAMPLE_ORDERS})
        SELECT op.order_id, op.product_id
        FROM read_csv_auto('{p('order_products__prior.csv')}') op
        JOIN sample USING (order_id) JOIN carried USING (product_id)""").df()
    hours = con.execute(f"""SELECT CAST(order_hour_of_day AS INTEGER) AS hour, COUNT(*) AS orders
        FROM read_csv_auto('{p('orders.csv')}') GROUP BY 1 ORDER BY 1""").df()
    days = con.execute(f"""SELECT CAST(order_dow AS INTEGER) AS dow, COUNT(*) AS orders
        FROM read_csv_auto('{p('orders.csv')}') GROUP BY 1 ORDER BY 1""").df()
    return skus, lines, hours, total_lines, days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    a = ap.parse_args()
    skus, lines, hours, total_lines, days = load(Path(a.data))
    coverage = skus["picks"].sum() / total_lines
    skus = R.abc(skus)

    layouts = {"category (baseline)": L.slot_by_category(skus),
               "velocity within category": L.slot_velocity_within_category(skus),
               "pure velocity": L.slot_by_velocity(skus)}
    results = {k: L.measure(v, lines) for k, v in layouts.items()}
    perf = pd.DataFrame([{"layout": k, "orders": len(r), "avg_lines": r["lines"].mean(),
                          "avg_metres": r["metres"].mean(), "p90_metres": r["metres"].quantile(0.9),
                          "avg_pick_seconds": r["seconds"].mean()} for k, r in results.items()]).round(1)
    base = perf.iloc[0]
    perf["walk_saving_pct"] = (100 * (1 - perf["avg_metres"] / base["avg_metres"])).round(1)
    perf["time_saving_pct"] = (100 * (1 - perf["avg_pick_seconds"] / base["avg_pick_seconds"])).round(1)

    hours["share"] = hours["orders"] / hours["orders"].sum()
    hours["store_orders"] = hours["share"] * C.DAILY_ORDERS
    staff = hours[["hour", "store_orders"]].copy()
    for _, row in perf.iterrows():
        staff[row["layout"]] = [Q.pickers_needed(o, row["avg_pick_seconds"]) if o > 0.5 else 0 for o in staff["store_orders"]]
    picker_hours = {k: int(staff[k].sum()) for k in perf["layout"]}

    avg_lines = perf.iloc[0]["avg_lines"]
    rep = R.min_max(skus, C.DAILY_ORDERS * avg_lines)
    by_class = rep.groupby("abc").agg(skus=("product_id", "size"), share_of_picks=("picks", "sum"),
                                      avg_min=("min_units", "mean"), avg_max=("max_units", "mean")).reset_index()
    by_class["share_of_picks"] = (by_class["share_of_picks"] / rep["picks"].sum()).round(3)

    acc = IA.compare(rep)
    peak_hour_share = hours["share"].max()
    peak_day_factor = days["orders"].max() / days["orders"].mean()
    cap = []
    for _, row in perf.iterrows():
        t = CP.throughput(row["avg_pick_seconds"])
        cap.append({"layout": row["layout"], **{k: (round(v, 1) if isinstance(v, float) else v) for k, v in t.items()}})
    cap = pd.DataFrame(cap)
    peak_now = C.DAILY_ORDERS * peak_day_factor * peak_hour_share
    new_store = pd.DataFrame([{"layout": r["layout"], **CP.size_store(C.NEW_STORE_DAILY_ORDERS, peak_hour_share, peak_day_factor, r["avg_pick_seconds"])}
                              for _, r in perf.iterrows()])

    (ROOT / "results").mkdir(exist_ok=True); (ROOT / "charts").mkdir(exist_ok=True)
    acc.round(4).to_csv(ROOT / "results/cycle_count_policies.csv", index=False)
    cap.to_csv(ROOT / "results/peak_throughput.csv", index=False)
    new_store.to_csv(ROOT / "results/new_store_sizing.csv", index=False)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.bar(acc["policy"], 100 * acc["pick_weighted_inaccuracy"], color=["#9DB4C0", "#2C7A7B", "#1F3A5F"])
    ax.set_ylabel("% of picks from a wrong record"); ax.set_title(f"Cycle-count policies, same budget ({int(acc.iloc[0].counts_per_day)} counts/day)")
    fig.tight_layout(); fig.savefig(ROOT / "charts/cycle_count_policies.png", dpi=120); plt.close(fig)
    perf.to_csv(ROOT / "results/layout_comparison.csv", index=False)
    staff.round(2).to_csv(ROOT / "results/staffing_by_hour.csv", index=False)
    rep.head(50).round(2).to_csv(ROOT / "results/min_max_top50.csv", index=False)
    by_class.round(1).to_csv(ROOT / "results/abc_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(9, 4))
    for k, c in zip(results, ["#9DB4C0", "#2C7A7B", "#1F3A5F"]):
        ax.hist(results[k]["metres"], bins=50, alpha=.55, label=k, color=c)
    ax.set_xlabel("Pick-path distance per order (m)"); ax.set_ylabel("orders"); ax.legend()
    ax.set_title("Walking distance per order by slotting policy"); fig.tight_layout(); fig.savefig(ROOT / "charts/pick_distance.png", dpi=120); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 4))
    w = 0.28
    for i, k in enumerate(perf["layout"]):
        ax.bar(staff["hour"] + (i - 1) * w, staff[k], w, label=k)
    ax.set_xlabel("Hour of day"); ax.set_ylabel("pickers needed"); ax.legend()
    ax.set_title(f"Pickers needed per hour ({C.DAILY_ORDERS} orders/day, {int(C.SLA_TARGET*100)}% start within {C.SLA_WAIT_SECONDS}s)")
    fig.tight_layout(); fig.savefig(ROOT / "charts/staffing_by_hour.png", dpi=120); plt.close(fig)
    cum = rep["picks"].cumsum() / rep["picks"].sum()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(np.arange(1, len(cum) + 1), 100 * cum, color="#2C7A7B")
    ax.set_xlabel("SKUs ranked by picks"); ax.set_ylabel("% of picks"); ax.set_title("Pick concentration (ABC)")
    fig.tight_layout(); fig.savefig(ROOT / "charts/abc_curve.png", dpi=120); plt.close(fig)

    v_mid, v_best = perf.iloc[1], perf.iloc[2]
    a_row = by_class.set_index("abc").loc["A"]
    lines_md = [
        "# Results summary", "",
        f"- Store range: top {C.SKUS_CARRIED:,} SKUs cover {100 * coverage:.0f}% of all Instacart pick lines; "
        f"{int(a_row.skus)} A-class SKUs ({100 * a_row.skus / len(rep):.0f}% of the range) take {100 * a_row.share_of_picks:.0f}% of picks.",
        f"- Measured on {int(base.orders):,} real orders ({base.avg_lines:.1f} lines each within the range).",
        f"- Walking per order: {base.avg_metres:.0f} m with category slotting; {v_mid.avg_metres:.0f} m with velocity-within-category "
        f"({v_mid.walk_saving_pct:.0f}% less); {v_best.avg_metres:.0f} m with pure velocity slotting ({v_best.walk_saving_pct:.0f}% less).",
        f"- Pick time per order: {base.avg_pick_seconds:.0f} s → {v_mid.avg_pick_seconds:.0f} s → {v_best.avg_pick_seconds:.0f} s "
        f"({v_mid.time_saving_pct:.0f}% and {v_best.time_saving_pct:.0f}% faster).",
        f"- Staffing at {C.DAILY_ORDERS:,} orders/day, {int(C.SLA_TARGET * 100)}% of orders starting within {C.SLA_WAIT_SECONDS} s: "
        + ", ".join(f"{k}: {v} picker-hours/day" for k, v in picker_hours.items()) + ".",
        f"- Replenishment (1-day lead time, daily review, ~95% service): A-class SKUs average min {a_row.avg_min:.0f} / max {a_row.avg_max:.0f} units.",
    ]
    u, ab, ex = acc.iloc[0], acc.iloc[1], acc.iloc[2]
    c0, c1 = cap.iloc[0], cap.iloc[1]
    ns0, ns1 = new_store.iloc[0], new_store.iloc[1]
    lines_md += [
        f"- Inventory accuracy (simulated {C.SIM_DAYS} days, {int(u.counts_per_day)} counts/day): picks from a wrong record fall from "
        f"{100 * u.pick_weighted_inaccuracy:.1f}% (uniform counting) to {100 * ab.pick_weighted_inaccuracy:.1f}% (ABC) and "
        f"{100 * ex.pick_weighted_inaccuracy:.1f}% (ABC + short-pick exceptions) with the same labour; error sources: "
        f"damage {100 * u.cause_damage:.0f}%, mis-picks {100 * u['cause_mis-pick']:.0f}%, receiving {100 * u.cause_receiving:.0f}%.",
        f"- Peak load: busiest day is {peak_day_factor:.2f}x an average day and the busiest hour takes {100 * peak_hour_share:.1f}% of orders, "
        f"so a 1,200-order store peaks at ~{peak_now:.0f} orders/hour. With {C.PICKERS_ON_SHIFT} pickers and {C.PACK_STATIONS} packing stations, "
        f"max throughput is {c0.max_orders_per_h:.0f}/h with category slotting ({c0.binding} bind) and {c1.max_orders_per_h:.0f}/h with velocity-within-category ({c1.binding} bind).",
        f"- New store at {C.NEW_STORE_DAILY_ORDERS:,} orders/day: peak hour ~{ns0.peak_hour_orders:.0f} orders needs {ns0.pickers_at_peak} pickers with category slotting "
        f"vs {ns1.pickers_at_peak} with velocity-within-category, and {ns1.pack_stations} packing stations.",
    ]
    (ROOT / "results/summary.md").write_text("\n".join(lines_md) + "\n")
    print("\n".join(lines_md))


if __name__ == "__main__":
    main()
