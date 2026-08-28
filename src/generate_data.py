import pandas as pd
import numpy as np
from pathlib import Path

np.random.seed(42)

NUM_TRANSACTIONS = 100_000

START_DATE = pd.Timestamp("2026-07-01")
END_DATE = pd.Timestamp("2026-08-01")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

OUTPUT_PATH = DATA_DIR / "transactions.csv"

merchants = [f"M{i:03d}" for i in range(1, 51)]
customers = [f"C{i:05d}" for i in range(1, 10_001)]

payment_methods = ["UPI", "CARD", "NETBANKING", "WALLET"]
banks = ["Bank_A", "Bank_B", "Bank_C", "Bank_X", "Bank_Y"]
devices = ["Android", "iOS", "Web"]
locations = ["Chennai", "Bangalore", "Hyderabad", "Mumbai", "Delhi"]

error_codes = [
    "BANK_DECLINE",
    "TIMEOUT",
    "INSUFFICIENT_FUNDS",
    "NETWORK_ERROR",
]


# =========================================
# GENERATE TRANSACTIONS
# =========================================

random_seconds = np.random.randint(
    0,
    int((END_DATE - START_DATE).total_seconds()),
    NUM_TRANSACTIONS,
    dtype=np.int64
)

timestamps = (
    START_DATE
    + pd.to_timedelta(random_seconds, unit="s")
)

transactions = pd.DataFrame({
    "transaction_id": [
        f"TXN{i:06d}"
        for i in range(1, NUM_TRANSACTIONS + 1)
    ],

    "merchant_id": np.random.choice(
        merchants,
        NUM_TRANSACTIONS
    ),

    "customer_id": np.random.choice(
        customers,
        NUM_TRANSACTIONS
    ),

    "amount": np.round(
        np.random.lognormal(
            mean=7.2,
            sigma=1.0,
            size=NUM_TRANSACTIONS
        ),
        2
    ),

    "payment_method": np.random.choice(
        payment_methods,
        NUM_TRANSACTIONS,
        p=[0.55, 0.25, 0.12, 0.08]
    ),

    "bank": np.random.choice(
        banks,
        NUM_TRANSACTIONS
    ),

    "device_type": np.random.choice(
        devices,
        NUM_TRANSACTIONS,
        p=[0.55, 0.25, 0.20]
    ),

    "location": np.random.choice(
        locations,
        NUM_TRANSACTIONS
    ),

    "timestamp": timestamps,
})


# =========================================
# NORMAL SUCCESS PROBABILITY
# =========================================

success_probability = np.full(
    NUM_TRANSACTIONS,
    0.94
)

# Payment method effects
success_probability += np.where(
    transactions["payment_method"] == "UPI",
    0.01,
    0
)

success_probability += np.where(
    transactions["payment_method"] == "NETBANKING",
    -0.03,
    0
)

success_probability += np.where(
    transactions["payment_method"] == "WALLET",
    -0.01,
    0
)

# Bank effects
success_probability += np.where(
    transactions["bank"] == "Bank_A",
    0.01,
    0
)

success_probability += np.where(
    transactions["bank"] == "Bank_C",
    -0.01,
    0
)

success_probability += np.where(
    transactions["bank"] == "Bank_X",
    -0.01,
    0
)

# Device effects
success_probability += np.where(
    transactions["device_type"] == "iOS",
    0.01,
    0
)

success_probability += np.where(
    transactions["device_type"] == "Web",
    -0.01,
    0
)


# =========================================
# HIGH-VOLUME INCIDENT
# =========================================
#
# We create a dedicated incident period:
#
# July 23, 19:00–20:00
#
# Affected route:
# UPI + Bank_X + Android
#
# To make the incident statistically useful,
# we add additional transactions to this route.
# =========================================

incident_start = pd.Timestamp("2026-07-23 19:00:00")
incident_end = pd.Timestamp("2026-07-23 20:00:00")

incident_count = 500

