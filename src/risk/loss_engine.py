from src.models.domain import LossEstimate, RiskAssessment


class ExpectedLossEngine:
    """
    Converts model risk into estimated financial exposure.

    Core principle:

        Expected Loss =
        Probability of Loss × Financial Exposure
    """

    def calculate(
        self,
        assessment: RiskAssessment,
        amount_rupees: float,
        currency: str = "INR",
    ) -> LossEstimate:

        if amount_rupees < 0:
            raise ValueError(
                "amount_rupees cannot be negative"
            )

        probability = max(
            0.0,
            min(1.0, assessment.probability_of_loss)
        )

        expected_loss = (
            probability * amount_rupees
        )

        return LossEstimate(
            payment_id=assessment.payment_id,
            financial_exposure=amount_rupees,
            probability_of_loss=probability,
            expected_loss=round(expected_loss, 2),
            currency=currency,
        )