import pandas as pd
import numpy as np


# =========================================
# CONFIGURATION
# =========================================

DATA_PATH = "data/transactions.csv"

MIN_TRANSACTIONS = 20
DEGRADATION_THRESHOLD = 10
MIN_HISTORICAL_TRANSACTIONS = 100


# =========================================
# LOAD DATA
# =========================================

def load_data():

    df = pd.read_csv(DATA_PATH)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        format="mixed"
    )

    return df


# =========================================
# DETECT INCIDENT
# =========================================

def detect_incident(df):

    df = df.copy()

    # -------------------------------------
    # Create hourly windows
    # -------------------------------------

    df["time_window"] = (
        df["timestamp"].dt.floor("1h")
    )

    # -------------------------------------
    # Numeric flags
    # -------------------------------------

    df["success_flag"] = (
        df["status"] == "SUCCESS"
    ).astype(int)

    df["failure_flag"] = (
        df["status"] == "FAILED"
    ).astype(int)

    df["failed_amount_value"] = (
        df["amount"]
        .where(
            df["status"] == "FAILED",
            0
        )
    )

    route_columns = [
        "payment_method",
        "bank",
        "device_type"
    ]

    group_columns = [
        "time_window",
        *route_columns
    ]

    # -------------------------------------
    # HOURLY ROUTE PERFORMANCE
    # -------------------------------------

    hourly = (
        df
        .groupby(group_columns)
        .agg(
            transactions=(
                "transaction_id",
                "count"
            ),

            successes=(
                "success_flag",
                "sum"
            ),

            failures=(
                "failure_flag",
                "sum"
            ),

            failed_amount=(
                "failed_amount_value",
                "sum"
            )
        )
        .reset_index()
    )

    hourly["success_rate"] = (
        hourly["successes"]
        / hourly["transactions"]
    )

    # -------------------------------------
    # ROUTE-WIDE TOTALS
    # -------------------------------------

    route_totals = (
        df
        .groupby(route_columns)
        .agg(
            total_transactions=(
                "transaction_id",
                "count"
            ),

            total_successes=(
                "success_flag",
                "sum"
            )
        )
        .reset_index()
    )

    # -------------------------------------
    # MERGE ROUTE TOTALS
    # -------------------------------------

    hourly = hourly.merge(
        route_totals,
        on=route_columns,
        how="left"
    )

    # -------------------------------------
    # HISTORICAL BASELINE
    #
    # Exclude the current hour.
    # -------------------------------------

    hourly["historical_transactions"] = (
        hourly["total_transactions"]
        - hourly["transactions"]
    )

    hourly["historical_successes"] = (
        hourly["total_successes"]
        - hourly["successes"]
    )

    hourly["baseline_success_rate"] = (
        hourly["historical_successes"]
        / hourly["historical_transactions"]
    )

    # -------------------------------------
    # FILTER LOW-VOLUME ROUTES
    # -------------------------------------

    candidates = hourly[
        hourly["transactions"]
        >= MIN_TRANSACTIONS
    ].copy()

    candidates = candidates[
        candidates["historical_transactions"]
        >= MIN_HISTORICAL_TRANSACTIONS
    ].copy()

    # -------------------------------------
    # DEGRADATION
    # -------------------------------------

    candidates["degradation"] = (
        candidates["baseline_success_rate"]
        - candidates["success_rate"]
    )

    candidates["degradation_percentage_points"] = (
        candidates["degradation"]
        * 100
    )

    # -------------------------------------
    # DETECTION THRESHOLD
    # -------------------------------------

    candidates = candidates[
        candidates["degradation_percentage_points"]
        >= DEGRADATION_THRESHOLD
    ].copy()

    if candidates.empty:
        return None

    # -------------------------------------
    # INCIDENT SCORE
    #
    # Combines:
    # - degradation
    # - transaction volume
    # - failed transaction value
    # -------------------------------------

    candidates["incident_score"] = (
        candidates["degradation"].clip(lower=0)
        * np.sqrt(
            candidates["transactions"]
        )
        * np.log1p(
            candidates["failed_amount"]
        )
    )

    # -------------------------------------
    # SORT CANDIDATES
    # -------------------------------------

    candidates = candidates.sort_values(
        [
            "incident_score",
            "failed_amount",
            "transactions"
        ],
        ascending=False
    )

    return candidates.iloc[0].to_dict()


# =========================================
# ROOT CAUSE ANALYSIS
# =========================================

