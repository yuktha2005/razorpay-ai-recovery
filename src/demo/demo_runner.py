"""
Deterministic Demo Runner for Razorpay AI Revenue Recovery.

Orchestrates the canonical judge-ready demonstration using the EXISTING architecture.
Strictly simulation-safe, deterministic, and reproducible.
No wall-clock dependence, unseeded randomness, or external network calls.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
import pandas as pd

from src.demo.demo_scenario import (
    DemoScenario,
    CANONICAL_HAPPY_PATH,
    get_demo_scenario,
)
from src.intelligence.incident_intelligence import (
    IncidentAssessment,
    IncidentIntelligence,
)
from src.intelligence.incident_revenue import (
    IncidentRevenueCalculator,
    IncidentRevenueImpact,
)
from src.intelligence.route_scoring import RouteScore, RouteScorer, rank_routes
from src.decision.incident_decision_engine import (
    IncidentDecisionEngine,
    IncidentDecisionResult,
)
from src.models.domain import Decision, SafetyDecision
from src.safety.controller import SafetyController
from src.recovery.orchestrated_batch import execute_orchestrated_batch_recovery
from src.recovery.recovery_orchestrator import (
    RecoveryOrchestrator,
    RecoveryOrchestrationResult,
)
from src.tracking.financial_summary import calculate_financial_summary
from src.tracking.recovery_learning import (
    RecoveryLearningEngine,
    RouteLearningStats,
)
from src.audit_logger import load_audit_log
from src.evaluation.evaluation_adapter import (
    build_system_evaluation_scorecard,
    prepare_dashboard_evaluation_scorecard,
)
from src.evaluation.scorecard import SystemEvaluationScorecard


class DemoPhase(str, Enum):
    """
    Explicit lifecycle phases for the deterministic judge demo.
    """

    BASELINE = "BASELINE"
    INCIDENT = "INCIDENT"
    DECISION = "DECISION"
    SAFETY = "SAFETY"
    CANARY = "CANARY"
    RECOVERY = "RECOVERY"
    LEARNING = "LEARNING"
    REEVALUATION = "REEVALUATION"
    COMPLETE = "COMPLETE"


@dataclass
class PhaseResult:
    """
    Deterministic output of a demo lifecycle phase.
    """

    phase: DemoPhase
    title: str
    status: str  # "SUCCESS", "BLOCKED", "STOPPED", "ROLLED_BACK", "SKIPPED", "NORMAL"
    detail: str
    provenance: str
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LifecycleEvent:
    """
    Representation of an individual lifecycle phase in the recovery journey (backwards compatible).
    """

    step_number: int
    stage_id: str  # "HEALTHY", "DETECT", "QUANTIFY", "DECIDE", "SAFETY", "RECOVER", "VERIFY", "LEARN", "ADAPT"
    title: str
    status: str  # "SUCCESS", "BLOCKED", "STOPPED", "ROLLED_BACK", "SKIPPED", "NORMAL"
    detail: str
    provenance: str
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DemoRunResult:
    """
    Complete output of a deterministic end-to-end demo execution.
    """

    scenario: DemoScenario
    incident: Optional[IncidentAssessment]
    revenue_impact: Optional[IncidentRevenueImpact]
    decision_result: Optional[IncidentDecisionResult]
    decision: Optional[Decision]
    safety_decision: Optional[SafetyDecision]
    batch_result: Optional[Dict[str, Any]]
    orchestration_result: Optional[RecoveryOrchestrationResult]
    financial_summary: Optional[Dict[str, Any]]
    scorecard: Optional[SystemEvaluationScorecard]
    scorecard_view: Optional[Any]
    route_score_before: float
    route_score_after: float
    score_delta: float
    top_route_before: str
    top_route_after: str
    ranking_changed: bool
    learning_evidence: Optional[RouteLearningStats]
    lifecycle_events: List[LifecycleEvent]
    is_success: bool
    final_status: str
    summary_message: str
    execution_timestamp: str
    phase_results: Dict[str, PhaseResult] = field(default_factory=dict)
    reevaluation_result: Optional[Dict[str, Any]] = None
    decision_changed_after_learning: bool = False
    audit_references: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def scenario_name(self) -> str:
        return self.scenario.name

    @property
    def scenario_description(self) -> str:
        return self.scenario.description

    @property
    def incident_result(self) -> Optional[IncidentAssessment]:
        return self.incident

    @property
    def safety_result(self) -> Optional[SafetyDecision]:
        return self.safety_decision

    @property
    def canary_result(self) -> Optional[Dict[str, Any]]:
        return self.batch_result

    @property
    def recovery_result(self) -> Optional[Dict[str, Any]]:
        return self.batch_result

    @property
    def financial_result(self) -> Optional[Dict[str, Any]]:
        return self.financial_summary

    @property
    def learning_result(self) -> Optional[RouteLearningStats]:
        return self.learning_evidence

    def format_report(self) -> str:
        return format_demo_report(self)

    @property
    def report(self) -> str:
        return self.format_report()


def format_demo_report(result: DemoRunResult) -> str:
    """
    Render a concise, deterministic human-readable report of the end-to-end demo.
    Conforms to the deterministic judge report specification.
    """
    sc = result.scenario
    inc = result.incident
    rev = result.revenue_impact
    dec = result.decision
    safe = result.safety_decision
    batch = result.batch_result or {}
    fin = result.financial_summary or {}
    learn = result.learning_evidence

    # Route info
    alt_routes = [c["route"] for c in sc.route_candidates] if sc.route_candidates else ["None"]
    alt_route_str = ", ".join(alt_routes)

    # Incident metrics
    sev = inc.severity if inc else "UNKNOWN"
    cur_sr = inc.current_success_rate if inc else 0.0
    base_sr = inc.baseline_success_rate if inc else sc.baseline_success_rate
    deg_pp = inc.degradation_pp if inc else 0.0
    txns_obs = inc.transactions_observed if inc else 0
    rar = rev.revenue_at_risk if rev else 0.0

    # Decision metrics
    act = dec.recommended_action if dec else "NONE"
    conf = dec.confidence if dec else 0.0
    el_before = dec.expected_loss_before if dec else 0.0
    el_after = dec.expected_loss_after if dec else 0.0
    loss_red_pct = (
        ((el_before - el_after) / el_before * 100)
        if el_before > 0
        else 0.0
    )

    # Safety metrics
    allowed_str = "ALLOWED" if safe and safe.allowed else "BLOCKED"
    human_str = "YES" if safe and safe.requires_human_review else "NO"
    reason_str = safe.reason if safe else "No safety decision"

    # Canary metrics
    elig_txns = batch.get("eligible_transactions", 0)
    att_txns = batch.get("attempted_transactions", 0)
    succ_rec = batch.get("successful_recoveries", 0)
    fail_rec = batch.get("failed_recoveries", 0)
    canary_sr = batch.get("canary_recovery_rate", (succ_rec / att_txns if att_txns > 0 else 0.0))
    canary_dec = batch.get("canary_decision", "N/A")

    # Recovery metrics
    att_amt = fin.get("attempted_amount", batch.get("attempted_amount", 0.0))
    gross_rec = fin.get("recovered_amount", batch.get("recovered_amount", 0.0))
    cost = fin.get("execution_cost", batch.get("execution_cost", 0.0))
    net_rec = fin.get("net_recovered_value", batch.get("net_recovered_value", 0.0))
    rec_rate = fin.get("recovery_rate", batch.get("recovery_rate", 0.0))
    roi = fin.get("recovery_roi", (gross_rec / max(1.0, cost) if cost > 0 else 0.0))
    fin_status = result.final_status

    # Learning metrics
    score_before = result.route_score_before
    score_after = result.route_score_after
    score_delta = result.score_delta
    ev_conf = learn.evidence_confidence if learn else 0.0

    # Re-evaluation metrics
    reeval = result.reevaluation_result or {}
    before_reeval = reeval.get("before_learning", {})
    after_reeval = reeval.get("after_learning", {})
    top_b = before_reeval.get("top_route", result.top_route_before)
    score_b = before_reeval.get("route_score", score_before)
    top_a = after_reeval.get("top_route", result.top_route_after)
    score_a = after_reeval.get("route_score", score_after)
    dec_changed = result.decision_changed_after_learning or result.ranking_changed

    lines = [
        "============================================================",
        "RAZORPAY PAYMENT RELIABILITY ENGINE — DEMO",
        "============================================================",
        "",
        "[1] BASELINE",
        f"Primary Route: {sc.route}",
        f"Baseline Success Rate: {base_sr:.1%}",
        f"Alternate Route: {alt_route_str}",
        "",
        "[2] INCIDENT DETECTED",
        f"Severity: {sev}",
        f"Observed Success Rate: {cur_sr:.1%}",
        f"Baseline Success Rate: {base_sr:.1%}",
        f"Degradation: {deg_pp:.1f} pp",
        f"Transactions: {txns_obs}",
        f"Revenue at Risk: ₹{rar:,.2f} [THEORETICAL]",
        "",
        "[3] AI DECISION",
        f"Selected Action: {act}",
        f"Confidence: {conf:.1%}",
        f"Expected Loss Before: ₹{el_before:,.2f}",
        f"Expected Loss After: ₹{el_after:,.2f}",
        f"Expected Loss Reduction: {loss_red_pct:.1f}%",
        "",
        "[4] SAFETY GATE",
        f"Allowed: {allowed_str}",
        f"Human Review: {human_str}",
        f"Reason: {reason_str}",
        "",
        "[5] BOUNDED CANARY",
        f"Eligible: {elig_txns}",
        f"Attempted: {att_txns}",
        f"Recovered: {succ_rec}",
        f"Failed: {fail_rec}",
        f"Canary Recovery Rate: {canary_sr:.1%}",
        f"Canary Decision: {canary_dec}",
        "",
        "[6] RECOVERY OUTCOME",
        f"Attempted Amount: ₹{att_amt:,.2f} [SIMULATED]",
        f"Gross Recovered: ₹{gross_rec:,.2f} [SIMULATED]",
        f"Execution Cost: ₹{cost:,.2f} [SIMULATED]",
        f"Net Recovered Value: ₹{net_rec:,.2f} [SIMULATED]",
        f"Recovery Rate: {rec_rate:.1%} [SIMULATED]",
        f"ROI: {roi:.2f}x [SIMULATED]",
        f"Final Status: {fin_status}",
        "",
        "[7] LEARNING",
        f"Route Score Before: {score_before:.4f}",
        f"Route Score After: {score_after:.4f}",
        f"Learning Score Delta: {score_delta:+.4f}",
        f"Evidence Confidence: {ev_conf:.1%}",
        "",
        "[8] RE-EVALUATION",
        f"Before Learning: {top_b} (Score: {score_b:.4f})",
        f"After Learning: {top_a} (Score: {score_a:.4f})",
        f"Decision Changed: {'YES' if dec_changed else 'NO'}",
        "",
        "============================================================",
        "FINAL RESULT",
        "============================================================",
        f"Incident → {'Detected' if inc and inc.incident_detected else 'Normal'}",
        f"Decision → {act}",
        f"Safety → {allowed_str}",
        f"Canary → {canary_dec}",
        f"Recovery → {fin_status}",
        f"Learning → {'UPDATED' if learn is not None else 'SKIPPED'}",
        "============================================================",
    ]
    return "\n".join(lines)


class DemoRunner:
    """
    Deterministic orchestrator for executing end-to-end revenue recovery demonstrations.

    Reuses authoritative domain components exclusively:
    - IncidentIntelligence (detection)
    - IncidentRevenueCalculator (revenue quantification)
    - RouteScorer / rank_routes (route intelligence)
    - IncidentDecisionEngine (intervention decision)
    - SafetyController (safety policy gate)
    - RecoveryOrchestrator / execute_orchestrated_batch_recovery (bounded canary)
    - RecoveryOutcomeVerifier / calculate_financial_summary (verification)
    - RecoveryLearningEngine (Bayesian evidence updates)
    - build_system_evaluation_scorecard (evaluation scorecard)
    """

    # Deterministic fixed reference timestamp to eliminate wall-clock drift
    DEFAULT_ANCHOR = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)

    def __init__(
        self,
        learning_engine: Optional[RecoveryLearningEngine] = None,
        orchestrator: Optional[RecoveryOrchestrator] = None,
    ):
        self._learning_engine = learning_engine
        if orchestrator is not None:
            self._orchestrator = orchestrator
        elif learning_engine is not None:
            self._orchestrator = RecoveryOrchestrator(learning_engine=learning_engine)
        else:
            self._orchestrator = None
        self._last_result: Optional[DemoRunResult] = None

    @staticmethod
    def generate_synthetic_transactions(
        scenario: DemoScenario,
        anchor_timestamp: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Generate a fully deterministic dataset representing baseline and incident traffic.

        Contains:
        1. Historical baseline: 100 transactions prior to incident window matching baseline_success_rate.
        2. Incident window: scenario.transaction_count transactions inside 15-minute window matching degraded_success_rate.
        """
        anchor = anchor_timestamp or DemoRunner.DEFAULT_ANCHOR

        # -------------------------------------------------------------
        # 1. Historical baseline period (60 minutes to 15 minutes before anchor)
        # -------------------------------------------------------------
        baseline_total = 100
        baseline_failures = int(round(baseline_total * (1.0 - scenario.baseline_success_rate)))

        baseline_txns: List[Dict[str, Any]] = []
        for i in range(baseline_total):
            ts = anchor - timedelta(minutes=60) + timedelta(seconds=i * 25)
            status = "FAILED" if i < baseline_failures else "SUCCESS"
            baseline_txns.append({
                "timestamp": ts,
                "payment_method": scenario.payment_method,
                "bank": scenario.bank,
                "device_type": scenario.device_type,
                "status": status,
                "amount": float(scenario.average_transaction_value),
            })

        # -------------------------------------------------------------
        # 2. Incident window (last 15 minutes up to anchor)
        # -------------------------------------------------------------
        incident_start = anchor - timedelta(minutes=15)
        incident_total = scenario.transaction_count
        incident_failures = int(round(incident_total * (1.0 - scenario.degraded_success_rate)))

        # Time step evenly distributed across 15-minute window
        step_seconds = max(1, int(900 / max(1, incident_total)))

        incident_txns: List[Dict[str, Any]] = []
        for i in range(incident_total):
            ts = incident_start + timedelta(seconds=i * step_seconds)
            status = "FAILED" if i < incident_failures else "SUCCESS"
            incident_txns.append({
                "timestamp": ts,
                "payment_method": scenario.payment_method,
                "bank": scenario.bank,
                "device_type": scenario.device_type,
                "status": status,
                "amount": float(scenario.average_transaction_value),
            })

        return pd.DataFrame(baseline_txns + incident_txns)

    def run(
        self,
        scenario: Optional[Any] = None,
        anchor_timestamp: Optional[datetime] = None,
    ) -> DemoRunResult:
        """
        Execute the full end-to-end recovery demonstration deterministically.
        """
        if isinstance(scenario, str):
            scenario = get_demo_scenario(scenario)
        scenario = scenario or CANONICAL_HAPPY_PATH
        anchor = anchor_timestamp or self.DEFAULT_ANCHOR
        events: List[LifecycleEvent] = []

        # -------------------------------------------------------------
        # STEP 1 / PHASE BASELINE: HEALTHY ROUTE BASELINE
        # -------------------------------------------------------------
        pre_learning_context = (
            self._learning_engine
            or (self._orchestrator.learning_engine if self._orchestrator else None)
        )
        pre_ranked = rank_routes(
            scenario.route_candidates,
            learning_history=pre_learning_context,
        )
        top_route_before = pre_ranked[0].route if pre_ranked else "NONE"
        route_score_before = pre_ranked[0].score if pre_ranked else 0.0

        events.append(
            LifecycleEvent(
                step_number=1,
                stage_id="HEALTHY",
                title="Healthy Baseline Route",
                status="SUCCESS",
                detail=(
                    f"Route {scenario.route} baseline success rate: "
                    f"{scenario.baseline_success_rate:.1%}"
                ),
                provenance="HistoricalBaseline",
                metrics={
                    "route": scenario.route,
                    "baseline_success_rate": scenario.baseline_success_rate,
                    "top_initial_alternate": top_route_before,
                    "initial_ranking": [r.route for r in pre_ranked],
                },
            )
        )

        # Generate deterministic synthetic transaction stream
        df = self.generate_synthetic_transactions(scenario, anchor_timestamp=anchor)

        # -------------------------------------------------------------
        # STEP 2 / PHASE INCIDENT: INCIDENT DETECTION
        # -------------------------------------------------------------
        intel = IncidentIntelligence(window_minutes=15)
        assessment = intel.assess(
            df,
            baseline_success_rate=scenario.baseline_success_rate,
        )

        detect_status = "SUCCESS" if assessment.incident_detected else "NORMAL"
        events.append(
            LifecycleEvent(
                step_number=2,
                stage_id="DETECT",
                title="Incident Detection",
                status=detect_status,
                detail=(
                    f"Severity: {assessment.severity} | "
                    f"Observed Success Rate: {assessment.current_success_rate:.1%} "
                    f"(Degradation: {assessment.degradation_pp:.1f} pp) | "
                    f"Observed: {assessment.transactions_observed} txns"
                ),
                provenance="IncidentIntelligence",
                metrics={
                    "severity": assessment.severity,
                    "observed_success_rate": assessment.current_success_rate,
                    "baseline_success_rate": assessment.baseline_success_rate,
                    "degradation_pp": assessment.degradation_pp,
                    "incident_detected": assessment.incident_detected,
                    "failures_observed": assessment.failures_observed,
                    "transactions_observed": assessment.transactions_observed,
                },
            )
        )

        # -------------------------------------------------------------
        # STEP 3: FINANCIAL IMPACT (Revenue at Risk)
        # -------------------------------------------------------------
        rev_calc = IncidentRevenueCalculator()
        incident_start = anchor - timedelta(minutes=15)
        incident_end = anchor
        revenue_impact = rev_calc.calculate(
            df,
            payment_method=scenario.payment_method,
            bank=scenario.bank,
            device_type=scenario.device_type,
            incident_start=incident_start,
            incident_end=incident_end,
        )

        events.append(
            LifecycleEvent(
                step_number=3,
                stage_id="QUANTIFY",
                title="Revenue at Risk Quantified",
                status="SUCCESS",
                detail=(
                    f"Revenue at Risk: ₹{revenue_impact.revenue_at_risk:,.2f} [THEORETICAL] "
                    f"across {revenue_impact.excess_failures:.0f} excess failures "
                    f"(Total actual failed amount: ₹{revenue_impact.actual_failed_amount:,.2f})"
                ),
                provenance="IncidentRevenueCalculator",
                metrics={
                    "revenue_at_risk": revenue_impact.revenue_at_risk,
                    "excess_failures": revenue_impact.excess_failures,
                    "actual_failed_amount": revenue_impact.actual_failed_amount,
                },
            )
        )

        # -------------------------------------------------------------
        # STEP 4 / PHASE DECISION: AI DECISION ENGINE
        # -------------------------------------------------------------
        decision_engine_before = IncidentDecisionEngine(learning_history=pre_learning_context)
        decision_result = decision_engine_before.evaluate(
            incident_route=scenario.route,
            transactions_affected=assessment.transactions_observed,
            failures_observed=assessment.failures_observed,
            baseline_success_rate=assessment.baseline_success_rate,
            current_success_rate=assessment.current_success_rate,
            severity=assessment.severity,
            average_transaction_value=scenario.average_transaction_value,
            route_candidates=scenario.route_candidates,
            revenue_impact=revenue_impact,
        )
        decision = decision_result.decision

        events.append(
            LifecycleEvent(
                step_number=4,
                stage_id="DECIDE",
                title="AI Intervention Optimization",
                status="SUCCESS",
                detail=(
                    f"Selected Action: {decision.recommended_action} | "
                    f"Confidence: {decision.confidence:.1%} | "
                    f"Expected Loss: ₹{decision.expected_loss_before:,.2f} → "
                    f"₹{decision.expected_loss_after:,.2f} "
                    f"(Net Loss Reduction: ₹{decision.estimated_value:,.2f})"
                ),
                provenance="IncidentDecisionEngine",
                metrics={
                    "recommended_action": decision.recommended_action,
                    "confidence": decision.confidence,
                    "expected_loss_before": decision.expected_loss_before,
                    "expected_loss_after": decision.expected_loss_after,
                    "estimated_loss_reduction": decision.estimated_value,
                },
            )
        )

        # -------------------------------------------------------------
        # STEP 5 / PHASE SAFETY: SAFETY GATE (SafetyController)
        # -------------------------------------------------------------
        safety_controller = SafetyController()
        safety_decision = safety_controller.evaluate(decision)

        safety_status = "SUCCESS" if safety_decision.allowed else "BLOCKED"
        events.append(
            LifecycleEvent(
                step_number=5,
                stage_id="SAFETY",
                title="Deterministic Safety Gate",
                status=safety_status,
                detail=(
                    f"Decision: {'ALLOWED' if safety_decision.allowed else 'BLOCKED'} | "
                    f"Human Review Required: {'YES' if safety_decision.requires_human_review else 'NO'} | "
                    f"Policy: {safety_decision.reason}"
                ),
                provenance="SafetyController",
                metrics={
                    "allowed": safety_decision.allowed,
                    "requires_human_review": safety_decision.requires_human_review,
                    "reason": safety_decision.reason,
                    "action": safety_decision.action,
                },
            )
        )

        # -------------------------------------------------------------
        # STEP 6 / PHASE CANARY: BOUNDED CANARY RECOVERY
        # -------------------------------------------------------------
        # Extract alternative bank for orchestrated recovery
        target_bank = "Bank_A"
        if decision.recommended_action.startswith("ROUTE_SWITCH:"):
            parts = decision.recommended_action.replace("ROUTE_SWITCH:", "").split("+")
            if len(parts) >= 2:
                target_bank = parts[1].strip()

        recovery_payload = {
            "simulated_success_rate": scenario.simulated_recovery_rate,
            "alternative_bank": target_bank,
        }

        batch_result = execute_orchestrated_batch_recovery(
            transactions=df,
            incident={
                "severity": assessment.severity,
                "baseline_success_rate": assessment.baseline_success_rate,
                "transactions": assessment.transactions_observed,
                "time_window": scenario.route,
            },
            decision=decision,
            safety=safety_decision,
            recovery=recovery_payload,
            payment_method=scenario.payment_method,
            affected_bank=scenario.bank,
            device_type=scenario.device_type,
            batch_size=scenario.canary_batch_size,
            human_approved=False,
            orchestrator=self._orchestrator,
        )

        canary_dec = batch_result.get("canary_decision", "NOT_APPLICABLE")
        if not safety_decision.allowed:
            recover_status = "BLOCKED"
            recover_detail = f"Execution safely prevented by Safety Controller: {safety_decision.reason}"
        elif canary_dec == "EXPAND":
            recover_status = "SUCCESS"
            recover_detail = (
                f"Canary execution succeeded: {batch_result['successful_recoveries']}/"
                f"{batch_result['attempted_transactions']} recovered "
                f"({batch_result['recovery_rate']:.1%}). Canary Decision: EXPAND."
            )
        elif canary_dec == "STOP":
            recover_status = "STOPPED"
            recover_detail = f"Canary execution halted: {batch_result.get('canary_reason', '')}"
        elif canary_dec == "ESCALATE":
            recover_status = "ESCALATED"
            recover_detail = f"Canary execution escalated: {batch_result.get('canary_reason', '')}"
        else:
            recover_status = "MONITORING"
            recover_detail = f"Action: {batch_result.get('final_status', 'MONITORING')}"

        events.append(
            LifecycleEvent(
                step_number=6,
                stage_id="RECOVER",
                title="Bounded Canary Recovery",
                status=recover_status,
                detail=recover_detail,
                provenance="RecoveryOrchestrator",
                metrics={
                    "eligible_transactions": batch_result.get("eligible_transactions", 0),
                    "attempted_transactions": batch_result["attempted_transactions"],
                    "successful_recoveries": batch_result["successful_recoveries"],
                    "failed_recoveries": batch_result["failed_recoveries"],
                    "canary_decision": canary_dec,
                    "canary_recovery_rate": batch_result.get("canary_recovery_rate", 0.0),
                },
            )
        )

        # -------------------------------------------------------------
        # STEP 7 / PHASE RECOVERY: FINANCIAL OUTCOME VERIFICATION
        # -------------------------------------------------------------
        final_status = batch_result.get("final_status", "UNKNOWN")
        net_recovered = batch_result.get("net_recovered_value", 0.0)
        recovered_amount = batch_result.get("recovered_amount", 0.0)
        cost = batch_result.get("execution_cost", 0.0)
        roi = round(recovered_amount / max(1.0, cost), 2) if cost > 0 else 0.0
        guardrail_dec = batch_result.get("guardrail_decision", "NOT_APPLICABLE")

        if not safety_decision.allowed:
            verify_status = "BLOCKED"
            verify_detail = "No financial recovery attempted due to safety gate."
        elif batch_result.get("rollback_required", False):
            verify_status = "ROLLED_BACK"
            verify_detail = (
                f"Status: {final_status} | Net Value: ₹{net_recovered:,.2f} [SIMULATED] | "
                f"Execution Cost: ₹{cost:,.2f} [SIMULATED] | Guardrail: ROLLBACK (Circuit breaker triggered)"
            )
        elif final_status == "RECOVERED":
            verify_status = "SUCCESS"
            verify_detail = (
                f"Verified Recovered Amount: ₹{recovered_amount:,.2f} [SIMULATED] | "
                f"Net Recovered Value: ₹{net_recovered:,.2f} [SIMULATED] | "
                f"ROI: {roi:.2f}x [SIMULATED] | Guardrail: {guardrail_dec}"
            )
        else:
            verify_status = final_status
            verify_detail = (
                f"Status: {final_status} | Recovered: ₹{recovered_amount:,.2f} [SIMULATED] | "
                f"Net: ₹{net_recovered:,.2f} [SIMULATED] | Guardrail: {guardrail_dec}"
            )

        events.append(
            LifecycleEvent(
                step_number=7,
                stage_id="VERIFY",
                title="Financial Outcome Verification",
                status=verify_status,
                detail=verify_detail,
                provenance="RecoveryOutcomeVerifier",
                metrics={
                    "final_status": final_status,
                    "attempted_amount": batch_result.get("attempted_amount", 0.0),
                    "recovered_amount": recovered_amount,
                    "execution_cost": cost,
                    "net_recovered_value": net_recovered,
                    "recovery_rate": batch_result.get("recovery_rate", 0.0),
                    "recovery_roi": roi,
                    "rollback_required": batch_result.get("rollback_required", False),
                    "guardrail_decision": guardrail_dec,
                },
            )
        )

        # -------------------------------------------------------------
        # STEP 8 / PHASE LEARNING: ROUTE LEARNING EVIDENCE
        # -------------------------------------------------------------
        learning_stats: Optional[RouteLearningStats] = batch_result.get("learning_stats")

        if learning_stats is not None:
            learn_status = "SUCCESS"
            learn_detail = (
                f"Route: {learning_stats.route} | "
                f"Cumulative Recoveries: {learning_stats.recoveries}/{learning_stats.attempts} "
                f"({learning_stats.recovery_rate:.1%}) | "
                f"Evidence Confidence: {learning_stats.evidence_confidence:.1%}"
            )
            learn_metrics = {
                "route": learning_stats.route,
                "attempts": learning_stats.attempts,
                "recoveries": learning_stats.recoveries,
                "recovery_rate": learning_stats.recovery_rate,
                "evidence_confidence": learning_stats.evidence_confidence,
            }
        else:
            learn_status = "SKIPPED"
            learn_detail = "No learning evidence recorded (execution blocked or not applicable)."
            learn_metrics = {}

        events.append(
            LifecycleEvent(
                step_number=8,
                stage_id="LEARN",
                title="Continuous Route Learning",
                status=learn_status,
                detail=learn_detail,
                provenance="RecoveryLearningEngine",
                metrics=learn_metrics,
            )
        )

        # -------------------------------------------------------------
        # STEP 9 / PHASE REEVALUATION: NEXT DECISION / ADAPTED ROUTE RANKING
        # -------------------------------------------------------------
        # Pass the newly learned evidence to route scoring and decision engine
        post_learning_context = (
            self._learning_engine
            or (self._orchestrator.learning_engine if self._orchestrator else None)
            or ({learning_stats.route: learning_stats} if learning_stats else None)
        )

        post_ranked = rank_routes(
            scenario.route_candidates,
            learning_history=post_learning_context,
        )
        top_route_after = post_ranked[0].route if post_ranked else "NONE"
        route_score_after = post_ranked[0].score if post_ranked else 0.0
        score_delta = round(route_score_after - route_score_before, 4)
        ranking_changed = top_route_after != top_route_before

        # Re-evaluate the same decision problem with learned history
        decision_engine_after = IncidentDecisionEngine(learning_history=post_learning_context)
        decision_result_after = decision_engine_after.evaluate(
            incident_route=scenario.route,
            transactions_affected=assessment.transactions_observed,
            failures_observed=assessment.failures_observed,
            baseline_success_rate=assessment.baseline_success_rate,
            current_success_rate=assessment.current_success_rate,
            severity=assessment.severity,
            average_transaction_value=scenario.average_transaction_value,
            route_candidates=scenario.route_candidates,
            revenue_impact=revenue_impact,
        )
        decision_after = decision_result_after.decision
        decision_changed_after_learning = (
            decision.recommended_action != decision_after.recommended_action
        )

        reevaluation_result = {
            "before_learning": {
                "selected_action": decision.recommended_action,
                "top_route": top_route_before,
                "route_score": route_score_before,
                "ranking": [r.route for r in pre_ranked],
            },
            "after_learning": {
                "selected_action": decision_after.recommended_action,
                "top_route": top_route_after,
                "route_score": route_score_after,
                "ranking": [r.route for r in post_ranked],
            },
            "decision_changed_after_learning": decision_changed_after_learning,
            "ranking_changed": ranking_changed,
            "score_delta": score_delta,
        }

        if ranking_changed or decision_changed_after_learning:
            adapt_detail = (
                f"Ranking adapted: {top_route_before} → {top_route_after} "
                f"(Score Lift: {score_delta:+.4f})"
            )
        elif score_delta != 0.0:
            adapt_detail = (
                f"Learning evidence recorded; score lift: {score_delta:+.4f} "
                f"(Top route: {top_route_after})"
            )
        else:
            adapt_detail = "Learning evidence recorded; ranking unchanged."

        events.append(
            LifecycleEvent(
                step_number=9,
                stage_id="ADAPT",
                title="Next Route Intelligence",
                status="SUCCESS",
                detail=adapt_detail,
                provenance="RouteScorer",
                metrics={
                    "top_route_before": top_route_before,
                    "top_route_after": top_route_after,
                    "route_score_before": route_score_before,
                    "route_score_after": route_score_after,
                    "score_delta": score_delta,
                    "ranking_changed": ranking_changed,
                    "decision_changed_after_learning": decision_changed_after_learning,
                },
            )
        )

        # -------------------------------------------------------------
        # EVALUATION SCORECARD & FINANCIAL SUMMARY
        # -------------------------------------------------------------
        scorecard = build_system_evaluation_scorecard(
            incident=assessment,
            decision=decision,
            safety_decision=safety_decision,
            orchestration_result=batch_result,
            learning_context=learning_stats,
            route_score_before=pre_ranked[0] if pre_ranked else None,
            route_score_after=post_ranked[0] if post_ranked else None,
            revenue_impact=revenue_impact,
        )
        scorecard_view = prepare_dashboard_evaluation_scorecard(scorecard)

        fin_summary = calculate_financial_summary(
            revenue_at_risk=revenue_impact.revenue_at_risk,
            eligible_amount=batch_result.get("eligible_amount", 0.0),
            batch_result=batch_result,
        )

        # Audit references
        audit_refs: List[Dict[str, Any]] = []
        if batch_result.get("audit_result"):
            audit_refs.append(batch_result["audit_result"])
        try:
            audit_df = load_audit_log()
            if audit_df is not None and not audit_df.empty:
                latest_records = audit_df.tail(3).to_dict(orient="records")
                audit_refs.extend(latest_records)
        except Exception:
            pass

        # Determine overall success state
        is_success = (
            not scenario.is_failure_scenario
            and safety_decision.allowed
            and final_status == "RECOVERED"
            and not batch_result.get("rollback_required", False)
        )

        if not safety_decision.allowed:
            summary_msg = f"Safety Gate Protected: {safety_decision.reason}"
        elif batch_result.get("rollback_required", False):
            summary_msg = f"Guardrail Circuit Breaker: Rollback triggered ({batch_result.get('guardrail_reason', '')})"
        elif is_success:
            summary_msg = (
                f"Autonomous Recovery Succeeded: Net Recovered ₹{net_recovered:,.2f} [SIMULATED] "
                f"({batch_result['successful_recoveries']}/{batch_result['attempted_transactions']} txns, ROI {roi:.2f}x)"
            )
        else:
            summary_msg = f"Demo Run Completed with status: {final_status}"

        # -------------------------------------------------------------
        # PHASE RESULTS MODEL
        # -------------------------------------------------------------
        phase_results: Dict[str, PhaseResult] = {
            DemoPhase.BASELINE.value: PhaseResult(
                phase=DemoPhase.BASELINE,
                title="Healthy Baseline Route",
                status="SUCCESS",
                detail=f"Route {scenario.route} baseline success rate: {scenario.baseline_success_rate:.1%}",
                provenance="HistoricalBaseline",
                metrics={
                    "primary_route": scenario.route,
                    "baseline_success_rate": scenario.baseline_success_rate,
                    "transaction_count": scenario.transaction_count,
                    "alternate_routes": [c["route"] for c in scenario.route_candidates],
                    "initial_ranking": [r.route for r in pre_ranked],
                },
            ),
            DemoPhase.INCIDENT.value: PhaseResult(
                phase=DemoPhase.INCIDENT,
                title="Incident Detection",
                status="SUCCESS" if assessment.incident_detected else "NORMAL",
                detail=(
                    f"Severity: {assessment.severity} | Observed: {assessment.current_success_rate:.1%} | "
                    f"Degradation: {assessment.degradation_pp:.1f} pp | Transactions: {assessment.transactions_observed}"
                ),
                provenance="IncidentIntelligence",
                metrics={
                    "severity": assessment.severity,
                    "observed_success_rate": assessment.current_success_rate,
                    "baseline_success_rate": assessment.baseline_success_rate,
                    "degradation_pp": assessment.degradation_pp,
                    "transactions_observed": assessment.transactions_observed,
                    "incident_detected": assessment.incident_detected,
                },
            ),
            DemoPhase.DECISION.value: PhaseResult(
                phase=DemoPhase.DECISION,
                title="AI Intervention Optimization",
                status="SUCCESS",
                detail=f"Selected: {decision.recommended_action} | Confidence: {decision.confidence:.1%}",
                provenance="IncidentDecisionEngine",
                metrics={
                    "recommended_action": decision.recommended_action,
                    "confidence": decision.confidence,
                    "expected_loss_before": decision.expected_loss_before,
                    "expected_loss_after": decision.expected_loss_after,
                    "estimated_loss_reduction": decision.estimated_value,
                },
            ),
            DemoPhase.SAFETY.value: PhaseResult(
                phase=DemoPhase.SAFETY,
                title="Deterministic Safety Gate",
                status="SUCCESS" if safety_decision.allowed else "BLOCKED",
                detail=f"Allowed: {safety_decision.allowed} | Reason: {safety_decision.reason}",
                provenance="SafetyController",
                metrics={
                    "allowed": safety_decision.allowed,
                    "requires_human_review": safety_decision.requires_human_review,
                    "reason": safety_decision.reason,
                    "action": safety_decision.action,
                },
            ),
            DemoPhase.CANARY.value: PhaseResult(
                phase=DemoPhase.CANARY,
                title="Bounded Canary Execution",
                status=recover_status,
                detail=recover_detail,
                provenance="RecoveryOrchestrator",
                metrics={
                    "eligible_transactions": batch_result.get("eligible_transactions", 0),
                    "attempted_transactions": batch_result.get("attempted_transactions", 0),
                    "successful_recoveries": batch_result.get("successful_recoveries", 0),
                    "failed_recoveries": batch_result.get("failed_recoveries", 0),
                    "canary_decision": canary_dec,
                    "canary_recovery_rate": batch_result.get("canary_recovery_rate", 0.0),
                },
            ),
            DemoPhase.RECOVERY.value: PhaseResult(
                phase=DemoPhase.RECOVERY,
                title="Recovery Outcome Verification",
                status=verify_status,
                detail=verify_detail,
                provenance="RecoveryOutcomeVerifier",
                metrics={
                    "attempted_amount": fin_summary.attempted_amount,
                    "recovered_amount": fin_summary.recovered_amount,
                    "execution_cost": fin_summary.execution_cost,
                    "net_recovered_value": fin_summary.net_recovered_value,
                    "recovery_rate": fin_summary.recovery_rate,
                    "recovery_roi": fin_summary.recovery_roi,
                    "final_status": final_status,
                    "rollback_required": batch_result.get("rollback_required", False),
                },
            ),
            DemoPhase.LEARNING.value: PhaseResult(
                phase=DemoPhase.LEARNING,
                title="Continuous Route Learning",
                status=learn_status,
                detail=learn_detail,
                provenance="RecoveryLearningEngine",
                metrics=learn_metrics,
            ),
            DemoPhase.REEVALUATION.value: PhaseResult(
                phase=DemoPhase.REEVALUATION,
                title="Next Route Intelligence Re-evaluation",
                status="SUCCESS",
                detail=adapt_detail,
                provenance="RouteScorer",
                metrics=reevaluation_result,
            ),
            DemoPhase.COMPLETE.value: PhaseResult(
                phase=DemoPhase.COMPLETE,
                title="Demo Lifecycle Completed",
                status="SUCCESS" if is_success else ("BLOCKED" if not safety_decision.allowed else "HALTED"),
                detail=summary_msg,
                provenance="DemoRunner",
                metrics={"final_status": final_status, "is_success": is_success},
            ),
        }

        result = DemoRunResult(
            scenario=scenario,
            incident=assessment,
            revenue_impact=revenue_impact,
            decision_result=decision_result,
            decision=decision,
            safety_decision=safety_decision,
            batch_result=batch_result,
            orchestration_result=None,
            financial_summary=fin_summary.__dict__ if hasattr(fin_summary, "__dict__") else {},
            scorecard=scorecard,
            scorecard_view=scorecard_view,
            route_score_before=route_score_before,
            route_score_after=route_score_after,
            score_delta=score_delta,
            top_route_before=top_route_before,
            top_route_after=top_route_after,
            ranking_changed=ranking_changed,
            learning_evidence=learning_stats,
            lifecycle_events=events,
            is_success=is_success,
            final_status=final_status,
            summary_message=summary_msg,
            execution_timestamp=anchor.isoformat(),
            phase_results=phase_results,
            reevaluation_result=reevaluation_result,
            decision_changed_after_learning=decision_changed_after_learning,
            audit_references=audit_refs,
        )

        self._last_result = result
        return result

    def reset(self) -> None:
        """
        Reset demo runner state.

        Clears in-memory demo run result.
        Does NOT delete persistent learning CSV.
        """
        self._last_result = None

    @property
    def last_result(self) -> Optional[DemoRunResult]:
        """Retrieve the result of the most recent demo execution."""
        return self._last_result
