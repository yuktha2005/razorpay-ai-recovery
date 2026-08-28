import pandas as pd

from agent import (
    load_data,
    detect_incident,
    recommend_recovery
)

from policy_engine import (
    evaluate_recovery_policy
)

from audit_logger import (
    log_recovery_event
)


# =========================================
# CONFIGURATION
# =========================================

MAX_BATCH_SIZE = 1000


# =========================================
# BATCH RECOVERY
# =========================================

def run_batch_recovery(
    df,
    incident,
    recovery,
    batch_size=1000
):
    """
    Simulate bounded recovery across a batch.

    No real payment routing is performed.

    The batch reports:

    - eligible failed transactions
    - simulated recovered transactions
    - expected additional successes
    - recovery rate
    - estimated recovered value
    - policy decision
    """

    if incident is None:
        return None

    if recovery is None:
        return None

    # =====================================
    # POLICY GATE
    # =====================================

    policy_result = evaluate_recovery_policy(
        df,
        incident,
        recovery,
        recovery_attempts=0
    )

    # =====================================
    # INCIDENT WINDOW
    # =====================================

    incident_start = pd.Timestamp(
        incident["time_window"]
    )

    incident_end = (
        incident_start
        + pd.Timedelta(hours=1)
    )

    # =====================================
    # INCIDENT TRANSACTIONS
    # =====================================

    incident_transactions = df[
        (df["timestamp"] >= incident_start)
        &
        (df["timestamp"] < incident_end)
        &
        (df["payment_method"]
         == incident["payment_method"])
        &
        (df["bank"]
         == incident["bank"])
        &
        (df["device_type"]
         == incident["device_type"])
    ].copy()

    if incident_transactions.empty:
        return None

    # =====================================
    # LIMIT BATCH SIZE
    # =====================================

    batch_size = min(
        int(batch_size),
        MAX_BATCH_SIZE,
        len(incident_transactions)
    )

    batch = (
        incident_transactions
        .head(batch_size)
        .copy()
    )

    # =====================================
    # BASIC COUNTS
    # =====================================

    total_transactions = len(batch)

    successful_transactions = (
        batch["status"] == "SUCCESS"
    ).sum()

    failed_transactions = (
        batch["status"] == "FAILED"
    ).sum()

    # =====================================
    # HISTORICAL AFFECTED-ROUTE DATA
    # =====================================

    historical = df[
        ~(
            (df["timestamp"] >= incident_start)
            &
            (df["timestamp"] < incident_end)
        )
    ].copy()

    historical_route = historical[
        (historical["payment_method"]
         == incident["payment_method"])
        &
        (historical["bank"]
         == incident["bank"])
        &
        (historical["device_type"]
         == incident["device_type"])
    ].copy()

    if historical_route.empty:
        return None

    average_transaction_value = (
        historical_route["amount"].mean()
    )

    # =====================================
    # POLICY DECISION
    # =====================================

    if policy_result["decision"] == "RECOVER":

        # ---------------------------------
        # Eligible failed transactions
        # ---------------------------------

        eligible = batch[
            batch["status"] == "FAILED"
        ].copy()

        eligible_transactions = len(
            eligible
        )

        # ---------------------------------
        # Success-rate improvement
        # ---------------------------------

        current_success_rate = float(
            incident["success_rate"]
        )

        alternative_success_rate = float(
            recovery[
                "alternative_success_rate"
            ]
        )

        success_rate_improvement = (
            alternative_success_rate
            - current_success_rate
        )

        # ---------------------------------
        # Expected additional successes
        # ---------------------------------

        expected_additional_successes = max(
            0,
            total_transactions
            * success_rate_improvement
        )

        # ---------------------------------
        # Simulated recovered transactions
        # ---------------------------------

        simulated_recovered_transactions = round(
            eligible_transactions
            * alternative_success_rate
        )

        simulated_recovered_transactions = min(
            simulated_recovered_transactions,
            eligible_transactions
        )

        remaining_failed = (
            eligible_transactions
            - simulated_recovered_transactions
        )

        stopped_transactions = 0

        escalated_transactions = 0

    elif policy_result["decision"] == "ESCALATE":

        eligible_transactions = 0

        simulated_recovered_transactions = 0

        expected_additional_successes = 0.0

        remaining_failed = failed_transactions

        stopped_transactions = 0

        escalated_transactions = (
            failed_transactions
        )

        success_rate_improvement = 0.0

    else:

        eligible_transactions = 0

        simulated_recovered_transactions = 0

        expected_additional_successes = 0.0

        remaining_failed = failed_transactions

        stopped_transactions = (
            failed_transactions
        )

        escalated_transactions = 0

        success_rate_improvement = 0.0

    # =====================================
    # RECOVERY RATE
    # =====================================

    if eligible_transactions > 0:

        recovery_rate = (
            simulated_recovered_transactions
            / eligible_transactions
        )

    else:

        recovery_rate = 0.0

    # =====================================
    # ESTIMATED RECOVERED VALUE
    # =====================================

    estimated_recovered_value = (
        expected_additional_successes
        * average_transaction_value
    )

    # =====================================
    # SIMULATED RECOVERED VALUE
    # =====================================

    simulated_recovered_value = (
        simulated_recovered_transactions
        * average_transaction_value
    )

    # =====================================
    # RESULT
    # =====================================

    return {
        "batch_size":
            batch_size,

        "total_transactions":
            total_transactions,

        "successful_transactions":
            int(successful_transactions),

        "failed_transactions":
            int(failed_transactions),

        "eligible_transactions":
            int(eligible_transactions),

        "recovered_transactions":
            int(simulated_recovered_transactions),

        "remaining_failed":
            int(remaining_failed),

        "stopped_transactions":
            int(stopped_transactions),

        "escalated_transactions":
            int(escalated_transactions),

        "recovery_rate":
            float(recovery_rate),

        "current_success_rate":
            float(
                incident["success_rate"]
            ),

        "alternative_success_rate":
            float(
                recovery[
                    "alternative_success_rate"
                ]
            ),

        "success_rate_improvement":
            float(
                success_rate_improvement
            ),

        "expected_additional_successes":
            float(
                expected_additional_successes
            ),

        "average_transaction_value":
            float(
                average_transaction_value
            ),

        "estimated_recovered_value":
            float(
                estimated_recovered_value
            ),

        "simulated_recovered_value":
            float(
                simulated_recovered_value
            ),

        "alternative_bank":
            recovery["alternative_bank"],

        "policy_decision":
            policy_result["decision"],

        "policy_approved":
            policy_result["approved"],

        "policy_reason":
            policy_result["reason"]
    }


