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

# Additional production-safety thresholds
MIN_RECOVERY_SUCCESS_RATE = 90.0

MAX_ALLOWED_RECOVERY_FAILURE_RATE = 10.0

ROLLBACK_DEGRADATION_PP = 5.0

MAX_ROLLOUT_PERCENTAGE = 100

STALE_EVIDENCE_HOURS = 2


# =========================================
# HELPER
# =========================================

def _result(
    decision,
    approved,
    reason,
    checks=None,
    **extra
):
    """
    Create a consistent policy result.
    """

    result = {
        "decision": decision,
        "approved": approved,
        "reason": reason,
        "checks": checks or []
    }

    result.update(extra)

    return result


# =========================================
# MAIN RECOVERY POLICY
# =========================================

def evaluate_recovery_policy(
    df,
    incident,
    recovery,
    recovery_attempts=0
):
    """
    Deterministic safety layer between
    AI diagnosis / recovery recommendation
    and recovery execution.

    Possible decisions:

        RECOVER
        STOP
        ESCALATE

    AI does not directly authorize recovery.
    """

    # =====================================
    # BASIC VALIDATION
    # =====================================

    if incident is None:

        return _result(
            "STOP",
            False,
            "No active payment incident detected."
        )


    if recovery is None:

        return _result(
            "STOP",
            False,
            "No recovery recommendation available."
        )


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

        return _result(
            "STOP",
            False,
            (
                "Incident volume is too low "
                "for automated recovery."
            ),
            checks
        )


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

        return _result(
            "STOP",
            False,
            (
                "Payment degradation is below "
                "the automated recovery threshold."
            ),
            checks
        )


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


        return _result(
            "ESCALATE",
            False,
            (
                "No suitable alternative "
                "payment route was identified. "
                "Human review is required."
            ),
            checks,
            human_review_required=True
        )


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

        return _result(
            "STOP",
            False,
            (
                "Alternative route does not provide "
                "sufficient improvement."
            ),
            checks
        )


    # =====================================
    # ALTERNATIVE SUCCESS RATE GUARDRAIL
    # =====================================

    alternative_quality_pass = (
        alternative_success_rate * 100
        >= MIN_RECOVERY_SUCCESS_RATE
    )


    checks.append({
        "check":
            "Alternative route quality",

        "passed":
            alternative_quality_pass,

        "value":
            alternative_success_rate * 100,

        "threshold":
            MIN_RECOVERY_SUCCESS_RATE
    })


    if not alternative_quality_pass:

        return _result(
            "ESCALATE",
            False,
            (
                "Alternative route success rate is "
                "below the minimum automated-recovery "
                "quality threshold."
            ),
            checks,
            human_review_required=True
        )


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

        return _result(
            "ESCALATE",
            False,
            (
                "The alternative route does not "
                "have sufficient historical evidence. "
                "Human review is required."
            ),
            checks,
            human_review_required=True
        )


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

        return _result(
            "ESCALATE",
            False,
            (
                "Agent confidence is below "
                "the automated recovery threshold. "
                "Human review is required."
            ),
            checks,
            human_review_required=True
        )


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

        return _result(
            "STOP",
            False,
            (
                "Maximum recovery attempts "
                "have already been reached. "
                "Automated recovery is blocked."
            ),
            checks
        )


    # =====================================
    # ALL AUTOMATED RECOVERY CHECKS PASSED
    # =====================================

    return _result(
        "RECOVER",
        True,
        (
            f"Recovery approved: {alternative_bank} "
            f"provides a {improvement_pp:.2f} pp "
            f"success-rate improvement with "
            f"sufficient historical evidence."
        ),
        checks,
        alternative_bank=alternative_bank,
        alternative_success_rate=alternative_success_rate,
        improvement_pp=improvement_pp,
        confidence=confidence,
        comparable_transactions=comparable_transactions,
        human_review_required=False,
        max_rollout_percentage=MAX_ROLLOUT_PERCENTAGE
    )


# =========================================
# ROLLBACK / CIRCUIT BREAKER
# =========================================

