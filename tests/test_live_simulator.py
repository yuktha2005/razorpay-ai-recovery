"""
Unit tests for LivePaymentSimulator (Live Payment Event & Routing Simulator).

Verifies:
1. Event generation
2. Webhook ingestion & normalization
3. Route degradation detection
4. All 5 scenario transitions and their expected safety controls
5. Simulation-only route switch
6. Safety decision preservation and demo authorization immutability
7. Canary and Guardrail integration
8. IncidentIntelligence is actually used
9. revenue_at_risk comes from actual transaction amounts / IncidentRevenueCalculator
10. SafetyController remains authoritative
11. Pause prevents event advancement
12. Reset clears pause state
"""

import pytest
import pandas as pd
from src.live_reporting.event_simulator import (
    LivePaymentSimulator,
    SimulatedPaymentEvent,
    RouteTelemetry,
)


@pytest.fixture
def simulator(tmp_path, monkeypatch):
    """Provide a simulator instance isolated from global audit files."""
    monkeypatch.setattr("src.audit_logger.AUDIT_FILE", tmp_path / "recovery_audit.csv")
    monkeypatch.setattr("src.audit_logger.LOG_DIR", tmp_path)
    return LivePaymentSimulator(scenario_name="Bank degradation — RECOVER", seed=123)


def test_event_generation(simulator):
    """1. Test that simulated payment events have all required fields and valid statuses."""
    events = simulator.step(count=5)
    assert len(events) == 5

    for ev in events:
        assert isinstance(ev, SimulatedPaymentEvent)
        assert ev.payment_id.startswith("PAY_")
        assert len(ev.timestamp_str.split(":")) == 3
        assert ev.payment_method in ("UPI", "Card", "Netbanking")
        assert ev.bank in ("Bank_X", "Bank_A", "HDFC", "SBI")
        assert ev.device in ("Android", "Web", "iOS")
        assert ev.amount > 0
        assert ev.status in ("SUCCESS", "FAILED")
        assert ev.risk_indicator in ("HEALTHY", "WATCH", "CRITICAL")
        assert "payload" in ev.webhook_payload
        assert "event_type" in ev.normalized_event


def test_webhook_ingestion_and_normalization(simulator):
    """2. Test that webhook payload is created and normalized via razorpay_webhook."""
    events = simulator.step(count=1)
    ev = events[0]

    # Verify standard Razorpay webhook structure
    assert "payload" in ev.webhook_payload
    payment_entity = ev.webhook_payload["payload"]["payment"]["entity"]
    assert payment_entity["id"] == ev.payment_id
    assert payment_entity["amount"] == int(ev.amount * 100)

    # Verify normalized revenue event structure
    norm = ev.normalized_event
    assert norm["payment_id"] == ev.payment_id
    assert norm["amount_rupees"] == ev.amount
    assert norm["payment_method"] == ev.payment_method.lower()

    # Ingestion pipeline status
    status = simulator.last_pipeline_status
    assert status["webhook_received"] is True
    assert status["event_normalized"] is True
    assert status["route_stats_updated"] is True


def test_route_degradation_detection(simulator):
    """3. Test that route degradation is correctly detected using incident intelligence."""
    incident = simulator.get_incident_detection()
    assert incident is not None
    assert incident["route"] == "UPI → Bank_X → Android"
    assert incident["degradation_pp"] > 5.0
    assert incident["revenue_at_risk"] > 0
    assert incident["severity"] in ("CRITICAL", "WATCH")


def test_all_five_scenario_transitions(simulator):
    """4. Test all 5 scenario transitions and their expected safety controls."""
    # Scenario 1: RECOVER
    simulator.set_scenario("Bank degradation — RECOVER")
    gate1 = simulator.get_safety_gate()
    assert gate1["action"] == "RECOVER"
    assert gate1["production_safety"] == "SAFE"
    assert gate1["allowed"] is True

    # Scenario 2: STOP
    simulator.set_scenario("Mild degradation — STOP")
    gate2 = simulator.get_safety_gate()
    assert gate2["action"] == "STOP"
    assert gate2["production_safety"] == "STOP"
    assert gate2["allowed"] is False

    # Scenario 3: ESCALATE
    simulator.set_scenario("Low AI confidence — ESCALATE")
    gate3 = simulator.get_safety_gate()
    assert gate3["action"] == "ESCALATE"
    assert gate3["production_safety"] == "HUMAN REVIEW REQUIRED"
    assert gate3["requires_human_review"] is True
    assert gate3["allowed"] is False

    # Scenario 4: ROLLBACK
    simulator.set_scenario("Recovery route degradation — ROLLBACK")
    gate4 = simulator.get_safety_gate()
    assert gate4["production_safety"] == "ROLLBACK"
    assert gate4["allowed"] is False

    # Scenario 5: CONTINUE
    simulator.set_scenario("Healthy system — CONTINUE")
    gate5 = simulator.get_safety_gate()
    assert gate5["action"] == "CONTINUE"
    assert gate5["production_safety"] == "CONTINUE"
    assert gate5["allowed"] is True