def analyze_root_cause(
    df,
    incident
):

    start = pd.Timestamp(
        incident["time_window"]
    )

    end = (
        start
        + pd.Timedelta(hours=1)
    )

    # -------------------------------------
    # Incident window
    # -------------------------------------

    incident_data = df[
        (df["timestamp"] >= start)
        & (df["timestamp"] < end)
    ].copy()

    # -------------------------------------
    # Historical data
    # -------------------------------------

    historical = df[
        ~(
            (df["timestamp"] >= start)
            & (df["timestamp"] < end)
        )
    ].copy()

    # -------------------------------------
    # Exact affected route
    # -------------------------------------

    route = incident_data[
        (incident_data["payment_method"]
         == incident["payment_method"])
        &
        (incident_data["bank"]
         == incident["bank"])
        &
        (incident_data["device_type"]
         == incident["device_type"])
    ]

    historical_route = historical[
        (historical["payment_method"]
         == incident["payment_method"])
        &
        (historical["bank"]
         == incident["bank"])
        &
        (historical["device_type"]
         == incident["device_type"])
    ]

    # -------------------------------------
    # Failure rates
    # -------------------------------------

    route_failure_rate = (
        (route["status"] == "FAILED").mean()
    )

    baseline_failure_rate = (
        (historical_route["status"] == "FAILED").mean()
    )

    route_degradation = (
        route_failure_rate
        - baseline_failure_rate
    )

    # -------------------------------------
    # Failure reason analysis
    # -------------------------------------

    failed_incident = incident_data[
        incident_data["status"] == "FAILED"
    ]

    error_analysis = (
        failed_incident["error_code"]
        .value_counts()
        .rename_axis("error_code")
        .reset_index(
            name="failures"
        )
    )

    if not error_analysis.empty:

        error_analysis["percentage"] = (
            error_analysis["failures"]
            / len(failed_incident)
            * 100
        )

    # -------------------------------------
    # Location analysis
    # -------------------------------------

    location_analysis = (
        route["location"]
        .value_counts()
        .rename_axis("location")
        .reset_index(
            name="transactions"
        )
    )

    # -------------------------------------
    # Confidence score
    # -------------------------------------

    confidence = 0

    if route_degradation >= 0.20:

        confidence += 50

    elif route_degradation >= 0.10:

        confidence += 35

    else:

        confidence += 20

    if len(route) >= 100:

        confidence += 25

    elif len(route) >= 50:

        confidence += 15

    if incident[
        "degradation_percentage_points"
    ] >= 20:

        confidence += 25

    elif incident[
        "degradation_percentage_points"
    ] >= 10:

        confidence += 15

    confidence = min(
        confidence,
        99
    )

    return {
        "route": {
            "payment_method":
                incident["payment_method"],

            "bank":
                incident["bank"],

            "device_type":
                incident["device_type"]
        },

        "route_transactions":
            len(route),

        "route_failure_rate":
            route_failure_rate,

        "baseline_failure_rate":
            baseline_failure_rate,

        "route_degradation":
            route_degradation,

        "confidence":
            confidence,

        "error_analysis":
            error_analysis,

        "location_analysis":
            location_analysis
    }


# =========================================
# REVENUE IMPACT
# =========================================

def calculate_revenue_impact(
    df,
    incident
):

    start = pd.Timestamp(
        incident["time_window"]
    )

    end = (
        start
        + pd.Timedelta(hours=1)
    )

    # -------------------------------------
    # Exact affected route
    # -------------------------------------

    route = df[
        (df["payment_method"]
         == incident["payment_method"])
        &
        (df["bank"]
         == incident["bank"])
        &
        (df["device_type"]
         == incident["device_type"])
    ]

    incident_route = route[
        (route["timestamp"] >= start)
        & (route["timestamp"] < end)
    ]

    historical_route = route[
        ~(
            (route["timestamp"] >= start)
            & (route["timestamp"] < end)
        )
    ]

    if historical_route.empty:
        return None

    # -------------------------------------
    # Baseline failure rate
    # -------------------------------------

    baseline_failure_rate = (
        historical_route["status"]
        == "FAILED"
    ).mean()

    # -------------------------------------
    # Actual failures
    # -------------------------------------

    actual_failures = (
        incident_route["status"]
        == "FAILED"
    ).sum()

    # -------------------------------------
    # Expected failures
    # -------------------------------------

    expected_failures = (
        len(incident_route)
        * baseline_failure_rate
    )

    # -------------------------------------
    # Excess failures
    # -------------------------------------

    excess_failures = max(
        0,
        actual_failures
        - expected_failures
    )

    # -------------------------------------
    # Actual failed amount
    # -------------------------------------

    failed_amount = incident_route.loc[
        incident_route["status"] == "FAILED",
        "amount"
    ].sum()

    # -------------------------------------
    # Historical average transaction value
    # -------------------------------------

    average_amount = (
        historical_route["amount"]
        .mean()
    )

    # -------------------------------------
    # Expected failed transaction value
    # -------------------------------------

    expected_failed_amount = (
        expected_failures
        * average_amount
    )

    # -------------------------------------
    # Revenue at risk
    # -------------------------------------

    revenue_at_risk = max(
        0,
        failed_amount
        - expected_failed_amount
    )

    return {
        "actual_failures":
            int(actual_failures),

        "expected_failures":
            float(expected_failures),

        "excess_failures":
            float(excess_failures),

        "failed_amount":
            float(failed_amount),

        "revenue_at_risk":
            float(revenue_at_risk)
    }