def evaluate_recovery_guardrail(
    baseline_success_rate,
    recovery_success_rate,
    rollout_percentage=100,
    recovery_active=True
):
    """
    Evaluate the health of an active recovery.

    This function is intentionally deterministic.

    Possible outcomes:

        CONTINUE
        STOP
        ROLLBACK
    """

    baseline = float(
        baseline_success_rate
    )

    current = float(
        recovery_success_rate
    )

    rollout = float(
        rollout_percentage
    )


    # -------------------------------------
    # Recovery already inactive
    # -------------------------------------

    if not recovery_active:

        return {
            "decision":
                "STOP",

            "reason":
                "Recovery is no longer active.",

            "rollback_required":
                False,

            "healthy":
                False
        }


    # -------------------------------------
    # Invalid rollout
    # -------------------------------------

    if (
        rollout < 0
        or rollout > MAX_ROLLOUT_PERCENTAGE
    ):

        return {
            "decision":
                "STOP",

            "reason":
                "Invalid rollout percentage.",

            "rollback_required":
                True,

            "healthy":
                False
        }


    # -------------------------------------
    # Recovery route deterioration
    # -------------------------------------

    deterioration_pp = (
        baseline
        - current
    )


    if deterioration_pp >= ROLLBACK_DEGRADATION_PP:

        return {
            "decision":
                "ROLLBACK",

            "reason":
                (
                    f"Recovery route degraded by "
                    f"{deterioration_pp:.2f} pp "
                    f"against the baseline guardrail."
                ),

            "rollback_required":
                True,

            "healthy":
                False,

            "baseline_success_rate":
                baseline,

            "recovery_success_rate":
                current,

            "deterioration_pp":
                deterioration_pp
        }


    # -------------------------------------
    # Recovery route below minimum quality
    # -------------------------------------

    if current < MIN_RECOVERY_SUCCESS_RATE:

        return {
            "decision":
                "ROLLBACK",

            "reason":
                (
                    f"Recovery route success rate "
                    f"{current:.2f}% is below the "
                    f"{MIN_RECOVERY_SUCCESS_RATE:.2f}% "
                    f"minimum guardrail."
                ),

            "rollback_required":
                True,

            "healthy":
                False,

            "baseline_success_rate":
                baseline,

            "recovery_success_rate":
                current
        }


    # -------------------------------------
    # Healthy recovery
    # -------------------------------------

    return {
        "decision":
            "CONTINUE",

        "reason":
            (
                "Recovery route remains within "
                "configured performance guardrails."
            ),

        "rollback_required":
            False,

        "healthy":
            True,

        "baseline_success_rate":
            baseline,

        "recovery_success_rate":
            current,

        "deterioration_pp":
            deterioration_pp
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
        "\nReason:"
    )

    print(
        policy_result["reason"]
    )

    if policy_result.get(
        "human_review_required",
        False
    ):

        print(
            "\n⚠️ Human review required."
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
# SAFETY TESTS
# =========================================

def run_safety_tests():

    print("\n")
    print("=" * 55)
    print("             SAFETY POLICY TESTS")
    print("=" * 55)


    # =====================================
    # TEST DATA
    # =====================================

    base_incident = {
        "transactions": 508,
        "degradation_percentage_points": 24.93,
        "success_rate": 0.6949,
        "confidence": 90
    }


    base_recovery = {
        "alternative_bank": "Bank_A",
        "alternative_success_rate": 0.9581,
        "historical_transactions": 6105,
        "confidence": 90
    }


    # =====================================
    # SCENARIO 1 — RECOVER
    # =====================================

    print(
        "\n\nSCENARIO 1 — SAFE RECOVERY"
    )


    result = evaluate_recovery_policy(
        None,
        base_incident,
        base_recovery
    )


    print_policy_result(
        result
    )


    # =====================================
    # SCENARIO 2 — ESCALATE
    # =====================================

    print(
        "\n\nSCENARIO 2 — LOW AI CONFIDENCE"
    )


    escalation_recovery = {
        **base_recovery,
        "confidence": 65
    }


    result = evaluate_recovery_policy(
        None,
        base_incident,
        escalation_recovery
    )


    print_policy_result(
        result
    )


    # =====================================
    # SCENARIO 3 — STOP
    # =====================================

    print(
        "\n\nSCENARIO 3 — RECOVERY LIMIT"
    )


    result = evaluate_recovery_policy(
        None,
        base_incident,
        base_recovery,
        recovery_attempts=1
    )


    print_policy_result(
        result
    )


    # =====================================
    # SCENARIO 4 — CONTINUE
    # =====================================

    print(
        "\n\nSCENARIO 4 — HEALTHY RECOVERY"
    )


    result = evaluate_recovery_guardrail(
        baseline_success_rate=94.42,
        recovery_success_rate=95.20,
        rollout_percentage=25
    )


    print(
        f"Decision: {result['decision']}"
    )

    print(
        f"Reason: {result['reason']}"
    )


    # =====================================
    # SCENARIO 5 — ROLLBACK
    # =====================================

    print(
        "\n\nSCENARIO 5 — RECOVERY DEGRADATION"
    )


    result = evaluate_recovery_guardrail(
        baseline_success_rate=94.42,
        recovery_success_rate=87.00,
        rollout_percentage=25
    )


    print(
        f"Decision: {result['decision']}"
    )

    print(
        f"Reason: {result['reason']}"
    )

    print(
        f"Rollback required: "
        f"{result['rollback_required']}"
    )


    print("\n")
    print("=" * 55)
    print("             SAFETY TESTS COMPLETE")
    print("=" * 55)


# =========================================
# STANDALONE POLICY TEST
# =========================================

def run_policy_test():

    from agent import (
        load_data,
        detect_incident,
        recommend_recovery
    )


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

        return


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

    run_safety_tests()