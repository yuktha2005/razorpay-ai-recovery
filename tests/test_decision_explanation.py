from dataclasses import asdict
from typing import Any, Dict

import pytest

from src.decision.decision_explanation import (
    DecisionExplanation,
    build_decision_explanation,
)
from src.models.domain import (
    Decision,
    Intervention,
    LossEstimate,
    RiskAssessment,
    SafetyDecision,
)


def test_complete_explanation_with_all_inputs():
    """Verify full explanation generation when all domain objects are provided."""
    decision = Decision(
        payment_id="pay_test_001",
        recommended_action="ROUTE_SWITCH:UPI+HDFC+Android",
        confidence=0.88,
        expected_loss_before=5000.0,
        expected_loss_after=750.0,
        estimated_value=4250.0,
        alternatives=[
            Intervention(
                action="RETRY_AFTER_DELAY",
                estimated_cost=15.0,
                expected_loss_after=2000.0,
                expected_benefit=3000.0,
                customer_friction=0.1,
                explanation="Wait 60s and re-attempt",
            ),
        ],
        explanation="Switch to higher-performing UPI route to recover degrading volume.",
    )

    risk_assessment = RiskAssessment(
        payment_id="pay_test_001",
        risk_score=0.82,
        risk_level="HIGH",
        probability_of_loss=0.78,
        risk_type="GATEWAY_DOWNTIME",
        reasons=["elevated_failure_rate", "latency_spike_over_4000ms"],
        model_version="v2.1",
    )

    loss_estimate = LossEstimate(
        payment_id="pay_test_001",
        financial_exposure=10000.0,
        probability_of_loss=0.78,
        expected_loss=5000.0,
        currency="INR",
    )

    safety_decision = SafetyDecision(
        payment_id="pay_test_001",
        action="ROUTE_SWITCH:UPI+HDFC+Android",
        allowed=True,
        reason="Action is within automated bounds and budget threshold.",
        requires_human_review=False,
    )

    route_context: Dict[str, Any] = {
        "route": "UPI+HDFC+Android",
        "observed_success_rate": 0.952,
        "adjusted_success_rate": 0.820,
        "evidence_confidence": 0.91,
        "score": 9.45,
        "explanation": "Consistent high availability on Android rail",
    }

    explanation = build_decision_explanation(
        decision=decision,
        risk_assessment=risk_assessment,
        loss_estimate=loss_estimate,
        safety_decision=safety_decision,
        route_context=route_context,
    )

    assert isinstance(explanation, DecisionExplanation)
    assert explanation.payment_id == "pay_test_001"
    assert explanation.selected_action == "ROUTE_SWITCH:UPI+HDFC+Android"
    assert "Switch to higher-performing UPI route" in explanation.selected_action_reason
    assert "88.0% confidence" in explanation.confidence_summary

    # Risk Summary checks
    assert "HIGH" in explanation.risk_summary
    assert "0.82" in explanation.risk_summary
    assert "78.0%" in explanation.risk_summary
    assert "GATEWAY_DOWNTIME" in explanation.risk_summary
    assert "elevated_failure_rate" in explanation.risk_summary

    # Financial Summary checks (₹ formatted)
    assert "₹5,000.00" in explanation.financial_summary
    assert "₹750.00" in explanation.financial_summary
    assert "₹4,250.00" in explanation.financial_summary
    assert "₹10,000.00" in explanation.financial_summary

    # Route incident summary checks
    assert "Route: UPI+HDFC+Android" in explanation.incident_summary
    assert "Observed Success Rate: 95.2%" in explanation.incident_summary
    assert "Adjusted Success Rate: 82.0%" in explanation.incident_summary
    assert "Evidence Confidence: 91.0%" in explanation.incident_summary
    assert "Score: 9.45" in explanation.incident_summary
    assert "Consistent high availability" in explanation.incident_summary

    # Safety checks
    assert "Status: Allowed" in explanation.safety_summary
    assert "Automated execution eligible" in explanation.safety_summary
    assert "within automated bounds" in explanation.safety_summary

    # Alternative actions check
    assert len(explanation.alternative_actions) == 1
    assert "RETRY_AFTER_DELAY" in explanation.alternative_actions[0]
    assert "Estimated Benefit: ₹3,000.00" in explanation.alternative_actions[0]
    assert "Expected Loss After: ₹2,000.00" in explanation.alternative_actions[0]
    assert "Cost: ₹15.00" in explanation.alternative_actions[0]

    # Key factors check
    assert any("HIGH" in kf for kf in explanation.key_factors)
    assert any("₹5,000.00" in kf for kf in explanation.key_factors)
    assert any("₹4,250.00" in kf for kf in explanation.key_factors)
    assert any("confidence" in kf.lower() for kf in explanation.key_factors)
    assert any("Safety policy passed" in kf for kf in explanation.key_factors)


