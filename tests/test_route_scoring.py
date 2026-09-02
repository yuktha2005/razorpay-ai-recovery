from src.intelligence.route_scoring import (
    RouteScorer,
    rank_routes,
)


def test_small_sample_is_not_treated_as_certain():

    scorer = RouteScorer()

    result = scorer.score(
        route="UPI + Bank_A + Android",
        transactions=3,
        successes=3,
    )

    assert result.observed_success_rate == 1.0
    assert result.adjusted_success_rate < 1.0
    assert result.evidence_confidence < 0.2


def test_large_sample_has_stronger_evidence():

    scorer = RouteScorer()

    result = scorer.score(
        route="UPI + Bank_X + Android",
        transactions=508,
        successes=353,
    )

    assert result.transactions == 508
    assert result.observed_success_rate < 0.70
    assert result.evidence_confidence > 0.9


def test_ranking_considers_evidence():

    routes = [
        {
            "route": "UPI + Bank_A + Android",
            "transactions": 3,
            "successes": 3,
        },
        {
            "route": "UPI + Bank_C + Android",
            "transactions": 8,
            "successes": 7,
        },
    ]

    ranked = rank_routes(routes)

    assert len(ranked) == 2
    assert ranked[0].route == "UPI + Bank_C + Android" 

def test_zero_transactions_are_safe():

    scorer = RouteScorer()

    result = scorer.score(
        route="UPI + Unknown + Android",
        transactions=0,
        successes=0,
    )

    assert result.score == 0.0
    assert result.evidence_confidence == 0.0