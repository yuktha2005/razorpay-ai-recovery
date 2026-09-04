import pytest

from src.tracking.financial_summary import (
    FinancialSummary,
    calculate_financial_summary,
)
from src.tracking.recovery_outcome import RecoveryOutcome


def test_positive_net_recovery_and_positive_roi():
    """
    Scenario 1: recovered_amount > execution_cost
    → positive net recovery
    → positive ROI
    Example: recovered = ₹1000, cost = ₹125 → net = ₹875, ROI = 7.0x
    """
    outcome = RecoveryOutcome(
        attempted_transactions=5,
        successful_recoveries=4,
        failed_recoveries=1,
        attempted_amount=1250.0,
        recovered_amount=1000.0,
        execution_cost=125.0,
        net_recovered_value=875.0,
        recovery_rate=0.80,
        outcome_status="RECOVERED",
        explanation="Positive net value.",
    )

    summary = calculate_financial_summary(
        revenue_at_risk=50000.0,
        eligible_amount=25000.0,
        recovery_outcome=outcome,
    )

    assert summary.revenue_at_risk == 50000.0
    assert summary.eligible_amount == 25000.0
    assert summary.attempted_amount == 1250.0
    assert summary.recovered_amount == 1000.0
    assert summary.execution_cost == 125.0
    assert summary.net_recovered_value == 875.0
    assert summary.recovery_rate == 0.80
    assert summary.recovery_roi == 7.0
    assert summary.roi_display == "7.0x"
    assert summary.has_executed is True


def test_breakeven_recovery_and_zero_roi():
    """
    Scenario 2: recovered_amount == execution_cost
    → net recovery = 0
    → ROI = 0.0x
    """
    outcome = RecoveryOutcome(
        attempted_transactions=5,
        successful_recoveries=1,
        failed_recoveries=4,
        attempted_amount=1250.0,
        recovered_amount=125.0,
        execution_cost=125.0,
        net_recovered_value=0.0,
        recovery_rate=0.20,
        outcome_status="UNPROFITABLE",
        explanation="Break-even recovery.",
    )

    summary = calculate_financial_summary(
        revenue_at_risk=20000.0,
        eligible_amount=5000.0,
        recovery_outcome=outcome,
    )

    assert summary.net_recovered_value == 0.0
    assert summary.recovery_roi == 0.0
    assert summary.roi_display == "0.0x"
    assert summary.has_executed is True


def test_unprofitable_recovery_and_negative_roi():
    """
    Scenario 3: recovered_amount < execution_cost
    → negative net recovery
    → negative ROI
    """
    outcome = RecoveryOutcome(
        attempted_transactions=4,
        successful_recoveries=1,
        failed_recoveries=3,
        attempted_amount=800.0,
        recovered_amount=50.0,
        execution_cost=100.0,
        net_recovered_value=-50.0,
        recovery_rate=0.25,
        outcome_status="UNPROFITABLE",
        explanation="Cost exceeded recovery.",
    )

    summary = calculate_financial_summary(
        revenue_at_risk=15000.0,
        eligible_amount=4000.0,
        recovery_outcome=outcome,
    )

    assert summary.net_recovered_value == -50.0
    assert summary.recovery_roi == -0.5
    assert summary.roi_display == "-0.5x"
    assert summary.has_executed is True


