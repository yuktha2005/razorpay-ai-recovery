from src.models.domain import Decision
from src.safety.policy import SafetyPolicy


def make_decision(
    action="CUSTOMER_CONFIRMATION",
    expected_loss=5000.0,
):
    return Decision(
        payment_id="policy_test_001",
        recommended_action=action,
        confidence=0.90,
        expected_loss_before=expected_loss,
        expected_loss_after=2000.0,
        estimated_value=3000.0,
        explanation="Policy test",
    )


def test_supported_action_is_allowed():
    result = SafetyPolicy().evaluate(
        make_decision("CUSTOMER_CONFIRMATION")
    )

    assert result.allowed is True
    assert result.requires_human_review is False


def test_monitor_is_allowed():
    result = SafetyPolicy().evaluate(
        make_decision("MONITOR")
    )

    assert result.allowed is True
    assert result.requires_human_review is False


def test_unknown_action_is_denied():
    result = SafetyPolicy().evaluate(
        make_decision("BLOCK_ACCOUNT")
    )

    assert result.allowed is False
    assert result.requires_human_review is True


def test_high_value_intervention_requires_human_review():
    result = SafetyPolicy().evaluate(
        make_decision(
            "STEP_UP_VERIFICATION",
            expected_loss=150000.0,
        )
    )

    assert result.allowed is True
    assert result.requires_human_review is True


def test_critical_value_intervention_is_not_automatically_allowed():
    result = SafetyPolicy().evaluate(
        make_decision(
            "MANUAL_REVIEW",
            expected_loss=500000.0,
        )
    )

    assert result.allowed is False
    assert result.requires_human_review is True


def test_high_value_monitoring_can_continue():
    result = SafetyPolicy().evaluate(
        make_decision(
            "MONITOR",
            expected_loss=150000.0,
        )
    )

    assert result.allowed is True
    assert result.requires_human_review is False