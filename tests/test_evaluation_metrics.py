import math
import pytest

from src.evaluation.scorecard import (
    METRIC_PROVENANCE,
    SystemEvaluationScorecard,
    build_scorecard,
)
from src.intelligence.incident_intelligence import IncidentAssessment
from src.intelligence.route_scoring import RouteScore
from src.models.domain import Decision, SafetyDecision
from src.tracking.financial_summary import (
    FinancialSummary,
    calculate_financial_summary,
)
from src.tracking.recovery_learning import RouteLearningStats
from src.tracking.recovery_outcome import RecoveryOutcome


def test_complete_successful_recovery_scorecard():
    """
    1. Complete successful recovery scorecard.
    Verifies that all 6 categories (Incident, Financial, Decision,
    Recovery, Safety, Learning) populate accurately from domain objects.
    """
    incident = IncidentAssessment(
        route="UPI + HDFC + Android",
        baseline_success_rate=0.95,
        current_success_rate=0.70,
        degradation_pp=25.0,
        transactions_observed=120,
        failures_observed=36,
        severity="CRITICAL",
        incident_detected=True,
        explanation="Route degradation of 25.0 pp exceeds critical threshold",
    )

    decision = Decision(
        payment_id="INCIDENT:UPI+HDFC+Android",
        recommended_action="ROUTE_SWITCH:UPI+ICICI+Android",
        confidence=0.88,
        expected_loss_before=60000.0,
        expected_loss_after=12000.0,
        estimated_value=48000.0,
        explanation="Switch to high-performing ICICI route",
    )

    safety = SafetyDecision(
        payment_id="INCIDENT:UPI+HDFC+Android",
        action="ROUTE_SWITCH:UPI+ICICI+Android",
        allowed=True,
        requires_human_review=False,
        reason="Action within safe financial exposure and confidence limits",
    )

    batch_result = {
        "eligible_transactions": 36,
        "eligible_amount": 54000.0,
        "attempted_transactions": 10,
        "successful_recoveries": 9,
        "failed_recoveries": 1,
        "attempted_amount": 15000.0,
        "recovered_amount": 13500.0,
        "execution_cost": 250.0,
        "net_recovered_value": 13250.0,
        "recovery_rate": 0.90,
        "canary_decision": "EXPAND",
        "guardrail_decision": "CONTINUE",
        "rollback_required": False,
        "final_status": "RECOVERED",
    }

    learning_stats = RouteLearningStats(
        route="UPI + ICICI + Android",
        attempts=25,
        recoveries=23,
        recovery_rate=0.92,
        total_recovered_value=34500.0,
        total_execution_cost=625.0,
        net_recovered_value=33875.0,
        evidence_confidence=0.7143,
    )

    scorecard = build_scorecard(
        incident=incident,
        decision=decision,
        safety_decision=safety,
        batch_result=batch_result,
        learning_stats=learning_stats,
        route_score_before=RouteScore(
            route="UPI + ICICI + Android",
            transactions=100,
            successes=94,
            observed_success_rate=0.94,
            adjusted_success_rate=0.94,
            evidence_confidence=0.7071,
            score=0.6647,
            explanation="Initial route score",
        ),
        route_score_after=RouteScore(
            route="UPI + ICICI + Android",
            transactions=125,
            successes=117,
            observed_success_rate=0.936,
            adjusted_success_rate=0.9378,
            evidence_confidence=0.7454,
            score=0.6990,
            explanation="Post-learning route score",
        ),
        action_before="ROUTE_SWITCH:UPI+SBI+Android",
        action_after="ROUTE_SWITCH:UPI+ICICI+Android",
        revenue_at_risk=45000.0,
    )

    # 1. INCIDENT
    assert scorecard.degradation_percentage_points == 25.0
    assert scorecard.severity == "CRITICAL"
    assert scorecard.transactions_observed == 120
    assert scorecard.incident_detected is True

    # 2. FINANCIAL (Authoritative FinancialSummary integration)
    assert scorecard.revenue_at_risk == 45000.0
    assert scorecard.eligible_amount == 54000.0
    assert scorecard.attempted_amount == 15000.0
    assert scorecard.recovered_amount == 13500.0
    assert scorecard.execution_cost == 250.0
    assert scorecard.net_recovered_value == 13250.0
    assert scorecard.recovery_rate == 0.90
    assert scorecard.recovery_roi == round(13250.0 / 250.0, 2)  # 53.0x

    # 3. DECISION
    assert scorecard.expected_loss_before == 60000.0
    assert scorecard.expected_loss_after == 12000.0
    assert scorecard.expected_loss_reduction == 48000.0
    assert scorecard.expected_loss_reduction_percentage == 80.0
    assert scorecard.decision_confidence == 0.88
    assert scorecard.selected_action == "ROUTE_SWITCH:UPI+ICICI+Android"

    # 4. RECOVERY
    assert scorecard.attempted_transactions == 10
    assert scorecard.successful_recoveries == 9
    assert scorecard.failed_recoveries == 1
    assert scorecard.canary_decision == "EXPAND"
    assert scorecard.guardrail_decision == "CONTINUE"
    assert scorecard.rollback_required is False
    assert scorecard.final_status == "RECOVERED"

    # 5. SAFETY
    assert scorecard.safety_allowed is True
    assert scorecard.human_review_required is False
    assert "safe" in scorecard.safety_reason

    # 6. LEARNING
    assert scorecard.learned_attempts == 25
    assert scorecard.learned_recoveries == 23
    assert scorecard.learned_recovery_rate == 0.92
    assert scorecard.learning_evidence_confidence == 0.7143
    assert scorecard.route_score_before_learning == 0.6647
    assert scorecard.route_score_after_learning == 0.6990
    assert scorecard.learning_score_delta == round(0.6990 - 0.6647, 4)
    assert scorecard.decision_changed_after_learning is True


