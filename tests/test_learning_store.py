from types import SimpleNamespace

from src.tracking.learning_store import (
    LEARNING_COLUMNS,
    load_learning_history,
    save_route_learning,
)


def test_learning_record_is_persisted(tmp_path, monkeypatch):
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

    stats = SimpleNamespace(
        route="UPI + Bank_Y + Android",
        attempts=10,
        recoveries=8,
        recovery_rate=0.75,
        total_recovered_value=8000,
        total_execution_cost=250,
        net_recovered_value=7750,
        evidence_confidence=0.50,
    )

    record = save_route_learning(
        stats=stats,
        timestamp="2026-09-02T10:00:00",
    )

    assert learning_file.exists()

    assert record["route"] == (
        "UPI + Bank_Y + Android"
    )

    assert record["attempts"] == 10
    assert record["recoveries"] == 8
    assert record["recovered_value"] == 8000


def test_learning_history_can_be_loaded(
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

    stats = SimpleNamespace(
        route="UPI + Bank_Y + Android",
        attempts=10,
        recoveries=8,
        recovery_rate=0.75,
        total_recovered_value=8000,
        total_execution_cost=250,
        net_recovered_value=7750,
        evidence_confidence=0.50,
    )

    save_route_learning(
        stats=stats,
        timestamp="2026-09-02T10:00:00",
    )

    history = load_learning_history()

    assert len(history) == 1
    assert history[0]["route"] == (
        "UPI + Bank_Y + Android"
    )
    assert history[0]["attempts"] == "10"
    assert history[0]["recoveries"] == "8"


def test_multiple_learning_records_are_preserved(
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

    first_stats = SimpleNamespace(
        route="UPI + Bank_Y + Android",
        attempts=10,
        recoveries=8,
        recovery_rate=0.75,
        total_recovered_value=8000,
        total_execution_cost=250,
        net_recovered_value=7750,
        evidence_confidence=0.50,
    )

    second_stats = SimpleNamespace(
        route="UPI + Bank_C + Android",
        attempts=20,
        recoveries=12,
        recovery_rate=0.60,
        total_recovered_value=12000,
        total_execution_cost=500,
        net_recovered_value=11500,
        evidence_confidence=0.67,
    )

    save_route_learning(
        stats=first_stats,
        timestamp="2026-09-02T10:00:00",
    )

    save_route_learning(
        stats=second_stats,
        timestamp="2026-09-02T10:05:00",
    )

    history = load_learning_history()

    assert len(history) == 2

    assert history[0]["route"] == (
        "UPI + Bank_Y + Android"
    )

    assert history[1]["route"] == (
        "UPI + Bank_C + Android"
    )


def test_learning_schema_is_stable(
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

    # Trigger store initialization.
    history = load_learning_history()

    assert history == []
    assert learning_file.exists()

    with open(
        learning_file,
        "r",
        encoding="utf-8",
    ) as file:

        header = file.readline().strip().split(",")

    assert header == LEARNING_COLUMNS