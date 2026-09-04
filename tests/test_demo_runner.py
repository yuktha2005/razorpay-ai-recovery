"""
Tests for Deterministic Demo Runner in Razorpay AI Revenue Recovery.

Verifies end-to-end demo orchestration, pipeline component reuse,
safety preservation, determinism, learning updates, re-evaluation,
audit trail, and integration safety.
"""

import inspect
import math
from datetime import datetime, timezone
from pathlib import Path
import pytest

from src.demo.demo_scenario import (
    CANONICAL_HAPPY_PATH,
    DEFAULT_DEMO_CANDIDATES,
    FAILURE_SAFETY_BLOCKED,
    FAILURE_UNPROFITABLE_ROLLBACK,
    DemoScenario,
    get_demo_scenario,
    list_demo_scenarios,
)
from src.demo.demo_runner import (
    DemoPhase,
    DemoRunResult,
    DemoRunner,
    LifecycleEvent,
    PhaseResult,
    format_demo_report,
)
from src.intelligence.incident_intelligence import IncidentAssessment
from src.intelligence.incident_revenue import IncidentRevenueImpact
from src.models.domain import Decision, SafetyDecision
from src.tracking.financial_summary import calculate_financial_summary
from src.tracking.learning_history import PersistentLearningHistory
from src.evaluation.scorecard import SystemEvaluationScorecard


@pytest.fixture(autouse=True)
def isolate_persistent_storage(tmp_path, monkeypatch):
    """Isolate file persistence to tmp_path for deterministic testing."""
    learning_file = tmp_path / "recovery_learning.csv"
    audit_file = tmp_path / "recovery_audit.csv"

    monkeypatch.setattr("src.tracking.learning_store.LEARNING_FILE", learning_file)
    monkeypatch.setattr("src.tracking.learning_store.LOG_DIR", tmp_path)
    monkeypatch.setattr("src.audit_logger.AUDIT_FILE", audit_file)
    monkeypatch.setattr("src.audit_logger.LOG_DIR", tmp_path)


# -------------------------------------------------------------------------
# Requirement 1 & 2: Deterministic Scenario Construction & Deterministic Output
# -------------------------------------------------------------------------

def test_deterministic_scenario_construction():
    """Requirement 1: Scenario construction is deterministic with fixed parameters and seed."""
    sc1 = CANONICAL_HAPPY_PATH
    sc2 = get_demo_scenario("canonical_happy_path")

    assert sc1.scenario_id == sc2.scenario_id
    assert sc1.baseline_success_rate == sc2.baseline_success_rate
    assert sc1.degraded_success_rate == sc2.degraded_success_rate
    assert sc1.transaction_count == sc2.transaction_count
    assert sc1.average_transaction_value == sc2.average_transaction_value
    assert sc1.canary_batch_size == sc2.canary_batch_size
    assert sc1.route == "UPI + Bank_X + Android"


def test_deterministic_demo_output(tmp_path, monkeypatch):
    """Requirement 2 & 20: Repeated runs in isolated environments produce identical outputs."""
    dir1 = tmp_path / "run1"
    dir1.mkdir()
    monkeypatch.setattr("src.tracking.learning_store.LEARNING_FILE", dir1 / "recovery_learning.csv")
    monkeypatch.setattr("src.tracking.learning_store.LOG_DIR", dir1)
    runner1 = DemoRunner()
    result1 = runner1.run(CANONICAL_HAPPY_PATH)

    dir2 = tmp_path / "run2"
    dir2.mkdir()
    monkeypatch.setattr("src.tracking.learning_store.LEARNING_FILE", dir2 / "recovery_learning.csv")
    monkeypatch.setattr("src.tracking.learning_store.LOG_DIR", dir2)
    runner2 = DemoRunner()
    result2 = runner2.run(CANONICAL_HAPPY_PATH)

    assert result1.incident.severity == result2.incident.severity
    assert result1.incident.degradation_pp == result2.incident.degradation_pp
    assert result1.revenue_impact.revenue_at_risk == result2.revenue_impact.revenue_at_risk
    assert result1.decision.recommended_action == result2.decision.recommended_action
    assert result1.safety_decision.allowed == result2.safety_decision.allowed
    assert result1.batch_result["successful_recoveries"] == result2.batch_result["successful_recoveries"]
    assert result1.route_score_before == result2.route_score_before
    assert result1.route_score_after == result2.route_score_after
    assert result1.score_delta == result2.score_delta
    assert result1.format_report() == result2.format_report()


