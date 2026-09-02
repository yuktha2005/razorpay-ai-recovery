from src.recovery.bounded_executor import BoundedRecoveryExecutor


def test_monitor_does_not_execute():
    executor = BoundedRecoveryExecutor()

    result = executor.execute(
        action="MONITOR",
        transaction_amounts=[1000, 2000, 3000],
        simulated_success_rate=0.90,
    )

    assert result.status == "NOT_EXECUTED"
    assert result.attempted_transactions == 0
    assert result.successful_recoveries == 0


def test_canary_limits_execution():
    executor = BoundedRecoveryExecutor(
        max_transactions=50,
        recovery_budget=5000,
        canary_percentage=0.10,
    )

    transactions = [1000] * 100

    result = executor.execute(
        action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        transaction_amounts=transactions,
        simulated_success_rate=0.90,
    )

    # 10% of 100 transactions = 10
    assert result.attempted_transactions <= 10


def test_max_transaction_limit():
    executor = BoundedRecoveryExecutor(
        max_transactions=5,
        recovery_budget=5000,
        canary_percentage=1.0,
    )

    transactions = [1000] * 100

    result = executor.execute(
        action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        transaction_amounts=transactions,
        simulated_success_rate=0.90,
    )

    assert result.attempted_transactions <= 5


def test_budget_limit():
    executor = BoundedRecoveryExecutor(
        max_transactions=50,
        recovery_budget=50,
        canary_percentage=1.0,
    )

    transactions = [1000] * 100

    result = executor.execute(
        action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        transaction_amounts=transactions,
        simulated_success_rate=0.90,
    )

    # Each simulated recovery costs ₹25.
    # ₹50 budget allows at most 2 attempts.
    assert result.attempted_transactions <= 2
    assert result.estimated_cost <= 50


def test_execution_stops_when_failure_rate_is_high():
    executor = BoundedRecoveryExecutor(
        max_transactions=50,
        recovery_budget=5000,
        canary_percentage=1.0,
    )

    transactions = [1000] * 20

    result = executor.execute(
        action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        transaction_amounts=transactions,
        simulated_success_rate=0.0,
    )

    assert result.status == "STOPPED"
    assert result.failed_recoveries > 0
    assert (
        "failure rate"
        in result.stop_reason.lower()
    )


def test_negative_transaction_amount_is_rejected():
    executor = BoundedRecoveryExecutor()

    try:
        executor.execute(
            action="ROUTE_SWITCH:UPI + Bank_Y + Android",
            transaction_amounts=[1000, -500],
            simulated_success_rate=0.90,
        )
        assert False
    except ValueError:
        assert True