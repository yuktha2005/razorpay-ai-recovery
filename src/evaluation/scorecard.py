import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from src.tracking.financial_summary import (
    FinancialSummary,
    calculate_financial_summary,
)


def _sanitize_float(val: Any, default: float = 0.0) -> float:
    """Safely convert value to float, replacing NaN, Inf, or invalid types with default."""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


def _sanitize_int(val: Any, default: int = 0) -> int:
    """Safely convert value to int, replacing invalid types with default."""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return int(f)
    except (ValueError, TypeError):
        return default


def _sanitize_str(val: Any, default: str = "") -> str:
    """Safely convert value to str."""
    if val is None:
        return default
    return str(val)


METRIC_PROVENANCE: Dict[str, str] = {
    # 1. INCIDENT (OBSERVED)
    "degradation_percentage_points": "OBSERVED",
    "severity": "OBSERVED",
    "transactions_observed": "OBSERVED",
    "incident_detected": "OBSERVED",

    # 2. FINANCIAL (THEORETICAL / COUNTERFACTUAL vs SIMULATED)
    "revenue_at_risk": "THEORETICAL / COUNTERFACTUAL",
    "eligible_amount": "THEORETICAL / COUNTERFACTUAL",
    "attempted_amount": "SIMULATED",
    "recovered_amount": "SIMULATED",
    "execution_cost": "SIMULATED",
    "net_recovered_value": "SIMULATED",
    "recovery_rate": "SIMULATED",
    "recovery_roi": "SIMULATED",

    # 3. DECISION (THEORETICAL / COUNTERFACTUAL & GOVERNED / EVALUATED)
    "expected_loss_before": "THEORETICAL / COUNTERFACTUAL",
    "expected_loss_after": "THEORETICAL / COUNTERFACTUAL",
    "expected_loss_reduction": "THEORETICAL / COUNTERFACTUAL",
    "expected_loss_reduction_percentage": "THEORETICAL / COUNTERFACTUAL",
    "decision_confidence": "GOVERNED / EVALUATED",
    "selected_action": "GOVERNED / EVALUATED",

    # 4. RECOVERY (SIMULATED)
    "attempted_transactions": "SIMULATED",
    "successful_recoveries": "SIMULATED",
    "failed_recoveries": "SIMULATED",
    "canary_decision": "SIMULATED",
    "guardrail_decision": "SIMULATED",
    "rollback_required": "SIMULATED",
    "final_status": "SIMULATED",

    # 5. SAFETY (GOVERNED / EVALUATED)
    "safety_allowed": "GOVERNED / EVALUATED",
    "human_review_required": "GOVERNED / EVALUATED",
    "safety_reason": "GOVERNED / EVALUATED",

    # 6. LEARNING (LEARNED)
    "learned_attempts": "LEARNED",
    "learned_recoveries": "LEARNED",
    "learned_recovery_rate": "LEARNED",
    "learning_evidence_confidence": "LEARNED",
    "route_score_before_learning": "LEARNED",
    "route_score_after_learning": "LEARNED",
    "learning_score_delta": "LEARNED",
    "decision_changed_after_learning": "LEARNED",
}