# =========================================
# DISPLAY
# =========================================

def print_batch_result(result):

    if result is None:

        print(
            "\nUnable to perform batch recovery."
        )

        return

    print("\n")
    print("=" * 60)
    print("                 BATCH RECOVERY")
    print("=" * 60)

    print(
        f"\nBatch size:"
        f" {result['batch_size']:,}"
    )

    print(
        f"Total transactions:"
        f" {result['total_transactions']:,}"
    )

    print(
        f"Successful transactions:"
        f" {result['successful_transactions']:,}"
    )

    print(
        f"Failed transactions:"
        f" {result['failed_transactions']:,}"
    )

    print("\n----------------------------------------")
    print("POLICY DECISION")
    print("----------------------------------------")

    print(
        f"Decision:"
        f" {result['policy_decision']}"
    )

    print(
        f"Approved:"
        f" {result['policy_approved']}"
    )

    print(
        f"Reason:"
        f" {result['policy_reason']}"
    )

    print("\n----------------------------------------")
    print("RECOVERY OUTCOME")
    print("----------------------------------------")

    print(
        f"Eligible transactions:"
        f" {result['eligible_transactions']:,}"
    )

    print(
        f"Simulated recovered transactions:"
        f" {result['recovered_transactions']:,}"
    )

    print(
        f"Remaining failed:"
        f" {result['remaining_failed']:,}"
    )

    print(
        f"Stopped:"
        f" {result['stopped_transactions']:,}"
    )

    print(
        f"Escalated:"
        f" {result['escalated_transactions']:,}"
    )

    print(
        f"Batch recovery rate:"
        f" {result['recovery_rate'] * 100:.2f}%"
    )

    print(
        f"Success improvement:"
        f" +{result['success_rate_improvement'] * 100:.2f} pp"
    )

    print(
        f"Expected additional successes:"
        f" {result['expected_additional_successes']:.1f}"
    )

    print(
        f"Historical average transaction value:"
        f" ₹{result['average_transaction_value']:,.2f}"
    )

    print(
        f"Estimated recovered value:"
        f" ₹{result['estimated_recovered_value']:,.2f}"
    )

    print(
        f"Simulated recovered value:"
        f" ₹{result['simulated_recovered_value']:,.2f}"
    )

    print(
        f"Recommended bank:"
        f" {result['alternative_bank']}"
    )

    print("\n")
    print("=" * 60)


# =========================================
# RUN BATCH + WRITE AUDIT
# =========================================

def execute_batch_recovery():

    print(
        "\nLoading transaction data..."
    )

    df = load_data()

    print(
        "Detecting incident..."
    )

    incident = detect_incident(
        df
    )

    if incident is None:

        print(
            "\nNo incident detected."
        )

        return None

    print(
        "Generating recovery recommendation..."
    )

    recovery = recommend_recovery(
        df,
        incident
    )

    if recovery is None:

        print(
            "\nNo recovery recommendation available."
        )

        return None

    print(
        "Evaluating recovery policy..."
    )

    result = run_batch_recovery(
        df,
        incident,
        recovery,
        batch_size=1000
    )

    if result is None:

        print(
            "\nUnable to complete batch recovery."
        )

        return None

    # =====================================
    # AUDIT LOG
    # =====================================

    policy_result = evaluate_recovery_policy(
        df,
        incident,
        recovery,
        recovery_attempts=0
    )

    audit_record = log_recovery_event(
        incident=incident,
        recovery=recovery,
        policy_result=policy_result,
        batch_result=result
    )

    print_batch_result(
        result
    )

    print(
        "\n📝 AUDIT LOG"
    )

    print(
        "Recovery decision recorded successfully."
    )

    print(
        "Audit file:"
        " logs/recovery_audit.csv"
    )

    return {
        "incident":
            incident,

        "recovery":
            recovery,

        "policy":
            policy_result,

        "batch":
            result,

        "audit":
            audit_record
    }


# =========================================
# MAIN
# =========================================

if __name__ == "__main__":

    execute_batch_recovery()