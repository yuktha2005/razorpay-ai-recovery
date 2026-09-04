"""
Deterministic Demo Scenario Definitions for Razorpay AI Revenue Recovery.

Defines canonical demonstration scenarios with explicit, reproducible parameters.
No wall-clock dependence, unseeded randomness, or external network calls.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DemoScenario:
    """
    Deterministic specification for an end-to-end payment reliability scenario.
    """

    scenario_id: str
    name: str
    description: str
    payment_method: str = "UPI"
    bank: str = "Bank_X"
    device_type: str = "Android"
    baseline_success_rate: float = 0.95
    degraded_success_rate: float = 0.70
    transaction_count: int = 100
    average_transaction_value: float = 500.0
    expected_severity: str = "CRITICAL"
    expected_action: str = "ROUTE_SWITCH:UPI + Bank_A + Android"
    route_candidates: List[Dict[str, Any]] = field(default_factory=list)
    canary_batch_size: int = 20
    simulated_recovery_rate: float = 0.95
    is_failure_scenario: bool = False
    failure_type: Optional[str] = None  # "SAFETY_BLOCKED" or "UNPROFITABLE_ROLLBACK"

    @property
    def route(self) -> str:
        """Formatted payment route identifier."""
        return f"{self.payment_method} + {self.bank} + {self.device_type}"


# -------------------------------------------------------------------------
# Default Route Candidates for Demo Scenarios
# -------------------------------------------------------------------------

DEFAULT_DEMO_CANDIDATES: List[Dict[str, Any]] = [
    {
        "route": "UPI + Bank_A + Android",
        "transactions": 100,
        "successes": 96,
    },
    {
        "route": "UPI + Bank_B + Android",
        "transactions": 100,
        "successes": 91,
    },
    {
        "route": "UPI + Bank_C + Android",
        "transactions": 100,
        "successes": 88,
    },
]


# -------------------------------------------------------------------------
# Canonical Scenario 1: Happy-Path Recovery (The Core Judge Story)
# -------------------------------------------------------------------------

CANONICAL_HAPPY_PATH = DemoScenario(
    scenario_id="canonical_happy_path",
    name="Canonical Happy Path: Degradation → AI Decision → Canary Verified → Learning",
    description=(
        "Primary demonstration of the end-to-end recovery loop: "
        "A healthy UPI route experiences a 25 pp degradation. AI detects the incident, "
        "quantifies revenue at risk, selects an optimal alternative route, passes "
        "deterministic safety controls, executes a bounded canary batch, verifies net "
        "recovered value, and updates route learning evidence."
    ),
    payment_method="UPI",
    bank="Bank_X",
    device_type="Android",
    baseline_success_rate=0.95,
    degraded_success_rate=0.70,
    transaction_count=200,
    average_transaction_value=500.0,
    expected_severity="CRITICAL",
    expected_action="ROUTE_SWITCH:UPI + Bank_A + Android",
    route_candidates=list(DEFAULT_DEMO_CANDIDATES),
    canary_batch_size=50,
    simulated_recovery_rate=0.95,
    is_failure_scenario=False,
    failure_type=None,
)


# -------------------------------------------------------------------------
# Failure Scenario 2: Safety Policy Blocked (Critical Exposure)
# -------------------------------------------------------------------------

FAILURE_SAFETY_BLOCKED = DemoScenario(
    scenario_id="safety_blocked",
    name="Safety Gate Blocked: Critical Financial Exposure",
    description=(
        "Demonstrates deterministic safety protection: "
        "A high-value enterprise payment route experiences degradation, but financial "
        "exposure exceeds the critical automated-action threshold (₹500,000). The SafetyController "
        "blocks automated execution, requiring human escalation and preventing unconstrained loss."
    ),
    payment_method="UPI",
    bank="Bank_X",
    device_type="Android",
    baseline_success_rate=0.95,
    degraded_success_rate=0.70,
    transaction_count=200,
    average_transaction_value=25000.0,  # 50 excess failures * 25,000 = ₹1,250,000 > ₹500,000 threshold
    expected_severity="CRITICAL",
    expected_action="ROUTE_SWITCH:UPI + Bank_A + Android",
    route_candidates=list(DEFAULT_DEMO_CANDIDATES),
    canary_batch_size=50,
    simulated_recovery_rate=0.95,
    is_failure_scenario=True,
    failure_type="SAFETY_BLOCKED",
)


# -------------------------------------------------------------------------
# Failure Scenario 3: Unprofitable Canary Rollback (Circuit Breaker)
# -------------------------------------------------------------------------

FAILURE_UNPROFITABLE_ROLLBACK = DemoScenario(
    scenario_id="unprofitable_rollback",
    name="Canary Guardrail Trip: Unprofitable Recovery → Rollback",
    description=(
        "Demonstrates bounded canary protection and circuit breakers: "
        "AI switches to a candidate route, but canary execution encounters unexpected "
        "failures. Because execution cost exceeds recovered value, the verifier identifies "
        "an unprofitable outcome and triggers an immediate ROLLBACK guardrail."
    ),
    payment_method="UPI",
    bank="Bank_X",
    device_type="Android",
    baseline_success_rate=0.95,
    degraded_success_rate=0.70,
    transaction_count=200,
    average_transaction_value=20.0,  # Low txn value ensures execution cost (₹25/txn) exceeds recovery
    expected_severity="CRITICAL",
    expected_action="ROUTE_SWITCH:UPI + Bank_A + Android",
    route_candidates=list(DEFAULT_DEMO_CANDIDATES),
    canary_batch_size=50,
    simulated_recovery_rate=0.10,  # 10% recovery rate -> cost > recovered -> UNPROFITABLE
    is_failure_scenario=True,
    failure_type="UNPROFITABLE_ROLLBACK",
)


DEMO_SCENARIOS: Dict[str, DemoScenario] = {
    CANONICAL_HAPPY_PATH.scenario_id: CANONICAL_HAPPY_PATH,
    FAILURE_SAFETY_BLOCKED.scenario_id: FAILURE_SAFETY_BLOCKED,
    FAILURE_UNPROFITABLE_ROLLBACK.scenario_id: FAILURE_UNPROFITABLE_ROLLBACK,
}


def get_demo_scenario(scenario_id: str) -> DemoScenario:
    """Retrieve a demo scenario by its identifier, defaulting to canonical happy path."""
    return DEMO_SCENARIOS.get(scenario_id, CANONICAL_HAPPY_PATH)


def list_demo_scenarios() -> List[str]:
    """List all available demo scenario IDs."""
    return list(DEMO_SCENARIOS.keys())
