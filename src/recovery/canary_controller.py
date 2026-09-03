from dataclasses import dataclass


@dataclass
class CanaryDecision:
    decision: str
    canary_recovery_rate: float
    expected_recovery_rate: float
    reason: str


class CanaryController:
    """
    Decides what to do after a bounded recovery canary.

    Possible decisions:
    - EXPAND
    - STOP
    - ESCALATE
    """

    MIN_CANARY_ATTEMPTS = 5
    EXPAND_RATIO = 0.80
    ESCALATE_RATIO = 0.50

    def evaluate(
        self,
        attempted_transactions: int,
        successful_recoveries: int,
        expected_recovery_rate: float,
    ) -> CanaryDecision:

        if attempted_transactions <= 0:
            return CanaryDecision(
                decision="STOP",
                canary_recovery_rate=0.0,
                expected_recovery_rate=expected_recovery_rate,
                reason="No canary transactions were executed.",
            )

        canary_rate = (
            successful_recoveries / attempted_transactions
        )

        if attempted_transactions < self.MIN_CANARY_ATTEMPTS:
            return CanaryDecision(
                decision="STOP",
                canary_recovery_rate=canary_rate,
                expected_recovery_rate=expected_recovery_rate,
                reason=(
                    "Canary sample is too small to justify expansion."
                ),
            )

        if canary_rate >= expected_recovery_rate * self.EXPAND_RATIO:
            return CanaryDecision(
                decision="EXPAND",
                canary_recovery_rate=canary_rate,
                expected_recovery_rate=expected_recovery_rate,
                reason=(
                    "Canary performance is within the approved "
                    "expansion threshold."
                ),
            )

        if canary_rate >= expected_recovery_rate * self.ESCALATE_RATIO:
            return CanaryDecision(
                decision="STOP",
                canary_recovery_rate=canary_rate,
                expected_recovery_rate=expected_recovery_rate,
                reason=(
                    "Canary performance is below the expansion "
                    "threshold. Further execution is stopped."
                ),
            )

        return CanaryDecision(
            decision="ESCALATE",
            canary_recovery_rate=canary_rate,
            expected_recovery_rate=expected_recovery_rate,
            reason=(
                "Canary performance is materially below expectation. "
                "Human review is required."
            ),
        )