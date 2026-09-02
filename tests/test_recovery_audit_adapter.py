import csv

from src.recovery.recovery_audit_adapter import (
    record_recovery_outcome,
)
from src.recovery.recovery_orchestrator import (
    RecoveryOrchestrationResult,
)
from src.recovery.bounded_executor import (
    RecoveryExecutionResult,
)
from src.tracking.recovery_outcome import (
    RecoveryOutcome,
)


def test_recovery_outcome_is_written_to_audit_log(tmp_path, monkeypatch):
    """
    Verify that a recovery outcome is converted into the
    existing audit-log schema and persisted correctly.
    """

    audit_file = tmp_path / "recovery_audit.csv"

    # Redirect the existing audit logger to a temporary file.
    monkeypatch.setattr(
        "src.audit_logger.AUDIT_FILE",
        audit_file,
    )

    monkeypatch.setattr(
        "src.audit_logger.LOG_DIR",
        tmp_path,
    )

    execution = RecoveryExecutionResult(
        action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        status="COMPLETED",
        attempted_transactions=5,
        successful_recoveries=4,
        failed_recoveries=1,
        recovery_budget=5000,
        estimated_cost=125,
        stop_reason="Bounded canary execution completed.",
        execution_log=[],
    )

    outcome = RecoveryOutcome(
        attempted_transactions=5,
        successful_recoveries=4,
        failed_recoveries=1,
        attempted_amount=10000,
        recovered_amount=8000,
        execution_cost=125,
        net_recovered_value=7875,
        recovery_rate=0.80,
        outcome_status="RECOVERED",
        explanation="Recovery generated measurable positive net recovered value.",
    )

    orchestration_result = RecoveryOrchestrationResult(
        decision_action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        safety_action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        safety_allowed=True,
        execution_result=execution,
        recovery_outcome=outcome,
        final_status="COMPLETED",
        explanation="Recovery completed successfully.",
    )

    record = record_recovery_outcome(
        orchestration_result=orchestration_result,
        incident_route="2026-07-23 19:00-20:00",
        payment_method="UPI",
        bank="Bank_X",
        device_type="Android",
        incident_transactions=50,
        average_transaction_value=2000,
    )

    # ---------------------------------------------------------
    # Verify returned audit record
    # ---------------------------------------------------------

    assert record["audit_event_type"] == "POLICY_EVENT"
    assert record["payment_method"] == "UPI"
    assert record["affected_bank"] == "Bank_X"

    assert (
        record["recommended_bank"]
        == "UPI + Bank_Y + Android"
    )

    assert record["policy_approved"] is True

    assert record["eligible_transactions"] == 5
    assert record["recovered_transactions"] == 4

    assert (
        float(record["simulated_recovered_value"])
        == 8000
    )

    assert (
        record["guardrail_decision"]
        == "COMPLETED"
    )

    # ---------------------------------------------------------
    # Verify CSV persistence
    # ---------------------------------------------------------

    assert audit_file.exists()

    with open(
        audit_file,
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        rows = list(
            csv.DictReader(file)
        )

    assert len(rows) == 1

    row = rows[0]

    assert row["payment_method"] == "UPI"
    assert row["affected_bank"] == "Bank_X"

    assert (
        row["recovered_transactions"]
        == "4"
    )

    assert (
        float(row["simulated_recovered_value"])
        == 8000
    )


def test_blocked_recovery_is_audited(tmp_path, monkeypatch):
    """
    Verify that a safety-blocked recovery is recorded
    without claiming any recovered money.
    """

    audit_file = tmp_path / "recovery_audit.csv"

    monkeypatch.setattr(
        "src.audit_logger.AUDIT_FILE",
        audit_file,
    )

    monkeypatch.setattr(
        "src.audit_logger.LOG_DIR",
        tmp_path,
    )

    execution = RecoveryExecutionResult(
        action="MONITOR",
        status="BLOCKED",
        attempted_transactions=0,
        successful_recoveries=0,
        failed_recoveries=0,
        recovery_budget=5000,
        estimated_cost=0,
        stop_reason="Safety Controller rejected the action.",
        execution_log=[],
    )

    outcome = RecoveryOutcome(
        attempted_transactions=0,
        successful_recoveries=0,
        failed_recoveries=0,
        attempted_amount=0,
        recovered_amount=0,
        execution_cost=0,
        net_recovered_value=0,
        recovery_rate=0,
        outcome_status="NO_EXECUTION",
        explanation="No recovery transactions were executed.",
    )

    orchestration_result = RecoveryOrchestrationResult(
        decision_action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        safety_action="MONITOR",
        safety_allowed=False,
        execution_result=execution,
        recovery_outcome=outcome,
        final_status="BLOCKED",
        explanation="Recovery was blocked by the Safety Controller.",
    )

    record = record_recovery_outcome(
        orchestration_result=orchestration_result,
        incident_route="2026-07-23 19:00-20:00",
        payment_method="UPI",
        bank="Bank_X",
        device_type="Android",
        incident_transactions=50,
        average_transaction_value=2000,
    )

    assert record["policy_approved"] is False
    assert record["eligible_transactions"] == 0
    assert record["recovered_transactions"] == 0
    assert float(record["simulated_recovered_value"]) == 0

    with open(
        audit_file,
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        rows = list(
            csv.DictReader(file)
        )

    assert len(rows) == 1
    assert rows[0]["recovered_transactions"] == "0"