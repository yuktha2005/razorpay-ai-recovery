from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd

from src.live_reporting.report_schema import (
    LiveOperationsReport,
    RouteHealth,
)


class LiveReportGenerator:
    """
    Generates synthetic real-time payment operations reports
    from the project's transaction dataset.

    The generated reports are simulation data and are not
    connected to live Razorpay production systems.
    """

    def __init__(self, baseline_success_rate: float = 0.9442):
        self.baseline_success_rate = baseline_success_rate

    def generate(
        self,
        transactions: pd.DataFrame,
        window_minutes: int = 15,
    ) -> LiveOperationsReport:

        required_columns = {
            "payment_method",
            "bank",
            "device_type",
            "status",
            "amount",
        }

        missing = required_columns - set(transactions.columns)

        if missing:
            raise ValueError(
                f"Missing required transaction columns: {sorted(missing)}"
            )

        df = transactions.copy()

        total_transactions = len(df)

        if total_transactions == 0:
            raise ValueError("Cannot generate a report from an empty dataset.")

        failures = df[
            df["status"].astype(str).str.upper()
            != "SUCCESS"
        ]

        total_failures = len(failures)

        overall_success_rate = (
            (total_transactions - total_failures)
            / total_transactions
        )

        failed_amount = float(failures["amount"].sum())

        expected_failures = (
            total_transactions
            * (1 - self.baseline_success_rate)
        )

        excess_failures = max(
            0.0,
            total_failures - expected_failures,
        )

        average_failed_amount = (
            failed_amount / total_failures
            if total_failures > 0
            else 0.0
        )

        revenue_at_risk = (
            excess_failures * average_failed_amount
        )

        route_health = []

        grouped = df.groupby(
            [
                "payment_method",
                "bank",
                "device_type",
            ],
            dropna=False,
        )

        for (
            payment_method,
            bank,
            device_type,
        ), group in grouped:

            route_transactions = len(group)

            route_failures = len(
                group[
                    group["status"].astype(str).str.upper()
                    != "SUCCESS"
                ]
            )

            route_success_rate = (
                (route_transactions - route_failures)
                / route_transactions
                if route_transactions
                else 0.0
            )

            degradation_pp = (
                self.baseline_success_rate
                - route_success_rate
            ) * 100

            if (
                degradation_pp >= 20
                and route_transactions >= 50
            ):
                severity = "CRITICAL"
            elif (
                degradation_pp >= 10
                and route_transactions >= 30
            ):
                severity = "DEGRADED"
            elif (
                degradation_pp >= 5
                and route_transactions >= 20
            ):
                severity = "WATCH"
            else:
                severity = "HEALTHY"

            route = (
                f"{payment_method} + "
                f"{bank} + "
                f"{device_type}"
            )

            route_health.append(
                RouteHealth(
                    route=route,
                    payment_method=str(payment_method),
                    bank=str(bank),
                    device_type=str(device_type),
                    transactions=route_transactions,
                    failures=route_failures,
                    success_rate=route_success_rate,
                    baseline_success_rate=self.baseline_success_rate,
                    degradation_pp=degradation_pp,
                    severity=severity,
                )
            )

        route_health.sort(
            key=lambda item: item.degradation_pp,
            reverse=True,
        )

        routes_monitored = len(route_health)

        healthy_routes = sum(
            route.severity == "HEALTHY"
            for route in route_health
        )

        degraded_routes = sum(
            route.severity in {"WATCH", "DEGRADED"}
            for route in route_health
        )

        critical_routes = sum(
            route.severity == "CRITICAL"
            for route in route_health
        )

        top_degraded_route = (
            route_health[0].route
            if route_health
            else "NONE"
        )

        return LiveOperationsReport(
            report_id=f"LIVE-{uuid4().hex[:10].upper()}",
            generated_at=datetime.now(
                timezone.utc
            ).isoformat(),

            window_minutes=window_minutes,

            total_transactions=total_transactions,
            total_failures=total_failures,
            overall_success_rate=overall_success_rate,
            baseline_success_rate=self.baseline_success_rate,

            revenue_at_risk=revenue_at_risk,
            failed_amount=failed_amount,

            routes_monitored=routes_monitored,
            healthy_routes=healthy_routes,
            degraded_routes=degraded_routes,
            critical_routes=critical_routes,

            top_degraded_route=top_degraded_route,
            route_health=route_health,
        )