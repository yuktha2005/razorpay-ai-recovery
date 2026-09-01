from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PaymentEvent:
    payment_id: str
    order_id: Optional[str]
    amount_rupees: float
    currency: str
    event_type: str
    payment_status: str
    payment_method: Optional[str] = None
    customer_id: Optional[str] = None
    device_id: Optional[str] = None
    ip_hash: Optional[str] = None
    timestamp: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskAssessment:
    payment_id: str
    risk_score: float
    risk_level: str
    probability_of_loss: float
    risk_type: str
    reasons: List[str] = field(default_factory=list)
    model_version: str = "baseline-v1"


@dataclass
class LossEstimate:
    payment_id: str
    financial_exposure: float
    probability_of_loss: float
    expected_loss: float
    currency: str = "INR"


@dataclass
class Intervention:
    action: str
    estimated_cost: float
    expected_loss_after: float
    expected_benefit: float
    customer_friction: float
    explanation: str = ""


@dataclass
class Decision:
    payment_id: str
    recommended_action: str
    confidence: float
    expected_loss_before: float
    expected_loss_after: float
    estimated_value: float
    alternatives: List[Intervention] = field(default_factory=list)
    explanation: str = ""


@dataclass
class SafetyDecision:
    payment_id: str
    action: str
    allowed: bool
    reason: str
    requires_human_review: bool = False


@dataclass
class Outcome:
    payment_id: str
    action: str
    outcome_status: str
    actual_loss: float = 0.0
    recovered_amount: float = 0.0
    loss_prevented: float = 0.0
    timestamp: str = field(default_factory=utc_now)