from src.decision.incident_decision_engine import (
    IncidentDecisionEngine,
)


def test_incident_decision_engine_produces_safe_decision():

    engine = IncidentDecisionEngine()

    result = engine.evaluate(
        incident_route="UPI + Bank_X + Android",
        transactions_affected=508,
        failures_observed=155,
        baseline_success_rate=0.946123,
        current_success_rate=0.694882,
        severity="CRITICAL",
        route_candidates=[
            {
                "route": "UPI + Bank_A + Android",
                "transactions": 3,
                "successes": 3,
            },
            {
                "route": "UPI + Bank_B + Android",
                "transactions": 6,
                "successes": 6,
            },
            {
                "route": "UPI + Bank_C + Android",
                "transactions": 8,
                "successes": 7,
            },
            {
                "route": "UPI + Bank_Y + Android",
                "transactions": 9,
                "successes": 9,
            },
        ],
        average_transaction_value=2376.307008,
    )

    assert result.incident_route == (
        "UPI + Bank_X + Android"
    )

    assert result.transactions_affected == 508

    assert result.failures_observed == 155

    assert result.severity == "CRITICAL"

    assert result.degradation_pp > 25

    assert result.financial_exposure > 0

    assert result.expected_loss > 0

    assert len(result.ranked_routes) == 4

    assert result.decision is not None

    assert result.safety_decision is not None


def test_critical_route_switch_is_safety_gated():

    engine = IncidentDecisionEngine()

    result = engine.evaluate(
        incident_route="UPI + Bank_X + Android",
        transactions_affected=508,
        failures_observed=155,
        baseline_success_rate=0.946123,
        current_success_rate=0.694882,
        severity="CRITICAL",
        route_candidates=[
            {
                "route": "UPI + Bank_C + Android",
                "transactions": 8,
                "successes": 7,
            },
        ],
        average_transaction_value=3000.0,
    )

    assert result.decision.recommended_action != ""

    assert result.safety_decision is not None