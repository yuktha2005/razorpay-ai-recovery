from dataclasses import dataclass

import pandas as pd

from src.intelligence.incident_intelligence import (
    IncidentAssessment,
    IncidentIntelligence,
)


@dataclass
class SyntheticIncident:
    route: str
    original_transactions: int
    original_failures: int
    injected_failures: int
    final_transactions: int
    final_failures: int
    assessment: IncidentAssessment


class LiveIncidentGenerator:
    """
    Creates a controlled synthetic payment incident.

    The original transaction dataset is never modified.
    Incident data exists only in memory for simulation/demo use.
    """

    def __init__(
        self,
        baseline_success_rate: float = 0.9442,
        window_minutes: int = 15,
    ):
        self.baseline_success_rate = baseline_success_rate
        self.window_minutes = window_minutes

        self.intelligence = IncidentIntelligence(
            window_minutes=window_minutes
        )

    @staticmethod
    def build_route(
        payment_method: str,
        bank: str,
        device_type: str,
    ) -> str:
        return (
            f"{payment_method} + "
            f"{bank} + "
            f"{device_type}"
        )

    def create_incident_window(
        self,
        transactions: pd.DataFrame,
        payment_method: str,
        bank: str,
        device_type: str,
        sample_size: int = 100,
        target_success_rate: float = 0.70,
    ) -> SyntheticIncident:

        required_columns = {
            "payment_method",
            "bank",
            "device_type",
            "status",
            "timestamp",
        }

        missing = required_columns - set(transactions.columns)

        if missing:
            raise ValueError(
                f"Missing required columns: {sorted(missing)}"
            )

        if sample_size < 50:
            raise ValueError(
                "sample_size must be at least 50 "
                "for a meaningful incident simulation."
            )

        if not 0.0 <= target_success_rate <= 1.0:
            raise ValueError(
                "target_success_rate must be between 0 and 1."
            )

        data = transactions.copy()

        data["timestamp"] = pd.to_datetime(
            data["timestamp"],
            format="mixed",
            errors="coerce",
        )

        data = data.dropna(
            subset=["timestamp"]
        )

        route_mask = (
            data["payment_method"].astype(str)
            == str(payment_method)
        ) & (
            data["bank"].astype(str)
            == str(bank)
        ) & (
            data["device_type"].astype(str)
            == str(device_type)
        )

        route_data = (
            data[route_mask]
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

        if len(route_data) < sample_size:
            raise ValueError(
                f"Route has only {len(route_data)} transactions; "
                f"{sample_size} required."
            )

        # Use a deterministic historical slice.
        incident_window = route_data.tail(
            sample_size
        ).copy()
                # Compress the selected historical transactions into a
        # synthetic 15-minute live incident window.
        incident_end = incident_window["timestamp"].max()

        incident_start = (
            incident_end
            - pd.Timedelta(
                minutes=self.window_minutes
            )
        )

        synthetic_timestamps = pd.date_range(
            start=incident_start
            + pd.Timedelta(seconds=1),
            end=incident_end,
            periods=sample_size,
        )

        incident_window["timestamp"] = synthetic_timestamps

        original_transactions = len(incident_window)

        original_failures = int(
            incident_window["status"].eq("FAILED").sum()
        )

        desired_failures = int(
            round(
                original_transactions
                * (1.0 - target_success_rate)
            )
        )

        additional_failures = max(
            0,
            desired_failures - original_failures,
        )

        success_indices = list(
            incident_window.index[
                incident_window["status"].eq("SUCCESS")
            ]
        )

        if additional_failures > len(success_indices):
            additional_failures = len(success_indices)

        indices_to_fail = success_indices[
            :additional_failures
        ]

        incident_window.loc[
            indices_to_fail,
            "status",
        ] = "FAILED"

        final_failures = int(
            incident_window["status"].eq("FAILED").sum()
        )

        assessment = self.intelligence.assess(
            incident_window,
            baseline_success_rate=self.baseline_success_rate,
        )

        route = self.build_route(
            payment_method,
            bank,
            device_type,
        )

        return SyntheticIncident(
            route=route,
            original_transactions=original_transactions,
            original_failures=original_failures,
            injected_failures=additional_failures,
            final_transactions=len(incident_window),
            final_failures=final_failures,
            assessment=assessment,
        )