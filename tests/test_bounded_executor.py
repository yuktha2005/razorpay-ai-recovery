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
    assert result.successful_transaction_amounts == []


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


def test_successful_transaction_amounts_recorded():
    executor = BoundedRecoveryExecutor(
        max_transactions=10,
        recovery_budget=5000,
        canary_percentage=1.0,
    )

    transactions = [1200.50, 450.0, 999.99, 1500.0]

    result = executor.execute(
        action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        transaction_amounts=transactions,
        simulated_success_rate=1.0,
    )

    assert result.status == "COMPLETED"
    assert result.attempted_transactions == 4
    assert result.successful_recoveries == 4
    assert result.successful_transaction_amounts == [1200.50, 450.0, 999.99, 1500.0]
    assert len(result.successful_transaction_amounts) == result.successful_recoveries


def test_successful_transaction_amounts_length_equals_successful_recoveries():
    executor = BoundedRecoveryExecutor(
        max_transactions=10,
        recovery_budget=5000,
        canary_percentage=1.0,
    )

    transactions = [500.0, 1000.0, 1500.0, 2000.0, 2500.0, 3000.0, 3500.0, 4000.0]

    result = executor.execute(
        action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        transaction_amounts=transactions,
        simulated_success_rate=0.90,
    )

    assert len(result.successful_transaction_amounts) == result.successful_recoveries
    assert all(isinstance(amt, float) for amt in result.successful_transaction_amounts)
    # The failed transaction at index 8 (simulated_score 96 >= 90) should not be present
    assert 4000.0 not in result.successful_transaction_amounts
    assert result.successful_recoveries == 7
    assert len(result.successful_transaction_amounts) == 7


def test_monitor_returns_empty_successful_transaction_amounts():
    executor = BoundedRecoveryExecutor()

    result = executor.execute(
        action="MONITOR",
        transaction_amounts=[500.0, 1500.0],
        simulated_success_rate=0.95,
    )

    assert result.status == "NOT_EXECUTED"
    assert result.successful_transaction_amounts == []
    assert len(result.successful_transaction_amounts) == 0


def test_not_executed_zero_budget_returns_empty_list():
    executor = BoundedRecoveryExecutor(
        max_transactions=10,
        recovery_budget=10.0,
        canary_percentage=1.0,
    )

    result = executor.execute(
        action="ROUTE_SWITCH:UPI + Bank_Y + Android",
        transaction_amounts=[1000.0, 2000.0],
        simulated_success_rate=0.90,
    )

    assert result.status == "NOT_EXECUTED"
    assert result.attempted_transactions == 0
    assert result.successful_recoveries == 0
    assert result.successful_transaction_amounts == []
