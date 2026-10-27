# Results summary

- Store range: top 2,000 SKUs cover 66% of all Instacart pick lines; 931 A-class SKUs (47% of the range) take 80% of picks.
- Measured on 19,064 real orders (7.0 lines each within the range).
- Walking per order: 184 m with category slotting; 135 m with velocity-within-category (27% less); 133 m with pure velocity slotting (28% less).
- Pick time per order: 285 s → 236 s → 234 s (17% and 18% faster).
- Staffing at 1,200 orders/day, 95% of orders starting within 60 s: category (baseline): 179 picker-hours/day, velocity within category: 156 picker-hours/day, pure velocity: 156 picker-hours/day.
- Replenishment (1-day lead time, daily review, ~95% service): A-class SKUs average min 11 / max 19 units.
- Inventory accuracy (simulated 60 days, 180 counts/day): picks from a wrong record fall from 23.3% (uniform counting) to 18.8% (ABC) and 8.9% (ABC + short-pick exceptions) with the same labour; error sources: damage 30%, mis-picks 18%, receiving 52%.
- Peak load: busiest day is 1.23x an average day and the busiest hour takes 8.4% of orders, so a 1,200-order store peaks at ~124 orders/hour. With 12 pickers and 3 packing stations, max throughput is 152/h with category slotting (pickers bind) and 183/h with velocity-within-category (pickers bind).
- New store at 2,000 orders/day: peak hour ~207 orders needs 22 pickers with category slotting vs 19 with velocity-within-category, and 4 packing stations.
