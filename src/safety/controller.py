from src.models.domain import Decision, SafetyDecision
from src.safety.policy import SafetyPolicy


class SafetyController:
    """
    Deterministic safety layer between AI recommendations
    and downstream execution.

    The AI recommends.
    The safety controller decides whether the recommendation
    is permitted.

    Safety checks are performed in two stages:

    1. AI confidence checks
    2. Deterministic business/safety policy checks
    """

    MINIMUM_CONFIDENCE = 0.50
    HIGH_IMPACT_CONFIDENCE = 0.90

    HIGH_IMPACT_ACTIONS = {
        "BLOCK",
        "MANUAL_REVIEW",
    }

    def __init__(self):
        self.policy = SafetyPolicy()

    def evaluate(self, decision: Decision) -> SafetyDecision:
        confidence = max(
            0.0,
            min(1.0, decision.confidence),
        )

        action = decision.recommended_action

        # --------------------------------------------------
        # Stage 1: AI confidence safety check
        # --------------------------------------------------

        if confidence < self.MINIMUM_CONFIDENCE:
            return SafetyDecision(
                payment_id=decision.payment_id,
                action="MONITOR",
                allowed=True,
                reason=(
                    "AI confidence is below the minimum "
                    "decision threshold."
                ),
                requires_human_review=False,
            )

        # --------------------------------------------------
        # Stage 2: High-impact confidence check
        # --------------------------------------------------

        if (
            action in self.HIGH_IMPACT_ACTIONS
            and confidence < self.HIGH_IMPACT_CONFIDENCE
        ):
            return SafetyDecision(
                payment_id=decision.payment_id,
                action="MANUAL_REVIEW",
                allowed=True,
                reason=(
                    "High-impact action requires higher "
                    "AI confidence and human review."
                ),
                requires_human_review=True,
            )

        # --------------------------------------------------
        # Stage 3: Deterministic policy evaluation
        # --------------------------------------------------

        policy_result = self.policy.evaluate(decision)

        if not policy_result.allowed:
            return SafetyDecision(
                payment_id=decision.payment_id,
                action="MONITOR",
                allowed=False,
                reason=policy_result.reason,
                requires_human_review=(
                    policy_result.requires_human_review
                ),
            )

        # --------------------------------------------------
        # Stage 4: Policy requires human review
        # --------------------------------------------------

        if policy_result.requires_human_review:
            return SafetyDecision(
                payment_id=decision.payment_id,
                action=action,
                allowed=False,
                reason=policy_result.reason,
                requires_human_review=True,
            )

        # --------------------------------------------------
        # Stage 5: Action passed all safety checks
        # --------------------------------------------------

        return SafetyDecision(
            payment_id=decision.payment_id,
            action=action,
            allowed=True,
            reason=policy_result.reason,
            requires_human_review=False,
        )