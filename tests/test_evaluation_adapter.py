import copy
import math
import pytest

from src.decision.incident_decision_engine import IncidentDecisionEngine
from src.evaluation.evaluation_adapter import (
    EvaluationAdapter,
    build_system_evaluation_scorecard,
)
from src.evaluation.scorecard import SystemEvaluationScorecard
from src.intelligence.incident_intelligence import IncidentAssessment
from src.models.domain import Decision, SafetyDecision
from src.recovery.recovery_orchestrator import RecoveryOrchestrator
from src.tracking.financial_summary import calculate_financial_summary
from src.tracking.recovery_learning import RouteLearningStats
from src.tracking.recovery_outcome import RecoveryOutcome


def test_full_successful_end_to_end_integration(tmp_path, monkeypatch):
    """
    1. Full successful end-to-end evaluation & integration test.
    Exercises the actual pipeline:
    Incident -> IncidentDecisionEngine -> RecoveryOrchestrator -> build_system_evaluation_scorecard.
    Verifies that the scorecard faithfully reflects the real pipeline outputs.
    """
    audit_file = tmp_path / "recovery_audit.csv"
    monkeypatch.setattr("src.audit_logger.AUDIT_FILE", audit_file)
    monkeypatch.setattr("src.audit_logger.LOG_DIR", tmp_path)

    # 1. Incident -> Decision
    engine = IncidentDecisionEngine()
    decision_result = engine.evaluate(
        incident_route="UPI + Bank_A + Android",
        transactions_affected=100,
        failures_observed=30,
        baseline_success_rate=0.95,
        current_success_rate=0.70,
        severity="CRITICAL",
        average_transaction_value=800.0,
        route_candidates=[
            {
                "route": "UPI + Bank_B + Android",
                "transactions": 100,
                "successes": 96,
            }
        ],
    )

    # 2. Decision -> Recovery Orchestration
    orchestrator = RecoveryOrchestrator()
    transaction_amounts = [800.0] * 10
    orchestration_result = orchestrator.execute(
        decision=decision_result.decision,
        safety_decision=decision_result.safety_decision,
        transaction_amounts=transaction_amounts,
        simulated_success_rate=0.96,
    )

    # 3. Adapter -> Scorecard
    scorecard = build_system_evaluation_scorecard(
        incident=decision_result,
        orchestration_result=orchestration_result,
    )

    # Assert incident metrics match real decision result
    assert scorecard.degradation_percentage_points == 25.0
    assert scorecard.severity == "CRITICAL"
    assert scorecard.transactions_observed == 100
    assert scorecard.incident_detected is True

    # Assert decision metrics match real decision
    assert scorecard.selected_action == "ROUTE_SWITCH:UPI + Bank_B + Android"
    assert scorecard.expected_loss_before == 24000.0
    assert scorecard.expected_loss_reduction > 0.0
    assert scorecard.expected_loss_reduction_percentage > 0.0

    # Assert safety metrics match
    assert scorecard.safety_allowed is True
    assert scorecard.human_review_required is False

    # Assert recovery metrics match actual execution
    assert (
        scorecard.attempted_transactions
        == orchestration_result.execution_result.attempted_transactions
    )
    assert scorecard.attempted_transactions > 0
    assert (
        scorecard.successful_recoveries
        == orchestration_result.execution_result.successful_recoveries
    )
    assert (
        scorecard.recovered_amount
        == orchestration_result.recovery_outcome.recovered_amount
    )
    assert (
        scorecard.execution_cost
        == orchestration_result.recovery_outcome.execution_cost
    )
    assert (
        scorecard.net_recovered_value
        == orchestration_result.recovery_outcome.net_recovered_value
    )
    assert scorecard.final_status == orchestration_result.final_status


def test_safety_blocked_evaluation():
    """
    2. Safety-blocked evaluation.
    Verifies that when safety blocks an action, simulated fields remain zero,
    ROI is None, and final_status reflects the block without fabricating recoveries.
    """
    incident = IncidentAssessment(
        route="UPI + Bank_X + Android",
        baseline_success_rate=0.95,
        current_success_rate=0.55,
        degradation_pp=40.0,
        transactions_observed=150,
        failures_observed=67,
        severity="CRITICAL",
        incident_detected=True,
        explanation="Severe degradation",
    )

    decision = Decision(
        payment_id="PAY_BLOCK",
        recommended_action="ROUTE_SWITCH:Bank_Risky",
        confidence=0.35,  # below critical threshold
        expected_loss_before=50000.0,
        expected_loss_after=10000.0,
        estimated_value=40000.0,
    )

    safety = SafetyDecision(
        payment_id="PAY_BLOCK",
        action="STOP",
        allowed=False,
        requires_human_review=False,
        reason="Confidence 0.35 is below critical threshold 0.40",
    )

    scorecard = build_system_evaluation_scorecard(
        incident=incident,
        decision=decision,
        safety_decision=safety,
        orchestration_result=None,
        revenue_impact=45000.0,
    )

    assert scorecard.safety_allowed is False
    assert scorecard.human_review_required is False
    assert "critical threshold" in scorecard.safety_reason
    assert scorecard.attempted_transactions == 0
    assert scorecard.successful_recoveries == 0
    assert scorecard.attempted_amount == 0.0
    assert scorecard.recovered_amount == 0.0
    assert scorecard.execution_cost == 0.0
    assert scorecard.net_recovered_value == 0.0
    assert scorecard.recovery_roi is None
    assert scorecard.final_status == "NO_EXECUTION"


