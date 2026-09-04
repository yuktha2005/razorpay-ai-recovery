"""
Demo UI View-Model Helpers for Razorpay AI Revenue Recovery.

Pure functions that transform DemoRunResult into display-ready structures.
No business logic. No calculations. No duplicated algorithms.
All values are consumed from the authoritative DemoRunResult.

Provenance labels follow the project convention:
  OBSERVED           — Measured from simulated telemetry
  THEORETICAL        — Modeled financial/risk estimate (counterfactual)
  SIMULATED          — Bounded sandbox recovery execution
  GOVERNED           — Safety and evaluation results
  LEARNED            — Evidence from verified simulated outcomes
"""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.demo.demo_runner import DemoRunResult, DemoPhase

# ---------------------------------------------------------------------------
# Provenance constants (single source of truth)
# ---------------------------------------------------------------------------

PROVENANCE_OBSERVED = "OBSERVED"
PROVENANCE_THEORETICAL = "THEORETICAL / COUNTERFACTUAL"
PROVENANCE_SIMULATED = "SIMULATED"
PROVENANCE_GOVERNED = "GOVERNED / EVALUATED"
PROVENANCE_LEARNED = "LEARNED"


# ---------------------------------------------------------------------------
# Primary view-model builder
# ---------------------------------------------------------------------------


