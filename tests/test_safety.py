from src.models.domain import Decision
from src.safety.controller import SafetyController


def make_decision(action="MONITOR", confidence=0.80):
    return Decision(
        payment_id="safety_test_001",
        recommended_action=action,
        confidence=confidence,
        expected_loss_before=10000.0,
        expected_loss_after=5000.0,
        estimated_value=5000.0,
        explanation="Test decision",
    )


def test_low_confidence_falls_back_to_monitor():
    decision = make_decision(
        action="CUSTOMER_CONFIRMATION",
        confidence=0.30,
    )

    result = SafetyController().evaluate(decision)

    assert result.action == "MONITOR"
    assert result.allowed is True
    assert result.requires_human_review is False


def test_normal_action_is_allowed():
    decision = make_decision(
        action="CUSTOMER_CONFIRMATION",
        confidence=0.80,
    )

    result = SafetyController().evaluate(decision)

    assert result.action == "CUSTOMER_CONFIRMATION"
    assert result.allowed is True
    assert result.requires_human_review is False


def test_high_impact_action_requires_high_confidence():
    decision = make_decision(
        action="MANUAL_REVIEW",
        confidence=0.75,
    )

    result = SafetyController().evaluate(decision)

    assert result.action == "MANUAL_REVIEW"
    assert result.allowed is True
    assert result.requires_human_review is True


def test_high_confidence_high_impact_action_is_allowed():
    decision = make_decision(
        action="MANUAL_REVIEW",
        confidence=0.95,
    )

    result = SafetyController().evaluate(decision)

    assert result.action == "MANUAL_REVIEW"
    assert result.allowed is True
    assert result.requires_human_review is False


def test_confidence_above_one_is_clamped():
    decision = make_decision(
        action="MANUAL_REVIEW",
        confidence=1.50,
    )

    result = SafetyController().evaluate(decision)

    assert result.action == "MANUAL_REVIEW"
    assert result.allowed is True


def test_confidence_below_zero_is_treated_as_low_confidence():
    decision = make_decision(
        action="CUSTOMER_CONFIRMATION",
        confidence=-0.50,
    )

    result = SafetyController().evaluate(decision)

    assert result.action == "MONITOR"
    assert result.allowed is True


def test_none_confidence_falls_back_to_monitor():
    decision = make_decision(
        action="CUSTOMER_CONFIRMATION",
        confidence=None,
    )

    result = SafetyController().evaluate(decision)

    assert result.action == "MONITOR"
    assert result.allowed is True
    assert result.requires_human_review is False


def test_nan_confidence_falls_back_to_monitor():
    decision = make_decision(
        action="CUSTOMER_CONFIRMATION",
        confidence=float("nan"),
    )

    result = SafetyController().evaluate(decision)

    assert result.action == "MONITOR"
    assert result.allowed is True
    assert result.requires_human_review is False


def test_pos_inf_confidence_falls_back_to_monitor():
    decision = make_decision(
        action="CUSTOMER_CONFIRMATION",
        confidence=float("inf"),
    )

    result = SafetyController().evaluate(decision)

    assert result.action == "MONITOR"
    assert result.allowed is True
    assert result.requires_human_review is False


def test_neg_inf_confidence_falls_back_to_monitor():
    decision = make_decision(
        action="CUSTOMER_CONFIRMATION",
        confidence=float("-inf"),
    )

    result = SafetyController().evaluate(decision)

    assert result.action == "MONITOR"
    assert result.allowed is True
    assert result.requires_human_review is False


def test_invalid_confidence_cannot_execute_high_impact_action():
    for invalid_conf in [None, float("nan"), float("inf"), float("-inf")]:
        decision = make_decision(
            action="MANUAL_REVIEW",
            confidence=invalid_conf,
        )

        result = SafetyController().evaluate(decision)

        assert result.action == "MONITOR"
        assert result.allowed is True
