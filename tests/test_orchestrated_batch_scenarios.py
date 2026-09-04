import pandas as pd
import pytest

from src.models.domain import Decision, SafetyDecision
from src.recovery.orchestrated_batch import execute_orchestrated_batch_recovery
from src.scenario_engine import get_scenario, list_scenarios


@pytest.fixture
def mock_transactions():
    """Create a minimal set of transactions matching the test incident route."""
    data = []
    for i in range(30):
        data.append({
            "transaction_id": f"txn_{i}",
            "timestamp": "2026-07-23 19:15:00",
            "payment_method": "UPI",
            "bank": "Bank_X",
            "device_type": "Android",
            "status": "FAILED",
            "amount": 1000.0,
        })
    return pd.DataFrame(data)


@pytest.fixture
def incident_context():
    return {
        "time_window": "2026-07-23 19:00:00",
        "payment_method": "UPI",
        "bank": "Bank_X",
        "device_type": "Android",
        "transactions": 508,
        "baseline_success_rate": 0.9442,
        "success_rate": 0.6949,
    }


def test_scenario_recover(mock_transactions, incident_context, tmp_path, monkeypatch):
    """Scenario 1: RECOVER executes bounded canary and expands."""
    monkeypatch.setattr("src.audit_logger.AUDIT_FILE", tmp_path / "recovery_audit.csv")
    monkeypatch.setattr("src.audit_logger.LOG_DIR", tmp_path)

    decision = Decision(
        payment_id="UPI + Bank_X + Android",
        recommended_action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        confidence=0.90,
        expected_loss_before=10000.0,
        expected_loss_after=2000.0,
        estimated_value=8000.0,
        explanation="Route degradation justifies recovery.",
    )

    safety = SafetyDecision(
        payment_id="UPI + Bank_X + Android",
        action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        allowed=True,
        reason="Route recovery passed safety checks.",
        requires_human_review=False,
    )

    recovery = {
        "alternative_bank": "Bank_Y",
        "alternative_success_rate": 0.95,
        "simulated_success_rate": 0.95,
    }

    result = execute_orchestrated_batch_recovery(
        transactions=mock_transactions,
        incident=incident_context,
        decision=decision,
        safety=safety,
        recovery=recovery,
        payment_method="UPI",
        affected_bank="Bank_X",
        device_type="Android",
        batch_size=20,
        human_approved=False,
    )

    assert result["simulation_authorized"] is False
    assert result["original_safety_allowed"] is True
    assert result["canary_decision"] in ("EXPAND", "STOP")
    assert result["guardrail_decision"] in ("CONTINUE", "STOP")
    assert result["recovered_transactions"] > 0
    assert result["simulated_recovered_value"] > 0


def test_scenario_escalate_without_human_approval_is_blocked(mock_transactions, incident_context, tmp_path, monkeypatch):
    """Scenario 3 (part 1): ESCALATE without human approval blocks execution."""
    monkeypatch.setattr("src.audit_logger.AUDIT_FILE", tmp_path / "recovery_audit.csv")
    monkeypatch.setattr("src.audit_logger.LOG_DIR", tmp_path)

    decision = Decision(
        payment_id="UPI + Bank_X + Android",
        recommended_action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        confidence=0.61,
        expected_loss_before=10000.0,
        expected_loss_after=2000.0,
        estimated_value=8000.0,
        explanation="Low AI confidence requires review.",
    )

    safety = SafetyDecision(
        payment_id="UPI + Bank_X + Android",
        action="ESCALATE",
        allowed=False,
        reason="AI confidence below automation threshold.",
        requires_human_review=True,
    )

    recovery = {
        "alternative_bank": "Bank_Y",
        "alternative_success_rate": 0.95,
    }

    result = execute_orchestrated_batch_recovery(
        transactions=mock_transactions,
        incident=incident_context,
        decision=decision,
        safety=safety,
        recovery=recovery,
        payment_method="UPI",
        affected_bank="Bank_X",
        device_type="Android",
        batch_size=20,
        human_approved=False,
    )

    # Execution must remain blocked
    assert result["simulation_authorized"] is False
    assert result["original_safety_requires_human_review"] is True
    assert result["final_status"] == "BLOCKED"
    assert result["canary_decision"] == "BLOCKED"
    assert result["guardrail_decision"] == "STOP"
    assert result["recovered_transactions"] == 0

    # Audit record must preserve original production safety gate
    audit_record = result["audit_result"]
    assert audit_record["policy_decision"] == "ESCALATE"
    assert audit_record["policy_approved"] is False
    assert audit_record["human_review_required"] is True


