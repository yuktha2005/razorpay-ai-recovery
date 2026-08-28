import pandas as pd


# =========================================
# POLICY CONFIGURATION
# =========================================

MIN_INCIDENT_TRANSACTIONS = 20

MIN_ALTERNATIVE_TRANSACTIONS = 100

MIN_DEGRADATION_PP = 10.0

MIN_ALTERNATIVE_IMPROVEMENT_PP = 5.0

MIN_CONFIDENCE = 80.0

MAX_RECOVERY_ATTEMPTS = 1


# =========================================
# POLICY ENGINE
# =========================================

def evaluate_recovery_policy(
    df,
    incident,
    recovery,
    recovery_attempts=0
):
    """
    Evaluate whether a proposed recovery action
    should be:

        RECOVER
        STOP
        ESCALATE

    This is a deterministic safety layer between
    the recovery recommendation and execution.
    """

    # =====================================
    # BASIC VALIDATION
    # =====================================

    if incident is None:

        return {
            "decision": "STOP",
            "approved": False,
            "reason": "No active payment incident detected.",
            "checks": []
        }


    if recovery is None:

        return {
            "decision": "STOP",
            "approved": False,
            "reason": "No recovery recommendation available.",
            "checks": []
        }


    checks = []


    # =====================================
    # INCIDENT TRANSACTION VOLUME
    # =====================================

    incident_transactions = int(
        incident.get(
            "transactions",
            0
        )
    )


    volume_pass = (
        incident_transactions
        >= MIN_INCIDENT_TRANSACTIONS
    )


    checks.append({
        "check":
            "Minimum incident volume",

        "passed":
            volume_pass,

        "value":
            incident_transactions,

        "threshold":
            MIN_INCIDENT_TRANSACTIONS
    })


    if not volume_pass:

        return {
            "decision": "STOP",
            "approved": False,
            "reason": (
                "Incident volume is too low "
                "for automated recovery."
            ),
            "checks": checks
        }


    # =====================================
    # INCIDENT DEGRADATION
    # =====================================

    degradation = float(
        incident.get(
            "degradation_percentage_points",
            0
        )
    )


    degradation_pass = (
        degradation
        >= MIN_DEGRADATION_PP
    )


    checks.append({
        "check":
            "Minimum degradation",

        "passed":
            degradation_pass,

        "value":
            degradation,

        "threshold":
            MIN_DEGRADATION_PP
    })


    if not degradation_pass:

        return {
            "decision": "STOP",
            "approved": False,
            "reason": (
                "Payment degradation is below "
                "the automated recovery threshold."
            ),
            "checks": checks
        }


    # =====================================
    # ALTERNATIVE BANK
    # =====================================

    alternative_bank = recovery.get(
        "alternative_bank"
    )


    if not alternative_bank:

        checks.append({
            "check":
                "Alternative route exists",

            "passed":
                False,

            "value":
                None,

            "threshold":
                "Required"
        })


        return {
            "decision": "ESCALATE",
            "approved": False,
            "reason": (
                "No suitable alternative "
                "payment route was identified."
            ),
            "checks": checks
        }


    checks.append({
        "check":
            "Alternative route exists",

        "passed":
            True,

        "value":
            alternative_bank,

        "threshold":
            "Required"
    })


    # =====================================
    # ALTERNATIVE HISTORICAL PERFORMANCE
    # =====================================

    alternative_success_rate = float(
        recovery.get(
            "alternative_success_rate",
            0
        )
    )


    current_success_rate = float(
        incident.get(
            "success_rate",
            0
        )
    )


    improvement_pp = (
        alternative_success_rate
        - current_success_rate
    ) * 100


    improvement_pass = (
        improvement_pp
        >= MIN_ALTERNATIVE_IMPROVEMENT_PP
    )


    checks.append({
        "check":
            "Alternative route improvement",

        "passed":
            improvement_pass,

        "value":
            improvement_pp,

        "threshold":
            MIN_ALTERNATIVE_IMPROVEMENT_PP
    })


    if not improvement_pass:

        return {
            "decision": "STOP",
            "approved": False,
            "reason": (
                "Alternative route does not provide "
                "sufficient improvement."
            ),
            "checks": checks
        }


    # =====================================
    # HISTORICAL ALTERNATIVE VOLUME
    # =====================================

    comparable_transactions = recovery.get(
        "historical_transactions",
        recovery.get(
            "comparable_transactions",
            None
        )
    )


    if comparable_transactions is None:

        # Try calculating it directly from data.

        try:

            payment_method = incident[
                "payment_method"
            ]

            device_type = incident[
                "device_type"
            ]

            incident_start = pd.Timestamp(
                incident["time_window"]
            )

            incident_end = (
                incident_start
                + pd.Timedelta(hours=1)
            )


            historical = df[
                ~(
                    (df["timestamp"] >= incident_start)
                    &
                    (df["timestamp"] < incident_end)
                )
            ]


            comparable_transactions = len(
                historical[
                    (historical["payment_method"]
                     == payment_method)
                    &
                    (historical["device_type"]
                     == device_type)
                    &
                    (historical["bank"]
                     == alternative_bank)
                ]
            )

        except Exception:

            comparable_transactions = 0


    comparable_transactions = int(
        comparable_transactions
    )


    history_pass = (
        comparable_transactions
        >= MIN_ALTERNATIVE_TRANSACTIONS
    )


    checks.append({
        "check":
            "Sufficient alternative history",

        "passed":
            history_pass,

        "value":
            comparable_transactions,

        "threshold":
            MIN_ALTERNATIVE_TRANSACTIONS
    })


    if not history_pass:

        return {
            "decision": "ESCALATE",
            "approved": False,
            "reason": (
                "The alternative route does not "
                "have sufficient historical evidence."
            ),
            "checks": checks
        }


    # =====================================
    # CONFIDENCE CHECK
    # =====================================

    confidence = float(
        recovery.get(
            "confidence",
            incident.get(
                "confidence",
                99
            )
        )
    )


    confidence_pass = (
        confidence
        >= MIN_CONFIDENCE
    )


    checks.append({
        "check":
            "Agent confidence",

        "passed":
            confidence_pass,

        "value":
            confidence,

        "threshold":
            MIN_CONFIDENCE
    })


    if not confidence_pass:

        return {
            "decision": "ESCALATE",
            "approved": False,
            "reason": (
                "Agent confidence is below "
                "the automated recovery threshold."
            ),
            "checks": checks
        }


    # =====================================
    # RECOVERY ATTEMPT LIMIT
    # =====================================

    attempt_pass = (
        recovery_attempts
        < MAX_RECOVERY_ATTEMPTS
    )


    checks.append({
        "check":
            "Recovery attempt limit",

        "passed":
            attempt_pass,

        "value":
            recovery_attempts,

        "threshold":
            MAX_RECOVERY_ATTEMPTS
    })


    if not attempt_pass:

        return {
            "decision": "STOP",
            "approved": False,
            "reason": (
                "Maximum recovery attempts "
                "have already been reached."
            ),
            "checks": checks
        }


    # =====================================
    # ALL CHECKS PASSED
    # =====================================

    return {
        "decision": "RECOVER",

        "approved": True,

        "reason": (
            f"Recovery approved: {alternative_bank} "
            f"provides a {improvement_pp:.2f} pp "
            f"success-rate improvement with "
            f"sufficient historical evidence."
        ),

        "alternative_bank":
            alternative_bank,

        "alternative_success_rate":
            alternative_success_rate,

        "improvement_pp":
            improvement_pp,

        "confidence":
            confidence,

        "comparable_transactions":
            comparable_transactions,

        "checks":
            checks
    }


