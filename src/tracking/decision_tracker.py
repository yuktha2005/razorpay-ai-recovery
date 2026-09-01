import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.models.domain import (
    Decision,
    Outcome,
    RiskAssessment,
    SafetyDecision,
)


BASE_DIR = Path(__file__).resolve().parent.parent.parent

TRACKING_DIR = BASE_DIR / "logs"

DECISION_LOG = TRACKING_DIR / "ai_decision_events.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionTracker:
    """
    Persistent tracker for the new AI decision pipeline.

    This tracker records AI reasoning and outcomes separately
    from the existing recovery audit system.

    It does NOT execute payments and does NOT modify Razorpay.
    """

    def __init__(
        self,
        log_file: Optional[Path] = None,
    ):
        self.log_file = (
            log_file
            if log_file is not None
            else DECISION_LOG
        )

        self.log_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _write_event(
        self,
        event_type: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:

        event = {
            "timestamp": utc_now(),
            "event_type": event_type,
            **data,
        }

        with open(
            self.log_file,
            "a",
            encoding="utf-8",
        ) as file:

            file.write(
                json.dumps(
                    event,
                    default=str,
                )
                + "\n"
            )

        return event

    def record_decision(
        self,
        risk: RiskAssessment,
        decision: Decision,
        safety: SafetyDecision,
    ) -> Dict[str, Any]:
        """
        Record one complete AI decision.

        Captures:

        - risk assessment
        - expected-loss decision
        - recommended intervention
        - confidence
        - safety result
        - human-review requirement
        """

        return self._write_event(
            "AI_DECISION",
            {
                "payment_id": decision.payment_id,

                "risk": {
                    "risk_score": risk.risk_score,
                    "risk_level": risk.risk_level,
                    "probability_of_loss":
                        risk.probability_of_loss,
                    "risk_type": risk.risk_type,
                    "reasons": risk.reasons,
                    "model_version":
                        risk.model_version,
                },

                "decision": {
                    "recommended_action":
                        decision.recommended_action,
                    "confidence":
                        decision.confidence,
                    "expected_loss_before":
                        decision.expected_loss_before,
                    "expected_loss_after":
                        decision.expected_loss_after,
                    "estimated_value":
                        decision.estimated_value,
                    "explanation":
                        decision.explanation,
                },

                "safety": {
                    "action":
                        safety.action,
                    "allowed":
                        safety.allowed,
                    "reason":
                        safety.reason,
                    "requires_human_review":
                        safety.requires_human_review,
                },
            },
        )

    def record_outcome(
        self,
        outcome: Outcome,
    ) -> Dict[str, Any]:
        """
        Record the actual outcome of an intervention.
        """

        return self._write_event(
            "INTERVENTION_OUTCOME",
            {
                "payment_id":
                    outcome.payment_id,

                "outcome": {
                    "action":
                        outcome.action,
                    "outcome_status":
                        outcome.outcome_status,
                    "actual_loss":
                        outcome.actual_loss,
                    "recovered_amount":
                        outcome.recovered_amount,
                    "loss_prevented":
                        outcome.loss_prevented,
                    "timestamp":
                        outcome.timestamp,
                },
            },
        )