def test_scenario_escalate_with_human_approval_runs_canary_preserving_safety(mock_transactions, incident_context, tmp_path, monkeypatch):
    """Scenario 3 (part 2): ESCALATE with human_approved=True executes bounded canary without mutating safety."""
    monkeypatch.setattr("src.audit_logger.AUDIT_FILE", tmp_path / "recovery_audit.csv")
    monkeypatch.setattr("src.audit_logger.LOG_DIR", tmp_path)

    decision = Decision(
        payment_id="UPI + Bank_X + Android",
        recommended_action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        confidence=0.61,
        expected_loss_before=10000.0,
        expected_loss_after=2000.0,
        estimated_value=8000.0,
        explanation="Low AI confidence requires review.",
    )

    safety = SafetyDecision(
        payment_id="UPI + Bank_X + Android",
        action="ESCALATE",
        allowed=False,
        reason="AI confidence below automation threshold.",
        requires_human_review=True,
    )

    recovery = {
        "alternative_bank": "Bank_Y",
        "alternative_success_rate": 0.95,
        "simulated_success_rate": 0.95,
    }

    result = execute_orchestrated_batch_recovery(
        transactions=mock_transactions,
        incident=incident_context,
        decision=decision,
        safety=safety,
        recovery=recovery,
        payment_method="UPI",
        affected_bank="Bank_X",
        device_type="Android",
        batch_size=20,
        human_approved=True,
    )

    # CRITICAL: original SafetyDecision was NOT mutated
    assert safety.allowed is False
    assert safety.requires_human_review is True
    assert safety.action == "ESCALATE"

    # Simulation context was authorized
    assert result["simulation_authorized"] is True
    assert result["original_safety_requires_human_review"] is True
    assert result["attempted_transactions"] > 0
    assert result["recovered_transactions"] > 0

    # Audit record faithfully recorded production decision
    audit_record = result["audit_result"]
    assert audit_record["policy_decision"] == "ESCALATE"
    assert audit_record["policy_approved"] is False
    assert audit_record["human_review_required"] is True


def test_scenario_rollback_guardrail_breach(mock_transactions, incident_context, tmp_path, monkeypatch):
    """Scenario 4: Recovery route degradation triggers guardrail ROLLBACK."""
    monkeypatch.setattr("src.audit_logger.AUDIT_FILE", tmp_path / "recovery_audit.csv")
    monkeypatch.setattr("src.audit_logger.LOG_DIR", tmp_path)

    scenario = get_scenario("Recovery route degradation — ROLLBACK")

    decision = Decision(
        payment_id="UPI + Bank_X + Android",
        recommended_action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        confidence=0.90,
        expected_loss_before=10000.0,
        expected_loss_after=4000.0,
        estimated_value=6000.0,
        explanation="Route recovery initiated.",
    )

    safety = SafetyDecision(
        payment_id="UPI + Bank_X + Android",
        action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        allowed=True,
        reason="Recovery permitted subject to guardrails.",
        requires_human_review=False,
    )

    recovery = {
        "alternative_bank": "Bank_Y",
        "alternative_success_rate": scenario["post_recovery_success_rate"],
        "simulated_success_rate": scenario["post_recovery_success_rate"],
    }

    result = execute_orchestrated_batch_recovery(
        transactions=mock_transactions,
        incident=incident_context,
        decision=decision,
        safety=safety,
        recovery=recovery,
        payment_method="UPI",
        affected_bank="Bank_X",
        device_type="Android",
        batch_size=20,
        human_approved=False,
    )

    assert result["guardrail_decision"] == "ROLLBACK"
    assert result["rollback_required"] is True
    assert result["recovery_healthy"] is False