def test_simulation_only_route_switch(simulator):
    """5. Test AI routing decision recommending alternative route."""
    simulator.set_scenario("Bank degradation — RECOVER")
    decision = simulator.get_ai_decision()

    assert decision["affected_route"] == "UPI → Bank_X → Android"
    assert decision["recommended_route"] == "UPI → Bank_A → Android"
    assert "ROUTE SWITCH → Bank_A" in decision["recommended_action"]
    assert decision["confidence"] >= 0.90
    assert decision["expected_loss_before"] > decision["expected_loss_after"]


def test_safety_decision_immutability_and_demo_authorization(simulator):
    """6. Test that production safety remains strictly preserved when operator authorizes demo."""
    simulator.set_scenario("Low AI confidence — ESCALATE")
    initial_gate = simulator.get_safety_gate()
    assert initial_gate["production_safety"] == "HUMAN REVIEW REQUIRED"
    assert initial_gate["allowed"] is False
    assert initial_gate["simulation_authorized"] is False

    # Operator grants demo authorization
    simulator.authorize_simulation()
    authorized_gate = simulator.get_safety_gate()

    # Production safety decision is preserved, demo authorization flag is set separately
    assert authorized_gate["production_safety"] == "HUMAN REVIEW REQUIRED"
    assert authorized_gate["allowed"] is False
    assert authorized_gate["simulation_authorized"] is True


def test_canary_and_guardrail_integration(simulator):
    """7. Test canary execution and guardrail rollback on alternative degradation."""
    # Test RECOVER canary pass
    simulator.set_scenario("Bank degradation — RECOVER")
    res_recover = simulator.execute_bounded_simulation()
    assert res_recover["canary_decision"] in ("EXPAND", "STOP")
    assert res_recover["guardrail_decision"] in ("CONTINUE", "STOP")
    assert res_recover["recovered_transactions"] > 0

    # Test ROLLBACK guardrail trigger
    simulator.set_scenario("Recovery route degradation — ROLLBACK")
    simulator.authorize_simulation()
    res_rollback = simulator.execute_bounded_simulation()
    assert res_rollback["guardrail_decision"] == "ROLLBACK"
    assert res_rollback["rollback_required"] is True


def test_incident_intelligence_is_used(simulator, monkeypatch):
    """8. Test that IncidentIntelligence.assess() is genuinely used in incident detection."""
    called = False
    orig_assess = simulator.incident_intelligence.assess

    def mock_assess(*args, **kwargs):
        nonlocal called
        called = True
        return orig_assess(*args, **kwargs)

    monkeypatch.setattr(simulator.incident_intelligence, "assess", mock_assess)
    incident = simulator.get_incident_detection()

    assert called is True
    assert incident is not None
    assert incident["degradation_pp"] > 5.0
    assert "description" in incident


def test_revenue_at_risk_uses_revenue_calculator_and_actual_amounts(simulator, monkeypatch):
    """9. Test that revenue_at_risk comes from IncidentRevenueCalculator using actual transaction amounts."""
    calc_called = False
    orig_calc = simulator.revenue_calculator.calculate

    def mock_calc(*args, **kwargs):
        nonlocal calc_called
        calc_called = True
        return orig_calc(*args, **kwargs)

    monkeypatch.setattr(simulator.revenue_calculator, "calculate", mock_calc)

    # Set custom high amounts on all streamed events
    for ev in simulator.events_stream:
        ev.amount = 12000.0

    incident = simulator.get_incident_detection()
    assert calc_called is True
    assert incident is not None
    # With 12,000.0 amounts, revenue_at_risk must scale far above the baseline 1450.0 calculation (~43k)
    assert incident["revenue_at_risk"] > 50000.0


def test_safety_controller_remains_authoritative(simulator, monkeypatch):
    """10. Test that SafetyController.evaluate() is called and its result determines safety gate."""
    eval_called = False
    orig_eval = simulator.safety_controller.evaluate

    def mock_eval(decision):
        nonlocal eval_called
        eval_called = True
        return orig_eval(decision)

    monkeypatch.setattr(simulator.safety_controller, "evaluate", mock_eval)

    gate = simulator.get_safety_gate()
    assert eval_called is True
    assert gate["production_safety"] == "SAFE"
    assert gate["allowed"] is True


def test_pause_stream_prevents_advancement(simulator):
    """11. Test that pause prevents event advancement in step()."""
    initial_count = len(simulator.events_stream)
    initial_counter = simulator.event_counter

    simulator.pause()
    assert simulator.stream_paused is True

    # Stepping while paused should produce no events and not increment counter
    new_events = simulator.step(count=5)
    assert new_events == []
    assert len(simulator.events_stream) == initial_count
    assert simulator.event_counter == initial_counter

    # Resume allows stepping again
    simulator.resume()
    assert simulator.stream_paused is False
    resumed_events = simulator.step(count=2)
    assert len(resumed_events) == 2
    assert simulator.event_counter == initial_counter + 2


def test_reset_clears_pause_state(simulator):
    """12. Test that reset clears the pause state and restores event stream."""
    simulator.pause()
    assert simulator.stream_paused is True

    simulator.reset()
    assert simulator.stream_paused is False

    # Should now step normally
    events = simulator.step(count=1)
    assert len(events) == 1
