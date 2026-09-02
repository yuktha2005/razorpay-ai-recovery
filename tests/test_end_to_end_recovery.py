from src.decision.incident_decision_engine import IncidentDecisionEngine
from src.recovery.recovery_orchestrator import RecoveryOrchestrator


def test_end_to_end_route_switch_recovery():
    engine = IncidentDecisionEngine()

    decision_result = engine.evaluate(
        incident_route="UPI + Bank_X + Android",
        transactions_affected=100,
        failures_observed=35,
        baseline_success_rate=0.95,
        current_success_rate=0.65,
        severity="CRITICAL",
        average_transaction_value=750.0,
        route_candidates=[
            {
                "route": "UPI + Bank_Y + Android",
                "transactions": 100,
                "successes": 97,
            },
            {
                "route": "UPI + Bank_Z + Android",
                "transactions": 80,
                "successes": 72,
            },
        ],
    )

    # Incident intelligence
    assert decision_result.incident_route == "UPI + Bank_X + Android"
    assert decision_result.degradation_pp == 30.0
    assert decision_result.financial_exposure == 75000.0
    assert decision_result.revenue_at_risk > 0

    # Decision should choose an alternative route
    assert decision_result.decision is not None
    assert decision_result.decision.recommended_action.startswith(
        "ROUTE_SWITCH:"
    )

    # Safety should allow the selected action
    assert decision_result.safety_decision is not None
    assert decision_result.safety_decision.allowed is True
    assert decision_result.safety_decision.action.startswith(
        "ROUTE_SWITCH:"
    )

    # Execute bounded recovery
    orchestrator = RecoveryOrchestrator()

    transaction_amounts = [750.0] * 20

    result = orchestrator.execute(
        decision=decision_result.decision,
        safety_decision=decision_result.safety_decision,
        transaction_amounts=transaction_amounts,
        simulated_success_rate=0.95,
    )

    # Decision → safety → execution
    assert result.decision_action == (
        decision_result.decision.recommended_action
    )

    assert result.safety_action == (
        decision_result.safety_decision.action
    )

    assert result.safety_allowed is True

    # Recovery actually executed
    assert result.execution_result.status == "COMPLETED"
    assert result.execution_result.attempted_transactions > 0

    # Outcome was measured
    assert result.recovery_outcome is not None
    assert result.recovery_outcome.attempted_transactions > 0
    assert result.recovery_outcome.successful_recoveries >= 0

    # Learning was updated for the selected route
    assert result.learning_stats is not None
    assert result.learning_stats.attempts > 0
    assert result.learning_stats.recoveries >= 0
    assert result.learning_stats.net_recovered_value >= 0

    # Final system state
    assert result.final_status in {
        "RECOVERED",
        "NO_RECOVERY",
        "UNPROFITABLE",
    }