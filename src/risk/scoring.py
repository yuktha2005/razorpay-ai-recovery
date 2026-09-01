from src.models.domain import RiskAssessment
from src.risk.features import PaymentFeatures


class PaymentRiskScorer:
    """
    Baseline payment-loss risk scorer.

    This is deliberately transparent and deterministic.
    It gives us a baseline that we can later compare
    against a trained ML model.
    """

    MODEL_VERSION = "baseline-v1"

    def score(
        self,
        payment_id: str,
        features: PaymentFeatures,
    ) -> RiskAssessment:

        score = 0.0
        reasons = []

        # --------------------------------------------------
        # Amount anomaly
        # --------------------------------------------------

        ratio = features.amount_deviation_ratio

        if ratio >= 10:
            score += 30
            reasons.append(
                "Transaction amount is significantly above "
                "the customer's historical average."
            )

        elif ratio >= 5:
            score += 20
            reasons.append(
                "Transaction amount is substantially above "
                "the customer's historical average."
            )

        elif ratio >= 2:
            score += 10
            reasons.append(
                "Transaction amount is above the customer's "
                "historical spending pattern."
            )

        # --------------------------------------------------
        # Device
        # --------------------------------------------------

        if features.new_device:
            score += 15
            reasons.append(
                "Transaction originated from a new device."
            )

        # --------------------------------------------------
        # Location
        # --------------------------------------------------

        if features.new_location:
            score += 10
            reasons.append(
                "Transaction originated from an unusual location."
            )

        # --------------------------------------------------
        # Transaction velocity
        # --------------------------------------------------

        if features.velocity_5m >= 5:
            score += 20
            reasons.append(
                "Unusually high transaction activity within five minutes."
            )

        elif features.velocity_5m >= 3:
            score += 10
            reasons.append(
                "Elevated transaction activity within five minutes."
            )

        # --------------------------------------------------
        # Previous disputes
        # --------------------------------------------------

        if features.previous_disputes >= 2:
            score += 15
            reasons.append(
                "Customer has multiple previous disputes."
            )

        elif features.previous_disputes == 1:
            score += 7
            reasons.append(
                "Customer has a previous dispute history."
            )

        # --------------------------------------------------
        # Previous payment failures
        # --------------------------------------------------

        if features.previous_failures >= 3:
            score += 8
            reasons.append(
                "Customer has several previous payment failures."
            )

        # --------------------------------------------------
        # Delivery
        # --------------------------------------------------

        if not features.delivery_confirmed:
            score += 10
            reasons.append(
                "Delivery confirmation is currently unavailable."
            )

        # --------------------------------------------------
        # Merchant dispute rate
        # --------------------------------------------------

        if features.merchant_dispute_rate >= 0.05:
            score += 15
            reasons.append(
                "Merchant's dispute rate is elevated."
            )

        elif features.merchant_dispute_rate >= 0.02:
            score += 7
            reasons.append(
                "Merchant's dispute rate is above baseline."
            )

        # --------------------------------------------------
        # Clamp score
        # --------------------------------------------------

        score = min(100.0, score)

        probability = score / 100.0

        if score >= 75:
            risk_level = "HIGH"

        elif score >= 45:
            risk_level = "MEDIUM"

        else:
            risk_level = "LOW"

        if not reasons:
            reasons.append(
                "No significant risk indicators detected."
            )

        return RiskAssessment(
            payment_id=payment_id,
            risk_score=round(score, 2),
            risk_level=risk_level,
            probability_of_loss=round(probability, 4),
            risk_type="PAYMENT_LOSS",
            reasons=reasons,
            model_version=self.MODEL_VERSION,
        )