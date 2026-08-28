import pandas as pd


# -----------------------------------------
# LOAD PAYMENT DATA
# -----------------------------------------

DATA_PATH = "data/transactions.csv"

transactions = pd.read_csv(DATA_PATH)

transactions["timestamp"] = pd.to_datetime(
    transactions["timestamp"],
    format="mixed"
)


# -----------------------------------------
# CALCULATE 15-MINUTE METRICS
# -----------------------------------------

transactions["time_window"] = transactions["timestamp"].dt.floor("15min")

monitoring = (
    transactions
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
        total_amount=("amount", "sum"),
        failed_amount=(
            "amount",
            lambda x: x[transactions.loc[x.index, "status"] == "FAILED"].sum()
        )
    )
    .reset_index()
)


# -----------------------------------------
# SUCCESS RATE
# -----------------------------------------

monitoring["success_rate"] = (
    monitoring["successful_transactions"]
    / monitoring["total_transactions"]
)


# -----------------------------------------
# DISPLAY RESULTS
# -----------------------------------------

print("\nPayment Monitoring:")
print(monitoring.head(20).to_string(index=False))

print("\nOverall average success rate:")
print(
    round(monitoring["success_rate"].mean() * 100, 2),
    "%"
)