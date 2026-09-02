from src.decision.incident_decision_engine import IncidentDecisionEngine
from src.recovery.recovery_orchestrator import RecoveryOrchestrator
from src.recovery.recovery_audit_adapter import record_recovery_outcome


def test_full_recovery_loop(tmp_path, monkeypatch):
    """
    Verify the complete recovery lifecycle:

    Incident
        -> Decision
        -> Safety
        -> Recovery
        -> Outcome
        -> Audit
        -> Learning
    """

    # ---------------------------------------------------------
    # Use temporary audit storage
    # ---------------------------------------------------------

    audit_file = tmp_path / "recovery_audit.csv"

    monkeypatch.setattr(
        "src.audit_logger.AUDIT_FILE",
        audit_file,
    )

    monkeypatch.setattr(
        "src.audit_logger.LOG_DIR",
        tmp_path,
    )

    # ---------------------------------------------------------
    # 1. Incident -> Decision
    # ---------------------------------------------------------

    engine = IncidentDecisionEngine()

    decision_result = engine.evaluate(
        incident_route="UPI + Bank_X + Android",
        transactions_affected=100,
        failures_observed=35,
        baseline_success_rate=0.95,
        current_success_rate=0.65,
        severity="CRITICAL",
        average_transaction_value=750.0,
        route_candidates=[
            {
                "route": "UPI + Bank_Y + Android",
                "transactions": 100,
                "successes": 97,
            },
            {
                "route": "UPI + Bank_Z + Android",
                "transactions": 80,
                "successes": 72,
            },
        ],
    )

    assert decision_result.decision is not None

    assert decision_result.decision.recommended_action.startswith(
        "ROUTE_SWITCH:"
    )

    assert decision_result.safety_decision.allowed is True

    # ---------------------------------------------------------
    # 2. Decision -> Bounded Recovery
    # ---------------------------------------------------------

    orchestrator = RecoveryOrchestrator()

    transaction_amounts = [750.0] * 20

    result = orchestrator.execute(
        decision=decision_result.decision,
        safety_decision=decision_result.safety_decision,
        transaction_amounts=transaction_amounts,
        simulated_success_rate=0.95,
    )

    assert result.safety_allowed is True

    assert result.execution_result.status == "COMPLETED"

    assert result.execution_result.attempted_transactions > 0

    # ---------------------------------------------------------
    # 3. Recovery -> Outcome
    # ---------------------------------------------------------

    assert result.recovery_outcome is not None

    assert result.recovery_outcome.attempted_transactions > 0

    assert result.recovery_outcome.recovered_amount >= 0

    assert result.recovery_outcome.net_recovered_value >= 0

    # ---------------------------------------------------------
    # 4. Outcome -> Learning
    # ---------------------------------------------------------

    assert result.learning_stats is not None

    assert result.learning_stats.attempts > 0

    assert result.learning_stats.recoveries >= 0

    # ---------------------------------------------------------
    # 5. Outcome -> Audit
    # ---------------------------------------------------------

    audit_record = record_recovery_outcome(
        orchestration_result=result,
        incident_route="2026-07-23 19:00-20:00",
        payment_method="UPI",
        bank="Bank_X",
        device_type="Android",
        incident_transactions=100,
        average_transaction_value=750.0,
    )

    assert audit_record is not None

    assert audit_record["policy_approved"] is True

    assert audit_record["eligible_transactions"] > 0

    assert audit_record["recovered_transactions"] >= 0

    assert audit_file.exists()

    # ---------------------------------------------------------
    # 6. Verify persisted audit record
    # ---------------------------------------------------------

    import csv

    with open(
        audit_file,
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        rows = list(csv.DictReader(file))

    assert len(rows) == 1

    row = rows[0]

    assert row["payment_method"] == "UPI"

    assert row["affected_bank"] == "Bank_X"

    assert row["recovered_transactions"] == str(
        result.execution_result.successful_recoveries
    )

    # ---------------------------------------------------------
    # Final lifecycle assertion
    # ---------------------------------------------------------

    assert result.final_status in {
        "RECOVERED",
        "NO_RECOVERY",
        "UNPROFITABLE",
    }