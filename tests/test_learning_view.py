"""
Tests for Learning View Model in Razorpay AI Revenue Recovery.

Verifies the presentation view of closed-loop recovery learning:
- Real verified evidence vs no evidence
- Score delta derivation from authoritative route scoring
- Ranking before/after tracking
- Decision adaptation detection
- Resilience to missing/invalid data and finite values
- Strictly zero side-effects on persistent files
"""

import math
from pathlib import Path
import pytest

from src.demo.demo_scenario import CANONICAL_HAPPY_PATH, DEFAULT_DEMO_CANDIDATES
from src.demo.demo_runner import DemoRunner
from src.intelligence.route_scoring import RouteScorer, rank_routes
from src.tracking.learning_view import (
    LearningComparisonView,
    RouteComparisonItem,
    build_learning_comparison,
)
from src.tracking.recovery_learning import (
    RecoveryLearningEngine,
    RouteLearningStats,
)


@pytest.fixture(autouse=True)
def isolate_persistent_storage(tmp_path, monkeypatch):
    """Ensure tests run against isolated storage paths."""
    learning_file = tmp_path / "recovery_learning.csv"
    audit_file = tmp_path / "recovery_audit.csv"
    monkeypatch.setattr("src.tracking.learning_store.LEARNING_FILE", learning_file)
    monkeypatch.setattr("src.tracking.learning_store.LOG_DIR", tmp_path)
    monkeypatch.setattr("src.audit_logger.AUDIT_FILE", audit_file)
    monkeypatch.setattr("src.audit_logger.LOG_DIR", tmp_path)


def test_learning_comparison_with_real_verified_evidence():
    """Requirement 1: Build learning comparison with real verified recovery evidence."""
    candidates = [
        {"route": "UPI + Bank_A + Android", "transactions": 100, "successes": 96},
        {"route": "UPI + Bank_B + Android", "transactions": 100, "successes": 91},
    ]

    stats = RouteLearningStats(
        route="UPI + Bank_A + Android",
        attempts=20,
        recoveries=20,
        recovery_rate=0.95,
        total_recovered_value=10000.0,
        total_execution_cost=500.0,
        net_recovered_value=9500.0,
        evidence_confidence=0.667,
    )

    view = build_learning_comparison(
        route_candidates=candidates,
        learning_context={"UPI + Bank_A + Android": stats},
        target_route="UPI + Bank_A + Android",
    )

    assert isinstance(view, LearningComparisonView)
    assert view.has_learning_evidence is True
    assert view.total_learned_attempts == 20
    assert view.total_learned_recoveries == 20
    assert view.overall_recovery_rate == pytest.approx(1.0, abs=0.01)
    assert view.learning_provenance == "LEARNED"
    assert view.learning_score_lift_value.startswith("+")

    # Find item for Bank_A
    item_a = next(c for c in view.route_comparisons if c.route == "UPI + Bank_A + Android")
    assert item_a.learned_attempts == 20
    assert item_a.learned_recoveries == 20
    assert item_a.learned_recovery_rate == 0.95
    assert item_a.score_after > item_a.score_before
    assert item_a.score_delta > 0.0
    assert item_a.status_label.startswith("LIFT")


def test_no_learning_evidence():
    """Requirement 2 & Part 6: No learning evidence is handled cleanly and does not display +0.0000."""
    candidates = list(DEFAULT_DEMO_CANDIDATES)

    view = build_learning_comparison(
        route_candidates=candidates,
        learning_context=None,
    )

    assert view.has_learning_evidence is False
    assert view.learning_score_lift_value == "No learning evidence"
    assert view.adaptation_status == "NO LEARNING EVIDENCE"
    assert view.preferred_route_changed is False

    for item in view.route_comparisons:
        assert item.learned_attempts == 0
        assert item.learned_recoveries == 0
        assert item.score_delta == 0.0
        assert item.status_label == "UNCHANGED"


def test_score_delta_derived_from_existing_route_scores():
    """Requirement 3: Score delta is strictly derived from authoritative RouteScorer output."""
    candidates = [
        {"route": "UPI + Bank_A + Android", "transactions": 100, "successes": 96},
        {"route": "UPI + Bank_B + Android", "transactions": 100, "successes": 91},
    ]

    stats = RouteLearningStats(
        route="UPI + Bank_A + Android",
        attempts=15,
        recoveries=15,
        recovery_rate=0.90,
        total_recovered_value=7500.0,
        total_execution_cost=375.0,
        net_recovered_value=7125.0,
        evidence_confidence=0.60,
    )

    view = build_learning_comparison(
        route_candidates=candidates,
        learning_context={"UPI + Bank_A + Android": stats},
    )

    scorer = RouteScorer()
    manual_before = scorer.score("UPI + Bank_A + Android", 100, 96, learning_stats=None).score
    manual_after = scorer.score("UPI + Bank_A + Android", 100, 96, learning_stats=stats).score
    expected_delta = round(manual_after - manual_before, 4)

    item_a = next(c for c in view.route_comparisons if c.route == "UPI + Bank_A + Android")
    assert item_a.score_before == pytest.approx(manual_before, abs=1e-5)
    assert item_a.score_after == pytest.approx(manual_after, abs=1e-5)
    assert item_a.score_delta == expected_delta


