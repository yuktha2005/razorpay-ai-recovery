from src.tracking.outcome_evaluator import OutcomeEvaluator


def test_successful_recovery():
    result = OutcomeEvaluator().evaluate(
        payment_id="outcome_test_001",
        predicted_action="MANUAL_REVIEW",
        expected_loss=37500.0,
        actual_action="MANUAL_REVIEW",
        actual_loss=0.0,
        recovered_amount=37500.0,
        loss_prevented=37500.0,
    )

    assert result.prediction_status == "SUCCESS"
    assert result.financial_error == -37500.0
    assert result.recovered_amount == 37500.0
    assert result.loss_prevented == 37500.0


def test_loss_was_underpredicted():
    result = OutcomeEvaluator().evaluate(
        payment_id="outcome_test_002",
        predicted_action="RETRY_PAYMENT",
        expected_loss=1000.0,
        actual_action="RETRY_PAYMENT",
        actual_loss=2500.0,
        recovered_amount=0.0,
        loss_prevented=0.0,
    )

    assert result.prediction_status == "UNDERPREDICTED_LOSS"
    assert result.financial_error == 1500.0


def test_action_changed():
    result = OutcomeEvaluator().evaluate(
        payment_id="outcome_test_003",
        predicted_action="RETRY_PAYMENT",
        expected_loss=5000.0,
        actual_action="MANUAL_REVIEW",
        actual_loss=0.0,
        recovered_amount=5000.0,
        loss_prevented=5000.0,
    )

    assert result.prediction_status == "ACTION_CHANGED"
    assert result.predicted_action == "RETRY_PAYMENT"
    assert result.actual_action == "MANUAL_REVIEW"


def test_zero_loss_prediction():
    result = OutcomeEvaluator().evaluate(
        payment_id="outcome_test_004",
        predicted_action="MONITOR",
        expected_loss=0.0,
        actual_action="MONITOR",
        actual_loss=0.0,
        recovered_amount=0.0,
        loss_prevented=0.0,
    )

    assert result.prediction_status == "SUCCESS"
    assert result.financial_error == 0.0


def test_negative_values_are_clamped():
    result = OutcomeEvaluator().evaluate(
        payment_id="outcome_test_005",
        predicted_action="MONITOR",
        expected_loss=-100.0,
        actual_action="MONITOR",
        actual_loss=-50.0,
        recovered_amount=-20.0,
        loss_prevented=-10.0,
    )

    assert result.expected_loss == 0.0
    assert result.actual_loss == 0.0
    assert result.recovered_amount == 0.0
    assert result.loss_prevented == 0.0
    assert result.financial_error == 0.0