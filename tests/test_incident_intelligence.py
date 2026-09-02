import pandas as pd

from src.intelligence.incident_intelligence import (
    IncidentIntelligence,
)


DATA_PATH = "data/transactions.csv"


def load_route():
    df = pd.read_csv(DATA_PATH)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        format="mixed",
    )

    return df[
        (df["payment_method"] == "UPI")
        & (df["bank"] == "Bank_X")
        & (df["device_type"] == "Android")
    ].copy()


def test_known_incident_is_detected():
    route = load_route()

    normal = route[
        route["timestamp"]
        < "2026-07-23 19:00:00"
    ]

    incident = route[
        (route["timestamp"] >= "2026-07-23 19:00:00")
        & (route["timestamp"] < "2026-07-23 20:00:00")
    ]

    baseline = (
        normal["status"] == "SUCCESS"
    ).mean()

    result = IncidentIntelligence(
        window_minutes=60
    ).assess(
        incident,
        baseline_success_rate=baseline,
    )

    assert result.incident_detected is True
    assert result.severity == "CRITICAL"
    assert result.degradation_pp > 20
    assert result.transactions_observed >= 500


def test_normal_period_does_not_trigger_critical():
    route = load_route()

    normal = route[
        route["timestamp"]
        < "2026-07-23 19:00:00"
    ]

    baseline = (
        normal["status"] == "SUCCESS"
    ).mean()

    # Take a representative 60-minute normal window.
    start = normal["timestamp"].max() - pd.Timedelta(
        minutes=60
    )

    window = normal[
        normal["timestamp"] >= start
    ]

    result = IncidentIntelligence(
        window_minutes=60
    ).assess(
        window,
        baseline_success_rate=baseline,
    )

    assert result.severity != "CRITICAL"