from dataclasses import dataclass
from typing import Optional

import pandas as pd

from src.decision.incident_decision_engine import (
    IncidentDecisionEngine,
    IncidentDecisionResult,
)
from src.intelligence.incident_revenue import (
    IncidentRevenueCalculator,
)
from src.live_reporting.incident_generator import (
    SyntheticIncident,
)


@dataclass
class LiveDecisionResult:
    incident: SyntheticIncident
    decision_result: IncidentDecisionResult


class LiveDecisionAdapter:
    """
    Connects the synthetic live incident layer to the existing
    IncidentDecisionEngine.

    This adapter does not implement new decision logic. It prepares
    live incident data for the authoritative decision engine.
    """

    def __init__(
        self,
        decision_engine: Optional[IncidentDecisionEngine] = None,
    ):
        self.decision_engine = (
            decision_engine
            or IncidentDecisionEngine()
        )

        self.revenue_calculator = (
            IncidentRevenueCalculator()
        )

    @staticmethod
    def _parse_route(route: str):
        parts = [
            part.strip()
            for part in route.split("+")
        ]

        if len(parts) != 3:
            raise ValueError(
                "Route must have the format: "
                "PAYMENT_METHOD + BANK + DEVICE_TYPE"
            )

        return parts[0], parts[1], parts[2]

    @staticmethod
    def _build_route_candidates(
        transactions: pd.DataFrame,
        incident_route: str,
    ) -> list:

        candidates = []

        grouped = transactions.groupby(
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

            route = (
                f"{payment_method} + "
                f"{bank} + "
                f"{device_type}"
            )

            if route == incident_route:
                continue

            transactions_count = len(group)

            successes = int(
                group["status"].eq("SUCCESS").sum()
            )

            candidates.append(
                {
                    "route": route,
                    "transactions": transactions_count,
                    "successes": successes,
                }
            )

        return candidates

    def evaluate(
        self,
        incident: SyntheticIncident,
        transactions: pd.DataFrame,
    ) -> LiveDecisionResult:

        payment_method, bank, device_type = (
            self._parse_route(incident.route)
        )

        incident_data = transactions.copy()

        incident_data["timestamp"] = pd.to_datetime(
            incident_data["timestamp"],
            format="mixed",
            errors="coerce",
        )

        incident_data = incident_data.dropna(
            subset=["timestamp"]
        )

        incident_end = (
            incident_data["timestamp"].max()
        )

        incident_start = (
            incident_end
            - pd.Timedelta(
                minutes=15
            )
        )

        incident_route_data = incident_data[
            (
                incident_data["payment_method"]
                == payment_method
            )
            & (
                incident_data["bank"]
                == bank
            )
            & (
                incident_data["device_type"]
                == device_type
            )
        ].copy()

        if incident_route_data.empty:
            raise ValueError(
                f"No transaction data found for incident route: "
                f"{incident.route}"
            )

        average_transaction_value = float(
            incident_route_data["amount"].mean()
        )

        route_candidates = (
            self._build_route_candidates(
                transactions=incident_data,
                incident_route=incident.route,
            )
        )

        decision_result = (
            self.decision_engine.evaluate(
                incident_route=incident.route,
                transactions_affected=(
                    incident.final_transactions
                ),
                failures_observed=(
                    incident.final_failures
                ),
                baseline_success_rate=(
                    incident.assessment
                    .baseline_success_rate
                ),
                current_success_rate=(
                    incident.assessment
                    .current_success_rate
                ),
                severity=(
                    incident.assessment.severity
                ),
                average_transaction_value=(
                    average_transaction_value
                ),
                route_candidates=route_candidates,
                revenue_impact=None,
            )
        )

        return LiveDecisionResult(
            incident=incident,
            decision_result=decision_result,
        )