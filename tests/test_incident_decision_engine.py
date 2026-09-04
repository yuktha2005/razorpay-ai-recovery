from src.decision.incident_decision_engine import (
    IncidentDecisionEngine,
)


def test_incident_decision_engine_produces_safe_decision():

    engine = IncidentDecisionEngine()

    result = engine.evaluate(
        incident_route="UPI + Bank_X + Android",
        transactions_affected=508,
        failures_observed=155,
        baseline_success_rate=0.946123,
        current_success_rate=0.694882,
        severity="CRITICAL",
        route_candidates=[
            {
                "route": "UPI + Bank_A + Android",
                "transactions": 3,
                "successes": 3,
            },
            {
                "route": "UPI + Bank_B + Android",
                "transactions": 6,
                "successes": 6,
            },
            {
                "route": "UPI + Bank_C + Android",
                "transactions": 8,
                "successes": 7,
            },
            {
                "route": "UPI + Bank_Y + Android",
                "transactions": 9,
                "successes": 9,
            },
        ],
        average_transaction_value=2376.307008,
    )

    assert result.incident_route == (
        "UPI + Bank_X + Android"
    )

    assert result.transactions_affected == 508

    assert result.failures_observed == 155

    assert result.severity == "CRITICAL"

    assert result.degradation_pp > 25

    assert result.financial_exposure > 0

    assert result.expected_loss > 0

    assert len(result.ranked_routes) == 4

    assert result.decision is not None

    assert result.safety_decision is not None


def test_critical_route_switch_is_safety_gated():

    engine = IncidentDecisionEngine()

    result = engine.evaluate(
        incident_route="UPI + Bank_X + Android",
        transactions_affected=508,
        failures_observed=155,
        baseline_success_rate=0.946123,
        current_success_rate=0.694882,
        severity="CRITICAL",
        route_candidates=[
            {
                "route": "UPI + Bank_C + Android",
                "transactions": 8,
                "successes": 7,
            },
        ],
        average_transaction_value=3000.0,
    )

    assert result.decision.recommended_action != ""

    assert result.safety_decision is not None


# =========================================================
# Milestone 3: Closed-Loop Learning Integration Tests
# =========================================================

from src.tracking.learning_history import PersistentLearningHistory
from src.tracking.recovery_learning import RouteLearningStats


def test_existing_behavior_without_learning_history_unchanged():
    """A. Existing behavior without learning history remains unchanged."""
    engine = IncidentDecisionEngine()

    result = engine.evaluate(
        incident_route="UPI + Bank_X + Android",
        transactions_affected=200,
        failures_observed=60,
        baseline_success_rate=0.95,
        current_success_rate=0.70,
        severity="CRITICAL",
        average_transaction_value=1500.0,
        route_candidates=[
            {"route": "UPI + Bank_A + Android", "transactions": 50, "successes": 49},
            {"route": "UPI + Bank_B + Android", "transactions": 50, "successes": 40},
        ],
    )

    assert result.decision is not None
    assert result.ranked_routes[0].route == "UPI + Bank_A + Android"
    assert result.decision.recommended_action == "ROUTE_SWITCH:UPI + Bank_A + Android"
    assert result.ranked_routes[0].learned_attempts == 0


