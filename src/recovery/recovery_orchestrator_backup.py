from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.models.domain import Decision, SafetyDecision
from src.recovery.bounded_executor import (
    BoundedRecoveryExecutor,
    RecoveryExecutionResult,
)
from src.recovery.canary_controller import CanaryController
from src.tracking.learning_history import PersistentLearningHistory
from src.tracking.learning_store import save_route_learning
from src.tracking.recovery_learning import (
    RecoveryLearningEngine,
    RouteLearningStats,
)
from src.tracking.recovery_outcome import (
    RecoveryOutcomeVerifier,
)


@dataclass
class RecoveryOrchestrationResult:
    decision_action: str
    safety_action: str
    safety_allowed: bool
    execution_result: RecoveryExecutionResult
    recovery_outcome: object
    final_status: str
    explanation: str
    canary_decision: str = "PENDING"
    canary_reason: str = ""
    learning_stats: Optional[RouteLearningStats] = None


class RecoveryOrchestrator:
    """
    Coordinates the bounded recovery lifecycle:

        Decision
            ↓
        Safety Gate
            ↓
        Bounded Execution
            ↓
        Outcome Verification
            ↓
        Canary Control
            ↓
        Learning
            ↓
        Persistence

    Recovery execution is simulation-only.
    """

    def __init__(
        self,
        executor: Optional[BoundedRecoveryExecutor] = None,
        outcome_verifier: Optional[
            RecoveryOutcomeVerifier
        ] = None,
        learning_engine: Optional[
            RecoveryLearningEngine
        ] = None,
    ):
        self.executor = (
            executor
            if executor is not None
            else BoundedRecoveryExecutor()
        )

        self.outcome_verifier = (
            outcome_verifier
            if outcome_verifier is not None
            else RecoveryOutcomeVerifier()
        )

        self.learning_engine = (
            learning_engine
            if learning_engine is not None
            else RecoveryLearningEngine()
        )

        self.canary_controller = CanaryController()

        # Restore persisted learning when the application starts.
        self._restore_learning_history()

    def _restore_learning_history(self) -> None:
        """
        Restore previously persisted route statistics
        into the in-memory learning engine.
        """
        history = PersistentLearningHistory()

        for stats in history.load():
            self.learning_engine.restore(stats)

    def execute(
        self,
        decision: Decision,
        safety_decision: SafetyDecision,
        transaction_amounts: list[float],
        simulated_success_rate: float,
    ) -> RecoveryOrchestrationResult:
        """
        Execute a safety-gated recovery decision.
        """

        # ---------------------------------------------------------
        # 1. Safety blocked
        # ---------------------------------------------------------
        if not safety_decision.allowed:

            execution_result = RecoveryExecutionResult(
                action=safety_decision.action,
                status="BLOCKED",
                attempted_transactions=0,
                successful_recoveries=0,
                failed_recoveries=0,
                recovery_budget=0.0,
                estimated_cost=0.0,
                stop_reason=safety_decision.reason,
                execution_log=[],
            )

            recovery_outcome = self.outcome_verifier.verify(
                transaction_amounts=[],
                successful_recoveries=0,
                failed_recoveries=0,
                execution_cost=0.0,
            )

            return RecoveryOrchestrationResult(
                decision_action=decision.recommended_action,
                safety_action=safety_decision.action,
                safety_allowed=False,
                execution_result=execution_result,
                recovery_outcome=recovery_outcome,
                final_status="BLOCKED",
                explanation=safety_decision.reason,
            )

        # ---------------------------------------------------------
        # 2. Monitor-only decision
        # ---------------------------------------------------------
        if safety_decision.action == "MONITOR":

            execution_result = self.executor.execute(
                action="MONITOR",
                transaction_amounts=[],
                simulated_success_rate=simulated_success_rate,
            )

            recovery_outcome = self.outcome_verifier.verify(
                transaction_amounts=[],
                successful_recoveries=0,
                failed_recoveries=0,
                execution_cost=0.0,
            )

            return RecoveryOrchestrationResult(
                decision_action=decision.recommended_action,
                safety_action=safety_decision.action,
                safety_allowed=True,
                execution_result=execution_result,
                recovery_outcome=recovery_outcome,
                final_status="MONITORING",
                explanation=safety_decision.reason,
            )

        # ---------------------------------------------------------
        # 3. Safety action must match recommended action
        # ---------------------------------------------------------
        if (
            safety_decision.action
            != decision.recommended_action
        ):

            reason = (
                "Execution blocked because the safety "
                "action differs from the recommended action."
            )

            execution_result = RecoveryExecutionResult(
                action=safety_decision.action,
                status="BLOCKED",
                attempted_transactions=0,
                successful_recoveries=0,
                failed_recoveries=0,
                recovery_budget=0.0,
                estimated_cost=0.0,
                stop_reason=reason,
                execution_log=[],
            )

            recovery_outcome = self.outcome_verifier.verify(
                transaction_amounts=[],
                successful_recoveries=0,
                failed_recoveries=0,
                execution_cost=0.0,
            )

            return RecoveryOrchestrationResult(
                decision_action=decision.recommended_action,
                safety_action=safety_decision.action,
                safety_allowed=True,
                execution_result=execution_result,
                recovery_outcome=recovery_outcome,
                final_status="BLOCKED",
                explanation=reason,
            )

        # ---------------------------------------------------------
        # 4. Execute bounded recovery
        # ---------------------------------------------------------
        execution_result = self.executor.execute(
            action=safety_decision.action,
            transaction_amounts=transaction_amounts,
            simulated_success_rate=simulated_success_rate,
        )

        # ---------------------------------------------------------
        # 5. Verify recovery outcome
        # ---------------------------------------------------------
        recovery_outcome = self.outcome_verifier.verify(
            transaction_amounts=transaction_amounts[
                :execution_result.attempted_transactions
            ],
            successful_recoveries=(
                execution_result.successful_recoveries
            ),
            failed_recoveries=(
                execution_result.failed_recoveries
            ),
            execution_cost=(
                execution_result.estimated_cost
            ),
        )

        learning_stats = None

        # ---------------------------------------------------------
        # 6. Evaluate bounded recovery canary
        # ---------------------------------------------------------
        canary_result = self.canary_controller.evaluate(
            attempted_transactions=(
                execution_result.attempted_transactions
            ),
            successful_recoveries=(
                execution_result.successful_recoveries
            ),
            expected_recovery_rate=simulated_success_rate,
        )

        # ---------------------------------------------------------
        # 7. Learn from verified route recovery
        # ---------------------------------------------------------
        if (
            execution_result.attempted_transactions > 0
            and safety_decision.action.startswith(
                "ROUTE_SWITCH:"
            )
        ):

            route = safety_decision.action.replace(
                "ROUTE_SWITCH:",
                "",
                1,
            ).strip()

            learning_stats = self.learning_engine.record(
                route=route,
                attempted_transactions=(
                    execution_result.attempted_transactions
                ),
                successful_recoveries=(
                    execution_result.successful_recoveries
                ),
                recovered_value=(
                    recovery_outcome.recovered_amount
                ),
                execution_cost=(
                    execution_result.estimated_cost
                ),
            )

            # Persist cumulative route statistics.
            save_route_learning(
                learning_stats,
                timestamp=datetime.now().isoformat(
                    timespec="seconds"
                ),
            )

        # ---------------------------------------------------------
        # 8. Return result
        # ---------------------------------------------------------
        return RecoveryOrchestrationResult(
            decision_action=decision.recommended_action,
            safety_action=safety_decision.action,
            safety_allowed=True,
            execution_result=execution_result,
            recovery_outcome=recovery_outcome,
            final_status=recovery_outcome.outcome_status,
            explanation=(
                "Recovery executed, verified, and "
                "learning statistics updated."
            ),
            canary_decision=canary_result.decision,
            canary_reason=canary_result.reason,
            learning_stats=learning_stats,
        )