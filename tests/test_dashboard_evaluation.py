"""
Unit tests for the Dashboard Evaluation Scorecard Integration (Milestone 5 Step 4).

Verifies the 10 core integration requirements:
1. Evaluation scorecard is generated from runtime outputs.
2. Successful recovery displays simulated recovery values.
3. Blocked safety path does not display fabricated recovery.
4. MONITOR/no-execution path remains unexecuted.
5. ROI is N/A when execution cost is zero.
6. Learning evidence is displayed only when available ("No learning evidence" when none).
7. Reset removes stale evaluation state.
8. Evaluation output changes when the underlying runtime result changes.
9. No hardcoded financial values are introduced.
10. No NaN/Inf values reach the UI.
"""

import math
import pytest

from src.evaluation.evaluation_adapter import (
    DashboardEvaluationView,
    EvaluationAdapter,
    prepare_dashboard_evaluation_scorecard,
)
from src.evaluation.scorecard import SystemEvaluationScorecard
from src.intelligence.incident_intelligence import IncidentAssessment
from src.models.domain import Decision, SafetyDecision
from src.tracking.recovery_learning import RouteLearningStats


@pytest.fixture
def sample_incident():
    return {
        "degradation_pp": 24.5,
        "severity": "CRITICAL",
        "transactions": 150,
        "revenue_at_risk": 75000.0,
    }


@pytest.fixture
def sample_decision():
    return Decision(
        payment_id="PAY_TEST_001",
        recommended_action="ROUTE_SWITCH:UPI + ICICI + Android",
        confidence=0.92,
        expected_loss_before=35000.0,
        expected_loss_after=5000.0,
        estimated_value=30000.0,
        explanation="High failure rate on primary route; switch recommended.",
    )


@pytest.fixture
def sample_safety_allowed():
    return SafetyDecision(
        payment_id="PAY_TEST_001",
        action="ROUTE_SWITCH:UPI + ICICI + Android",
        allowed=True,
        requires_human_review=False,
        reason="Automated safety checks passed within bounds.",
    )


@pytest.fixture
def sample_safety_blocked():
    return SafetyDecision(
        payment_id="PAY_TEST_001",
        action="STOP",
        allowed=False,
        requires_human_review=False,
        reason="Confidence 0.35 below critical threshold 0.40.",
    )


@pytest.fixture
def sample_route_candidates():
    return [
        {"route": "UPI + ICICI + Android", "transactions": 100, "successes": 96},
        {"route": "UPI + AXIS + Android", "transactions": 100, "successes": 88},
    ]


def test_1_scorecard_generated_from_runtime_outputs(
    sample_incident, sample_decision, sample_safety_allowed, sample_route_candidates
):
    """
    Requirement 1: Evaluation scorecard is generated from actual runtime outputs.
    """
    view = prepare_dashboard_evaluation_scorecard(
        incident=sample_incident,
        decision=sample_decision,
        safety_decision=sample_safety_allowed,
        batch_result=None,
        route_candidates=sample_route_candidates,
    )

    assert isinstance(view, DashboardEvaluationView)
    assert isinstance(view.scorecard, SystemEvaluationScorecard)
    assert view.scorecard.degradation_percentage_points == 24.5
    assert view.scorecard.severity == "CRITICAL"
    assert view.scorecard.transactions_observed == 150
    assert view.scorecard.revenue_at_risk == 75000.0
    assert view.scorecard.expected_loss_before == 35000.0
    assert view.scorecard.expected_loss_after == 5000.0
    assert view.scorecard.expected_loss_reduction == 30000.0
    assert view.scorecard.expected_loss_reduction_percentage == round((30000.0 / 35000.0) * 100.0, 2)
    assert view.scorecard.selected_action == "ROUTE_SWITCH:UPI + ICICI + Android"
    assert view.scorecard.safety_allowed is True