def test_empty_learning_history_does_not_change_decision():
    """B. Empty PersistentLearningHistory produces the exact same decision as baseline."""
    candidates = [
        {"route": "UPI + Bank_A + Android", "transactions": 50, "successes": 49},
        {"route": "UPI + Bank_B + Android", "transactions": 50, "successes": 40},
    ]

    engine_baseline = IncidentDecisionEngine()
    result_baseline = engine_baseline.evaluate(
        incident_route="UPI + Bank_X + Android",
        transactions_affected=100,
        failures_observed=30,
        baseline_success_rate=0.95,
        current_success_rate=0.70,
        severity="CRITICAL",
        average_transaction_value=1000.0,
        route_candidates=candidates,
    )

    class EmptyHistoryMock:
        def load(self):
            return []

    engine_empty = IncidentDecisionEngine(learning_history=EmptyHistoryMock())
    result_empty = engine_empty.evaluate(
        incident_route="UPI + Bank_X + Android",
        transactions_affected=100,
        failures_observed=30,
        baseline_success_rate=0.95,
        current_success_rate=0.70,
        severity="CRITICAL",
        average_transaction_value=1000.0,
        route_candidates=candidates,
    )

    assert result_empty.decision.recommended_action == result_baseline.decision.recommended_action
    assert result_empty.decision.confidence == result_baseline.decision.confidence
    assert len(result_empty.ranked_routes) == len(result_baseline.ranked_routes)
    for r_empty, r_base in zip(result_empty.ranked_routes, result_baseline.ranked_routes):
        assert r_empty.route == r_base.route
        assert r_empty.score == r_base.score
        assert r_empty.transactions == r_base.transactions


def test_injected_learning_history_changes_route_ranking():
    """C. Injected learning history changes route ranking when evidence is materially stronger."""
    candidates = [
        {"route": "UPI + Bank_A + Android", "transactions": 50, "successes": 49},
        {"route": "UPI + Bank_B + Android", "transactions": 50, "successes": 40},
    ]

    # Baseline: Bank_A is ranked #1 and selected by optimizer because 49/50 > 40/50
    engine_baseline = IncidentDecisionEngine()
    res_base = engine_baseline.evaluate(
        incident_route="UPI + Bank_X + Android",
        transactions_affected=100,
        failures_observed=30,
        baseline_success_rate=0.95,
        current_success_rate=0.70,
        severity="CRITICAL",
        average_transaction_value=1000.0,
        route_candidates=candidates,
    )
    assert res_base.ranked_routes[0].route == "UPI + Bank_A + Android"
    assert res_base.decision.recommended_action == "ROUTE_SWITCH:UPI + Bank_A + Android"

    # Now inject verified historical recovery evidence for Bank_B via an object with .load()
    # (mimicking PersistentLearningHistory)
    class MockPersistentLearningHistory:
        def load(self):
            return [
                RouteLearningStats(
                    route="UPI + Bank_B + Android",
                    attempts=400,
                    recoveries=395,
                    recovery_rate=0.9875,
                    total_recovered_value=395000.0,
                    total_execution_cost=10000.0,
                    net_recovered_value=385000.0,
                    evidence_confidence=0.98,
                )
            ]

    engine_learned = IncidentDecisionEngine(learning_history=MockPersistentLearningHistory())
    res_learned = engine_learned.evaluate(
        incident_route="UPI + Bank_X + Android",
        transactions_affected=100,
        failures_observed=30,
        baseline_success_rate=0.95,
        current_success_rate=0.70,
        severity="CRITICAL",
        average_transaction_value=1000.0,
        route_candidates=candidates,
    )

    # Bank_B should now overtake Bank_A and become the recommended recovery action!
    assert res_learned.ranked_routes[0].route == "UPI + Bank_B + Android"
    assert res_learned.decision.recommended_action == "ROUTE_SWITCH:UPI + Bank_B + Android"
    assert res_learned.decision.confidence > res_base.decision.confidence


def test_learned_evidence_reaches_rank_routes():
    """D. Learned evidence reaches rank_routes through IncidentDecisionEngine."""
    candidates = [
        {"route": "UPI + Bank_Target + Android", "transactions": 5, "successes": 5},
    ]

    learning_history = {
        "UPI + Bank_Target + Android": {
            "route": "UPI + Bank_Target + Android",
            "attempts": 40,
            "recoveries": 38,
        }
    }

    engine = IncidentDecisionEngine(learning_history=learning_history)
    result = engine.evaluate(
        incident_route="UPI + Bank_Degraded + Android",
        transactions_affected=50,
        failures_observed=20,
        baseline_success_rate=0.95,
        current_success_rate=0.60,
        severity="CRITICAL",
        average_transaction_value=500.0,
        route_candidates=candidates,
    )

    top_route = result.ranked_routes[0]
    assert top_route.transactions == 45  # 5 observed + 40 learned
    assert top_route.successes == 43     # 5 observed + 38 learned
    assert top_route.learned_attempts == 40
    assert top_route.learned_recoveries == 38
    assert "Score incorporates 40 verified recovery attempts with 38 recoveries" in top_route.explanation


