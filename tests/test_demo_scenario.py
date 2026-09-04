"""
Tests for Deterministic Demo Scenarios.

Verifies scenario definitions, parameter validity, and isolation.
"""

import pytest

from src.demo.demo_scenario import (
    CANONICAL_HAPPY_PATH,
    DEFAULT_DEMO_CANDIDATES,
    DEMO_SCENARIOS,
    FAILURE_SAFETY_BLOCKED,
    FAILURE_UNPROFITABLE_ROLLBACK,
    DemoScenario,
    get_demo_scenario,
    list_demo_scenarios,
)


def test_canonical_happy_path_parameters():
    """Verify the canonical happy path specification conforms to expected ranges."""
    scenario = CANONICAL_HAPPY_PATH
    assert scenario.scenario_id == "canonical_happy_path"
    assert scenario.route == "UPI + Bank_X + Android"
    assert scenario.baseline_success_rate == 0.95
    assert scenario.degraded_success_rate == 0.70
    assert scenario.degraded_success_rate < scenario.baseline_success_rate
    assert scenario.transaction_count >= 100
    assert scenario.average_transaction_value > 0
    assert scenario.canary_batch_size > 0
    assert scenario.simulated_recovery_rate == 0.95
    assert not scenario.is_failure_scenario
    assert scenario.failure_type is None
    assert scenario.expected_severity == "CRITICAL"


def test_failure_safety_blocked_parameters():
    """Verify safety blocked scenario has parameters triggering critical financial policy."""
    scenario = FAILURE_SAFETY_BLOCKED
    assert scenario.scenario_id == "safety_blocked"
    assert scenario.is_failure_scenario
    assert scenario.failure_type == "SAFETY_BLOCKED"
    # Exposure = transaction_count * average_value * degradation >= 500k threshold
    exposure = scenario.transaction_count * scenario.average_transaction_value
    assert exposure >= 500000.0


def test_failure_unprofitable_rollback_parameters():
    """Verify unprofitable rollback scenario has low recovery rate and low transaction value."""
    scenario = FAILURE_UNPROFITABLE_ROLLBACK
    assert scenario.scenario_id == "unprofitable_rollback"
    assert scenario.is_failure_scenario
    assert scenario.failure_type == "UNPROFITABLE_ROLLBACK"
    assert scenario.average_transaction_value <= 50.0  # Low value ensures cost (₹25) exceeds recovery
    assert scenario.simulated_recovery_rate <= 0.20


def test_demo_scenarios_registry():
    """Verify all scenarios are registered in DEMO_SCENARIOS dictionary."""
    scenarios = list_demo_scenarios()
    assert "canonical_happy_path" in scenarios
    assert "safety_blocked" in scenarios
    assert "unprofitable_rollback" in scenarios
    assert len(scenarios) >= 3


def test_get_demo_scenario():
    """Verify scenario retrieval by ID and default fallback."""
    canonical = get_demo_scenario("canonical_happy_path")
    assert canonical.scenario_id == "canonical_happy_path"

    blocked = get_demo_scenario("safety_blocked")
    assert blocked.scenario_id == "safety_blocked"

    # Unknown fallback defaults to canonical happy path
    unknown = get_demo_scenario("unknown_scenario_xyz")
    assert unknown.scenario_id == "canonical_happy_path"


def test_scenario_route_candidates_validity():
    """Verify route candidates contain required route structure and positive counts."""
    for s_id, scenario in DEMO_SCENARIOS.items():
        assert len(scenario.route_candidates) >= 1
        for candidate in scenario.route_candidates:
            assert "route" in candidate
            assert "transactions" in candidate
            assert "successes" in candidate
            assert candidate["transactions"] >= candidate["successes"] >= 0
