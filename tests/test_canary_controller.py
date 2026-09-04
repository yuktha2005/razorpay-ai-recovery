from src.recovery.canary_controller import CanaryController


def test_small_canary_stops():
    controller = CanaryController()

    result = controller.evaluate(
        attempted_transactions=3,
        successful_recoveries=3,
        expected_recovery_rate=0.80,
    )

    assert result.decision == "STOP"


def test_good_canary_expands():
    controller = CanaryController()

    result = controller.evaluate(
        attempted_transactions=10,
        successful_recoveries=8,
        expected_recovery_rate=0.80,
    )

    assert result.decision == "EXPAND"


def test_weak_canary_stops():
    controller = CanaryController()

    result = controller.evaluate(
        attempted_transactions=10,
        successful_recoveries=5,
        expected_recovery_rate=0.80,
    )

    assert result.decision == "STOP"


def test_bad_canary_escalates():
    controller = CanaryController()

    result = controller.evaluate(
        attempted_transactions=10,
        successful_recoveries=3,
        expected_recovery_rate=0.80,
    )

    assert result.decision == "ESCALATE"


def test_zero_attempts_stops():
    controller = CanaryController()

    result = controller.evaluate(
        attempted_transactions=0,
        successful_recoveries=0,
        expected_recovery_rate=0.80,
    )

    assert result.decision == "STOP"


def test_zero_expected_recovery_rate_stops():
    controller = CanaryController()

    result = controller.evaluate(
        attempted_transactions=10,
        successful_recoveries=10,
        expected_recovery_rate=0.0,
    )

    assert result.decision == "STOP"
    assert result.canary_recovery_rate == 1.0
    assert result.expected_recovery_rate == 0.0
    assert "Expected recovery rate is too low" in result.reason


def test_near_zero_expected_recovery_rate_stops():
    controller = CanaryController()

    result = controller.evaluate(
        attempted_transactions=10,
        successful_recoveries=10,
        expected_recovery_rate=0.05,
    )

    assert result.decision == "STOP"
    assert result.canary_recovery_rate == 1.0
    assert result.expected_recovery_rate == 0.05
    assert "Expected recovery rate is too low" in result.reason


def test_normal_expected_rate_allows_expand():
    controller = CanaryController()

    result = controller.evaluate(
        attempted_transactions=10,
        successful_recoveries=8,
        expected_recovery_rate=0.80,
    )

    assert result.decision == "EXPAND"
    assert result.canary_recovery_rate == 0.80
    assert result.expected_recovery_rate == 0.80
