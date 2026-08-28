import pandas as pd
import numpy as np


# =========================================
# LOAD DATA
# =========================================

DATA_PATH = "data/transactions.csv"

transactions = pd.read_csv(DATA_PATH)

transactions["timestamp"] = pd.to_datetime(
    transactions["timestamp"],
    format="mixed"
)


# =========================================
# CREATE HOURLY WINDOWS
# =========================================

transactions["time_window"] = (
    transactions["timestamp"].dt.floor("1h")
)


# =========================================
# GROUP PAYMENT ROUTES
# =========================================

route_hourly = (
    transactions
    .groupby(
        [
            "time_window",
            "payment_method",
            "bank",
            "device_type"
        ]
    )
    .agg(
        transactions=("transaction_id", "count"),

        successes=(
            "status",
            lambda x: (x == "SUCCESS").sum()
        ),

        failures=(
            "status",
            lambda x: (x == "FAILED").sum()
        ),

        failed_amount=(
            "amount",
            lambda x: x[
                transactions.loc[x.index, "status"] == "FAILED"
            ].sum()
        )
    )
    .reset_index()
)


# =========================================
# SUCCESS RATE
# =========================================

route_hourly["success_rate"] = (
    route_hourly["successes"]
    / route_hourly["transactions"]
)


# =========================================
# ROUTE-LEVEL BASELINE
# =========================================
#
# Calculate the historical success rate for
# each route WITHOUT including the current
# hour being evaluated.
# =========================================

route_totals = (
    route_hourly
    .groupby(
        [
            "payment_method",
            "bank",
            "device_type"
        ]
    )
    .agg(
        total_successes=("successes", "sum"),
        total_transactions=("transactions", "sum")
    )
    .reset_index()
)


# -----------------------------------------
# Exclude each hour from its own baseline
# -----------------------------------------

route_hourly = route_hourly.merge(
    route_totals,
    on=[
        "payment_method",
        "bank",
        "device_type"
    ],
    how="left"
)


route_hourly["baseline_successes"] = (
    route_hourly["total_successes"]
    - route_hourly["successes"]
)

route_hourly["baseline_transactions"] = (
    route_hourly["total_transactions"]
    - route_hourly["transactions"]
)


route_hourly["baseline_success_rate"] = (
    route_hourly["baseline_successes"]
    / route_hourly["baseline_transactions"]
)




# =========================================
# DEGRADATION
# =========================================

route_hourly["degradation"] = (
    route_hourly["baseline_success_rate"]
    - route_hourly["success_rate"]
)

route_hourly["degradation_percentage_points"] = (
    route_hourly["degradation"] * 100
)


# =========================================
# FILTER LOW-VOLUME WINDOWS
# =========================================

route_hourly = route_hourly[
    route_hourly["transactions"] >= 20
].copy()


# =========================================
# DETECTION SCORE
# =========================================
#
# Combine:
# - degradation
# - transaction volume
#
# Larger + more severe = higher score.
# =========================================

route_hourly["detection_score"] = (
    route_hourly["degradation"].clip(lower=0)
    * np.log1p(route_hourly["transactions"])
)


# =========================================
# FIND CANDIDATES
# =========================================

candidates = route_hourly[
    route_hourly["degradation_percentage_points"] >= 10
].copy()


candidates = candidates.sort_values(
    "detection_score",
    ascending=False
)


# =========================================
# DISPLAY
# =========================================

print("\n=========================================")
print("TEMPORAL PAYMENT INCIDENT DETECTOR")
print("=========================================")

print("\nTop detected degradation events:\n")


if candidates.empty:

    print("No significant degradation detected.")

else:

    print(
        candidates[
            [
                "time_window",
                "payment_method",
                "bank",
                "device_type",
                "transactions",
                "success_rate",
                "baseline_success_rate",
                "degradation_percentage_points",
                "failed_amount",
                "detection_score"
            ]
        ]
        .head(20)
        .to_string(index=False)
    )