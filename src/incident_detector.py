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
# BUILD SEGMENTS
# =========================================

segments = (
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
                transactions.loc[x.index, "status"] == "FAILED"
            ].sum()
        )
    )
    .reset_index()
)


# =========================================
# SUCCESS RATE
# =========================================

segments["success_rate"] = (
    segments["successful_transactions"]
    / segments["total_transactions"]
)


# =========================================
# GLOBAL BASELINE
# =========================================

global_success_rate = (
    transactions["status"] == "SUCCESS"
).mean()


# =========================================
# FILTER VERY SMALL GROUPS
# =========================================
#
# Small samples create noisy percentages.
# =========================================

segments = segments[
    segments["total_transactions"] >= 20
].copy()


# =========================================
# EXPECTED SUCCESS
# =========================================

segments["expected_successes"] = (
    segments["total_transactions"]
    * global_success_rate
)


# =========================================
# BINOMIAL STANDARD DEVIATION
# =========================================

segments["std_dev"] = np.sqrt(
    segments["total_transactions"]
    * global_success_rate
    * (1 - global_success_rate)
)


# =========================================
# Z-SCORE
# =========================================

segments["z_score"] = (
    segments["successful_transactions"]
    - segments["expected_successes"]
) / segments["std_dev"]


# =========================================
# PERFORMANCE DEGRADATION
# =========================================

segments["degradation"] = (
    global_success_rate
    - segments["success_rate"]
)


segments["degradation_percentage_points"] = (
    segments["degradation"] * 100
)


# =========================================
# REVENUE AT RISK
# =========================================

segments["revenue_at_risk"] = (
    segments["failed_amount"]
)


# =========================================
# ANOMALY SCORE
# =========================================
#
# We combine:
#   statistical abnormality
#   degradation
#   transaction volume
#
# Higher = more suspicious.
# =========================================

segments["anomaly_score"] = (
    (-segments["z_score"])
    * segments["degradation"].clip(lower=0)
    * np.log1p(segments["total_transactions"])
)


# =========================================
# ONLY NEGATIVE Z-SCORES
# =========================================

anomalies = segments[
    segments["z_score"] < 0
].copy()


# =========================================
# RANK
# =========================================

anomalies = anomalies.sort_values(
    "anomaly_score",
    ascending=False
)


# =========================================
# DISPLAY
# =========================================

print("\n=========================================")
print("AUTOMATIC INCIDENT DETECTION")
print("=========================================")

print("\nGlobal success rate:")
print(
    round(global_success_rate * 100, 2),
    "%"
)


print("\nTop suspicious segments:\n")

if anomalies.empty:

    print("No suspicious segments detected.")

else:

    output_columns = [
        "time_window",
        "payment_method",
        "bank",
        "device_type",
        "total_transactions",
        "successful_transactions",
        "failed_transactions",
        "success_rate",
        "degradation_percentage_points",
        "z_score",
        "anomaly_score",
        "revenue_at_risk"
    ]

    print(
        anomalies[
            output_columns
        ]
        .head(20)
        .to_string(index=False)
    )