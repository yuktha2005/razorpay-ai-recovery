"""
Learning View Model for Razorpay AI Revenue Recovery.

Transforms verified recovery learning statistics and Bayesian route scoring outputs
into a clean, judge-ready presentation view.

Strictly read-only, deterministic, and free of persistent side effects.
Does NOT train or retrain ML models.
Evidence accumulation + Bayesian route scoring.
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional

from src.intelligence.route_scoring import RouteScore, RouteScorer, rank_routes
from src.tracking.recovery_learning import (
    RecoveryLearningEngine,
    RouteLearningStats,
)


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert value to float, replacing NaN or Inf with default."""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    """Safely convert value to int."""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return int(f)
    except (ValueError, TypeError):
        return default


@dataclass
class RouteComparisonItem:
    """
    Comparison metrics for an individual payment route before and after verified recovery learning.
    """

    route: str
    observed_attempts: int
    observed_recoveries: int
    observed_success_rate: float
    learned_attempts: int
    learned_recoveries: int
    learned_recovery_rate: float
    evidence_confidence: float
    score_before: float
    score_after: float
    score_delta: float
    rank_before: int
    rank_after: int
    is_preferred_before: bool
    is_preferred_after: bool
    status_label: str  # "LIFT (+0.0090)", "UNCHANGED", "DROP"


@dataclass
class LearningComparisonView:
    """
    Complete presentation view model for Section 6 — Recovery Learning.
    """

    has_learning_evidence: bool
    route_comparisons: List[RouteComparisonItem]
    top_route_before: str
    top_route_after: str
    preferred_route_changed: bool
    adaptation_status: str  # "DECISION ADAPTED", "DECISION UNCHANGED", "NO LEARNING EVIDENCE"
    adaptation_summary: str
    learning_score_lift_value: str  # e.g. "+0.0090" or "No learning evidence"
    learning_provenance: str = "LEARNED"
    total_learned_attempts: int = 0
    total_learned_recoveries: int = 0
    overall_recovery_rate: float = 0.0
    mean_evidence_confidence: float = 0.0


def _extract_route_stats(
    route_name: str,
    learning_context: Any,
) -> Optional[Any]:
    """
    Extract route learning statistics for a specific route from any supported context format.
    """
    if learning_context is None:
        return None

    # 1. Object with get_route method (e.g. RecoveryLearningEngine, PersistentLearningHistory)
    if hasattr(learning_context, "get_route") and callable(learning_context.get_route):
        try:
            return learning_context.get_route(route_name)
        except Exception:
            pass

    # 2. Keyed dictionary
    if isinstance(learning_context, dict):
        # Direct key match
        target = str(route_name).strip()
        if target in learning_context:
            return learning_context[target]
        # Iterate keys in case of whitespace mismatches
        for k, v in learning_context.items():
            if str(k).strip() == target:
                return v

    # 3. List or tuple of statistics objects
    if isinstance(learning_context, (list, tuple)):
        target = str(route_name).strip()
        for item in learning_context:
            r = getattr(item, "route", None)
            if r is None and isinstance(item, dict):
                r = item.get("route")
            if r and str(r).strip() == target:
                return item

    # 4. Single statistics object matching route
    if hasattr(learning_context, "route"):
        if str(getattr(learning_context, "route", "")).strip() == str(route_name).strip():
            return learning_context

    return None