def test_missing_optional_inputs():
    """Verify safe degradation when all optional parameters are omitted."""
    decision = Decision(
        payment_id="pay_test_002",
        recommended_action="MONITOR",
        confidence=0.65,
        expected_loss_before=1200.50,
        expected_loss_after=1200.50,
        estimated_value=0.0,
        alternatives=[],
        explanation="Insufficient evidence to intervene, continuing observation.",
    )

    explanation = build_decision_explanation(decision=decision)

    assert explanation.payment_id == "pay_test_002"
    assert explanation.selected_action == "MONITOR"
    assert explanation.incident_summary == "No additional route evidence available."
    assert explanation.risk_summary == "Risk assessment: Not available."
    assert explanation.safety_summary == "Safety evaluation: Not available."
    assert explanation.alternative_actions == []

    # Financial summary should still display available values correctly
    assert "Expected Loss Before: ₹1,200.50" in explanation.financial_summary
    assert "Expected Loss After: ₹1,200.50" in explanation.financial_summary
    assert "Estimated Value: ₹0.00" in explanation.financial_summary
    # Exposure is omitted rather than fabricated
    assert "Financial Exposure" not in explanation.financial_summary


def test_alternative_intervention_formatting():
    """Verify formatting of various types of alternatives (Intervention, dict, str)."""
    decision = Decision(
        payment_id="pay_test_003",
        recommended_action="PRIMARY_ACTION",
        confidence=0.75,
        expected_loss_before=2000.0,
        expected_loss_after=500.0,
        estimated_value=1500.0,
        alternatives=[
            Intervention(
                action="STEP_UP_VERIFICATION",
                estimated_cost=30.0,
                expected_loss_after=700.0,
                expected_benefit=1300.0,
                customer_friction=0.2,
                explanation="2FA prompt",
            ),
            {
                "action": "DYNAMIC_RETRY",
                "estimated_cost": 5.0,
                "expected_loss_after": 900.0,
                "expected_benefit": 1100.0,
            },
            "MANUAL_REVIEW",
        ],
        explanation="Select best net value action.",
    )

    explanation = build_decision_explanation(decision=decision)

    assert len(explanation.alternative_actions) == 3
    # First: Intervention object
    assert "STEP_UP_VERIFICATION" in explanation.alternative_actions[0]
    assert "Estimated Benefit: ₹1,300.00" in explanation.alternative_actions[0]
    assert "Expected Loss After: ₹700.00" in explanation.alternative_actions[0]
    assert "Cost: ₹30.00" in explanation.alternative_actions[0]

    # Second: Dict alternative
    assert "DYNAMIC_RETRY" in explanation.alternative_actions[1]
    assert "Estimated Benefit: ₹1,100.00" in explanation.alternative_actions[1]
    assert "Expected Loss After: ₹900.00" in explanation.alternative_actions[1]
    assert "Cost: ₹5.00" in explanation.alternative_actions[1]

    # Third: String alternative
    assert explanation.alternative_actions[2] == "MANUAL_REVIEW"


def test_safety_blocked_explanation():
    """Verify that a blocked safety decision communicates the gate block and reason."""
    decision = Decision(
        payment_id="pay_test_004",
        recommended_action="AGGRESSIVE_ROUTING",
        confidence=0.90,
        expected_loss_before=8000.0,
        expected_loss_after=1000.0,
        estimated_value=7000.0,
        alternatives=[],
        explanation="Attempt aggressive failover.",
    )

    safety_decision = SafetyDecision(
        payment_id="pay_test_004",
        action="AGGRESSIVE_ROUTING",
        allowed=False,
        reason="EXPOSURE_CAP_EXCEEDED: High financial risk above ₹5,000 threshold",
        requires_human_review=True,
    )

    explanation = build_decision_explanation(
        decision=decision,
        safety_decision=safety_decision,
    )

    assert "Status: Blocked" in explanation.safety_summary
    assert "Human review required" in explanation.safety_summary
    assert "EXPOSURE_CAP_EXCEEDED" in explanation.safety_summary

    # Key factors must reflect safety gate block and review requirement
    assert any("Safety gate blocked execution" in kf for kf in explanation.key_factors)
    assert any("EXPOSURE_CAP_EXCEEDED" in kf for kf in explanation.key_factors)
    assert any("Human review required" in kf for kf in explanation.key_factors)
    assert not any("Safety policy passed" in kf for kf in explanation.key_factors)


