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