def test_2_successful_recovery_displays_simulated_values(
    sample_incident, sample_decision, sample_safety_allowed, sample_route_candidates
):
    """
    Requirement 2: Successful recovery displays simulated recovery values.
    """
    batch_result = {
        "safety_allowed": True,
        "final_status": "RECOVERED",
        "attempted_transactions": 50,
        "successful_recoveries": 45,
        "recovered_amount": 45000.0,
        "attempted_amount": 50000.0,
        "execution_cost": 1250.0,
        "net_recovered_value": 43750.0,
        "recovery_rate": 0.90,
        "canary_decision": "EXPAND",
        "guardrail_decision": "CONTINUE",
        "rollback_required": False,
    }

    view = prepare_dashboard_evaluation_scorecard(
        incident=sample_incident,
        decision=sample_decision,
        safety_decision=sample_safety_allowed,
        batch_result=batch_result,
        route_candidates=sample_route_candidates,
    )

    assert view.has_executed is True
    assert view.is_blocked is False
    assert view.recovery_rate_value == "90.00%"
    assert "43,750.00" in view.net_recovered_value
    assert view.recovery_roi_value == f"{round(43750.0 / 1250.0, 2):.2f}x"
    assert view.final_status == "RECOVERED"
    assert view.canary_decision == "EXPAND"
    assert view.guardrail_decision == "CONTINUE"
    assert view.rollback_required == "NO"
    assert view.recovery_rate_provenance == "SIMULATED"
    assert view.net_recovered_provenance == "SIMULATED"
    assert view.recovery_roi_provenance == "SIMULATED"


def test_3_blocked_safety_path_does_not_display_fabricated_recovery(
    sample_incident, sample_decision, sample_safety_blocked
):
    """
    Requirement 3: Blocked safety path does not display fabricated recovery.
    """
    batch_result = {
        "safety_allowed": False,
        "final_status": "BLOCKED",
        "attempted_transactions": 0,
        "recovered_amount": 0.0,
        "execution_cost": 0.0,
        "canary_decision": "NOT_APPLICABLE",
        "guardrail_decision": "STOP",
        "rollback_required": False,
    }

    view = prepare_dashboard_evaluation_scorecard(
        incident=sample_incident,
        decision=sample_decision,
        safety_decision=sample_safety_blocked,
        batch_result=batch_result,
    )

    assert view.is_blocked is True
    assert view.has_executed is False
    assert view.safety_status_value == "BLOCKED"
    assert view.safety_pill_class == "pill-red"
    assert view.recovery_rate_value == "0.00% (Blocked)"
    assert view.net_recovered_value == "₹0.00 (Blocked)"
    assert view.recovery_roi_value == "N/A"
    assert view.final_status == "BLOCKED"
    assert view.scorecard.recovered_amount == 0.0
    assert view.scorecard.recovery_roi is None


def test_4_monitor_no_execution_path_remains_unexecuted(sample_incident):
    """
    Requirement 4: MONITOR / no-execution path remains unexecuted.
    """
    monitor_decision = Decision(
        payment_id="PAY_MON",
        recommended_action="MONITOR",
        confidence=0.95,
        expected_loss_before=0.0,
        expected_loss_after=0.0,
        estimated_value=0.0,
    )

    view = prepare_dashboard_evaluation_scorecard(
        incident=sample_incident,
        decision=monitor_decision,
        batch_result=None,
    )

    assert view.has_executed is False
    assert view.recovery_rate_value == "Not executed"
    assert view.net_recovered_value == "Not executed"
    assert view.recovery_roi_value == "N/A"
    assert view.final_status == "NO_EXECUTION"
    assert view.scorecard.attempted_transactions == 0
    assert view.scorecard.recovered_amount == 0.0
    assert view.scorecard.recovery_roi is None


def test_5_roi_is_na_when_execution_cost_is_zero(
    sample_incident, sample_decision, sample_safety_allowed
):
    """
    Requirement 5: ROI is N/A when execution cost is zero.
    """
    batch_result = {
        "safety_allowed": True,
        "final_status": "NO_EXECUTION",
        "attempted_transactions": 0,
        "recovered_amount": 0.0,
        "execution_cost": 0.0,
        "net_recovered_value": 0.0,
        "recovery_rate": 0.0,
    }

    view = prepare_dashboard_evaluation_scorecard(
        incident=sample_incident,
        decision=sample_decision,
        safety_decision=sample_safety_allowed,
        batch_result=batch_result,
    )

    assert view.recovery_roi_value == "N/A"
    assert view.scorecard.recovery_roi is None


