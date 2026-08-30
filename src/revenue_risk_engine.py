"""
AI Revenue Recovery
Revenue Risk Engine

Converts a failed payment into a structured revenue-risk assessment.

This module does NOT execute payments or refunds.
It only:
1. Calculates risk
2. Diagnoses likely failure category
3. Recommends a bounded recovery action
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class RevenueRisk:
    payment_id: str
    order_id: str

    amount_rupees: float
    currency: str

    failure_category: str
    risk_score: int
    risk_level: str

    revenue_at_risk: float
    recommended_action: str

    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RevenueRiskEngine:

    def analyze(self, payment: Dict[str, Any]) -> RevenueRisk:
        """
        Analyze a failed payment and determine revenue risk.
        """

        payment_id = payment.get("payment_id", "unknown")
        order_id = payment.get("order_id", "unknown")

        amount = float(payment.get("amount_rupees", 0))
        currency = payment.get("currency", "INR")

        failure_reason = (
            payment.get("failure_reason")
            or payment.get("error_description")
            or payment.get("reason")
            or ""
        ).lower()

        method = payment.get("payment_method", "unknown").lower()

        # ---------------------------------------------------------
        # 1. Diagnose failure category
        # ---------------------------------------------------------

        if any(word in failure_reason for word in [
            "insufficient",
            "balance",
            "funds"
        ]):
            failure_category = "INSUFFICIENT_FUNDS"

        elif any(word in failure_reason for word in [
            "timeout",
            "timed out",
            "network",
            "gateway",
            "technical"
        ]):
            failure_category = "TEMPORARY_TECHNICAL"

        elif any(word in failure_reason for word in [
            "declined",
            "bank",
            "issuer"
        ]):
            failure_category = "BANK_DECLINE"

        elif any(word in failure_reason for word in [
            "authentication",
            "otp",
            "verification"
        ]):
            failure_category = "AUTHENTICATION_FAILURE"

        else:
            failure_category = "UNKNOWN_FAILURE"

        # ---------------------------------------------------------
        # 2. Calculate risk score
        # ---------------------------------------------------------

        score = 50

        # Higher-value transactions deserve attention.
        if amount >= 10000:
            score += 20
        elif amount >= 5000:
            score += 15
        elif amount >= 1000:
            score += 10

        # Failure-specific weighting.
        if failure_category == "TEMPORARY_TECHNICAL":
            score += 20

        elif failure_category == "BANK_DECLINE":
            score += 15

        elif failure_category == "INSUFFICIENT_FUNDS":
            score += 10

        elif failure_category == "AUTHENTICATION_FAILURE":
            score += 5

        # Known payment methods are easier to recover.
        if method in ["card", "upi", "netbanking"]:
            score += 5

        score = min(score, 100)

        # ---------------------------------------------------------
        # 3. Risk level
        # ---------------------------------------------------------

        if score >= 80:
            risk_level = "HIGH"

        elif score >= 60:
            risk_level = "MEDIUM"

        else:
            risk_level = "LOW"

        # ---------------------------------------------------------
        # 4. Choose bounded intervention
        # ---------------------------------------------------------

        if failure_category == "TEMPORARY_TECHNICAL":
            recommended_action = "RETRY_PAYMENT"

            reason = (
                "Failure appears temporary. "
                "A bounded retry may recover the transaction."
            )

        elif failure_category == "BANK_DECLINE":
            recommended_action = "CUSTOMER_RETRY"

            reason = (
                "Bank declined the transaction. "
                "Ask the customer to retry or use another payment method."
            )

        elif failure_category == "INSUFFICIENT_FUNDS":
            recommended_action = "CUSTOMER_RETRY_LATER"

            reason = (
                "Insufficient funds detected. "
                "Immediate repeated retries should be avoided."
            )

        elif failure_category == "AUTHENTICATION_FAILURE":
            recommended_action = "CUSTOMER_RETRY"

            reason = (
                "Authentication failed. "
                "Customer should retry authentication."
            )

        else:
            recommended_action = "ESCALATE"

            reason = (
                "Failure reason is uncertain. "
                "Human review is safer than automatic recovery."
            )

        return RevenueRisk(
            payment_id=payment_id,
            order_id=order_id,
            amount_rupees=amount,
            currency=currency,
            failure_category=failure_category,
            risk_score=score,
            risk_level=risk_level,
            revenue_at_risk=amount,
            recommended_action=recommended_action,
            reason=reason,
        )


# =========================================================
# DEMO
# =========================================================

if __name__ == "__main__":

    engine = RevenueRiskEngine()

    test_payment = {
        "payment_id": "pay_demo_001",
        "order_id": "order_demo_001",
        "amount_rupees": 750,
        "currency": "INR",
        "payment_status": "failed",
        "payment_method": "netbanking",
        "failure_reason": "bank timeout",
    }

    result = engine.analyze(test_payment)

    print("=" * 65)
    print("AI REVENUE RECOVERY — REVENUE RISK ENGINE")
    print("=" * 65)

    for key, value in result.to_dict().items():
        print(f"{key:25}: {value}")

    print("=" * 65)