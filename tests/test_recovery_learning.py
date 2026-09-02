from src.tracking.recovery_learning import (
    RecoveryLearningEngine,
)


def test_first_route_outcome_is_recorded():
    engine = RecoveryLearningEngine()

    result = engine.record(
        route="UPI + Bank_Y + Android",
        attempted_transactions=10,
        successful_recoveries=8,
        recovered_value=8000,
        execution_cost=250,
    )

    assert result.route == "UPI + Bank_Y + Android"
    assert result.attempts == 10
    assert result.recoveries == 8

    assert result.total_recovered_value == 8000
    assert result.total_execution_cost == 250
    assert result.net_recovered_value == 7750

    assert result.recovery_rate > 0
    assert result.evidence_confidence > 0


def test_multiple_outcomes_are_accumulated():
    engine = RecoveryLearningEngine()

    engine.record(
        route="UPI + Bank_Y + Android",
        attempted_transactions=10,
        successful_recoveries=8,
        recovered_value=8000,
        execution_cost=250,
    )

    result = engine.record(
        route="UPI + Bank_Y + Android",
        attempted_transactions=20,
        successful_recoveries=14,
        recovered_value=14000,
        execution_cost=500,
    )

    assert result.attempts == 30
    assert result.recoveries == 22

    assert result.total_recovered_value == 22000
    assert result.total_execution_cost == 750
    assert result.net_recovered_value == 21250


def test_small_sample_is_smoothed():
    engine = RecoveryLearningEngine()

    result = engine.record(
        route="UPI + Bank_A + Android",
        attempted_transactions=1,
        successful_recoveries=1,
        recovered_value=1000,
        execution_cost=25,
    )

    # One successful attempt should not immediately
    # produce a raw 100% confidence-adjusted rate.
    assert result.recovery_rate < 1.0
    assert result.evidence_confidence < 1.0


def test_route_ranking_prefers_stronger_evidence():
    engine = RecoveryLearningEngine()

    engine.record(
        route="UPI + Bank_A + Android",
        attempted_transactions=1,
        successful_recoveries=1,
        recovered_value=1000,
        execution_cost=25,
    )

    engine.record(
        route="UPI + Bank_Y + Android",
        attempted_transactions=100,
        successful_recoveries=75,
        recovered_value=75000,
        execution_cost=2500,
    )

    ranked = engine.rank_routes()

    assert ranked[0].route == "UPI + Bank_Y + Android"


def test_get_route_returns_saved_statistics():
    engine = RecoveryLearningEngine()

    engine.record(
        route="UPI + Bank_C + Android",
        attempted_transactions=20,
        successful_recoveries=12,
        recovered_value=12000,
        execution_cost=500,
    )

    result = engine.get_route(
        "UPI + Bank_C + Android"
    )

    assert result is not None
    assert result.attempts == 20
    assert result.recoveries == 12


def test_unknown_route_returns_none():
    engine = RecoveryLearningEngine()

    result = engine.get_route(
        "UPI + UnknownBank + Android"
    )

    assert result is None


def test_invalid_recovery_count_is_rejected():
    engine = RecoveryLearningEngine()

    try:
        engine.record(
            route="UPI + Bank_Y + Android",
            attempted_transactions=5,
            successful_recoveries=6,
            recovered_value=6000,
            execution_cost=100,
        )
        assert False
    except ValueError:
        assert True