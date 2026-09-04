"""
Milestone 4 — Safety & Failure Scenarios Integration Tests (Phase 2).

Validates that safety, budget, guardrail, canary, and learning boundaries
hold across the end-to-end recovery pipeline under stress and failure conditions:
1. Critical Exposure End-to-End Block
2. Zero Eligible Transactions
3. Canary Escalation Propagation
4. Unprofitable Recovery -> Rollback
5. Partial Budget Exhaustion
6. Learning Contamination Prevention
"""

import pandas as pd
import pytest

from src.models.domain import Decision, SafetyDecision
from src.recovery.bounded_executor import BoundedRecoveryExecutor
from src.recovery.orchestrated_batch import execute_orchestrated_batch_recovery
from src.recovery.recovery_orchestrator import RecoveryOrchestrator
from src.safety.controller import SafetyController
from src.tracking.learning_history import PersistentLearningHistory
from src.tracking.learning_store import load_learning_history


@pytest.fixture(autouse=True)
def isolate_storage(tmp_path, monkeypatch):
    """Isolate learning and audit storage to temporary directory for all tests."""
    learning_file = tmp_path / "recovery_learning.csv"
    audit_file = tmp_path / "recovery_audit.csv"

    monkeypatch.setattr("src.tracking.learning_store.LEARNING_FILE", learning_file)
    monkeypatch.setattr("src.tracking.learning_store.LOG_DIR", tmp_path)
    monkeypatch.setattr("src.audit_logger.AUDIT_FILE", audit_file)
    monkeypatch.setattr("src.audit_logger.LOG_DIR", tmp_path)


def test_critical_exposure_end_to_end_block():
    """
    Scenario 1: Critical Exposure End-to-End Block.
    Proves that a decision with financial exposure >= ₹500,000 is blocked
    by the safety controller, requires human review, and when passed to the
    recovery orchestrator results in 0 attempts, ₹0 recovered, ₹0 cost,
    and no learning evidence.
    """
    decision = Decision(
        payment_id="INCIDENT:UPI + Bank_Critical + Android",
        recommended_action="ROUTE_SWITCH:UPI + Bank_Backup + Android",
        confidence=0.98,
        expected_loss_before=500000.0,
        expected_loss_after=50000.0,
        estimated_value=450000.0,
        explanation="Critical financial exposure recovery.",
    )

    safety_controller = SafetyController()
    safety_decision = safety_controller.evaluate(decision)

    # Policy gate verifies critical exposure block
    assert safety_decision.allowed is False
    assert safety_decision.requires_human_review is True
    assert "critical" in safety_decision.reason.lower()

    # Direct RecoveryOrchestrator execution
    orchestrator = RecoveryOrchestrator()
    amounts = [5000.0] * 20
    orchestration_result = orchestrator.execute(
        decision=decision,
        safety_decision=safety_decision,
        transaction_amounts=amounts,
        simulated_success_rate=0.95,
    )

    assert orchestration_result.safety_allowed is False
    assert orchestration_result.final_status == "BLOCKED"
    assert orchestration_result.canary_decision == "BLOCKED"
    assert orchestration_result.execution_result.attempted_transactions == 0
    assert orchestration_result.execution_result.successful_recoveries == 0
    assert orchestration_result.execution_result.failed_recoveries == 0
    assert orchestration_result.recovery_outcome.recovered_amount == 0.0
    assert orchestration_result.recovery_outcome.execution_cost == 0.0
    assert orchestration_result.learning_stats is None

    # Full batch orchestration execution
    txns = pd.DataFrame([
        {
            "transaction_id": f"txn_{i}",
            "timestamp": "2026-07-23 19:15:00",
            "payment_method": "UPI",
            "bank": "Bank_Critical",
            "device_type": "Android",
            "status": "FAILED",
            "amount": 25000.0,
        }
        for i in range(20)
    ])
    incident = {
        "time_window": "2026-07-23 19:00:00",
        "payment_method": "UPI",
        "bank": "Bank_Critical",
        "device_type": "Android",
        "transactions": 20,
        "baseline_success_rate": 0.95,
        "success_rate": 0.60,
    }

    batch_result = execute_orchestrated_batch_recovery(
        transactions=txns,
        incident=incident,
        decision=decision,
        safety=safety_decision,
        recovery={"alternative_bank": "Bank_Backup", "simulated_success_rate": 0.95},
        payment_method="UPI",
        affected_bank="Bank_Critical",
        device_type="Android",
        batch_size=20,
        human_approved=False,
    )

    assert batch_result["original_safety_allowed"] is False
    assert batch_result["original_safety_requires_human_review"] is True
    assert batch_result["final_status"] == "BLOCKED"
    assert batch_result["attempted_transactions"] == 0
    assert batch_result["recovered_amount"] == 0.0
    assert batch_result["execution_cost"] == 0.0
    assert batch_result["learning_stats"] is None

    # Verify no learning evidence is recorded
    history = load_learning_history()
    assert len(history) == 0


