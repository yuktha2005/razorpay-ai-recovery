from dataclasses import dataclass

from src.decision.interventions import InterventionLibrary
from src.decision.optimizer import InterventionOptimizer
from src.intelligence.incident_revenue import IncidentRevenueCalculator
from src.intelligence.route_scoring import rank_routes
from src.models.domain import Decision, LossEstimate
from src.safety.controller import SafetyController


@dataclass
class IncidentDecisionResult:
    incident_route: str

    transactions_affected: int
    failures_observed: int

    baseline_success_rate: float
    current_success_rate: float
    degradation_pp: float
    severity: str

    # Financial intelligence
    financial_exposure: float
    expected_loss: float
    revenue_at_risk: float
    excess_failures: float

    ranked_routes: list
    decision: Decision
    safety_decision: object


class IncidentDecisionEngine:
    """
    Converts a detected payment-route incident into a bounded
    recovery decision.

    Pipeline:

        Incident
          ↓
        Financial Impact
          ↓
        Route Ranking
          ↓
        Intervention Optimization
          ↓
        Safety Controller
          ↓
        Final Decision
    """

    def __init__(self):
        self.intervention_library = InterventionLibrary()
        self.optimizer = InterventionOptimizer()
        self.safety_controller = SafetyController()
        self.revenue_calculator = IncidentRevenueCalculator()

    def evaluate(
        self,
        incident_route: str,
        transactions_affected: int,
        failures_observed: int,
        baseline_success_rate: float,
        current_success_rate: float,
        severity: str,
        average_transaction_value: float,
        route_candidates: list,
        revenue_impact=None,
    ) -> IncidentDecisionResult:

        if transactions_affected <= 0:
            raise ValueError(
                "transactions_affected must be greater than zero."
            )

        if average_transaction_value < 0:
         raise ValueError(
        "average_transaction_value cannot be negative."
    )

        # ---------------------------------------------------------
        # 1. Calculate incident degradation
        # ---------------------------------------------------------

        degradation_pp = (
            baseline_success_rate - current_success_rate
        ) * 100

        # ---------------------------------------------------------
        # 2. Financial exposure
        #
        # This represents the total transaction value flowing
        # through the affected route during the incident.
        # ---------------------------------------------------------

        financial_exposure = (
    transactions_affected * average_transaction_value
)

        # Current probability of failure is used as a simple
        # incident-level expected-loss estimate.
        probability_of_loss = max(
            0.0,
            min(
                1.0,
                1.0 - current_success_rate,
            ),
        )

        expected_loss = (
            financial_exposure * probability_of_loss
        )

        # ---------------------------------------------------------
        # 3. Revenue-at-risk intelligence
        #
        # If a precomputed IncidentRevenueImpact is supplied,
        # use it. Otherwise preserve the engine's existing
        # expected-loss calculation.
        # ---------------------------------------------------------

        revenue_at_risk = expected_loss
        excess_failures = float(failures_observed)

        if revenue_impact is not None:
            revenue_at_risk = float(
                revenue_impact.revenue_at_risk
            )

            excess_failures = float(
                revenue_impact.excess_failures
            )

        # ---------------------------------------------------------
        # 4. Rank alternative payment routes
        # ---------------------------------------------------------

        ranked_routes = rank_routes(route_candidates)

        scored_routes = []

        for route in ranked_routes:
            scored_routes.append(
                {
                    "route": route.route,
                    "success_rate": route.adjusted_success_rate,
                    "transactions": route.transactions,
                    "confidence": route.evidence_confidence,
                }
            )

        # ---------------------------------------------------------
        # 5. Generate possible interventions
        # ---------------------------------------------------------

        loss_estimate = LossEstimate(
            payment_id=f"INCIDENT:{incident_route}",
            financial_exposure=financial_exposure,
            probability_of_loss=probability_of_loss,
            expected_loss=expected_loss,
            currency="INR",
        )

        interventions = self.intervention_library.generate(
            loss_estimate,
            alternative_routes=scored_routes,
        )

        # ---------------------------------------------------------
        # 6. Decision confidence
        #
        # For route switching, confidence comes from the evidence
        # behind the selected alternative route.
        # ---------------------------------------------------------

        if ranked_routes:
            decision_confidence = (
                ranked_routes[0].evidence_confidence
            )
        else:
            severity_confidence = {
                "CRITICAL": 0.90,
                "DEGRADED": 0.70,
                "WATCH": 0.50,
            }

            decision_confidence = severity_confidence.get(
                severity.upper(),
                0.50,
            )

        # ---------------------------------------------------------
        # 7. Optimize intervention
        # ---------------------------------------------------------

        decision = self.optimizer.optimize(
    loss_estimate=loss_estimate,
    interventions=interventions,
    confidence=decision_confidence,
)

        # ---------------------------------------------------------
        # 8. Apply deterministic safety controls
        # ---------------------------------------------------------

        safety_decision = self.safety_controller.evaluate(
            decision
        )

        return IncidentDecisionResult(
            incident_route=incident_route,
            transactions_affected=transactions_affected,
            failures_observed=failures_observed,
            baseline_success_rate=baseline_success_rate,
            current_success_rate=current_success_rate,
            degradation_pp=round(degradation_pp, 2),
            severity=severity,
            financial_exposure=round(
                financial_exposure,
                2,
            ),
            expected_loss=round(
                expected_loss,
                2,
            ),
            revenue_at_risk=round(
                revenue_at_risk,
                2,
            ),
            excess_failures=round(
                excess_failures,
                2,
            ),
            ranked_routes=ranked_routes,
            decision=decision,
            safety_decision=safety_decision,
        )