# =========================================
# RECOVERY RECOMMENDATION
# =========================================

def recommend_recovery(
    df,
    incident
):

    start = pd.Timestamp(
        incident["time_window"]
    )

    end = (
        start
        + pd.Timedelta(hours=1)
    )

    # -------------------------------------
    # Historical data
    #
    # Exclude incident window.
    # -------------------------------------

    historical = df[
        ~(
            (df["timestamp"] >= start)
            & (df["timestamp"] < end)
        )
    ].copy()

    # -------------------------------------
    # Match payment method + device.
    # -------------------------------------

    method_device_data = historical[
        (historical["payment_method"]
         == incident["payment_method"])
        &
        (historical["device_type"]
         == incident["device_type"])
    ]

    # -------------------------------------
    # Historical bank performance
    # -------------------------------------

    bank_stats = (
        method_device_data
        .groupby("bank")
        .agg(
            transactions=(
                "transaction_id",
                "count"
            ),

            successes=(
                "status",
                lambda x:
                (x == "SUCCESS").sum()
            )
        )
        .reset_index()
    )

    if bank_stats.empty:
        return None

    bank_stats["success_rate"] = (
        bank_stats["successes"]
        / bank_stats["transactions"]
    )

    # -------------------------------------
    # Remove affected bank
    # -------------------------------------

    alternatives = bank_stats[
        (bank_stats["bank"]
         != incident["bank"])
        &
        (
            bank_stats["transactions"]
            >= MIN_HISTORICAL_TRANSACTIONS
        )
    ].copy()

    if alternatives.empty:
        return None

    # -------------------------------------
    # Rank alternatives
    # -------------------------------------

    alternatives = alternatives.sort_values(
        [
            "success_rate",
            "transactions"
        ],
        ascending=[
            False,
            False
        ]
    )

    best = alternatives.iloc[0]

    # -------------------------------------
    # Current incident success rate
    # -------------------------------------

    current_rate = (
        incident["success_rate"]
    )

    # -------------------------------------
    # Improvement
    # -------------------------------------

    improvement = (
        best["success_rate"]
        - current_rate
    )

    # -------------------------------------
    # Potential additional successes
    # -------------------------------------

    potential_successes = max(
        0,
        incident["transactions"]
        * improvement
    )

    # -------------------------------------
    # Historical affected-route data
    # -------------------------------------

    route_data = historical[
        (historical["payment_method"]
         == incident["payment_method"])
        &
        (historical["bank"]
         == incident["bank"])
        &
        (historical["device_type"]
         == incident["device_type"])
    ].copy()

    if route_data.empty:
        return None

    # -------------------------------------
    # Historical average transaction value
    # -------------------------------------

    average_amount = (
        route_data["amount"].mean()
    )

    # -------------------------------------
    # Estimated recovery
    # -------------------------------------

    estimated_recovery = (
        potential_successes
        * average_amount
    )

    # -------------------------------------
    # Historical comparable transactions
    # -------------------------------------

    historical_transactions = int(
        best["transactions"]
    )

    return {
        "alternative_bank":
            best["bank"],

        "alternative_success_rate":
            float(
                best["success_rate"]
            ),

        "current_success_rate":
            float(
                current_rate
            ),

        "potential_successes":
            float(
                potential_successes
            ),

        "estimated_recovery":
            float(
                estimated_recovery
            ),

        "historical_transactions":
            historical_transactions,

        "confidence":
            99.0
    }


# =========================================
# POLICY ENGINE
# =========================================

def evaluate_policy(
    df,
    incident,
    recovery,
    recovery_attempts=0
):

    # Import here to avoid circular imports.
    from policy_engine import (
        evaluate_recovery_policy
    )

    return evaluate_recovery_policy(
        df,
        incident,
        recovery,
        recovery_attempts
    )


# =========================================
# COMPLETE AGENT
# =========================================

