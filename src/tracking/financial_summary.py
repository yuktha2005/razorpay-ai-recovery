from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class FinancialSummary:
    """
    Authoritative financial summary of incident impact and bounded recovery.

    Preserves the distinction between pre-execution estimates (revenue at risk)
    and post-execution measured outcomes (actual bounded recovery results).
    """

    revenue_at_risk: float
    eligible_amount: float
    attempted_amount: float
    recovered_amount: float
    execution_cost: float
    net_recovered_value: float
    recovery_rate: float
    recovery_roi: Optional[float]
    roi_display: str
    has_executed: bool = False


def calculate_financial_summary(
    revenue_at_risk: float = 0.0,
    eligible_amount: float = 0.0,
    batch_result: Optional[Dict[str, Any]] = None,
    recovery_outcome: Optional[Any] = None,
) -> FinancialSummary:
    """
    Construct an authoritative FinancialSummary.

    If recovery has not been executed yet (both batch_result and recovery_outcome
    are None), post-execution fields are safely zeroed with has_executed=False.

    When executed, metrics are extracted strictly from the authoritative
    RecoveryOutcome or batch_result, computing ROI safely without division by zero.
    """
    revenue_at_risk = round(float(revenue_at_risk or 0.0), 2)
    eligible_amount = round(float(eligible_amount or 0.0), 2)

    has_executed = False
    attempted_amount = 0.0
    recovered_amount = 0.0
    execution_cost = 0.0
    net_recovered_value = 0.0
    recovery_rate = 0.0

    if recovery_outcome is not None:
        has_executed = True
        attempted_amount = round(
            float(getattr(recovery_outcome, "attempted_amount", 0.0)), 2
        )
        recovered_amount = round(
            float(getattr(recovery_outcome, "recovered_amount", 0.0)), 2
        )
        execution_cost = round(
            float(getattr(recovery_outcome, "execution_cost", 0.0)), 2
        )
        net_recovered_value = round(
            float(getattr(recovery_outcome, "net_recovered_value", 0.0)), 2
        )
        recovery_rate = round(
            float(getattr(recovery_outcome, "recovery_rate", 0.0)), 4
        )
    elif batch_result is not None:
        has_executed = True
        attempted_amount = round(
            float(batch_result.get("attempted_amount", 0.0)), 2
        )
        recovered_amount = round(
            float(batch_result.get("recovered_amount", 0.0)), 2
        )
        execution_cost = round(
            float(batch_result.get("execution_cost", 0.0)), 2
        )
        net_recovered_value = round(
            float(batch_result.get("net_recovered_value", 0.0)), 2
        )
        recovery_rate = round(
            float(batch_result.get("recovery_rate", 0.0)), 4
        )
        if eligible_amount == 0.0 and "eligible_amount" in batch_result:
            eligible_amount = round(
                float(batch_result["eligible_amount"] or 0.0), 2
            )

    # ---------------------------------------------------------
    # Semantically safe ROI calculation
    # ---------------------------------------------------------
    if not has_executed or execution_cost <= 0:
        recovery_roi = None
        roi_display = "ROI: N/A — no execution cost recorded"
    else:
        recovery_roi = round(net_recovered_value / execution_cost, 2)
        roi_display = f"{recovery_roi:.1f}x"

    return FinancialSummary(
        revenue_at_risk=revenue_at_risk,
        eligible_amount=eligible_amount,
        attempted_amount=attempted_amount,
        recovered_amount=recovered_amount,
        execution_cost=execution_cost,
        net_recovered_value=net_recovered_value,
        recovery_rate=recovery_rate,
        recovery_roi=recovery_roi,
        roi_display=roi_display,
        has_executed=has_executed,
    )