def test_route_context_formatting():
    """Verify route_context handles full, partial, degraded, and empty cases cleanly."""
    decision = Decision(
        payment_id="pay_test_005",
        recommended_action="ROUTE_SWITCH:UPI_Axis",
        confidence=0.85,
        expected_loss_before=3000.0,
        expected_loss_after=600.0,
        estimated_value=2400.0,
        alternatives=[],
        explanation="Failover to healthy provider",
    )

    # Full route context with degradation (obs < adj)
    degraded_context = {
        "route": "UPI_SBI",
        "observed_success_rate": 0.625,
        "adjusted_success_rate": 0.930,
        "evidence_confidence": 0.85,
        "score": 6.25,
        "explanation": "Timeout rate rising on SBI node",
    }

    explanation_degraded = build_decision_explanation(
        decision=decision,
        route_context=degraded_context,
    )

    assert "Route: UPI_SBI" in explanation_degraded.incident_summary
    assert "Observed Success Rate: 62.5%" in explanation_degraded.incident_summary
    assert "Adjusted Success Rate: 93.0%" in explanation_degraded.incident_summary
    assert "Evidence: Timeout rate rising" in explanation_degraded.incident_summary
    assert any("Route degradation detected" in kf for kf in explanation_degraded.key_factors)

    # Route context with stronger alternative evidence (obs >= adj)
    healthy_context = {
        "route": "UPI_Axis",
        "observed_success_rate": 0.960,
        "adjusted_success_rate": 0.910,
    }
    explanation_healthy = build_decision_explanation(
        decision=decision,
        route_context=healthy_context,
    )
    assert any("Alternative route has stronger evidence" in kf for kf in explanation_healthy.key_factors)

    # Empty route context dict
    explanation_empty = build_decision_explanation(
        decision=decision,
        route_context={},
    )
    assert explanation_empty.incident_summary == "No additional route evidence available."

    # Partial route context dict with only route
    explanation_partial = build_decision_explanation(
        decision=decision,
        route_context={"route": "Card_Network_Visa"},
    )
    assert "Route: Card_Network_Visa" in explanation_partial.incident_summary
    assert "Observed Success Rate" not in explanation_partial.incident_summary


def test_no_fabricated_financial_values():
    """Verify that absent financial numbers are represented as 'Not available' and not fabricated."""
    # Decision with None / non-numeric fields
    empty_decision = Decision(
        payment_id="pay_test_006",
        recommended_action="MONITOR",
        confidence=None,  # type: ignore
        expected_loss_before=None,  # type: ignore
        expected_loss_after=None,  # type: ignore
        estimated_value=None,  # type: ignore
        alternatives=[],
        explanation="",
    )

    explanation = build_decision_explanation(
        decision=empty_decision,
        risk_assessment=None,
        loss_estimate=None,
        safety_decision=None,
        route_context=None,
    )

    assert "Expected Loss Before: Not available" in explanation.financial_summary
    assert "Expected Loss After: Not available" in explanation.financial_summary
    assert "Estimated Value: Not available" in explanation.financial_summary
    assert "Financial Exposure" not in explanation.financial_summary
    assert explanation.confidence_summary == "Confidence: Not available"
    assert explanation.selected_action_reason == "No specific action reason provided."


def test_deterministic_output_for_identical_inputs():
    """Verify that multiple runs with the exact same inputs yield identical results."""
    decision = Decision(
        payment_id="pay_deterministic_001",
        recommended_action="ROUTE_SWITCH:UPI+ICICI",
        confidence=0.81234,
        expected_loss_before=3456.78,
        expected_loss_after=456.78,
        estimated_value=3000.00,
        alternatives=[
            Intervention(
                action="RETRY",
                estimated_cost=10.0,
                expected_loss_after=1200.0,
                expected_benefit=2256.78,
                customer_friction=0.05,
                explanation="Simple retry",
            )
        ],
        explanation="Determinism verification test",
    )

    risk = RiskAssessment(
        payment_id="pay_deterministic_001",
        risk_score=0.74,
        risk_level="HIGH",
        probability_of_loss=0.70,
        risk_type="ROUTE_DEGRADATION",
        reasons=["elevated_error_ratio"],
    )

    loss = LossEstimate(
        payment_id="pay_deterministic_001",
        financial_exposure=8000.0,
        probability_of_loss=0.70,
        expected_loss=3456.78,
    )

    safety = SafetyDecision(
        payment_id="pay_deterministic_001",
        action="ROUTE_SWITCH:UPI+ICICI",
        allowed=True,
        reason="Within boundaries",
        requires_human_review=False,
    )

    route_ctx = {
        "route": "UPI+ICICI",
        "observed_success_rate": 0.94,
        "adjusted_success_rate": 0.88,
        "evidence_confidence": 0.90,
        "score": 8.8,
        "explanation": "Healthy gateway",
    }

    res1 = build_decision_explanation(
        decision=decision,
        risk_assessment=risk,
        loss_estimate=loss,
        safety_decision=safety,
        route_context=route_ctx,
    )

    res2 = build_decision_explanation(
        decision=decision,
        risk_assessment=risk,
        loss_estimate=loss,
        safety_decision=safety,
        route_context=route_ctx,
    )

    assert asdict(res1) == asdict(res2)
    assert res1.payment_id == res2.payment_id
    assert res1.incident_summary == res2.incident_summary
    assert res1.risk_summary == res2.risk_summary
    assert res1.financial_summary == res2.financial_summary
    assert res1.selected_action == res2.selected_action
    assert res1.selected_action_reason == res2.selected_action_reason
    assert res1.confidence_summary == res2.confidence_summary
    assert res1.alternative_actions == res2.alternative_actions
    assert res1.safety_summary == res2.safety_summary
    assert res1.key_factors == res2.key_factors
