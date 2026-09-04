from src.tracking.recovery_outcome import RecoveryOutcomeVerifier


def test_successful_recovery():
    verifier = RecoveryOutcomeVerifier()

    result = verifier.verify(
        transaction_amounts=[1000, 2000, 1500, 500],
        successful_recoveries=3,
        failed_recoveries=1,
        execution_cost=50,
    )

    assert result.attempted_transactions == 4
    assert result.successful_recoveries == 3
    assert result.failed_recoveries == 1

    assert result.attempted_amount == 5000
    assert result.recovered_amount == 4500

    assert result.execution_cost == 50
    assert result.net_recovered_value == 4450

    assert result.recovery_rate == 0.75
    assert result.outcome_status == "RECOVERED"


def test_no_execution():
    verifier = RecoveryOutcomeVerifier()

    result = verifier.verify(
        transaction_amounts=[],
        successful_recoveries=0,
        failed_recoveries=0,
        execution_cost=0,
    )

    assert result.attempted_transactions == 0
    assert result.recovered_amount == 0
    assert result.net_recovered_value == 0
    assert result.recovery_rate == 0
    assert result.outcome_status == "NO_EXECUTION"


def test_no_recovery():
    verifier = RecoveryOutcomeVerifier()

    result = verifier.verify(
        transaction_amounts=[1000, 2000],
        successful_recoveries=0,
        failed_recoveries=2,
        execution_cost=50,
    )

    assert result.recovered_amount == 0
    assert result.net_recovered_value == -50
    assert result.outcome_status == "NO_RECOVERY"


def test_unprofitable_recovery():
    verifier = RecoveryOutcomeVerifier()

    result = verifier.verify(
        transaction_amounts=[100],
        successful_recoveries=1,
        failed_recoveries=0,
        execution_cost=200,
    )

    assert result.recovered_amount == 100
    assert result.net_recovered_value == -100
    assert result.outcome_status == "UNPROFITABLE"


def test_negative_amount_rejected():
    verifier = RecoveryOutcomeVerifier()

    try:
        verifier.verify(
            transaction_amounts=[1000, -500],
            successful_recoveries=1,
            failed_recoveries=0,
            execution_cost=25,
        )
        assert False
    except ValueError:
        assert True


def test_inconsistent_recovery_counts_rejected():
    verifier = RecoveryOutcomeVerifier()

    try:
        verifier.verify(
            transaction_amounts=[1000, 2000],
            successful_recoveries=2,
            failed_recoveries=2,
            execution_cost=25,
        )
        assert False
    except ValueError:
        assert True


def test_successful_transactions_not_necessarily_first_n_transactions():
    verifier = RecoveryOutcomeVerifier()

    # Transactions 1 ($1000) and 3 ($3000) failed.
    # Transactions 2 ($2000) and 4 ($4000) succeeded.
    result = verifier.verify(
        transaction_amounts=[1000.0, 2000.0, 3000.0, 4000.0],
        successful_recoveries=2,
        failed_recoveries=2,
        execution_cost=50.0,
        successful_transaction_amounts=[2000.0, 4000.0],
    )

    # If it had taken the first 2 attempted, it would be 1000 + 2000 = 3000.
    # With actual successful amounts, it is 2000 + 4000 = 6000.
    assert result.recovered_amount == 6000.0
    assert result.attempted_amount == 10000.0
    assert result.successful_recoveries == 2
    assert result.failed_recoveries == 2
    assert result.net_recovered_value == 5950.0
    assert result.outcome_status == "RECOVERED"


def test_recovered_amount_equals_sum_of_actual_successful_amounts():
    verifier = RecoveryOutcomeVerifier()

    successful_amounts = [150.25, 349.75, 500.0]
    result = verifier.verify(
        transaction_amounts=[150.25, 349.75, 500.0, 800.0],
        successful_recoveries=3,
        failed_recoveries=1,
        execution_cost=25.0,
        successful_transaction_amounts=successful_amounts,
    )

    assert result.recovered_amount == sum(successful_amounts)
    assert result.recovered_amount == 1000.0
    assert result.attempted_amount == 1800.0
    assert result.net_recovered_value == 975.0


def test_mismatch_between_successful_recoveries_and_amounts_raises_value_error():
    verifier = RecoveryOutcomeVerifier()

    # Fewer amounts than successful_recoveries
    try:
        verifier.verify(
            transaction_amounts=[1000.0, 2000.0, 3000.0],
            successful_recoveries=2,
            failed_recoveries=1,
            execution_cost=25.0,
            successful_transaction_amounts=[1000.0],
        )
        assert False
    except ValueError as e:
        assert "Length of successful transaction amounts" in str(e)

    # More amounts than successful_recoveries
    try:
        verifier.verify(
            transaction_amounts=[1000.0, 2000.0, 3000.0],
            successful_recoveries=1,
            failed_recoveries=2,
            execution_cost=25.0,
            successful_transaction_amounts=[1000.0, 2000.0],
        )
        assert False
    except ValueError as e:
        assert "Length of successful transaction amounts" in str(e)


def test_negative_successful_transaction_amount_raises_value_error():
    verifier = RecoveryOutcomeVerifier()

    try:
        verifier.verify(
            transaction_amounts=[1000.0, 2000.0],
            successful_recoveries=2,
            failed_recoveries=0,
            execution_cost=25.0,
            successful_transaction_amounts=[1000.0, -50.0],
        )
        assert False
    except ValueError as e:
        assert "Successful transaction amounts cannot be negative" in str(e)


def test_legacy_behavior_without_successful_transaction_amounts():
    verifier = RecoveryOutcomeVerifier()

    result = verifier.verify(
        transaction_amounts=[1000.0, 2000.0, 3000.0],
        successful_recoveries=2,
        failed_recoveries=1,
        execution_cost=50.0,
        successful_transaction_amounts=None,
    )

    # Legacy behavior takes the first N (2) attempted amounts: 1000 + 2000 = 3000
    assert result.recovered_amount == 3000.0
    assert result.attempted_amount == 6000.0
    assert result.net_recovered_value == 2950.0
