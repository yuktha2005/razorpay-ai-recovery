"""
Evaluation adapter for the Razorpay AI Revenue Recovery pipeline.

Transforms outputs across incident intelligence, revenue quantification,
AI decision-making, deterministic safety gating, bounded recovery,
and closed-loop learning into an authoritative SystemEvaluationScorecard.

This adapter is strictly read-only and produces NO side effects.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.evaluation.scorecard import (
    SystemEvaluationScorecard,
    build_scorecard,
)
from src.intelligence.route_scoring import rank_routes
from src.models.domain import Decision, SafetyDecision
from src.recovery.recovery_orchestrator import RecoveryOrchestrationResult
from src.tracking.financial_summary import (
    FinancialSummary,
    calculate_financial_summary,
)
from src.tracking.recovery_learning import RouteLearningStats


def build_system_evaluation_scorecard(
    incident: Any,
    decision: Optional[Any] = None,
    safety_decision: Optional[Any] = None,
    orchestration_result: Optional[Any] = None,
    learning_context: Optional[Any] = None,
    route_score_before: Optional[Any] = None,
    route_score_after: Optional[Any] = None,
    action_before: Optional[str] = None,
    action_after: Optional[str] = None,
    revenue_impact: Optional[Any] = None,
    eligible_amount: Optional[float] = None,
) -> SystemEvaluationScorecard:
    """
    Construct a complete SystemEvaluationScorecard from pipeline stage outputs.

    Parameters
    ----------
    incident : Any
        IncidentAssessment, IncidentDecisionResult, SyntheticIncident, or dict.
    decision : Optional[Any]
        Decision domain object, IncidentDecisionResult, dict, or action string.
    safety_decision : Optional[Any]
        SafetyDecision domain object or dict.
    orchestration_result : Optional[Any]
        RecoveryOrchestrationResult, batch_result dict, RecoveryOutcome, or None.
    learning_context : Optional[Any]
        RouteLearningStats, dict, RecoveryLearningEngine, or None.
    route_score_before : Optional[Any]
        RouteScore or float prior to learning.
    route_score_after : Optional[Any]
        RouteScore or float after learning.
    action_before : Optional[str]
        Recommended route/action before learning update.
    action_after : Optional[str]
        Recommended route/action after learning update.
    revenue_impact : Optional[Any]
        IncidentRevenueImpact object or float revenue-at-risk.
    eligible_amount : Optional[float]
        Monetary amount of failed transactions eligible for recovery batch.

    Returns
    -------
    SystemEvaluationScorecard
        Authoritative, deterministic scorecard preserving explicit metric provenance.
    """

    # ---------------------------------------------------------
    # 1. Incident Resolution
    # ---------------------------------------------------------
    incident_assessment = incident
    extracted_decision = decision
    extracted_safety = safety_decision
    calc_revenue_at_risk = 0.0

    # IncidentDecisionResult encapsulates incident + decision + safety + revenue
    if hasattr(incident, "decision") and hasattr(incident, "safety_decision"):
        if extracted_decision is None:
            extracted_decision = incident.decision
        if extracted_safety is None:
            extracted_safety = incident.safety_decision
        if hasattr(incident, "revenue_at_risk"):
            calc_revenue_at_risk = float(incident.revenue_at_risk)
        incident_assessment = incident
    elif hasattr(incident, "assessment"):  # SyntheticIncident
        incident_assessment = incident.assessment
        if hasattr(incident, "revenue_at_risk"):
            calc_revenue_at_risk = float(incident.revenue_at_risk)

    # Explicit revenue_impact takes precedence if passed
    if revenue_impact is not None:
        if hasattr(revenue_impact, "revenue_at_risk"):
            calc_revenue_at_risk = float(revenue_impact.revenue_at_risk)
        else:
            try:
                calc_revenue_at_risk = float(revenue_impact)
            except (ValueError, TypeError):
                calc_revenue_at_risk = 0.0
    elif calc_revenue_at_risk == 0.0:
        if hasattr(incident_assessment, "revenue_at_risk"):
            calc_revenue_at_risk = float(incident_assessment.revenue_at_risk)
        elif isinstance(incident_assessment, dict) and "revenue_at_risk" in incident_assessment:
            calc_revenue_at_risk = float(incident_assessment.get("revenue_at_risk", 0.0))

    # ---------------------------------------------------------
    # 2. Decision Resolution
    # ---------------------------------------------------------
    if extracted_decision is None:
        extracted_decision = Decision(
            payment_id="",
            recommended_action="MONITOR",
            confidence=0.0,
            expected_loss_before=0.0,
            expected_loss_after=0.0,
            estimated_value=0.0,
            explanation="No decision evaluated",
        )
    elif isinstance(extracted_decision, str):
        extracted_decision = Decision(
            payment_id="",
            recommended_action=extracted_decision,
            confidence=0.0,
            expected_loss_before=0.0,
            expected_loss_after=0.0,
            estimated_value=0.0,
            explanation="Action string provided",
        )

    # ---------------------------------------------------------
    # 3. Safety Resolution
    # ---------------------------------------------------------
    if extracted_safety is None:
        if hasattr(orchestration_result, "safety_allowed"):
            extracted_safety = SafetyDecision(
                payment_id="",
                action=getattr(orchestration_result, "safety_action", "MONITOR"),
                allowed=getattr(orchestration_result, "safety_allowed", True),
                reason=getattr(orchestration_result, "explanation", "No safety constraints evaluated"),
                requires_human_review=False,
            )
        elif isinstance(orchestration_result, dict) and "safety_allowed" in orchestration_result:
            extracted_safety = SafetyDecision(
                payment_id="",
                action=orchestration_result.get("safety_action", "MONITOR"),
                allowed=bool(orchestration_result.get("safety_allowed", True)),
                reason=orchestration_result.get(
                    "safety_reason",
                    orchestration_result.get("explanation", "No safety constraints evaluated"),
                ),
                requires_human_review=bool(
                    orchestration_result.get("original_safety_requires_human_review", False)
                ),
            )
        else:
            extracted_safety = SafetyDecision(
                payment_id="",
                action=getattr(extracted_decision, "recommended_action", "MONITOR"),
                allowed=True,
                reason="No safety constraints evaluated",
                requires_human_review=False,
            )

    # ---------------------------------------------------------
    # 4. Orchestration & Recovery Resolution
    # ---------------------------------------------------------
    batch_dict: Optional[Dict[str, Any]] = None
    extracted_learning_stats: Optional[Any] = None
    calc_eligible = eligible_amount if eligible_amount is not None else 0.0

    if orchestration_result is not None:
        if isinstance(orchestration_result, RecoveryOrchestrationResult):
            exec_res = orchestration_result.execution_result
            outcome = orchestration_result.recovery_outcome

            # Determine rollback requirement and guardrail decision
            is_unprofitable = (
                orchestration_result.final_status == "UNPROFITABLE"
                or getattr(outcome, "outcome_status", "") == "UNPROFITABLE"
            )
            rollback_required = is_unprofitable

            if orchestration_result.final_status in ("RECOVERED", "COMPLETED"):
                guardrail_dec = "CONTINUE"
            elif is_unprofitable:
                guardrail_dec = "ROLLBACK"
            elif orchestration_result.final_status == "BLOCKED":
                guardrail_dec = "STOP"
            else:
                guardrail_dec = "NOT_APPLICABLE"

            if calc_eligible == 0.0 and outcome is not None:
                calc_eligible = float(getattr(outcome, "attempted_amount", 0.0))

            batch_dict = {
                "eligible_transactions": (
                    exec_res.attempted_transactions if exec_res else 0
                ),
                "attempted_transactions": (
                    exec_res.attempted_transactions if exec_res else 0
                ),
                "successful_recoveries": (
                    exec_res.successful_recoveries if exec_res else 0
                ),
                "failed_recoveries": (
                    exec_res.failed_recoveries if exec_res else 0
                ),
                "attempted_amount": float(
                    getattr(outcome, "attempted_amount", 0.0)
                ),
                "recovered_amount": float(
                    getattr(outcome, "recovered_amount", 0.0)
                ),
                "execution_cost": float(
                    getattr(outcome, "execution_cost", 0.0)
                ),
                "net_recovered_value": float(
                    getattr(outcome, "net_recovered_value", 0.0)
                ),
                "recovery_rate": float(
                    getattr(outcome, "recovery_rate", 0.0)
                ),
                "canary_decision": orchestration_result.canary_decision,
                "guardrail_decision": guardrail_dec,
                "rollback_required": rollback_required,
                "final_status": orchestration_result.final_status,
                "eligible_amount": calc_eligible,
            }

            if learning_context is None and orchestration_result.learning_stats is not None:
                extracted_learning_stats = orchestration_result.learning_stats

        elif isinstance(orchestration_result, dict):
            batch_dict = dict(orchestration_result)
            if calc_eligible == 0.0 and "eligible_amount" in batch_dict:
                calc_eligible = float(batch_dict["eligible_amount"])
            batch_dict["eligible_amount"] = calc_eligible

            if learning_context is None and "learning_stats" in batch_dict:
                extracted_learning_stats = batch_dict.get("learning_stats")

        elif hasattr(orchestration_result, "attempted_transactions"):  # RecoveryOutcome directly
            outcome = orchestration_result
            is_unprofitable = getattr(outcome, "outcome_status", "") == "UNPROFITABLE"
            batch_dict = {
                "attempted_transactions": getattr(outcome, "attempted_transactions", 0),
                "successful_recoveries": getattr(outcome, "successful_recoveries", 0),
                "failed_recoveries": getattr(outcome, "failed_recoveries", 0),
                "attempted_amount": float(getattr(outcome, "attempted_amount", 0.0)),
                "recovered_amount": float(getattr(outcome, "recovered_amount", 0.0)),
                "execution_cost": float(getattr(outcome, "execution_cost", 0.0)),
                "net_recovered_value": float(getattr(outcome, "net_recovered_value", 0.0)),
                "recovery_rate": float(getattr(outcome, "recovery_rate", 0.0)),
                "canary_decision": getattr(outcome, "canary_decision", "NOT_APPLICABLE"),
                "guardrail_decision": "ROLLBACK" if is_unprofitable else "NOT_APPLICABLE",
                "rollback_required": is_unprofitable,
                "final_status": getattr(outcome, "outcome_status", "NO_EXECUTION"),
                "eligible_amount": calc_eligible,
            }

    # ---------------------------------------------------------
    # 5. Learning Resolution
    # ---------------------------------------------------------
    calc_action_before = action_before
    calc_action_after = action_after

    if learning_context is not None:
        if isinstance(learning_context, RouteLearningStats):
            extracted_learning_stats = learning_context
        elif isinstance(learning_context, dict):
            extracted_learning_stats = learning_context.get(
                "learning_stats", extracted_learning_stats
            )
            if route_score_before is None:
                route_score_before = learning_context.get("route_score_before")
            if route_score_after is None:
                route_score_after = learning_context.get("route_score_after")
            if calc_action_before is None:
                calc_action_before = learning_context.get("action_before")
            if calc_action_after is None:
                calc_action_after = learning_context.get("action_after")
        elif hasattr(learning_context, "get_route"):  # RecoveryLearningEngine
            rec_action = getattr(extracted_decision, "recommended_action", "")
            route_name = rec_action.replace("ROUTE_SWITCH:", "").strip()
            extracted_learning_stats = learning_context.get_route(route_name)

    # ---------------------------------------------------------
    # 6. Delegate to Authoritative Scorecard Builder
    # ---------------------------------------------------------
    return build_scorecard(
        incident=incident_assessment,
        decision=extracted_decision,
        safety_decision=extracted_safety,
        batch_result=batch_dict,
        learning_stats=extracted_learning_stats,
        route_score_before=route_score_before,
        route_score_after=route_score_after,
        action_before=calc_action_before,
        action_after=calc_action_after,
        revenue_at_risk=calc_revenue_at_risk,
        eligible_amount=calc_eligible,
    )


class EvaluationAdapter:
    """
    Class-based interface for the evaluation adapter.
    """

    @staticmethod
    def adapt(
        incident: Any,
        decision: Optional[Any] = None,
        safety_decision: Optional[Any] = None,
        orchestration_result: Optional[Any] = None,
        learning_context: Optional[Any] = None,
        route_score_before: Optional[Any] = None,
        route_score_after: Optional[Any] = None,
        action_before: Optional[str] = None,
        action_after: Optional[str] = None,
        revenue_impact: Optional[Any] = None,
        eligible_amount: Optional[float] = None,
    ) -> SystemEvaluationScorecard:
        """Convenience method delegating to build_system_evaluation_scorecard."""
        return build_system_evaluation_scorecard(
            incident=incident,
            decision=decision,
            safety_decision=safety_decision,
            orchestration_result=orchestration_result,
            learning_context=learning_context,
            route_score_before=route_score_before,
            route_score_after=route_score_after,
            action_before=action_before,
            action_after=action_after,
            revenue_impact=revenue_impact,
            eligible_amount=eligible_amount,
        )

    @staticmethod
    def prepare_dashboard_view(
        incident: Any,
        decision: Optional[Any] = None,
        safety_decision: Optional[Any] = None,
        batch_result: Optional[Dict[str, Any]] = None,
        learning_history: Optional[Any] = None,
        revenue_impact: Optional[Any] = None,
        eligible_amount: Optional[float] = None,
        route_candidates: Optional[Any] = None,
    ) -> "DashboardEvaluationView":
        """Convenience method delegating to prepare_dashboard_evaluation_scorecard."""
        return prepare_dashboard_evaluation_scorecard(
            incident=incident,
            decision=decision,
            safety_decision=safety_decision,
            batch_result=batch_result,
            learning_history=learning_history,
            revenue_impact=revenue_impact,
            eligible_amount=eligible_amount,
            route_candidates=route_candidates,
        )


@dataclass
class DashboardEvaluationView:
    """
    Presentation-ready view model for the Streamlit dashboard evaluation section.

    Encapsulates the authoritative SystemEvaluationScorecard with pre-formatted display
    strings and explicit provenance tags, ensuring zero business/financial calculations in app.py.
    """

    scorecard: SystemEvaluationScorecard
    has_executed: bool
    is_blocked: bool
    has_learning_evidence: bool

    # Metric 1: Degradation
    degradation_value: str
    degradation_provenance: str
    degradation_sub: str

    # Metric 2: Revenue at Risk
    revenue_at_risk_value: str
    revenue_at_risk_provenance: str
    revenue_at_risk_sub: str

    # Metric 3: Expected Loss Reduction
    expected_loss_reduction_value: str
    expected_loss_reduction_provenance: str
    expected_loss_reduction_sub: str

    # Metric 4: Recovery Rate
    recovery_rate_value: str
    recovery_rate_provenance: str
    recovery_rate_sub: str

    # Metric 5: Net Recovered Value
    net_recovered_value: str
    net_recovered_provenance: str
    net_recovered_sub: str

    # Metric 6: Recovery ROI
    recovery_roi_value: str
    recovery_roi_provenance: str
    recovery_roi_sub: str

    # Metric 7: Safety Outcome
    safety_status_value: str
    safety_provenance: str
    safety_pill_class: str
    safety_reason: str

    # Metric 8: Learning Evidence Lift
    learning_lift_value: str
    learning_provenance: str
    learning_pill_class: str
    learning_sub: str

    # Compact Pipeline Status Summary
    selected_action: str
    canary_decision: str
    canary_pill_class: str
    guardrail_decision: str
    guardrail_pill_class: str
    final_status: str
    final_pill_class: str
    rollback_required: str
    rollback_pill_class: str


def prepare_dashboard_evaluation_scorecard(
    incident: Any,
    decision: Optional[Any] = None,
    safety_decision: Optional[Any] = None,
    batch_result: Optional[Dict[str, Any]] = None,
    learning_history: Optional[Any] = None,
    revenue_impact: Optional[Any] = None,
    eligible_amount: Optional[float] = None,
    route_candidates: Optional[Any] = None,
) -> DashboardEvaluationView:
    """
    Bridge runtime dashboard outputs to an authoritative SystemEvaluationScorecard and
    produce a sanitized, presentation-ready DashboardEvaluationView for app.py.

    Parameters
    ----------
    incident : Any
        Live incident assessment object or dictionary.
    decision : Optional[Any]
        AI Decision object, DecisionExplanation, or action string.
    safety_decision : Optional[Any]
        Deterministic SafetyDecision object or dictionary.
    batch_result : Optional[Dict[str, Any]]
        Executed batch recovery result dictionary from session state, or None if unexecuted.
    learning_history : Optional[Any]
        PersistentLearningHistory instance, dictionary of learned routes, or None.
    revenue_impact : Optional[Any]
        IncidentRevenueImpact object or float revenue-at-risk.
    eligible_amount : Optional[float]
        Monetary amount of eligible failure transactions.
    route_candidates : Optional[Any]
        Candidate route list for route scoring evaluation before and after learning.

    Returns
    -------
    DashboardEvaluationView
        Formatted and sanitized view model containing the authoritative scorecard
        and UI-ready labels with explicit semantic provenance.
    """
    # 1. Resolve Learning Evidence & Route Ranking Lift
    history_dict: Dict[str, Any] = {}
    if learning_history is not None:
        if hasattr(learning_history, "load"):
            try:
                loaded = learning_history.load() or []
                for r in loaded:
                    history_dict[r.route] = r
            except Exception:
                pass
        elif isinstance(learning_history, dict):
            history_dict = dict(learning_history)

    # Incorporate just-executed batch learning stats if present
    if batch_result and batch_result.get("learning_stats"):
        bs = batch_result["learning_stats"]
        if hasattr(bs, "route"):
            history_dict[bs.route] = bs

    route_score_before = None
    route_score_after = None
    action_before = None
    action_after = None
    learning_stats_for_route = None

    if route_candidates:
        try:
            ranked_unlearned = rank_routes(route_candidates, learning_history=None)
            if ranked_unlearned:
                action_before = ranked_unlearned[0].route
                route_score_before = ranked_unlearned[0].score

            if history_dict:
                ranked_learned = rank_routes(route_candidates, learning_history=history_dict)
                if ranked_learned:
                    action_after = ranked_learned[0].route
                    route_score_after = ranked_learned[0].score
                    learning_stats_for_route = history_dict.get(action_after)
            else:
                action_after = action_before
                route_score_after = route_score_before
        except Exception:
            pass

    # 2. Build Authoritative System Evaluation Scorecard
    scorecard = build_system_evaluation_scorecard(
        incident=incident,
        decision=decision,
        safety_decision=safety_decision,
        orchestration_result=batch_result,
        learning_context=learning_stats_for_route or history_dict,
        route_score_before=route_score_before,
        route_score_after=route_score_after,
        action_before=action_before,
        action_after=action_after,
        revenue_impact=revenue_impact,
        eligible_amount=eligible_amount,
    )

    # 3. Determine Execution and Safety Statuses
    is_blocked = (
        not scorecard.safety_allowed
        or (batch_result is not None and not batch_result.get("safety_allowed", True))
        or scorecard.final_status == "BLOCKED"
    )

    has_executed = (
        batch_result is not None
        and not is_blocked
        and scorecard.final_status not in ("NO_EXECUTION", "BLOCKED")
        and scorecard.attempted_transactions > 0
    )

    # 4. Format Metric 1: Degradation (OBSERVED)
    deg_val = f"{scorecard.degradation_percentage_points:.2f} pp"
    deg_sub = f"Severity: {scorecard.severity} ({scorecard.transactions_observed:,} txns)"
    deg_prov = scorecard.get_provenance("degradation_percentage_points")

    # 5. Format Metric 2: Revenue at Risk (THEORETICAL / COUNTERFACTUAL)
    rev_val = f"₹{scorecard.revenue_at_risk:,.2f}"
    rev_sub = "Counterfactual exposure before intervention"
    rev_prov = scorecard.get_provenance("revenue_at_risk")

    # 6. Format Metric 3: Expected Loss Reduction (THEORETICAL / COUNTERFACTUAL)
    loss_val = f"{scorecard.expected_loss_reduction_percentage:.2f}%"
    loss_sub = f"₹{scorecard.expected_loss_reduction:,.2f} projected loss mitigated"
    loss_prov = scorecard.get_provenance("expected_loss_reduction")

    # 7. Format Metric 4: Recovery Rate (SIMULATED)
    rec_prov = scorecard.get_provenance("recovery_rate")
    if is_blocked:
        rec_rate_val = "0.00% (Blocked)"
        rec_rate_sub = "Execution blocked by safety policy"
    elif has_executed:
        rec_rate_val = f"{scorecard.recovery_rate * 100:.2f}%"
        rec_rate_sub = f"{scorecard.successful_recoveries:,}/{scorecard.attempted_transactions:,} canary txns recovered"
    else:
        rec_rate_val = "Not executed"
        rec_rate_sub = "Awaiting bounded canary execution"

    # 8. Format Metric 5: Net Recovered Value (SIMULATED)
    net_prov = scorecard.get_provenance("net_recovered_value")
    if is_blocked:
        net_rec_val = "₹0.00 (Blocked)"
        net_rec_sub = "Zero execution loss incurred"
    elif has_executed:
        net_rec_val = f"₹{scorecard.net_recovered_value:,.2f}"
        net_rec_sub = f"Gross: ₹{scorecard.recovered_amount:,.2f} | Cost: ₹{scorecard.execution_cost:,.2f}"
    else:
        net_rec_val = "Not executed"
        net_rec_sub = "Pre-execution baseline"

    # 9. Format Metric 6: Recovery ROI (SIMULATED)
    roi_prov = scorecard.get_provenance("recovery_roi")
    if is_blocked:
        roi_val = "N/A"
        roi_sub = "Zero execution cost (Blocked)"
    elif has_executed and scorecard.recovery_roi is not None:
        roi_val = f"{scorecard.recovery_roi:.2f}x"
        roi_sub = "Net value / execution cost"
    else:
        roi_val = "N/A"
        roi_sub = "No execution cost incurred"

    # 10. Format Metric 7: Safety Outcome (GOVERNED / EVALUATED)
    safe_prov = scorecard.get_provenance("safety_allowed")
    if scorecard.human_review_required:
        safe_val = "HUMAN REVIEW"
        safe_pill = "pill-amber"
    elif scorecard.safety_allowed and not is_blocked:
        safe_val = "ALLOWED"
        safe_pill = "pill-green"
    else:
        safe_val = "BLOCKED"
        safe_pill = "pill-red"
    safe_reason = scorecard.safety_reason

    # 11. Format Metric 8: Learning Evidence Lift (LEARNED)
    learn_prov = scorecard.get_provenance("learning_score_delta")
    top_target_route = (
        action_after
        or scorecard.selected_action.replace("ROUTE_SWITCH:", "").strip()
    )
    has_learning_evidence = bool(
        scorecard.learned_attempts > 0
        or scorecard.learning_evidence_confidence > 0.0
        or (bool(history_dict) and top_target_route in history_dict)
    )

    if has_learning_evidence:
        delta = scorecard.learning_score_delta
        if delta > 0:
            learn_lift_val = f"+{delta:.4f} score lift"
            learn_pill = "pill-green"
        elif delta < 0:
            learn_lift_val = f"{delta:.4f} score drop"
            learn_pill = "pill-amber"
        else:
            learn_lift_val = f"0.0000 ({scorecard.learned_attempts} attempts)"
            learn_pill = "pill-blue"
        learn_sub = f"{scorecard.learned_attempts} attempts | {scorecard.learning_evidence_confidence * 100:.1f}% confidence"
    else:
        learn_lift_val = "No learning evidence"
        learn_pill = "pill-blue"
        learn_sub = "No prior outcome feedback for this route"

    # 12. Compact Pipeline Status Summary
    # Selected action
    selected_act = scorecard.selected_action

    # Canary Decision
    canary_dec = scorecard.canary_decision
    if canary_dec == "EXPAND":
        canary_pill = "pill-green"
    elif canary_dec in ("STOP", "ESCALATE"):
        canary_pill = "pill-amber"
    elif canary_dec == "BLOCKED":
        canary_pill = "pill-red"
    else:
        canary_pill = "pill-blue"

    # Guardrail Decision
    guard_dec = scorecard.guardrail_decision
    if guard_dec == "CONTINUE":
        guard_pill = "pill-green"
    elif guard_dec in ("ROLLBACK", "STOP"):
        guard_pill = "pill-red"
    else:
        guard_pill = "pill-blue"

    # Final Status
    fin_status = scorecard.final_status
    if fin_status in ("RECOVERED", "COMPLETED"):
        fin_pill = "pill-green"
    elif fin_status in ("UNPROFITABLE", "BLOCKED"):
        fin_pill = "pill-red"
    elif fin_status == "NO_EXECUTION":
        fin_pill = "pill-blue"
    else:
        fin_pill = "pill-amber"

    # Rollback Required
    if scorecard.rollback_required:
        roll_val = "YES"
        roll_pill = "pill-red"
    else:
        roll_val = "NO"
        roll_pill = "pill-green"

    return DashboardEvaluationView(
        scorecard=scorecard,
        has_executed=has_executed,
        is_blocked=is_blocked,
        has_learning_evidence=has_learning_evidence,
        degradation_value=deg_val,
        degradation_provenance=deg_prov,
        degradation_sub=deg_sub,
        revenue_at_risk_value=rev_val,
        revenue_at_risk_provenance=rev_prov,
        revenue_at_risk_sub=rev_sub,
        expected_loss_reduction_value=loss_val,
        expected_loss_reduction_provenance=loss_prov,
        expected_loss_reduction_sub=loss_sub,
        recovery_rate_value=rec_rate_val,
        recovery_rate_provenance=rec_prov,
        recovery_rate_sub=rec_rate_sub,
        net_recovered_value=net_rec_val,
        net_recovered_provenance=net_prov,
        net_recovered_sub=net_rec_sub,
        recovery_roi_value=roi_val,
        recovery_roi_provenance=roi_prov,
        recovery_roi_sub=roi_sub,
        safety_status_value=safe_val,
        safety_provenance=safe_prov,
        safety_pill_class=safe_pill,
        safety_reason=safe_reason,
        learning_lift_value=learn_lift_val,
        learning_provenance=learn_prov,
        learning_pill_class=learn_pill,
        learning_sub=learn_sub,
        selected_action=selected_act,
        canary_decision=canary_dec,
        canary_pill_class=canary_pill,
        guardrail_decision=guard_dec,
        guardrail_pill_class=guard_pill,
        final_status=fin_status,
        final_pill_class=fin_pill,
        rollback_required=roll_val,
        rollback_pill_class=roll_pill,
    )
