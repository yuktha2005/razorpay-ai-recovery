from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class IncidentAssessment:
    route: str
    baseline_success_rate: float
    current_success_rate: float
    degradation_pp: float
    transactions_observed: int
    failures_observed: int
    severity: str
    incident_detected: bool
    explanation: str


class IncidentIntelligence:
    """
    Detects degradation in a payment route by comparing
    recent performance with historical baseline performance.

    This component intentionally does not use incident_ground_truth.
    """

    WATCH_DEGRADATION_PP = 5.0
    DEGRADED_DEGRADATION_PP = 10.0
    CRITICAL_DEGRADATION_PP = 20.0

    MIN_TRANSACTIONS_WATCH = 20
    MIN_TRANSACTIONS_DEGRADED = 30
    MIN_TRANSACTIONS_CRITICAL = 50

    def __init__(
        self,
        window_minutes: int = 15,
    ):
        if window_minutes <= 0:
            raise ValueError(
                "window_minutes must be greater than zero."
            )

        self.window_minutes = window_minutes

    def assess(
        self,
        route_data: pd.DataFrame,
        baseline_success_rate: Optional[float] = None,
    ) -> IncidentAssessment:
        """
        Assess the latest rolling window for a payment route.

        Required columns:
            timestamp
            status
        """

        required_columns = {
            "timestamp",
            "status",
        }

        missing = required_columns - set(route_data.columns)

        if missing:
            raise ValueError(
                f"Missing required columns: {sorted(missing)}"
            )

        if route_data.empty:
            raise ValueError(
                "Route dataset is empty."
            )

        data = route_data.copy()

        data["timestamp"] = pd.to_datetime(
            data["timestamp"],
            format="mixed",
            errors="coerce",
        )

        if data["timestamp"].isna().any():
            raise ValueError(
                "Route dataset contains invalid timestamps."
            )

        data = data.sort_values(
            "timestamp"
        ).reset_index(drop=True)

        # ----------------------------------------------
        # Baseline
        # ----------------------------------------------

        if baseline_success_rate is None:
            baseline_success_rate = (
                data["status"].eq("SUCCESS").mean()
            )

        baseline_success_rate = max(
            0.0,
            min(1.0, float(baseline_success_rate)),
        )

        # ----------------------------------------------
        # Latest rolling window
        # ----------------------------------------------

        latest_timestamp = data["timestamp"].max()

        window_start = (
            latest_timestamp
            - pd.Timedelta(
                minutes=self.window_minutes
            )
        )

        recent = data[
            data["timestamp"] >= window_start
        ]

        transactions_observed = len(recent)

        if transactions_observed == 0:
            return IncidentAssessment(
                route="UNKNOWN",
                baseline_success_rate=baseline_success_rate,
                current_success_rate=0.0,
                degradation_pp=0.0,
                transactions_observed=0,
                failures_observed=0,
                severity="NORMAL",
                incident_detected=False,
                explanation="No transactions observed in the monitoring window.",
            )

        successes = recent["status"].eq(
            "SUCCESS"
        ).sum()

        failures = recent["status"].eq(
            "FAILED"
        ).sum()

        current_success_rate = (
            successes / transactions_observed
        )

        degradation_pp = (
            baseline_success_rate
            - current_success_rate
        ) * 100

        # ----------------------------------------------
        # Severity
        # ----------------------------------------------

        severity = "NORMAL"

        if (
            transactions_observed >= self.MIN_TRANSACTIONS_WATCH
            and degradation_pp >= self.WATCH_DEGRADATION_PP
        ):
            severity = "WATCH"

        if (
            transactions_observed >= self.MIN_TRANSACTIONS_DEGRADED
            and degradation_pp >= self.DEGRADED_DEGRADATION_PP
        ):
            severity = "DEGRADED"

        if (
            transactions_observed >= self.MIN_TRANSACTIONS_CRITICAL
            and degradation_pp >= self.CRITICAL_DEGRADATION_PP
        ):
            severity = "CRITICAL"

        incident_detected = severity in {
            "DEGRADED",
            "CRITICAL",
        }

        route = self._build_route_name(
            recent
        )

        explanation = (
            f"Recent {self.window_minutes}-minute success rate "
            f"is {current_success_rate * 100:.2f}%, "
            f"compared with a baseline of "
            f"{baseline_success_rate * 100:.2f}%. "
            f"Observed degradation is "
            f"{degradation_pp:.2f} percentage points "
            f"across {transactions_observed} transactions."
        )

        return IncidentAssessment(
            route=route,
            baseline_success_rate=baseline_success_rate,
            current_success_rate=current_success_rate,
            degradation_pp=degradation_pp,
            transactions_observed=transactions_observed,
            failures_observed=failures,
            severity=severity,
            incident_detected=incident_detected,
            explanation=explanation,
        )

    @staticmethod
    def _build_route_name(
        data: pd.DataFrame,
    ) -> str:

        route_parts = []

        for column in [
            "payment_method",
            "bank",
            "device_type",
        ]:
            if column in data.columns:
                values = data[column].dropna().unique()

                if len(values) == 1:
                    route_parts.append(
                        str(values[0])
                    )

        if route_parts:
            return " + ".join(route_parts)

        return "UNKNOWN"