def test_zero_eligible_transactions():
    """
    Scenario 2: Zero Eligible Transactions.
    Run orchestrated batch recovery with an incident whose route/time filter
    produces zero eligible failed transactions.
    Verify:
    - eligible_transactions == 0
    - attempted_transactions == 0
    - successful_recoveries == 0
    - recovered_amount == 0
    - execution_cost == 0
    - no division-by-zero
    - no learning record is created
    - final state is safely non-executed
    """
    # Transactions exist, but none match the incident criteria (different bank)
    txns = pd.DataFrame([
        {
            "transaction_id": f"txn_{i}",
            "timestamp": "2026-07-23 19:15:00",
            "payment_method": "UPI",
            "bank": "Bank_UNRELATED",
            "device_type": "Android",
            "status": "FAILED",
            "amount": 1000.0,
        }
        for i in range(10)
    ])
    incident = {
        "time_window": "2026-07-23 19:00:00",
        "payment_method": "UPI",
        "bank": "Bank_Target",
        "device_type": "Android",
        "transactions": 10,
        "baseline_success_rate": 0.95,
        "success_rate": 0.65,
    }
    decision = Decision(
        payment_id="INCIDENT:UPI + Bank_Target + Android",
        recommended_action="ROUTE_SWITCH:UPI + Bank_Alternative + Android",
        confidence=0.92,
        expected_loss_before=15000.0,
        expected_loss_after=3000.0,
        estimated_value=12000.0,
        explanation="Route switch recommendation.",
    )
    safety = SafetyDecision(
        payment_id="INCIDENT:UPI + Bank_Target + Android",
        action="ROUTE_SWITCH:UPI + Bank_Alternative + Android",
        allowed=True,
        reason="Route recovery permitted.",
        requires_human_review=False,
    )
    recovery = {
        "alternative_bank": "Bank_Alternative",
        "simulated_success_rate": 0.95,
    }

    result = execute_orchestrated_batch_recovery(
        transactions=txns,
        incident=incident,
        decision=decision,
        safety=safety,
        recovery=recovery,
        payment_method="UPI",
        affected_bank="Bank_Target",
        device_type="Android",
        batch_size=20,
        human_approved=False,
    )

    assert result["eligible_transactions"] == 0
    assert result["attempted_transactions"] == 0
    assert result["successful_recoveries"] == 0
    assert result["recovered_amount"] == 0.0
    assert result["execution_cost"] == 0.0
    assert result["final_status"] == "NO_EXECUTION"
    assert result["canary_decision"] == "STOP"
    assert result["learning_stats"] is None
    assert len(load_learning_history()) == 0