def build_learning_comparison(
    route_candidates: List[Dict[str, Any]],
    learning_context: Optional[Any] = None,
    pre_learning_context: Optional[Any] = None,
    target_route: Optional[str] = None,
) -> LearningComparisonView:
    """
    Build a deterministic presentation view of closed-loop recovery learning.

    Compares candidate routes before and after applying verified recovery evidence:
    1. Evaluates pre-learning route scores using the authoritative RouteScorer.
    2. Evaluates post-learning route scores using the authoritative RouteScorer with verified evidence.
    3. Identifies score lifts, rank adjustments, and whether the preferred decision adapted.

    Parameters
    ----------
    route_candidates : List[Dict[str, Any]]
        Candidate routes with observed baseline transaction and success counts.
    learning_context : Optional[Any]
        Post-recovery learning evidence (RecoveryLearningEngine, PersistentLearningHistory,
        RouteLearningStats, list, or dict).
    pre_learning_context : Optional[Any]
        Pre-recovery learning evidence (defaults to None for clean baseline).
    target_route : Optional[str]
        Specific route that executed recovery (if applicable).

    Returns
    -------
    LearningComparisonView
        Presentation view model strictly derived from authoritative domain scoring.
    """
    if not route_candidates:
        return LearningComparisonView(
            has_learning_evidence=False,
            route_comparisons=[],
            top_route_before="NONE",
            top_route_after="NONE",
            preferred_route_changed=False,
            adaptation_status="NO LEARNING EVIDENCE",
            adaptation_summary="No candidate routes provided for learning comparison.",
            learning_score_lift_value="No learning evidence",
            learning_provenance="LEARNED",
        )

    # -------------------------------------------------------------
    # 1. Route ranking before learning
    # -------------------------------------------------------------
    pre_ranked: List[RouteScore] = rank_routes(
        route_candidates,
        learning_history=pre_learning_context,
    )

    # -------------------------------------------------------------
    # 2. Route ranking after verified recovery evidence
    # -------------------------------------------------------------
    post_ranked: List[RouteScore] = rank_routes(
        route_candidates,
        learning_history=learning_context,
    )

    top_route_before = pre_ranked[0].route if pre_ranked else "NONE"
    top_route_after = post_ranked[0].route if post_ranked else "NONE"

    # Index lookups for O(1) comparison
    pre_score_map = {r.route: r for r in pre_ranked}
    post_score_map = {r.route: r for r in post_ranked}

    rank_before_map = {r.route: i + 1 for i, r in enumerate(pre_ranked)}
    rank_after_map = {r.route: i + 1 for i, r in enumerate(post_ranked)}

    comparisons: List[RouteComparisonItem] = []
    total_learned_attempts = 0
    total_learned_recoveries = 0
    confidence_sum = 0.0
    has_any_evidence = False

    for candidate in route_candidates:
        route_name = candidate.get("route", "")
        observed_attempts = _safe_int(candidate.get("transactions", 0))
        observed_recoveries = _safe_int(candidate.get("successes", 0))
        observed_rate = (
            observed_recoveries / observed_attempts
            if observed_attempts > 0
            else 0.0
        )

        stats = _extract_route_stats(route_name, learning_context)

        learned_attempts = 0
        learned_recoveries = 0
        learned_recovery_rate = 0.0
        evidence_confidence = 0.0

        if stats is not None:
            att = getattr(stats, "attempts", None)
            if att is None and isinstance(stats, dict):
                att = stats.get("attempts")
            learned_attempts = _safe_int(att)

            rec = getattr(stats, "recoveries", None)
            if rec is None and isinstance(stats, dict):
                rec = stats.get("recoveries")
            learned_recoveries = _safe_int(rec)

            rate = getattr(stats, "recovery_rate", None)
            if rate is None and isinstance(stats, dict):
                rate = stats.get("recovery_rate")
            learned_recovery_rate = _safe_float(rate)

            conf = getattr(stats, "evidence_confidence", None)
            if conf is None and isinstance(stats, dict):
                conf = stats.get("evidence_confidence")
            evidence_confidence = _safe_float(conf)

            if learned_attempts > 0:
                has_any_evidence = True
                total_learned_attempts += learned_attempts
                total_learned_recoveries += learned_recoveries
                confidence_sum += evidence_confidence

        score_before = (
            _safe_float(pre_score_map[route_name].score)
            if route_name in pre_score_map
            else 0.0
        )
        score_after = (
            _safe_float(post_score_map[route_name].score)
            if route_name in post_score_map
            else 0.0
        )
        score_delta = round(score_after - score_before, 4)

        rank_before = rank_before_map.get(route_name, 0)
        rank_after = rank_after_map.get(route_name, 0)

        is_pref_before = (rank_before == 1)
        is_pref_after = (rank_after == 1)

        if score_delta > 0:
            status_label = f"LIFT ({score_delta:+.4f})"
        elif score_delta < 0:
            status_label = f"DROP ({score_delta:+.4f})"
        else:
            status_label = "UNCHANGED"

        comparisons.append(
            RouteComparisonItem(
                route=route_name,
                observed_attempts=observed_attempts,
                observed_recoveries=observed_recoveries,
                observed_success_rate=round(observed_rate, 4),
                learned_attempts=learned_attempts,
                learned_recoveries=learned_recoveries,
                learned_recovery_rate=round(learned_recovery_rate, 4),
                evidence_confidence=round(evidence_confidence, 4),
                score_before=round(score_before, 6),
                score_after=round(score_after, 6),
                score_delta=score_delta,
                rank_before=rank_before,
                rank_after=rank_after,
                is_preferred_before=is_pref_before,
                is_preferred_after=is_pref_after,
                status_label=status_label,
            )
        )

    # Sort comparisons by post-learning rank
    comparisons.sort(key=lambda item: item.rank_after)

    preferred_route_changed = (
        top_route_before != top_route_after
        and bool(top_route_before and top_route_after)
        and has_any_evidence
    )

    if not has_any_evidence:
        adaptation_status = "NO LEARNING EVIDENCE"
        adaptation_summary = "No verified recovery evidence recorded yet."
        learning_score_lift_value = "No learning evidence"
    elif preferred_route_changed:
        adaptation_status = "DECISION ADAPTED"
        adaptation_summary = (
            f"Verified recovery evidence changed the preferred route from "
            f"{top_route_before} to {top_route_after}."
        )
        lift = max((c.score_delta for c in comparisons if c.score_delta > 0), default=0.0)
        learning_score_lift_value = f"{lift:+.4f}" if lift > 0 else "Recorded"
    else:
        adaptation_status = "DECISION UNCHANGED"
        adaptation_summary = (
            f"Verified recovery evidence recorded. Current route remains preferred ({top_route_after})."
        )
        # Identify lift for target route or highest lift
        target_item = None
        if target_route:
            for c in comparisons:
                if c.route == target_route:
                    target_item = c
                    break
        if target_item and target_item.score_delta > 0:
            learning_score_lift_value = f"{target_item.score_delta:+.4f}"
        else:
            max_lift = max((c.score_delta for c in comparisons if c.score_delta > 0), default=0.0)
            learning_score_lift_value = f"{max_lift:+.4f}" if max_lift > 0 else "Recorded"

    num_learned_routes = sum(1 for c in comparisons if c.learned_attempts > 0)
    overall_recovery_rate = (
        total_learned_recoveries / total_learned_attempts
        if total_learned_attempts > 0
        else 0.0
    )
    mean_confidence = (
        confidence_sum / max(1, num_learned_routes)
        if num_learned_routes > 0
        else 0.0
    )

    return LearningComparisonView(
        has_learning_evidence=has_any_evidence,
        route_comparisons=comparisons,
        top_route_before=top_route_before,
        top_route_after=top_route_after,
        preferred_route_changed=preferred_route_changed,
        adaptation_status=adaptation_status,
        adaptation_summary=adaptation_summary,
        learning_score_lift_value=learning_score_lift_value,
        learning_provenance="LEARNED",
        total_learned_attempts=total_learned_attempts,
        total_learned_recoveries=total_learned_recoveries,
        overall_recovery_rate=round(overall_recovery_rate, 4),
        mean_evidence_confidence=round(mean_confidence, 4),
    )
