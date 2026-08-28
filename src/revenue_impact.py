import pandas as pd


# =========================================
# CONFIGURATION
# =========================================

DATA_PATH = "data/transactions.csv"

INCIDENT_START = pd.Timestamp(
    "2026-07-23 19:00:00"
)

INCIDENT_END = pd.Timestamp(
    "2026-07-23 20:00:00"
)

PAYMENT_METHOD = "UPI"
BANK = "Bank_X"
DEVICE = "Android"


# =========================================
# LOAD DATA
# =========================================

transactions = pd.read_csv(DATA_PATH)

transactions["timestamp"] = pd.to_datetime(
    transactions["timestamp"],
    format="mixed"
)


# =========================================
# SELECT AFFECTED ROUTE
# =========================================

route = transactions[
    (transactions["payment_method"] == PAYMENT_METHOD)
    & (transactions["bank"] == BANK)
    & (transactions["device_type"] == DEVICE)
].copy()


# =========================================
# INCIDENT DATA
# =========================================

incident = route[
    (route["timestamp"] >= INCIDENT_START)
    & (route["timestamp"] < INCIDENT_END)
].copy()


# =========================================
# BASELINE DATA
# =========================================

baseline = route[
    ~(
        (route["timestamp"] >= INCIDENT_START)
        & (route["timestamp"] < INCIDENT_END)
    )
].copy()


# =========================================
# BASELINE FAILURE RATE
# =========================================

baseline_failure_rate = (
    baseline["status"] == "FAILED"
).mean()


# =========================================
# INCIDENT METRICS
# =========================================

incident_transactions = len(incident)

incident_failures = (
    incident["status"] == "FAILED"
).sum()

incident_successes = (
    incident["status"] == "SUCCESS"
).sum()


incident_failure_rate = (
    incident_failures
    / incident_transactions
)


# =========================================
# EXPECTED FAILURES
# =========================================

expected_failures = (
    incident_transactions
    * baseline_failure_rate
)


# =========================================
# EXCESS FAILURES
# =========================================

excess_failures = max(
    0,
    incident_failures - expected_failures
)


# =========================================
# ACTUAL FAILED AMOUNT
# =========================================

actual_failed_amount = incident.loc[
    incident["status"] == "FAILED",
    "amount"
].sum()


# =========================================
# EXPECTED FAILED AMOUNT
# =========================================

average_transaction_amount = (
    baseline["amount"].mean()
)

expected_failed_amount = (
    expected_failures
    * average_transaction_amount
)


# =========================================
# REVENUE AT RISK
# =========================================

revenue_at_risk = max(
    0,
    actual_failed_amount
    - expected_failed_amount
)


# =========================================
# DISPLAY
# =========================================

print("\n=========================================")
print("REVENUE IMPACT ANALYSIS")
print("=========================================")

print("\nAffected route:")
print(
    f"{PAYMENT_METHOD} → {BANK} → {DEVICE}"
)

print("\nIncident window:")
print(
    f"{INCIDENT_START} → {INCIDENT_END}"
)

print("\nIncident transactions:")
print(
    incident_transactions
)

print("\nActual failures:")
print(
    incident_failures
)

print("\nBaseline failure rate:")
print(
    f"{baseline_failure_rate * 100:.2f}%"
)

print("\nExpected failures:")
print(
    f"{expected_failures:.1f}"
)

print("\nExcess failures:")
print(
    f"{excess_failures:.1f}"
)

print("\nActual failed transaction value:")
print(
    f"₹{actual_failed_amount:,.2f}"
)

print("\nEstimated expected failed value:")
print(
    f"₹{expected_failed_amount:,.2f}"
)

print("\nEstimated revenue at risk:")
print(
    f"₹{revenue_at_risk:,.2f}"
)