# =========================================
# DISPLAY POLICY RESULT
# =========================================

def print_policy_result(policy_result):

    print("\n")
    print("=" * 55)
    print("                 POLICY ENGINE")
    print("=" * 55)


    print(
        f"\nDecision: "
        f"{policy_result['decision']}"
    )


    print(
        f"Approved: "
        f"{policy_result['approved']}"
    )


    print(
        f"\nReason:"
    )


    print(
        policy_result["reason"]
    )


    print(
        "\nPolicy checks:"
    )


    for check in policy_result["checks"]:

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


    print("\n")
    print("=" * 55)


# =========================================
# STANDALONE TEST
# =========================================

def run_policy_test():

    from agent import (
        load_data,
        detect_incident,
        recommend_recovery
    )


    print("\nLoading transaction data...")

    df = load_data()


    print("Detecting incident...")

    incident = detect_incident(
        df
    )


    if incident is None:

        print(
            "\nNo incident detected."
        )

        return


    print("Generating recovery recommendation...")

    recovery = recommend_recovery(
        df,
        incident
    )


    if recovery is None:

        print(
            "\nNo recovery recommendation available."
        )

        return


    policy_result = (
        evaluate_recovery_policy(
            df,
            incident,
            recovery
        )
    )


    print_policy_result(
        policy_result
    )


# =========================================
# MAIN
# =========================================

if __name__ == "__main__":

    run_policy_test()