def test_ranking_before_and_after_uses_existing_route_ranking():
    """Requirement 4: Ranks before and after are strictly determined by rank_routes()."""
    candidates = [
        {"route": "UPI + Bank_A + Android", "transactions": 100, "successes": 96},
        {"route": "UPI + Bank_B + Android", "transactions": 100, "successes": 91},
        {"route": "UPI + Bank_C + Android", "transactions": 100, "successes": 88},
    ]

    stats_b = RouteLearningStats(
        route="UPI + Bank_B + Android",
        attempts=50,
        recoveries=50,
        recovery_rate=0.98,
        total_recovered_value=25000.0,
        total_execution_cost=1250.0,
        net_recovered_value=23750.0,
        evidence_confidence=0.833,
    )

    view = build_learning_comparison(
        route_candidates=candidates,
        learning_context={"UPI + Bank_B + Android": stats_b},
    )

    expected_pre = rank_routes(candidates, learning_history=None)
    expected_post = rank_routes(candidates, learning_history={"UPI + Bank_B + Android": stats_b})

    pre_ranks = {r.route: i + 1 for i, r in enumerate(expected_pre)}
    post_ranks = {r.route: i + 1 for i, r in enumerate(expected_post)}

    for item in view.route_comparisons:
        assert item.rank_before == pre_ranks[item.route]
        assert item.rank_after == post_ranks[item.route]


def test_decision_change_is_correctly_identified():
    """Requirement 5: Identifies when verified recovery evidence changes the preferred route."""
    # Route A initially preferred: 85/100
    # Route B close behind: 83/100
    candidates = [
        {"route": "UPI + Bank_A + Android", "transactions": 100, "successes": 85},
        {"route": "UPI + Bank_B + Android", "transactions": 100, "successes": 83},
    ]

    # Strong verified recovery evidence on Route B
    stats_b = RouteLearningStats(
        route="UPI + Bank_B + Android",
        attempts=150,
        recoveries=150,
        recovery_rate=1.0,
        total_recovered_value=75000.0,
        total_execution_cost=3750.0,
        net_recovered_value=71250.0,
        evidence_confidence=0.9375,
    )

    view = build_learning_comparison(
        route_candidates=candidates,
        learning_context={"UPI + Bank_B + Android": stats_b},
    )

    assert view.top_route_before == "UPI + Bank_A + Android"
    assert view.top_route_after == "UPI + Bank_B + Android"
    assert view.preferred_route_changed is True
    assert view.adaptation_status == "DECISION ADAPTED"
    assert "changed the preferred route" in view.adaptation_summary


def test_ranking_unchanged_correctly_represented():
    """Requirement 6: When evidence does not flip the ranking, reports DECISION UNCHANGED."""
    candidates = [
        {"route": "UPI + Bank_A + Android", "transactions": 100, "successes": 96},
        {"route": "UPI + Bank_B + Android", "transactions": 100, "successes": 85},
    ]

    # Small evidence on Route A keeps Route A on top
    stats_a = RouteLearningStats(
        route="UPI + Bank_A + Android",
        attempts=5,
        recoveries=5,
        recovery_rate=0.90,
        total_recovered_value=2500.0,
        total_execution_cost=125.0,
        net_recovered_value=2375.0,
        evidence_confidence=0.333,
    )

    view = build_learning_comparison(
        route_candidates=candidates,
        learning_context={"UPI + Bank_A + Android": stats_a},
        target_route="UPI + Bank_A + Android",
    )

    assert view.top_route_before == "UPI + Bank_A + Android"
    assert view.top_route_after == "UPI + Bank_A + Android"
    assert view.preferred_route_changed is False
    assert view.adaptation_status == "DECISION UNCHANGED"
    assert "Current route remains preferred" in view.adaptation_summary


