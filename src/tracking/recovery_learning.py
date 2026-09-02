from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RouteLearningStats:
    """
    Historical recovery performance for one route.
    """

    route: str
    attempts: int
    recoveries: int
    recovery_rate: float
    total_recovered_value: float
    total_execution_cost: float
    net_recovered_value: float
    evidence_confidence: float


class RecoveryLearningEngine:
    """
    Learns route performance from verified recovery outcomes.

    This component maintains historical evidence that can
    later be used by the route-ranking layer.
    """

    PRIOR_RECOVERY_RATE = 0.50
    PRIOR_WEIGHT = 10

    def __init__(self):
        self._routes: Dict[str, RouteLearningStats] = {}

    def restore(self, stats: RouteLearningStats) -> None:
        """
        Restore previously persisted statistics into memory.
        """
        if not stats.route:
            raise ValueError("route is required")

        if stats.attempts < 0:
            raise ValueError("attempts cannot be negative")

        if stats.recoveries < 0:
            raise ValueError("recoveries cannot be negative")

        if stats.recoveries > stats.attempts:
            raise ValueError(
                "recoveries cannot exceed attempts"
            )

        self._routes[stats.route] = stats

    def record(
        self,
        route: str,
        attempted_transactions: int,
        successful_recoveries: int,
        recovered_value: float,
        execution_cost: float,
    ) -> RouteLearningStats:

        if not route:
            raise ValueError("route is required")

        if attempted_transactions < 0:
            raise ValueError(
                "attempted_transactions cannot be negative"
            )

        if successful_recoveries < 0:
            raise ValueError(
                "successful_recoveries cannot be negative"
            )

        if successful_recoveries > attempted_transactions:
            raise ValueError(
                "successful_recoveries cannot exceed "
                "attempted_transactions"
            )

        if recovered_value < 0:
            raise ValueError(
                "recovered_value cannot be negative"
            )

        if execution_cost < 0:
            raise ValueError(
                "execution_cost cannot be negative"
            )

        existing = self._routes.get(route)

        previous_attempts = (
            existing.attempts if existing else 0
        )

        previous_recoveries = (
            existing.recoveries if existing else 0
        )

        previous_recovered_value = (
            existing.total_recovered_value
            if existing
            else 0.0
        )

        previous_execution_cost = (
            existing.total_execution_cost
            if existing
            else 0.0
        )

        total_attempts = (
            previous_attempts + attempted_transactions
        )

        total_recoveries = (
            previous_recoveries + successful_recoveries
        )

        total_recovered_value = (
            previous_recovered_value + recovered_value
        )

        total_execution_cost = (
            previous_execution_cost + execution_cost
        )

        if total_attempts > 0:
            raw_recovery_rate = (
                total_recoveries / total_attempts
            )
        else:
            raw_recovery_rate = 0.0

        recovery_rate = (
            (
                total_recoveries
                + self.PRIOR_RECOVERY_RATE
                * self.PRIOR_WEIGHT
            )
            / (total_attempts + self.PRIOR_WEIGHT)
        )

        evidence_confidence = (
            total_attempts
            / (total_attempts + self.PRIOR_WEIGHT)
        )

        net_recovered_value = (
            total_recovered_value
            - total_execution_cost
        )

        stats = RouteLearningStats(
            route=route,
            attempts=total_attempts,
            recoveries=total_recoveries,
            recovery_rate=recovery_rate,
            total_recovered_value=round(
                total_recovered_value,
                2,
            ),
            total_execution_cost=round(
                total_execution_cost,
                2,
            ),
            net_recovered_value=round(
                net_recovered_value,
                2,
            ),
            evidence_confidence=evidence_confidence,
        )

        self._routes[route] = stats

        return stats

    def get_route(
        self,
        route: str,
    ) -> RouteLearningStats | None:
        return self._routes.get(route)

    def rank_routes(self) -> List[RouteLearningStats]:
        return sorted(
            self._routes.values(),
            key=lambda item: (
                item.recovery_rate
                * item.evidence_confidence,
                item.net_recovered_value,
            ),
            reverse=True,
        )