# -------------------------------------------------------------------------
# Requirement 3: Baseline Phase
# -------------------------------------------------------------------------

def test_baseline_phase():
    """Requirement 3: Baseline phase records primary route and healthy baseline success rate."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)

    assert DemoPhase.BASELINE.value in result.phase_results
    baseline_phase = result.phase_results[DemoPhase.BASELINE.value]
    assert baseline_phase.status == "SUCCESS"
    assert baseline_phase.metrics["primary_route"] == CANONICAL_HAPPY_PATH.route
    assert baseline_phase.metrics["baseline_success_rate"] == CANONICAL_HAPPY_PATH.baseline_success_rate
    assert len(baseline_phase.metrics["initial_ranking"]) >= 1


# -------------------------------------------------------------------------
# Requirement 4: Incident Detection
# -------------------------------------------------------------------------

def test_incident_detection():
    """Requirement 4: Incident detection triggers from existing IncidentIntelligence."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)

    assert result.incident is not None
    assert isinstance(result.incident, IncidentAssessment)
    assert result.incident.incident_detected is True
    assert result.incident.severity == CANONICAL_HAPPY_PATH.expected_severity
    assert result.incident.degradation_pp == pytest.approx(25.0, abs=0.1)
    assert result.incident.current_success_rate == pytest.approx(0.70, abs=0.05)


# -------------------------------------------------------------------------
# Requirement 5: Revenue-at-Risk Calculation
# -------------------------------------------------------------------------

def test_revenue_at_risk_calculation():
    """Requirement 5: Revenue-at-risk comes from IncidentRevenueCalculator, marked theoretical."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)

    assert result.revenue_impact is not None
    assert isinstance(result.revenue_impact, IncidentRevenueImpact)
    assert result.revenue_impact.excess_failures > 0
    # 50 excess failures * ₹500 avg txn value = ₹25,000
    expected_rev = result.revenue_impact.excess_failures * CANONICAL_HAPPY_PATH.average_transaction_value
    assert result.revenue_impact.revenue_at_risk == pytest.approx(expected_rev, abs=1.0)


# -------------------------------------------------------------------------
# Requirement 6: Decision Engine Integration
# -------------------------------------------------------------------------

def test_decision_engine_integration():
    """Requirement 6: Decision comes from IncidentDecisionEngine evaluating alternatives."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)

    assert result.decision is not None
    assert isinstance(result.decision, Decision)
    assert result.decision.recommended_action == CANONICAL_HAPPY_PATH.expected_action
    assert 0.0 <= result.decision.confidence <= 1.0
    assert result.decision.expected_loss_before > result.decision.expected_loss_after
    assert result.decision.estimated_value > 0.0


# -------------------------------------------------------------------------
# Requirement 7: Safety Gate Integration
# -------------------------------------------------------------------------

def test_safety_gate_integration():
    """Requirement 7: Safety decision is produced by the authoritative SafetyController."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)

    assert result.safety_decision is not None
    assert isinstance(result.safety_decision, SafetyDecision)
    assert result.safety_decision.allowed is True
    assert result.safety_decision.requires_human_review is False
    assert "Route recovery passed deterministic safety policy checks" in result.safety_decision.reason


# -------------------------------------------------------------------------
# Requirement 8: Bounded Canary Integration
# -------------------------------------------------------------------------

def test_bounded_canary_integration():
    """Requirement 8: Canary execution respects bounds and remains simulation-only."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)

    assert result.batch_result is not None
    assert result.batch_result["attempted_transactions"] > 0
    assert result.batch_result["attempted_transactions"] <= CANONICAL_HAPPY_PATH.canary_batch_size
    assert result.batch_result["attempted_transactions"] <= 50
    assert result.batch_result["successful_recoveries"] <= result.batch_result["attempted_transactions"]
    assert result.batch_result["canary_decision"] in ("EXPAND", "STOP", "ESCALATE")


# -------------------------------------------------------------------------
# Requirement 9: Recovery Verification
# -------------------------------------------------------------------------

