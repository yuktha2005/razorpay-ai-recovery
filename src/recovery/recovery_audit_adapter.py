from src.audit_logger import log_recovery_event
from src.recovery.recovery_orchestrator import (
    RecoveryOrchestrationResult,
)


def record_recovery_outcome(
    orchestration_result: RecoveryOrchestrationResult,
    incident_route: str,
    payment_method: str,
    bank: str,
    device_type: str,
    incident_transactions: int,
    average_transaction_value: float,
    original_safety=None,
    simulation_authorized: bool = False,
):
    """
    Convert the new recovery orchestration result into the
    existing audit logger format.

    This function does not execute recovery.
    It only records what happened.
    """

    execution = orchestration_result.execution_result
    outcome = orchestration_result.recovery_outcome

    # ---------------------------------------------------------
    # Incident information
    # ---------------------------------------------------------

    incident = {
        "time_window": incident_route,
        "payment_method": payment_method,
        "bank": bank,
        "device_type": device_type,
    }

    # ---------------------------------------------------------
    # Recovery information
    # ---------------------------------------------------------

    recommended_action = (
        orchestration_result.decision_action
    )

    recommended_bank = ""

    if recommended_action.startswith(
        "ROUTE_SWITCH:"
    ):
        recommended_bank = (
            recommended_action
            .replace("ROUTE_SWITCH:", "")
            .strip()
        )

    recovery = {
        "alternative_bank": recommended_bank,
    }

    # ---------------------------------------------------------
    # Policy information
    #
    # Never overwrite the original production safety decision.
    # If an original_safety is provided, record it faithfully.
    # ---------------------------------------------------------

    if original_safety is not None:
        policy_result = {
            "decision": original_safety.action,
            "approved": original_safety.allowed,
            "reason": original_safety.reason,
            "human_review_required": (
                original_safety.requires_human_review
            ),
        }
    else:
        policy_result = {
            "decision": orchestration_result.safety_action,
            "approved": orchestration_result.safety_allowed,
            "reason": orchestration_result.explanation,
            "human_review_required": False,
        }

    # ---------------------------------------------------------
    # Determine recovery health
    # ---------------------------------------------------------

    recovery_healthy = (
        outcome.outcome_status == "RECOVERED"
        and outcome.net_recovered_value > 0
    )

    rollback_required = (
        outcome.outcome_status
        in {
            "NO_RECOVERY",
            "UNPROFITABLE",
        }
    )

    # ---------------------------------------------------------
    # Batch result
    # ---------------------------------------------------------

    batch_result = {
        "total_transactions": incident_transactions,

        "failed_transactions": (
            execution.failed_recoveries
        ),

        "eligible_transactions": (
            execution.attempted_transactions
        ),

        "recovered_transactions": (
            execution.successful_recoveries
        ),

        "remaining_failed": (
            execution.failed_recoveries
        ),

        "stopped_transactions": (
            execution.failed_recoveries
            if execution.status == "STOPPED"
            else 0
        ),

        "escalated_transactions": 0,

        "current_success_rate": 0,

        "alternative_success_rate": (
            outcome.recovery_rate
        ),

        "success_rate_improvement": (
            outcome.recovery_rate
        ),

        "expected_additional_successes": (
            execution.successful_recoveries
        ),

        "estimated_recovered_value": (
            outcome.recovered_amount
        ),

        "simulated_recovered_value": (
            outcome.recovered_amount
        ),

        "average_transaction_value": (
            average_transaction_value
        ),

        "guardrail_decision": (
            execution.status
        ),

        "guardrail_reason": (
            execution.stop_reason
        ),

        "recovery_healthy": (
            recovery_healthy
        ),

        "rollback_required": (
            rollback_required
        ),
    }

    # ---------------------------------------------------------
    # Write using the existing audit logger
    # ---------------------------------------------------------

    return log_recovery_event(
        incident=incident,
        recovery=recovery,
        policy_result=policy_result,
        batch_result=batch_result,
    )