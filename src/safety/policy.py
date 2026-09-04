import math
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

    The policy explicitly controls which classes of actions
    can move from recommendation toward execution.
    """

    SUPPORTED_ACTIONS: Set[str] = {
        "MONITOR",
        "CUSTOMER_CONFIRMATION",
        "STEP_UP_VERIFICATION",
        "MANUAL_REVIEW",
    }

    ROUTE_SWITCH_PREFIX = "ROUTE_SWITCH:"

    # Transactions above this value require human review
    # before a non-monitor intervention is permitted.
    HIGH_VALUE_THRESHOLD = 100000.0

    # Extremely high-value transactions should never be
    # automatically acted upon.
    CRITICAL_VALUE_THRESHOLD = 500000.0

    def _is_supported_action(self, action: str) -> bool:
        """
        Validate both fixed actions and explicitly supported
        route-switch actions.
        """

        if action in self.SUPPORTED_ACTIONS:
            return True

        if action.startswith(self.ROUTE_SWITCH_PREFIX):
            route = action[len(self.ROUTE_SWITCH_PREFIX):].strip()

            # Empty route names are not valid.
            return bool(route)

        return False

    def evaluate(self, decision: Decision) -> PolicyResult:
        action = decision.recommended_action
        amount_at_risk = decision.expected_loss_before

        # -----------------------------------------------
        # Unknown action
        # -----------------------------------------------

        if not self._is_supported_action(action):
            return PolicyResult(
                allowed=False,
                requires_human_review=True,
                reason=(
                    f"Unsupported action '{action}'. "
                    "The safety policy does not permit it."
                ),
            )

        # -----------------------------------------------
        # Financial input validation
        # -----------------------------------------------

        if (
            amount_at_risk is None
            or not isinstance(amount_at_risk, (int, float))
            or not math.isfinite(amount_at_risk)
            or amount_at_risk < 0
        ):
            return PolicyResult(
                allowed=False,
                requires_human_review=True,
                reason=(
                    "Invalid financial exposure value. "
                    "Amount at risk must be a non-negative finite number."
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
        # Route recovery
        # -----------------------------------------------

        if action.startswith(self.ROUTE_SWITCH_PREFIX):
            return PolicyResult(
                allowed=True,
                requires_human_review=False,
                reason=(
                    "Route recovery passed deterministic safety "
                    "policy checks. Execution must remain bounded "
                    "and subject to recovery guardrails."
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