def test_6_learning_evidence_displayed_only_when_available(
    sample_incident, sample_decision, sample_safety_allowed, sample_route_candidates
):
    """
    Requirement 6: Learning evidence is displayed only when available.
    When unavailable, clearly display 'No learning evidence' rather than a fake zero lift.
    """
    # Case A: No learning evidence
    view_no_learning = prepare_dashboard_evaluation_scorecard(
        incident=sample_incident,
        decision=sample_decision,
        safety_decision=sample_safety_allowed,
        batch_result=None,
        learning_history=None,
        route_candidates=sample_route_candidates,
    )
    assert view_no_learning.has_learning_evidence is False
    assert view_no_learning.learning_lift_value == "No learning evidence"
    assert view_no_learning.learning_pill_class == "pill-blue"
    assert "No prior outcome" in view_no_learning.learning_sub

    # Case B: With learning evidence
    learning_stats = RouteLearningStats(
        route="UPI + ICICI + Android",
        attempts=60,
        recoveries=54,
        recovery_rate=0.90,
        total_recovered_value=54000.0,
        total_execution_cost=1500.0,
        net_recovered_value=52500.0,
        evidence_confidence=0.88,
    )

    view_with_learning = prepare_dashboard_evaluation_scorecard(
        incident=sample_incident,
        decision=sample_decision,
        safety_decision=sample_safety_allowed,
        batch_result={"learning_stats": learning_stats},
        learning_history={"UPI + ICICI + Android": learning_stats},
        route_candidates=sample_route_candidates,
    )

    assert view_with_learning.has_learning_evidence is True
    assert "score lift" in view_with_learning.learning_lift_value
    assert view_with_learning.learning_pill_class == "pill-green"
    assert "60 attempts" in view_with_learning.learning_sub
    assert "88.0% confidence" in view_with_learning.learning_sub


def test_7_reset_removes_stale_evaluation_state(
    sample_incident, sample_decision, sample_safety_allowed, sample_route_candidates
):
    """
    Requirement 7: Reset removes stale evaluation state.
    Simulates session state lifecycle: running recovery -> resetting -> view returns to unexecuted.
    """
    session_state = {}

    # Step 1: Execute recovery
    batch_result = {
        "safety_allowed": True,
        "final_status": "RECOVERED",
        "attempted_transactions": 50,
        "successful_recoveries": 42,
        "recovered_amount": 42000.0,
        "attempted_amount": 50000.0,
        "execution_cost": 1250.0,
        "net_recovered_value": 40750.0,
        "recovery_rate": 0.84,
    }
    session_state["batch_result"] = batch_result
    view_executed = prepare_dashboard_evaluation_scorecard(
        incident=sample_incident,
        decision=sample_decision,
        safety_decision=sample_safety_allowed,
        batch_result=session_state["batch_result"],
        route_candidates=sample_route_candidates,
    )
    session_state["evaluation_scorecard"] = view_executed.scorecard
    assert view_executed.has_executed is True
    assert session_state["evaluation_scorecard"].net_recovered_value == 40750.0

    # Step 2: User triggers Reset
    session_state["batch_result"] = None
    session_state["evaluation_scorecard"] = None

    # Step 3: View re-evaluates after reset
    view_reset = prepare_dashboard_evaluation_scorecard(
        incident=sample_incident,
        decision=sample_decision,
        safety_decision=sample_safety_allowed,
        batch_result=session_state["batch_result"],
        route_candidates=sample_route_candidates,
    )
    assert view_reset.has_executed is False
    assert view_reset.recovery_rate_value == "Not executed"
    assert view_reset.net_recovered_value == "Not executed"
    assert view_reset.recovery_roi_value == "N/A"
    assert view_reset.scorecard.net_recovered_value == 0.0