def test_monitor_no_execution_evaluation():
    """
    3. MONITOR / no-execution evaluation.
    Verifies that when the decision is MONITOR, recovery is not executed,
    all simulated recovery fields are safely zeroed, and ROI is None.
    """
    decision = Decision(
        payment_id="PAY_MONITOR",
        recommended_action="MONITOR",
        confidence=0.90,
        expected_loss_before=0.0,
        expected_loss_after=0.0,
        estimated_value=0.0,
    )

    scorecard = build_system_evaluation_scorecard(
        incident={"degradation_percentage_points": 2.0, "severity": "NORMAL", "transactions": 50},
        decision=decision,
        orchestration_result=None,
    )

    assert scorecard.selected_action == "MONITOR"
    assert scorecard.attempted_transactions == 0
    assert scorecard.recovered_amount == 0.0
    assert scorecard.recovery_roi is None
    assert scorecard.final_status == "NO_EXECUTION"


def test_zero_eligible_evaluation():
    """
    4. Zero-eligible evaluation.
    Verifies that when eligible amount is zero, eligible_amount is 0.0,
    recovery is not attempted, and ROI is safely None.
    """
    batch_result = {
        "eligible_transactions": 0,
        "eligible_amount": 0.0,
        "attempted_transactions": 0,
        "successful_recoveries": 0,
        "failed_recoveries": 0,
        "attempted_amount": 0.0,
        "recovered_amount": 0.0,
        "execution_cost": 0.0,
        "net_recovered_value": 0.0,
        "recovery_rate": 0.0,
        "final_status": "NO_EXECUTION",
    }

    scorecard = build_system_evaluation_scorecard(
        incident={"degradation_pp": 0.0, "severity": "HEALTHY", "transactions": 20},
        orchestration_result=batch_result,
        eligible_amount=0.0,
    )

    assert scorecard.eligible_amount == 0.0
    assert scorecard.attempted_amount == 0.0
    assert scorecard.recovered_amount == 0.0
    assert scorecard.execution_cost == 0.0
    assert scorecard.recovery_roi is None
    assert scorecard.final_status == "NO_EXECUTION"


def test_partial_recovery_canary_stop_or_escalate():
    """
    5. Partial recovery / canary STOP or ESCALATE.
    Verifies that canary status and partial recovery metrics are
    accurately preserved without exaggeration.
    """
    batch_result = {
        "attempted_transactions": 5,
        "successful_recoveries": 2,
        "failed_recoveries": 3,
        "attempted_amount": 2500.0,
        "recovered_amount": 1000.0,
        "execution_cost": 125.0,
        "net_recovered_value": 875.0,
        "recovery_rate": 0.40,
        "canary_decision": "STOP",
        "guardrail_decision": "CONTINUE",
        "rollback_required": False,
        "final_status": "RECOVERED",
    }

    scorecard = build_system_evaluation_scorecard(
        incident={"degradation_pp": 15.0, "severity": "DEGRADED", "transactions": 45},
        orchestration_result=batch_result,
    )

    assert scorecard.canary_decision == "STOP"
    assert scorecard.attempted_transactions == 5
    assert scorecard.successful_recoveries == 2
    assert scorecard.failed_recoveries == 3
    assert scorecard.recovery_rate == 0.40
    assert scorecard.net_recovered_value == 875.0
    assert scorecard.recovery_roi == round(875.0 / 125.0, 2)  # 7.0x


