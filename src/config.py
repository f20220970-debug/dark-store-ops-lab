"""Store, labour and planning assumptions. Every number here is an assumption to replace
with a real store's data; the method is what the project demonstrates."""
SKUS_CARRIED = 2000          # dark stores carry a few thousand SKUs: keep the top sellers
AISLES = 10                  # storage aisles
BAYS_PER_SIDE = 25           # bays along each side of an aisle
LEVELS = 4                   # shelf levels per bay (2 sides x 25 bays x 4 levels = 200 slots/aisle)
AISLE_PITCH_M = 3.0          # distance between aisle centre lines (front cross-aisle)
BAY_WIDTH_M = 1.2            # metres per bay along the aisle
WALK_SPEED_MPS = 1.0         # picker walking speed with a trolley
SECONDS_PER_LINE = 8         # find, pick and scan one item line
SECONDS_PER_ORDER = 45       # start order, bag, label and hand over
SAMPLE_ORDERS = 20000        # real orders used to measure pick paths
DAILY_ORDERS = 1200          # assumed orders per day for one dark store
SLA_WAIT_SECONDS = 60        # order should start picking within this
SLA_TARGET = 0.95            # ... for this share of orders
LEAD_TIME_DAYS = 1           # DC to store replenishment lead time
REVIEW_DAYS = 1              # store reorders once a day
SERVICE_Z = 1.65             # ~95% cycle service level
CV_BY_CLASS = {"A": 0.30, "B": 0.50, "C": 0.80}   # assumed day-to-day demand variability
SEED = 7

# ---- Inventory accuracy and cycle counting (assumptions) ----
SIM_DAYS = 60
MISPICK_RATE = 0.0015          # share of pick lines where the wrong item or quantity is taken
DAMAGE_RATE = {"produce": 0.004, "dairy eggs": 0.002, "bakery": 0.003}   # unrecorded write-offs per unit sold
DAMAGE_RATE_DEFAULT = 0.0005
RECEIVING_ERROR_RATE = 0.01   # share of replenishment receipts booked with the wrong quantity
COUNT_SECONDS = 40            # time to count one SKU location
COUNT_HOURS_PER_DAY = 2.0     # daily cycle-count labour budget
SHORT_PICK_FLAG_PROB = 0.5    # chance a picker flags a short pick when shelf < system

# ---- Capacity and new-store planning (assumptions) ----
PICKERS_ON_SHIFT = 12
PACK_STATIONS = 3
PACK_SECONDS = 45             # packing time per order at a station
NEW_STORE_DAILY_ORDERS = 2000
