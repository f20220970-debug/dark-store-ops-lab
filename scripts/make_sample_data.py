"""Small FAKE Instacart-shaped files so the pipeline and CI run without the real data."""
import csv
import random
from pathlib import Path

random.seed(3)
D = Path(__file__).resolve().parents[1] / "data"; D.mkdir(exist_ok=True)
deps = ["produce", "dairy eggs", "snacks", "beverages", "frozen", "pantry", "bakery", "household"]
with open(D / "departments.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["department_id", "department"]); [w.writerow([i + 1, d]) for i, d in enumerate(deps)]
with open(D / "products.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["product_id", "product_name", "aisle_id", "department_id"])
    for p in range(1, 3001): w.writerow([p, f"P{p}", 1, random.randint(1, len(deps))])
weights = [1 / (p ** 0.9) for p in range(1, 3001)]
with open(D / "orders.csv", "w", newline="") as fo, open(D / "order_products__prior.csv", "w", newline="") as fp:
    wo, wp = csv.writer(fo), csv.writer(fp)
    wo.writerow(["order_id", "user_id", "eval_set", "order_number", "order_dow", "order_hour_of_day", "days_since_prior_order"])
    wp.writerow(["order_id", "product_id", "add_to_cart_order", "reordered"])
    for o in range(1, 6001):
        wo.writerow([o, o % 900, "prior", 1, o % 7, random.choice([8, 9, 10, 11, 14, 16, 18, 19, 20]), ""])
        for k, p in enumerate(set(random.choices(range(1, 3001), weights, k=random.randint(3, 15))), 1):
            wp.writerow([o, p, k, 0])
print("fake data written")