def test_multiple_routes_handled():
    """Requirement 7: Multiple routes are accurately compared and ordered by post-learning rank."""
    candidates = [
        {"route": "Route_1", "transactions": 100, "successes": 95},
        {"route": "Route_2", "transactions": 100, "successes": 92},
        {"route": "Route_3", "transactions": 100, "successes": 89},
        {"route": "Route_4", "transactions": 100, "successes": 85},
    ]

    view = build_learning_comparison(candidates, learning_context=None)
    assert len(view.route_comparisons) == 4
    # Ensure ordered by rank_after 1, 2, 3, 4
    ranks = [item.rank_after for item in view.route_comparisons]
    assert ranks == [1, 2, 3, 4]


def test_invalid_and_missing_learning_evidence_handled_safely():
    """Requirement 8: Tolerates None, empty, or partial learning evidence safely."""
    candidates = [{"route": "Route_X", "transactions": 50, "successes": 45}]

    # None context
    v1 = build_learning_comparison(candidates, None)
    assert v1.has_learning_evidence is False

    # Empty dict context
    v2 = build_learning_comparison(candidates, {})
    assert v2.has_learning_evidence is False

    # Empty candidate list
    v3 = build_learning_comparison([], None)
    assert v3.has_learning_evidence is False
    assert v3.top_route_before == "NONE"

    # Malformed stats object
    v4 = build_learning_comparison(candidates, {"Route_X": {"attempts": -5, "recoveries": "bad"}})
    assert v4.route_comparisons[0].learned_attempts == -5
    assert v4.route_comparisons[0].learned_recoveries == 0


def test_no_nan_or_inf_values_in_learning_view():
    """Requirement 9: Guarantees zero NaN or Inf values in view properties."""
    candidates = [
        {"route": "Route_1", "transactions": 0, "successes": 0},
        {"route": "Route_2", "transactions": 100, "successes": 90},
    ]

    stats = RouteLearningStats(
        route="Route_1",
        attempts=0,
        recoveries=0,
        recovery_rate=float("nan"),
        total_recovered_value=0.0,
        total_execution_cost=0.0,
        net_recovered_value=0.0,
        evidence_confidence=float("inf"),
    )

    view = build_learning_comparison(candidates, {"Route_1": stats})

    assert math.isfinite(view.overall_recovery_rate)
    assert math.isfinite(view.mean_evidence_confidence)
    for c in view.route_comparisons:
        assert math.isfinite(c.observed_success_rate)
        assert math.isfinite(c.learned_recovery_rate)
        assert math.isfinite(c.evidence_confidence)
        assert math.isfinite(c.score_before)
        assert math.isfinite(c.score_after)
        assert math.isfinite(c.score_delta)


def test_deterministic_repeated_output():
    """Requirement 10: Repeated calls with identical inputs produce identical outputs."""
    candidates = list(DEFAULT_DEMO_CANDIDATES)
    engine = RecoveryLearningEngine()
    engine.record("UPI + Bank_A + Android", 10, 10, 5000.0, 250.0)

    view1 = build_learning_comparison(candidates, engine)
    view2 = build_learning_comparison(candidates, engine)

    assert view1.top_route_before == view2.top_route_before
    assert view1.top_route_after == view2.top_route_after
    assert view1.learning_score_lift_value == view2.learning_score_lift_value
    assert len(view1.route_comparisons) == len(view2.route_comparisons)
    for i in range(len(view1.route_comparisons)):
        assert view1.route_comparisons[i].score_after == view2.route_comparisons[i].score_after


def test_no_persistence_side_effects(tmp_path):
    """Requirement 11 & 12: Building learning comparison produces zero file writes or deletions."""
    csv_file = tmp_path / "recovery_learning.csv"
    assert not csv_file.exists()

    candidates = list(DEFAULT_DEMO_CANDIDATES)
    view = build_learning_comparison(candidates, None)

    # Calling view layer must NOT create or mutate persistence files
    assert not csv_file.exists()


def test_integration_with_demo_runner_output():
    """Part 8: DemoRunner output seamlessly feeds into build_learning_comparison."""
    runner = DemoRunner()
    result = runner.run(CANONICAL_HAPPY_PATH)

    assert result.learning_evidence is not None

    view = build_learning_comparison(
        route_candidates=CANONICAL_HAPPY_PATH.route_candidates,
        learning_context={result.learning_evidence.route: result.learning_evidence},
        target_route=result.learning_evidence.route,
    )

    assert view.has_learning_evidence is True
    assert view.top_route_after == result.top_route_after
    item = next(c for c in view.route_comparisons if c.route == result.learning_evidence.route)
    assert item.score_delta == pytest.approx(result.score_delta, abs=1e-4)
