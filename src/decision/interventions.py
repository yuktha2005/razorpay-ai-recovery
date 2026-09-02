from typing import List, Optional

from src.models.domain import Intervention, LossEstimate


class InterventionLibrary:
    """
    Generates candidate interventions for a payment-loss or
    payment-route degradation case.

    Recommendations only.
    No payment action is executed by this class.
    """

    def generate(
        self,
        loss_estimate: LossEstimate,
        alternative_routes: Optional[List[dict]] = None,
    ) -> List[Intervention]:

        expected_loss = loss_estimate.expected_loss

        interventions = [
            Intervention(
                action="MONITOR",
                estimated_cost=0.0,
                expected_loss_after=round(expected_loss, 2),
                expected_benefit=0.0,
                customer_friction=0.0,
                explanation=(
                    "No intervention. Continue monitoring the payment "
                    "or affected route."
                ),
            ),
            Intervention(
                action="CUSTOMER_CONFIRMATION",
                estimated_cost=10.0,
                expected_loss_after=round(expected_loss * 0.65, 2),
                expected_benefit=round(
                    expected_loss
                    - (expected_loss * 0.65)
                    - 10.0,
                    2,
                ),
                customer_friction=0.15,
                explanation=(
                    "Ask the customer to confirm the transaction "
                    "before taking stronger action."
                ),
            ),
            Intervention(
                action="STEP_UP_VERIFICATION",
                estimated_cost=30.0,
                expected_loss_after=round(expected_loss * 0.35, 2),
                expected_benefit=round(
                    expected_loss
                    - (expected_loss * 0.35)
                    - 30.0,
                    2,
                ),
                customer_friction=0.30,
                explanation=(
                    "Apply additional verification to reduce "
                    "the probability of loss."
                ),
            ),
            Intervention(
                action="MANUAL_REVIEW",
                estimated_cost=300.0,
                expected_loss_after=round(expected_loss * 0.20, 2),
                expected_benefit=round(
                    expected_loss
                    - (expected_loss * 0.20)
                    - 300.0,
                    2,
                ),
                customer_friction=0.60,
                explanation=(
                    "Send the transaction to a human reviewer "
                    "for further investigation."
                ),
            ),
        ]

        # ---------------------------------------------------------
        # Route-level recovery candidates
        # ---------------------------------------------------------
        #
        # Each route dictionary may contain:
        #
        # {
        #     "route": "UPI + Bank_A + Android",
        #     "success_rate": 0.95,
        #     "transactions": 500,
        #     "confidence": 0.85,
        # }
        #
        # These candidates are recommendations only.
        # The actual routing layer must enforce safety policies.
        # ---------------------------------------------------------

        if alternative_routes:
            for route in alternative_routes:

                route_name = route.get("route", "UNKNOWN_ROUTE")
                success_rate = float(route.get("success_rate", 0.0))
                transactions = int(route.get("transactions", 0))
                route_confidence = float(
                    route.get("confidence", 0.0)
                )

                # Ignore unusable candidates.
                if transactions <= 0:
                    continue

                if success_rate <= 0:
                    continue

                # Estimated residual loss after moving to this route.
                expected_loss_after = expected_loss * (
                    1.0 - success_rate
                )

                # Small operational cost for a bounded route intervention.
                estimated_cost = 25.0

                expected_benefit = (
                    expected_loss
                    - expected_loss_after
                    - estimated_cost
                )

                interventions.append(
                    Intervention(
                        action=f"ROUTE_SWITCH:{route_name}",
                        estimated_cost=estimated_cost,
                        expected_loss_after=round(
                            expected_loss_after,
                            2,
                        ),
                        expected_benefit=round(
                            expected_benefit,
                            2,
                        ),
                        customer_friction=0.05,
                        explanation=(
                            f"Consider a bounded route switch to "
                            f"{route_name}. Observed success rate is "
                            f"{success_rate:.2%} across "
                            f"{transactions} transactions, with "
                            f"route evidence confidence "
                            f"{route_confidence:.2f}."
                        ),
                    )
                )

        return interventions