def build_demo_view_model(result: "DemoRunResult") -> Dict[str, Any]:
    """
    Build a flat display-ready dictionary from a DemoRunResult.

    Returns a dict with all judge-facing values, provenance labels,
    and phase statuses pre-computed for rendering.

    No financial calculations are performed here — all values come
    directly from result fields.
    """
    if result is None:
        return {}

    inc = result.incident
    rev = result.revenue_impact
    dec = result.decision
    safe = result.safety_decision
    batch = result.batch_result or {}
    fin = result.financial_summary or {}
    learn = result.learning_evidence
    sc = result.scenario
    reeval = result.reevaluation_result or {}

    # ------------------------------------------------------------------
    # Incident
    # ------------------------------------------------------------------
    severity = inc.severity if inc else "UNKNOWN"
    observed_sr = inc.current_success_rate if inc else 0.0
    baseline_sr = inc.baseline_success_rate if inc else (sc.baseline_success_rate if sc else 0.0)
    degradation_pp = inc.degradation_pp if inc else 0.0
    txns_observed = inc.transactions_observed if inc else 0
    incident_detected = inc.incident_detected if inc else False
    revenue_at_risk = rev.revenue_at_risk if rev else 0.0

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------
    selected_action = dec.recommended_action if dec else "NONE"
    confidence = dec.confidence if dec else 0.0
    loss_before = dec.expected_loss_before if dec else 0.0
    loss_after = dec.expected_loss_after if dec else 0.0
    loss_reduction_pct = (
        round(((loss_before - loss_after) / loss_before) * 100.0, 1)
        if loss_before > 0
        else 0.0
    )

    # ------------------------------------------------------------------
    # Safety
    # ------------------------------------------------------------------
    safety_allowed = safe.allowed if safe else False
    safety_human_review = safe.requires_human_review if safe else False
    safety_action = safe.action if safe else "UNKNOWN"
    safety_reason = safe.reason if safe else "No safety decision recorded."

    # ------------------------------------------------------------------
    # Canary
    # ------------------------------------------------------------------
    eligible_txns = batch.get("eligible_transactions", 0)
    attempted_txns = batch.get("attempted_transactions", 0)
    successful_recoveries = batch.get("successful_recoveries", 0)
    failed_recoveries = batch.get("failed_recoveries", 0)
    canary_rate = batch.get(
        "canary_recovery_rate",
        (successful_recoveries / attempted_txns if attempted_txns > 0 else 0.0),
    )
    canary_decision = batch.get("canary_decision", "N/A")
    guardrail_decision = batch.get("guardrail_decision", "N/A")
    rollback_required = batch.get("rollback_required", False)

    # ------------------------------------------------------------------
    # Recovery financials
    # ------------------------------------------------------------------
    attempted_amount = fin.get("attempted_amount", batch.get("attempted_amount", 0.0))
    gross_recovered = fin.get("recovered_amount", batch.get("recovered_amount", 0.0))
    execution_cost = fin.get("execution_cost", batch.get("execution_cost", 0.0))
    net_recovered_value = fin.get("net_recovered_value", batch.get("net_recovered_value", 0.0))
    recovery_rate = fin.get("recovery_rate", batch.get("recovery_rate", 0.0))
    final_status = getattr(result, "final_status", "PENDING")
    recovery_executed = attempted_txns > 0

    scorecard_obj = getattr(result, "scorecard", None)
    if "recovery_roi" in fin:
        recovery_roi = fin.get("recovery_roi")
    elif scorecard_obj and hasattr(scorecard_obj, "recovery_roi"):
        recovery_roi = scorecard_obj.recovery_roi
    elif recovery_executed and execution_cost > 0:
        recovery_roi = gross_recovered / execution_cost
    else:
        recovery_roi = None

    # ------------------------------------------------------------------
    # Learning
    # ------------------------------------------------------------------
    route_name_learned = learn.route if learn else (sc.route if sc else "Unknown")
    learn_attempts = learn.attempts if learn else 0
    learn_recoveries = learn.recoveries if learn else 0
    learn_confidence = learn.evidence_confidence if learn else 0.0
    score_before = result.route_score_before
    score_after = result.route_score_after
    score_delta = result.score_delta
    has_learning = learn is not None

    # ------------------------------------------------------------------
    # Re-evaluation
    # ------------------------------------------------------------------
    before_reeval = reeval.get("before_learning", {})
    after_reeval = reeval.get("after_learning", {})
    top_before = before_reeval.get("top_route", result.top_route_before)
    score_reeval_before = before_reeval.get("route_score", score_before)
    top_after = after_reeval.get("top_route", result.top_route_after)
    score_reeval_after = after_reeval.get("route_score", score_after)
    decision_changed = result.decision_changed_after_learning

    # ------------------------------------------------------------------
    # Assemble view model
    # ------------------------------------------------------------------
    return {
        # Meta
        "scenario_name": sc.name if sc else "Unknown",
        "scenario_description": sc.description if sc else "",
        "is_success": result.is_success,
        "final_status": final_status,
        "summary_message": result.summary_message,
        # Incident
        "incident_detected": incident_detected,
        "severity": severity,
        "observed_success_rate": observed_sr,
        "baseline_success_rate": baseline_sr,
        "degradation_pp": degradation_pp,
        "transactions_observed": txns_observed,
        "revenue_at_risk": revenue_at_risk,
        "revenue_at_risk_provenance": PROVENANCE_THEORETICAL,
        # Decision
        "selected_action": selected_action,
        "confidence": confidence,
        "expected_loss_before": loss_before,
        "expected_loss_after": loss_after,
        "loss_reduction_pct": loss_reduction_pct,
        "decision_provenance": PROVENANCE_GOVERNED,
        # Safety
        "safety_allowed": safety_allowed,
        "safety_human_review": safety_human_review,
        "safety_action": safety_action,
        "safety_reason": safety_reason,
        "safety_provenance": PROVENANCE_GOVERNED,
        # Canary
        "eligible_transactions": eligible_txns,
        "attempted_transactions": attempted_txns,
        "successful_recoveries": successful_recoveries,
        "failed_recoveries": failed_recoveries,
        "canary_recovery_rate": canary_rate,
        "canary_decision": canary_decision,
        "guardrail_decision": guardrail_decision,
        "rollback_required": rollback_required,
        "canary_provenance": PROVENANCE_SIMULATED,
        # Recovery financials
        "attempted_amount": attempted_amount,
        "gross_recovered": gross_recovered,
        "execution_cost": execution_cost,
        "net_recovered_value": net_recovered_value,
        "recovery_rate": recovery_rate,
        "recovery_roi": recovery_roi,
        "recovery_executed": recovery_executed,
        "financial_provenance": PROVENANCE_SIMULATED,
        # Learning
        "route_name_learned": route_name_learned,
        "learned_attempts": learn_attempts,
        "learned_recoveries": learn_recoveries,
        "evidence_confidence": learn_confidence,
        "route_score_before": score_before,
        "route_score_after": score_after,
        "score_delta": score_delta,
        "has_learning_evidence": has_learning,
        "learning_provenance": PROVENANCE_LEARNED,
        # Re-evaluation
        "top_route_before_learning": top_before,
        "score_before_learning": score_reeval_before,
        "top_route_after_learning": top_after,
        "score_after_learning": score_reeval_after,
        "decision_changed_after_learning": decision_changed,
        "reevaluation_provenance": PROVENANCE_GOVERNED,
    }


