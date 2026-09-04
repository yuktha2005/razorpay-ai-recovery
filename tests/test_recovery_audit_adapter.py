import csv
import pandas as pd

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


def test_audit_records_persist_net_recovered_value(tmp_path, monkeypatch):
    """
    Verify that net_recovered_value and financial fields are
    persisted into the audit file upon recovery execution.
    """
    audit_file = tmp_path / "recovery_audit.csv"
    monkeypatch.setattr("src.audit_logger.AUDIT_FILE", audit_file)
    monkeypatch.setattr("src.audit_logger.LOG_DIR", tmp_path)

    execution = RecoveryExecutionResult(
        action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        status="COMPLETED",
        attempted_transactions=10,
        successful_recoveries=8,
        failed_recoveries=2,
        recovery_budget=5000,
        estimated_cost=250,
        stop_reason="Bounded canary execution completed.",
        execution_log=[],
    )

    outcome = RecoveryOutcome(
        attempted_transactions=10,
        successful_recoveries=8,
        failed_recoveries=2,
        attempted_amount=20000.0,
        recovered_amount=16000.0,
        execution_cost=250.0,
        net_recovered_value=15750.0,
        recovery_rate=0.80,
        outcome_status="RECOVERED",
        explanation="Recovery generated positive net recovered value.",
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
        average_transaction_value=2000.0,
    )

    assert record["net_recovered_value"] == 15750.0
    assert record["recovered_amount"] == 16000.0
    assert record["attempted_amount"] == 20000.0
    assert record["execution_cost"] == 250.0
    assert record["recovery_rate"] == 0.80

    with open(audit_file, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 1
    row = rows[0]
    assert float(row["net_recovered_value"]) == 15750.0
    assert float(row["recovered_amount"]) == 16000.0
    assert float(row["attempted_amount"]) == 20000.0
    assert float(row["execution_cost"]) == 250.0
    assert float(row["recovery_rate"]) == 0.80


def test_old_audit_rows_without_financial_fields_remain_readable(tmp_path, monkeypatch):
    """
    Verify backward compatibility: reading historical audit logs that
    lack the new financial fields succeeds safely without crashing.
    """
    audit_file = tmp_path / "recovery_audit.csv"
    monkeypatch.setattr("src.audit_logger.AUDIT_FILE", audit_file)
    monkeypatch.setattr("src.audit_logger.LOG_DIR", tmp_path)

    legacy_columns = [
        "timestamp", "audit_event_type", "incident_time", "payment_method",
        "affected_bank", "device_type", "recommended_bank", "policy_decision",
        "policy_approved", "policy_reason", "human_review_required",
        "incident_transactions", "failed_transactions", "eligible_transactions",
        "recovered_transactions", "remaining_failed", "stopped_transactions",
        "escalated_transactions", "success_rate_before", "success_rate_after",
        "success_improvement_pp", "expected_additional_successes",
        "estimated_recovered_value", "simulated_recovered_value",
        "average_transaction_value", "guardrail_decision", "guardrail_reason",
        "recovery_healthy", "rollback_required"
    ]

    with open(audit_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=legacy_columns)
        writer.writeheader()
        writer.writerow({
            "timestamp": "2026-07-23T19:15:00",
            "audit_event_type": "RECOVERY_DECISION",
            "incident_time": "2026-07-23 19:00:00",
            "payment_method": "UPI",
            "affected_bank": "Bank_X",
            "device_type": "Android",
            "recommended_bank": "Bank_Y",
            "policy_decision": "RECOVER",
            "policy_approved": "True",
            "recovered_transactions": "5",
            "simulated_recovered_value": "10000.0",
        })

    from src.audit_logger import load_audit_log
    df = load_audit_log()
    assert df is not None
    assert len(df) == 1
    assert "net_recovered_value" in df.columns
    for col in [
        "attempted_amount",
        "recovered_amount",
        "execution_cost",
        "net_recovered_value",
        "recovery_rate",
    ]:
        assert col in df.columns
        assert pd.isna(df[col].iloc[0]) or df[col].iloc[0] == ""
    assert df["payment_method"].iloc[0] == "UPI"
    assert df["affected_bank"].iloc[0] == "Bank_X"

    # Append a new record
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
        attempted_amount=10000.0,
        recovered_amount=8000.0,
        execution_cost=125.0,
        net_recovered_value=7875.0,
        recovery_rate=0.80,
        outcome_status="RECOVERED",
        explanation="Positive net value.",
    )

    orchestration_result = RecoveryOrchestrationResult(
        decision_action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        safety_action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        safety_allowed=True,
        execution_result=execution,
        recovery_outcome=outcome,
        final_status="COMPLETED",
        explanation="Recovery completed.",
    )

    record_recovery_outcome(
        orchestration_result=orchestration_result,
        incident_route="2026-07-23 19:00-20:00",
        payment_method="UPI",
        bank="Bank_X",
        device_type="Android",
        incident_transactions=50,
        average_transaction_value=2000.0,
    )

    df_updated = load_audit_log()
    assert len(df_updated) == 2
    assert float(df_updated["net_recovered_value"].iloc[1]) == 7875.0


def test_audit_logger_owns_financial_columns_without_adapter():
    """
    Verify src.audit_logger alone defines and owns all five financial columns.
    """
    import src.audit_logger as audit_mod

    required = [
        "attempted_amount",
        "recovered_amount",
        "execution_cost",
        "net_recovered_value",
        "recovery_rate",
    ]
    for col in required:
        assert col in audit_mod.AUDIT_COLUMNS


def test_recovery_audit_adapter_does_not_monkey_patch():
    """
    Verify recovery_audit_adapter does not monkey-patch or replace log_recovery_event.
    """
    import src.audit_logger as audit_mod
    import src.recovery.recovery_audit_adapter as adapter_mod

    assert adapter_mod.log_recovery_event is audit_mod.log_recovery_event