def test_unexecuted_recovery():
    """
    2. Unexecuted recovery.
    Verifies that when recovery is not simulated/executed, simulated fields
    are safely zeroed and recovery_roi is None with final_status='NO_EXECUTION'.
    """
    incident = {
        "degradation_percentage_points": 14.5,
        "severity": "DEGRADED",
        "transactions": 80,
    }

    decision = {
        "recommended_action": "ROUTE_SWITCH:Bank_B",
        "confidence": 0.75,
        "expected_loss_before": 20000.0,
        "expected_loss_after": 5000.0,
    }

    scorecard = build_scorecard(
        incident=incident,
        decision=decision,
        revenue_at_risk=15000.0,
    )

    assert scorecard.attempted_amount == 0.0
    assert scorecard.recovered_amount == 0.0
    assert scorecard.execution_cost == 0.0
    assert scorecard.net_recovered_value == 0.0
    assert scorecard.recovery_rate == 0.0
    assert scorecard.recovery_roi is None

    assert scorecard.attempted_transactions == 0
    assert scorecard.successful_recoveries == 0
    assert scorecard.failed_recoveries == 0
    assert scorecard.canary_decision == "NOT_APPLICABLE"
    assert scorecard.guardrail_decision == "NOT_APPLICABLE"
    assert scorecard.rollback_required is False
    assert scorecard.final_status == "NO_EXECUTION"


def test_zero_execution_cost():
    """
    3. Zero execution cost.
    Verifies no division-by-zero error, recovery_roi is None,
    and net_recovered_value equals 0.0.
    """
    outcome = RecoveryOutcome(
        attempted_transactions=0,
        successful_recoveries=0,
        failed_recoveries=0,
        attempted_amount=0.0,
        recovered_amount=0.0,
        execution_cost=0.0,
        net_recovered_value=0.0,
        recovery_rate=0.0,
        outcome_status="NO_EXECUTION",
        explanation="No recovery execution attempted.",
    )

    scorecard = build_scorecard(
        recovery_outcome=outcome,
        revenue_at_risk=10000.0,
    )

    assert scorecard.execution_cost == 0.0
    assert scorecard.recovery_roi is None
    assert scorecard.net_recovered_value == 0.0


def test_zero_expected_loss():
    """
    4. Zero expected loss.
    Verifies expected_loss_reduction is 0.0 and percentage is safely 0.0
    without ZeroDivisionError.
    """
    decision = Decision(
        payment_id="PAY_ZERO",
        recommended_action="MONITOR",
        confidence=0.50,
        expected_loss_before=0.0,
        expected_loss_after=0.0,
        estimated_value=0.0,
    )

    scorecard = build_scorecard(
        decision=decision,
        expected_loss_before=0.0,
        expected_loss_after=0.0,
    )

    assert scorecard.expected_loss_before == 0.0
    assert scorecard.expected_loss_after == 0.0
    assert scorecard.expected_loss_reduction == 0.0
    assert scorecard.expected_loss_reduction_percentage == 0.0


