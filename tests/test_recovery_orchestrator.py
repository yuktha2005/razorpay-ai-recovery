from src.models.domain import Decision, SafetyDecision
from src.recovery.recovery_orchestrator import RecoveryOrchestrator


def make_decision(action):
    return Decision(
        payment_id="INCIDENT:TEST",
        recommended_action=action,
        confidence=0.95,
        expected_loss_before=10000,
        expected_loss_after=2000,
        estimated_value=8000,
    )


def test_blocked_safety_prevents_execution():
    orchestrator = RecoveryOrchestrator()

    decision = make_decision(
        "ROUTE_SWITCH:UPI + Bank_Y + Android"
    )

    safety_decision = SafetyDecision(
        payment_id="INCIDENT:TEST",
        action="MONITOR",
        allowed=False,
        reason="High-value recovery requires human review.",
        requires_human_review=True,
    )

    result = orchestrator.execute(
        decision=decision,
        safety_decision=safety_decision,
        transaction_amounts=[1000, 2000, 3000],
        simulated_success_rate=0.90,
    )

    assert result.final_status == "BLOCKED"
    assert result.execution_result.attempted_transactions == 0
    assert result.recovery_outcome.recovered_amount == 0


def test_monitor_does_not_execute():
    orchestrator = RecoveryOrchestrator()

    decision = make_decision("MONITOR")

    safety_decision = SafetyDecision(
        payment_id="INCIDENT:TEST",
        action="MONITOR",
        allowed=True,
        reason="Confidence below minimum threshold.",
        requires_human_review=False,
    )

    result = orchestrator.execute(
        decision=decision,
        safety_decision=safety_decision,
        transaction_amounts=[1000, 2000, 3000],
        simulated_success_rate=0.90,
    )

    assert result.final_status == "MONITORING"
    assert result.execution_result.status == "NOT_EXECUTED"
    assert result.recovery_outcome.outcome_status == "NO_EXECUTION"


def test_action_mismatch_is_blocked():
    orchestrator = RecoveryOrchestrator()

    decision = make_decision(
        "ROUTE_SWITCH:UPI + Bank_Y + Android"
    )

    safety_decision = SafetyDecision(
        payment_id="INCIDENT:TEST",
        action="ROUTE_SWITCH:UPI + Bank_C + Android",
        allowed=True,
        reason="Approved alternative route.",
        requires_human_review=False,
    )

    result = orchestrator.execute(
        decision=decision,
        safety_decision=safety_decision,
        transaction_amounts=[1000, 2000, 3000],
        simulated_success_rate=0.90,
    )

    assert result.final_status == "BLOCKED"
    assert result.execution_result.attempted_transactions == 0
    assert result.recovery_outcome.recovered_amount == 0


def test_approved_recovery_is_executed_and_verified():
    orchestrator = RecoveryOrchestrator()

    action = "ROUTE_SWITCH:UPI + Bank_Y + Android"

    decision = make_decision(action)

    safety_decision = SafetyDecision(
        payment_id="INCIDENT:TEST",
        action=action,
        allowed=True,
        reason="Recovery action passed safety controls.",
        requires_human_review=False,
    )

    result = orchestrator.execute(
        decision=decision,
        safety_decision=safety_decision,
        transaction_amounts=[
            1000,
            2000,
            1500,
            500,
            3000,
        ],
        simulated_success_rate=1.0,
    )

    assert result.safety_allowed is True
    assert result.execution_result.attempted_transactions > 0
    assert result.execution_result.successful_recoveries > 0

    assert (
        result.recovery_outcome.successful_recoveries
        == result.execution_result.successful_recoveries
    )

    assert (
        result.recovery_outcome.failed_recoveries
        == result.execution_result.failed_recoveries
    )

    assert result.recovery_outcome.recovered_amount > 0


def test_failed_recovery_is_stopped_and_verified():
    orchestrator = RecoveryOrchestrator()

    action = "ROUTE_SWITCH:UPI + Bank_Y + Android"

    decision = make_decision(action)

    safety_decision = SafetyDecision(
        payment_id="INCIDENT:TEST",
        action=action,
        allowed=True,
        reason="Recovery action passed safety controls.",
        requires_human_review=False,
    )

    result = orchestrator.execute(
        decision=decision,
        safety_decision=safety_decision,
        transaction_amounts=[
            1000,
            2000,
            1500,
            500,
            3000,
        ],
        simulated_success_rate=0.0,
    )

    assert result.execution_result.status == "STOPPED"
    assert result.execution_result.failed_recoveries > 0
    assert result.recovery_outcome.recovered_amount == 0
    assert result.recovery_outcome.outcome_status == "NO_RECOVERY"


def test_learning_is_restored_after_orchestrator_restart(
    tmp_path,
    monkeypatch,
):
    learning_file = (
        tmp_path / "recovery_learning.csv"
    )

    monkeypatch.setattr(
        "src.tracking.learning_store.LEARNING_FILE",
        learning_file,
    )

    monkeypatch.setattr(
        "src.tracking.learning_store.LOG_DIR",
        tmp_path,
    )

    action = "ROUTE_SWITCH:UPI + Bank_Y + Android"

    decision = make_decision(action)

    safety_decision = SafetyDecision(
        payment_id="INCIDENT:PERSISTENCE",
        action=action,
        allowed=True,
        reason="Recovery action passed safety controls.",
        requires_human_review=False,
    )

    # ---------------------------------------------------------
    # First orchestrator learns from a recovery.
    # ---------------------------------------------------------
    first = RecoveryOrchestrator()

    first_result = first.execute(
        decision=decision,
        safety_decision=safety_decision,
        transaction_amounts=[
            1000,
            2000,
            1500,
        ],
        simulated_success_rate=1.0,
    )

    assert first_result.learning_stats is not None

    first_attempts = (
        first_result.execution_result.attempted_transactions
    )

    first_recoveries = (
        first_result.execution_result.successful_recoveries
    )

    assert first_attempts > 0
    assert first_recoveries > 0

    assert (
        first_result.learning_stats.attempts
        == first_attempts
    )

    assert (
        first_result.learning_stats.recoveries
        == first_recoveries
    )

    # ---------------------------------------------------------
    # Create a completely new orchestrator.
    # ---------------------------------------------------------
    second = RecoveryOrchestrator()

    restored = second.learning_engine.get_route(
        "UPI + Bank_Y + Android"
    )

    assert restored is not None

    assert (
        restored.attempts
        == first_attempts
    )

    assert (
        restored.recoveries
        == first_recoveries
    )

    # ---------------------------------------------------------
    # New recovery continues from restored history.
    # ---------------------------------------------------------
    second_result = second.execute(
        decision=decision,
        safety_decision=safety_decision,
        transaction_amounts=[
            500,
            700,
        ],
        simulated_success_rate=1.0,
    )

    assert second_result.learning_stats is not None

    second_attempts = (
        second_result.execution_result.attempted_transactions
    )

    second_recoveries = (
        second_result.execution_result.successful_recoveries
    )

    assert second_attempts > 0
    assert second_recoveries > 0

    assert (
        second_result.learning_stats.attempts
        == first_attempts + second_attempts
    )

    assert (
        second_result.learning_stats.recoveries
        == first_recoveries + second_recoveries
    )