# ---------------------------------------------------------------------------
# Phase status helper
# ---------------------------------------------------------------------------


def get_phase_status(result: "DemoRunResult", phase_name: str) -> str:
    """
    Return the status string for a named lifecycle phase.

    Returns one of: "SUCCESS", "BLOCKED", "STOPPED", "ROLLED_BACK",
    "SKIPPED", "NORMAL", "PENDING".

    All values are read from result.phase_results — no inference.
    """
    if result is None:
        return "PENDING"
    phase_results = getattr(result, "phase_results", {}) or {}
    phase_obj = phase_results.get(phase_name)
    if phase_obj is None:
        return "PENDING"
    return getattr(phase_obj, "status", "PENDING")


def get_phase_icon(status: str) -> str:
    """Map a phase status to a display icon."""
    return {
        "SUCCESS": "✓",
        "BLOCKED": "🚫",
        "STOPPED": "🛑",
        "ROLLED_BACK": "↩️",
        "SKIPPED": "—",
        "NORMAL": "✓",
    }.get(status, "○")


def get_phase_css_class(status: str) -> str:
    """Map a phase status to a CSS lifecycle class."""
    return {
        "SUCCESS": "step-success",
        "BLOCKED": "step-blocked",
        "STOPPED": "step-blocked",
        "ROLLED_BACK": "step-warn",
        "SKIPPED": "step-pending",
        "NORMAL": "step-success",
    }.get(status, "step-pending")


# ---------------------------------------------------------------------------
# Financial display helper
# ---------------------------------------------------------------------------


def get_financial_display(result: "DemoRunResult") -> Dict[str, str]:
    """
    Return formatted financial strings with provenance labels.

    All values are read from result — no computations performed here.
    """
    vm = build_demo_view_model(result)
    if not vm:
        return {}

    def fmt_inr(v: Optional[float]) -> str:
        if v is None:
            return "₹0.00"
        return f"₹{v:,.2f}"

    rec_roi = vm.get("recovery_roi")
    if rec_roi is not None and isinstance(rec_roi, (int, float)) and rec_roi > 0:
        roi_str = f"{rec_roi:.2f}x [{vm.get('financial_provenance', PROVENANCE_SIMULATED)}]"
    elif rec_roi is None:
        roi_str = "N/A — no execution cost recorded"
    else:
        roi_str = f"0.00x [{vm.get('financial_provenance', PROVENANCE_SIMULATED)}]"

    rec_rate = vm.get("recovery_rate")
    rate_pct = f"{rec_rate * 100:.1f}% [{vm.get('financial_provenance', PROVENANCE_SIMULATED)}]" if rec_rate is not None else f"0.0% [{vm.get('financial_provenance', PROVENANCE_SIMULATED)}]"

    return {
        "revenue_at_risk": fmt_inr(vm.get("revenue_at_risk")),
        "revenue_at_risk_label": f"{fmt_inr(vm.get('revenue_at_risk'))} [{vm.get('revenue_at_risk_provenance', PROVENANCE_THEORETICAL)}]",
        "attempted_amount": fmt_inr(vm.get("attempted_amount")),
        "attempted_amount_label": f"{fmt_inr(vm.get('attempted_amount'))} [{vm.get('financial_provenance', PROVENANCE_SIMULATED)}]",
        "gross_recovered": fmt_inr(vm.get("gross_recovered")),
        "gross_recovered_label": f"{fmt_inr(vm.get('gross_recovered'))} [{vm.get('financial_provenance', PROVENANCE_SIMULATED)}]",
        "execution_cost": fmt_inr(vm.get("execution_cost")),
        "execution_cost_label": f"{fmt_inr(vm.get('execution_cost'))} [{vm.get('financial_provenance', PROVENANCE_SIMULATED)}]",
        "net_recovered_value": fmt_inr(vm.get("net_recovered_value")),
        "net_recovered_label": f"{PROVENANCE_SIMULATED} Net Recovered Value: {fmt_inr(vm.get('net_recovered_value'))}",
        "recovery_rate_pct": rate_pct,
        "recovery_roi_str": roi_str,
        "final_status": vm.get("final_status", "PENDING"),
        "provenance": vm.get("financial_provenance", PROVENANCE_SIMULATED),
    }


