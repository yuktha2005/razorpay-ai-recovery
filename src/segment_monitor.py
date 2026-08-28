import pandas as pd


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
# CREATE TIME FEATURES
# -----------------------------------------

transactions["hour"] = transactions["timestamp"].dt.hour

transactions["time_window"] = transactions[
    "timestamp"
].dt.floor("1h")


# -----------------------------------------
# SEGMENTED PAYMENT ANALYSIS
# -----------------------------------------

segment_analysis = (
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

        total_amount=("amount", "sum"),

        failed_amount=(
            "amount",
            lambda x: x[
                transactions.loc[x.index, "status"] == "FAILED"
            ].sum()
        )
    )
    .reset_index()
)


# -----------------------------------------
# SUCCESS RATE
# -----------------------------------------

segment_analysis["success_rate"] = (
    segment_analysis["successful_transactions"]
    / segment_analysis["total_transactions"]
)


# -----------------------------------------
# SHOW LOW SUCCESS SEGMENTS
# -----------------------------------------

suspicious_segments = segment_analysis[
    (segment_analysis["total_transactions"] >= 10)
    & (segment_analysis["success_rate"] < 0.85)
].sort_values(
    "success_rate"
)


print("\nSuspicious payment segments:\n")

print(
    suspicious_segments.head(20).to_string(
        index=False
    )
)