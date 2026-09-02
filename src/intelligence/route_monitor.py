from dataclasses import dataclass

import pandas as pd

from src.intelligence.baseline import RouteBaselineBuilder
from src.intelligence.incident_intelligence import (
    IncidentAssessment,
    IncidentIntelligence,
)


@dataclass
class RouteMonitoringResult:
    route: str
    baseline_success_rate: float
    assessment: IncidentAssessment


class RouteMonitor:
    """
    Combines historical route baselines with rolling
    incident detection.

    The baseline is calculated only from transactions
    before the monitoring period.
    """

    def __init__(
        self,
        window_minutes: int = 15,
    ):
        self.baseline_builder = RouteBaselineBuilder()

        self.incident_detector = IncidentIntelligence(
            window_minutes=window_minutes
        )

    def monitor(
        self,
        df: pd.DataFrame,
        payment_method: str,
        bank: str,
        device_type: str,
        monitoring_start: pd.Timestamp,
        monitoring_end: pd.Timestamp,
    ) -> RouteMonitoringResult:

        monitoring_start = pd.Timestamp(
            monitoring_start
        )

        monitoring_end = pd.Timestamp(
            monitoring_end
        )

        if monitoring_end <= monitoring_start:
            raise ValueError(
                "monitoring_end must be after monitoring_start."
            )

        # --------------------------------------------------
        # Historical data
        # --------------------------------------------------

        historical = df[
            pd.to_datetime(
                df["timestamp"],
                format="mixed",
                errors="coerce",
            )
            < monitoring_start
        ].copy()

        if historical.empty:
            raise ValueError(
                "No historical data exists before "
                "the monitoring period."
            )

        # --------------------------------------------------
        # Get clean route baseline
        # --------------------------------------------------

        baseline = (
            self.baseline_builder.get_route_baseline(
                historical,
                payment_method=payment_method,
                bank=bank,
                device_type=device_type,
            )
        )

        # --------------------------------------------------
        # Monitoring-period transactions
        # --------------------------------------------------

        data = df.copy()

        data["timestamp"] = pd.to_datetime(
            data["timestamp"],
            format="mixed",
            errors="coerce",
        )

        if data["timestamp"].isna().any():
            raise ValueError(
                "Dataset contains invalid timestamps."
            )

        route_data = data[
            (data["payment_method"] == payment_method)
            & (data["bank"] == bank)
            & (data["device_type"] == device_type)
            & (data["timestamp"] >= monitoring_start)
            & (data["timestamp"] <= monitoring_end)
        ].copy()

        if route_data.empty:
            raise ValueError(
                "No route transactions found "
                "during the monitoring period."
            )

        # --------------------------------------------------
        # Detect incident
        # --------------------------------------------------

        assessment = self.incident_detector.assess(
            route_data,
            baseline_success_rate=baseline.success_rate,
        )

        return RouteMonitoringResult(
            route=baseline.route,
            baseline_success_rate=baseline.success_rate,
            assessment=assessment,
        )