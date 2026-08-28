import pandas as pd
import numpy as np


# -----------------------------------------
# LOAD DATA
# -----------------------------------------

DATA_PATH = "data/transactions.csv"

transactions = pd.read_csv(DATA_PATH)

transactions["timestamp"] = pd.to_datetime(
    transactions["timestamp"],
    format="mixed"
)


# -----------------------------------------
# CREATE HOURLY TIME WINDOW
# -----------------------------------------

transactions["time_window"] = transactions[
    "timestamp"
].dt.floor("1h")


# -----------------------------------------
# SELECT A PAYMENT SEGMENT
# -----------------------------------------

segment = transactions[
    (transactions["payment_method"] == "UPI")
    & (transactions["bank"] == "Bank_X")
    & (transactions["device_type"] == "Android")
].copy()


# -----------------------------------------
# HOURLY PERFORMANCE
# -----------------------------------------

hourly = (
    segment
    .groupby("time_window")
    .agg(
        total_transactions=("transaction_id", "count"),

        successful_transactions=(
            "status",
            lambda x: (x == "SUCCESS").sum()
        ),

        failed_transactions=(
            "status",
            lambda x: (x == "FAILED").sum()
        ),

        failed_amount=(
            "amount",
            lambda x: x[
                segment.loc[x.index, "status"] == "FAILED"
            ].sum()
        )
    )
    .reset_index()
)


# -----------------------------------------
# SUCCESS RATE
# -----------------------------------------

hourly["success_rate"] = (
    hourly["successful_transactions"]
    / hourly["total_transactions"]
)


# -----------------------------------------
# HISTORICAL BASELINE
# -----------------------------------------

baseline_rate = hourly["success_rate"].median()


# -----------------------------------------
# DEVIATION FROM BASELINE
# -----------------------------------------

hourly["deviation"] = (
    hourly["success_rate"] - baseline_rate
)


hourly["deviation_percentage_points"] = (
    hourly["deviation"] * 100
)


# -----------------------------------------
# DISPLAY
# -----------------------------------------

print("\nSegment:")
print("UPI + Bank_X + Android")

print("\nHistorical baseline:")
print(
    round(baseline_rate * 100, 2),
    "%"
)


print("\nHourly performance:\n")

print(
    hourly[
        [
            "time_window",
            "total_transactions",
            "successful_transactions",
            "failed_transactions",
            "success_rate",
            "deviation_percentage_points"
        ]
    ]
    .to_string(index=False)
)


# -----------------------------------------
# LOW PERFORMANCE WINDOWS
# -----------------------------------------

alerts = hourly[
    hourly["deviation_percentage_points"] <= -10
]


print("\nPotential degradation windows:\n")

print(
    alerts[
        [
            "time_window",
            "total_transactions",
            "success_rate",
            "deviation_percentage_points"
        ]
    ]
    .to_string(index=False)
)