def test_8_evaluation_output_changes_when_underlying_runtime_result_changes(
    sample_incident, sample_decision, sample_safety_allowed
):
    """
    Requirement 8: Evaluation output dynamically changes when underlying runtime inputs change.
    """
    # Batch run A: 30 attempts, 25 recoveries
    batch_a = {
        "safety_allowed": True,
        "final_status": "RECOVERED",
        "attempted_transactions": 30,
        "successful_recoveries": 25,
        "recovered_amount": 25000.0,
        "execution_cost": 750.0,
        "net_recovered_value": 24250.0,
        "recovery_rate": round(25 / 30, 4),
    }
    view_a = prepare_dashboard_evaluation_scorecard(
        incident=sample_incident,
        decision=sample_decision,
        safety_decision=sample_safety_allowed,
        batch_result=batch_a,
    )

    # Batch run B: 50 attempts, 48 recoveries
    batch_b = {
        "safety_allowed": True,
        "final_status": "RECOVERED",
        "attempted_transactions": 50,
        "successful_recoveries": 48,
        "recovered_amount": 48000.0,
        "execution_cost": 1250.0,
        "net_recovered_value": 46750.0,
        "recovery_rate": round(48 / 50, 4),
    }
    view_b = prepare_dashboard_evaluation_scorecard(
        incident=sample_incident,
        decision=sample_decision,
        safety_decision=sample_safety_allowed,
        batch_result=batch_b,
    )

    assert view_a.recovery_rate_value != view_b.recovery_rate_value
    assert view_a.net_recovered_value != view_b.net_recovered_value
    assert view_a.recovery_roi_value != view_b.recovery_roi_value
    assert view_a.scorecard.attempted_transactions == 30
    assert view_b.scorecard.attempted_transactions == 50


def test_9_no_hardcoded_financial_values_introduced(sample_safety_allowed):
    """
    Requirement 9: No hardcoded financial values are introduced; formulas and summaries
    strictly derive from authoritative calculators and inputs.
    """
    incident_x = {"degradation_pp": 18.2, "severity": "DEGRADED", "transactions": 88, "revenue_at_risk": 43210.50}
    decision_x = Decision(
        payment_id="PAY_X",
        recommended_action="ROUTE_SWITCH:Bank_X",
        confidence=0.88,
        expected_loss_before=21000.0,
        expected_loss_after=3000.0,
        estimated_value=18000.0,
    )
    batch_x = {
        "safety_allowed": True,
        "final_status": "RECOVERED",
        "attempted_transactions": 20,
        "successful_recoveries": 17,
        "recovered_amount": 17500.0,
        "execution_cost": 500.0,
        "net_recovered_value": 17000.0,
        "recovery_rate": 0.85,
    }

    view = prepare_dashboard_evaluation_scorecard(
        incident=incident_x,
        decision=decision_x,
        safety_decision=sample_safety_allowed,
        batch_result=batch_x,
    )

    assert "43,210.50" in view.revenue_at_risk_value
    assert "17,000.00" in view.net_recovered_value
    assert view.recovery_roi_value == "34.00x"  # 17000 / 500


def test_10_no_nan_or_inf_values_reach_the_ui():
    """
    Requirement 10: No NaN or Inf values reach the UI view.
    """
    malformed_incident = {
        "degradation_pp": float("nan"),
        "severity": None,
        "transactions": float("inf"),
        "revenue_at_risk": float("nan"),
    }
    malformed_decision = Decision(
        payment_id="",
        recommended_action="MONITOR",
        confidence=float("nan"),
        expected_loss_before=float("inf"),
        expected_loss_after=float("-inf"),
        estimated_value=float("nan"),
    )
    malformed_batch = {
        "safety_allowed": True,
        "final_status": None,
        "attempted_transactions": float("nan"),
        "successful_recoveries": float("inf"),
        "recovered_amount": float("nan"),
        "execution_cost": float("inf"),
        "net_recovered_value": float("nan"),
        "recovery_rate": float("nan"),
    }

    view = prepare_dashboard_evaluation_scorecard(
        incident=malformed_incident,
        decision=malformed_decision,
        batch_result=malformed_batch,
    )

    # Check that all string representations contain no 'nan' or 'inf'
    for attr in dir(view):
        if attr.startswith("_"):
            continue
        val = getattr(view, attr)
        if isinstance(val, str):
            assert "nan" not in val.lower(), f"Attribute {attr} contains 'nan': {val}"
            assert "inf" not in val.lower(), f"Attribute {attr} contains 'inf': {val}"

    # Check that scorecard fields are valid floats
    for k, v in view.scorecard.to_dict().items():
        if isinstance(v, float):
            assert not math.isnan(v), f"Scorecard field {k} is NaN"
            assert not math.isinf(v), f"Scorecard field {k} is Inf"