def test_canary_escalation_propagation():
    """
    Scenario 3: Canary Escalation Propagation.
    Forces a canary outcome where enough attempts exist (>= 5),
    but the canary recovery rate is below the escalation threshold (< expected_rate * 0.50).
    Uses the real CanaryController and real orchestration path without mocking.
    Verify:
    - CanaryDecision.decision == "ESCALATE"
    - canary_reason is populated
    - orchestrated batch maps it to the expected guardrail state
    - recovery_healthy == False
    - no expansion occurs
    """
    # 50 transactions with canary_percentage=0.10 gives 5 attempts
    txns = pd.DataFrame([
        {
            "transaction_id": f"txn_{i}",
            "timestamp": "2026-07-23 19:15:00",
            "payment_method": "UPI",
            "bank": "Bank_Degraded",
            "device_type": "Android",
            "status": "FAILED",
            "amount": 1000.0,
        }
        for i in range(50)
    ])
    incident = {
        "time_window": "2026-07-23 19:00:00",
        "payment_method": "UPI",
        "bank": "Bank_Degraded",
        "device_type": "Android",
        "transactions": 50,
        "baseline_success_rate": 0.95,
        "success_rate": 0.65,
    }
    decision = Decision(
        payment_id="INCIDENT:UPI + Bank_Degraded + Android",
        recommended_action="ROUTE_SWITCH:UPI + Bank_Alternative + Android",
        confidence=0.90,
        expected_loss_before=20000.0,
        expected_loss_after=4000.0,
        estimated_value=16000.0,
        explanation="Route recovery initiated.",
    )
    safety = SafetyDecision(
        payment_id="INCIDENT:UPI + Bank_Degraded + Android",
        action="ROUTE_SWITCH:UPI + Bank_Alternative + Android",
        allowed=True,
        reason="Recovery permitted subject to guardrails.",
        requires_human_review=False,
    )
    # simulated_success_rate=0.10 produces 0 successes out of 5 attempts deterministically
    # (canary_rate = 0.0 < 0.10 * 0.50 = 0.05, and expected_rate = 0.10 > 0.05 min threshold)
    recovery = {
        "alternative_bank": "Bank_Alternative",
        "simulated_success_rate": 0.10,
    }

    result = execute_orchestrated_batch_recovery(
        transactions=txns,
        incident=incident,
        decision=decision,
        safety=safety,
        recovery=recovery,
        payment_method="UPI",
        affected_bank="Bank_Degraded",
        device_type="Android",
        batch_size=50,
        human_approved=False,
    )

    assert result["canary_attempted"] == 5
    assert result["canary_decision"] == "ESCALATE"
    assert "materially below expectation" in result["canary_reason"]
    assert result["recovery_healthy"] is False
    assert result["canary_decision"] != "EXPAND"
    assert result["guardrail_decision"] in ("ESCALATE", "ROLLBACK")


def test_unprofitable_recovery_triggers_rollback():
    """
    Scenario 4: Unprofitable Recovery -> Rollback.
    Constructs a deterministic recovery outcome where:
    - at least one transaction succeeds
    - recovered amount is lower than execution cost
    - net_recovered_value <= 0
    Verify:
    - outcome is UNPROFITABLE according to existing financial model
    - rollback_required == True
    - system does not report run as financially successful
    - audit/financial values remain internally consistent
    """
    # 1 failed transaction with small amount (₹10.0)
    # Execution cost is ₹25.0 per attempt
    txns = pd.DataFrame([
        {
            "transaction_id": "txn_micro_0",
            "timestamp": "2026-07-23 19:15:00",
            "payment_method": "UPI",
            "bank": "Bank_LowValue",
            "device_type": "Android",
            "status": "FAILED",
            "amount": 10.0,
        }
    ])
    incident = {
        "time_window": "2026-07-23 19:00:00",
        "payment_method": "UPI",
        "bank": "Bank_LowValue",
        "device_type": "Android",
        "transactions": 1,
        "baseline_success_rate": 0.95,
        "success_rate": 0.60,
    }
    decision = Decision(
        payment_id="INCIDENT:UPI + Bank_LowValue + Android",
        recommended_action="ROUTE_SWITCH:UPI + Bank_Alternative + Android",
        confidence=0.90,
        expected_loss_before=1000.0,
        expected_loss_after=200.0,
        estimated_value=800.0,
        explanation="Attempt recovery on micro transaction.",
    )
    safety = SafetyDecision(
        payment_id="INCIDENT:UPI + Bank_LowValue + Android",
        action="ROUTE_SWITCH:UPI + Bank_Alternative + Android",
        allowed=True,
        reason="Permitted.",
        requires_human_review=False,
    )
    # With simulated_success_rate = 0.70, (1*37)%100 = 37 < 70 -> transaction succeeds
    # Route is degraded against 95% baseline (70% < 90% min recovery guardrail)
    recovery = {
        "alternative_bank": "Bank_Alternative",
        "simulated_success_rate": 0.70,
    }

    result = execute_orchestrated_batch_recovery(
        transactions=txns,
        incident=incident,
        decision=decision,
        safety=safety,
        recovery=recovery,
        payment_method="UPI",
        affected_bank="Bank_LowValue",
        device_type="Android",
        batch_size=1,
        human_approved=False,
    )

    # 1. At least one transaction succeeded
    assert result["successful_recoveries"] == 1
    # 2. Recovered amount is lower than execution cost
    assert result["recovered_amount"] == 10.0
    assert result["execution_cost"] == 25.0
    assert result["recovered_amount"] < result["execution_cost"]
    # 3. Net recovered value <= 0
    assert result["net_recovered_value"] == -15.0
    # 4. Outcome is UNPROFITABLE
    assert result["final_status"] == "UNPROFITABLE"
    # 5. Rollback is required
    assert result["rollback_required"] is True
    # 6. Not reported as financially successful
    assert result["recovery_healthy"] is False
    assert result["audit_result"]["audit_event_type"] == "ROLLBACK"
    # 7. Audit/financial consistency
    audit = result["audit_result"]
    assert audit["recovered_amount"] == 10.0
    assert audit["execution_cost"] == 25.0
    assert audit["net_recovered_value"] == -15.0
    assert audit["net_recovered_value"] == audit["recovered_amount"] - audit["execution_cost"]


