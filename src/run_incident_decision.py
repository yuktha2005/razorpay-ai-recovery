import pandas as pd

from src.decision.incident_decision_engine import IncidentDecisionEngine
from src.intelligence.incident_revenue import IncidentRevenueCalculator
from src.intelligence.route_monitor import RouteMonitor


DATA_PATH = "data/transactions.csv"

PAYMENT_METHOD = "UPI"
BANK = "Bank_X"
DEVICE_TYPE = "Android"

INCIDENT_START = "2026-07-23 19:00:00"
INCIDENT_END = "2026-07-23 20:00:00"


def main():
    # ---------------------------------------------------------
    # Load transaction data
    # ---------------------------------------------------------

    df = pd.read_csv(DATA_PATH)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        format="mixed",
    )

    incident_route = (
        f"{PAYMENT_METHOD} + "
        f"{BANK} + "
        f"{DEVICE_TYPE}"
    )

    # =========================================================
    # 1. REAL-TIME DETECTION
    #
    # Uses the rolling monitoring window to determine whether
    # the route is currently unhealthy.
    # =========================================================

    monitor = RouteMonitor()

    monitoring_result = monitor.monitor(
        df=df,
        payment_method=PAYMENT_METHOD,
        bank=BANK,
        device_type=DEVICE_TYPE,
        monitoring_start=INCIDENT_START,
        monitoring_end=INCIDENT_END,
    )

    assessment = monitoring_result.assessment

    # =========================================================
    # 2. FULL INCIDENT FINANCIAL IMPACT
    #
    # Uses the complete incident window to quantify revenue
    # exposure against the historical baseline.
    # =========================================================

    revenue_calculator = IncidentRevenueCalculator()

    revenue_impact = revenue_calculator.calculate(
        df=df,
        payment_method=PAYMENT_METHOD,
        bank=BANK,
        device_type=DEVICE_TYPE,
        incident_start=INCIDENT_START,
        incident_end=INCIDENT_END,
    )

    # =========================================================
    # 3. ALTERNATIVE ROUTES
    #
    # Find other banks handling the same payment method and
    # device type during the incident window.
    # =========================================================

    incident_start = pd.Timestamp(INCIDENT_START)
    incident_end = pd.Timestamp(INCIDENT_END)

    period_data = df[
        (df["timestamp"] >= incident_start)
        & (df["timestamp"] < incident_end)
        & (df["payment_method"] == PAYMENT_METHOD)
        & (df["device_type"] == DEVICE_TYPE)
    ].copy()

    alternative_data = period_data[
        period_data["bank"] != BANK
    ]

    route_candidates = []

    for alternative_bank, group in alternative_data.groupby("bank"):
        transactions = len(group)

        successes = int(
            (group["status"] == "SUCCESS").sum()
        )

        route_candidates.append(
            {
                "route": (
                    f"{PAYMENT_METHOD} + "
                    f"{alternative_bank} + "
                    f"{DEVICE_TYPE}"
                ),
                "transactions": transactions,
                "successes": successes,
            }
        )

    # =========================================================
    # 4. AVERAGE TRANSACTION VALUE
    # =========================================================

    affected_data = period_data[
        period_data["bank"] == BANK
    ]

    average_transaction_value = float(
        affected_data["amount"].mean()
    )

    # =========================================================
    # 5. RECOVERY DECISION
    # =========================================================

    engine = IncidentDecisionEngine()

    result = engine.evaluate(
        incident_route=incident_route,
        transactions_affected=assessment.transactions_observed,
        failures_observed=assessment.failures_observed,
        baseline_success_rate=assessment.baseline_success_rate,
        current_success_rate=assessment.current_success_rate,
        severity=assessment.severity,
        average_transaction_value=average_transaction_value,
        route_candidates=route_candidates,
        revenue_impact=revenue_impact,
    )

    # =========================================================
    # OUTPUT
    # =========================================================

    print()
    print("=" * 64)
    print("PAYMENT RELIABILITY INTELLIGENCE")
    print("=" * 64)

    # ---------------------------------------------------------
    # REAL-TIME DETECTION
    # ---------------------------------------------------------

    print()
    print("1. REAL-TIME DETECTION")
    print("-" * 64)

    print(f"Route: {incident_route}")
    print(f"Severity: {assessment.severity}")

    print(
        f"Baseline success rate: "
        f"{assessment.baseline_success_rate:.2%}"
    )

    print(
        f"Current success rate: "
        f"{assessment.current_success_rate:.2%}"
    )

    print(
        f"Current degradation: "
        f"{assessment.degradation_pp:.2f} percentage points"
    )

    print(
        f"Rolling-window transactions: "
        f"{assessment.transactions_observed}"
    )

    print(
        f"Rolling-window failures: "
        f"{assessment.failures_observed}"
    )

    print(
        f"Incident detected: "
        f"{assessment.incident_detected}"
    )

    print()
    print(
        "Purpose: determine whether the route is currently "
        "unhealthy."
    )

    # ---------------------------------------------------------
    # FULL INCIDENT IMPACT
    # ---------------------------------------------------------

    print()
    print("2. FULL INCIDENT FINANCIAL IMPACT")
    print("-" * 64)

    print(
        f"Incident window: "
        f"{INCIDENT_START} → {INCIDENT_END}"
    )

    print(
        f"Transactions in incident: "
        f"{revenue_impact.incident_transactions}"
    )

    print(
        f"Failures in incident: "
        f"{revenue_impact.incident_failures}"
    )

    print(
        f"Baseline failure rate: "
        f"{revenue_impact.baseline_failure_rate:.2%}"
    )

    print(
        f"Expected failures: "
        f"{revenue_impact.expected_failures:.2f}"
    )

    print(
        f"Excess failures: "
        f"{revenue_impact.excess_failures:.2f}"
    )

    print(
        f"Actual failed amount: "
        f"₹{revenue_impact.actual_failed_amount:,.2f}"
    )

    print(
        f"Expected failed amount: "
        f"₹{revenue_impact.expected_failed_amount:,.2f}"
    )

    print(
        f"REVENUE AT RISK: "
        f"₹{revenue_impact.revenue_at_risk:,.2f}"
    )

    print()
    print(
        "Purpose: quantify the business impact of the incident."
    )

    # ---------------------------------------------------------
    # ALTERNATIVE ROUTES
    # ---------------------------------------------------------

    print()
    print("3. ALTERNATIVE ROUTE INTELLIGENCE")
    print("-" * 64)

    if not result.ranked_routes:
        print("No alternative routes available.")

    else:
        for index, route in enumerate(
            result.ranked_routes,
            start=1,
        ):
            print(
                f"{index}. {route.route}"
            )

            print(
                f"   Transactions: "
                f"{route.transactions}"
            )

            print(
                f"   Observed success: "
                f"{route.observed_success_rate:.2%}"
            )

            print(
                f"   Evidence-adjusted success: "
                f"{route.adjusted_success_rate:.2%}"
            )

            print(
                f"   Evidence confidence: "
                f"{route.evidence_confidence:.2%}"
            )

            print(
                f"   Route score: "
                f"{route.score:.4f}"
            )

    # ---------------------------------------------------------
    # RECOVERY DECISION
    # ---------------------------------------------------------

    print()
    print("4. RECOVERY DECISION")
    print("-" * 64)

    print(
        f"Recommended action: "
        f"{result.decision.recommended_action}"
    )

    print(
        f"Decision confidence: "
        f"{result.decision.confidence:.2%}"
    )

    print(
        f"Expected loss before: "
        f"₹{result.decision.expected_loss_before:,.2f}"
    )

    print(
        f"Expected loss after: "
        f"₹{result.decision.expected_loss_after:,.2f}"
    )

    print(
        f"Estimated intervention value: "
        f"₹{result.decision.estimated_value:,.2f}"
    )

    print(
        f"Explanation: "
        f"{result.decision.explanation}"
    )

    # ---------------------------------------------------------
    # SAFETY CONTROLLER
    # ---------------------------------------------------------

    print()
    print("5. SAFETY CONTROLLER")
    print("-" * 64)

    print(
        f"Final action: "
        f"{result.safety_decision.action}"
    )

    print(
        f"Automation allowed: "
        f"{result.safety_decision.allowed}"
    )

    print(
        f"Human review required: "
        f"{result.safety_decision.requires_human_review}"
    )

    print(
        f"Safety reason: "
        f"{result.safety_decision.reason}"
    )

    # ---------------------------------------------------------
    # FINAL SYSTEM DECISION
    # ---------------------------------------------------------

    print()
    print("=" * 64)
    print("FINAL SYSTEM DECISION")
    print("=" * 64)

    print(
        f"Detected: "
        f"{assessment.incident_detected}"
    )

    print(
        f"Severity: "
        f"{assessment.severity}"
    )

    print(
        f"Revenue at risk: "
        f"₹{revenue_impact.revenue_at_risk:,.2f}"
    )

    print(
        f"Recommended: "
        f"{result.decision.recommended_action}"
    )

    route_switch_recommended = (
        result.decision.recommended_action.startswith(
            "ROUTE_SWITCH:"
        )
    )

    route_switch_executed = (
        route_switch_recommended
        and result.safety_decision.allowed
        and result.safety_decision.action.startswith(
            "ROUTE_SWITCH:"
        )
    )

    print(
        f"Route switch executed: "
        f"{route_switch_executed}"
    )

    print(
        f"Final action: "
        f"{result.safety_decision.action}"
    )

    print("=" * 64)


if __name__ == "__main__":
    main()