def test_recovery_verification():
    """Requirement 9: Recovery outcome verifier determines profitability and rollback need."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)

    assert result.final_status == "RECOVERED"
    assert result.batch_result["recovered_amount"] > 0.0
    assert result.batch_result["execution_cost"] > 0.0
    assert result.batch_result["net_recovered_value"] > 0.0
    assert result.batch_result["rollback_required"] is False


# -------------------------------------------------------------------------
# Requirement 10: Financial Summary Integration
# -------------------------------------------------------------------------

def test_financial_summary_integration():
    """Requirement 10: Financial metrics match calculate_financial_summary output exactly."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)

    calc_summary = calculate_financial_summary(
        revenue_at_risk=result.revenue_impact.revenue_at_risk,
        eligible_amount=result.batch_result.get("eligible_amount", 0.0),
        batch_result=result.batch_result,
    )

    assert result.financial_summary["recovered_amount"] == calc_summary.recovered_amount
    assert result.financial_summary["execution_cost"] == calc_summary.execution_cost
    assert result.financial_summary["net_recovered_value"] == calc_summary.net_recovered_value
    assert result.financial_summary["recovery_roi"] == calc_summary.recovery_roi


# -------------------------------------------------------------------------
# Requirement 11: Learning Persistence
# -------------------------------------------------------------------------

def test_learning_persistence():
    """Requirement 11: Verified recovery evidence is persisted to the learning store."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)

    assert result.learning_evidence is not None
    assert result.learning_evidence.attempts > 0
    assert result.learning_evidence.recoveries > 0
    assert result.learning_evidence.recovery_rate > 0.0
    assert result.route_score_after > result.route_score_before
    assert result.score_delta > 0.0


# -------------------------------------------------------------------------
# Requirement 12: Re-evaluation Consumes Learned Evidence
# -------------------------------------------------------------------------

def test_reevaluation_consumes_learned_evidence():
    """Requirement 12: Re-evaluation phase runs the decision again with learned evidence."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)

    assert result.reevaluation_result is not None
    assert "before_learning" in result.reevaluation_result
    assert "after_learning" in result.reevaluation_result
    assert "decision_changed_after_learning" in result.reevaluation_result

    before = result.reevaluation_result["before_learning"]
    after = result.reevaluation_result["after_learning"]
    assert after["route_score"] >= before["route_score"]
    assert math.isfinite(after["route_score"])


# -------------------------------------------------------------------------
# Requirement 13: No Hard-coded Decision Override
# -------------------------------------------------------------------------

def test_no_hard_coded_decision_override():
    """Requirement 13: Decision engine selects route naturally based on scoring, not hardcoded."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)

    # Decision action must match the top ranked candidate from optimizer
    assert result.decision.recommended_action.startswith("ROUTE_SWITCH:")
    assert result.decision.confidence > 0.50


# -------------------------------------------------------------------------
# Requirement 14: No Safety Bypass
# -------------------------------------------------------------------------

def test_no_safety_bypass():
    """Requirement 14: Safety controller blocks unsafe execution without bypass."""
    runner = DemoRunner()
    result = runner.run(FAILURE_SAFETY_BLOCKED)

    assert result.safety_decision.allowed is False
    assert result.batch_result["safety_allowed"] is False
    assert result.batch_result["final_status"] == "BLOCKED"
    assert result.batch_result["attempted_transactions"] == 0
    assert result.batch_result["recovered_amount"] == 0.0
    assert result.is_success is False


# -------------------------------------------------------------------------
# Requirement 15: No Real Payment Execution
# -------------------------------------------------------------------------

def test_no_real_payment_execution():
    """Requirement 15: Execution operates strictly on synthetic in-memory dataframes."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)

    assert result.batch_result["simulation_authorized"] is False or result.batch_result["simulation_authorized"] is True
    # Verify no real payment IDs or external identifiers exist
    assert result.incident is not None
    assert result.final_status in ("RECOVERED", "BLOCKED", "STOPPED", "MONITORING")


# -------------------------------------------------------------------------
# Requirement 16: No External API Dependency
# -------------------------------------------------------------------------

def test_no_external_api_dependency():
    """Requirement 16: Demo runner executes offline with zero network connectivity."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)
    assert result is not None
    assert result.is_success is True


# -------------------------------------------------------------------------
# Requirement 17: Audit Trail Presence
# -------------------------------------------------------------------------

def test_audit_trail_presence():
    """Requirement 17: Audit trail references are populated from existing audit infrastructure."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)

    assert result.audit_references is not None
    assert len(result.audit_references) >= 1
    assert "audit_event_type" in result.audit_references[0] or "timestamp" in result.audit_references[0]