def test_partial_budget_exhaustion():
    """
    Scenario 5: Partial Budget Exhaustion.
    Uses a small recovery budget (₹75.0) so only part of an otherwise eligible batch can execute.
    Verify:
    - attempted_transactions never exceeds the budget
    - successful + failed == attempted
    - attempted_amount equals the amounts actually attempted
    - recovered_amount equals actual successful transaction amounts
    - execution_cost equals attempted_transactions * per-transaction cost
    - net_recovered_value == recovered_amount - execution_cost
    - recovery rate is mathematically correct
    - no extra transaction executes after budget exhaustion
    """
    amounts = [100.0, 200.0, 300.0, 400.0, 500.0, 600.0]
    executor = BoundedRecoveryExecutor(
        max_transactions=10,
        recovery_budget=75.0,  # ₹25 per txn -> max 3 txns
        canary_percentage=1.0,
    )
    orchestrator = RecoveryOrchestrator(executor=executor)

    decision = Decision(
        payment_id="INCIDENT:UPI + Bank_Budget + Android",
        recommended_action="ROUTE_SWITCH:UPI + Bank_Alternative + Android",
        confidence=0.95,
        expected_loss_before=5000.0,
        expected_loss_after=1000.0,
        estimated_value=4000.0,
        explanation="Budget bounded recovery.",
    )
    safety = SafetyDecision(
        payment_id="INCIDENT:UPI + Bank_Budget + Android",
        action="ROUTE_SWITCH:UPI + Bank_Alternative + Android",
        allowed=True,
        reason="Safety cleared.",
        requires_human_review=False,
    )

    result = orchestrator.execute(
        decision=decision,
        safety_decision=safety,
        transaction_amounts=amounts,
        simulated_success_rate=0.95,
    )

    exec_res = result.execution_result
    outcome = result.recovery_outcome

    # 1. Budget allows exactly 3 transactions: 3 * 25 = 75 <= 75, 4th would cost 100 > 75
    assert exec_res.attempted_transactions == 3
    assert exec_res.attempted_transactions * 25.0 <= 75.0
    # 2. successful + failed == attempted
    assert exec_res.successful_recoveries + exec_res.failed_recoveries == exec_res.attempted_transactions
    # 3. attempted_amount equals amounts actually attempted (first 3 amounts: 100 + 200 + 300 = 600.0)
    assert outcome.attempted_amount == sum(amounts[:3])
    # 4. recovered_amount equals actual successful transaction amounts
    assert outcome.recovered_amount == sum(exec_res.successful_transaction_amounts)
    # 5. execution_cost equals attempted_transactions * 25.0
    assert outcome.execution_cost == exec_res.attempted_transactions * 25.0
    # 6. net_recovered_value == recovered_amount - execution_cost
    assert outcome.net_recovered_value == outcome.recovered_amount - outcome.execution_cost
    # 7. recovery rate is mathematically correct
    expected_rate = round(exec_res.successful_recoveries / exec_res.attempted_transactions, 4)
    assert outcome.recovery_rate == expected_rate
    # 8. No extra transaction executes after budget exhaustion
    assert "Recovery budget reached." in exec_res.execution_log
    assert exec_res.status == "STOPPED"


