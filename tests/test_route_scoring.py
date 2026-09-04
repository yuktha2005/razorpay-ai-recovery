from src.intelligence.route_scoring import (
    RouteScorer,
    RouteScore,
    rank_routes,
)
from src.tracking.recovery_learning import (
    RecoveryLearningEngine,
    RouteLearningStats,
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


# =========================================================
# Milestone 3: Learning Evidence Blending Tests
# =========================================================


def test_backward_compatibility_rank_routes():
    """A. Backward compatibility: rank_routes(routes) produces identical results when learning is None."""
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

    ranked_default = rank_routes(routes)
    ranked_explicit_none = rank_routes(routes, learning_history=None)

    assert len(ranked_default) == len(ranked_explicit_none)
    for r1, r2 in zip(ranked_default, ranked_explicit_none):
        assert r1.route == r2.route
        assert r1.score == r2.score
        assert r1.transactions == r2.transactions
        assert r1.successes == r2.successes
        assert r1.explanation == r2.explanation
        assert r1.learned_attempts == 0
        assert r1.learned_recoveries == 0


def test_no_matching_learning_history():
    """B. No matching learning history: score remains unchanged."""
    scorer = RouteScorer()

    baseline = scorer.score(
        route="UPI + Bank_A + Android",
        transactions=50,
        successes=40,
    )

    # Passing stats with a non-matching route name
    unmatched_stats = RouteLearningStats(
        route="UPI + Bank_B + Android",
        attempts=25,
        recoveries=22,
        recovery_rate=0.88,
        total_recovered_value=22000.0,
        total_execution_cost=550.0,
        net_recovered_value=21450.0,
        evidence_confidence=0.71,
    )

    result = scorer.score(
        route="UPI + Bank_A + Android",
        transactions=50,
        successes=40,
        learning_stats=unmatched_stats,
    )

    assert result.score == baseline.score
    assert result.transactions == baseline.transactions
    assert result.successes == baseline.successes
    assert result.explanation == baseline.explanation
    assert result.learned_attempts == 0
    assert result.learned_recoveries == 0


def test_positive_learning_evidence_improves_score():
    """C. Positive learning evidence: strong recovery history yields a higher score."""
    scorer = RouteScorer()

    # Small sample without learning: high rate but low confidence
    baseline = scorer.score(
        route="UPI + Bank_A + Android",
        transactions=3,
        successes=3,
    )

    # Add verified recovery evidence: 50 attempts, 48 recoveries
    stats = {
        "route": "UPI + Bank_A + Android",
        "attempts": 50,
        "recoveries": 48,
    }

    learned_result = scorer.score(
        route="UPI + Bank_A + Android",
        transactions=3,
        successes=3,
        learning_stats=stats,
    )

    assert learned_result.score > baseline.score
    assert learned_result.evidence_confidence > baseline.evidence_confidence
    assert learned_result.transactions == 53
    assert learned_result.successes == 51
    assert learned_result.learned_attempts == 50
    assert learned_result.learned_recoveries == 48
    assert "Score incorporates 50 verified recovery attempts with 48 recoveries" in learned_result.explanation


def test_learned_evidence_blended_correctly():
    """D. Learned evidence is blended correctly:
    observed: 50 txns / 40 succ
    learned: 20 attempts / 18 succ
    effective: 70 txns / 58 succ -> matches baseline scorer using 70/58.
    """
    scorer = RouteScorer()

    learned_stats = {
        "route": "UPI + Bank_B + Android",
        "attempts": 20,
        "recoveries": 18,
    }

    blended_result = scorer.score(
        route="UPI + Bank_B + Android",
        transactions=50,
        successes=40,
        learning_stats=learned_stats,
    )

    expected_70_58 = scorer.score(
        route="UPI + Bank_B + Android",
        transactions=70,
        successes=58,
    )

    assert blended_result.transactions == 70
    assert blended_result.successes == 58
    assert blended_result.observed_success_rate == expected_70_58.observed_success_rate
    assert blended_result.adjusted_success_rate == expected_70_58.adjusted_success_rate
    assert blended_result.evidence_confidence == expected_70_58.evidence_confidence
    assert blended_result.score == expected_70_58.score
    assert blended_result.learned_attempts == 20
    assert blended_result.learned_recoveries == 18
    assert "Score incorporates 20 verified recovery attempts with 18 recoveries" in blended_result.explanation


def test_invalid_learning_evidence_ignored():
    """E. Invalid learning evidence (attempts <= 0, recoveries > attempts, negative values)
    must not alter the baseline score.
    """
    scorer = RouteScorer()

    baseline = scorer.score(
        route="UPI + Bank_X + Android",
        transactions=100,
        successes=85,
    )

    invalid_cases = [
        {"route": "UPI + Bank_X + Android", "attempts": 0, "recoveries": 0},
        {"route": "UPI + Bank_X + Android", "attempts": -10, "recoveries": 5},
        {"route": "UPI + Bank_X + Android", "attempts": 20, "recoveries": -3},
        {"route": "UPI + Bank_X + Android", "attempts": 20, "recoveries": 25},  # rec > att
        {"route": "UPI + Bank_X + Android", "attempts": "invalid", "recoveries": 5},
        {"route": "UPI + Bank_X + Android", "attempts": None, "recoveries": None},
    ]

    for bad_stats in invalid_cases:
        res = scorer.score(
            route="UPI + Bank_X + Android",
            transactions=100,
            successes=85,
            learning_stats=bad_stats,
        )
        assert res.score == baseline.score
        assert res.transactions == baseline.transactions
        assert res.successes == baseline.successes
        assert res.explanation == baseline.explanation
        assert res.learned_attempts == 0
        assert res.learned_recoveries == 0


def test_route_isolation():
    """F. Route isolation: Learning evidence for Route B must not affect Route A."""
    routes = [
        {
            "route": "UPI + Bank_A + Android",
            "transactions": 50,
            "successes": 40,
        },
        {
            "route": "UPI + Bank_B + Android",
            "transactions": 20,
            "successes": 15,
        },
    ]

    # Only provide learning history for Route B
    learning_history = {
        "UPI + Bank_B + Android": RouteLearningStats(
            route="UPI + Bank_B + Android",
            attempts=30,
            recoveries=28,
            recovery_rate=0.85,
            total_recovered_value=28000.0,
            total_execution_cost=700.0,
            net_recovered_value=27300.0,
            evidence_confidence=0.75,
        )
    }

    scorer = RouteScorer()
    baseline_a = scorer.score("UPI + Bank_A + Android", 50, 40)
    expected_b_blended = scorer.score("UPI + Bank_B + Android", 50, 43)

    ranked = rank_routes(routes, learning_history=learning_history)

    route_a_res = next(r for r in ranked if r.route == "UPI + Bank_A + Android")
    route_b_res = next(r for r in ranked if r.route == "UPI + Bank_B + Android")

    # Route A is untouched
    assert route_a_res.score == baseline_a.score
    assert route_a_res.transactions == 50
    assert route_a_res.successes == 40
    assert route_a_res.learned_attempts == 0

    # Route B is updated by 30 attempts, 28 recoveries (20+30=50, 15+28=43)
    assert route_b_res.score == expected_b_blended.score
    assert route_b_res.transactions == 50
    assert route_b_res.successes == 43
    assert route_b_res.learned_attempts == 30
    assert route_b_res.learned_recoveries == 28


def test_determinism_with_learning_history():
    """G. Determinism: Same routes + same learning history yields identical results."""
    routes = [
        {
            "route": "UPI + Bank_A + Android",
            "transactions": 10,
            "successes": 9,
        },
        {
            "route": "UPI + Bank_B + Android",
            "transactions": 12,
            "successes": 11,
        },
    ]

    learning_history = [
        RouteLearningStats(
            route="UPI + Bank_A + Android",
            attempts=15,
            recoveries=14,
            recovery_rate=0.86,
            total_recovered_value=14000.0,
            total_execution_cost=375.0,
            net_recovered_value=13625.0,
            evidence_confidence=0.60,
        )
    ]

    run1 = rank_routes(routes, learning_history=learning_history)
    run2 = rank_routes(routes, learning_history=learning_history)

    assert len(run1) == len(run2)
    for r1, r2 in zip(run1, run2):
        assert r1.route == r2.route
        assert r1.score == r2.score
        assert r1.transactions == r2.transactions
        assert r1.successes == r2.successes
        assert r1.explanation == r2.explanation
        assert r1.learned_attempts == r2.learned_attempts
        assert r1.learned_recoveries == r2.learned_recoveries


def test_integration_with_recovery_learning_engine():
    """Verify rank_routes works directly with a RecoveryLearningEngine instance."""
    engine = RecoveryLearningEngine()
    engine.record(
        route="UPI + Bank_A + Android",
        attempted_transactions=25,
        successful_recoveries=24,
        recovered_value=24000.0,
        execution_cost=625.0,
    )

    routes = [
        {"route": "UPI + Bank_A + Android", "transactions": 5, "successes": 4},
        {"route": "UPI + Bank_B + Android", "transactions": 30, "successes": 27},
    ]

    ranked = rank_routes(routes, learning_history=engine)

    route_a_res = next(r for r in ranked if r.route == "UPI + Bank_A + Android")
    assert route_a_res.transactions == 30  # 5 observed + 25 learned
    assert route_a_res.successes == 28     # 4 observed + 24 learned
    assert route_a_res.learned_attempts == 25
    assert route_a_res.learned_recoveries == 24