def test_zero_execution_cost_safe_roi():
    """
    Scenario 4: execution_cost == 0
    → no division by zero
    → ROI represented safely as None with clean N/A message
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
        explanation="Blocked before execution.",
    )

    summary = calculate_financial_summary(
        revenue_at_risk=30000.0,
        eligible_amount=10000.0,
        recovery_outcome=outcome,
    )

    assert summary.execution_cost == 0.0
    assert summary.net_recovered_value == 0.0
    assert summary.recovery_roi is None
    assert summary.roi_display == "ROI: N/A — no execution cost recorded"


def test_unexecuted_state_handling():
    """
    Verify clean pre-execution behavior when neither batch_result nor
    recovery_outcome is supplied.
    """
    summary = calculate_financial_summary(
        revenue_at_risk=45000.0,
        eligible_amount=18000.0,
    )

    assert summary.revenue_at_risk == 45000.0
    assert summary.eligible_amount == 18000.0
    assert summary.attempted_amount == 0.0
    assert summary.recovered_amount == 0.0
    assert summary.execution_cost == 0.0
    assert summary.net_recovered_value == 0.0
    assert summary.recovery_rate == 0.0
    assert summary.recovery_roi is None
    assert summary.roi_display == "ROI: N/A — no execution cost recorded"
    assert summary.has_executed is False


def test_batch_result_dictionary_integration():
    """
    Verify calculate_financial_summary works correctly with batch_result dictionaries
    and extracts all authoritative metrics.
    """
    batch_result = {
        "eligible_transactions": 25,
        "eligible_amount": 50000.0,
        "attempted_transactions": 5,
        "successful_recoveries": 4,
        "recovered_amount": 8000.0,
        "attempted_amount": 10000.0,
        "execution_cost": 125.0,
        "net_recovered_value": 7875.0,
        "recovery_rate": 0.80,
    }

    summary = calculate_financial_summary(
        revenue_at_risk=60000.0,
        batch_result=batch_result,
    )

    assert summary.revenue_at_risk == 60000.0
    assert summary.eligible_amount == 50000.0
    assert summary.attempted_amount == 10000.0
    assert summary.recovered_amount == 8000.0
    assert summary.execution_cost == 125.0
    assert summary.net_recovered_value == 7875.0
    assert summary.recovery_rate == 0.80
    assert summary.recovery_roi == round(7875.0 / 125.0, 2)
    assert summary.roi_display == "63.0x"
    assert summary.has_executed is True


def test_orchestrated_batch_recovery_financial_integration(tmp_path, monkeypatch):
    """
    Verify execute_orchestrated_batch_recovery includes eligible_amount, net_recovered_value,
    and execution_cost, and that calculate_financial_summary authoritatively computes ROI.
    """
    import pandas as pd
    from src.models.domain import Decision, SafetyDecision
    from src.recovery.orchestrated_batch import execute_orchestrated_batch_recovery

    audit_file = tmp_path / "recovery_audit.csv"
    monkeypatch.setattr("src.audit_logger.AUDIT_FILE", audit_file)
    monkeypatch.setattr("src.audit_logger.LOG_DIR", tmp_path)

    # 10 failed transactions
    df = pd.DataFrame([
        {
            "payment_method": "UPI",
            "bank": "Bank_X",
            "device_type": "Android",
            "status": "FAILED",
            "amount": 2000.0,
        }
        for _ in range(10)
    ])

    incident = {
        "time_window": "2026-07-23 19:00-20:00",
        "baseline_success_rate": 0.95,
        "transactions": 10,
    }

    decision = Decision(
        payment_id="PAY_TEST",
        recommended_action="ROUTE_SWITCH:Bank_Y",
        confidence=0.92,
        expected_loss_before=20000.0,
        expected_loss_after=2000.0,
        estimated_value=18000.0,
        explanation="Switch to Bank_Y",
    )

    safety = SafetyDecision(
        payment_id="PAY_TEST",
        action="ROUTE_SWITCH:Bank_Y",
        allowed=True,
        requires_human_review=False,
        reason="Action is safe",
    )

    recovery = {
        "alternative_bank": "Bank_Y",
        "simulated_success_rate": 0.90,
    }

    result = execute_orchestrated_batch_recovery(
        transactions=df,
        incident=incident,
        decision=decision,
        safety=safety,
        recovery=recovery,
        payment_method="UPI",
        affected_bank="Bank_X",
        device_type="Android",
        batch_size=10,
    )

    assert "eligible_amount" in result
    assert result["eligible_amount"] == 20000.0  # 10 * 2000.0
    assert "net_recovered_value" in result
    assert "execution_cost" in result
    # recovery_roi is NOT duplicated in batch_result; FinancialSummary owns it
    assert "recovery_roi" not in result

    # FinancialSummary authoritatively computes ROI from the batch result
    summary = calculate_financial_summary(batch_result=result)
    if result["execution_cost"] > 0:
        expected_roi = round(
            result["net_recovered_value"] / result["execution_cost"], 2
        )
        assert summary.recovery_roi == expected_roi
        assert summary.roi_display == f"{expected_roi:.1f}x"