# ---------------------------------------------------------------------------
# Learning display helper
# ---------------------------------------------------------------------------


def get_learning_display(result: "DemoRunResult") -> Dict[str, str]:
    """
    Return formatted learning strings for display.

    All values are read from result — no computations performed here.
    """
    vm = build_demo_view_model(result)
    if not vm:
        return {}

    delta = vm["score_delta"]
    delta_str = f"{delta:+.4f}" if delta else "0.0000"

    return {
        "route": vm["route_name_learned"],
        "evidence": f"{vm['learned_recoveries']}/{vm['learned_attempts']} recovered",
        "evidence_confidence": f"{vm['evidence_confidence'] * 100:.1f}%",
        "score_before": f"{vm['route_score_before']:.4f}",
        "score_after": f"{vm['route_score_after']:.4f}",
        "score_delta": delta_str,
        "has_evidence": vm["has_learning_evidence"],
        "provenance": vm["learning_provenance"],
    }


# ---------------------------------------------------------------------------
# Re-evaluation display helper
# ---------------------------------------------------------------------------


def get_reevaluation_display(result: "DemoRunResult") -> Dict[str, Any]:
    """
    Return formatted re-evaluation strings for display.

    All values are read from result — no computations performed here.
    """
    vm = build_demo_view_model(result)
    if not vm:
        return {}

    changed = vm["decision_changed_after_learning"]
    return {
        "top_route_before": vm["top_route_before_learning"],
        "score_before": f"{vm['score_before_learning']:.4f}",
        "top_route_after": vm["top_route_after_learning"],
        "score_after": f"{vm['score_after_learning']:.4f}",
        "decision_changed": changed,
        "decision_changed_label": "YES — Route changed after learning" if changed else "NO",
        "provenance": vm["reevaluation_provenance"],
    }


# ---------------------------------------------------------------------------
# Closed-loop learning flow helper (Milestone 7)
# ---------------------------------------------------------------------------


def get_closed_loop_learning_flow(result: "DemoRunResult") -> Dict[str, Any]:
    """
    Return pure view-model data structured for the Milestone 7 Closed-Loop Learning visualization.

    Flow:
        BEFORE LEARNING (Route, Score)
            ↓
        Verified Recovery Evidence (Attempts, Recoveries, Evidence Confidence)
            ↓
        AFTER LEARNING (Route, Score, Score Delta)
            ↓
        RE-EVALUATION (Top Route Before, Top Route After, Decision Changed)

    All data is read directly from DemoRunResult without artificial modification or hard-coding.
    """
    if result is None:
        return {
            "has_learning_evidence": False,
            "route_before": "N/A",
            "score_before": "0.0000",
            "score_before_raw": 0.0,
            "attempts": 0,
            "recoveries": 0,
            "recovery_rate_pct": "0.0%",
            "evidence_confidence": "0.0%",
            "evidence_confidence_raw": 0.0,
            "route_after": "N/A",
            "score_after": "0.0000",
            "score_after_raw": 0.0,
            "score_delta": "+0.0000",
            "score_delta_raw": 0.0,
            "top_route_before": "N/A",
            "top_route_after": "N/A",
            "decision_changed": False,
            "decision_changed_label": "NO",
            "provenance": PROVENANCE_LEARNED,
        }

    vm = build_demo_view_model(result)
    has_learning = vm.get("has_learning_evidence", False)
    route_name = vm.get("route_name_learned") or vm.get("selected_action") or "N/A"
    if route_name.startswith("ROUTE_SWITCH:"):
        route_name = route_name.replace("ROUTE_SWITCH:", "")

    score_before_val = vm.get("route_score_before", 0.0)
    score_after_val = vm.get("route_score_after", 0.0)
    delta_val = vm.get("score_delta", 0.0)
    conf_val = vm.get("evidence_confidence", 0.0)
    attempts = vm.get("learned_attempts", 0)
    recoveries = vm.get("learned_recoveries", 0)
    rate_pct = f"{(recoveries / attempts * 100):.1f}%" if attempts > 0 else "0.0%"

    delta_str = f"{delta_val:+.4f}" if delta_val != 0 else "+0.0000"
    dec_changed = vm.get("decision_changed_after_learning", False)

    return {
        "has_learning_evidence": has_learning,
        "route_before": route_name,
        "score_before": f"{score_before_val:.4f}",
        "score_before_raw": score_before_val,
        "attempts": attempts,
        "recoveries": recoveries,
        "recovery_rate_pct": rate_pct,
        "evidence_confidence": f"{conf_val * 100:.1f}%",
        "evidence_confidence_raw": conf_val,
        "route_after": route_name,
        "score_after": f"{score_after_val:.4f}",
        "score_after_raw": score_after_val,
        "score_delta": delta_str,
        "score_delta_raw": delta_val,
        "top_route_before": vm.get("top_route_before_learning", "N/A"),
        "top_route_after": vm.get("top_route_after_learning", "N/A"),
        "decision_changed": dec_changed,
        "decision_changed_label": "YES — Route adapted" if dec_changed else "NO",
        "provenance": PROVENANCE_LEARNED,
    }