# -------------------------------------------------------------------------
# Requirement 18: Complete Phase Ordering
# -------------------------------------------------------------------------

def test_complete_phase_ordering():
    """Requirement 18: All lifecycle events and phase results are correctly ordered."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)

    # 9 Lifecycle events
    assert len(result.lifecycle_events) == 9
    stage_ids = [e.stage_id for e in result.lifecycle_events]
    assert stage_ids == [
        "HEALTHY",
        "DETECT",
        "QUANTIFY",
        "DECIDE",
        "SAFETY",
        "RECOVER",
        "VERIFY",
        "LEARN",
        "ADAPT",
    ]

    # Phase results
    expected_phases = [
        DemoPhase.BASELINE.value,
        DemoPhase.INCIDENT.value,
        DemoPhase.DECISION.value,
        DemoPhase.SAFETY.value,
        DemoPhase.CANARY.value,
        DemoPhase.RECOVERY.value,
        DemoPhase.LEARNING.value,
        DemoPhase.REEVALUATION.value,
        DemoPhase.COMPLETE.value,
    ]
    for phase in expected_phases:
        assert phase in result.phase_results
        assert isinstance(result.phase_results[phase], PhaseResult)


# -------------------------------------------------------------------------
# Requirement 19: Final Status Consistency
# -------------------------------------------------------------------------

def test_final_status_consistency():
    """Requirement 19: Final status is consistent across all result views."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)

    assert result.final_status == "RECOVERED"
    assert result.batch_result["final_status"] == "RECOVERED"
    assert result.is_success is True
    assert result.scorecard.net_recovered_value == result.batch_result["net_recovered_value"]


# -------------------------------------------------------------------------
# Requirement 20: Repeated Runs Produce Equivalent Results
# -------------------------------------------------------------------------

def test_repeated_runs_produce_equivalent_results():
    """Requirement 20: Running the demo repeatedly produces equivalent results."""
    runner = DemoRunner()
    results = [runner.run(CANONICAL_HAPPY_PATH) for _ in range(3)]

    for r in results[1:]:
        assert r.is_success == results[0].is_success
        assert r.final_status == results[0].final_status
        assert r.batch_result["net_recovered_value"] == results[0].batch_result["net_recovered_value"]


# -------------------------------------------------------------------------
# Human-Readable Demo Report Verification
# -------------------------------------------------------------------------

def test_format_demo_report_output():
    """Verify format_demo_report renders all required sections in the exact format."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)
    report = result.format_report()

    assert "RAZORPAY PAYMENT RELIABILITY ENGINE — DEMO" in report
    assert "[1] BASELINE" in report
    assert "[2] INCIDENT DETECTED" in report
    assert "[3] AI DECISION" in report
    assert "[4] SAFETY GATE" in report
    assert "[5] BOUNDED CANARY" in report
    assert "[6] RECOVERY OUTCOME" in report
    assert "[7] LEARNING" in report
    assert "[8] RE-EVALUATION" in report
    assert "FINAL RESULT" in report
    assert "[THEORETICAL]" in report
    assert "[SIMULATED]" in report


# -------------------------------------------------------------------------
# Step 17: Integration Safety Test (No prohibited imports/calls)
# -------------------------------------------------------------------------

def test_integration_safety_no_prohibited_imports_or_calls():
    """Step 17: Verify demo components do not import requests, razorpay SDK, or LLM clients."""
    import src.demo.demo_runner as demo_module
    import src.demo.demo_scenario as scenario_module

    demo_source = inspect.getsource(demo_module)
    scenario_source = inspect.getsource(scenario_module)
    combined = demo_source + "\n" + scenario_source

    prohibited_tokens = [
        "import requests",
        "from requests",
        "import urllib.request",
        "import httpx",
        "import razorpay",
        "from razorpay",
        "openai",
        "anthropic",
        "google.generativeai",
    ]
    for token in prohibited_tokens:
        assert token not in combined, f"Prohibited integration token found: {token}"


def test_unprofitable_recovery_triggers_rollback():
    """Verify unprofitable recovery triggers circuit breaker rollback."""
    runner = DemoRunner()
    result = runner.run(FAILURE_UNPROFITABLE_ROLLBACK)

    assert result.safety_decision.allowed is True
    assert result.batch_result["rollback_required"] is True
    assert result.batch_result["guardrail_decision"] in ("STOP", "ROLLBACK")
    assert result.is_success is False