@dataclass
class SystemEvaluationScorecard:
    """
    Authoritative evaluation scorecard for the Razorpay AI Revenue Recovery system.

    Aggregates incident intelligence, financial economics, decision quality,
    bounded recovery outcomes, safety controls, and closed-loop learning.

    Preserves explicit semantic provenance across:
    - OBSERVED: Ground-truth incident telemetry.
    - THEORETICAL / COUNTERFACTUAL: Pre-execution risk and optimization projections.
    - SIMULATED: Bounded canary and circuit-breaker execution outcomes.
    - GOVERNED / EVALUATED: Deterministic safety policy decisions and constraints.
    - LEARNED: Outcome-driven Bayesian evidence and routing lift.
    """

    # 1. INCIDENT
    degradation_percentage_points: float
    severity: str
    transactions_observed: int
    incident_detected: bool

    # 2. FINANCIAL
    revenue_at_risk: float
    eligible_amount: float
    attempted_amount: float
    recovered_amount: float
    execution_cost: float
    net_recovered_value: float
    recovery_rate: float
    recovery_roi: Optional[float]

    # 3. DECISION
    expected_loss_before: float
    expected_loss_after: float
    expected_loss_reduction: float
    expected_loss_reduction_percentage: float
    decision_confidence: float
    selected_action: str

    # 4. RECOVERY
    attempted_transactions: int
    successful_recoveries: int
    failed_recoveries: int
    canary_decision: str
    guardrail_decision: str
    rollback_required: bool
    final_status: str

    # 5. SAFETY
    safety_allowed: bool
    human_review_required: bool
    safety_reason: str

    # 6. LEARNING
    learned_attempts: int
    learned_recoveries: int
    learned_recovery_rate: float
    learning_evidence_confidence: float
    route_score_before_learning: float
    route_score_after_learning: float
    learning_score_delta: float
    decision_changed_after_learning: bool

    @property
    def provenance(self) -> Dict[str, str]:
        """Mapping of metric field name to its semantic provenance category."""
        return dict(METRIC_PROVENANCE)

    def get_provenance(self, metric_name: str) -> str:
        """Return the semantic provenance label for a given scorecard metric."""
        return METRIC_PROVENANCE.get(metric_name, "UNKNOWN")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize scorecard fields to a plain dictionary."""
        return asdict(self)


def build_scorecard(
    incident: Optional[Any] = None,
    financial_summary: Optional[FinancialSummary] = None,
    decision: Optional[Any] = None,
    safety_decision: Optional[Any] = None,
    batch_result: Optional[Dict[str, Any]] = None,
    recovery_outcome: Optional[Any] = None,
    learning_stats: Optional[Any] = None,
    route_score_before: Optional[Any] = None,
    route_score_after: Optional[Any] = None,
    action_before: Optional[str] = None,
    action_after: Optional[str] = None,
    *,
    degradation_percentage_points: Optional[float] = None,
    severity: Optional[str] = None,
    transactions_observed: Optional[int] = None,
    incident_detected: Optional[bool] = None,
    revenue_at_risk: Optional[float] = None,
    eligible_amount: Optional[float] = None,
    attempted_amount: Optional[float] = None,
    recovered_amount: Optional[float] = None,
    execution_cost: Optional[float] = None,
    net_recovered_value: Optional[float] = None,
    recovery_rate: Optional[float] = None,
    recovery_roi: Optional[float] = None,
    expected_loss_before: Optional[float] = None,
    expected_loss_after: Optional[float] = None,
    expected_loss_reduction: Optional[float] = None,
    expected_loss_reduction_percentage: Optional[float] = None,
    decision_confidence: Optional[float] = None,
    selected_action: Optional[str] = None,
    attempted_transactions: Optional[int] = None,
    successful_recoveries: Optional[int] = None,
    failed_recoveries: Optional[int] = None,
    canary_decision: Optional[str] = None,
    guardrail_decision: Optional[str] = None,
    rollback_required: Optional[bool] = None,
    final_status: Optional[str] = None,
    safety_allowed: Optional[bool] = None,
    human_review_required: Optional[bool] = None,
    safety_reason: Optional[str] = None,
    learned_attempts: Optional[int] = None,
    learned_recoveries: Optional[int] = None,
    learned_recovery_rate: Optional[float] = None,
    learning_evidence_confidence: Optional[float] = None,
    route_score_before_learning: Optional[float] = None,
    route_score_after_learning: Optional[float] = None,
    learning_score_delta: Optional[float] = None,
    decision_changed_after_learning: Optional[bool] = None,
) -> SystemEvaluationScorecard:
    """
    Construct an authoritative SystemEvaluationScorecard from domain objects or parameters.

    Reuses existing authoritative calculators (e.g. calculate_financial_summary)
    without duplicating financial math or creating mock benchmarks.
    """

    # ---------------------------------------------------------
    # 1. INCIDENT METRICS
    # ---------------------------------------------------------
    if degradation_percentage_points is None:
        if incident is not None:
            if hasattr(incident, "degradation_percentage_points"):
                degradation_percentage_points = getattr(
                    incident, "degradation_percentage_points"
                )
            elif hasattr(incident, "degradation_pp"):
                degradation_percentage_points = getattr(
                    incident, "degradation_pp"
                )
            elif isinstance(incident, dict):
                degradation_percentage_points = incident.get(
                    "degradation_percentage_points",
                    incident.get("degradation_pp", 0.0),
                )
    degradation_percentage_points = round(
        _sanitize_float(degradation_percentage_points, 0.0), 2
    )

    if severity is None:
        if incident is not None:
            if hasattr(incident, "severity"):
                severity = getattr(incident, "severity")
            elif isinstance(incident, dict):
                severity = incident.get("severity", "HEALTHY")
    severity = _sanitize_str(severity, "HEALTHY")

    if transactions_observed is None:
        if incident is not None:
            if hasattr(incident, "transactions_observed"):
                transactions_observed = getattr(
                    incident, "transactions_observed"
                )
            elif hasattr(incident, "transactions_affected"):
                transactions_observed = getattr(
                    incident, "transactions_affected"
                )
            elif isinstance(incident, dict):
                transactions_observed = incident.get(
                    "transactions_observed", incident.get("transactions", 0)
                )
    transactions_observed = max(0, _sanitize_int(transactions_observed, 0))

    if incident_detected is None:
        if incident is not None:
            if hasattr(incident, "incident_detected"):
                incident_detected = bool(
                    getattr(incident, "incident_detected")
                )
            elif isinstance(incident, dict):
                incident_detected = bool(
                    incident.get(
                        "incident_detected",
                        severity in ("WATCH", "DEGRADED", "CRITICAL"),
                    )
                )
            else:
                incident_detected = severity in (
                    "WATCH",
                    "DEGRADED",
                    "CRITICAL",
                )
        else:
            incident_detected = severity in ("WATCH", "DEGRADED", "CRITICAL")
    incident_detected = bool(incident_detected)

    # ---------------------------------------------------------
    # 2. FINANCIAL METRICS
    # Reuses existing authoritative calculate_financial_summary
    # ---------------------------------------------------------
    calc_rev_at_risk = 0.0
    if revenue_at_risk is not None:
        calc_rev_at_risk = _sanitize_float(revenue_at_risk, 0.0)
    elif incident is not None:
        if hasattr(incident, "revenue_at_risk"):
            calc_rev_at_risk = _sanitize_float(
                getattr(incident, "revenue_at_risk"), 0.0
            )
        elif isinstance(incident, dict):
            calc_rev_at_risk = _sanitize_float(
                incident.get("revenue_at_risk", 0.0), 0.0
            )

    calc_eligible = 0.0
    if eligible_amount is not None:
        calc_eligible = _sanitize_float(eligible_amount, 0.0)
    elif batch_result and "eligible_amount" in batch_result:
        calc_eligible = _sanitize_float(batch_result["eligible_amount"], 0.0)

    if financial_summary is None:
        fin_summary = calculate_financial_summary(
            revenue_at_risk=calc_rev_at_risk,
            eligible_amount=calc_eligible,
            batch_result=batch_result,
            recovery_outcome=recovery_outcome,
        )
    else:
        fin_summary = financial_summary

    raw_rev_at_risk = (
        revenue_at_risk if revenue_at_risk is not None else fin_summary.revenue_at_risk
    )
    final_rev_at_risk = _sanitize_float(raw_rev_at_risk, 0.0)

    raw_eligible = (
        eligible_amount if eligible_amount is not None else fin_summary.eligible_amount
    )
    final_eligible = _sanitize_float(raw_eligible, 0.0)

    raw_attempted = (
        attempted_amount if attempted_amount is not None else fin_summary.attempted_amount
    )
    final_attempted = _sanitize_float(raw_attempted, 0.0)

    raw_recovered = (
        recovered_amount if recovered_amount is not None else fin_summary.recovered_amount
    )
    final_recovered = _sanitize_float(raw_recovered, 0.0)

    raw_cost = (
        execution_cost if execution_cost is not None else fin_summary.execution_cost
    )
    final_cost = _sanitize_float(raw_cost, 0.0)

    raw_net = (
        net_recovered_value if net_recovered_value is not None else fin_summary.net_recovered_value
    )
    final_net = _sanitize_float(raw_net, 0.0)

    raw_rec_rate = (
        recovery_rate if recovery_rate is not None else fin_summary.recovery_rate
    )
    final_rec_rate = _sanitize_float(raw_rec_rate, 0.0)

    raw_roi = (
        recovery_roi if recovery_roi is not None else fin_summary.recovery_roi
    )
    if raw_roi is not None:
        try:
            f_roi = float(raw_roi)
            if math.isnan(f_roi) or math.isinf(f_roi):
                final_roi = None
            else:
                final_roi = round(f_roi, 2)
        except (ValueError, TypeError):
            final_roi = None
    else:
        final_roi = None

    # ---------------------------------------------------------
    # 3. DECISION METRICS
    # ---------------------------------------------------------
    if expected_loss_before is None:
        if decision is not None:
            if hasattr(decision, "expected_loss_before"):
                expected_loss_before = getattr(decision, "expected_loss_before")
            elif hasattr(decision, "expected_loss"):
                expected_loss_before = getattr(decision, "expected_loss")
            elif (
                hasattr(decision, "decision")
                and hasattr(decision.decision, "expected_loss_before")
            ):
                expected_loss_before = getattr(
                    decision.decision, "expected_loss_before"
                )
            elif isinstance(decision, dict):
                expected_loss_before = decision.get(
                    "expected_loss_before", decision.get("expected_loss", 0.0)
                )
    expected_loss_before = max(
        0.0, round(_sanitize_float(expected_loss_before, 0.0), 2)
    )

    if expected_loss_after is None:
        if decision is not None:
            if hasattr(decision, "expected_loss_after"):
                expected_loss_after = getattr(decision, "expected_loss_after")
            elif (
                hasattr(decision, "decision")
                and hasattr(decision.decision, "expected_loss_after")
            ):
                expected_loss_after = getattr(
                    decision.decision, "expected_loss_after"
                )
            elif isinstance(decision, dict):
                expected_loss_after = decision.get("expected_loss_after", 0.0)
    expected_loss_after = max(
        0.0, round(_sanitize_float(expected_loss_after, 0.0), 2)
    )

    # Authoritative Expected Loss Reduction
    if expected_loss_reduction is None:
        expected_loss_reduction = round(
            max(0.0, expected_loss_before - expected_loss_after), 2
        )
    else:
        expected_loss_reduction = max(
            0.0, round(_sanitize_float(expected_loss_reduction, 0.0), 2)
        )

    # Authoritative Expected Loss Reduction Percentage
    if expected_loss_reduction_percentage is None:
        if expected_loss_before > 0:
            expected_loss_reduction_percentage = round(
                (expected_loss_reduction / expected_loss_before) * 100.0, 2
            )
        else:
            expected_loss_reduction_percentage = 0.0
    else:
        expected_loss_reduction_percentage = max(
            0.0,
            round(
                _sanitize_float(expected_loss_reduction_percentage, 0.0), 2
            ),
        )

    if decision_confidence is None:
        if decision is not None:
            if hasattr(decision, "confidence"):
                decision_confidence = getattr(decision, "confidence")
            elif (
                hasattr(decision, "decision")
                and hasattr(decision.decision, "confidence")
            ):
                decision_confidence = getattr(decision.decision, "confidence")
            elif isinstance(decision, dict):
                decision_confidence = decision.get("confidence", 0.0)
    decision_confidence = max(
        0.0, min(1.0, round(_sanitize_float(decision_confidence, 0.0), 4))
    )

    if selected_action is None:
        if decision is not None:
            if hasattr(decision, "recommended_action"):
                selected_action = getattr(decision, "recommended_action")
            elif (
                hasattr(decision, "decision")
                and hasattr(decision.decision, "recommended_action")
            ):
                selected_action = getattr(
                    decision.decision, "recommended_action"
                )
            elif isinstance(decision, dict):
                selected_action = decision.get(
                    "recommended_action", decision.get("action", "MONITOR")
                )
    selected_action = _sanitize_str(selected_action, "MONITOR")

    # ---------------------------------------------------------
    # 4. RECOVERY METRICS
    # ---------------------------------------------------------
    if attempted_transactions is None:
        if batch_result is not None:
            attempted_transactions = batch_result.get(
                "attempted_transactions", 0
            )
        elif recovery_outcome is not None:
            attempted_transactions = getattr(
                recovery_outcome, "attempted_transactions", 0
            )
    attempted_transactions = max(
        0, _sanitize_int(attempted_transactions, 0)
    )

    if successful_recoveries is None:
        if batch_result is not None:
            successful_recoveries = batch_result.get(
                "successful_recoveries",
                batch_result.get("recovered_transactions", 0),
            )
        elif recovery_outcome is not None:
            successful_recoveries = getattr(
                recovery_outcome, "successful_recoveries", 0
            )
    successful_recoveries = max(
        0, _sanitize_int(successful_recoveries, 0)
    )

    if failed_recoveries is None:
        if batch_result is not None:
            failed_recoveries = batch_result.get(
                "failed_recoveries",
                max(0, attempted_transactions - successful_recoveries),
            )
        elif recovery_outcome is not None:
            failed_recoveries = getattr(
                recovery_outcome, "failed_recoveries", 0
            )
        else:
            failed_recoveries = max(
                0, attempted_transactions - successful_recoveries
            )
    failed_recoveries = max(0, _sanitize_int(failed_recoveries, 0))

    if canary_decision is None:
        if batch_result is not None:
            canary_decision = batch_result.get(
                "canary_decision", "NOT_APPLICABLE"
            )
        elif recovery_outcome is not None:
            canary_decision = getattr(
                recovery_outcome, "canary_decision", "NOT_APPLICABLE"
            )
    canary_decision = _sanitize_str(canary_decision, "NOT_APPLICABLE")

    if guardrail_decision is None:
        if batch_result is not None:
            guardrail_decision = batch_result.get(
                "guardrail_decision", "NOT_APPLICABLE"
            )
        elif recovery_outcome is not None:
            guardrail_decision = getattr(
                recovery_outcome, "guardrail_decision", "NOT_APPLICABLE"
            )
    guardrail_decision = _sanitize_str(guardrail_decision, "NOT_APPLICABLE")

    if rollback_required is None:
        if batch_result is not None:
            rollback_required = bool(batch_result.get("rollback_required", False))
        elif recovery_outcome is not None:
            rollback_required = bool(
                getattr(recovery_outcome, "rollback_required", False)
            )
    rollback_required = bool(rollback_required)

    if final_status is None:
        if batch_result is not None:
            final_status = batch_result.get(
                "final_status",
                batch_result.get("outcome_status", "NO_EXECUTION"),
            )
        elif recovery_outcome is not None:
            final_status = getattr(
                recovery_outcome, "outcome_status", "NO_EXECUTION"
            )
    final_status = _sanitize_str(final_status, "NO_EXECUTION")

    # ---------------------------------------------------------
    # 5. SAFETY METRICS
    # ---------------------------------------------------------
    if safety_allowed is None:
        if safety_decision is not None:
            if hasattr(safety_decision, "allowed"):
                safety_allowed = getattr(safety_decision, "allowed")
            elif isinstance(safety_decision, dict):
                safety_allowed = safety_decision.get("allowed", True)
    if safety_allowed is None:
        safety_allowed = True
    safety_allowed = bool(safety_allowed)

    if human_review_required is None:
        if safety_decision is not None:
            if hasattr(safety_decision, "requires_human_review"):
                human_review_required = getattr(
                    safety_decision, "requires_human_review"
                )
            elif isinstance(safety_decision, dict):
                human_review_required = safety_decision.get(
                    "requires_human_review", False
                )
    if human_review_required is None:
        human_review_required = False
    human_review_required = bool(human_review_required)

    if safety_reason is None:
        if safety_decision is not None:
            if hasattr(safety_decision, "reason"):
                safety_reason = getattr(safety_decision, "reason")
            elif isinstance(safety_decision, dict):
                safety_reason = safety_decision.get(
                    "reason", "No safety constraints evaluated"
                )
    safety_reason = _sanitize_str(
        safety_reason, "No safety constraints evaluated"
    )

    # ---------------------------------------------------------
    # 6. LEARNING METRICS
    # ---------------------------------------------------------
    if learned_attempts is None:
        if learning_stats is not None:
            if hasattr(learning_stats, "attempts"):
                learned_attempts = getattr(learning_stats, "attempts")
            elif isinstance(learning_stats, dict):
                learned_attempts = learning_stats.get("attempts", 0)
    learned_attempts = max(0, _sanitize_int(learned_attempts, 0))

    if learned_recoveries is None:
        if learning_stats is not None:
            if hasattr(learning_stats, "recoveries"):
                learned_recoveries = getattr(learning_stats, "recoveries")
            elif isinstance(learning_stats, dict):
                learned_recoveries = learning_stats.get("recoveries", 0)
    learned_recoveries = max(0, _sanitize_int(learned_recoveries, 0))

    if learned_recovery_rate is None:
        if learning_stats is not None:
            if hasattr(learning_stats, "recovery_rate"):
                learned_recovery_rate = getattr(
                    learning_stats, "recovery_rate"
                )
            elif isinstance(learning_stats, dict):
                learned_recovery_rate = learning_stats.get(
                    "recovery_rate", 0.0
                )
    learned_recovery_rate = max(
        0.0, min(1.0, round(_sanitize_float(learned_recovery_rate, 0.0), 4))
    )

    if learning_evidence_confidence is None:
        if learning_stats is not None:
            if hasattr(learning_stats, "evidence_confidence"):
                learning_evidence_confidence = getattr(
                    learning_stats, "evidence_confidence"
                )
            elif isinstance(learning_stats, dict):
                learning_evidence_confidence = learning_stats.get(
                    "evidence_confidence", 0.0
                )
    learning_evidence_confidence = max(
        0.0,
        min(1.0, round(_sanitize_float(learning_evidence_confidence, 0.0), 4)),
    )

    # Route score before learning
    if route_score_before_learning is None:
        if route_score_before is not None:
            if hasattr(route_score_before, "score"):
                route_score_before_learning = getattr(
                    route_score_before, "score"
                )
            else:
                route_score_before_learning = route_score_before
    route_score_before_learning = round(
        _sanitize_float(route_score_before_learning, 0.0), 4
    )

    # Route score after learning
    if route_score_after_learning is None:
        if route_score_after is not None:
            if hasattr(route_score_after, "score"):
                route_score_after_learning = getattr(
                    route_score_after, "score"
                )
            else:
                route_score_after_learning = route_score_after
    route_score_after_learning = round(
        _sanitize_float(route_score_after_learning, 0.0), 4
    )

    # Learning score delta
    if learning_score_delta is None:
        learning_score_delta = round(
            route_score_after_learning - route_score_before_learning, 4
        )
    else:
        learning_score_delta = round(
            _sanitize_float(learning_score_delta, 0.0), 4
        )

    # Decision changed after learning
    if decision_changed_after_learning is None:
        act_before = None
        if action_before is not None:
            act_before = getattr(
                action_before, "recommended_action", str(action_before)
            )

        act_after = None
        if action_after is not None:
            act_after = getattr(
                action_after, "recommended_action", str(action_after)
            )

        if act_before is not None and act_after is not None:
            decision_changed_after_learning = bool(
                str(act_before).strip() != str(act_after).strip()
            )
        else:
            decision_changed_after_learning = False
    else:
        decision_changed_after_learning = bool(decision_changed_after_learning)

    return SystemEvaluationScorecard(
        degradation_percentage_points=degradation_percentage_points,
        severity=severity,
        transactions_observed=transactions_observed,
        incident_detected=incident_detected,
        revenue_at_risk=final_rev_at_risk,
        eligible_amount=final_eligible,
        attempted_amount=final_attempted,
        recovered_amount=final_recovered,
        execution_cost=final_cost,
        net_recovered_value=final_net,
        recovery_rate=final_rec_rate,
        recovery_roi=final_roi,
        expected_loss_before=expected_loss_before,
        expected_loss_after=expected_loss_after,
        expected_loss_reduction=expected_loss_reduction,
        expected_loss_reduction_percentage=expected_loss_reduction_percentage,
        decision_confidence=decision_confidence,
        selected_action=selected_action,
        attempted_transactions=attempted_transactions,
        successful_recoveries=successful_recoveries,
        failed_recoveries=failed_recoveries,
        canary_decision=canary_decision,
        guardrail_decision=guardrail_decision,
        rollback_required=rollback_required,
        final_status=final_status,
        safety_allowed=safety_allowed,
        human_review_required=human_review_required,
        safety_reason=safety_reason,
        learned_attempts=learned_attempts,
        learned_recoveries=learned_recoveries,
        learned_recovery_rate=learned_recovery_rate,
        learning_evidence_confidence=learning_evidence_confidence,
        route_score_before_learning=route_score_before_learning,
        route_score_after_learning=route_score_after_learning,
        learning_score_delta=learning_score_delta,
        decision_changed_after_learning=decision_changed_after_learning,
    )
