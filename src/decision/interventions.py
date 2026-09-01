from typing import List

from src.models.domain import Intervention, LossEstimate


class InterventionLibrary:
    """
    Generates candidate interventions for a payment-loss case.

    These are recommendations only. No payment action is
    executed by this class.
    """

    def generate(
        self,
        loss_estimate: LossEstimate,
    ) -> List[Intervention]:

        expected_loss = loss_estimate.expected_loss

        return [
            Intervention(
                action="MONITOR",
                estimated_cost=0.0,
                expected_loss_after=round(expected_loss, 2),
                expected_benefit=0.0,
                customer_friction=0.0,
                explanation=(
                    "No intervention. Continue monitoring the payment."
                ),
            ),
            Intervention(
                action="CUSTOMER_CONFIRMATION",
                estimated_cost=10.0,
                expected_loss_after=round(
                    expected_loss * 0.65, 2
                ),
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
                expected_loss_after=round(
                    expected_loss * 0.35, 2
                ),
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
                expected_loss_after=round(
                    expected_loss * 0.20, 2
                ),
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