def test_unprofitable_recovery():
    """
    5. Unprofitable recovery.
    Verifies that when cost exceeds recovery, net_recovered_value is negative,
    recovery_roi is negative, and final_status and rollback reflect the deficit.
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

    scorecard = build_scorecard(
        batch_result=batch_result,
        revenue_at_risk=20000.0,
    )

    assert scorecard.attempted_transactions == 5
    assert scorecard.successful_recoveries == 1
    assert scorecard.recovered_amount == 50.0
    assert scorecard.execution_cost == 125.0
    assert scorecard.net_recovered_value == -75.0
    assert scorecard.recovery_roi == -0.6
    assert scorecard.canary_decision == "STOP"
    assert scorecard.guardrail_decision == "ROLLBACK"
    assert scorecard.rollback_required is True
    assert scorecard.final_status == "UNPROFITABLE"


def test_safety_blocked_recovery():
    """
    6. Safety-blocked recovery.
    Verifies that critical exposure or confidence policy violations produce
    safety_allowed=False, correct reason, and prevent automated execution.
    """
    safety = SafetyDecision(
        payment_id="PAY_CRITICAL",
        action="STOP",
        allowed=False,
        requires_human_review=False,
        reason="Financial exposure ₹2,500,000 exceeds critical ceiling ₹2,000,000",
    )

    scorecard = build_scorecard(
        safety_decision=safety,
        selected_action="STOP",
        decision_confidence=0.35,
    )

    assert scorecard.safety_allowed is False
    assert scorecard.human_review_required is False
    assert "critical ceiling" in scorecard.safety_reason
    assert scorecard.attempted_transactions == 0
    assert scorecard.final_status == "NO_EXECUTION"


def test_learning_lift():
    """
    7. Learning lift.
    Verifies that route learning stats, route score delta, and decision change
    attribution are computed accurately.
    """
    stats = RouteLearningStats(
        route="UPI + Axis + iOS",
        attempts=30,
        recoveries=27,
        recovery_rate=0.8833,
        total_recovered_value=45000.0,
        total_execution_cost=750.0,
        net_recovered_value=44250.0,
        evidence_confidence=0.75,
    )

    scorecard = build_scorecard(
        learning_stats=stats,
        route_score_before=0.6200,
        route_score_after=0.8150,
        action_before="ROUTE_SWITCH:Bank_Old",
        action_after="ROUTE_SWITCH:UPI+Axis+iOS",
    )

    assert scorecard.learned_attempts == 30
    assert scorecard.learned_recoveries == 27
    assert scorecard.learned_recovery_rate == 0.8833
    assert scorecard.learning_evidence_confidence == 0.75
    assert scorecard.route_score_before_learning == 0.6200
    assert scorecard.route_score_after_learning == 0.8150
    assert scorecard.learning_score_delta == 0.1950
    assert scorecard.decision_changed_after_learning is True


def test_no_learning_evidence():
    """
    8. No learning evidence.
    Verifies safe zeroing of learning metrics when no historical recovery
    evidence exists, without inventing synthetic lift.
    """
    scorecard = build_scorecard(
        learning_stats=None,
        route_score_before=None,
        route_score_after=None,
        action_before=None,
        action_after=None,
    )

    assert scorecard.learned_attempts == 0
    assert scorecard.learned_recoveries == 0
    assert scorecard.learned_recovery_rate == 0.0
    assert scorecard.learning_evidence_confidence == 0.0
    assert scorecard.route_score_before_learning == 0.0
    assert scorecard.route_score_after_learning == 0.0
    assert scorecard.learning_score_delta == 0.0
    assert scorecard.decision_changed_after_learning is False


def test_expected_loss_reduction_calculation():
    """
    9. Expected loss reduction calculation.
    Tests various loss configurations:
    - Normal reduction
    - Zero loss after (100% reduction)
    - Worsened loss after (clamped to 0)
    """
    # Normal reduction: 10,000 -> 2,500 = 7,500 (75%)
    sc1 = build_scorecard(
        expected_loss_before=10000.0,
        expected_loss_after=2500.0,
    )
    assert sc1.expected_loss_reduction == 7500.0
    assert sc1.expected_loss_reduction_percentage == 75.0

    # Complete loss prevention: 8,000 -> 0 = 8,000 (100%)
    sc2 = build_scorecard(
        expected_loss_before=8000.0,
        expected_loss_after=0.0,
    )
    assert sc2.expected_loss_reduction == 8000.0
    assert sc2.expected_loss_reduction_percentage == 100.0

    # Worsened outcome: 5,000 -> 6,000 = reduction clamped to 0.0
    sc3 = build_scorecard(
        expected_loss_before=5000.0,
        expected_loss_after=6000.0,
    )
    assert sc3.expected_loss_reduction == 0.0
    assert sc3.expected_loss_reduction_percentage == 0.0


def test_zero_division_protection():
    """
    10. Zero-division protection.
    Explicitly passes 0 for all denominator candidates (transactions,
    expected_loss_before, execution_cost, attempts).
    """
    scorecard = build_scorecard(
        transactions_observed=0,
        expected_loss_before=0.0,
        expected_loss_after=0.0,
        execution_cost=0.0,
        learned_attempts=0,
        learned_recoveries=0,
    )

    assert scorecard.expected_loss_reduction_percentage == 0.0
    assert scorecard.recovery_roi is None
    assert scorecard.recovery_rate == 0.0
    assert scorecard.learned_recovery_rate == 0.0


def test_provenance_type_labels():
    """
    11. Provenance/type labels.
    Verifies that all metrics strictly belong to the authoritative semantic categories:
    - OBSERVED
    - THEORETICAL / COUNTERFACTUAL
    - SIMULATED
    - GOVERNED / EVALUATED
    - LEARNED
    """
    valid_categories = {
        "OBSERVED",
        "THEORETICAL / COUNTERFACTUAL",
        "SIMULATED",
        "GOVERNED / EVALUATED",
        "LEARNED",
    }

    scorecard = build_scorecard()
    provenance = scorecard.provenance

    for metric_name, category in provenance.items():
        assert (
            category in valid_categories
        ), f"Metric '{metric_name}' has invalid category '{category}'"

    # Specific strict provenance assertions
    assert scorecard.get_provenance("degradation_percentage_points") == "OBSERVED"
    assert scorecard.get_provenance("transactions_observed") == "OBSERVED"
    assert scorecard.get_provenance("revenue_at_risk") == "THEORETICAL / COUNTERFACTUAL"
    assert scorecard.get_provenance("expected_loss_before") == "THEORETICAL / COUNTERFACTUAL"
    assert scorecard.get_provenance("recovered_amount") == "SIMULATED"
    assert scorecard.get_provenance("net_recovered_value") == "SIMULATED"
    assert scorecard.get_provenance("recovery_roi") == "SIMULATED"
    assert scorecard.get_provenance("safety_allowed") == "GOVERNED / EVALUATED"
    assert scorecard.get_provenance("learned_recovery_rate") == "LEARNED"
    assert scorecard.get_provenance("learning_score_delta") == "LEARNED"


def test_no_nan_or_inf_output():
    """
    12. No NaN/Inf output.
    Verifies that passing NaN, Inf, or -Inf to numeric fields produces
    deterministic safe default floats without raising exceptions or leaking NaN.
    """
    nan = float("nan")
    inf = float("inf")
    neg_inf = float("-inf")

    scorecard = build_scorecard(
        degradation_percentage_points=nan,
        revenue_at_risk=inf,
        eligible_amount=neg_inf,
        attempted_amount=nan,
        recovered_amount=inf,
        execution_cost=nan,
        net_recovered_value=inf,
        recovery_rate=nan,
        recovery_roi=inf,
        expected_loss_before=nan,
        expected_loss_after=inf,
        expected_loss_reduction=nan,
        expected_loss_reduction_percentage=inf,
        decision_confidence=nan,
        route_score_before_learning=nan,
        route_score_after_learning=inf,
        learning_score_delta=nan,
    )

    data = scorecard.to_dict()

    for field_name, value in data.items():
        if isinstance(value, float):
            assert not math.isnan(
                value
            ), f"Field '{field_name}' contains NaN!"
            assert not math.isinf(
                value
            ), f"Field '{field_name}' contains Inf!"
