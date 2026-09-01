from dataclasses import dataclass
from typing import Set

from src.models.domain import Decision


@dataclass
class PolicyResult:
    allowed: bool
    requires_human_review: bool
    reason: str


class SafetyPolicy:
    """
    Deterministic business and safety policies.

    This layer is intentionally independent of the AI model.
    """

    SUPPORTED_ACTIONS: Set[str] = {
        "MONITOR",
        "CUSTOMER_CONFIRMATION",
        "STEP_UP_VERIFICATION",
        "MANUAL_REVIEW",
    }

    # Transactions above this value require human review
    # before a non-monitor intervention is permitted.
    HIGH_VALUE_THRESHOLD = 100000.0

    # Extremely high-value transactions should never be
    # automatically acted upon.
    CRITICAL_VALUE_THRESHOLD = 500000.0

    def evaluate(self, decision: Decision) -> PolicyResult:
        action = decision.recommended_action
        amount_at_risk = decision.expected_loss_before

        # -----------------------------------------------
        # Unknown action
        # -----------------------------------------------

        if action not in self.SUPPORTED_ACTIONS:
            return PolicyResult(
                allowed=False,
                requires_human_review=True,
                reason=(
                    f"Unsupported action '{action}'. "
                    "The safety policy does not permit it."
                ),
            )

        # -----------------------------------------------
        # Critical financial exposure
        # -----------------------------------------------

        if amount_at_risk >= self.CRITICAL_VALUE_THRESHOLD:
            return PolicyResult(
                allowed=False,
                requires_human_review=True,
                reason=(
                    "Financial exposure exceeds the critical "
                    "automated-action threshold."
                ),
            )

        # -----------------------------------------------
        # High financial exposure
        # -----------------------------------------------

        if (
            amount_at_risk >= self.HIGH_VALUE_THRESHOLD
            and action != "MONITOR"
        ):
            return PolicyResult(
                allowed=True,
                requires_human_review=True,
                reason=(
                    "High-value transaction requires human "
                    "review before intervention."
                ),
            )

        # -----------------------------------------------
        # Safe monitoring
        # -----------------------------------------------

        if action == "MONITOR":
            return PolicyResult(
                allowed=True,
                requires_human_review=False,
                reason=(
                    "Monitoring is a non-destructive action "
                    "and is permitted."
                ),
            )

        # -----------------------------------------------
        # Normal intervention
        # -----------------------------------------------

        return PolicyResult(
            allowed=True,
            requires_human_review=False,
            reason="Action passed deterministic safety policies.",
        )