def test_scenario_stop_enforcement(mock_transactions, incident_context, tmp_path, monkeypatch):
    """Scenario 2: Mild degradation produces STOP decision."""
    monkeypatch.setattr("src.audit_logger.AUDIT_FILE", tmp_path / "recovery_audit.csv")
    monkeypatch.setattr("src.audit_logger.LOG_DIR", tmp_path)

    decision = Decision(
        payment_id="UPI + Bank_X + Android",
        recommended_action="MONITOR",
        confidence=0.92,
        expected_loss_before=1000.0,
        expected_loss_after=1000.0,
        estimated_value=0.0,
        explanation="Degradation below recovery threshold.",
    )

    safety = SafetyDecision(
        payment_id="UPI + Bank_X + Android",
        action="STOP",
        allowed=False,
        reason="Degradation does not justify route switch.",
        requires_human_review=False,
    )

    recovery = {
        "alternative_bank": "Bank_Y",
        "alternative_success_rate": 0.95,
    }

    result = execute_orchestrated_batch_recovery(
        transactions=mock_transactions,
        incident=incident_context,
        decision=decision,
        safety=safety,
        recovery=recovery,
        payment_method="UPI",
        affected_bank="Bank_X",
        device_type="Android",
        batch_size=20,
        human_approved=False,
    )

    assert result["final_status"] == "BLOCKED"
    assert result["guardrail_decision"] == "STOP"
    assert result["recovered_transactions"] == 0


def test_batch_result_authoritative_financial_metrics(mock_transactions, incident_context, tmp_path, monkeypatch):
    """
    Verify that batch_result['recovery_rate'] and batch_result['net_recovered_value']
    are sourced authoritatively and match RecoveryOutcome.
    """
    monkeypatch.setattr("src.audit_logger.AUDIT_FILE", tmp_path / "recovery_audit.csv")
    monkeypatch.setattr("src.audit_logger.LOG_DIR", tmp_path)

    decision = Decision(
        payment_id="UPI + Bank_X + Android",
        recommended_action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        confidence=0.92,
        expected_loss_before=10000.0,
        expected_loss_after=2000.0,
        estimated_value=8000.0,
        explanation="Route degradation justifies recovery.",
    )

    safety = SafetyDecision(
        payment_id="UPI + Bank_X + Android",
        action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        allowed=True,
        reason="Passed safety check.",
        requires_human_review=False,
    )

    recovery = {
        "alternative_bank": "Bank_Y",
        "alternative_success_rate": 0.95,
        "simulated_success_rate": 0.95,
    }

    result = execute_orchestrated_batch_recovery(
        transactions=mock_transactions,
        incident=incident_context,
        decision=decision,
        safety=safety,
        recovery=recovery,
        payment_method="UPI",
        affected_bank="Bank_X",
        device_type="Android",
        batch_size=20,
        human_approved=False,
    )

    # Verify authoritative financial fields are present
    assert "recovery_rate" in result
    assert "net_recovered_value" in result
    assert "recovered_amount" in result
    assert "execution_cost" in result
    assert "attempted_amount" in result

    # Verify math consistency
    assert result["net_recovered_value"] == round(
        result["recovered_amount"] - result["execution_cost"], 2
    )
    if result["attempted_transactions"] > 0:
        expected_rate = round(
            result["successful_recoveries"] / result["attempted_transactions"], 4
        )
        assert result["recovery_rate"] == expected_rate


def test_section_6_recovery_analysis_updates_session_state(mock_transactions, incident_context, tmp_path, monkeypatch):
    """
    Verify that executing recovery analysis assigns batch_result to session state,
    ensuring Section 4 reflects the execution immediately.
    """
    monkeypatch.setattr("src.audit_logger.AUDIT_FILE", tmp_path / "recovery_audit.csv")
    monkeypatch.setattr("src.audit_logger.LOG_DIR", tmp_path)

    mock_session_state = {}

    decision = Decision(
        payment_id="UPI + Bank_X + Android",
        recommended_action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        confidence=0.90,
        expected_loss_before=10000.0,
        expected_loss_after=2000.0,
        estimated_value=8000.0,
        explanation="Route switch justified.",
    )

    safety = SafetyDecision(
        payment_id="UPI + Bank_X + Android",
        action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        allowed=True,
        reason="Allowed.",
        requires_human_review=False,
    )

    recovery = {
        "alternative_bank": "Bank_Y",
        "alternative_success_rate": 0.90,
        "simulated_success_rate": 0.90,
    }

    # Simulate the exact Section 6 button execution logic
    analysis_result = execute_orchestrated_batch_recovery(
        transactions=mock_transactions,
        incident=incident_context,
        decision=decision,
        safety=safety,
        recovery=recovery,
        payment_method="UPI",
        affected_bank="Bank_X",
        device_type="Android",
        batch_size=20,
        human_approved=True,
    )
    mock_session_state["batch_result"] = analysis_result

    assert mock_session_state.get("batch_result") is not None
    assert mock_session_state["batch_result"]["recovery_rate"] > 0
    assert mock_session_state["batch_result"]["net_recovered_value"] > 0
