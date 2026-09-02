from dataclasses import dataclass

import pandas as pd


@dataclass
class IncidentRevenueImpact:
    incident_transactions: int
    incident_failures: int

    baseline_failure_rate: float
    expected_failures: float
    excess_failures: float

    actual_failed_amount: float
    expected_failed_amount: float
    revenue_at_risk: float


class IncidentRevenueCalculator:
    """
    Calculates the financial impact of a payment-route incident.

    The calculation compares the incident period against a clean
    historical baseline for the same payment route.
    """

    def calculate(
        self,
        df: pd.DataFrame,
        payment_method: str,
        bank: str,
        device_type: str,
        incident_start,
        incident_end,
    ) -> IncidentRevenueImpact:

        if df.empty:
            raise ValueError("Transaction dataframe cannot be empty.")

        required_columns = {
            "payment_method",
            "bank",
            "device_type",
            "timestamp",
            "status",
            "amount",
        }

        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {sorted(missing_columns)}"
            )

        data = df.copy()

        data["timestamp"] = pd.to_datetime(
            data["timestamp"],
            format="mixed",
        )

        route_mask = (
            (data["payment_method"] == payment_method)
            & (data["bank"] == bank)
            & (data["device_type"] == device_type)
        )

        route_data = data[route_mask].copy()

        incident_start = pd.Timestamp(incident_start)
        incident_end = pd.Timestamp(incident_end)

        # ---------------------------------------------------------
        # Incident period
        # ---------------------------------------------------------

        incident_data = route_data[
            (route_data["timestamp"] >= incident_start)
            & (route_data["timestamp"] < incident_end)
        ].copy()

        incident_transactions = len(incident_data)

        if incident_transactions == 0:
            return IncidentRevenueImpact(
                incident_transactions=0,
                incident_failures=0,
                baseline_failure_rate=0.0,
                expected_failures=0.0,
                excess_failures=0.0,
                actual_failed_amount=0.0,
                expected_failed_amount=0.0,
                revenue_at_risk=0.0,
            )

        incident_failures = int(
            (incident_data["status"] == "FAILED").sum()
        )

        # ---------------------------------------------------------
        # Historical baseline
        #
        # Only transactions BEFORE the incident are used.
        # This prevents the incident itself from contaminating
        # the baseline.
        # ---------------------------------------------------------

        baseline_data = route_data[
            route_data["timestamp"] < incident_start
        ].copy()

        if baseline_data.empty:
            raise ValueError(
                "No historical baseline data exists before the incident."
            )

        baseline_failures = int(
            (baseline_data["status"] == "FAILED").sum()
        )

        baseline_transactions = len(baseline_data)

        baseline_failure_rate = (
            baseline_failures / baseline_transactions
        )

        # ---------------------------------------------------------
        # Expected failures
        # ---------------------------------------------------------

        expected_failures = (
            incident_transactions * baseline_failure_rate
        )

        excess_failures = max(
            0.0,
            incident_failures - expected_failures,
        )

        # ---------------------------------------------------------
        # Financial impact
        # ---------------------------------------------------------

        actual_failed_amount = float(
            incident_data.loc[
                incident_data["status"] == "FAILED",
                "amount",
            ].sum()
        )

        baseline_average_amount = float(
            baseline_data["amount"].mean()
        )

        expected_failed_amount = (
            expected_failures * baseline_average_amount
        )

        # Revenue at risk represents the excess failed-payment
        # value compared with what would normally be expected.
        revenue_at_risk = max(
            0.0,
            actual_failed_amount - expected_failed_amount,
        )

        return IncidentRevenueImpact(
            incident_transactions=incident_transactions,
            incident_failures=incident_failures,
            baseline_failure_rate=round(
                baseline_failure_rate,
                6,
            ),
            expected_failures=round(
                expected_failures,
                2,
            ),
            excess_failures=round(
                excess_failures,
                2,
            ),
            actual_failed_amount=round(
                actual_failed_amount,
                2,
            ),
            expected_failed_amount=round(
                expected_failed_amount,
                2,
            ),
            revenue_at_risk=round(
                revenue_at_risk,
                2,
            ),
        )