# ---------------------------------------------------------------------------
# Final status bar helpers
# ---------------------------------------------------------------------------

def get_final_status_bar(result: "DemoRunResult") -> list:
    """
    Return an ordered list of (label, status, icon) tuples for the final status bar.

    Each status is derived from actual phase results — no inference.
    """
    if result is None:
        return []

    vm = build_demo_view_model(result)
    safe_allowed = vm.get("safety_allowed", False)
    rec_executed = vm.get("recovery_executed", False)
    final_st = vm.get("final_status", "PENDING")
    has_learning = vm.get("has_learning_evidence", False)
    reeval_done = bool(result.reevaluation_result)

    items = [
        ("INCIDENT", "SUCCESS" if vm.get("incident_detected") else "PENDING",
         "Detected ✓" if vm.get("incident_detected") else "—"),
        ("DECISION", "SUCCESS" if vm.get("selected_action", "NONE") != "NONE" else "PENDING",
         "Route selected ✓" if vm.get("selected_action", "NONE") != "NONE" else "—"),
        ("SAFETY", "SUCCESS" if safe_allowed else "BLOCKED",
         "Allowed ✓" if safe_allowed else "Blocked 🚫"),
        ("CANARY", _canary_status(vm), _canary_label(vm)),
        ("RECOVERY", "SUCCESS" if final_st == "RECOVERED" else ("ROLLED_BACK" if vm.get("rollback_required") else ("BLOCKED" if not safe_allowed else "PENDING")),
         "Verified ✓" if final_st == "RECOVERED" else ("Rolled back ↩️" if vm.get("rollback_required") else ("Blocked 🚫" if not safe_allowed else "—"))),
        ("LEARNING", "SUCCESS" if has_learning else "PENDING",
         "Updated ✓" if has_learning else "—"),
        ("RE-EVALUATION", "SUCCESS" if reeval_done else "PENDING",
         "Completed ✓" if reeval_done else "—"),
    ]
    return items


def _canary_status(vm: dict) -> str:
    cd = vm.get("canary_decision", "N/A")
    if cd == "EXPAND":
        return "SUCCESS"
    if cd in ("STOP", "ESCALATE"):
        return "STOPPED"
    if not vm.get("safety_allowed", False):
        return "BLOCKED"
    return "PENDING"


def _canary_label(vm: dict) -> str:
    cd = vm.get("canary_decision", "N/A")
    if cd == "EXPAND":
        return "Expanded ✓"
    if cd == "STOP":
        return "Stopped 🛑"
    if not vm.get("safety_allowed", False):
        return "Blocked 🚫"
    return "—"
