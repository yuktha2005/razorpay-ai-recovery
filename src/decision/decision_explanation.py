from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.models.domain import (
    Decision,
    Intervention,
    LossEstimate,
    RiskAssessment,
    SafetyDecision,
)


@dataclass
class DecisionExplanation:
    """
    Structured, deterministic explanation of an AI recovery decision.

    Provides a complete, human-auditable breakdown of why an intervention
    was chosen, its risk context, financial exposure, safety evaluation,
    and alternative actions considered.
    """

    payment_id: str
    incident_summary: str
    risk_summary: str
    financial_summary: str
    selected_action: str
    selected_action_reason: str
    confidence_summary: str
    alternative_actions: List[str]
    safety_summary: str
    key_factors: List[str]


def build_decision_explanation(
    decision: Decision,
    risk_assessment: Optional[RiskAssessment] = None,
    loss_estimate: Optional[LossEstimate] = None,
    safety_decision: Optional[SafetyDecision] = None,
    route_context: Optional[Dict[str, Any]] = None,
) -> DecisionExplanation:
    """
    Convert decision engine and safety controller outputs into a structured,
    deterministic explanation.

    This function does not use LLMs, random numbers, or external APIs.
    All outputs are generated deterministically from the provided domain objects.
    """
    payment_id = str(getattr(decision, "payment_id", "Not available"))

    # ---------------------------------------------------------
    # 1. Incident & Route Context Summary
    # ---------------------------------------------------------
    if route_context and isinstance(route_context, dict):
        route_parts = []
        if "route" in route_context and route_context["route"]:
            route_parts.append(f"Route: {route_context['route']}")

        if "observed_success_rate" in route_context:
            obs = route_context["observed_success_rate"]
            if isinstance(obs, (int, float)):
                obs_pct = obs * 100.0 if obs <= 1.0 else obs
                route_parts.append(f"Observed Success Rate: {obs_pct:.1f}%")

        if "adjusted_success_rate" in route_context:
            adj = route_context["adjusted_success_rate"]
            if isinstance(adj, (int, float)):
                adj_pct = adj * 100.0 if adj <= 1.0 else adj
                route_parts.append(f"Adjusted Success Rate: {adj_pct:.1f}%")

        if "evidence_confidence" in route_context:
            econf = route_context["evidence_confidence"]
            if isinstance(econf, (int, float)):
                econf_pct = econf * 100.0 if econf <= 1.0 else econf
                route_parts.append(f"Evidence Confidence: {econf_pct:.1f}%")

        if "score" in route_context and isinstance(
            route_context["score"], (int, float)
        ):
            route_parts.append(f"Score: {route_context['score']:.2f}")

        if "explanation" in route_context and route_context["explanation"]:
            route_parts.append(f"Evidence: {route_context['explanation']}")

        if route_parts:
            incident_summary = "Route Evidence: " + " | ".join(route_parts)
        else:
            incident_summary = "No additional route evidence available."
    else:
        incident_summary = "No additional route evidence available."

    # ---------------------------------------------------------
    # 2. Risk Assessment Summary
    # ---------------------------------------------------------
    if risk_assessment is not None:
        risk_level = getattr(risk_assessment, "risk_level", "Not available")
        risk_score = getattr(risk_assessment, "risk_score", None)
        score_str = (
            f"{risk_score:.2f}"
            if isinstance(risk_score, (int, float))
            else "Not available"
        )

        prob_loss = getattr(risk_assessment, "probability_of_loss", None)
        if isinstance(prob_loss, (int, float)):
            prob_str = (
                f"{prob_loss * 100:.1f}%" if prob_loss <= 1.0 else f"{prob_loss:.1f}%"
            )
        else:
            prob_str = "Not available"

        risk_type = getattr(risk_assessment, "risk_type", "Not available")
        reasons = getattr(risk_assessment, "reasons", [])
        reasons_str = f" | Reasons: {'; '.join(reasons)}" if reasons else ""

        risk_summary = (
            f"Risk Level: {risk_level} | Risk Score: {score_str} | "
            f"Probability of Loss: {prob_str} | Risk Type: {risk_type}{reasons_str}"
        )
    else:
        risk_summary = "Risk assessment: Not available."

    # ---------------------------------------------------------
    # 3. Financial Impact Summary
    # ---------------------------------------------------------
    exp_before = getattr(decision, "expected_loss_before", None)
    if exp_before is None and loss_estimate is not None:
        exp_before = getattr(loss_estimate, "expected_loss", None)

    exp_after = getattr(decision, "expected_loss_after", None)
    est_value = getattr(decision, "estimated_value", None)

    before_str = (
        f"₹{exp_before:,.2f}"
        if isinstance(exp_before, (int, float))
        else "Not available"
    )
    after_str = (
        f"₹{exp_after:,.2f}"
        if isinstance(exp_after, (int, float))
        else "Not available"
    )
    val_str = (
        f"₹{est_value:,.2f}"
        if isinstance(est_value, (int, float))
        else "Not available"
    )

    fin_parts = [
        f"Expected Loss Before: {before_str}",
        f"Expected Loss After: {after_str}",
        f"Estimated Value: {val_str}",
    ]

    if loss_estimate is not None:
        exposure = getattr(loss_estimate, "financial_exposure", None)
        if isinstance(exposure, (int, float)):
            fin_parts.append(f"Financial Exposure: ₹{exposure:,.2f}")

    financial_summary = " | ".join(fin_parts)

    # ---------------------------------------------------------
    # 4. Action & Action Reason
    # ---------------------------------------------------------
    selected_action = str(
        getattr(decision, "recommended_action", "Not available")
    )
    selected_action_reason = str(
        getattr(decision, "explanation", "")
        or "No specific action reason provided."
    )

    # ---------------------------------------------------------
    # 5. Confidence Summary
    # ---------------------------------------------------------
    conf = getattr(decision, "confidence", None)
    if isinstance(conf, (int, float)):
        conf_pct = conf * 100.0 if conf <= 1.0 else conf
        confidence_summary = f"{conf_pct:.1f}% confidence"
    else:
        confidence_summary = "Confidence: Not available"

    # ---------------------------------------------------------
    # 6. Alternative Actions
    # ---------------------------------------------------------
    alternative_actions: List[str] = []
    alternatives = getattr(decision, "alternatives", []) or []
    for alt in alternatives:
        if isinstance(alt, str):
            alternative_actions.append(alt)
        elif isinstance(alt, dict):
            action_name = str(alt.get("action", "Unknown"))
            val_items = []
            benefit = alt.get("expected_benefit")
            if benefit is None:
                benefit = alt.get("estimated_value")
            if isinstance(benefit, (int, float)):
                val_items.append(f"Estimated Benefit: ₹{benefit:,.2f}")
            loss_after_val = alt.get("expected_loss_after")
            if isinstance(loss_after_val, (int, float)):
                val_items.append(f"Expected Loss After: ₹{loss_after_val:,.2f}")
            cost_val = alt.get("estimated_cost")
            if isinstance(cost_val, (int, float)):
                val_items.append(f"Cost: ₹{cost_val:,.2f}")

            if val_items:
                alternative_actions.append(
                    f"{action_name} ({', '.join(val_items)})"
                )
            else:
                alternative_actions.append(action_name)
        elif isinstance(alt, Intervention) or hasattr(alt, "action"):
            action_name = str(getattr(alt, "action", str(alt)))
            val_items = []
            benefit = getattr(alt, "expected_benefit", None)
            if benefit is None:
                benefit = getattr(alt, "estimated_value", None)
            if isinstance(benefit, (int, float)):
                val_items.append(f"Estimated Benefit: ₹{benefit:,.2f}")
            loss_after_val = getattr(alt, "expected_loss_after", None)
            if isinstance(loss_after_val, (int, float)):
                val_items.append(f"Expected Loss After: ₹{loss_after_val:,.2f}")
            cost_val = getattr(alt, "estimated_cost", None)
            if isinstance(cost_val, (int, float)):
                val_items.append(f"Cost: ₹{cost_val:,.2f}")

            if val_items:
                alternative_actions.append(
                    f"{action_name} ({', '.join(val_items)})"
                )
            else:
                alternative_actions.append(action_name)
        else:
            alternative_actions.append(str(alt))

    # ---------------------------------------------------------
    # 7. Safety Summary
    # ---------------------------------------------------------
    if safety_decision is not None:
        allowed = bool(getattr(safety_decision, "allowed", False))
        status_str = "Allowed" if allowed else "Blocked"
        review = bool(getattr(safety_decision, "requires_human_review", False))
        review_str = (
            "Human review required"
            if review
            else "Automated execution eligible"
        )
        reason = getattr(safety_decision, "reason", "") or "No reason provided."
        safety_summary = (
            f"Status: {status_str} | {review_str} | Reason: {reason}"
        )
    else:
        safety_summary = "Safety evaluation: Not available."

    # ---------------------------------------------------------
    # 8. Key Factors Supporting the Decision
    # ---------------------------------------------------------
    key_factors: List[str] = []

    # Risk factor
    if risk_assessment is not None:
        score_val = getattr(risk_assessment, "risk_score", None)
        score_str = (
            f" (score: {score_val:.2f})"
            if isinstance(score_val, (int, float))
            else ""
        )
        risk_lvl = getattr(risk_assessment, "risk_level", None)
        if risk_lvl in ("HIGH", "CRITICAL"):
            key_factors.append(
                f"Elevated risk level assessed: {risk_lvl}{score_str}."
            )
        elif getattr(risk_assessment, "reasons", None):
            key_factors.append(
                f"Risk factor identified: {risk_assessment.reasons[0]}"
            )
        elif risk_lvl:
            key_factors.append(
                f"Risk level assessed: {risk_lvl}{score_str}."
            )

    # Route degradation or stronger alternative route factor
    if route_context and isinstance(route_context, dict):
        obs = route_context.get("observed_success_rate")
        adj = route_context.get("adjusted_success_rate")
        target_route = route_context.get("route")

        if (
            isinstance(obs, (int, float))
            and isinstance(adj, (int, float))
        ):
            obs_pct = obs * 100.0 if obs <= 1.0 else obs
            adj_pct = adj * 100.0 if adj <= 1.0 else adj
            if obs < adj:
                key_factors.append(
                    f"Route degradation detected: observed success rate "
                    f"({obs_pct:.1f}%) is below adjusted baseline ({adj_pct:.1f}%)."
                )
            else:
                route_name = f" for {target_route}" if target_route else ""
                key_factors.append(
                    f"Alternative route has stronger evidence{route_name}: "
                    f"observed success rate ({obs_pct:.1f}%) exceeds baseline ({adj_pct:.1f}%)."
                )
        elif target_route:
            key_factors.append(
                f"Route evidence available for alternative target: {target_route}."
            )

    # Financial factor: expected loss
    if isinstance(exp_before, (int, float)) and exp_before > 0:
        key_factors.append(
            f"High expected loss before intervention: ₹{exp_before:,.2f}."
        )

    # Recovery value factor
    if isinstance(est_value, (int, float)) and est_value > 0:
        key_factors.append(
            f"Intervention offers positive estimated recovery value: ₹{est_value:,.2f}."
        )

    # Confidence factor
    if isinstance(conf, (int, float)):
        conf_pct = conf * 100.0 if conf <= 1.0 else conf
        if conf_pct >= 70.0:
            key_factors.append(
                f"High decision confidence: {conf_pct:.1f}%."
            )
        elif conf_pct >= 50.0:
            key_factors.append(
                f"Moderate decision confidence: {conf_pct:.1f}%."
            )

    # Safety factor
    if safety_decision is not None:
        if getattr(safety_decision, "allowed", False):
            key_factors.append("Safety policy passed: intervention is safe to execute.")
        else:
            reason_txt = getattr(safety_decision, "reason", "policy violation")
            key_factors.append(
                f"Safety gate blocked execution: {reason_txt}"
            )
        if getattr(safety_decision, "requires_human_review", False):
            key_factors.append(
                "Human review required prior to execution."
            )

    return DecisionExplanation(
        payment_id=payment_id,
        incident_summary=incident_summary,
        risk_summary=risk_summary,
        financial_summary=financial_summary,
        selected_action=selected_action,
        selected_action_reason=selected_action_reason,
        confidence_summary=confidence_summary,
        alternative_actions=alternative_actions,
        safety_summary=safety_summary,
        key_factors=key_factors,
    )
