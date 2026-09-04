"""
Unit tests for src/demo/demo_ui.py — pure view-model helper functions.

Tests 17 requirements:
1.  build_demo_view_model returns empty dict when result is None.
2.  build_demo_view_model populates incident fields from DemoRunResult.
3.  build_demo_view_model populates decision fields from DemoRunResult.
4.  build_demo_view_model populates safety fields from DemoRunResult.
5.  build_demo_view_model populates canary fields from DemoRunResult.
6.  build_demo_view_model populates financial/recovery fields from DemoRunResult.
7.  build_demo_view_model populates learning fields from DemoRunResult.
8.  build_demo_view_model populates re-evaluation fields from DemoRunResult.
9.  get_financial_display returns correctly formatted INR strings.
10. get_financial_display uses SIMULATED provenance for all execution values.
11. get_learning_display returns formatted learning summary.
12. get_reevaluation_display returns before/after comparison.
13. get_phase_status returns PENDING when result is None.
14. get_phase_status returns phase status from phase_results.
15. get_phase_icon returns correct icons for each status.
16. get_phase_css_class returns correct CSS class for each status.
17. get_final_status_bar returns correct ordered list of (label, status, display).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pytest

from src.demo.demo_ui import (
    build_demo_view_model,
    get_phase_status,
    get_phase_icon,
    get_phase_css_class,
    get_financial_display,
    get_learning_display,
    get_reevaluation_display,
    get_closed_loop_learning_flow,
    get_final_status_bar,
    PROVENANCE_OBSERVED,
    PROVENANCE_THEORETICAL,
    PROVENANCE_SIMULATED,
    PROVENANCE_GOVERNED,
    PROVENANCE_LEARNED,
)


# ---------------------------------------------------------------------------
# Minimal stubs — only the attributes consumed by demo_ui.py
# ---------------------------------------------------------------------------

@dataclass
class _FakeScenario:
    name: str = "Canonical Happy Path"
    description: str = "Test scenario"
    payment_method: str = "UPI"
    bank: str = "Bank_X"
    device_type: str = "Android"
    baseline_success_rate: float = 0.95
    route_candidates: list = field(default_factory=list)

    @property
    def route(self) -> str:
        return f"{self.payment_method} + {self.bank} + {self.device_type}"


@dataclass
class _FakeIncident:
    severity: str = "CRITICAL"
    current_success_rate: float = 0.70
    baseline_success_rate: float = 0.95
    degradation_pp: float = 25.0
    transactions_observed: int = 100
    incident_detected: bool = True


@dataclass
class _FakeRevenue:
    revenue_at_risk: float = 50000.0


@dataclass
class _FakeDecision:
    recommended_action: str = "ROUTE_SWITCH:UPI + Bank_A + Android"
    confidence: float = 0.91
    expected_loss_before: float = 25000.0
    expected_loss_after: float = 5000.0


@dataclass
class _FakeSafety:
    allowed: bool = True
    requires_human_review: bool = False
    action: str = "ROUTE_SWITCH:UPI + Bank_A + Android"
    reason: str = "All safety checks passed."


@dataclass
class _FakeLearning:
    route: str = "UPI + Bank_A + Android"
    attempts: int = 20
    recoveries: int = 19
    evidence_confidence: float = 0.85


@dataclass
class _FakePhaseResult:
    status: str = "SUCCESS"


@dataclass
class _FakeDemoResult:
    scenario: _FakeScenario = field(default_factory=_FakeScenario)
    incident: Optional[_FakeIncident] = field(default_factory=_FakeIncident)
    revenue_impact: Optional[_FakeRevenue] = field(default_factory=_FakeRevenue)
    decision: Optional[_FakeDecision] = field(default_factory=_FakeDecision)
    safety_decision: Optional[_FakeSafety] = field(default_factory=_FakeSafety)
    batch_result: Optional[Dict[str, Any]] = None
    financial_summary: Optional[Dict[str, Any]] = None
    learning_evidence: Optional[_FakeLearning] = None
    reevaluation_result: Optional[Dict[str, Any]] = None
    route_score_before: float = 0.7200
    route_score_after: float = 0.7895
    score_delta: float = 0.0695
    top_route_before: str = "UPI + Bank_B + Android"
    top_route_after: str = "UPI + Bank_A + Android"
    ranking_changed: bool = True
    is_success: bool = True
    final_status: str = "RECOVERED"
    summary_message: str = "Recovery successful."
    execution_timestamp: str = "2026-01-01T00:00:00Z"
    lifecycle_events: list = field(default_factory=list)
    phase_results: Dict[str, Any] = field(default_factory=dict)
    decision_changed_after_learning: bool = False
    audit_references: list = field(default_factory=list)


def _make_batch(**kwargs):
    defaults = {
        "eligible_transactions": 100,
        "attempted_transactions": 20,
        "successful_recoveries": 19,
        "failed_recoveries": 1,
        "canary_decision": "EXPAND",
        "guardrail_decision": "CONTINUE",
        "rollback_required": False,
        "attempted_amount": 10000.0,
        "recovered_amount": 9500.0,
        "execution_cost": 500.0,
        "net_recovered_value": 9000.0,
        "recovery_rate": 0.95,
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Test 1: build_demo_view_model — None returns empty dict
# ---------------------------------------------------------------------------
def test_1_returns_empty_dict_when_result_is_none():
    result = build_demo_view_model(None)
    assert result == {}


# ---------------------------------------------------------------------------
# Test 2: build_demo_view_model — incident fields
# ---------------------------------------------------------------------------
def test_2_populates_incident_fields():
    r = _FakeDemoResult()
    vm = build_demo_view_model(r)
    assert vm["severity"] == "CRITICAL"
    assert vm["observed_success_rate"] == pytest.approx(0.70)
    assert vm["baseline_success_rate"] == pytest.approx(0.95)
    assert vm["degradation_pp"] == pytest.approx(25.0)
    assert vm["transactions_observed"] == 100
    assert vm["incident_detected"] is True
    assert vm["revenue_at_risk"] == pytest.approx(50000.0)
    assert vm["revenue_at_risk_provenance"] == PROVENANCE_THEORETICAL


# ---------------------------------------------------------------------------
# Test 3: build_demo_view_model — decision fields
# ---------------------------------------------------------------------------
def test_3_populates_decision_fields():
    r = _FakeDemoResult()
    vm = build_demo_view_model(r)
    assert vm["selected_action"] == "ROUTE_SWITCH:UPI + Bank_A + Android"
    assert vm["confidence"] == pytest.approx(0.91)
    assert vm["expected_loss_before"] == pytest.approx(25000.0)
    assert vm["expected_loss_after"] == pytest.approx(5000.0)
    # 20000/25000 * 100 = 80.0
    assert vm["loss_reduction_pct"] == pytest.approx(80.0)
    assert vm["decision_provenance"] == PROVENANCE_GOVERNED


# ---------------------------------------------------------------------------
# Test 4: build_demo_view_model — safety fields
# ---------------------------------------------------------------------------
def test_4_populates_safety_fields():
    r = _FakeDemoResult()
    vm = build_demo_view_model(r)
    assert vm["safety_allowed"] is True
    assert vm["safety_human_review"] is False
    assert vm["safety_reason"] == "All safety checks passed."
    assert vm["safety_provenance"] == PROVENANCE_GOVERNED


def test_4b_safety_blocked():
    r = _FakeDemoResult(safety_decision=_FakeSafety(allowed=False, requires_human_review=False, reason="Confidence too low."))
    vm = build_demo_view_model(r)
    assert vm["safety_allowed"] is False
    assert vm["safety_provenance"] == PROVENANCE_GOVERNED


# ---------------------------------------------------------------------------
# Test 5: build_demo_view_model — canary fields
# ---------------------------------------------------------------------------
def test_5_populates_canary_fields():
    r = _FakeDemoResult(batch_result=_make_batch())
    vm = build_demo_view_model(r)
    assert vm["eligible_transactions"] == 100
    assert vm["attempted_transactions"] == 20
    assert vm["successful_recoveries"] == 19
    assert vm["failed_recoveries"] == 1
    assert vm["canary_decision"] == "EXPAND"
    assert vm["guardrail_decision"] == "CONTINUE"
    assert vm["rollback_required"] is False
    assert vm["canary_provenance"] == PROVENANCE_SIMULATED


# ---------------------------------------------------------------------------
# Test 6: build_demo_view_model — financial/recovery fields
# ---------------------------------------------------------------------------
def test_6_populates_financial_fields():
    r = _FakeDemoResult(batch_result=_make_batch())
    vm = build_demo_view_model(r)
    assert vm["attempted_amount"] == pytest.approx(10000.0)
    assert vm["gross_recovered"] == pytest.approx(9500.0)
    assert vm["execution_cost"] == pytest.approx(500.0)
    assert vm["net_recovered_value"] == pytest.approx(9000.0)
    assert vm["recovery_rate"] == pytest.approx(0.95)
    assert vm["recovery_executed"] is True
    assert vm["financial_provenance"] == PROVENANCE_SIMULATED


def test_6b_no_batch_result_recovery_not_executed():
    r = _FakeDemoResult(batch_result=None)
    vm = build_demo_view_model(r)
    assert vm["recovery_executed"] is False
    assert vm["attempted_transactions"] == 0


# ---------------------------------------------------------------------------
# Test 7: build_demo_view_model — learning fields
# ---------------------------------------------------------------------------
def test_7_populates_learning_fields():
    r = _FakeDemoResult(
        learning_evidence=_FakeLearning(),
        route_score_before=0.7200,
        route_score_after=0.7895,
        score_delta=0.0695,
    )
    vm = build_demo_view_model(r)
    assert vm["route_name_learned"] == "UPI + Bank_A + Android"
    assert vm["learned_attempts"] == 20
    assert vm["learned_recoveries"] == 19
    assert vm["evidence_confidence"] == pytest.approx(0.85)
    assert vm["route_score_before"] == pytest.approx(0.7200)
    assert vm["route_score_after"] == pytest.approx(0.7895)
    assert vm["score_delta"] == pytest.approx(0.0695)
    assert vm["has_learning_evidence"] is True
    assert vm["learning_provenance"] == PROVENANCE_LEARNED


def test_7b_no_learning_evidence():
    r = _FakeDemoResult(learning_evidence=None)
    vm = build_demo_view_model(r)
    assert vm["has_learning_evidence"] is False
    assert vm["learned_attempts"] == 0
    assert vm["learned_recoveries"] == 0


# ---------------------------------------------------------------------------
# Test 8: build_demo_view_model — re-evaluation fields
# ---------------------------------------------------------------------------
def test_8_populates_reevaluation_fields():
    r = _FakeDemoResult(
        reevaluation_result={
            "before_learning": {"top_route": "UPI + Bank_B + Android", "route_score": 0.72},
            "after_learning": {"top_route": "UPI + Bank_A + Android", "route_score": 0.7895},
        },
        decision_changed_after_learning=True,
    )
    vm = build_demo_view_model(r)
    assert vm["top_route_before_learning"] == "UPI + Bank_B + Android"
    assert vm["score_before_learning"] == pytest.approx(0.72)
    assert vm["top_route_after_learning"] == "UPI + Bank_A + Android"
    assert vm["score_after_learning"] == pytest.approx(0.7895)
    assert vm["decision_changed_after_learning"] is True
    assert vm["reevaluation_provenance"] == PROVENANCE_GOVERNED


# ---------------------------------------------------------------------------
# Test 9: get_financial_display — formatted INR strings
# ---------------------------------------------------------------------------
def test_9_financial_display_formats_inr():
    r = _FakeDemoResult(batch_result=_make_batch())
    fd = get_financial_display(r)
    assert "₹10,000.00" in fd["attempted_amount"]
    assert "₹9,500.00" in fd["gross_recovered"]
    assert "₹500.00" in fd["execution_cost"]
    assert "₹9,000.00" in fd["net_recovered_value"]


# ---------------------------------------------------------------------------
# Test 10: get_financial_display — SIMULATED provenance
# ---------------------------------------------------------------------------
def test_10_financial_display_provenance_is_simulated():
    r = _FakeDemoResult(batch_result=_make_batch())
    fd = get_financial_display(r)
    assert fd["provenance"] == PROVENANCE_SIMULATED
    # Net recovered label should contain SIMULATED
    assert PROVENANCE_SIMULATED in fd["net_recovered_label"]
    # Recovery rate label should contain SIMULATED
    assert PROVENANCE_SIMULATED in fd["recovery_rate_pct"]


# ---------------------------------------------------------------------------
# Test 11: get_learning_display — formatted learning summary
# ---------------------------------------------------------------------------
def test_11_learning_display_formats_correctly():
    r = _FakeDemoResult(
        learning_evidence=_FakeLearning(attempts=20, recoveries=19, evidence_confidence=0.85),
        route_score_before=0.7200,
        route_score_after=0.7895,
        score_delta=0.0695,
    )
    ld = get_learning_display(r)
    assert ld["route"] == "UPI + Bank_A + Android"
    assert ld["evidence"] == "19/20 recovered"
    assert ld["evidence_confidence"] == "85.0%"
    assert ld["score_before"] == "0.7200"
    assert ld["score_after"] == "0.7895"
    assert "+0.0695" in ld["score_delta"]
    assert ld["has_evidence"] is True
    assert ld["provenance"] == PROVENANCE_LEARNED


# ---------------------------------------------------------------------------
# Test 12: get_reevaluation_display — before/after comparison
# ---------------------------------------------------------------------------
def test_12_reevaluation_display_comparison():
    r = _FakeDemoResult(
        reevaluation_result={
            "before_learning": {"top_route": "UPI + Bank_B + Android", "route_score": 0.72},
            "after_learning": {"top_route": "UPI + Bank_A + Android", "route_score": 0.7895},
        },
        decision_changed_after_learning=True,
    )
    rd = get_reevaluation_display(r)
    assert rd["top_route_before"] == "UPI + Bank_B + Android"
    assert rd["score_before"] == "0.7200"
    assert rd["top_route_after"] == "UPI + Bank_A + Android"
    assert rd["score_after"] == "0.7895"
    assert rd["decision_changed"] is True
    assert "YES" in rd["decision_changed_label"]
    assert rd["provenance"] == PROVENANCE_GOVERNED


def test_12b_reevaluation_no_change():
    r = _FakeDemoResult(decision_changed_after_learning=False)
    rd = get_reevaluation_display(r)
    assert rd["decision_changed"] is False
    assert "NO" in rd["decision_changed_label"]


# ---------------------------------------------------------------------------
# Test 13: get_phase_status — returns PENDING when result is None
# ---------------------------------------------------------------------------
def test_13_phase_status_none_result():
    status = get_phase_status(None, "CANARY")
    assert status == "PENDING"


# ---------------------------------------------------------------------------
# Test 14: get_phase_status — reads from phase_results
# ---------------------------------------------------------------------------
def test_14_phase_status_from_phase_results():
    phase_obj = _FakePhaseResult(status="BLOCKED")
    r = _FakeDemoResult(phase_results={"CANARY": phase_obj})
    assert get_phase_status(r, "CANARY") == "BLOCKED"


def test_14b_phase_status_missing_returns_pending():
    r = _FakeDemoResult(phase_results={})
    assert get_phase_status(r, "RECOVERY") == "PENDING"


# ---------------------------------------------------------------------------
# Test 15: get_phase_icon — icons for all statuses
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("status,expected", [
    ("SUCCESS", "✓"),
    ("BLOCKED", "🚫"),
    ("STOPPED", "🛑"),
    ("ROLLED_BACK", "↩️"),
    ("SKIPPED", "—"),
    ("NORMAL", "✓"),
    ("PENDING", "○"),
])
def test_15_phase_icon_mapping(status, expected):
    assert get_phase_icon(status) == expected


# ---------------------------------------------------------------------------
# Test 16: get_phase_css_class — CSS class per status
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("status,expected_class", [
    ("SUCCESS", "step-success"),
    ("BLOCKED", "step-blocked"),
    ("STOPPED", "step-blocked"),
    ("ROLLED_BACK", "step-warn"),
    ("SKIPPED", "step-pending"),
    ("NORMAL", "step-success"),
    ("PENDING", "step-pending"),
])
def test_16_phase_css_class_mapping(status, expected_class):
    assert get_phase_css_class(status) == expected_class


# ---------------------------------------------------------------------------
# Test 17: get_final_status_bar — ordered list of tuples
# ---------------------------------------------------------------------------
def test_17_final_status_bar_structure():
    r = _FakeDemoResult(
        batch_result=_make_batch(),
        learning_evidence=_FakeLearning(),
        reevaluation_result={"before_learning": {}, "after_learning": {}},
    )
    bar = get_final_status_bar(r)
    # Must have 7 items: INCIDENT, DECISION, SAFETY, CANARY, RECOVERY, LEARNING, RE-EVALUATION
    assert len(bar) == 7
    stage_labels = [item[0] for item in bar]
    assert "INCIDENT" in stage_labels
    assert "DECISION" in stage_labels
    assert "SAFETY" in stage_labels
    assert "CANARY" in stage_labels
    assert "RECOVERY" in stage_labels
    assert "LEARNING" in stage_labels
    assert "RE-EVALUATION" in stage_labels
    # All items are 3-tuples (label, status, display)
    for item in bar:
        assert len(item) == 3


def test_17b_status_bar_safety_blocked():
    blocked_safety = _FakeSafety(allowed=False, requires_human_review=False, reason="Blocked.")
    r = _FakeDemoResult(
        safety_decision=blocked_safety,
        batch_result=None,
        final_status="BLOCKED",
    )
    bar = get_final_status_bar(r)
    safety_item = next(item for item in bar if item[0] == "SAFETY")
    assert safety_item[1] == "BLOCKED"


# ===========================================================================
# MILESTONE 7: CLOSED-LOOP LEARNING VISUALIZATION TESTS
# ===========================================================================


def test_18_closed_loop_learning_values_from_actual_result():
    """Requirement 1: Learning values come directly from actual result without fabrication."""
    learning_stats = _FakeLearning(
        route="UPI + Bank_A + Android",
        attempts=25,
        recoveries=24,
        evidence_confidence=0.825,
    )
    r = _FakeDemoResult(
        batch_result=_make_batch(learning_stats=learning_stats),
        learning_evidence=learning_stats,
        route_score_before=0.6800,
        route_score_after=0.8950,
        score_delta=0.2150,
    )
    flow = get_closed_loop_learning_flow(r)

    assert flow["has_learning_evidence"] is True
    assert flow["route_before"] == "UPI + Bank_A + Android"
    assert flow["route_after"] == "UPI + Bank_A + Android"
    assert flow["attempts"] == 25
    assert flow["recoveries"] == 24
    assert flow["recovery_rate_pct"] == "96.0%"
    assert flow["evidence_confidence"] == "82.5%"
    assert flow["provenance"] == PROVENANCE_LEARNED


def test_19_closed_loop_learning_score_before_displayed():
    """Requirement 2: Score before is formatted to 4 decimal places and matches raw score."""
    r = _FakeDemoResult(
        route_score_before=0.671751,
        learning_evidence=_FakeLearning(),
    )
    flow = get_closed_loop_learning_flow(r)
    assert flow["score_before"] == "0.6718"
    assert flow["score_before_raw"] == pytest.approx(0.671751, abs=1e-5)


def test_20_closed_loop_learning_score_after_displayed():
    """Requirement 3: Score after is formatted to 4 decimal places and matches raw score."""
    r = _FakeDemoResult(
        route_score_after=0.888678,
        learning_evidence=_FakeLearning(),
    )
    flow = get_closed_loop_learning_flow(r)
    assert flow["score_after"] == "0.8887"
    assert flow["score_after_raw"] == pytest.approx(0.888678, abs=1e-5)


def test_21_closed_loop_learning_score_delta_displayed():
    """Requirement 4: Score delta is formatted with explicit sign (+/-)."""
    r = _FakeDemoResult(
        score_delta=0.2169,
        learning_evidence=_FakeLearning(),
    )
    flow = get_closed_loop_learning_flow(r)
    assert flow["score_delta"] == "+0.2169"
    assert flow["score_delta_raw"] == pytest.approx(0.2169, abs=1e-5)


def test_22_closed_loop_learning_evidence_confidence_displayed():
    """Requirement 5: Evidence confidence is formatted as percentage."""
    stats = _FakeLearning(evidence_confidence=0.734)
    r = _FakeDemoResult(
        batch_result=_make_batch(learning_stats=stats),
        learning_evidence=stats,
    )
    flow = get_closed_loop_learning_flow(r)
    assert flow["evidence_confidence"] == "73.4%"
    assert flow["evidence_confidence_raw"] == pytest.approx(0.734, abs=1e-3)


def test_23_closed_loop_learning_reevaluation_displayed():
    """Requirement 6: Re-evaluation top routes and decision changed flag are accurately formatted."""
    r = _FakeDemoResult(
        top_route_before="UPI + Bank_B + iOS",
        top_route_after="UPI + Bank_A + Android",
        ranking_changed=True,
        decision_changed_after_learning=True,
        learning_evidence=_FakeLearning(),
    )
    flow = get_closed_loop_learning_flow(r)
    assert flow["top_route_before"] == "UPI + Bank_B + iOS"
    assert flow["top_route_after"] == "UPI + Bank_A + Android"
    assert flow["decision_changed"] is True
    assert "YES" in flow["decision_changed_label"]


def test_24_closed_loop_learning_no_hardcoded_values():
    """Requirement 7: Output changes dynamically when input attributes change."""
    stats1 = _FakeLearning(route="Route_Alpha", attempts=10, recoveries=8, evidence_confidence=0.50)
    r1 = _FakeDemoResult(
        batch_result=_make_batch(learning_stats=stats1),
        learning_evidence=stats1,
        route_score_before=0.50,
        route_score_after=0.75,
        score_delta=0.25,
    )
    flow1 = get_closed_loop_learning_flow(r1)

    stats2 = _FakeLearning(route="Route_Beta", attempts=50, recoveries=49, evidence_confidence=0.95)
    r2 = _FakeDemoResult(
        batch_result=_make_batch(learning_stats=stats2),
        learning_evidence=stats2,
        route_score_before=0.40,
        route_score_after=0.90,
        score_delta=0.50,
    )
    flow2 = get_closed_loop_learning_flow(r2)

    assert flow1["route_before"] == "Route_Alpha"
    assert flow2["route_before"] == "Route_Beta"
    assert flow1["attempts"] == 10
    assert flow2["attempts"] == 50
    assert flow1["score_delta"] == "+0.2500"
    assert flow2["score_delta"] == "+0.5000"


def test_25_closed_loop_learning_deterministic_output():
    """Requirement 8: Multiple calls on identical input produce identical output."""
    stats = _FakeLearning(attempts=30, recoveries=28, evidence_confidence=0.88)
    r = _FakeDemoResult(
        batch_result=_make_batch(learning_stats=stats),
        learning_evidence=stats,
        route_score_before=0.60,
        route_score_after=0.85,
        score_delta=0.25,
    )
    flow_a = get_closed_loop_learning_flow(r)
    flow_b = get_closed_loop_learning_flow(r)
    assert flow_a == flow_b


def test_26_closed_loop_learning_empty_state_handled_safely():
    """Requirement 9: None result and empty learning states are handled safely without errors."""
    flow_none = get_closed_loop_learning_flow(None)
    assert flow_none["has_learning_evidence"] is False
    assert flow_none["route_before"] == "N/A"
    assert flow_none["score_before"] == "0.0000"
    assert flow_none["attempts"] == 0

    r_empty = _FakeDemoResult(
        batch_result=None,
        learning_evidence=None,
        route_score_before=0.0,
        route_score_after=0.0,
        score_delta=0.0,
    )
    flow_empty = get_closed_loop_learning_flow(r_empty)
    assert flow_empty["has_learning_evidence"] is False
    assert flow_empty["attempts"] == 0
    assert flow_empty["recoveries"] == 0
    assert flow_empty["decision_changed"] is False


def test_27_safety_blocked_scenario_consistency_and_none_safe_roi():
    """Verify safety-blocked scenario produces None-safe ROI and consistent data."""
    from src.demo.demo_scenario import FAILURE_SAFETY_BLOCKED
    from src.demo.demo_runner import DemoRunner

    runner = DemoRunner()
    res = runner.run(FAILURE_SAFETY_BLOCKED)

    # 1. View model populated consistently from DemoRunResult
    vm = build_demo_view_model(res)
    assert vm["severity"] == "CRITICAL"
    assert vm["revenue_at_risk"] == pytest.approx(1250000.0)
    assert vm["degradation_pp"] == pytest.approx(25.0)
    assert vm["safety_allowed"] is False
    assert vm["safety_reason"] == "Financial exposure exceeds the critical automated-action threshold."
    assert vm["recovery_executed"] is False
    assert vm["selected_action"] == "ROUTE_SWITCH:UPI + Bank_A + Android"
    assert vm["recovery_roi"] is None

    # 2. Financial display is completely None-safe
    fd = get_financial_display(res)
    assert "₹1,250,000.00" in fd["revenue_at_risk"]
    assert fd["recovery_roi_str"] == "N/A — no execution cost recorded"
    assert fd["final_status"] == "BLOCKED"
    assert "₹0.00" in fd["execution_cost"]
    assert "₹0.00" in fd["gross_recovered"]


def test_28_canonical_happy_path_financial_display():
    """Verify canonical happy path produces valid ROI and simulated financials."""
    from src.demo.demo_scenario import CANONICAL_HAPPY_PATH
    from src.demo.demo_runner import DemoRunner

    runner = DemoRunner()
    res = runner.run(CANONICAL_HAPPY_PATH)

    vm = build_demo_view_model(res)
    assert vm["severity"] == "CRITICAL"
    assert vm["safety_allowed"] is True
    assert vm["recovery_executed"] is True
    assert vm["recovery_roi"] is not None
    assert vm["recovery_roi"] > 0

    fd = get_financial_display(res)
    assert "x" in fd["recovery_roi_str"]
    assert PROVENANCE_SIMULATED in fd["recovery_roi_str"]
    assert "₹" in fd["net_recovered_value"]


def test_29_unprofitable_rollback_scenario_consistency():
    """Verify unprofitable canary scenario triggers circuit breaker and rollback state."""
    from src.demo.demo_scenario import FAILURE_UNPROFITABLE_ROLLBACK
    from src.demo.demo_runner import DemoRunner

    runner = DemoRunner()
    res = runner.run(FAILURE_UNPROFITABLE_ROLLBACK)

    vm = build_demo_view_model(res)
    assert vm["rollback_required"] is True
    assert vm["guardrail_decision"] == "ROLLBACK"
    assert vm["canary_decision"] in ("STOP", "ESCALATE")

    fd = get_financial_display(res)
    assert fd["final_status"] in ("NO_RECOVERY", "ROLLED_BACK")

    status_bar = get_final_status_bar(res)
    rec_step = [s for s in status_bar if s[0] == "RECOVERY"][0]
    assert rec_step[1] == "ROLLED_BACK"


def test_30_demo_runner_accepts_string_scenario_id():
    """Verify DemoRunner.run accepts string scenario IDs seamlessly."""
    from src.demo.demo_runner import DemoRunner

    runner = DemoRunner()
    res = runner.run("safety_blocked")
    assert res.scenario.scenario_id == "safety_blocked"
    assert res.final_status == "BLOCKED"



