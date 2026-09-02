from typing import Dict, List

from src.tracking.learning_store import (
    load_learning_history,
)
from src.tracking.recovery_learning import (
    RouteLearningStats,
)


class PersistentLearningHistory:
    """
    Reconstruct route-level learning statistics from the
    persistent recovery-learning CSV.

    The loader is read-only. It does not modify the learning
    history.
    """

    def load(self) -> List[RouteLearningStats]:
        """
        Load all persisted route observations and return the
        latest aggregate statistics for each route.
        """

        history = load_learning_history()

        routes: Dict[str, RouteLearningStats] = {}

        for row in history:

            route = row.get("route", "").strip()

            if not route:
                continue

            attempts = self._to_int(
                row.get("attempts", 0)
            )

            recoveries = self._to_int(
                row.get("recoveries", 0)
            )

            recovered_value = self._to_float(
                row.get("recovered_value", 0)
            )

            execution_cost = self._to_float(
                row.get("execution_cost", 0)
            )

            recovery_rate = self._to_float(
                row.get("recovery_rate", 0)
            )

            evidence_confidence = self._to_float(
                row.get("evidence_confidence", 0)
            )

            net_recovered_value = (
                recovered_value
                - execution_cost
            )

            routes[route] = RouteLearningStats(
                route=route,
                attempts=attempts,
                recoveries=recoveries,
                recovery_rate=recovery_rate,
                total_recovered_value=round(
                    recovered_value,
                    2,
                ),
                total_execution_cost=round(
                    execution_cost,
                    2,
                ),
                net_recovered_value=round(
                    net_recovered_value,
                    2,
                ),
                evidence_confidence=evidence_confidence,
            )

        return list(routes.values())

    def get_route(
        self,
        route: str,
    ) -> RouteLearningStats | None:
        """
        Return persisted statistics for one route.
        """

        routes = self.load()

        for stats in routes:

            if stats.route == route:
                return stats

        return None

    def rank_routes(
        self,
    ) -> List[RouteLearningStats]:
        """
        Rank persisted routes by recovery performance
        and evidence confidence.
        """

        routes = self.load()

        return sorted(
            routes,
            key=lambda item: (
                item.recovery_rate
                * item.evidence_confidence,
                item.net_recovered_value,
            ),
            reverse=True,
        )

    @staticmethod
    def _to_int(value) -> int:

        try:
            return int(float(value))
        except (
            TypeError,
            ValueError,
        ):
            return 0

    @staticmethod
    def _to_float(value) -> float:

        try:
            return float(value)
        except (
            TypeError,
            ValueError,
        ):
            return 0.0