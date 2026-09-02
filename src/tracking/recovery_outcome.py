from dataclasses import dataclass
from typing import List


@dataclass
class RecoveryOutcome:
    """
    Measured outcome of a bounded recovery execution.
    """

    attempted_transactions: int
    successful_recoveries: int
    failed_recoveries: int

    attempted_amount: float
    recovered_amount: float

    execution_cost: float
    net_recovered_value: float

    recovery_rate: float
    outcome_status: str
    explanation: str


class RecoveryOutcomeVerifier:
    """
    Converts an execution result into a measurable financial outcome.

    This verifier does not execute payments.
    It only evaluates the result of an execution.
    """

    def verify(
        self,
        transaction_amounts: List[float],
        successful_recoveries: int,
        failed_recoveries: int,
        execution_cost: float,
    ) -> RecoveryOutcome:

        # ---------------------------------------------------------
        # Validate inputs
        # ---------------------------------------------------------

        if any(amount < 0 for amount in transaction_amounts):
            raise ValueError(
                "Transaction amounts cannot be negative."
            )

        if successful_recoveries < 0:
            raise ValueError(
                "Successful recoveries cannot be negative."
            )

        if failed_recoveries < 0:
            raise ValueError(
                "Failed recoveries cannot be negative."
            )

        if execution_cost < 0:
            raise ValueError(
                "Execution cost cannot be negative."
            )

        attempted_transactions = (
            successful_recoveries + failed_recoveries
        )

        # ---------------------------------------------------------
        # Make sure execution counts are consistent.
        # ---------------------------------------------------------

        if attempted_transactions > len(transaction_amounts):
            raise ValueError(
                "Recovery counts exceed available transactions."
            )

        # Only transactions actually attempted are considered.
        attempted_amounts = transaction_amounts[
            :attempted_transactions
        ]

        attempted_amount = sum(attempted_amounts)

        # ---------------------------------------------------------
        # Calculate recovered amount.
        #
        # Successful transactions are taken from the beginning
        # of the attempted batch for deterministic simulation.
        # ---------------------------------------------------------

        recovered_amount = sum(
            attempted_amounts[:successful_recoveries]
        )

        # ---------------------------------------------------------
        # Financial outcome
        # ---------------------------------------------------------

        net_recovered_value = (
            recovered_amount - execution_cost
        )

        if attempted_transactions == 0:
            recovery_rate = 0.0
            outcome_status = "NO_EXECUTION"
            explanation = (
                "No recovery transactions were executed."
            )

        else:
            recovery_rate = (
                successful_recoveries
                / attempted_transactions
            )

            if successful_recoveries == 0:
                outcome_status = "NO_RECOVERY"

                explanation = (
                    "Recovery execution completed, "
                    "but no transactions were recovered."
                )

            elif net_recovered_value <= 0:
                outcome_status = "UNPROFITABLE"

                explanation = (
                    "Recovery generated recovered value, "
                    "but execution cost eliminated the "
                    "financial benefit."
                )

            else:
                outcome_status = "RECOVERED"

                explanation = (
                    "Recovery generated measurable "
                    "positive net recovered value."
                )

        return RecoveryOutcome(
            attempted_transactions=attempted_transactions,
            successful_recoveries=successful_recoveries,
            failed_recoveries=failed_recoveries,
            attempted_amount=round(
                attempted_amount,
                2,
            ),
            recovered_amount=round(
                recovered_amount,
                2,
            ),
            execution_cost=round(
                execution_cost,
                2,
            ),
            net_recovered_value=round(
                net_recovered_value,
                2,
            ),
            recovery_rate=round(
                recovery_rate,
                4,
            ),
            outcome_status=outcome_status,
            explanation=explanation,
        )