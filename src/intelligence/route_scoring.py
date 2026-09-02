from dataclasses import dataclass
from math import sqrt


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


class RouteScorer:
    """
    Scores alternative payment routes using both performance
    and evidence volume.

    The goal is to avoid selecting a route merely because it
    has a perfect success rate on a tiny number of transactions.
    """

    PRIOR_SUCCESS_RATE = 0.94

    def score(
        self,
        route: str,
        transactions: int,
        successes: int,
    ) -> RouteScore:

        if transactions <= 0:
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
            )

        transactions = int(transactions)
        successes = min(max(int(successes), 0), transactions)

        observed_rate = successes / transactions

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
            transactions / (transactions + 100)
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
                successes
                + self.PRIOR_SUCCESS_RATE * prior_weight
            )
            / (transactions + prior_weight)
        )

        # ---------------------------------------------------------
        # Final route score
        # ---------------------------------------------------------
        #
        # Performance matters, but evidence confidence also matters.
        # ---------------------------------------------------------

        score = adjusted_rate * evidence_confidence

        if transactions < 10:
            evidence_description = "very limited"
        elif transactions < 50:
            evidence_description = "limited"
        elif transactions < 200:
            evidence_description = "moderate"
        else:
            evidence_description = "strong"

        explanation = (
            f"Observed success rate is {observed_rate:.2%}, "
            f"adjusted to {adjusted_rate:.2%} using a healthy-route "
            f"prior. Evidence volume is {evidence_description} "
            f"({transactions} transactions), producing "
            f"{evidence_confidence:.2%} evidence confidence."
        )

        return RouteScore(
            route=route,
            transactions=transactions,
            successes=successes,
            observed_success_rate=round(observed_rate, 6),
            adjusted_success_rate=round(adjusted_rate, 6),
            evidence_confidence=round(evidence_confidence, 6),
            score=round(score, 6),
            explanation=explanation,
        )


def rank_routes(routes):
    """
    Score and rank multiple alternative routes.

    Expected input:

    [
        {
            "route": "UPI + Bank_A + Android",
            "transactions": 3,
            "successes": 3,
        },
        ...
    ]
    """

    scorer = RouteScorer()

    results = []

    for route in routes:
        result = scorer.score(
            route=route["route"],
            transactions=route["transactions"],
            successes=route["successes"],
        )

        results.append(result)

    return sorted(
        results,
        key=lambda result: result.score,
        reverse=True,
    )