def test_learning_contamination_prevention():
    """
    Scenario 6: Learning Contamination Prevention.
    Uses temporary learning storage.
    Runs:
    a) A safety-blocked recovery
    b) A zero-attempt/non-executed recovery
    c) A safety-action mismatch recovery (which safely blocks execution)
    Verify:
    - no invalid learning evidence is persisted
    - blocked/zero-attempt runs do not increase learned attempts
    - valid successful recovery evidence still persists normally
    """
    orchestrator = RecoveryOrchestrator()

    # a) Safety-blocked recovery (amount at risk >= 500,000)
    decision_blocked = Decision(
        payment_id="INCIDENT:UPI + Bank_Blocked + Android",
        recommended_action="ROUTE_SWITCH:UPI + Bank_Blocked_Alt + Android",
        confidence=0.95,
        expected_loss_before=600000.0,
        expected_loss_after=50000.0,
        estimated_value=550000.0,
        explanation="Blocked decision.",
    )
    safety_blocked = SafetyController().evaluate(decision_blocked)
    assert safety_blocked.allowed is False

    res_blocked = orchestrator.execute(
        decision=decision_blocked,
        safety_decision=safety_blocked,
        transaction_amounts=[1000.0] * 10,
        simulated_success_rate=0.95,
    )
    assert res_blocked.learning_stats is None

    # b) Zero-attempt recovery
    decision_zero = Decision(
        payment_id="INCIDENT:UPI + Bank_Zero + Android",
        recommended_action="ROUTE_SWITCH:UPI + Bank_Zero_Alt + Android",
        confidence=0.95,
        expected_loss_before=10000.0,
        expected_loss_after=2000.0,
        estimated_value=8000.0,
        explanation="Zero attempt decision.",
    )
    safety_zero = SafetyDecision(
        payment_id="INCIDENT:UPI + Bank_Zero + Android",
        action="ROUTE_SWITCH:UPI + Bank_Zero_Alt + Android",
        allowed=True,
        reason="Allowed.",
        requires_human_review=False,
    )
    res_zero = orchestrator.execute(
        decision=decision_zero,
        safety_decision=safety_zero,
        transaction_amounts=[],
        simulated_success_rate=0.95,
    )
    assert res_zero.learning_stats is None

    # c) Safety action mismatch (e.g. Safety returned MONITOR for a ROUTE_SWITCH decision)
    decision_mismatch = Decision(
        payment_id="INCIDENT:UPI + Bank_Mismatch + Android",
        recommended_action="ROUTE_SWITCH:UPI + Bank_Mismatch_Alt + Android",
        confidence=0.40,
        expected_loss_before=10000.0,
        expected_loss_after=2000.0,
        estimated_value=8000.0,
        explanation="Low confidence decision.",
    )
    safety_mismatch = SafetyController().evaluate(decision_mismatch)
    assert safety_mismatch.action == "MONITOR"
    assert safety_mismatch.action != decision_mismatch.recommended_action

    res_mismatch = orchestrator.execute(
        decision=decision_mismatch,
        safety_decision=safety_mismatch,
        transaction_amounts=[1000.0] * 10,
        simulated_success_rate=0.95,
    )
    assert res_mismatch.learning_stats is None

    # Verify no learning evidence persisted for any invalid/blocked/zero-attempt runs
    history_pre = load_learning_history()
    assert len(history_pre) == 0

    # Now execute a valid successful recovery
    decision_valid = Decision(
        payment_id="INCIDENT:UPI + Bank_Valid + Android",
        recommended_action="ROUTE_SWITCH:UPI + Bank_Valid_Alt + Android",
        confidence=0.95,
        expected_loss_before=15000.0,
        expected_loss_after=2000.0,
        estimated_value=13000.0,
        explanation="Valid recovery decision.",
    )
    safety_valid = SafetyDecision(
        payment_id="INCIDENT:UPI + Bank_Valid + Android",
        action="ROUTE_SWITCH:UPI + Bank_Valid_Alt + Android",
        allowed=True,
        reason="Valid safety approval.",
        requires_human_review=False,
    )
    res_valid = orchestrator.execute(
        decision=decision_valid,
        safety_decision=safety_valid,
        transaction_amounts=[1000.0] * 20,
        simulated_success_rate=0.95,
    )
    assert res_valid.learning_stats is not None
    assert res_valid.learning_stats.route == "UPI + Bank_Valid_Alt + Android"

    # Verify that only the valid route was persisted
    history_post = load_learning_history()
    assert len(history_post) == 1
    assert history_post[0]["route"] == "UPI + Bank_Valid_Alt + Android"
    assert int(history_post[0]["attempts"]) > 0

    # Verify reloading via PersistentLearningHistory
    loaded_stats = PersistentLearningHistory().load()
    assert len(loaded_stats) == 1
    assert loaded_stats[0].route == "UPI + Bank_Valid_Alt + Android"
    assert loaded_stats[0].attempts == res_valid.learning_stats.attempts
    assert loaded_stats[0].recoveries == res_valid.learning_stats.recoveries


