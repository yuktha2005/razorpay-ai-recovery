from typing import Any, Dict, List

from src.models.domain import Decision, SafetyDecision
from src.recovery.recovery_orchestrator import (
    RecoveryOrchestrator,
    RecoveryOrchestrationResult,
)
from src.recovery.recovery_audit_adapter import (
    record_recovery_outcome,
)


def execute_orchestrated_batch_recovery(
    transactions,
    incident,
    decision: Decision,
    safety: SafetyDecision,
    recovery,
    payment_method: str,
    affected_bank: str,
    device_type: str,
    batch_size: int = 50,
    human_approved: bool = False,
) -> Dict[str, Any]:
    """
    Execute a bounded batch recovery through the authoritative
    RecoveryOrchestrator.

    Lifecycle:

        Incident
            ↓
        Decision
            ↓
        Safety Gate
            ↓
        Bounded Canary Execution
            ↓
        Canary Evaluation
            ↓
        Outcome Verification
            ↓
        Learning
            ↓
        Audit

    This adapter preserves the legacy batch_result schema used
    by the dashboard while routing execution through the
    authoritative recovery orchestrator.
    """

    # -------------------------------------------------------------
    # 1. Build incident batch
    # -------------------------------------------------------------
    incident_transactions = transactions[
        transactions["payment_method"].eq(payment_method)
        & transactions["bank"].eq(affected_bank)
        & transactions["device_type"].eq(device_type)
        & transactions["status"].eq("FAILED")
    ].copy()

    # -------------------------------------------------------------
    # 2. Apply bounded batch size
    # -------------------------------------------------------------
    incident_transactions = incident_transactions.head(
        max(0, int(batch_size))
    )

    transaction_amounts: List[float] = (
        incident_transactions["amount"]
        .astype(float)
        .tolist()
    )

    eligible_transactions = len(transaction_amounts)

    # -------------------------------------------------------------
    # 3. Determine simulated recovery effectiveness
    # -------------------------------------------------------------
    if isinstance(recovery, dict):
        simulated_success_rate = float(
            recovery.get(
                "simulated_success_rate",
                recovery.get("alternative_success_rate", 0.80),
            )
        )
    else:
        simulated_success_rate = float(
            getattr(
                recovery,
                "simulated_success_rate",
                getattr(recovery, "alternative_success_rate", 0.80),
            )
        )

    simulated_success_rate = max(
        0.0,
        min(1.0, simulated_success_rate),
    )

    # -------------------------------------------------------------
    # 4. Safe Simulation Authorization Context
    #
    # NEVER mutate or overwrite the original production SafetyDecision.
    # If human_approved is True and safety requires human review,
    # create a separate simulation execution authorization object.
    # -------------------------------------------------------------
    if safety.requires_human_review and human_approved:
        execution_safety = SafetyDecision(
            payment_id=decision.payment_id,
            action=decision.recommended_action,
            allowed=True,
            requires_human_review=False,
            reason=(
                "[SIMULATION ONLY - DEMO AUTHORIZATION] Human operator authorized "
                f"bounded canary simulation for demo. Original safety gate: {safety.reason}"
            ),
        )
        is_simulation_authorized = True
    else:
        execution_safety = safety
        is_simulation_authorized = False

    orchestrator = RecoveryOrchestrator()

    orchestration_result: RecoveryOrchestrationResult = (
        orchestrator.execute(
            decision=decision,
            safety_decision=execution_safety,
            transaction_amounts=transaction_amounts,
            simulated_success_rate=simulated_success_rate,
        )
    )

    execution_result = orchestration_result.execution_result
    recovery_outcome = orchestration_result.recovery_outcome

    # -------------------------------------------------------------
    # 5. Extract authoritative canary result
    # -------------------------------------------------------------
    canary_decision = orchestration_result.canary_decision
    canary_reason = orchestration_result.canary_reason

    canary_attempted = (
        execution_result.attempted_transactions
    )

    canary_recoveries = (
        execution_result.successful_recoveries
    )

    if canary_attempted > 0:
        canary_recovery_rate = (
            canary_recoveries / canary_attempted
        )
    else:
        canary_recovery_rate = 0.0

    # -------------------------------------------------------------
    # 6. Map canary result to guardrail schema
    # -------------------------------------------------------------
    from src.policy_engine import evaluate_recovery_guardrail

    baseline_sr = (
        incident.get("baseline_success_rate", 0.9442)
        if isinstance(incident, dict)
        else getattr(incident, "baseline_success_rate", 0.9442)
    )
    if baseline_sr <= 1.0:
        baseline_sr *= 100.0

    current_alt_sr = simulated_success_rate
    if current_alt_sr <= 1.0:
        current_alt_sr *= 100.0

    guardrail_check = evaluate_recovery_guardrail(
        baseline_success_rate=baseline_sr,
        recovery_success_rate=current_alt_sr,
        rollout_percentage=100,
        recovery_active=True,
    )

    if guardrail_check.get("rollback_required") or guardrail_check.get("decision") == "ROLLBACK":
        guardrail_decision = "ROLLBACK"
        guardrail_reason = guardrail_check.get(
            "reason",
            "Recovery route degraded below the guardrail threshold.",
        )
        recovery_healthy = False
        rollback_required = True
    elif canary_decision == "EXPAND":
        guardrail_decision = "CONTINUE"
        guardrail_reason = (
            "Canary performance passed the expansion threshold. "
            "A larger bounded recovery batch may be evaluated."
        )
        recovery_healthy = True
        rollback_required = False
    elif canary_decision == "STOP":
        guardrail_decision = "STOP"
        guardrail_reason = canary_reason
        recovery_healthy = False
        rollback_required = False
    elif canary_decision == "ESCALATE":
        guardrail_decision = "ESCALATE"
        guardrail_reason = canary_reason
        recovery_healthy = False
        rollback_required = False
    elif canary_decision == "BLOCKED":
        guardrail_decision = "STOP"
        guardrail_reason = (
            "Safety controller blocked the recovery action."
        )
        recovery_healthy = False
        rollback_required = False
    elif canary_decision in (
        "RECOVERED",
        "NO_RECOVERY",
        "UNPROFITABLE",
    ):
        if canary_decision == "RECOVERED":
            guardrail_decision = "CONTINUE"
            guardrail_reason = "Recovery completed successfully."
            recovery_healthy = True
            rollback_required = False
        elif canary_decision == "NO_RECOVERY":
            guardrail_decision = "STOP"
            guardrail_reason = "No transactions were successfully recovered."
            recovery_healthy = False
            rollback_required = False
        else:
            guardrail_decision = "STOP"
            guardrail_reason = "Recovery was not economically viable."
            recovery_healthy = False
            rollback_required = True
    else:
        guardrail_decision = "NOT_APPLICABLE"
        guardrail_reason = "No recovery guardrail decision was required."
        recovery_healthy = False
        rollback_required = False

    # -------------------------------------------------------------
    # 7. Audit the verified recovery outcome
    # -------------------------------------------------------------
    incident_time_window = str(
        incident.get("time_window", "")
        if isinstance(incident, dict)
        else getattr(incident, "time_window", "")
    )
    if not incident_time_window:
        incident_time_window = (
            f"{payment_method} + "
            f"{affected_bank} + "
            f"{device_type}"
        )

    incident_txns_count = int(
        incident.get("transactions", eligible_transactions)
        if isinstance(incident, dict)
        else getattr(incident, "transactions_affected", eligible_transactions)
    )

    audit_result = record_recovery_outcome(
        orchestration_result=orchestration_result,
        incident_route=incident_time_window,
        payment_method=payment_method,
        bank=affected_bank,
        device_type=device_type,
        incident_transactions=incident_txns_count,
        average_transaction_value=(
            float(
                incident_transactions["amount"].mean()
            )
            if eligible_transactions > 0
            else 0.0
        ),
        original_safety=safety,
        simulation_authorized=is_simulation_authorized,
    )

    # -------------------------------------------------------------
    # 8. Preserve legacy batch_result contract and aliases
    # -------------------------------------------------------------
    recommended_bank = ""
    if decision.recommended_action.startswith("ROUTE_SWITCH:"):
        recommended_bank = decision.recommended_action.replace(
            "ROUTE_SWITCH:", ""
        ).strip()
    elif isinstance(recovery, dict):
        recommended_bank = recovery.get("alternative_bank", "")
    else:
        recommended_bank = getattr(recovery, "alternative_bank", "")

    result: Dict[str, Any] = {
        # Core recovery information
        "decision_action": orchestration_result.decision_action,
        "safety_action": orchestration_result.safety_action,
        "safety_allowed": orchestration_result.safety_allowed,
        "final_status": orchestration_result.final_status,
        "explanation": orchestration_result.explanation,

        # Simulation & Safety distinction
        "simulation_authorized": is_simulation_authorized,
        "original_safety_action": safety.action,
        "original_safety_allowed": safety.allowed,
        "original_safety_requires_human_review": safety.requires_human_review,

        # Batch metrics
        "eligible_transactions": eligible_transactions,
        "attempted_transactions": execution_result.attempted_transactions,
        "successful_recoveries": execution_result.successful_recoveries,
        "recovered_transactions": execution_result.successful_recoveries,
        "failed_recoveries": execution_result.failed_recoveries,
        "failed_transactions": execution_result.failed_recoveries,
        "remaining_failed": execution_result.failed_recoveries,
        "stopped_transactions": (
            execution_result.failed_recoveries
            if execution_result.status == "STOPPED"
            else 0
        ),
        "escalated_transactions": 0,
        "recovered_amount": float(recovery_outcome.recovered_amount),
        "attempted_amount": float(recovery_outcome.attempted_amount),
        "execution_cost": float(recovery_outcome.execution_cost),
        "net_recovered_value": float(recovery_outcome.net_recovered_value),
        "recovery_rate": float(recovery_outcome.recovery_rate),
        "success_rate_improvement": float(recovery_outcome.recovery_rate),
        "expected_additional_successes": float(
            execution_result.successful_recoveries
        ),
        "alternative_bank": recommended_bank,
        "estimated_recovered_value": float(recovery_outcome.recovered_amount),
        "simulated_recovered_value": float(recovery_outcome.recovered_amount),

        # Canary control
        "canary_attempted": canary_attempted,
        "canary_recovery_rate": float(canary_recovery_rate),
        "canary_decision": canary_decision,
        "canary_reason": canary_reason,

        # Guardrails
        "guardrail_decision": guardrail_decision,
        "guardrail_reason": guardrail_reason,
        "recovery_healthy": recovery_healthy,
        "rollback_required": rollback_required,

        # Learning & Audit
        "learning_stats": orchestration_result.learning_stats,
        "audit_result": audit_result,
        "execution_log": execution_result.execution_log,
    }

    return result