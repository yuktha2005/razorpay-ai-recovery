import pandas as pd


# =========================================
# CONFIGURATION
# =========================================

DATA_PATH = "data/transactions.csv"

INCIDENT_START = pd.Timestamp("2026-07-23 19:00:00")
INCIDENT_END = pd.Timestamp("2026-07-23 20:00:00")


# =========================================
# LOAD DATA
# =========================================

transactions = pd.read_csv(DATA_PATH)

transactions["timestamp"] = pd.to_datetime(
    transactions["timestamp"],
    format="mixed"
)


# =========================================
# INCIDENT WINDOW
# =========================================

incident = transactions[
    (transactions["timestamp"] >= INCIDENT_START)
    & (transactions["timestamp"] < INCIDENT_END)
].copy()


# =========================================
# BASELINE WINDOW
# =========================================
#
# Use the rest of the dataset as normal
# historical behavior for this first version.
# =========================================

baseline = transactions[
    ~(
        (transactions["timestamp"] >= INCIDENT_START)
        & (transactions["timestamp"] < INCIDENT_END)
    )
].copy()


# =========================================
# HELPER FUNCTION
# =========================================

def calculate_dimension_impact(
    incident_data,
    baseline_data,
    column
):
    """
    Compare failure rates during the incident
    against the normal failure rate for each
    category of a dimension.
    """

    incident_stats = (
        incident_data
        .groupby(column)
        .agg(
            incident_transactions=(
                "transaction_id",
                "count"
            ),
            incident_failures=(
                "status",
                lambda x: (x == "FAILED").sum()
            )
        )
        .reset_index()
    )

    baseline_stats = (
        baseline_data
        .groupby(column)
        .agg(
            baseline_transactions=(
                "transaction_id",
                "count"
            ),
            baseline_failures=(
                "status",
                lambda x: (x == "FAILED").sum()
            )
        )
        .reset_index()
    )

    result = incident_stats.merge(
        baseline_stats,
        on=column,
        how="left"
    )

    result["incident_failure_rate"] = (
        result["incident_failures"]
        / result["incident_transactions"]
    )

    result["baseline_failure_rate"] = (
        result["baseline_failures"]
        / result["baseline_transactions"]
    )

    result["failure_rate_increase"] = (
        result["incident_failure_rate"]
        - result["baseline_failure_rate"]
    )

    result["impact_score"] = (
        result["failure_rate_increase"]
        * result["incident_transactions"]
    )

    return result.sort_values(
        "impact_score",
        ascending=False
    )


# =========================================
# ANALYZE DIMENSIONS
# =========================================

dimensions = [
    "payment_method",
    "bank",
    "device_type",
    "location",
    "error_code"
]


print("\n=========================================")
print("ROOT CAUSE ANALYSIS")
print("=========================================")

print("\nIncident window:")
print(
    f"{INCIDENT_START} → {INCIDENT_END}"
)

print("\nIncident transactions:")
print(len(incident))


# =========================================
# ANALYZE EACH DIMENSION
# =========================================

for dimension in dimensions:

    print("\n-----------------------------------------")
    print(f"Dimension: {dimension}")
    print("-----------------------------------------")

    analysis = calculate_dimension_impact(
        incident,
        baseline,
        dimension
    )

    print(
        analysis.head(5).to_string(
            index=False
        )
    )


# =========================================
# ROUTE-LEVEL ANALYSIS
# =========================================

print("\n=========================================")
print("PAYMENT ROUTE ANALYSIS")
print("=========================================")


route_analysis = calculate_dimension_impact(
    incident,
    baseline,
    [
        "payment_method",
        "bank",
        "device_type"
    ]
)


print(
    route_analysis
    .head(10)
    .to_string(index=False)
)


# =========================================
# TOP ROOT CAUSE CANDIDATE
# =========================================

if not route_analysis.empty:

    top = route_analysis.iloc[0]

    print("\n=========================================")
    print("TOP ROOT CAUSE CANDIDATE")
    print("=========================================")

    print(
        f"Payment method : {top['payment_method']}"
    )

    print(
        f"Bank           : {top['bank']}"
    )

    print(
        f"Device         : {top['device_type']}"
    )

    print(
        f"Incident failure rate : "
        f"{top['incident_failure_rate'] * 100:.2f}%"
    )

    print(
        f"Baseline failure rate : "
        f"{top['baseline_failure_rate'] * 100:.2f}%"
    )

    print(
        f"Failure increase      : "
        f"{top['failure_rate_increase'] * 100:.2f} percentage points"
    )

    print(
        f"Incident transactions : "
        f"{int(top['incident_transactions'])}"
    )