def test_unprofitable_recovery_rollback():
    """
    6. Unprofitable recovery / rollback.
    Verifies that when cost exceeds recovery, net_recovered_value is negative,
    recovery_roi is negative, and rollback_required is True.
    """
    batch_result = {
        "attempted_transactions": 5,
        "successful_recoveries": 1,
        "failed_recoveries": 4,
        "attempted_amount": 1000.0,
        "recovered_amount": 50.0,
        "execution_cost": 125.0,
        "net_recovered_value": -75.0,
        "recovery_rate": 0.20,
        "canary_decision": "STOP",
        "guardrail_decision": "ROLLBACK",
        "rollback_required": True,
        "final_status": "UNPROFITABLE",
    }

    scorecard = build_system_evaluation_scorecard(
        incident={"degradation_pp": 22.0, "severity": "CRITICAL", "transactions": 60},
        orchestration_result=batch_result,
    )

    assert scorecard.rollback_required is True
    assert scorecard.guardrail_decision == "ROLLBACK"
    assert scorecard.net_recovered_value == -75.0
    assert scorecard.recovery_roi == -0.6
    assert scorecard.final_status == "UNPROFITABLE"


def test_learning_evidence_populated():
    """
    7. Learning evidence populated.
    Verifies that historical learning stats, score lift, and decision change
    attribution are preserved.
    """
    stats = RouteLearningStats(
        route="UPI + Axis + iOS",
        attempts=40,
        recoveries=36,
        recovery_rate=0.90,
        total_recovered_value=40000.0,
        total_execution_cost=1000.0,
        net_recovered_value=39000.0,
        evidence_confidence=0.80,
    )

    scorecard = build_system_evaluation_scorecard(
        incident={"degradation_pp": 15.0, "severity": "DEGRADED", "transactions": 50},
        learning_context={
            "learning_stats": stats,
            "route_score_before": 0.6100,
            "route_score_after": 0.8250,
            "action_before": "ROUTE_SWITCH:Bank_Old",
            "action_after": "ROUTE_SWITCH:UPI+Axis+iOS",
        },
    )

    assert scorecard.learned_attempts == 40
    assert scorecard.learned_recoveries == 36
    assert scorecard.learned_recovery_rate == 0.90
    assert scorecard.learning_evidence_confidence == 0.80
    assert scorecard.route_score_before_learning == 0.6100
    assert scorecard.route_score_after_learning == 0.8250
    assert scorecard.learning_score_delta == 0.2150
    assert scorecard.decision_changed_after_learning is True


def test_no_learning_evidence_does_not_fabricate_values():
    """
    8. No learning evidence does not fabricate values.
    Verifies that when no learning history exists, learning fields remain 0.0
    and decision_changed_after_learning is False.
    """
    scorecard = build_system_evaluation_scorecard(
        incident={"degradation_pp": 10.0, "severity": "DEGRADED", "transactions": 40},
        learning_context=None,
    )

    assert scorecard.learned_attempts == 0
    assert scorecard.learned_recoveries == 0
    assert scorecard.learned_recovery_rate == 0.0
    assert scorecard.learning_evidence_confidence == 0.0
    assert scorecard.route_score_before_learning == 0.0
    assert scorecard.route_score_after_learning == 0.0
    assert scorecard.learning_score_delta == 0.0
    assert scorecard.decision_changed_after_learning is False


def test_financial_metrics_match_authoritative_summary():
    """
    9. Financial metrics exactly match calculate_financial_summary().
    Proves that the adapter does not duplicate financial math, but strictly
    delegates to the authoritative calculator.
    """
    outcome = RecoveryOutcome(
        attempted_transactions=8,
        successful_recoveries=7,
        failed_recoveries=1,
        attempted_amount=8000.0,
        recovered_amount=7000.0,
        execution_cost=200.0,
        net_recovered_value=6800.0,
        recovery_rate=0.875,
        outcome_status="RECOVERED",
        explanation="Authoritative test outcome",
    )

    # Authoritative summary calculation
    expected_fin = calculate_financial_summary(
        revenue_at_risk=25000.0,
        eligible_amount=10000.0,
        recovery_outcome=outcome,
    )

    # Adapter execution
    scorecard = build_system_evaluation_scorecard(
        incident={"revenue_at_risk": 25000.0, "transactions": 80, "degradation_pp": 12.0},
        orchestration_result=outcome,
        eligible_amount=10000.0,
    )

    assert scorecard.revenue_at_risk == expected_fin.revenue_at_risk
    assert scorecard.eligible_amount == expected_fin.eligible_amount
    assert scorecard.attempted_amount == expected_fin.attempted_amount
    assert scorecard.recovered_amount == expected_fin.recovered_amount
    assert scorecard.execution_cost == expected_fin.execution_cost
    assert scorecard.net_recovered_value == expected_fin.net_recovered_value
    assert scorecard.recovery_rate == expected_fin.recovery_rate
    assert scorecard.recovery_roi == expected_fin.recovery_roi