def run_agent():

    df = load_data()

    incident = detect_incident(
        df
    )

    print("\n")
    print("=" * 60)
    print("             AI PAYMENT RECOVERY AGENT")
    print("=" * 60)

    # =====================================
    # DETECTION
    # =====================================

    if incident is None:

        print(
            "\n🟢 NO INCIDENT"
        )

        print(
            "No significant payment degradation detected."
        )

        print("\n")
        print("=" * 60)
        print("                 COMPLETE")
        print("=" * 60)

        return None

    print("\n🔴 INCIDENT DETECTED")

    print(
        f"\nRoute:"
        f" {incident['payment_method']}"
        f" → {incident['bank']}"
        f" → {incident['device_type']}"
    )

    print(
        f"Time:"
        f" {incident['time_window']}"
    )

    print(
        f"Transactions:"
        f" {int(incident['transactions'])}"
    )

    print(
        f"Success rate:"
        f" {incident['success_rate'] * 100:.2f}%"
    )

    print(
        f"Baseline:"
        f" {incident['baseline_success_rate'] * 100:.2f}%"
    )

    print(
        f"Degradation:"
        f" {incident['degradation_percentage_points']:.2f} pp"
    )

    # =====================================
    # ROOT CAUSE
    # =====================================

    root_cause = analyze_root_cause(
        df,
        incident
    )

    print("\n🧠 ROOT CAUSE")

    print(
        f"Route:"
        f" {incident['payment_method']}"
        f" → {incident['bank']}"
        f" → {incident['device_type']}"
    )

    print(
        f"Confidence:"
        f" {root_cause['confidence']}%"
    )

    print(
        f"Route failure:"
        f" {root_cause['route_failure_rate'] * 100:.2f}%"
    )

    print(
        f"Normal failure:"
        f" {root_cause['baseline_failure_rate'] * 100:.2f}%"
    )

    if not root_cause[
        "error_analysis"
    ].empty:

        print(
            "\nTop failure reasons:"
        )

        print(
            root_cause[
                "error_analysis"
            ]
            .head(5)
            .to_string(index=False)
        )

    # =====================================
    # BUSINESS IMPACT
    # =====================================

    impact = calculate_revenue_impact(
        df,
        incident
    )

    print("\n💰 BUSINESS IMPACT")

    if impact:

        print(
            f"Excess failures:"
            f" {impact['excess_failures']:.1f}"
        )

        print(
            f"Revenue at risk:"
            f" ₹{impact['revenue_at_risk']:,.2f}"
        )

    else:

        print(
            "Unable to calculate revenue impact."
        )

    # =====================================
    # RECOVERY RECOMMENDATION
    # =====================================

    recovery = recommend_recovery(
        df,
        incident
    )

    print(
        "\n⚡ RECOVERY RECOMMENDATION"
    )

    if recovery:

        print(
            f"Alternative bank:"
            f" {recovery['alternative_bank']}"
        )

        print(
            f"Historical success:"
            f" {recovery['alternative_success_rate'] * 100:.2f}%"
        )

        print(
            f"Potential additional successes:"
            f" {recovery['potential_successes']:.1f}"
        )

        print(
            f"Estimated recovery:"
            f" ₹{recovery['estimated_recovery']:,.2f}"
        )

        print(
            f"Historical comparable transactions:"
            f" {recovery['historical_transactions']:,}"
        )

    else:

        print(
            "No suitable alternative route found."
        )

    # =====================================
    # POLICY GATE
    # =====================================

    print("\n🛡️ POLICY GATE")

    if recovery:

        policy_result = evaluate_policy(
            df,
            incident,
            recovery,
            recovery_attempts=0
        )

        print(
            f"Decision:"
            f" {policy_result['decision']}"
        )

        print(
            f"Approved:"
            f" {policy_result['approved']}"
        )

        print(
            f"Reason:"
            f" {policy_result['reason']}"
        )

        print(
            "\nPolicy checks:"
        )

        for check in policy_result[
            "checks"
        ]:

            status = (
                "PASS"
                if check["passed"]
                else
                "FAIL"
            )

            print(
                f"  [{status}] "
                f"{check['check']}"
            )

    else:

        policy_result = {
            "decision": "STOP",
            "approved": False,
            "reason": (
                "No recovery recommendation "
                "available."
            ),
            "checks": []
        }

        print(
            "Decision: STOP"
        )

        print(
            "Approved: False"
        )

        print(
            "Reason: No recovery recommendation available."
        )

    # =====================================
    # FINAL AGENT ACTION
    # =====================================

    print("\n⚡ AGENT ACTION")

    if (
        recovery
        and policy_result["approved"]
    ):

        print(
            f"RECOVER → Prefer "
            f"{recovery['alternative_bank']} "
            f"for eligible "
            f"{incident['payment_method']} + "
            f"{incident['device_type']} traffic."
        )

    elif policy_result["decision"] == "ESCALATE":

        print(
            "ESCALATE → Human review required."
        )

    else:

        print(
            "STOP → No automated recovery action permitted."
        )

    # =====================================
    # COMPLETE
    # =====================================

    print("\n")
    print("=" * 60)
    print("                 COMPLETE")
    print("=" * 60)

    return {
        "incident":
            incident,

        "root_cause":
            root_cause,

        "impact":
            impact,

        "recovery":
            recovery,

        "policy":
            policy_result
    }


# =========================================
# MAIN
# =========================================

if __name__ == "__main__":

    run_agent()