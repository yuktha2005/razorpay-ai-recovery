from dataclasses import dataclass
from math import sqrt
from typing import Any, Dict, List, Optional

from src.tracking.recovery_learning import RouteLearningStats


@dataclass
class RouteScore:
    """
    Evidence-adjusted assessment of an alternative payment route.
    """

    route: str
    transactions: int
    successes: int
    observed_success_rate: float
    adjusted_success_rate: float
    evidence_confidence: float
    score: float
    explanation: str
    learned_attempts: int = 0
    learned_recoveries: int = 0


class RouteScorer:
    """
    Scores alternative payment routes using both performance
    and evidence volume.

    The goal is to avoid selecting a route merely because it
    has a perfect success rate on a tiny number of transactions.
    Optionally blends verified historical recovery evidence.
    """

    PRIOR_SUCCESS_RATE = 0.94

    def score(
        self,
        route: str,
        transactions: int,
        successes: int,
        learning_stats: Optional[Any] = None,
    ) -> RouteScore:

        base_transactions = int(transactions) if transactions is not None else 0
        base_successes = (
            min(max(int(successes), 0), max(0, base_transactions))
            if successes is not None
            else 0
        )

        # ---------------------------------------------------------
        # Validate optional historical learning evidence
        # ---------------------------------------------------------
        has_valid_learning = False
        learned_attempts = 0
        learned_recoveries = 0

        if learning_stats is not None:
            stats_route = getattr(learning_stats, "route", None)
            if stats_route is None and isinstance(learning_stats, dict):
                stats_route = learning_stats.get("route")

            route_matches = True
            if stats_route is not None and str(stats_route).strip() != str(route).strip():
                route_matches = False

            if route_matches:
                att = getattr(learning_stats, "attempts", None)
                if att is None and isinstance(learning_stats, dict):
                    att = learning_stats.get("attempts")

                rec = getattr(learning_stats, "recoveries", None)
                if rec is None and isinstance(learning_stats, dict):
                    rec = learning_stats.get("recoveries")

                if (
                    isinstance(att, (int, float))
                    and isinstance(rec, (int, float))
                    and att > 0
                    and rec >= 0
                    and rec <= att
                ):
                    has_valid_learning = True
                    learned_attempts = int(att)
                    learned_recoveries = int(rec)

        # ---------------------------------------------------------
        # Blend verified historical evidence with observed counts
        # ---------------------------------------------------------
        if has_valid_learning:
            effective_transactions = max(0, base_transactions) + learned_attempts
            effective_successes = base_successes + learned_recoveries
        else:
            effective_transactions = max(0, base_transactions)
            effective_successes = base_successes

        if effective_transactions <= 0:
            return RouteScore(
                route=route,
                transactions=0,
                successes=0,
                observed_success_rate=0.0,
                adjusted_success_rate=0.0,
                evidence_confidence=0.0,
                score=0.0,
                explanation=(
                    "Insufficient transaction evidence for this route."
                ),
                learned_attempts=0,
                learned_recoveries=0,
            )

        observed_rate = effective_successes / effective_transactions

        # ---------------------------------------------------------
        # Evidence confidence
        # ---------------------------------------------------------
        #
        # Confidence increases with transaction volume.
        # 100 observations gives approximately 70% confidence.
        # More observations gradually approach 100%.
        #
        # This intentionally prevents tiny samples such as 3/3
        # from dominating larger evidence sets.
        # ---------------------------------------------------------

        evidence_confidence = sqrt(
            effective_transactions / (effective_transactions + 100)
        )

        # ---------------------------------------------------------
        # Bayesian-style shrinkage toward a normal route prior.
        #
        # The prior represents expected healthy payment behavior.
        # It prevents very small samples from being treated as
        # statistically certain.
        # ---------------------------------------------------------

        prior_weight = 100

        adjusted_rate = (
            (
                effective_successes
                + self.PRIOR_SUCCESS_RATE * prior_weight
            )
            / (effective_transactions + prior_weight)
        )

        # ---------------------------------------------------------
        # Final route score
        # ---------------------------------------------------------
        #
        # Performance matters, but evidence confidence also matters.
        # ---------------------------------------------------------

        score = adjusted_rate * evidence_confidence

        if effective_transactions < 10:
            evidence_description = "very limited"
        elif effective_transactions < 50:
            evidence_description = "limited"
        elif effective_transactions < 200:
            evidence_description = "moderate"
        else:
            evidence_description = "strong"

        explanation = (
            f"Observed success rate is {observed_rate:.2%}, "
            f"adjusted to {adjusted_rate:.2%} using a healthy-route "
            f"prior. Evidence volume is {evidence_description} "
            f"({effective_transactions} transactions), producing "
            f"{evidence_confidence:.2%} evidence confidence."
        )

        if has_valid_learning:
            explanation += (
                f" Score incorporates {learned_attempts} verified recovery "
                f"attempts with {learned_recoveries} recoveries "
                f"(outcome-based route intelligence via Bayesian evidence update)."
            )

        return RouteScore(
            route=route,
            transactions=effective_transactions,
            successes=effective_successes,
            observed_success_rate=round(observed_rate, 6),
            adjusted_success_rate=round(adjusted_rate, 6),
            evidence_confidence=round(evidence_confidence, 6),
            score=round(score, 6),
            explanation=explanation,
            learned_attempts=learned_attempts,
            learned_recoveries=learned_recoveries,
        )


def rank_routes(
    routes: List[Dict[str, Any]],
    learning_history: Optional[Any] = None,
) -> List[RouteScore]:
    """
    Score and rank multiple alternative routes, optionally incorporating
    verified historical recovery evidence.

    Expected input for routes:

    [
        {
            "route": "UPI + Bank_A + Android",
            "transactions": 3,
            "successes": 3,
        },
        ...
    ]

    learning_history: Optional collection of learned route statistics.
    Supported types:
    - None: standard scoring without recovery learning.
    - Dict[str, RouteLearningStats | Dict]: keyed by route name.
    - List[RouteLearningStats | Dict]: list of stats objects/dicts with route property.
    - Object with get_route(route) method (e.g. PersistentLearningHistory, RecoveryLearningEngine).
    """

    scorer = RouteScorer()

    # Pre-index learning history if it's a list for O(1) lookup
    history_map: Optional[Dict[str, Any]] = None
    get_route_fn = None

    if learning_history is not None:
        if hasattr(learning_history, "get_route") and callable(learning_history.get_route):
            get_route_fn = learning_history.get_route
        elif isinstance(learning_history, dict):
            history_map = learning_history
        elif isinstance(learning_history, (list, tuple)):
            history_map = {}
            for item in learning_history:
                r_name = getattr(item, "route", None)
                if r_name is None and isinstance(item, dict):
                    r_name = item.get("route")
                if r_name:
                    history_map[str(r_name).strip()] = item

    results = []

    for route_info in routes:
        route_name = route_info["route"]
        txns = route_info["transactions"]
        succs = route_info["successes"]

        # Look up learning stats
        stats = None
        if get_route_fn is not None:
            stats = get_route_fn(route_name)
        elif history_map is not None:
            stats = history_map.get(str(route_name).strip())

        # Fallback to route_info dict if learning_stats is attached directly
        if stats is None and "learning_stats" in route_info:
            stats = route_info["learning_stats"]

        result = scorer.score(
            route=route_name,
            transactions=txns,
            successes=succs,
            learning_stats=stats,
        )

        results.append(result)

    return sorted(
        results,
        key=lambda result: result.score,
        reverse=True,
    )