incident_timestamps = pd.to_datetime(
    np.random.randint(
        incident_start.value,
        incident_end.value,
        incident_count,
        dtype=np.int64
    )
)

incident_transactions = pd.DataFrame({
    "transaction_id": [
        f"INC{i:04d}"
        for i in range(1, incident_count + 1)
    ],

    "merchant_id": np.random.choice(
        merchants,
        incident_count
    ),

    "customer_id": np.random.choice(
        customers,
        incident_count
    ),

    "amount": np.round(
        np.random.lognormal(
            mean=7.2,
            sigma=1.0,
            size=incident_count
        ),
        2
    ),

    "payment_method": "UPI",

    "bank": "Bank_X",

    "device_type": "Android",

    "location": np.random.choice(
        locations,
        incident_count
    ),

    "timestamp": incident_timestamps,
})


# =========================================
# NORMAL TRANSACTION STATUS
# =========================================

random_values = np.random.random(
    NUM_TRANSACTIONS
)

transactions["status"] = np.where(
    random_values < success_probability,
    "SUCCESS",
    "FAILED"
)


# =========================================
# INCIDENT STATUS
# =========================================

incident_status = np.where(
    np.random.random(incident_count) < 0.70,
    "SUCCESS",
    "FAILED"
)

incident_transactions["status"] = incident_status


# =========================================
# GROUND TRUTH
# =========================================

transactions["incident_ground_truth"] = 0

incident_transactions["incident_ground_truth"] = 1


# =========================================
# ERROR CODES
# =========================================

transactions["error_code"] = None
incident_transactions["error_code"] = None

normal_failed_mask = (
    transactions["status"] == "FAILED"
)

incident_failed_mask = (
    incident_transactions["status"] == "FAILED"
)

transactions.loc[
    normal_failed_mask,
    "error_code"
] = np.random.choice(
    error_codes,
    normal_failed_mask.sum()
)

incident_transactions.loc[
    incident_failed_mask,
    "error_code"
] = np.random.choice(
    error_codes,
    incident_failed_mask.sum()
)


# =========================================
# RETRY COUNT
# =========================================

transactions["retry_count"] = 0
incident_transactions["retry_count"] = 0

transactions.loc[
    normal_failed_mask,
    "retry_count"
] = np.random.choice(
    [1, 2, 3],
    size=normal_failed_mask.sum(),
    p=[0.60, 0.30, 0.10]
)

incident_transactions.loc[
    incident_failed_mask,
    "retry_count"
] = np.random.choice(
    [1, 2, 3],
    size=incident_failed_mask.sum(),
    p=[0.60, 0.30, 0.10]
)


# =========================================
# COMBINE DATA
# =========================================

transactions = pd.concat(
    [
        transactions,
        incident_transactions
    ],
    ignore_index=True
)


# =========================================
# SHUFFLE
# =========================================

transactions = transactions.sample(
    frac=1,
    random_state=42
).reset_index(drop=True)


# =========================================
# SAVE
# =========================================

transactions.to_csv(
    OUTPUT_PATH,
    index=False
)


# =========================================
# REPORT
# =========================================

print(transactions.head())

print("\nDataset shape:")
print(transactions.shape)

print("\nPayment status:")
print(transactions["status"].value_counts())

overall_success = (
    transactions["status"] == "SUCCESS"
).mean()

print("\nOverall success rate:")
print(
    round(overall_success * 100, 2),
    "%"
)

incident_data = transactions[
    transactions["incident_ground_truth"] == 1
]

print("\nIncident transactions:")
print(len(incident_data))

incident_success = (
    incident_data["status"] == "SUCCESS"
).mean()

print("\nIncident success rate:")
print(
    round(incident_success * 100, 2),
    "%"
)

print("\nIncident time:")
print("2026-07-23 19:00 → 20:00")

print("\nIncident route:")
print("UPI + Bank_X + Android")

print(f"\nDataset saved to: {OUTPUT_PATH}")