def test_expected_loss_reduction_matches_scorecard_calculation():
    """
    10. Expected-loss reduction matches existing scorecard calculation.
    """
    decision = Decision(
        payment_id="PAY_LOSS",
        recommended_action="ROUTE_SWITCH:Bank_B",
        confidence=0.85,
        expected_loss_before=30000.0,
        expected_loss_after=6000.0,
        estimated_value=24000.0,
    )

    scorecard = build_system_evaluation_scorecard(
        incident={"degradation_pp": 18.0, "severity": "DEGRADED", "transactions": 60},
        decision=decision,
    )

    assert scorecard.expected_loss_before == 30000.0
    assert scorecard.expected_loss_after == 6000.0
    assert scorecard.expected_loss_reduction == 24000.0
    assert scorecard.expected_loss_reduction_percentage == 80.0


def test_learning_score_delta_matches_scorecard_calculation():
    """
    11. Learning score delta matches existing scorecard calculation.
    """
    scorecard = build_system_evaluation_scorecard(
        incident={"degradation_pp": 8.0, "severity": "WATCH", "transactions": 25},
        route_score_before=0.5500,
        route_score_after=0.7825,
    )

    assert scorecard.route_score_before_learning == 0.5500
    assert scorecard.route_score_after_learning == 0.7825
    assert scorecard.learning_score_delta == 0.2325


def test_no_nan_or_inf_values():
    """
    12. No NaN or Inf values.
    Verifies that malformed, NaN, or Inf inputs are sanitized and never leak.
    """
    scorecard = build_system_evaluation_scorecard(
        incident={"degradation_pp": float("nan"), "severity": "CRITICAL", "transactions": 50},
        decision=Decision(
            payment_id="",
            recommended_action="MONITOR",
            confidence=float("nan"),
            expected_loss_before=float("inf"),
            expected_loss_after=float("-inf"),
            estimated_value=float("nan"),
        ),
        revenue_impact=float("nan"),
        eligible_amount=float("inf"),
    )

    data = scorecard.to_dict()
    for k, v in data.items():
        if isinstance(v, float):
            assert not math.isnan(v), f"Key {k} is NaN"
            assert not math.isinf(v), f"Key {k} is Inf"


def test_adapter_has_no_side_effects():
    """
    13. Adapter has no side effects.
    Verifies that domain objects passed in are not mutated, modified, or written.
    """
    decision = Decision(
        payment_id="PAY_IMMUTABLE",
        recommended_action="ROUTE_SWITCH:Bank_X",
        confidence=0.80,
        expected_loss_before=10000.0,
        expected_loss_after=2000.0,
        estimated_value=8000.0,
    )
    decision_copy = copy.deepcopy(decision)

    safety = SafetyDecision(
        payment_id="PAY_IMMUTABLE",
        action="ROUTE_SWITCH:Bank_X",
        allowed=True,
        requires_human_review=False,
        reason="Initial reason",
    )
    safety_copy = copy.deepcopy(safety)

    batch_result = {
        "attempted_transactions": 5,
        "recovered_amount": 1000.0,
        "execution_cost": 125.0,
    }
    batch_copy = copy.deepcopy(batch_result)

    # Call adapter
    EvaluationAdapter.adapt(
        incident={"degradation_pp": 12.0, "severity": "DEGRADED", "transactions": 40},
        decision=decision,
        safety_decision=safety,
        orchestration_result=batch_result,
    )

    # Verify input objects remained identical
    assert decision == decision_copy
    assert safety == safety_copy
    assert batch_result == batch_copy


def test_deterministic_repeated_evaluation():
    """
    14. Deterministic repeated evaluation produces identical results.
    """
    incident = {"degradation_pp": 16.0, "severity": "DEGRADED", "transactions": 55}
    decision = Decision(
        payment_id="PAY_DET",
        recommended_action="ROUTE_SWITCH:Bank_Z",
        confidence=0.82,
        expected_loss_before=20000.0,
        expected_loss_after=4000.0,
        estimated_value=16000.0,
    )
    batch_result = {
        "attempted_transactions": 10,
        "successful_recoveries": 8,
        "failed_recoveries": 2,
        "attempted_amount": 5000.0,
        "recovered_amount": 4000.0,
        "execution_cost": 250.0,
        "net_recovered_value": 3750.0,
        "recovery_rate": 0.80,
        "final_status": "RECOVERED",
    }

    sc1 = build_system_evaluation_scorecard(
        incident=incident,
        decision=decision,
        orchestration_result=batch_result,
    )
    sc2 = build_system_evaluation_scorecard(
        incident=incident,
        decision=decision,
        orchestration_result=batch_result,
    )

    assert sc1.to_dict() == sc2.to_dict()
