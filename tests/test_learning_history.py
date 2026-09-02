from src.tracking.learning_history import (
    PersistentLearningHistory,
)


def test_persisted_route_can_be_loaded(
    tmp_path,
    monkeypatch,
):
    learning_file = (
        tmp_path / "recovery_learning.csv"
    )

    monkeypatch.setattr(
        "src.tracking.learning_store.LEARNING_FILE",
        learning_file,
    )

    monkeypatch.setattr(
        "src.tracking.learning_store.LOG_DIR",
        tmp_path,
    )

    # Write a realistic persisted learning record.
    learning_file.write_text(
        (
            "timestamp,route,attempts,recoveries,"
            "recovery_rate,recovered_value,"
            "execution_cost,net_recovered_value,"
            "evidence_confidence\n"
            "2026-09-02T10:00:00,"
            "UPI + Bank_Y + Android,"
            "10,8,0.75,8000,250,7750,0.5\n"
        ),
        encoding="utf-8",
    )

    history = PersistentLearningHistory()

    result = history.get_route(
        "UPI + Bank_Y + Android"
    )

    assert result is not None
    assert result.route == (
        "UPI + Bank_Y + Android"
    )
    assert result.attempts == 10
    assert result.recoveries == 8
    assert result.recovery_rate == 0.75
    assert result.total_recovered_value == 8000
    assert result.total_execution_cost == 250
    assert result.net_recovered_value == 7750
    assert result.evidence_confidence == 0.5


def test_multiple_routes_are_loaded(
    tmp_path,
    monkeypatch,
):
    learning_file = (
        tmp_path / "recovery_learning.csv"
    )

    monkeypatch.setattr(
        "src.tracking.learning_store.LEARNING_FILE",
        learning_file,
    )

    monkeypatch.setattr(
        "src.tracking.learning_store.LOG_DIR",
        tmp_path,
    )

    learning_file.write_text(
        (
            "timestamp,route,attempts,recoveries,"
            "recovery_rate,recovered_value,"
            "execution_cost,net_recovered_value,"
            "evidence_confidence\n"
            "2026-09-02T10:00:00,"
            "UPI + Bank_Y + Android,"
            "10,8,0.75,8000,250,7750,0.5\n"
            "2026-09-02T10:05:00,"
            "UPI + Bank_C + Android,"
            "20,12,0.6,12000,500,11500,0.6667\n"
        ),
        encoding="utf-8",
    )

    history = PersistentLearningHistory()

    routes = history.load()

    assert len(routes) == 2

    route_names = {
        route.route
        for route in routes
    }

    assert "UPI + Bank_Y + Android" in route_names
    assert "UPI + Bank_C + Android" in route_names


def test_unknown_persisted_route_returns_none(
    tmp_path,
    monkeypatch,
):
    learning_file = (
        tmp_path / "recovery_learning.csv"
    )

    monkeypatch.setattr(
        "src.tracking.learning_store.LEARNING_FILE",
        learning_file,
    )

    monkeypatch.setattr(
        "src.tracking.learning_store.LOG_DIR",
        tmp_path,
    )

    learning_file.write_text(
        (
            "timestamp,route,attempts,recoveries,"
            "recovery_rate,recovered_value,"
            "execution_cost,net_recovered_value,"
            "evidence_confidence\n"
        ),
        encoding="utf-8",
    )

    history = PersistentLearningHistory()

    result = history.get_route(
        "UPI + UnknownBank + Android"
    )

    assert result is None


def test_persisted_routes_can_be_ranked(
    tmp_path,
    monkeypatch,
):
    learning_file = (
        tmp_path / "recovery_learning.csv"
    )

    monkeypatch.setattr(
        "src.tracking.learning_store.LEARNING_FILE",
        learning_file,
    )

    monkeypatch.setattr(
        "src.tracking.learning_store.LOG_DIR",
        tmp_path,
    )

    learning_file.write_text(
        (
            "timestamp,route,attempts,recoveries,"
            "recovery_rate,recovered_value,"
            "execution_cost,net_recovered_value,"
            "evidence_confidence\n"
            "2026-09-02T10:00:00,"
            "UPI + Bank_A + Android,"
            "2,2,0.6,2000,50,1950,0.1667\n"
            "2026-09-02T10:05:00,"
            "UPI + Bank_Y + Android,"
            "100,75,0.75,75000,2500,72500,0.9091\n"
        ),
        encoding="utf-8",
    )

    history = PersistentLearningHistory()

    ranked = history.rank_routes()

    assert ranked[0].route == (
        "UPI + Bank_Y + Android"
    )


def test_malformed_numeric_values_use_safe_defaults(
    tmp_path,
    monkeypatch,
):
    learning_file = (
        tmp_path / "recovery_learning.csv"
    )

    monkeypatch.setattr(
        "src.tracking.learning_store.LEARNING_FILE",
        learning_file,
    )

    monkeypatch.setattr(
        "src.tracking.learning_store.LOG_DIR",
        tmp_path,
    )

    learning_file.write_text(
        (
            "timestamp,route,attempts,recoveries,"
            "recovery_rate,recovered_value,"
            "execution_cost,net_recovered_value,"
            "evidence_confidence\n"
            "2026-09-02T10:00:00,"
            "UPI + Bank_Y + Android,"
            "invalid,invalid,invalid,invalid,"
            "invalid,invalid,invalid\n"
        ),
        encoding="utf-8",
    )

    history = PersistentLearningHistory()

    result = history.get_route(
        "UPI + Bank_Y + Android"
    )

    assert result is not None
    assert result.attempts == 0
    assert result.recoveries == 0
    assert result.recovery_rate == 0
    assert result.total_recovered_value == 0
    assert result.total_execution_cost == 0
    assert result.net_recovered_value == 0
    assert result.evidence_confidence == 0