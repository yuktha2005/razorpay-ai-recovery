def test_route_switch_action_is_supported():
    from src.models.domain import Decision
    from src.safety.policy import SafetyPolicy

    decision = Decision(
        payment_id="route_test_001",
        recommended_action="ROUTE_SWITCH:UPI + Bank_C + Android",
        confidence=0.95,
        expected_loss_before=50000.0,
        expected_loss_after=10000.0,
        estimated_value=40000.0,
        alternatives=[],
        explanation="Alternative route has better observed reliability.",
    )

    result = SafetyPolicy().evaluate(decision)

    assert result.allowed is True
    assert result.requires_human_review is False


def test_empty_route_switch_is_rejected():
    from src.models.domain import Decision
    from src.safety.policy import SafetyPolicy

    decision = Decision(
        payment_id="route_test_002",
        recommended_action="ROUTE_SWITCH:",
        confidence=0.95,
        expected_loss_before=50000.0,
        expected_loss_after=10000.0,
        estimated_value=40000.0,
        alternatives=[],
        explanation="Invalid route.",
    )

    result = SafetyPolicy().evaluate(decision)

    assert result.allowed is False
    assert result.requires_human_review is True


def test_high_value_route_switch_requires_human_review():
    from src.models.domain import Decision
    from src.safety.policy import SafetyPolicy

    decision = Decision(
        payment_id="route_test_003",
        recommended_action="ROUTE_SWITCH:UPI + Bank_C + Android",
        confidence=0.95,
        expected_loss_before=150000.0,
        expected_loss_after=30000.0,
        estimated_value=120000.0,
        alternatives=[],
        explanation="High-value route recovery.",
    )

    result = SafetyPolicy().evaluate(decision)

    assert result.allowed is True
    assert result.requires_human_review is True


def test_critical_value_route_switch_is_blocked():
    from src.models.domain import Decision
    from src.safety.policy import SafetyPolicy

    decision = Decision(
        payment_id="route_test_004",
        recommended_action="ROUTE_SWITCH:UPI + Bank_C + Android",
        confidence=0.99,
        expected_loss_before=500000.0,
        expected_loss_after=50000.0,
        estimated_value=450000.0,
        alternatives=[],
        explanation="Critical-value route recovery.",
    )

    result = SafetyPolicy().evaluate(decision)

    assert result.allowed is False
    assert result.requires_human_review is True


def test_negative_amount_at_risk_is_rejected():
    from src.models.domain import Decision
    from src.safety.policy import SafetyPolicy

    decision = Decision(
        payment_id="finance_test_001",
        recommended_action="ROUTE_SWITCH:UPI + Bank_C + Android",
        confidence=0.95,
        expected_loss_before=-100.0,
        expected_loss_after=0.0,
        estimated_value=100.0,
        alternatives=[],
        explanation="Negative financial value.",
    )

    result = SafetyPolicy().evaluate(decision)

    assert result.allowed is False
    assert result.requires_human_review is True
    assert "Invalid financial exposure value" in result.reason


def test_nan_amount_at_risk_is_rejected():
    from src.models.domain import Decision
    from src.safety.policy import SafetyPolicy

    decision = Decision(
        payment_id="finance_test_002",
        recommended_action="ROUTE_SWITCH:UPI + Bank_C + Android",
        confidence=0.95,
        expected_loss_before=float("nan"),
        expected_loss_after=0.0,
        estimated_value=100.0,
        alternatives=[],
        explanation="NaN financial value.",
    )

    result = SafetyPolicy().evaluate(decision)

    assert result.allowed is False
    assert result.requires_human_review is True
    assert "Invalid financial exposure value" in result.reason


def test_inf_amount_at_risk_is_rejected():
    from src.models.domain import Decision
    from src.safety.policy import SafetyPolicy

    decision = Decision(
        payment_id="finance_test_003",
        recommended_action="ROUTE_SWITCH:UPI + Bank_C + Android",
        confidence=0.95,
        expected_loss_before=float("inf"),
        expected_loss_after=0.0,
        estimated_value=100.0,
        alternatives=[],
        explanation="Infinite financial value.",
    )

    result = SafetyPolicy().evaluate(decision)

    assert result.allowed is False
    assert result.requires_human_review is True
    assert "Invalid financial exposure value" in result.reason


def test_neg_inf_amount_at_risk_is_rejected():
    from src.models.domain import Decision
    from src.safety.policy import SafetyPolicy

    decision = Decision(
        payment_id="finance_test_004",
        recommended_action="ROUTE_SWITCH:UPI + Bank_C + Android",
        confidence=0.95,
        expected_loss_before=float("-inf"),
        expected_loss_after=0.0,
        estimated_value=100.0,
        alternatives=[],
        explanation="Negative infinite financial value.",
    )

    result = SafetyPolicy().evaluate(decision)

    assert result.allowed is False
    assert result.requires_human_review is True
    assert "Invalid financial exposure value" in result.reason