def test_route_isolation_in_decision_engine():
    """E. Route isolation: learning evidence for Route B cannot alter Route A's metrics."""
    candidates = [
        {"route": "UPI + Bank_A + Android", "transactions": 20, "successes": 18},
        {"route": "UPI + Bank_B + Android", "transactions": 15, "successes": 14},
    ]

    engine_base = IncidentDecisionEngine()
    res_base = engine_base.evaluate(
        incident_route="UPI + Degraded + Android",
        transactions_affected=50,
        failures_observed=15,
        baseline_success_rate=0.95,
        current_success_rate=0.70,
        severity="CRITICAL",
        average_transaction_value=800.0,
        route_candidates=candidates,
    )
    base_a = next(r for r in res_base.ranked_routes if r.route == "UPI + Bank_A + Android")

    # Inject learning ONLY for Route B
    learning_history = {
        "UPI + Bank_B + Android": {
            "route": "UPI + Bank_B + Android",
            "attempts": 50,
            "recoveries": 49,
        }
    }

    engine_learned = IncidentDecisionEngine(learning_history=learning_history)
    res_learned = engine_learned.evaluate(
        incident_route="UPI + Degraded + Android",
        transactions_affected=50,
        failures_observed=15,
        baseline_success_rate=0.95,
        current_success_rate=0.70,
        severity="CRITICAL",
        average_transaction_value=800.0,
        route_candidates=candidates,
    )
    learned_a = next(r for r in res_learned.ranked_routes if r.route == "UPI + Bank_A + Android")

    assert learned_a.score == base_a.score
    assert learned_a.transactions == base_a.transactions
    assert learned_a.successes == base_a.successes
    assert learned_a.learned_attempts == 0


def test_determinism_with_learning_history():
    """F. Determinism: same candidates + same learning history produce identical decisions."""
    candidates = [
        {"route": "UPI + Bank_A + Android", "transactions": 10, "successes": 9},
        {"route": "UPI + Bank_B + Android", "transactions": 8, "successes": 7},
    ]

    learning_history = {
        "UPI + Bank_A + Android": {"route": "UPI + Bank_A + Android", "attempts": 20, "recoveries": 19},
        "UPI + Bank_B + Android": {"route": "UPI + Bank_B + Android", "attempts": 25, "recoveries": 24},
    }

    engine = IncidentDecisionEngine(learning_history=learning_history)

    kwargs = dict(
        incident_route="UPI + Bank_X + Android",
        transactions_affected=80,
        failures_observed=25,
        baseline_success_rate=0.95,
        current_success_rate=0.68,
        severity="CRITICAL",
        average_transaction_value=1200.0,
        route_candidates=candidates,
    )

    run1 = engine.evaluate(**kwargs)
    run2 = engine.evaluate(**kwargs)

    assert run1.decision.recommended_action == run2.decision.recommended_action
    assert run1.decision.confidence == run2.decision.confidence
    assert run1.decision.estimated_value == run2.decision.estimated_value
    assert len(run1.ranked_routes) == len(run2.ranked_routes)
    for r1, r2 in zip(run1.ranked_routes, run2.ranked_routes):
        assert r1.route == r2.route
        assert r1.score == r2.score
        assert r1.transactions == r2.transactions
        assert r1.successes == r2.successes
        assert r1.learned_attempts == r2.learned_attempts
        assert r1.learned_recoveries == r2.learned_recoveries
