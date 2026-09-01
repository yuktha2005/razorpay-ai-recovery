from typing import List

from src.models.domain import (
    Decision,
    Intervention,
    LossEstimate,
)


class InterventionOptimizer:
    """
    Selects the intervention with the highest positive
    expected financial value.

    This component recommends actions only.
    It never executes payment operations.
    """

    def optimize(
        self,
        loss_estimate: LossEstimate,
        interventions: List[Intervention],
        confidence: float = 0.0,
    ) -> Decision:

        if not interventions:
            return Decision(
                payment_id=loss_estimate.payment_id,
                recommended_action="MONITOR",
                confidence=confidence,
                expected_loss_before=loss_estimate.expected_loss,
                expected_loss_after=loss_estimate.expected_loss,
                estimated_value=0.0,
                alternatives=[],
                explanation=(
                    "No intervention candidates are available."
                ),
            )

        profitable = [
            intervention
            for intervention in interventions
            if intervention.expected_benefit > 0
        ]

        if not profitable:
            return Decision(
                payment_id=loss_estimate.payment_id,
                recommended_action="MONITOR",
                confidence=confidence,
                expected_loss_before=loss_estimate.expected_loss,
                expected_loss_after=loss_estimate.expected_loss,
                estimated_value=0.0,
                alternatives=interventions,
                explanation=(
                    "No available intervention provides "
                    "positive expected financial value."
                ),
            )

        best = max(
            profitable,
            key=lambda intervention: intervention.expected_benefit,
        )

        return Decision(
            payment_id=loss_estimate.payment_id,
            recommended_action=best.action,
            confidence=confidence,
            expected_loss_before=loss_estimate.expected_loss,
            expected_loss_after=best.expected_loss_after,
            estimated_value=best.expected_benefit,
            alternatives=interventions,
            explanation=best.explanation,
        )