def test_unprofitable_recovery_independently_triggers_rollback_on_healthy_route():
    """
    Phase 2.5 Regression Test:
    Proves that an UNPROFITABLE recovery outcome independently triggers
    rollback_required=True, even when the recovery route remains fully healthy
    (so route-level degradation guardrails do NOT trigger rollback) and the
    canary controller returns STOP (small sample) rather than being conflated
    with the recovery outcome state machine.

    Also proves that a profitable recovery on the same healthy route does NOT
    trigger rollback.
    """
    # 1. Unprofitable recovery on healthy route
    # 1 transaction of ₹10.0 vs fixed execution cost of ₹25.0
    txns_unprofitable = pd.DataFrame([
        {
            "transaction_id": "txn_healthy_micro",
            "timestamp": "2026-07-23 19:15:00",
            "payment_method": "UPI",
            "bank": "Bank_Incident",
            "device_type": "Android",
            "status": "FAILED",
            "amount": 10.0,
        }
    ])
    incident = {
        "time_window": "2026-07-23 19:00:00",
        "payment_method": "UPI",
        "bank": "Bank_Incident",
        "device_type": "Android",
        "transactions": 50,
        "baseline_success_rate": 0.95,
        "success_rate": 0.65,
    }
    decision = Decision(
        payment_id="INCIDENT:UPI + Bank_Incident + Android",
        recommended_action="ROUTE_SWITCH:UPI + Bank_Healthy + Android",
        confidence=0.92,
        expected_loss_before=5000.0,
        expected_loss_after=500.0,
        estimated_value=4500.0,
        explanation="Switch to healthy candidate route.",
    )
    safety = SafetyDecision(
        payment_id="INCIDENT:UPI + Bank_Incident + Android",
        action="ROUTE_SWITCH:UPI + Bank_Healthy + Android",
        allowed=True,
        reason="Route recovery permitted.",
        requires_human_review=False,
    )
    # 95% simulated success rate matches baseline 95%, so route degradation is 0.0 pp
    # and 95% >= 90% min quality guardrail. Route guardrail does NOT trigger rollback.
    recovery = {
        "alternative_bank": "Bank_Healthy",
        "simulated_success_rate": 0.95,
    }

    result_unprofitable = execute_orchestrated_batch_recovery(
        transactions=txns_unprofitable,
        incident=incident,
        decision=decision,
        safety=safety,
        recovery=recovery,
        payment_method="UPI",
        affected_bank="Bank_Incident",
        device_type="Android",
        batch_size=1,
        human_approved=False,
    )

    # Recovery executes at least one successful transaction
    assert result_unprofitable["attempted_transactions"] == 1
    assert result_unprofitable["successful_recoveries"] == 1
    # recovered_amount < execution_cost
    assert result_unprofitable["recovered_amount"] == 10.0
    assert result_unprofitable["execution_cost"] == 25.0
    assert result_unprofitable["recovered_amount"] < result_unprofitable["execution_cost"]
    # Canary decision is STOP (sample size < 5), proving canary state is not conflated with outcome
    assert result_unprofitable["canary_decision"] == "STOP"
    # Recovery outcome verifier produces UNPROFITABLE
    assert result_unprofitable["final_status"] == "UNPROFITABLE"
    # UNPROFITABLE outcome independently forces rollback_required=True and recovery_healthy=False
    assert result_unprofitable["rollback_required"] is True
    assert result_unprofitable["recovery_healthy"] is False
    # Financial values reconcile
    assert result_unprofitable["net_recovered_value"] == -15.0
    assert (
        result_unprofitable["net_recovered_value"]
        == result_unprofitable["recovered_amount"] - result_unprofitable["execution_cost"]
    )

    # 2. Profitable counterpart on the same healthy route
    # 1 transaction of ₹1000.0 vs ₹25.0 execution cost -> net +₹975.0
    txns_profitable = pd.DataFrame([
        {
            "transaction_id": "txn_healthy_profitable",
            "timestamp": "2026-07-23 19:15:00",
            "payment_method": "UPI",
            "bank": "Bank_Incident",
            "device_type": "Android",
            "status": "FAILED",
            "amount": 1000.0,
        }
    ])

    result_profitable = execute_orchestrated_batch_recovery(
        transactions=txns_profitable,
        incident=incident,
        decision=decision,
        safety=safety,
        recovery=recovery,
        payment_method="UPI",
        affected_bank="Bank_Incident",
        device_type="Android",
        batch_size=1,
        human_approved=False,
    )

    # Profitable recovery produces RECOVERED outcome and does NOT trigger rollback
    assert result_profitable["final_status"] == "RECOVERED"
    assert result_profitable["net_recovered_value"] == 975.0
    assert result_profitable["rollback_required"] is False
