"""
Controlled incident scenarios for the AI Payment Recovery Agent.

This module is deliberately independent of the live application flow.
It creates counterfactual scenario overrides for demo/testing only.

No real payment routing is performed.
"""

from copy import deepcopy


BASELINE_SUCCESS = 0.9442
DEFAULT_TRANSACTIONS = 508


SCENARIOS = {
    "Bank degradation — RECOVER": {
        "description": "Severe route degradation with strong evidence.",
        "current_success_rate": 0.6949,
        "baseline_success_rate": BASELINE_SUCCESS,
        "transactions": 508,
        "ai_confidence": 0.90,
        "severity": "HIGH",
        "expected_control": "RECOVER",
        "guardrail": "CONTINUE",
        "failure_reasons": {
            "BANK_DECLINE": 42,
            "INSUFFICIENT_FUNDS": 39,
            "TIMEOUT": 38,
            "NETWORK_ERROR": 36,
        },
    },
    "Mild degradation — STOP": {
        "description": "Small degradation that does not cross the recovery threshold.",
        "current_success_rate": 0.9050,
        "baseline_success_rate": BASELINE_SUCCESS,
        "transactions": 508,
        "ai_confidence": 0.92,
        "severity": "MEDIUM",
        "expected_control": "STOP",
        "guardrail": "STOP",
        "failure_reasons": {
            "BANK_DECLINE": 18,
            "INSUFFICIENT_FUNDS": 20,
            "TIMEOUT": 8,
            "NETWORK_ERROR": 6,
        },
    },
    "Low AI confidence — ESCALATE": {
        "description": "Severe incident, but AI confidence is below the automation threshold.",
        "current_success_rate": 0.6949,
        "baseline_success_rate": BASELINE_SUCCESS,
        "transactions": 508,
        "ai_confidence": 0.61,
        "severity": "HIGH",
        "expected_control": "ESCALATE",
        "guardrail": "HUMAN_REVIEW",
        "failure_reasons": {
            "BANK_DECLINE": 42,
            "INSUFFICIENT_FUNDS": 39,
            "TIMEOUT": 38,
            "NETWORK_ERROR": 36,
        },
    },
    "Recovery route degradation — ROLLBACK": {
        "description": "Recovery starts successfully but the alternative route breaches its guardrail.",
        "current_success_rate": 0.6949,
        "baseline_success_rate": BASELINE_SUCCESS,
        "transactions": 508,
        "ai_confidence": 0.90,
        "severity": "HIGH",
        "expected_control": "RECOVER",
        "guardrail": "ROLLBACK",
        "failure_reasons": {
            "BANK_DECLINE": 42,
            "INSUFFICIENT_FUNDS": 39,
            "TIMEOUT": 38,
            "NETWORK_ERROR": 36,
        },
        "post_recovery_success_rate": 0.8839,
        "rollback_threshold": 0.9100,
    },
    "Healthy system — CONTINUE": {
        "description": "Route remains inside normal operating guardrails.",
        "current_success_rate": 0.9420,
        "baseline_success_rate": BASELINE_SUCCESS,
        "transactions": 508,
        "ai_confidence": 0.96,
        "severity": "LOW",
        "expected_control": "CONTINUE",
        "guardrail": "CONTINUE",
        "failure_reasons": {
            "BANK_DECLINE": 8,
            "INSUFFICIENT_FUNDS": 9,
            "TIMEOUT": 2,
            "NETWORK_ERROR": 1,
        },
    },
}


def list_scenarios():
    """Return scenario names in presentation order."""
    return list(SCENARIOS.keys())


def get_scenario(name):
    """Return a defensive copy of one scenario."""
    if name not in SCENARIOS:
        raise KeyError(f"Unknown scenario: {name}")
    return deepcopy(SCENARIOS[name])


def scenario_summary(name):
    """Return a compact summary suitable for a Streamlit control panel."""
    s = get_scenario(name)

    degradation_pp = (
        s["baseline_success_rate"] - s["current_success_rate"]
    ) * 100

    return {
        "name": name,
        "description": s["description"],
        "current_success_rate": s["current_success_rate"],
        "baseline_success_rate": s["baseline_success_rate"],
        "degradation_pp": degradation_pp,
        "transactions": s["transactions"],
        "ai_confidence": s["ai_confidence"],
        "severity": s["severity"],
        "expected_control": s["expected_control"],
        "guardrail": s["guardrail"],
    }


def simulate_counterfactual(
    current_success_rate,
    alternative_success_rate,
    transaction_count,
    average_transaction_value,
):
    """
    Calculate counterfactual improvement without touching real payments.
    """
    current_successes = round(
        transaction_count * current_success_rate
    )

    current_failures = (
        transaction_count - current_successes
    )

    after_successes = round(
        transaction_count * alternative_success_rate
    )

    after_failures = (
        transaction_count - after_successes
    )

    additional_successes = max(
        0,
        after_successes - current_successes
    )

    recovered_value = (
        additional_successes
        * average_transaction_value
    )

    improvement_pp = (
        alternative_success_rate
        - current_success_rate
    ) * 100

    return {
        "before_successes": current_successes,
        "before_failures": current_failures,
        "after_successes": after_successes,
        "after_failures": after_failures,
        "additional_successes": additional_successes,
        "success_improvement_pp": improvement_pp,
        "estimated_recovered_value": recovered_value,
    }


def evaluate_scenario_control(name):
    """
    Return the intended bounded-control outcome for demo validation.

    This is intentionally explicit rather than pretending the scenario
    changed the underlying production policy engine.
    """
    s = get_scenario(name)

    return {
        "scenario": name,
        "decision": s["expected_control"],
        "guardrail": s["guardrail"],
        "confidence": s["ai_confidence"],
        "severity": s["severity"],
        "rollback_required": s["guardrail"] == "ROLLBACK",
        "human_review_required": s["expected_control"] == "ESCALATE",
    }


if __name__ == "__main__":
    print("=" * 70)
    print("CONTROLLED INCIDENT SCENARIO ENGINE")
    print("=" * 70)

    for name in list_scenarios():
        result = evaluate_scenario_control(name)
        print(
            f"{name}: "
            f"{result['decision']} / "
            f"{result['guardrail']}"
        )

    print("=" * 70)
