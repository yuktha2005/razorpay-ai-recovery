"""
AI Revenue Recovery
Recovery Agent

Combines:
    Revenue Risk Engine
    Safety Controller

The agent proposes a recovery action, but the safety
controller has final authority over whether that action
can execute.
"""

from typing import Dict, Any

from revenue_risk_engine import RevenueRiskEngine


class RecoveryAgent:

    def __init__(self):
        self.risk_engine = RevenueRiskEngine()

    def evaluate(
        self,
        payment: Dict[str, Any],
        system_state: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:

        if system_state is None:
            system_state = {
                "bank_status": "healthy",
                "recovery_route_status": "healthy",
                "ai_confidence": 0.90,
            }

        # ---------------------------------------------------------
        # 1. Analyze revenue risk
        # ---------------------------------------------------------

        risk = self.risk_engine.analyze(payment)

        # ---------------------------------------------------------
        # 2. Proposed action
        # ---------------------------------------------------------

        proposed_action = risk.recommended_action

        # ---------------------------------------------------------
        # 3. Safety constraints
        # ---------------------------------------------------------

        bank_status = system_state.get("bank_status", "healthy")
        recovery_route_status = system_state.get(
            "recovery_route_status",
            "healthy"
        )
        ai_confidence = float(
            system_state.get("ai_confidence", 0.0)
        )

        # ---------------------------------------------------------
        # 4. Safety decision
        # ---------------------------------------------------------

        if ai_confidence < 0.70:
            decision = "ESCALATE"
            reason = "AI confidence is below the safety threshold."

        elif recovery_route_status != "healthy":
            decision = "STOP"
            reason = "Recovery route is unhealthy."

        elif bank_status == "degraded":
            decision = "RECOVER"
            reason = "Bank degradation detected; bounded recovery is allowed."

        elif proposed_action in [
            "RETRY_PAYMENT",
            "CUSTOMER_RETRY",
            "CUSTOMER_RETRY_LATER",
        ]:
            decision = "RECOVER"
            reason = "Recovery action passed safety checks."

        else:
            decision = "ESCALATE"
            reason = "No safe automatic recovery action is available."

        # ---------------------------------------------------------
        # 5. Build agent decision
        # ---------------------------------------------------------

        return {
            "agent": "AI Revenue Recovery Agent",

            "payment": payment,

            "risk_assessment": risk.to_dict(),

            "proposed_action": proposed_action,

            "system_state": system_state,

            "safety_decision": decision,

            "safety_reason": reason,

            "execution_allowed": decision == "RECOVER",
        }


# =========================================================
# DEMO
# =========================================================

if __name__ == "__main__":

    agent = RecoveryAgent()

    payment = {
        "payment_id": "pay_demo_001",
        "order_id": "order_demo_001",
        "amount_rupees": 750,
        "currency": "INR",
        "payment_status": "failed",
        "payment_method": "netbanking",
        "failure_reason": "bank timeout",
    }

    result = agent.evaluate(payment)

    print("=" * 70)
    print("AI REVENUE RECOVERY AGENT")
    print("=" * 70)

    print("\nPAYMENT")
    print("-" * 70)
    print(f"Payment ID       : {payment['payment_id']}")
    print(f"Amount           : ₹{payment['amount_rupees']:.2f}")
    print(f"Failure          : {payment['failure_reason']}")

    print("\nRISK ASSESSMENT")
    print("-" * 70)

    risk = result["risk_assessment"]

    print(f"Category         : {risk['failure_category']}")
    print(f"Risk score       : {risk['risk_score']}")
    print(f"Risk level       : {risk['risk_level']}")
    print(f"Revenue at risk  : ₹{risk['revenue_at_risk']:.2f}")

    print("\nAGENT DECISION")
    print("-" * 70)
    print(f"Proposed action  : {result['proposed_action']}")
    print(f"Safety decision  : {result['safety_decision']}")
    print(f"Reason           : {result['safety_reason']}")
    print(f"Execution allowed: {result['execution_allowed']}")

    print("=" * 70)