from dataclasses import dataclass, field
from typing import List


@dataclass
class RecoveryExecutionResult:
    """
    Result of a bounded recovery execution.

    This executor is simulation-only. It does not call any
    payment gateway and does not move real money.
    """

    action: str
    status: str

    attempted_transactions: int
    successful_recoveries: int
    failed_recoveries: int

    recovery_budget: float
    estimated_cost: float

    stop_reason: str
    execution_log: List[str]
    successful_transaction_amounts: List[float] = field(default_factory=list)


class BoundedRecoveryExecutor:
    """
    Executes a recovery decision inside strict safety boundaries.

    The executor supports simulation/canary execution only.

    Safety boundaries:
    - maximum transaction count
    - maximum monetary budget
    - canary percentage
    - deterministic stop conditions

    It never performs real payment operations.
    """

    DEFAULT_MAX_TRANSACTIONS = 50
    DEFAULT_RECOVERY_BUDGET = 5000.0
    DEFAULT_CANARY_PERCENTAGE = 0.10

    def __init__(
        self,
        max_transactions: int = DEFAULT_MAX_TRANSACTIONS,
        recovery_budget: float = DEFAULT_RECOVERY_BUDGET,
        canary_percentage: float = DEFAULT_CANARY_PERCENTAGE,
    ):
        if max_transactions <= 0:
            raise ValueError(
                "max_transactions must be greater than zero."
            )

        if recovery_budget < 0:
            raise ValueError(
                "recovery_budget cannot be negative."
            )

        if not 0 < canary_percentage <= 1:
            raise ValueError(
                "canary_percentage must be between 0 and 1."
            )

        self.max_transactions = max_transactions
        self.recovery_budget = recovery_budget
        self.canary_percentage = canary_percentage

    def execute(
        self,
        action: str,
        transaction_amounts: List[float],
        simulated_success_rate: float,
    ) -> RecoveryExecutionResult:

        # ---------------------------------------------------------
        # Validate inputs
        # ---------------------------------------------------------

        if not action:
            raise ValueError(
                "Recovery action cannot be empty."
            )

        if simulated_success_rate < 0:
            raise ValueError(
                "simulated_success_rate cannot be negative."
            )

        if simulated_success_rate > 1:
            raise ValueError(
                "simulated_success_rate cannot exceed 1."
            )

        if any(amount < 0 for amount in transaction_amounts):
            raise ValueError(
                "Transaction amounts cannot be negative."
            )

        # ---------------------------------------------------------
        # MONITOR means no execution
        # ---------------------------------------------------------

        if action == "MONITOR":
            return RecoveryExecutionResult(
                action=action,
                status="NOT_EXECUTED",
                attempted_transactions=0,
                successful_recoveries=0,
                failed_recoveries=0,
                recovery_budget=self.recovery_budget,
                estimated_cost=0.0,
                stop_reason=(
                    "Recovery execution was not authorized. "
                    "System remains in monitoring mode."
                ),
                execution_log=[
                    "Action MONITOR received.",
                    "No recovery transactions executed.",
                ],
                successful_transaction_amounts=[],
            )

        # ---------------------------------------------------------
        # Determine bounded execution size
        # ---------------------------------------------------------

        available_transactions = len(transaction_amounts)

        canary_count = max(
            1,
            int(
                available_transactions
                * self.canary_percentage
            ),
        )

        execution_limit = min(
            canary_count,
            self.max_transactions,
            available_transactions,
        )

        selected_amounts = transaction_amounts[
            :execution_limit
        ]

        execution_log = [
            f"Action received: {action}",
            (
                f"Canary percentage: "
                f"{self.canary_percentage:.0%}"
            ),
            (
                f"Maximum transactions: "
                f"{self.max_transactions}"
            ),
            (
                f"Recovery budget: "
                f"₹{self.recovery_budget:,.2f}"
            ),
        ]

        # ---------------------------------------------------------
        # Execute bounded simulation
        # ---------------------------------------------------------

        attempted_transactions = 0
        successful_recoveries = 0
        failed_recoveries = 0
        estimated_cost = 0.0
        successful_transaction_amounts = []

        for index, amount in enumerate(
            selected_amounts,
            start=1,
        ):

            # -----------------------------------------------------
            # Stop if the next transaction exceeds budget.
            #
            # Simulation assumes a fixed execution cost of ₹25.
            # -----------------------------------------------------

            transaction_cost = 25.0

            if (
                estimated_cost + transaction_cost
                > self.recovery_budget
            ):
                execution_log.append(
                    "Recovery budget reached."
                )

                break

            attempted_transactions += 1
            estimated_cost += transaction_cost

            # -----------------------------------------------------
            # Deterministic simulation
            #
            # This avoids random results and makes the demo
            # reproducible.
            # -----------------------------------------------------

            success_threshold = (
                simulated_success_rate
                * 100
            )

            simulated_score = (
                (index * 37) % 100
            )

            if simulated_score < success_threshold:
                successful_recoveries += 1
                successful_transaction_amounts.append(float(amount))
            else:
                failed_recoveries += 1

            # -----------------------------------------------------
            # Stop condition: too many failures
            # -----------------------------------------------------

            if attempted_transactions >= 5:
                failure_rate = (
                    failed_recoveries
                    / attempted_transactions
                )

                if failure_rate > 0.50:
                    execution_log.append(
                        (
                            "Stop condition triggered: "
                            "simulated failure rate exceeded 50%."
                        )
                    )

                    break

        # ---------------------------------------------------------
        # Determine final execution status
        # ---------------------------------------------------------

        if attempted_transactions == 0:
            status = "NOT_EXECUTED"

            stop_reason = (
                "No transaction could be executed within "
                "the configured recovery budget."
            )

        elif (
            failed_recoveries
            / attempted_transactions
            > 0.50
        ):
            status = "STOPPED"

            stop_reason = (
                "Recovery stopped because the simulated "
                "failure rate exceeded the safety threshold."
            )

        elif attempted_transactions >= self.max_transactions:
            status = "COMPLETED"

            stop_reason = (
                "Maximum transaction limit reached."
            )

        elif attempted_transactions == len(selected_amounts):
            status = "COMPLETED"

            stop_reason = (
                "Bounded canary execution completed."
            )

        else:
            status = "STOPPED"

            stop_reason = (
                "Execution stopped by a configured "
                "safety boundary."
            )

        execution_log.append(
            (
                f"Attempted: {attempted_transactions}, "
                f"successful: {successful_recoveries}, "
                f"failed: {failed_recoveries}."
            )
        )

        execution_log.append(
            f"Final status: {status}."
        )

        return RecoveryExecutionResult(
            action=action,
            status=status,
            attempted_transactions=attempted_transactions,
            successful_recoveries=successful_recoveries,
            failed_recoveries=failed_recoveries,
            recovery_budget=self.recovery_budget,
            estimated_cost=round(
                estimated_cost,
                2,
            ),
            stop_reason=stop_reason,
            execution_log=execution_log,
            successful_transaction_amounts=successful_transaction_amounts,
        )
