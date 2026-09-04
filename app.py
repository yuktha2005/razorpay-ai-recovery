import json
import textwrap
import streamlit as st
import pandas as pd
from typing import Optional
import sys
from pathlib import Path


# =========================================
# PATH CONFIGURATION
# =========================================

BASE_DIR = Path(__file__).resolve().parent

SRC_DIR = BASE_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from src.decision.incident_decision_engine import (
    IncidentDecisionEngine
)

from src.decision.decision_explanation import (
    DecisionExplanation,
    build_decision_explanation,
)

from src.models.domain import (
    LossEstimate,
    RiskAssessment,
)

from src.recovery.recovery_orchestrator import (
    RecoveryOrchestrator
)

from src.recovery.orchestrated_batch import (
    execute_orchestrated_batch_recovery
)

from src.recovery.recovery_audit_adapter import (
    record_recovery_outcome
)

from src.intelligence.incident_revenue import (
    IncidentRevenueImpact
)

from src.live_reporting.report_store import (
    LiveReportStore
)

from src.live_reporting.report_generator import (
    LiveReportGenerator
)

from src.tracking.learning_history import (
    PersistentLearningHistory
)

from src.tracking.financial_summary import (
    calculate_financial_summary,
    FinancialSummary,
)

from src.evaluation.evaluation_adapter import (
    prepare_dashboard_evaluation_scorecard,
)

from src.demo import (
    DemoRunner,
    DemoRunResult,
    DemoScenario,
    CANONICAL_HAPPY_PATH,
    DEFAULT_DEMO_CANDIDATES,
    FAILURE_SAFETY_BLOCKED,
    FAILURE_UNPROFITABLE_ROLLBACK,
    get_demo_scenario,
    list_demo_scenarios,
    build_demo_view_model,
    get_financial_display,
    get_learning_display,
    get_reevaluation_display,
    get_closed_loop_learning_flow,
    get_final_status_bar,
    get_phase_css_class,
    get_phase_icon,
    PROVENANCE_OBSERVED,
    PROVENANCE_THEORETICAL,
    PROVENANCE_SIMULATED,
    PROVENANCE_GOVERNED,
    PROVENANCE_LEARNED,
)

from src.tracking.learning_view import (
    LearningComparisonView,
    build_learning_comparison,
)
# =========================================
# BACKEND IMPORTS
# =========================================

from agent import (
    load_data,
    detect_incident,
    analyze_root_cause,
    calculate_revenue_impact,
    recommend_recovery
)

from ai_diagnosis import (
    diagnose_incident
)

from recovery_simulator import (
    simulate_recovery
)

from policy_engine import (
    evaluate_recovery_policy,
    evaluate_recovery_guardrail
)

from batch_recovery import (
    execute_batch_recovery,
    run_batch_recovery
)

from audit_logger import (
    load_audit_log
)

from scenario_engine import (
    list_scenarios,
    get_scenario,
    scenario_summary,
    evaluate_scenario_control
)

from src.live_reporting.event_simulator import (
    LivePaymentSimulator,
)


# =========================================
# PAGE CONFIGURATION
# =========================================

st.set_page_config(
    page_title="RouteIQ — Intelligent Payment Route Recovery",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================
# CENTRALIZED FINTECH CSS
# =========================================

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #1e293b;
    background-color: #f8fafc;
}

.block-container {
    max-width: 1320px;
    padding-top: 1.25rem;
    padding-bottom: 3rem;
}

/* Header & Status */
.header-bar {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 1.1rem;
    margin-bottom: 1.25rem;
}

.product-title {
    font-size: 1.85rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.02em;
    margin: 0;
    line-height: 1.2;
}

.product-subtitle {
    font-size: 0.92rem;
    color: #64748b;
    margin-top: 0.3rem;
    font-weight: 400;
}

.badge-sim {
    background-color: #f0f9ff;
    color: #0284c7;
    border: 1px solid #bae6fd;
    padding: 3px 9px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}

.badge-status {
    background-color: #ecfdf5;
    color: #059669;
    border: 1px solid #a7f3d0;
    padding: 3px 9px;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}

/* Section Titles */
.section-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.01em;
    margin-top: 1.6rem;
    margin-bottom: 0.85rem;
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid #f1f5f9;
    padding-bottom: 6px;
}

/* Fintech Cards */
.fintech-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1.25rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04);
}

.incident-card {
    background: #ffffff;
    border: 1px solid #fed7aa;
    border-left: 4px solid #f97316;
    border-radius: 10px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04);
}

.incident-card-critical {
    background: #ffffff;
    border: 1px solid #fecaca;
    border-left: 4px solid #ef4444;
    border-radius: 10px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04);
}

.decision-card {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-left: 4px solid #0284c7;
    border-radius: 10px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04);
}

.safety-card-safe {
    background: #ffffff;
    border: 1px solid #a7f3d0;
    border-left: 4px solid #10b981;
    border-radius: 10px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1rem;
}

.safety-card-review {
    background: #ffffff;
    border: 1px solid #fde68a;
    border-left: 4px solid #f59e0b;
    border-radius: 10px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1rem;
}

.safety-card-stop {
    background: #ffffff;
    border: 1px solid #fecaca;
    border-left: 4px solid #ef4444;
    border-radius: 10px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1rem;
}

.ai-card {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-left: 4px solid #0284c7;
    border-radius: 10px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04);
}

.ai-source {
    font-size: 0.75rem;
    font-weight: 700;
    color: #0284c7;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 6px;
}

.explanation-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    font-size: 0.85rem;
    color: #334155;
    margin: 0.75rem 0;
    line-height: 1.5;
}

.recovery-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04);
}

.policy-recover {
    background: #ffffff;
    border: 1px solid #a7f3d0;
    border-left: 4px solid #10b981;
    border-radius: 10px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1rem;
}

.policy-escalate {
    background: #ffffff;
    border: 1px solid #fde68a;
    border-left: 4px solid #f59e0b;
    border-radius: 10px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1rem;
}

.policy-stop {
    background: #ffffff;
    border: 1px solid #fecaca;
    border-left: 4px solid #ef4444;
    border-radius: 10px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1rem;
}

/* Status Pills */
.pill-green {
    background: #ecfdf5;
    color: #065f46;
    border: 1px solid #a7f3d0;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    display: inline-block;
}

.pill-amber {
    background: #fffbeb;
    color: #92400e;
    border: 1px solid #fde68a;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    display: inline-block;
}

.pill-red {
    background: #fef2f2;
    color: #991b1b;
    border: 1px solid #fecaca;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    display: inline-block;
}

.pill-blue {
    background: #f0f9ff;
    color: #0369a1;
    border: 1px solid #bae6fd;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    display: inline-block;
}

/* Horizontal Lifecycle */
.lifecycle-wrapper {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin: 1rem 0;
}

.lifecycle-node {
    flex: 1;
    text-align: center;
    padding: 8px 10px;
    border-radius: 8px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
}

.lifecycle-node-label {
    font-size: 0.7rem;
    color: #64748b;
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.03em;
    margin-bottom: 4px;
}

.lifecycle-arrow {
    color: #94a3b8;
    font-size: 1.1rem;
    font-weight: bold;
}

/* Vertical Timeline */
.timeline-track {
    border-left: 2px solid #e2e8f0;
    margin-left: 14px;
    padding-left: 18px;
    position: relative;
    margin-top: 1rem;
    margin-bottom: 1.25rem;
}

.timeline-step {
    position: relative;
    padding-bottom: 16px;
}

.timeline-step:last-child {
    padding-bottom: 0;
}

.timeline-marker {
    position: absolute;
    left: -25px;
    top: 3px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #0284c7;
    border: 2px solid #ffffff;
    box-shadow: 0 0 0 2px #bae6fd;
}

.timeline-marker-success {
    background: #10b981;
    box-shadow: 0 0 0 2px #a7f3d0;
}

.timeline-marker-warn {
    background: #f59e0b;
    box-shadow: 0 0 0 2px #fde68a;
}

/* Footer */
.footer-text {
    color: #94a3b8;
    font-size: 0.8rem;
    text-align: center;
    margin-top: 2rem;
    padding-top: 1.5rem;
    border-top: 1px solid #e2e8f0;
}

/* Demo Banner & Lifecycle */
.demo-card {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 2px 4px rgba(15, 23, 42, 0.05);
}

.lifecycle-flow {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin: 0.75rem 0 1rem 0;
    padding: 10px 14px;
    background: #0f172a;
    border-radius: 8px;
    border: 1px solid #334155;
}

.lifecycle-step {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 9px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.02em;
}

.step-success {
    background: #064e3b;
    color: #34d399;
    border: 1px solid #059669;
}

.step-blocked {
    background: #7f1d1d;
    color: #f87171;
    border: 1px solid #dc2626;
}

.step-warn {
    background: #78350f;
    color: #fbbf24;
    border: 1px solid #d97706;
}

.step-pending {
    background: #1e293b;
    color: #64748b;
    border: 1px solid #334155;
}

.lifecycle-sep {
    color: #475569;
    font-weight: 700;
    font-size: 0.8rem;
}
</style>
""",
    unsafe_allow_html=True,
)


def render_html(html_str: str) -> None:
    """Render raw HTML safely without Markdown indentation or code-block artifacts."""
    clean = "\n".join(line.lstrip() for line in html_str.splitlines()).strip()
    st.markdown(clean, unsafe_allow_html=True)


# =========================================
# SIDEBAR
# =========================================

with st.sidebar:
    render_html(
        """
        <div style="font-size: 1.45rem; font-weight: 800; color: #0f172a; line-height: 1.15; margin-bottom: 2px;">
            Route<span style="color: #0284c7;">IQ</span>
        </div>
        <div style="font-size: 0.8rem; color: #64748b; margin-bottom: 12px;">Payment Reliability & Recovery Engine</div>
        """
    )

    st.markdown("**Demo Scenario**")
    scenario_name = st.selectbox(
        "Select scenario",
        list_scenarios(),
        index=0,
        label_visibility="collapsed",
        help="Counterfactual validation scenarios without live payment execution.",
    )

    if st.session_state.get("current_scenario") != scenario_name:
        st.session_state["current_scenario"] = scenario_name
        st.session_state["batch_result"] = None
        st.session_state["evaluation_scorecard"] = None
        st.session_state["demo_run_result"] = None

    selected_scenario = get_scenario(scenario_name)
    scenario_view = scenario_summary(scenario_name)
    scenario_control = evaluate_scenario_control(scenario_name)

    st.caption(f"{scenario_view['description']}")

    st.markdown("---")

    st.markdown(
        """
        **Navigation**
        - [• End-to-End Demo](#end-to-end-recovery-demo)
        - [• System Overview](#system-overview)
        - [• Decision Intelligence](#ai-decision-intelligence)
        - [• Safety Control](#safety-control)
        - [• Recovery Control](#recovery-control)
        - [• Continuous Learning](#recovery-learning)
        - [• System Evaluation](#system-evaluation)
        - [• Audit Trail](#recovery-audit-trail)
        """
    )

    st.markdown("---")

    render_html(
        """
        <div style="background: #f1f5f9; padding: 10px 12px; border-radius: 8px; font-size: 0.8rem;">
            <div style="color: #0284c7; font-weight: 700;">⚙ SIMULATION MODE</div>
            <div style="color: #334155; margin-top: 4px;">Environment: <b>Demo</b></div>
            <div style="color: #334155;">Safety: <b>Enforced</b></div>
            <div style="color: #64748b; font-size: 0.72rem; margin-top: 4px;">No live routing performed</div>
        </div>
        """
    )


# =========================================
# HEADER
# =========================================

render_html(
    """
    <div class="header-bar">
        <div>
            <div class="product-title">ROUTEIQ — PAYMENT RELIABILITY CENTER</div>
            <div class="product-subtitle">Detect revenue risk · Decide safely · Recover within bounds · Learn continuously</div>
        </div>
        <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
            <span class="badge-sim">⚙ SIMULATION MODE</span>
            <span class="badge-status">⚙ System Operational</span>
        </div>
    </div>
    """
)


# =========================================
# LOAD DATA
# =========================================

try:

    transactions = load_data()

except Exception as e:

    st.error(
        f"Unable to load transaction data: {e}"
    )

    st.stop()


# =========================================
# PAYMENT HEALTH
# =========================================

overall_success = (
    transactions["status"] == "SUCCESS"
).mean()

total_transactions = len(
    transactions
)

failed_transactions = (
    transactions["status"] == "FAILED"
).sum()

failed_amount = transactions.loc[
    transactions["status"] == "FAILED",
    "amount"
].sum()


# Load live report & audit data for overview metrics
try:
    live_store = LiveReportStore()
    latest_path = live_store.latest()
    if latest_path and latest_path.exists():
        with open(latest_path, "r", encoding="utf-8") as f:
            live_report = json.load(f)
    else:
        rep_gen = LiveReportGenerator()
        live_report_obj = rep_gen.generate(transactions)
        saved_path = live_store.save(live_report_obj)
        with open(saved_path, "r", encoding="utf-8") as f:
            live_report = json.load(f)
except Exception:
    live_report = {}

audit_log = load_audit_log()
total_net_recovered = 0.0
if audit_log is not None and not audit_log.empty:
    if "net_recovered_value" in audit_log.columns:
        valid_net = pd.to_numeric(
            audit_log["net_recovered_value"], errors="coerce"
        ).dropna()
        if not valid_net.empty:
            total_net_recovered = float(valid_net.sum())

incident = detect_incident(transactions)
impact = calculate_revenue_impact(transactions, incident) if incident is not None else None


# =========================================
# END-TO-END RECOVERY DEMO (JUDGE-READY)
# =========================================

st.markdown('<div id="end-to-end-recovery-demo"></div>', unsafe_allow_html=True)
render_html(
    """
    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.2rem;">
        <div class="section-title" style="margin-bottom: 0; font-size: 1.35rem; font-weight: 800;">🚀 END-TO-END RECOVERY DEMO</div>
        <span class="badge-sim">Deterministic Judge Flow</span>
    </div>
    <div style="font-size: 0.86rem; font-weight: 600; color: #475569; margin-bottom: 0.85rem; letter-spacing: 0.02em;">
        Detect → Quantify → Decide → Safety-gate → Recover → Verify → Learn → Adapt
    </div>
    """
)

with st.container():
    demo_ctrl_col1, demo_ctrl_col2, demo_ctrl_col3 = st.columns([2.5, 1.2, 1.0])

    with demo_ctrl_col1:
        demo_scenario_options = {
            "canonical_happy_path": "Canonical: Degradation → AI Decision → Canary Verified → Learning",
            "safety_blocked": "Safety Blocked: Critical Exposure (> ₹500k Policy Threshold)",
            "unprofitable_rollback": "Circuit Breaker: Unprofitable Recovery → Auto Rollback",
        }
        selected_demo_id = st.selectbox(
            "Demo Scenario Selector",
            options=list(demo_scenario_options.keys()),
            format_func=lambda sid: demo_scenario_options[sid],
            key="demo_scenario_selector",
            label_visibility="collapsed",
        )

    with demo_ctrl_col2:
        run_demo_clicked = st.button(
            "▶ Run End-to-End Demo",
            type="primary",
            use_container_width=True,
            help="Run the deterministic demo using the existing domain pipeline.",
        )

    with demo_ctrl_col3:
        reset_demo_clicked = st.button(
            "↻ Reset Demo",
            use_container_width=True,
            help="Clear demo outputs. Does not delete historical persistent learning.",
        )

    if reset_demo_clicked:
        st.session_state["demo_run_result"] = None
        st.session_state["batch_result"] = None
        st.session_state["evaluation_scorecard"] = None
        st.session_state["evaluation_scorecard_view"] = None
        st.session_state["demo_reset_flag"] = True
        st.rerun()

    if (
        run_demo_clicked
        or (st.session_state.get("active_demo_scenario") != selected_demo_id)
        or (st.session_state.get("demo_run_result") is None and not st.session_state.get("demo_reset_flag", False))
    ):
        st.session_state["active_demo_scenario"] = selected_demo_id
        st.session_state["demo_reset_flag"] = False
        scenario_obj = get_demo_scenario(selected_demo_id)
        runner = DemoRunner()
        demo_res = runner.run(scenario_obj)

        st.session_state["demo_run_result"] = demo_res
        st.session_state["batch_result"] = demo_res.batch_result
        st.session_state["evaluation_scorecard"] = demo_res.scorecard
        st.session_state["evaluation_scorecard_view"] = demo_res.scorecard_view

    demo_result: Optional[DemoRunResult] = st.session_state.get("demo_run_result")

    # 1. Lifecycle Bar (Rendered in all states for immediate judge orientation)
    if demo_result is not None:
        safe_allowed = demo_result.safety_decision.allowed if demo_result.safety_decision else False
        succ_rec = demo_result.batch_result.get("successful_recoveries", 0) if demo_result.batch_result else 0
        final_st = demo_result.final_status
        has_learn = demo_result.learning_evidence is not None
        has_lift = demo_result.score_delta > 0 or demo_result.ranking_changed

        recover_step_cls = "step-success" if succ_rec > 0 else ("step-blocked" if not safe_allowed else "step-warn")
        recover_step_icon = "✓" if succ_rec > 0 else ("🚫" if not safe_allowed else "⚠️")

        verify_step_cls = "step-success" if final_st == "RECOVERED" else ("step-blocked" if not safe_allowed else "step-warn")
        verify_step_icon = "✓" if final_st == "RECOVERED" else ("🚫" if not safe_allowed else "⚠️")

        render_html(
            f"""
            <div class="lifecycle-flow">
                <div class="lifecycle-step step-success">✓ 1. DETECT</div>
                <div class="lifecycle-sep">→</div>
                <div class="lifecycle-step step-success">✓ 2. QUANTIFY</div>
                <div class="lifecycle-sep">→</div>
                <div class="lifecycle-step step-success">✓ 3. DECIDE</div>
                <div class="lifecycle-sep">→</div>
                <div class="lifecycle-step {'step-success' if safe_allowed else 'step-blocked'}">
                    {'✓' if safe_allowed else '🚫'} 4. SAFETY
                </div>
                <div class="lifecycle-sep">→</div>
                <div class="lifecycle-step {recover_step_cls}">
                    {recover_step_icon} 5. RECOVER
                </div>
                <div class="lifecycle-sep">→</div>
                <div class="lifecycle-step {verify_step_cls}">
                    {verify_step_icon} 6. VERIFY
                </div>
                <div class="lifecycle-sep">→</div>
                <div class="lifecycle-step {'step-success' if has_learn else 'step-pending'}">
                    {'✓' if has_learn else '○'} 7. LEARN
                </div>
                <div class="lifecycle-sep">→</div>
                <div class="lifecycle-step {'step-success' if has_lift else 'step-pending'}">
                    {'✓' if has_lift else '○'} 8. ADAPT
                </div>
            </div>
            """
        )

        # 2. Executive 5-KPI Summary Cards
        k1, k2, k3, k4, k5 = st.columns(5)

        with k1:
            st.metric(
                label="Incident",
                value=f"{demo_result.incident.severity}",
                delta=f"-{demo_result.incident.degradation_pp:.1f} pp drop",
                delta_color="inverse",
                help=f"Observed Success Rate: {demo_result.incident.current_success_rate:.1%} vs {demo_result.incident.baseline_success_rate:.1%} baseline (OBSERVED)",
            )
            st.caption("**OBSERVED** · Route degradation")

        with k2:
            st.metric(
                label="Revenue at Risk",
                value=f"₹{demo_result.revenue_impact.revenue_at_risk:,.0f}",
                delta=f"-{demo_result.revenue_impact.excess_failures:.0f} excess fails",
                delta_color="inverse",
                help="Authoritative revenue at risk calculated by IncidentRevenueCalculator (COUNTERFACTUAL)",
            )
            st.caption("**THEORETICAL** · Pre-intervention risk")

        with k3:
            safe_pill = "pill-green" if safe_allowed else "pill-red"
            safe_text = "ALLOWED" if safe_allowed else "BLOCKED"
            render_html(
                f"""
                <div>
                    <div style="font-size: 0.82rem; color: #64748b; font-weight: 600; margin-bottom: 4px;">SAFETY GATE</div>
                    <div style="margin-top: 2px;"><span class="{safe_pill}" style="font-size: 0.95rem; font-weight: 700; padding: 4px 10px;">{safe_text}</span></div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{demo_result.safety_decision.reason if demo_result.safety_decision else 'Evaluated'}">
                        {demo_result.safety_decision.action if demo_result.safety_decision else 'EVALUATED'}
                    </div>
                </div>
                """
            )
            st.caption("**GOVERNED** · Deterministic policy")

        with k4:
            net_rec = demo_result.batch_result.get("net_recovered_value", 0.0) if demo_result.batch_result else 0.0
            roi_val = demo_result.scorecard.recovery_roi if demo_result.scorecard else 0.0
            roi_str = f"{roi_val:.1f}x ROI" if roi_val and roi_val > 0 else "0.0x ROI"

            if demo_result.batch_result and safe_allowed:
                st.metric(
                    label="Recovery",
                    value=f"₹{net_rec:,.0f} net",
                    delta=f"{succ_rec}/{demo_result.batch_result.get('attempted_transactions', 0)} rec · {roi_str}",
                    delta_color="normal",
                    help="Simulated net value = Recovered Amount - Execution Cost (SIMULATED)",
                )
            else:
                st.metric(
                    label="Recovery",
                    value="Not executed",
                    delta="Blocked / 0 attempted",
                    delta_color="off",
                    help="Recovery batch was not executed due to safety controls.",
                )
            st.caption("**SIMULATED** · Bounded canary")

        with k5:
            lift_str = f"{demo_result.score_delta:+.4f}" if demo_result.score_delta else ("Recorded" if demo_result.learning_evidence else "None")
            lift_delta = f"Top: {demo_result.top_route_after}" if demo_result.top_route_after else "No change"
            st.metric(
                label="Learning",
                value=lift_str,
                delta=lift_delta,
                delta_color="normal" if demo_result.score_delta and demo_result.score_delta > 0 else "off",
                help="Route score update derived from verified recovery evidence (LEARNED)",
            )
            st.caption(f"**{PROVENANCE_LEARNED}** · Bayesian lift")

        # Summary banner
        if demo_result.is_success:
            st.success(f"✅ {demo_result.summary_message}")
        elif not safe_allowed:
            st.error(f"🛡️ {demo_result.summary_message}")
        else:
            st.warning(f"⚠️ {demo_result.summary_message}")

        # ---------------------------------------------------------------
        # JUDGE DEMO — DETAILED PHASE CARDS
        # ---------------------------------------------------------------
        _vm = build_demo_view_model(demo_result)
        _fin = get_financial_display(demo_result)
        _learn = get_learning_display(demo_result)
        _reeval = get_reevaluation_display(demo_result)
        _flow = get_closed_loop_learning_flow(demo_result)
        _status_bar = get_final_status_bar(demo_result)

        st.markdown("---")
        render_html(
            """
            <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:0.25rem;">
                <div style="font-size:1.05rem; font-weight:800; color:#0f172a;">📋 Payment Reliability Demo</div>
                <span class="badge-sim">Deterministic simulation of incident detection, governed recovery, and closed-loop learning.</span>
            </div>
            """
        )

        # ---- Phase 1+2: Incident ----------------------------------------
        inc_sev = _vm.get("severity", "UNKNOWN")
        inc_pill = "pill-red" if inc_sev == "CRITICAL" else "pill-amber"
        render_html(
            f"""
            <div class="incident-card-critical" id="judge-incident-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <div style="font-size:0.78rem; font-weight:700; color:#64748b; letter-spacing:0.04em; text-transform:uppercase;">INCIDENT DETECTED</div>
                    <span class="{inc_pill}">SEVERITY: {inc_sev}</span>
                </div>
                <div style="display:grid; grid-template-columns:repeat(6,1fr); gap:10px; padding-top:10px; border-top:1px solid #f1f5f9;">
                    <div>
                        <div style="font-size:0.72rem; color:#64748b;">Observed Success Rate</div>
                        <div style="font-size:1.05rem; font-weight:700; color:#dc2626;">{_vm['observed_success_rate'] * 100:.1f}%</div>
                        <div style="font-size:0.65rem; color:#94a3b8;">{PROVENANCE_OBSERVED}</div>
                    </div>
                    <div>
                        <div style="font-size:0.72rem; color:#64748b;">Baseline</div>
                        <div style="font-size:1.05rem; font-weight:600; color:#334155;">{_vm['baseline_success_rate'] * 100:.1f}%</div>
                        <div style="font-size:0.65rem; color:#94a3b8;">{PROVENANCE_OBSERVED}</div>
                    </div>
                    <div>
                        <div style="font-size:0.72rem; color:#64748b;">Degradation</div>
                        <div style="font-size:1.05rem; font-weight:700; color:#dc2626;">−{_vm['degradation_pp']:.1f} pp</div>
                        <div style="font-size:0.65rem; color:#94a3b8;">{PROVENANCE_OBSERVED}</div>
                    </div>
                    <div>
                        <div style="font-size:0.72rem; color:#64748b;">Transactions</div>
                        <div style="font-size:1.05rem; font-weight:600; color:#0f172a;">{_vm['transactions_observed']:,}</div>
                        <div style="font-size:0.65rem; color:#94a3b8;">{PROVENANCE_OBSERVED}</div>
                    </div>
                    <div>
                        <div style="font-size:0.72rem; color:#64748b;">Revenue at Risk</div>
                        <div style="font-size:1.05rem; font-weight:700; color:#dc2626;">{_fin.get('revenue_at_risk','₹0.00')}</div>
                        <div style="font-size:0.65rem; color:#94a3b8;">{PROVENANCE_THEORETICAL}</div>
                    </div>
                    <div>
                        <div style="font-size:0.72rem; color:#64748b;">Provenance</div>
                        <div style="font-size:0.72rem; font-weight:600; color:#475569;">Simulated telemetry</div>
                        <div style="font-size:0.65rem; color:#94a3b8;">IncidentIntelligence</div>
                    </div>
                </div>
                <div style="margin-top:8px; font-size:0.70rem; color:#94a3b8;">Revenue at Risk: THEORETICAL / COUNTERFACTUAL — modeled financial estimate, not money lost.</div>
            </div>
            """
        )

        # ---- Phase 3+4: AI Decision + Safety Gate -----------------------
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            d_conf_pct = _vm['confidence'] * 100
            loss_red = _vm.get('loss_reduction_pct', 0.0)
            render_html(
                f"""
                <div class="decision-card" id="judge-decision-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <div style="font-size:0.78rem; font-weight:700; color:#0284c7; text-transform:uppercase;">AI ROUTE DECISION</div>
                        <span class="pill-blue">Confidence: {d_conf_pct:.1f}%</span>
                    </div>
                    <div style="font-size:1.05rem; font-weight:700; color:#0f172a; margin-bottom:8px;">{_vm['selected_action']}</div>
                    <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:8px; padding-top:8px; border-top:1px solid #f1f5f9;">
                        <div>
                            <div style="font-size:0.70rem; color:#64748b;">Expected Loss Before</div>
                            <div style="font-size:0.90rem; font-weight:600; color:#64748b;">₹{_vm['expected_loss_before']:,.0f}</div>
                            <div style="font-size:0.60rem; color:#94a3b8;">{PROVENANCE_THEORETICAL}</div>
                        </div>
                        <div>
                            <div style="font-size:0.70rem; color:#64748b;">Expected Loss After</div>
                            <div style="font-size:0.90rem; font-weight:600; color:#059669;">₹{_vm['expected_loss_after']:,.0f}</div>
                            <div style="font-size:0.60rem; color:#94a3b8;">{PROVENANCE_THEORETICAL}</div>
                        </div>
                        <div>
                            <div style="font-size:0.70rem; color:#64748b;">Loss Reduction</div>
                            <div style="font-size:0.90rem; font-weight:700; color:#059669;">{loss_red:.1f}%</div>
                            <div style="font-size:0.60rem; color:#94a3b8;">{PROVENANCE_THEORETICAL}</div>
                        </div>
                    </div>
                    <div style="margin-top:8px; font-size:0.68rem; color:#94a3b8;">*Modeled counterfactual projections — IncidentDecisionEngine</div>
                </div>
                """
            )

        with dcol2:
            s_allowed = _vm.get('safety_allowed', False)
            s_review = _vm.get('safety_human_review', False)
            if s_allowed:
                s_bg, s_border, s_color, s_badge = "#f0fdf4", "#bbf7d0", "#15803d", "pill-green"
                s_status_text = "Safety policy: ALLOWED"
            elif s_review:
                s_bg, s_border, s_color, s_badge = "#fffbeb", "#fde68a", "#b45309", "pill-amber"
                s_status_text = "Safety policy: HUMAN REVIEW REQUIRED"
            else:
                s_bg, s_border, s_color, s_badge = "#fef2f2", "#fecaca", "#b91c1c", "pill-red"
                s_status_text = "Safety policy: BLOCKED"
            human_review_txt = "Yes — Required" if s_review else "Not required"
            render_html(
                f"""
                <div style="background:{s_bg}; border:1px solid {s_border}; border-left:4px solid {s_color}; border-radius:10px; padding:1.25rem 1.4rem; height:100%;" id="judge-safety-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <div style="font-size:0.78rem; font-weight:700; color:{s_color}; text-transform:uppercase;">SAFETY GATE</div>
                        <span class="{s_badge}">{"ALLOWED" if s_allowed else ("REVIEW" if s_review else "BLOCKED")}</span>
                    </div>
                    <div style="font-size:1.0rem; font-weight:800; color:{s_color}; margin-bottom:6px;">{s_status_text}</div>
                    <div style="font-size:0.82rem; font-weight:600; color:#334155; margin-bottom:6px;">Human Review: {human_review_txt}</div>
                    <div style="font-size:0.76rem; color:#475569; line-height:1.4; margin-bottom:8px;">{_vm.get('safety_reason', '')}</div>
                    <div style="font-size:0.68rem; color:#94a3b8; border-top:1px solid {s_border}; padding-top:6px;">Simulation only · SafetyController · {PROVENANCE_GOVERNED}</div>
                </div>
                """
            )

        # ---- Phase 5+6: Canary + Recovery Outcome -----------------------
        cc1, cc2 = st.columns(2)
        with cc1:
            canary_dec = _vm.get('canary_decision', 'N/A')
            canary_pill = "pill-green" if canary_dec == "EXPAND" else ("pill-amber" if canary_dec in ("STOP", "ESCALATE") else "pill-blue")
            render_html(
                f"""
                <div class="recovery-card" id="judge-canary-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <div style="font-size:0.78rem; font-weight:700; color:#64748b; text-transform:uppercase;">BOUNDED CANARY</div>
                        <span class="{canary_pill}">{canary_dec}</span>
                    </div>
                    <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:8px; padding-top:8px; border-top:1px solid #f1f5f9;">
                        <div>
                            <div style="font-size:0.70rem; color:#64748b;">Eligible</div>
                            <div style="font-size:1.0rem; font-weight:700; color:#0f172a;">{_vm['eligible_transactions']}</div>
                        </div>
                        <div>
                            <div style="font-size:0.70rem; color:#64748b;">Attempted</div>
                            <div style="font-size:1.0rem; font-weight:700; color:#0284c7;">{_vm['attempted_transactions']}</div>
                        </div>
                        <div>
                            <div style="font-size:0.70rem; color:#64748b;">Recovered</div>
                            <div style="font-size:1.0rem; font-weight:700; color:#059669;">{_vm['successful_recoveries']}</div>
                        </div>
                        <div>
                            <div style="font-size:0.70rem; color:#64748b;">Failed</div>
                            <div style="font-size:1.0rem; font-weight:600; color:#dc2626;">{_vm['failed_recoveries']}</div>
                        </div>
                        <div>
                            <div style="font-size:0.70rem; color:#64748b;">Canary Rate</div>
                            <div style="font-size:1.0rem; font-weight:700; color:#059669;">{_vm['canary_recovery_rate'] * 100:.1f}%</div>
                        </div>
                        <div>
                            <div style="font-size:0.70rem; color:#64748b;">Decision</div>
                            <div style="font-size:0.90rem; font-weight:700; color:#0f172a;">{canary_dec}</div>
                        </div>
                    </div>
                    <div style="margin-top:8px; font-size:0.68rem; color:#94a3b8;">{PROVENANCE_SIMULATED} · BoundedRecoveryExecutor</div>
                </div>
                """
            )

        with cc2:
            rb = _vm.get('rollback_required', False)
            fin_st = _vm.get('final_status', 'PENDING')
            rec_bg = "#f0fdf4" if fin_st == "RECOVERED" else ("#fef2f2" if rb else "#f8fafc")
            rec_border = "#bbf7d0" if fin_st == "RECOVERED" else ("#fecaca" if rb else "#e2e8f0")
            render_html(
                f"""
                <div style="background:{rec_bg}; border:1px solid {rec_border}; border-radius:10px; padding:1.25rem; height:100%;" id="judge-recovery-card">
                    <div style="font-size:0.78rem; font-weight:700; color:#64748b; text-transform:uppercase; margin-bottom:8px;">RECOVERY OUTCOME</div>
                    <div style="display:grid; grid-template-columns:repeat(2,1fr); gap:8px; padding-top:8px; border-top:1px solid {rec_border}; margin-bottom:8px;">
                        <div>
                            <div style="font-size:0.70rem; color:#64748b;">Attempted Amount</div>
                            <div style="font-size:0.88rem; font-weight:600; color:#0f172a;">{_fin.get('attempted_amount','₹0.00')}</div>
                            <div style="font-size:0.60rem; color:#94a3b8;">[{PROVENANCE_SIMULATED}]</div>
                        </div>
                        <div>
                            <div style="font-size:0.70rem; color:#64748b;">Gross Recovered</div>
                            <div style="font-size:0.88rem; font-weight:600; color:#059669;">{_fin.get('gross_recovered','₹0.00')}</div>
                            <div style="font-size:0.60rem; color:#94a3b8;">[{PROVENANCE_SIMULATED}]</div>
                        </div>
                        <div>
                            <div style="font-size:0.70rem; color:#64748b;">Execution Cost</div>
                            <div style="font-size:0.88rem; font-weight:600; color:#64748b;">{_fin.get('execution_cost','₹0.00')}</div>
                            <div style="font-size:0.60rem; color:#94a3b8;">[{PROVENANCE_SIMULATED}]</div>
                        </div>
                        <div>
                            <div style="font-size:0.70rem; color:#64748b;">ROI</div>
                            <div style="font-size:0.88rem; font-weight:700; color:#0284c7;">{_fin.get('recovery_roi_str','N/A')}</div>
                            <div style="font-size:0.60rem; color:#94a3b8;">[{PROVENANCE_SIMULATED}]</div>
                        </div>
                    </div>
                    <div style="font-size:0.90rem; font-weight:700; color:#0f172a; margin-bottom:4px;">
                        Simulated Net Recovered Value: {_fin.get('net_recovered_value','₹0.00')} [{PROVENANCE_SIMULATED}]
                    </div>
                    <div style="font-size:0.78rem; color:#475569;">Recovery Rate: {_fin.get('recovery_rate_pct','0.0%')} &nbsp;|&nbsp; Final Status: <b>{fin_st}</b></div>
                    <div style="margin-top:8px; font-size:0.68rem; color:#94a3b8;">All execution values are SIMULATED · Bounded sandbox only</div>
                </div>
                """
            )

        # ---- Phase 7+8: Closed-Loop Learning Visualization (Milestone 7) ---
        dec_changed_color = "#b45309" if _flow['decision_changed'] else "#059669"
        render_html(
            f"""
            <div class="fintech-card" id="judge-learning-card" style="padding:1.25rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div style="font-size:0.82rem; font-weight:700; color:#7c3aed; letter-spacing:0.04em; text-transform:uppercase;">
                        🔄 CLOSED-LOOP LEARNING VISUALIZATION
                    </div>
                    <span class="pill-purple">[{PROVENANCE_LEARNED}]</span>
                </div>

                <div style="display:grid; grid-template-columns:1fr auto 1.15fr auto 1fr auto 1.15fr; gap:8px; align-items:center;">
                    <!-- Stage 1: BEFORE LEARNING -->
                    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:10px;">
                        <div style="font-size:0.68rem; font-weight:700; color:#64748b; text-transform:uppercase; margin-bottom:4px;">BEFORE LEARNING</div>
                        <div style="font-size:0.78rem; font-weight:600; color:#0f172a; margin-bottom:2px;">Route: {_flow['route_before']}</div>
                        <div style="font-size:0.78rem; font-family:monospace; color:#475569;">Score: <b>{_flow['score_before']}</b></div>
                    </div>

                    <div style="font-size:1.1rem; font-weight:700; color:#94a3b8; text-align:center;">→</div>

                    <!-- Stage 2: VERIFIED RECOVERY EVIDENCE -->
                    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:10px;">
                        <div style="font-size:0.68rem; font-weight:700; color:#0284c7; text-transform:uppercase; margin-bottom:4px;">VERIFIED EVIDENCE</div>
                        <div style="font-size:0.74rem; color:#475569;">Attempts: <b style="color:#0f172a;">{_flow['attempts']}</b> &nbsp;|&nbsp; Recoveries: <b style="color:#059669;">{_flow['recoveries']}</b></div>
                        <div style="font-size:0.74rem; color:#475569; margin-top:2px;">Confidence: <b style="color:#0284c7;">{_flow['evidence_confidence']}</b></div>
                    </div>

                    <div style="font-size:1.1rem; font-weight:700; color:#94a3b8; text-align:center;">→</div>

                    <!-- Stage 3: AFTER LEARNING -->
                    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:10px;">
                        <div style="font-size:0.68rem; font-weight:700; color:#059669; text-transform:uppercase; margin-bottom:4px;">AFTER LEARNING</div>
                        <div style="font-size:0.78rem; font-weight:600; color:#0f172a; margin-bottom:2px;">Route: {_flow['route_after']}</div>
                        <div style="font-size:0.78rem; font-family:monospace; color:#059669;">Score: <b>{_flow['score_after']}</b></div>
                        <div style="font-size:0.72rem; color:#059669; font-weight:600; margin-top:1px;">Delta: {_flow['score_delta']}</div>
                    </div>

                    <div style="font-size:1.1rem; font-weight:700; color:#94a3b8; text-align:center;">→</div>

                    <!-- Stage 4: RE-EVALUATION -->
                    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:10px;">
                        <div style="font-size:0.68rem; font-weight:700; color:#0369a1; text-transform:uppercase; margin-bottom:4px;">RE-EVALUATION</div>
                        <div style="font-size:0.74rem; color:#475569;">Top Before: <span style="font-weight:600; color:#0f172a;">{_flow['top_route_before']}</span></div>
                        <div style="font-size:0.74rem; color:#475569;">Top After: <span style="font-weight:600; color:#059669;">{_flow['top_route_after']}</span></div>
                        <div style="font-size:0.74rem; color:#475569; margin-top:2px;">Decision Changed: <b style="color:{dec_changed_color};">{_flow['decision_changed_label']}</b></div>
                    </div>
                </div>
                <div style="margin-top:10px; font-size:0.68rem; color:#94a3b8; border-top:1px solid #f1f5f9; padding-top:6px;">
                    {PROVENANCE_LEARNED} · RecoveryLearningEngine evidence updates Bayesian route scoring and feeds subsequent decision engine cycles.
                </div>
            </div>
            """
        )

        # ---- Final Status Bar -------------------------------------------
        render_html("<div style='margin-top:1rem;'></div>")
        status_bar_html = '<div class="lifecycle-flow" id="judge-status-bar">'
        first_item = True
        for stage_label, phase_status, phase_display in _status_bar:
            css_cls = get_phase_css_class(phase_status)
            icon = get_phase_icon(phase_status)
            if not first_item:
                status_bar_html += '<div class="lifecycle-sep">→</div>'
            status_bar_html += (
                f'<div class="lifecycle-step {css_cls}">'
                f'{icon} {stage_label}<br>'
                f'<span style="font-size:0.68rem; font-weight:400;">{phase_display}</span>'
                f'</div>'
            )
            first_item = False
        status_bar_html += '</div>'
        render_html(status_bar_html)

        # ---- Provenance Legend ------------------------------------------
        with st.expander("ℹ️ Metric Provenance Legend", expanded=False):
            render_html(
                f"""
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px,1fr)); gap:10px; font-size:0.78rem;">
                    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px;">
                        <div style="font-weight:700; color:#475569; margin-bottom:4px;">{PROVENANCE_OBSERVED}</div>
                        <div style="color:#64748b;">Measured from simulated payment telemetry</div>
                    </div>
                    <div style="background:#fef3c7; border:1px solid #fde68a; border-radius:8px; padding:10px;">
                        <div style="font-weight:700; color:#92400e; margin-bottom:4px;">{PROVENANCE_THEORETICAL}</div>
                        <div style="color:#64748b;">Modeled financial/risk estimate — counterfactual</div>
                    </div>
                    <div style="background:#e0e7ff; border:1px solid #c7d2fe; border-radius:8px; padding:10px;">
                        <div style="font-weight:700; color:#3730a3; margin-bottom:4px;">{PROVENANCE_SIMULATED}</div>
                        <div style="color:#64748b;">Bounded sandbox recovery execution</div>
                    </div>
                    <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:10px;">
                        <div style="font-weight:700; color:#15803d; margin-bottom:4px;">{PROVENANCE_GOVERNED}</div>
                        <div style="color:#64748b;">Safety and evaluation — deterministic policy</div>
                    </div>
                    <div style="background:#fdf4ff; border:1px solid #e9d5ff; border-radius:8px; padding:10px;">
                        <div style="font-weight:700; color:#7c3aed; margin-bottom:4px;">{PROVENANCE_LEARNED}</div>
                        <div style="color:#64748b;">Evidence from verified simulated outcomes</div>
                    </div>
                </div>
                """
            )

        # ---- Step-by-Step Lifecycle Trace (technical detail) ------------
        with st.expander("🔍 View Step-by-Step Lifecycle Execution Trace & Subsystem Provenance", expanded=False):
            trace_rows = []
            for ev in demo_result.lifecycle_events:
                trace_rows.append({
                    "Step": f"{ev.step_number}. {ev.stage_id}",
                    "Title": ev.title,
                    "Subsystem": ev.provenance,
                    "Status": ev.status,
                    "Detail": ev.detail,
                })
            st.dataframe(pd.DataFrame(trace_rows), use_container_width=True, hide_index=True)

    else:
        render_html(
            """
            <div class="lifecycle-flow">
                <div class="lifecycle-step step-pending">○ 1. DETECT</div>
                <div class="lifecycle-sep">→</div>
                <div class="lifecycle-step step-pending">○ 2. QUANTIFY</div>
                <div class="lifecycle-sep">→</div>
                <div class="lifecycle-step step-pending">○ 3. DECIDE</div>
                <div class="lifecycle-sep">→</div>
                <div class="lifecycle-step step-pending">○ 4. SAFETY</div>
                <div class="lifecycle-sep">→</div>
                <div class="lifecycle-step step-pending">○ 5. RECOVER</div>
                <div class="lifecycle-sep">→</div>
                <div class="lifecycle-step step-pending">○ 6. VERIFY</div>
                <div class="lifecycle-sep">→</div>
                <div class="lifecycle-step step-pending">○ 7. LEARN</div>
                <div class="lifecycle-sep">→</div>
                <div class="lifecycle-step step-pending">○ 8. ADAPT</div>
            </div>
            <div style="background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px; padding: 12px 16px; margin-top: 0.5rem; text-align: center;">
                <span style="font-size: 0.85rem; color: #475569;">
                    ℹ️ Select a scenario above and click <b>▶ Run End-to-End Demo</b> to execute the complete 8-stage recovery loop in real-time.
                </span>
            </div>
            """
        )

st.markdown("<hr style='margin: 1.5rem 0 1.25rem 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)


# =========================================
# SECTION 1 — SYSTEM OVERVIEW
# =========================================

st.markdown('<div id="system-overview"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">📊 System Overview</div>', unsafe_allow_html=True)
st.caption(
    "An AI-driven payment reliability layer that detects route degradation, "
    "quantifies revenue exposure, selects bounded recovery actions, "
    "verifies outcomes, and learns from verified recovery evidence."
)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(
        "Monitored Routes",
        f"{live_report.get('routes_monitored', 60)}",
        help="Active payment routes under continuous monitoring",
    )

with kpi2:
    st.metric(
        "Success Rate",
        f"{overall_success * 100:.2f}%",
        delta=f"{(overall_success - 0.9442) * 100:.2f} pp vs baseline",
        help="Across all transactions in observation window",
    )

with kpi3:
    risk_display = impact["revenue_at_risk"] if impact else 0.0
    st.metric(
        "Revenue at Risk",
        f"₹{risk_display:,.0f}",
        delta=f"-{impact['excess_failures']:.0f} excess failures" if impact else "0",
        delta_color="inverse",
        help="Excess failure loss quantified by revenue engine",
    )

with kpi4:
    st.metric(
        "Net Recovered Value",
        f"₹{total_net_recovered:,.0f}",
        help="Cumulative authoritative net recovered value across executed recovery actions (recovered value minus execution cost)",
    )
    st.caption("Simulated / Counterfactual")

# Scenario control overlay alert
if scenario_control["decision"] == "ESCALATE":
    st.warning(
        "🟡 Scenario safety control: automated recovery is intentionally "
        "held for human review because AI confidence is below threshold."
    )
elif scenario_control["guardrail"] == "ROLLBACK":
    st.error(
        "↩️ Scenario safety control: recovery is expected to trigger "
        "rollback if the simulated alternative breaches its guardrail."
    )
elif scenario_control["decision"] == "STOP":
    st.info(
        "🔴 Scenario safety control: recovery is intentionally blocked "
        "because the simulated degradation is below the recovery threshold."
    )
elif scenario_control["decision"] == "CONTINUE":
    st.success(
        "🟢 Scenario safety control: route remains within configured "
        "performance guardrails."
    )

if incident is None:
    st.success(
        "🟢 Payment system operating normally. "
        "No significant degradation detected."
    )
else:
    payment_method = incident["payment_method"]
    affected_bank = incident["bank"]
    device_type = incident["device_type"]
    route = f"{payment_method} → {affected_bank} → {device_type}"
    incident_success = incident["success_rate"] * 100
    baseline_success = incident["baseline_success_rate"] * 100
    degradation = incident["degradation_percentage_points"]
    incident_start = pd.Timestamp(incident["time_window"])
    incident_end = incident_start + pd.Timedelta(hours=1)

    severity_label = (
        scenario_control.get("severity")
        if scenario_control
        else ("CRITICAL" if degradation >= 20 else "DEGRADED")
    )
    is_critical = severity_label == "CRITICAL"
    card_border_class = (
        "incident-card-critical" if is_critical else "incident-card"
    )
    pill_style = "pill-red" if is_critical else "pill-amber"

    render_html(
        f"""
        <div class="{card_border_class}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="font-size: 0.78rem; font-weight: 700; color: #64748b; letter-spacing: 0.04em; text-transform: uppercase;">
                    Active Incident
                </div>
                <span class="{pill_style}">SEVERITY: {severity_label}</span>
            </div>
            <div style="font-size: 1.4rem; font-weight: 700; color: #0f172a; margin-bottom: 12px;">
                {route}
            </div>
            <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; padding-top: 10px; border-top: 1px solid #f1f5f9;">
                <div>
                    <div style="font-size: 0.72rem; color: #64748b;">Current Success</div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #dc2626;">{incident_success:.2f}%</div>
                </div>
                <div>
                    <div style="font-size: 0.72rem; color: #64748b;">Baseline</div>
                    <div style="font-size: 1.15rem; font-weight: 600; color: #334155;">{baseline_success:.2f}%</div>
                </div>
                <div>
                    <div style="font-size: 0.72rem; color: #64748b;">Degradation</div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #dc2626;">-{degradation:.2f} pp</div>
                </div>
                <div>
                    <div style="font-size: 0.72rem; color: #64748b;">Revenue at Risk</div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #dc2626;">₹{impact['revenue_at_risk']:,.0f}</div>
                </div>
                <div>
                    <div style="font-size: 0.72rem; color: #64748b;">Failed Txns</div>
                    <div style="font-size: 1.15rem; font-weight: 600; color: #0f172a;">{impact['actual_failures']:,}</div>
                </div>
            </div>
        </div>
        """
    )

    with st.expander("🔎 Incident Window & Historical Breakdown", expanded=False):
        det_c1, det_c2 = st.columns(2)
        with det_c1:
            st.markdown(f"**Window:** `{incident_start} → {incident_end}`")
            st.markdown(f"**Total Transactions:** `{int(incident['transactions']):,}`")
        with det_c2:
            st.markdown(f"**Failed Amount:** `₹{impact['failed_amount']:,.0f}`")
            st.markdown(f"**Excess Failures:** `{impact['excess_failures']:.1f}`")


    # =====================================
    # INCIDENT TIMELINE
    # =====================================

    timeline = transactions.copy()
    timeline["timestamp"] = pd.to_datetime(timeline["timestamp"], format="mixed")
    timeline["hour"] = timeline["timestamp"].dt.floor("1h")

    hourly = (
        timeline.groupby("hour")
        .agg(
            transactions=("transaction_id", "count"),
            successful=("status", lambda x: (x == "SUCCESS").sum()),
        )
        .reset_index()
    )
    hourly["success_rate"] = (hourly["successful"] / hourly["transactions"]) * 100
    hourly = hourly.sort_values("hour")

    with st.expander("📈 View Hourly Incident Degradation Timeline Chart", expanded=False):
        timeline_start = incident_start - pd.Timedelta(hours=12)
        timeline_end = incident_start + pd.Timedelta(hours=12)

        focused_hourly = hourly[
            (hourly["hour"] >= timeline_start) & (hourly["hour"] <= timeline_end)
        ].copy()

        if not focused_hourly.empty:
            st.line_chart(
                focused_hourly.set_index("hour")["success_rate"],
                height=260,
                use_container_width=True,
            )
        else:
            st.line_chart(
                hourly.set_index("hour")["success_rate"],
                height=260,
                use_container_width=True,
            )

        incident_row = hourly[hourly["hour"] == incident_start]
        if not incident_row.empty:
            incident_rate = float(incident_row.iloc[0]["success_rate"])
            st.caption(
                f"Incident window detected at {incident_start.strftime('%Y-%m-%d %H:%M')} — "
                f"hourly system success rate: {incident_rate:.2f}%."
            )


    # =====================================
    # AI DIAGNOSIS
    # =====================================

    st.markdown(
        '<div class="section-title">'
        '🧠 AI Root Cause Analysis'
        '</div>',
        unsafe_allow_html=True
    )


    # -------------------------------------
    # Run Gemini diagnosis
    # -------------------------------------

    with st.spinner(
        "AI agent analyzing incident evidence..."
    ):

        try:

            ai_diagnosis = diagnose_incident(
                transactions,
                incident
            )

        except Exception as e:

            ai_diagnosis = None

            st.warning(
                f"AI diagnosis unavailable: {e}"
            )


    # -------------------------------------
    # Deterministic root cause
    # -------------------------------------

    root_cause = analyze_root_cause(
        transactions,
        incident
    )


    col1, col2 = st.columns(2)


    # =====================================
    # AI PRIMARY DIAGNOSIS
    # =====================================

    with col1:

        st.markdown(
            "### Primary Diagnosis"
        )

        st.caption(
            "Gemini analyzes incident evidence and provides an advisory diagnosis. "
            "It does not authorize payment recovery."
        )


        if ai_diagnosis:

            ai_source = ai_diagnosis.get(
                "source",
                "unknown"
            )


            source_label = (
                "🤖 Gemini AI"
                if ai_source == "gemini"
                else
                "🛡️ Evidence-Based Fallback"
            )


            st.markdown(
                f"""
<div class="ai-card">

<div class="ai-source">
{source_label}
</div>

<h3>
{ai_diagnosis['primary_diagnosis']}
</h3>

</div>
""",
                unsafe_allow_html=True
            )


            c1, c2 = st.columns(2)


            with c1:

                st.metric(
                    "AI Confidence",
                    f"{ai_diagnosis['confidence']:.0f}%"
                )


            with c2:

                st.metric(
                    "Severity",
                    ai_diagnosis["severity"]
                )


            st.caption(
                f"Diagnosis source: "
                f"{ai_source}"
            )


            st.markdown(
                f"""
<div class="explanation-card">

The AI identified
<b>{route}</b>
as a route-specific degradation based on
the observed transaction evidence.

</div>
""",
                unsafe_allow_html=True
            )


        else:

            st.warning(
                "AI diagnosis is currently unavailable."
            )


    # =====================================
    # DETERMINISTIC FAILURE ANALYSIS
    # =====================================

    with col2:

        st.markdown(
            "### Failure Reasons"
        )


        error_analysis = root_cause[
            "error_analysis"
        ]


        if not error_analysis.empty:

            display_errors = (
                error_analysis.copy()
            )


            display_errors[
                "percentage"
            ] = (
                display_errors[
                    "percentage"
                ].round(2)
            )


            display_errors = (
                display_errors.rename(
                    columns={
                        "error_code":
                            "Error Code",

                        "failures":
                            "Failures",

                        "percentage":
                            "Share (%)"
                    }
                )
            )


            st.dataframe(
                display_errors[
                    [
                        "Error Code",
                        "Failures",
                        "Share (%)"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )


        else:

            st.info(
                "No failure reason data available."
            )


    # =====================================
    # AI EVIDENCE
    # =====================================

    if ai_diagnosis:
        with st.expander("🔍 Detailed AI Evidence & Investigation Recommendations", expanded=False):
            st.markdown("**Incident Evidence Observed:**")
            for evidence in ai_diagnosis.get("evidence", []):
                st.markdown(f"• {evidence}")

            st.markdown("**Recommended Advisory Investigation:**")
            for item in ai_diagnosis.get("recommended_investigation", []):
                st.markdown(f"• {item}")

            st.caption(
                "AI diagnosis is advisory. "
                "Recovery authorization remains strictly controlled "
                "by the deterministic policy engine."
            )


    # Ensure authoritative impact object is present for downstream engines
    if impact is None and incident is not None:
        impact = calculate_revenue_impact(transactions, incident)

historical_candidates = transactions.copy()
historical_candidates["timestamp"] = pd.to_datetime(
    historical_candidates["timestamp"],
    format="mixed",
    errors="coerce"
)

historical_candidates = historical_candidates[
    ~(
        (historical_candidates["timestamp"] >= incident_start)
        &
        (historical_candidates["timestamp"] < incident_end)
    )
].copy()

candidate_data = (
    historical_candidates[
        (historical_candidates["payment_method"] == payment_method)
        &
        (historical_candidates["device_type"] == device_type)
    ]
    .groupby("bank")
    .agg(
        transactions=("transaction_id", "count"),
        successes=(
            "status",
            lambda x: (x == "SUCCESS").sum()
        ),
    )
    .reset_index()
)

route_candidates = []

for _, row in candidate_data.iterrows():

    if row["bank"] == affected_bank:
        continue

    route_candidates.append(
        {
            "route": (
                f"{payment_method} + "
                f"{row['bank']} + "
                f"{device_type}"
            ),
            "transactions": int(row["transactions"]),
            "successes": int(row["successes"]),
        }
    )

average_transaction_value = float(
    transactions[
        (transactions["payment_method"] == payment_method)
        &
        (transactions["bank"] == affected_bank)
        &
        (transactions["device_type"] == device_type)
    ]["amount"].mean()
)

try:

    if "learning_history" not in st.session_state:
        st.session_state["learning_history"] = PersistentLearningHistory()

    learning_history = st.session_state["learning_history"]

    decision_engine = IncidentDecisionEngine(
        learning_history=learning_history
    )

    revenue_impact_obj = None
    if impact:
        revenue_impact_obj = IncidentRevenueImpact(
            incident_transactions=int(incident["transactions"]),
            incident_failures=int(impact["actual_failures"]),
            baseline_failure_rate=max(
                0.0,
                1.0 - float(incident["baseline_success_rate"]),
            ),
            expected_failures=float(impact["expected_failures"]),
            excess_failures=float(impact["excess_failures"]),
            actual_failed_amount=float(impact.get("failed_amount", 0.0)),
            expected_failed_amount=float(
                impact.get("failed_amount", 0.0)
                - impact.get("revenue_at_risk", 0.0)
            ),
            revenue_at_risk=float(impact["revenue_at_risk"]),
        )

    intelligence_result = decision_engine.evaluate(
        incident_route=(
            f"{payment_method} + "
            f"{affected_bank} + "
            f"{device_type}"
        ),
        transactions_affected=int(
            incident["transactions"]
        ),
        failures_observed=int(
            impact["actual_failures"]
        ),
        baseline_success_rate=float(
            incident["baseline_success_rate"]
        ),
        current_success_rate=float(
            incident["success_rate"]
        ),
        severity=(
            "CRITICAL"
            if degradation >= 20
            else "DEGRADED"
        ),
        average_transaction_value=average_transaction_value,
        route_candidates=route_candidates,
        revenue_impact=revenue_impact_obj,
    )

except Exception as e:

    intelligence_result = None

    st.error(
        f"Decision intelligence unavailable: {e}"
    )

if intelligence_result:

    intelligence_decision = intelligence_result.decision
    safety = intelligence_result.safety_decision

    # =====================================
    # FINAL SCENARIO SAFETY GATE
    # =====================================

    scenario_decision = scenario_control["decision"]
    scenario_guardrail = scenario_control["guardrail"]

    if scenario_decision == "ESCALATE":

        safety.allowed = False
        safety.requires_human_review = True
        safety.action = "ESCALATE"
        safety.reason = (
            "Scenario safety control requires human review "
            "because AI confidence is below the automation threshold."
        )

    elif scenario_decision == "STOP":

        safety.allowed = False
        safety.requires_human_review = False
        safety.action = "STOP"
        safety.reason = (
            "Scenario safety control blocks automated recovery "
            "because the degradation does not cross the recovery threshold."
        )

    elif scenario_decision == "CONTINUE":

        safety.allowed = False
        safety.requires_human_review = False
        safety.action = "CONTINUE"
        safety.reason = (
            "Scenario safety control indicates that the route remains "
            "within normal operating guardrails."
        )

    elif scenario_guardrail == "ROLLBACK":

        safety.allowed = False
        safety.requires_human_review = False
        safety.action = "ROLLBACK"
        safety.reason = (
            "Scenario recovery route breached its configured "
            "performance guardrail. Recovery must be rolled back."
        )

    # =====================================
    # RECOVERY RECOMMENDATION & POLICY
    # =====================================

    recovery = recommend_recovery(
        transactions,
        incident
    )

    if recovery and "post_recovery_success_rate" in selected_scenario:
        recovery["simulated_success_rate"] = float(
            selected_scenario["post_recovery_success_rate"]
        )
        recovery["alternative_success_rate"] = float(
            selected_scenario["post_recovery_success_rate"]
        )


       # =====================================
    # POLICY GATE
    # =====================================

    # The deterministic IncidentDecisionEngine is the
    # authoritative recovery authorization layer.
    #
    # The legacy policy engine is still evaluated so that
    # its individual policy checks remain visible in the UI,
    # but the final decision is derived from the deterministic
    # safety decision above.

    if recovery:

        legacy_policy_result = evaluate_recovery_policy(
            transactions,
            incident,
            recovery,
            recovery_attempts=0
        )

    else:

        legacy_policy_result = {
            "decision": "STOP",
            "approved": False,
            "reason": "No recovery recommendation available.",
            "checks": []
        }


    # Preserve the existing policy-check information while
    # making Decision Intelligence the authoritative control.
    policy_result = dict(legacy_policy_result)

    if intelligence_result:

        if safety.requires_human_review:

            policy_result["decision"] = "ESCALATE"
            policy_result["approved"] = False
            policy_result["reason"] = safety.reason

        elif not safety.allowed:

            policy_result["decision"] = safety.action
            policy_result["approved"] = False
            policy_result["reason"] = safety.reason

        elif (
            intelligence_decision.recommended_action.startswith(
                "ROUTE_SWITCH:"
            )
            and recovery
        ):

            policy_result["decision"] = "RECOVER"
            policy_result["approved"] = True
            policy_result["reason"] = (
                "Decision Intelligence authorized a bounded route-switch "
                "recovery after deterministic safety checks passed."
            )

        else:

            policy_result["decision"] = "CONTINUE"
            policy_result["approved"] = False
            policy_result["reason"] = (
                "Decision Intelligence determined that automated recovery "
                "is not required."
            )


    # =====================================
    # SCENARIO POLICY OVERRIDE
    # =====================================

    # Scenario controls remain a hard safety overlay for
    # controlled validation scenarios.

    if intelligence_result:

        scenario_decision = scenario_control["decision"]
        scenario_guardrail = scenario_control["guardrail"]

        if scenario_decision == "ESCALATE":

            policy_result = dict(policy_result)

            policy_result["decision"] = "ESCALATE"
            policy_result["approved"] = False
            policy_result["reason"] = (
                "Scenario safety control requires human review "
                "because AI confidence is below the automation threshold."
            )

        elif scenario_decision == "STOP":

            policy_result = dict(policy_result)

            policy_result["decision"] = "STOP"
            policy_result["approved"] = False
            policy_result["reason"] = (
                "Scenario safety control blocks automated recovery "
                "because the degradation does not cross the recovery threshold."
            )

        elif scenario_decision == "CONTINUE":

            policy_result = dict(policy_result)

            policy_result["decision"] = "CONTINUE"
            policy_result["approved"] = False
            policy_result["reason"] = (
                "Scenario safety control indicates that the route remains "
                "within normal operating guardrails. No recovery is required."
            )

        elif scenario_guardrail == "ROLLBACK":
            policy_result = dict(policy_result)

            policy_result["decision"] = "ROLLBACK"
            policy_result["approved"] = False
            policy_result["reason"] = (
                "Scenario recovery route breached its configured "
                "performance guardrail. Recovery must be rolled back."
            )

    # =====================================
    # RECOVERY INFORMATION & ALTERNATIVE ROUTE ANALYSIS
    # =====================================

    with st.expander("🏦 View Historical Alternative Route Health & Policy Checks", expanded=False):
        if recovery:
            simulation_preview = simulate_recovery(transactions, incident, recovery)

            st.markdown('<div class="recovery-card">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Current Bank", affected_bank)
            with col2:
                st.metric("Proposed Bank", recovery["alternative_bank"])
            with col3:
                st.metric("Historical Success", f"{recovery['alternative_success_rate'] * 100:.2f}%")

            expected_improvement = (
                recovery["alternative_success_rate"] - incident["success_rate"]
            ) * 100

            st.markdown(
                f"""
                <div class="explanation-card">
                <b>Why {recovery['alternative_bank']}?</b><br><br>
                The recovery engine evaluated historical <b>{payment_method} + {device_type}</b> traffic and identified
                <b>{recovery['alternative_bank']}</b> as the strongest eligible alternative.<br><br>
                <b>Current route:</b> {affected_bank}<br>
                <b>Alternative route:</b> {recovery['alternative_bank']}<br>
                <b>Current success rate:</b> {incident_success:.2f}%<br>
                <b>Historical alternative success rate:</b> {recovery['alternative_success_rate'] * 100:.2f}%<br>
                <b>Expected improvement:</b> {expected_improvement:.2f} percentage points<br><br>
                The recommendation is subject to all policy safety checks before any simulated recovery action is permitted.
                </div>
                """,
                unsafe_allow_html=True,
            )

        decision = policy_result["decision"]

        if decision == "RECOVER":
            st.markdown(
                f"""
                <div class="policy-recover">
                <h3>🟢 RECOVER — Approved</h3>
                <b>Decision:</b> {decision}<br><br>
                <b>Policy reason:</b><br>{policy_result['reason']}
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif decision == "ESCALATE":
            st.markdown(
                f"""
                <div class="policy-escalate">
                <h3>🟡 ESCALATE — Human Review Required</h3>
                <b>Decision:</b> {decision}<br><br>
                <b>Policy reason:</b><br>{policy_result['reason']}
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif decision == "ROLLBACK":
            st.markdown(
                f"""
                <div class="policy-stop">
                <h3>↩️ ROLLBACK — Recovery Reversed</h3>
                <b>Decision:</b> {decision}<br><br>
                <b>Policy reason:</b><br>{policy_result['reason']}
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif decision == "CONTINUE":
            st.success(f"🟢 **CONTINUE — No Recovery Required**\n\n{policy_result['reason']}")
        else:
            st.markdown(
                f"""
                <div class="policy-stop">
                <h3>🔴 STOP — Recovery Blocked</h3>
                <b>Decision:</b> {decision}<br><br>
                <b>Policy reason:</b><br>{policy_result['reason']}
                </div>
                """,
                unsafe_allow_html=True,
            )

        if policy_result["checks"]:
            st.markdown("### Policy Checks")
            policy_rows = []
            for check in policy_result["checks"]:
                policy_rows.append({
                    "Status": "✅ PASS" if check["passed"] else "❌ FAIL",
                    "Policy Check": check["check"],
                    "Value": check["value"],
                    "Threshold": check["threshold"],
                })
            policy_df = pd.DataFrame(policy_rows)
            st.dataframe(policy_df, use_container_width=True, hide_index=True)
            passed_checks = sum(check["passed"] for check in policy_result["checks"])
            total_checks = len(policy_result["checks"])
            st.caption(f"{passed_checks}/{total_checks} policy checks passed.")

        # Alternative Route Analysis
        historical = transactions[
            ~(
                (transactions["timestamp"] >= incident_start)
                & (transactions["timestamp"] < incident_end)
            )
        ].copy()

        route_data = historical[
            (historical["payment_method"] == payment_method)
            & (historical["device_type"] == device_type)
        ].copy()

        route_comparison = (
            route_data.groupby("bank")
            .agg(
                transactions=("transaction_id", "count"),
                successful=("status", lambda x: (x == "SUCCESS").sum()),
                failed=("status", lambda x: (x == "FAILED").sum()),
            )
            .reset_index()
        )

        if not route_comparison.empty:
            route_comparison["success_rate"] = (
                route_comparison["successful"] / route_comparison["transactions"] * 100
            )
            route_comparison = route_comparison[route_comparison["transactions"] >= 100].copy()
            route_comparison = route_comparison.sort_values("success_rate", ascending=False)

            def get_route_status(bank):
                if bank == affected_bank:
                    return "🔴 Degraded"
                if recovery and bank == recovery["alternative_bank"]:
                    if decision == "RECOVER":
                        return "🟢 Recommended"
                    elif decision == "ESCALATE":
                        return "🟡 Proposed"
                    else:
                        return "⚪ Blocked"
                return "Normal"

            route_comparison["status"] = route_comparison["bank"].apply(get_route_status)
            display_routes = route_comparison.rename(
                columns={
                    "bank": "Bank",
                    "transactions": "Transactions",
                    "successful": "Successful",
                    "failed": "Failed",
                    "success_rate": "Success Rate (%)",
                    "status": "Route Status",
                }
            )
            st.dataframe(
                display_routes[
                    ["Bank", "Transactions", "Successful", "Failed", "Success Rate (%)", "Route Status"]
                ].style.format({"Success Rate (%)": "{:.2f}"}),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No sufficient historical alternative route data available.")

            if recovery:
                if decision == "RECOVER":
                    st.success(
                        f"⚡ Approved action: Prefer {recovery['alternative_bank']} "
                        f"for eligible {payment_method} + {device_type} traffic."
                    )
                elif decision == "ESCALATE":
                    st.warning("⚠️ Automated recovery is not approved. Human review is required before routing changes.")
                elif decision == "ROLLBACK":
                    st.error("↩️ Recovery is blocked because the simulated alternative route breached its guardrail.")
                elif decision == "CONTINUE":
                    st.success("🟢 No automated recovery is required for this scenario.")
                else:
                    st.error("🛑 Automated recovery is blocked by the policy engine.")


    # =====================================
    # PERSISTENT BATCH RESULT
    # =====================================

    # Streamlit reruns the script after widget interactions.
    # Initialize this before the decision trail because the
    # trail displays the current guardrail state.
    if "batch_result" not in st.session_state:
        st.session_state["batch_result"] = None

    # =========================================
    # SECTION 2 — AI DECISION INTELLIGENCE
    # =========================================

    st.markdown('<div id="ai-decision-intelligence"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">🤖 AI Decision Intelligence</div>',
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------------
    # Build Deterministic Decision Explanation
    # ---------------------------------------------------------
    active_demo: Optional[DemoRunResult] = st.session_state.get("demo_run_result")

    if active_demo is not None and active_demo.incident is not None:
        act_inc = active_demo.incident
        act_rev = active_demo.revenue_impact
        act_dec = active_demo.decision
        act_dec_res = active_demo.decision_result
        act_safe = active_demo.safety_decision

        degradation_val = act_inc.degradation_pp
        rev_risk_val = act_rev.revenue_at_risk if act_rev else (impact["revenue_at_risk"] if impact else 0.0)
        loss_val = act_dec.expected_loss_before if act_dec else (act_rev.revenue_at_risk if act_rev else 0.0)

        route_ctx = None
        if act_dec_res and act_dec_res.ranked_routes:
            best_candidate = act_dec_res.ranked_routes[0]
            route_ctx = {
                "route": getattr(best_candidate, "route", ""),
                "observed_success_rate": getattr(best_candidate, "observed_success_rate", None),
                "adjusted_success_rate": getattr(best_candidate, "adjusted_success_rate", None),
                "evidence_confidence": getattr(best_candidate, "evidence_confidence", None),
                "score": getattr(best_candidate, "score", None),
                "explanation": getattr(best_candidate, "explanation", ""),
            }

        loss_estimate = LossEstimate(
            payment_id=f"inc_{act_inc.route}",
            financial_exposure=rev_risk_val,
            probability_of_loss=max(0.0, min(1.0, degradation_val / 100.0)),
            expected_loss=loss_val,
            currency="INR",
        )
        risk_assessment = RiskAssessment(
            payment_id=f"inc_{act_inc.route}",
            risk_score=round(min(1.0, degradation_val / 50.0), 2),
            risk_level=act_inc.severity,
            probability_of_loss=round(max(0.0, min(1.0, degradation_val / 100.0)), 2),
            risk_type="ROUTE_DEGRADATION",
            reasons=[f"Observed degradation of {degradation_val:.1f} pp on route"],
        )

        effective_decision = act_dec if act_dec else intelligence_decision
        effective_safety = act_safe if act_safe else safety
    else:
        degradation_val = degradation
        rev_risk_val = impact["revenue_at_risk"] if impact else 0.0
        loss_val = intelligence_result.expected_loss if intelligence_result else 0.0

        route_ctx = None
        if intelligence_result and intelligence_result.ranked_routes:
            best_candidate = intelligence_result.ranked_routes[0]
            route_ctx = {
                "route": getattr(best_candidate, "route", ""),
                "observed_success_rate": getattr(best_candidate, "observed_success_rate", None),
                "adjusted_success_rate": getattr(best_candidate, "adjusted_success_rate", None),
                "evidence_confidence": getattr(best_candidate, "evidence_confidence", None),
                "score": getattr(best_candidate, "score", None),
                "explanation": getattr(best_candidate, "explanation", ""),
            }
        elif recovery:
            route_ctx = {
                "route": f"{payment_method} + {recovery.get('alternative_bank', '')} + {device_type}",
                "observed_success_rate": recovery.get("alternative_success_rate"),
                "adjusted_success_rate": recovery.get("simulated_success_rate"),
                "explanation": recovery.get("reason", ""),
            }

        risk_assessment = None
        loss_estimate = None
        if intelligence_result:
            loss_estimate = LossEstimate(
                payment_id=f"inc_{incident.get('incident_id', 'unknown')}",
                financial_exposure=intelligence_result.financial_exposure,
                probability_of_loss=max(0.0, min(1.0, degradation / 100.0)) if degradation else 0.5,
                expected_loss=intelligence_result.expected_loss,
                currency="INR",
            )
            risk_assessment = RiskAssessment(
                payment_id=f"inc_{incident.get('incident_id', 'unknown')}",
                risk_score=round(min(1.0, degradation / 50.0), 2) if degradation else 0.5,
                risk_level=intelligence_result.severity,
                probability_of_loss=round(max(0.0, min(1.0, degradation / 100.0)), 2) if degradation else 0.5,
                risk_type="ROUTE_DEGRADATION",
                reasons=[f"Observed degradation of {degradation:.1f} pp on route"],
            )

        effective_decision = intelligence_decision
        effective_safety = safety

    decision_explanation = build_decision_explanation(
        decision=effective_decision,
        risk_assessment=risk_assessment,
        loss_estimate=loss_estimate,
        safety_decision=effective_safety,
        route_context=route_ctx,
    )

    incident_matters_text = (
        f"Route degradation of -{degradation_val:.1f} pp caused ₹{rev_risk_val:,.0f} revenue at risk "
        f"with an estimated expected loss of ₹{loss_val:,.0f}."
    )
    loss_reduction = max(
        0.0,
        effective_decision.expected_loss_before - effective_decision.expected_loss_after,
    ) if effective_decision else 0.0

    # Format Key Factors with visual icons
    def _format_kf_item(kf_text: str) -> tuple[str, str, str]:
        lower = kf_text.lower()
        if "safety gate blocked" in lower:
            return "✕", "#ef4444", kf_text
        elif "human review" in lower:
            return "⚠", "#f59e0b", "Human review required"
        elif "route degradation" in lower or "degradation" in lower:
            return "✓", "#10b981", "Critical route degradation"
        elif "expected loss" in lower:
            return "✓", "#10b981", "High expected loss"
        elif "stronger evidence" in lower or "alternative route" in lower:
            return "✓", "#10b981", "Alternative route has stronger evidence"
        elif "confidence" in lower:
            return "✓", "#10b981", "High decision confidence"
        elif "safety policy passed" in lower or "safe to execute" in lower:
            return "✓", "#10b981", "Safety gate passed"
        elif "positive estimated recovery" in lower or "recovery value" in lower:
            return "✓", "#10b981", "Positive recovery value projected"
        elif "elevated risk" in lower:
            return "✓", "#10b981", "Elevated route risk"
        return "✓", "#10b981", kf_text

    kf_items_html = []
    for kf in decision_explanation.key_factors:
        icon, icon_color, label = _format_kf_item(kf)
        kf_items_html.append(
            f'<div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem; color: #1e293b; line-height: 1.45;">'
            f'<span style="color: {icon_color}; font-weight: 800; font-size: 0.95rem;">{icon}</span>'
            f'<span>{label}</span>'
            f'</div>'
        )
    key_factors_html = "\n".join(kf_items_html) if kf_items_html else '<div style="color: #94a3b8; font-size: 0.82rem;">No specific factors recorded.</div>'

    # Alternatives HTML
    alt_items_html = []
    if decision_explanation.alternative_actions:
        for alt_str in decision_explanation.alternative_actions:
            if " (" in alt_str and alt_str.endswith(")"):
                action_part, details_part = alt_str.split(" (", 1)
                details_clean = details_part[:-1]
            else:
                action_part = alt_str
                details_clean = "Evaluated"

            alt_items_html.append(
                f'<div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px dashed #f1f5f9; font-size: 0.82rem;">'
                f'<span style="font-weight: 600; color: #1e293b; font-family: monospace; font-size: 0.78rem;">{action_part}</span>'
                f'<span style="color: #64748b; font-size: 0.74rem;">{details_clean}</span>'
                f'</div>'
            )
    alternatives_html = "\n".join(alt_items_html) if alt_items_html else '<div style="color: #94a3b8; font-size: 0.82rem;">No alternative interventions evaluated.</div>'

    # Safety status styling
    if effective_safety.allowed:
        safety_badge_text = "✓ AUTOMATION ALLOWED"
        safety_review_text = "Required" if effective_safety.requires_human_review else "Not required"
        safety_bg = "#f0fdf4"
        safety_border = "#bbf7d0"
        safety_header_color = "#15803d"
        safety_title_color = "#15803d"
    elif effective_safety.requires_human_review:
        safety_badge_text = "⚠ HUMAN REVIEW REQUIRED"
        safety_review_text = "Required"
        safety_bg = "#fffbeb"
        safety_border = "#fde68a"
        safety_header_color = "#b45309"
        safety_title_color = "#b45309"
    else:
        safety_badge_text = "✕ AUTOMATION BLOCKED"
        safety_review_text = "Required" if effective_safety.requires_human_review else "Not required"
        safety_bg = "#fef2f2"
        safety_border = "#fecaca"
        safety_header_color = "#b91c1c"
        safety_title_color = "#b91c1c"

    conf_display = f"{effective_decision.confidence * 100:.2f}%" if effective_decision else "0.00%"
    loss_before_val = effective_decision.expected_loss_before if effective_decision else loss_val
    loss_after_val = effective_decision.expected_loss_after if effective_decision else 0.0
    est_val = effective_decision.estimated_value if effective_decision else 0.0

    html_card = f"""
<div class="decision-card" style="border-left: 4px solid #0284c7; padding: 1.5rem; margin-bottom: 1.25rem;">
    <!-- Brand / Header -->
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <div style="font-size: 1.15rem; font-weight: 800; color: #0f172a; display: flex; align-items: center; gap: 8px;">
            🤖 AI DECISION INTELLIGENCE
        </div>
        <span class="pill-blue" style="font-size: 0.76rem; font-weight: 700;">DETERMINISTIC & AUDITABLE</span>
    </div>

    <!-- WHY THIS INCIDENT MATTERS -->
    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; margin-bottom: 14px;">
        <div style="font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">
            WHY THIS INCIDENT MATTERS
        </div>
        <div style="font-size: 0.95rem; font-weight: 600; color: #0f172a;">
            {incident_matters_text}
        </div>
    </div>

    <!-- 2-COLUMN: ACTION + KEY FACTORS -->
    <div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 16px; margin-bottom: 14px;">
        <!-- Left: WHY THIS ACTION -->
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <div style="font-size: 0.72rem; font-weight: 700; color: #0284c7; text-transform: uppercase; letter-spacing: 0.5px;">
                    WHY THIS ACTION
                </div>
                <span class="pill-blue">Confidence: {conf_display}</span>
            </div>
            <div style="font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-bottom: 8px;">
                {decision_explanation.selected_action}
            </div>
            <div style="font-size: 0.82rem; color: #475569; line-height: 1.45; margin-bottom: 10px;">
                {decision_explanation.selected_action_reason}
            </div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; padding-top: 8px; border-top: 1px solid #f1f5f9;">
                <div>
                    <div style="font-size: 0.68rem; color: #64748b;">Loss Before</div>
                    <div style="font-size: 0.85rem; font-weight: 600; color: #64748b;">₹{loss_before_val:,.0f}</div>
                </div>
                <div>
                    <div style="font-size: 0.68rem; color: #64748b;">Loss After</div>
                    <div style="font-size: 0.85rem; font-weight: 600; color: #059669;">₹{loss_after_val:,.0f}</div>
                </div>
                <div>
                    <div style="font-size: 0.68rem; color: #64748b;">Loss Reduction</div>
                    <div style="font-size: 0.85rem; font-weight: 700; color: #059669;">₹{loss_reduction:,.0f}</div>
                </div>
                <div>
                    <div style="font-size: 0.68rem; color: #64748b;">Est. Recovery</div>
                    <div style="font-size: 0.85rem; font-weight: 700; color: #0284c7;">₹{est_val:,.0f}*</div>
                </div>
            </div>
            <div style="font-size: 0.7rem; color: #94a3b8; margin-top: 6px;">*Simulated counterfactual projection</div>
        </div>

        <!-- Right: KEY FACTORS -->
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px;">
            <div style="font-size: 0.72rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">
                KEY FACTORS
            </div>
            <div style="display: flex; flex-direction: column; gap: 6px;">
                {key_factors_html}
            </div>
        </div>
    </div>

    <!-- 2-COLUMN: ALTERNATIVES + SAFETY DECISION -->
    <div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 16px;">
        <!-- Left: ALTERNATIVES CONSIDERED -->
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px;">
            <div style="font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">
                ALTERNATIVES CONSIDERED
            </div>
            <div style="display: flex; flex-direction: column; gap: 4px;">
                {alternatives_html}
            </div>
        </div>

        <!-- Right: 🛡 SAFETY DECISION -->
        <div style="background: {safety_bg}; border: 1px solid {safety_border}; border-radius: 8px; padding: 14px;">
            <div style="font-size: 0.72rem; font-weight: 700; color: {safety_header_color}; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                🛡 SAFETY DECISION
            </div>
            <div style="font-size: 1.05rem; font-weight: 800; color: {safety_title_color}; margin-bottom: 4px;">
                {safety_badge_text}
            </div>
            <div style="font-size: 0.82rem; font-weight: 600; color: #334155; margin-bottom: 6px;">
                Human review: {safety_review_text}
            </div>
            <div style="font-size: 0.76rem; color: #475569; line-height: 1.4; margin-bottom: 6px;">
                {effective_safety.reason}
            </div>
            <div style="font-size: 0.74rem; font-weight: 700; color: {safety_title_color};">
                Recovery Execution: {'EXECUTED (SIMULATED)' if effective_safety.allowed else 'NOT EXECUTED'}
            </div>
        </div>
    </div>
</div>
"""
    clean_html_card = "\n".join(line.lstrip() for line in html_card.splitlines()).strip()
    st.markdown(clean_html_card, unsafe_allow_html=True)

    if recovery:
        st.markdown("**Route Performance Comparison**")
        comp_df = pd.DataFrame(
            [
                {
                    "Route": f"{payment_method} + {affected_bank} + {device_type} (Affected)",
                    "Success Rate": f"{incident_success:.2f}%",
                    "Baseline": f"{baseline_success:.2f}%",
                    "Degradation": f"-{degradation:.2f} pp",
                    "Role": "Underperforming Route",
                },
                {
                    "Route": f"{payment_method} + {recovery['alternative_bank']} + {device_type} (Recommended)",
                    "Success Rate": f"{recovery['alternative_success_rate'] * 100:.2f}%",
                    "Baseline": f"{baseline_success:.2f}%",
                    "Degradation": f"+{recovery.get('improvement', (recovery['alternative_success_rate'] - incident['success_rate'])) * 100:.2f} pp",
                    "Role": "Alternative Target",
                },
            ]
        )
        st.dataframe(comp_df, use_container_width=True, hide_index=True)

    # =========================================
    # SECTION 3 — SAFETY CONTROL
    # =========================================

    st.markdown('<div id="safety-control"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">🛡️ Safety Control</div>',
        unsafe_allow_html=True,
    )

    safety_col, demo_auth_col = st.columns(2)

    decision_status = policy_result.get("decision", safety.action)

    with safety_col:
        if decision_status == "RECOVER":
            s_class = "safety-card-safe"
            s_badge = '<span class="pill-green">SAFE</span>'
        elif decision_status == "ESCALATE":
            s_class = "safety-card-review"
            s_badge = '<span class="pill-amber">HUMAN REVIEW REQUIRED</span>'
        elif decision_status == "ROLLBACK":
            s_class = "safety-card-stop"
            s_badge = '<span class="pill-red">ROLLBACK</span>'
        else:
            s_class = "safety-card-stop"
            s_badge = '<span class="pill-red">STOP</span>'

        st.markdown(
            f"""
            <div class="{s_class}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-size: 0.78rem; font-weight: 700; color: #475569; text-transform: uppercase;">
                        Production Safety Decision
                    </div>
                    {s_badge}
                </div>
                <div style="font-size: 1.15rem; font-weight: 700; color: #0f172a; margin-bottom: 8px;">
                    {safety.action}
                </div>
                <div style="font-size: 0.85rem; color: #475569; line-height: 1.45; margin-bottom: 10px;">
                    {policy_result.get('reason', safety.reason)}
                </div>
                <div style="font-size: 0.76rem; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 8px;">
                    Automated execution is controlled by deterministic safety policies.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with demo_auth_col:
        st.markdown(
            """
            <div class="fintech-card" style="border: 1px solid #bae6fd; background: #f0f9ff;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-size: 0.78rem; font-weight: 700; color: #0369a1; text-transform: uppercase;">
                        Simulation Authorization
                    </div>
                    <span class="pill-blue">DEMO ONLY</span>
                </div>
                <div style="font-size: 0.95rem; font-weight: 600; color: #0f172a; margin-bottom: 6px;">
                    Operator Authorization for Bounded Recovery Simulation
                </div>
                <div style="font-size: 0.82rem; color: #475569; line-height: 1.4; margin-bottom: 12px;">
                    Demo-only authorization for bounded recovery simulation. Does NOT authorize real payment execution.
                </div>
            """,
            unsafe_allow_html=True,
        )

        human_auth_confirmed = False
        if decision_status == "ESCALATE":
            human_auth_confirmed = st.checkbox(
                "Authorize Bounded Recovery Simulation",
                key="human_operator_simulation_auth",
                help="Demo authorization for simulation. Production safety remains strictly recorded as HUMAN REVIEW REQUIRED in the audit log.",
            )
            if human_auth_confirmed:
                st.caption(
                    "✔ Demo authorization active for bounded recovery simulation."
                )
            else:
                st.caption(
                    "Operator authorization required to simulate bounded recovery."
                )
        else:
            st.caption("Human escalation not required for this scenario.")

        st.markdown("</div>", unsafe_allow_html=True)

    # =========================================
    # SECTION 4 — RECOVERY CONTROL
    # =========================================

    st.markdown('<div id="recovery-control"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">⚡ Recovery Control</div>',
        unsafe_allow_html=True,
    )

    stage_dec = (
        f'<span class="pill-green">✔ {intelligence_decision.recommended_action}</span>'
    )
    if safety.requires_human_review:
        stage_safe = '<span class="pill-amber">! HUMAN REVIEW</span>'
    elif safety.allowed:
        stage_safe = '<span class="pill-green">✔ SAFE</span>'
    else:
        stage_safe = '<span class="pill-red">✖ BLOCKED</span>'

    batch_result = st.session_state.get("batch_result")

    canary_status = (
        batch_result.get("canary_decision", "PENDING")
        if batch_result
        else "PENDING"
    )
    if canary_status == "EXPAND":
        stage_canary = '<span class="pill-green">✔ EXPAND</span>'
    elif canary_status in ("STOP", "ESCALATE"):
        stage_canary = f'<span class="pill-amber">! {canary_status}</span>'
    elif canary_status == "BLOCKED":
        stage_canary = '<span class="pill-red">✖ BLOCKED</span>'
    else:
        stage_canary = '<span class="pill-blue">⚙ PENDING</span>'

    guardrail_status = (
        batch_result.get("guardrail_decision", "PENDING")
        if batch_result
        else "PENDING"
    )
    if guardrail_status == "CONTINUE":
        stage_guard = '<span class="pill-green">✔ CONTINUE</span>'
    elif guardrail_status == "ROLLBACK":
        stage_guard = '<span class="pill-red">↩️ ROLLBACK</span>'
    elif guardrail_status == "STOP":
        stage_guard = '<span class="pill-red">✖ STOP</span>'
    else:
        stage_guard = '<span class="pill-blue">⚙ PENDING</span>'

    outcome_status = (
        batch_result.get("final_status", "PENDING")
        if batch_result
        else "PENDING"
    )
    if outcome_status in ("RECOVERED", "COMPLETED"):
        stage_out = '<span class="pill-green">✔ RECOVERED</span>'
    elif outcome_status == "BLOCKED":
        stage_out = '<span class="pill-red">✖ BLOCKED</span>'
    else:
        stage_out = f'<span class="pill-blue">⚙ {outcome_status}</span>'

    st.markdown(
        f"""
        <div class="lifecycle-wrapper">
            <div class="lifecycle-node">
                <div class="lifecycle-node-label">Decision</div>
                <div>{stage_dec}</div>
            </div>
            <div class="lifecycle-arrow">→</div>
            <div class="lifecycle-node">
                <div class="lifecycle-node-label">Safety Gate</div>
                <div>{stage_safe}</div>
            </div>
            <div class="lifecycle-arrow">→</div>
            <div class="lifecycle-node">
                <div class="lifecycle-node-label">Canary</div>
                <div>{stage_canary}</div>
            </div>
            <div class="lifecycle-arrow">→</div>
            <div class="lifecycle-node">
                <div class="lifecycle-node-label">Guardrail</div>
                <div>{stage_guard}</div>
            </div>
            <div class="lifecycle-arrow">→</div>
            <div class="lifecycle-node">
                <div class="lifecycle-node-label">Outcome</div>
                <div>{stage_out}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    run_sim = False
    sim_human_approved = False

    if decision_status == "RECOVER":
        if st.button(
            "🚀 Simulate Approved Batch Recovery",
            type="primary",
            use_container_width=True,
        ):
            run_sim = True
            sim_human_approved = False
    elif decision_status == "ESCALATE":
        if human_auth_confirmed:
            if st.button(
                "🚀 Simulate Human-Approved Bounded Recovery",
                type="primary",
                use_container_width=True,
            ):
                run_sim = True
                sim_human_approved = True
        else:
            st.button(
                "🔒 Human Review Required (Authorize in Safety Panel)",
                disabled=True,
                use_container_width=True,
            )
    elif decision_status == "ROLLBACK":
        st.markdown(
            """
            <div style="background: #fef2f2; border: 1px solid #fecaca; padding: 10px; border-radius: 8px; font-size: 0.82rem; color: #991b1b; margin-bottom: 10px;">
                <b>Guardrail Alert:</b> Alternative route post-recovery rate <b>88.39% &lt; 91.00%</b>. <b>ROLLBACK REQUIRED</b>.
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "🔄 Simulate Active Recovery (Rollback Test)",
            type="primary",
            use_container_width=True,
        ):
            run_sim = True
            sim_human_approved = True
    elif decision_status == "STOP":
        st.caption(
            "Degradation is below the 5.0 pp threshold. Safety controller blocks automated route intervention."
        )
        if st.button(
            "🔒 Verify Bounded Safety Gate (Simulate Blocked)",
            use_container_width=True,
        ):
            run_sim = True
            sim_human_approved = False
    else:
        st.success("🟢 Route Operating Normally. No recovery required.")

    if run_sim:
        with st.spinner("Executing bounded canary simulation through orchestrator..."):
            try:
                batch_result = execute_orchestrated_batch_recovery(
                    transactions=transactions,
                    incident=incident,
                    decision=intelligence_result.decision,
                    safety=safety,
                    recovery=recovery,
                    payment_method=payment_method,
                    affected_bank=affected_bank,
                    device_type=device_type,
                    batch_size=50,
                    human_approved=sim_human_approved,
                )
                st.session_state["batch_result"] = batch_result
            except Exception as e:
                st.error(f"Simulation failed: {e}")

    batch_result = st.session_state.get("batch_result")

    # -------------------------------------------------------------
    # Authoritative Financial Summary
    # -------------------------------------------------------------
    rev_at_risk = float(impact["revenue_at_risk"]) if impact else 0.0
    est_recoverable = (
        float(intelligence_decision.estimated_value)
        if intelligence_decision
        else 0.0
    )

    if transactions is not None and incident is not None:
        inc_txns = transactions[
            transactions["payment_method"].eq(payment_method)
            & transactions["bank"].eq(affected_bank)
            & transactions["device_type"].eq(device_type)
            & transactions["status"].eq("FAILED")
        ].head(50)
        calc_eligible_amount = float(inc_txns["amount"].sum())
        calc_eligible_count = len(inc_txns)
    else:
        calc_eligible_amount = 0.0
        calc_eligible_count = 0

    fin_summary = calculate_financial_summary(
        revenue_at_risk=rev_at_risk,
        eligible_amount=(
            batch_result.get("eligible_amount", calc_eligible_amount)
            if batch_result
            else calc_eligible_amount
        ),
        batch_result=batch_result,
    )

    st.markdown("---")
    st.markdown("### 💰 Financial Impact & Recovery Economics")
    st.caption(
        "Authoritative progression: Revenue at Risk → Eligible Amount → Attempted Amount → Gross Recovered → Execution Cost → NET RECOVERED → Recovery Rate → Recovery ROI"
    )

    # 1. PRE-EXECUTION: FINANCIAL IMPACT
    st.markdown("#### 1️⃣ Pre-Execution: Quantified Financial Risk")
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        st.metric(
            "Revenue at Risk",
            f"₹{fin_summary.revenue_at_risk:,.2f}",
            delta=f"-{impact['excess_failures']:.0f} excess failures" if impact else None,
            delta_color="inverse",
            help="Business revenue at risk estimated before recovery by IncidentRevenueCalculator.",
        )
    with f_col2:
        st.metric(
            "Estimated Recoverable Value",
            f"₹{est_recoverable:,.2f}",
            help="Theoretical counterfactual recovery potential projected by IncidentDecisionEngine.",
        )
        st.caption("THEORETICAL / COUNTERFACTUAL")
    with f_col3:
        eligible_count = (
            batch_result.get("eligible_transactions", calc_eligible_count)
            if batch_result
            else calc_eligible_count
        )
        st.metric(
            "Eligible Batch Amount",
            f"₹{fin_summary.eligible_amount:,.2f}",
            delta=f"{eligible_count} transactions",
            delta_color="off",
            help="Total monetary value of failed transactions eligible for bounded recovery batch.",
        )

    # 2. POST-EXECUTION: BOUNDED RECOVERY RESULT
    st.markdown("#### 2️⃣ Post-Execution: Bounded Recovery Result")
    r_col1, r_col2, r_col3, r_col4 = st.columns(4)

    if fin_summary.has_executed and batch_result:
        with r_col1:
            st.metric(
                "Attempted Amount",
                f"₹{fin_summary.attempted_amount:,.2f}",
                delta=f"{batch_result.get('attempted_transactions', 0)} canary txns",
                delta_color="off",
                help="Actual monetary value of transactions attempted by BoundedRecoveryExecutor.",
            )
        with r_col2:
            st.metric(
                "Gross Recovered",
                f"₹{fin_summary.recovered_amount:,.2f}",
                delta=f"+{batch_result.get('recovered_transactions', 0)} recovered",
                help="Actual monetary value of successfully recovered transactions.",
            )
            st.caption("SIMULATED")
        with r_col3:
            st.metric(
                "Execution Cost",
                f"₹{fin_summary.execution_cost:,.2f}",
                delta=f"{batch_result.get('attempted_transactions', 0)} × ₹25",
                delta_color="inverse",
                help="Actual execution cost incurred by bounded canary simulation.",
            )
        with r_col4:
            st.metric(
                "NET RECOVERED",
                f"₹{fin_summary.net_recovered_value:,.2f}",
                delta=f"₹{fin_summary.net_recovered_value:,.2f} net",
                help="Authoritative net recovered value (Gross Recovered minus Execution Cost).",
            )
            st.caption("SIMULATED")
    else:
        with r_col1:
            st.metric("Attempted Amount", "Not executed")
        with r_col2:
            st.metric("Gross Recovered", "Not executed")
        with r_col3:
            st.metric("Execution Cost", "Not executed")
        with r_col4:
            st.metric("NET RECOVERED", "Not executed")
        st.info(
            "ℹ️ Post-execution recovery metrics become available after executing bounded recovery simulation above."
        )

    # 3. PERFORMANCE & ROI
    st.markdown("#### 3️⃣ Performance & Recovery ROI")
    p_col1, p_col2, p_col3, p_col4, p_col5 = st.columns(5)

    if fin_summary.has_executed and batch_result:
        with p_col1:
            st.metric(
                "Recovery Rate",
                f"{fin_summary.recovery_rate * 100:.2f}%",
                help="Proportion of attempted recovery transactions that succeeded.",
            )
        with p_col2:
            st.metric(
                "Recovery ROI",
                fin_summary.roi_display,
                help="Net Recovered Value divided by Execution Cost. N/A if execution cost is zero.",
            )
        with p_col3:
            st.metric(
                "Canary",
                batch_result.get("canary_decision", "NOT_APPLICABLE"),
                help="Bounded canary evaluation result.",
            )
        with p_col4:
            st.metric(
                "Guardrail",
                batch_result.get("guardrail_decision", "NOT_RECORDED"),
                help="Circuit breaker guardrail decision for route safety.",
            )
        with p_col5:
            is_rb = batch_result.get("rollback_required", False)
            st.metric(
                "Rollback",
                "TRIGGERED" if is_rb else "NONE",
                delta="Reversed" if is_rb else "Safe",
                delta_color="inverse" if is_rb else "normal",
                help="Circuit breaker rollback status.",
            )
    else:
        with p_col1:
            st.metric("Recovery Rate", "Not executed")
        with p_col2:
            st.metric("Recovery ROI", "N/A")
        with p_col3:
            st.metric("Canary", "PENDING")
        with p_col4:
            st.metric("Guardrail", "PENDING")
        with p_col5:
            st.metric("Rollback", "NONE")


    # =========================================
    # SECTION 5 — LIVE OPERATIONS & EVENT SIMULATOR
    # =========================================

    st.markdown('<div id="live-operations"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">📡 Live Payment Operations & Event Stream</div>',
        unsafe_allow_html=True,
    )

    # Initialize / retrieve live simulator instance
    if "live_simulator" not in st.session_state:
        st.session_state["live_simulator"] = LivePaymentSimulator(
            scenario_name=scenario_name
        )
    sim = st.session_state["live_simulator"]
    if sim.scenario_name != scenario_name:
        sim.set_scenario(scenario_name)

    # Top summary telemetry
    if live_report:
        lr1, lr2, lr3, lr4, lr5 = st.columns(5)
        with lr1:
            st.metric("Total Routes", f"{live_report.get('routes_monitored', 60)}")
        with lr2:
            st.metric("Healthy", f"{live_report.get('healthy_routes', 55)}")
        with lr3:
            st.metric("Watch", f"{live_report.get('degraded_routes', 5)}")
        with lr4:
            st.metric("Critical", f"{live_report.get('critical_routes', 0)}")
        with lr5:
            st.metric(
                "System Success",
                f"{live_report.get('overall_success_rate', 0.0) * 100:.2f}%",
            )

    # 1. LIVE SIMULATION CONTROLS & DEMO MODES
    st.markdown(
        """
        <div class="fintech-card" style="margin-top: 14px; margin-bottom: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="font-size: 0.85rem; font-weight: 700; color: #0f172a; text-transform: uppercase;">
                    🎛️ Live Simulation Controls
                </div>
                <span class="pill-blue">SIMULATED LIVE EVENTS · DEMO ONLY</span>
            </div>
            <div style="font-size: 0.82rem; color: #64748b; margin-bottom: 12px;">
                Demonstrate continuous event-driven payment telemetry, webhook normalization, and automated recovery response.
            </div>
        """,
        unsafe_allow_html=True,
    )

    sim_ctrl1, sim_ctrl2, sim_ctrl3, sim_ctrl4 = st.columns([1.5, 1.2, 1.2, 1.5])

    with sim_ctrl1:
        step_rate = st.selectbox(
            "Event Ingestion Rate",
            [
                "Normal (5 events/step)",
                "Slow (1 event/step)",
                "Fast (15 events/step)",
            ],
            index=0,
            help="Simulates payment event arrival rate from payment gateway",
        )
        batch_n = (
            5
            if "Normal" in step_rate
            else (1 if "Slow" in step_rate else 15)
        )

    with sim_ctrl2:
        st.write("")
        st.write("")
        if st.button("▶ Stream Events", type="primary", use_container_width=True):
            sim.step(count=batch_n)
            st.rerun()

    with sim_ctrl3:
        st.write("")
        st.write("")
        if st.button("⏸ Pause Stream", use_container_width=True):
            sim.pause()
            st.info("Event stream paused.")

    with sim_ctrl4:
        st.write("")
        st.write("")
        if st.button("↻ Reset Stream", use_container_width=True):
            sim.reset()
            st.session_state["batch_result"] = None
            st.session_state["evaluation_scorecard"] = None
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # 2. WEBHOOK INGESTION PIPELINE VISUALIZATION
    st.markdown(
        f"""
        <div class="lifecycle-wrapper" style="margin-bottom: 16px;">
            <div class="lifecycle-node">
                <div class="lifecycle-node-label">Webhook Ingestion</div>
                <div><span class="pill-green">✔ WEBHOOK RECEIVED</span></div>
                <div style="font-size: 0.70rem; color: #64748b; margin-top: 4px;">{sim.last_pipeline_status['last_event_id'] or 'PAY_10480'}</div>
            </div>
            <div class="lifecycle-arrow">→</div>
            <div class="lifecycle-node">
                <div class="lifecycle-node-label">Normalization</div>
                <div><span class="pill-green">✔ EVENT NORMALIZED</span></div>
                <div style="font-size: 0.70rem; color: #64748b; margin-top: 4px;">{sim.last_pipeline_status['last_event_type'] or 'payment.captured'}</div>
            </div>
            <div class="lifecycle-arrow">→</div>
            <div class="lifecycle-node">
                <div class="lifecycle-node-label">Telemetry Engine</div>
                <div><span class="pill-green">✔ STATS UPDATED</span></div>
                <div style="font-size: 0.70rem; color: #64748b; margin-top: 4px;">{sim.webhook_count} events ingested</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3. REAL-TIME ROUTE HEALTH
    st.markdown("**Real-Time Route Telemetry**")
    r_cols = st.columns(4)
    for idx, (rk, rt) in enumerate(sim.routes.items()):
        with r_cols[idx % 4]:
            if rt.status == "CRITICAL":
                card_style = "border: 1px solid #fecaca; background: #fef2f2;"
                pill = '<span class="pill-red">CRITICAL</span>'
            elif rt.status == "WATCH":
                card_style = "border: 1px solid #fde68a; background: #fffbeb;"
                pill = '<span class="pill-amber">WATCH</span>'
            else:
                card_style = "border: 1px solid #e2e8f0; background: #ffffff;"
                pill = '<span class="pill-green">HEALTHY</span>'

            success_color = (
                "#dc2626" if rt.degradation_pp >= 5 else "#059669"
            )

            st.markdown(
                f"""
                <div class="fintech-card" style="{card_style} padding: 12px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <div style="font-size: 0.70rem; font-weight: 700; color: #64748b;">{rt.payment_method} · {rt.device}</div>
                        {pill}
                    </div>
                    <div style="font-size: 0.95rem; font-weight: 700; color: #0f172a; margin-bottom: 8px;">
                        {rt.bank}
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.78rem;">
                        <span style="color: #64748b;">Success:</span>
                        <span style="font-weight: 700; color: {success_color};">{rt.success_rate * 100:.2f}%</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.78rem;">
                        <span style="color: #64748b;">Txns / Fails:</span>
                        <span style="font-weight: 600;">{rt.transactions:,} / {rt.failures:,}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 4. LIVE INCIDENT DETECTION & AI ROUTING DECISION
    inc_det = sim.get_incident_detection()
    ai_dec = sim.get_ai_decision()
    safety_g = sim.get_safety_gate()

    if inc_det:
        st.markdown(
            f"""
            <div class="incident-card-critical" style="margin-top: 10px; margin-bottom: 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div style="font-size: 0.80rem; font-weight: 700; color: #dc2626; text-transform: uppercase;">
                        ⚠ Route Degradation Detected
                    </div>
                    <span class="pill-red">SEVERITY: {inc_det['severity']}</span>
                </div>
                <div style="font-size: 1.15rem; font-weight: 700; color: #0f172a; margin-bottom: 10px;">
                    {inc_det['route']} dropped to {inc_det['current_success_rate'] * 100:.2f}% (Baseline: {inc_det['baseline_success_rate'] * 100:.2f}%)
                </div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; border-top: 1px solid #fee2e2; padding-top: 8px;">
                    <div><span style="font-size: 0.72rem; color: #64748b;">Degradation:</span><br><b style="color: #dc2626;">-{inc_det['degradation_pp']:.2f} pp</b></div>
                    <div><span style="font-size: 0.72rem; color: #64748b;">Failed Txns:</span><br><b>{inc_det['failed_transactions']:,}</b></div>
                    <div><span style="font-size: 0.72rem; color: #64748b;">Excess Failures:</span><br><b>{inc_det['excess_failures']:.1f}</b></div>
                    <div><span style="font-size: 0.72rem; color: #64748b;">Revenue at Risk:</span><br><b style="color: #dc2626;">₹{inc_det['revenue_at_risk']:,.0f}</b></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        sim_dec1, sim_dec2 = st.columns(2)
        with sim_dec1:
            st.markdown(
                f"""
                <div class="decision-card" style="height: 100%;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <div style="font-size: 0.75rem; font-weight: 700; color: #0284c7; text-transform: uppercase;">
                            AI Routing Decision
                        </div>
                        <span class="pill-blue">CONFIDENCE: {ai_dec['confidence'] * 100:.0f}%</span>
                    </div>
                    <div style="font-size: 1.05rem; font-weight: 700; color: #0f172a; margin-bottom: 8px;">
                        {ai_dec['recommended_action']}
                    </div>
                    <div style="font-size: 0.80rem; color: #475569; margin-bottom: 10px;">
                        {ai_dec['explanation']}
                    </div>
                    <div style="font-size: 0.75rem; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 6px;">
                        Expected Loss: ₹{ai_dec['expected_loss_before']:,.0f} → ₹{ai_dec['expected_loss_after']:,.0f}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with sim_dec2:
            auth_status = (
                "✔ Simulation authorized by operator"
                if sim.operator_authorized
                else "Operator authorization required to simulate bounded routing"
            )
            st.markdown(
                f"""
                <div class="fintech-card" style="height: 100%; border: 1px solid #bae6fd; background: #f0f9ff;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <div style="font-size: 0.75rem; font-weight: 700; color: #0369a1; text-transform: uppercase;">
                            Live Route Switch Simulation
                        </div>
                        <span class="pill-blue">COUNTERFACTUAL / DEMO ONLY</span>
                    </div>
                    <div style="font-size: 0.95rem; font-weight: 600; color: #0f172a; margin-bottom: 8px;">
                        Bank_X (DEGRADED) → Bank_A (HEALTHY)
                    </div>
                    <div style="font-size: 0.80rem; color: #475569; margin-bottom: 10px;">
                        Production Safety: <b>{safety_g['production_safety']}</b><br>
                        {safety_g['reason']}
                    </div>
                    <div style="font-size: 0.75rem; color: #0369a1; border-top: 1px solid #bae6fd; padding-top: 6px;">
                        {auth_status}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.success(
            "🟢 All monitored routes operating normally within baseline guardrails. No degradation detected."
        )

    # 5. LIVE PAYMENT EVENT STREAM PANEL
    st.markdown("**Live Payment Event Stream**")
    st.caption(
        "Continuous simulated incoming transaction feed. Labeled: SIMULATED LIVE EVENTS."
    )

    df_events = sim.get_events_dataframe()
    if not df_events.empty:
        st.dataframe(
            df_events.head(15),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No events in buffer. Click 'Stream Events' to start ingestion.")

    # 6. SIMULATED AUDIT LIFECYCLE TRACKER
    if sim.lifecycle_log:
        with st.expander("📋 Live Event Ingestion & Recovery Lifecycle Audit", expanded=False):
            st.markdown(
                """
                <div class="timeline-track" style="margin-top: 8px;">
                """,
                unsafe_allow_html=True,
            )
            for item in sim.lifecycle_log[:8]:
                st.markdown(
                    f"""
                    <div class="timeline-step">
                        <div class="timeline-marker timeline-marker-success"></div>
                        <div style="font-weight: 600; font-size: 0.82rem; color: #0f172a;">{item['time']} · {item['step']}</div>
                        <div style="font-size: 0.74rem; color: #64748b;">{item['detail']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

    # Monitored Route Health Table from live report
    with st.expander("📊 Full Monitored Route Health Directory (60 Routes)", expanded=False):
        rh_data = live_report.get("route_health", [])
        if rh_data:
            df_rh = pd.DataFrame(rh_data)
            rh_cols = [
                c
                for c in [
                    "route",
                    "transactions",
                    "failures",
                    "success_rate",
                    "degradation_pp",
                    "severity",
                ]
                if c in df_rh.columns
            ]
            df_rh_disp = df_rh[rh_cols].copy()
            if "success_rate" in df_rh_disp.columns:
                df_rh_disp["success_rate"] = df_rh_disp[
                    "success_rate"
                ].apply(lambda v: f"{v * 100:.2f}%")
            if "degradation_pp" in df_rh_disp.columns:
                df_rh_disp["degradation_pp"] = df_rh_disp[
                    "degradation_pp"
                ].apply(lambda v: f"{v:.2f}")

            df_rh_disp = df_rh_disp.rename(
                columns={
                    "route": "Route",
                    "transactions": "Transactions",
                    "failures": "Failures",
                    "success_rate": "Success Rate",
                    "degradation_pp": "Degradation (pp)",
                    "severity": "Severity",
                }
            )
            st.dataframe(df_rh_disp, use_container_width=True, hide_index=True)


    # =========================================
    # SECTION 6 — RECOVERY LEARNING (CLOSED-LOOP INTELLIGENCE)
    # =========================================

    st.markdown('<div id="recovery-learning"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">🧠 Recovery Learning</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Closed-loop Bayesian route intelligence. Verified recovery evidence updates route confidence "
        "to continuously adapt future routing decisions. "
        "Mechanism: Verified evidence accumulation + Bayesian route scoring (no ML model retraining)."
    )

    try:
        demo_res = st.session_state.get("demo_run_result")
        batch_res = st.session_state.get("batch_result")

        # Resolve active candidate routes and verified learning context
        if demo_res is not None and getattr(demo_res, "scenario", None) is not None:
            active_candidates = demo_res.scenario.route_candidates
            active_learning_ctx = (
                demo_res.learning_evidence
                or (batch_res.get("learning_stats") if batch_res else None)
                or st.session_state.get("learning_history")
                or PersistentLearningHistory()
            )
            active_target_route = demo_res.scenario.target_route
        elif batch_res is not None and batch_res.get("learning_stats") is not None:
            active_candidates = route_candidates if route_candidates else DEFAULT_DEMO_CANDIDATES
            active_learning_ctx = batch_res.get("learning_stats")
            active_target_route = getattr(batch_res["learning_stats"], "route", None)
        else:
            active_candidates = route_candidates if route_candidates else DEFAULT_DEMO_CANDIDATES
            active_learning_ctx = st.session_state.get("learning_history") or PersistentLearningHistory()
            active_target_route = None

        learning_view: LearningComparisonView = build_learning_comparison(
            route_candidates=active_candidates,
            learning_context=active_learning_ctx,
            target_route=active_target_route,
        )

        # 1. Closed-Loop Lifecycle Stepper Flow
        st.markdown(
            """
            <div style="display: flex; align-items: center; justify-content: space-between; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 16px; margin-bottom: 16px; font-size: 0.8rem; font-weight: 600; color: #475569;">
                <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="background: #e2e8f0; color: #334155; border-radius: 50%; width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center; font-size: 0.7rem;">1</span>
                    <span>Before Recovery (Baseline)</span>
                </div>
                <span style="color: #94a3b8;">→</span>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="background: #dbeafe; color: #1e40af; border-radius: 50%; width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center; font-size: 0.7rem;">2</span>
                    <span>Verified Recovery Evidence</span>
                </div>
                <span style="color: #94a3b8;">→</span>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="background: #e0e7ff; color: #4338ca; border-radius: 50%; width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center; font-size: 0.7rem;">3</span>
                    <span>Route Score Update</span>
                </div>
                <span style="color: #94a3b8;">→</span>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="background: #dcfce7; color: #166534; border-radius: 50%; width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center; font-size: 0.7rem;">4</span>
                    <span>Next Decision (Adapted)</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 2. Executive KPI Cards
        l_col1, l_col2, l_col3, l_col4 = st.columns(4)
        with l_col1:
            if learning_view.has_learning_evidence:
                st.metric(
                    "Verified Evidence",
                    f"{learning_view.total_learned_recoveries:,} / {learning_view.total_learned_attempts:,}",
                    delta=f"{learning_view.overall_recovery_rate * 100:.1f}% recovery rate",
                    delta_color="normal",
                    help="Recoveries verified by RecoveryOutcomeVerifier over bounded canary attempts.",
                )
            else:
                st.metric(
                    "Verified Evidence",
                    "0 / 0",
                    delta="Awaiting execution",
                    delta_color="off",
                    help="No verified recovery evidence recorded yet.",
                )
            st.caption(f"**{learning_view.learning_provenance}** • Verified recovery outcomes")

        with l_col2:
            if learning_view.has_learning_evidence:
                st.metric(
                    "Evidence Confidence",
                    f"{learning_view.mean_evidence_confidence * 100:.1f}%",
                    delta="Bayesian weight",
                    delta_color="normal",
                    help="Confidence weight calculated from sample size and outcome consistency.",
                )
            else:
                st.metric(
                    "Evidence Confidence",
                    "N/A",
                    delta="No samples",
                    delta_color="off",
                    help="Awaiting verified recovery evidence.",
                )
            st.caption(f"**{learning_view.learning_provenance}** • Evidence reliability weight")

        with l_col3:
            st.metric(
                "Learning Score Lift",
                learning_view.learning_score_lift_value,
                delta="Bayesian route update" if learning_view.has_learning_evidence else "No lift measured",
                delta_color="normal" if learning_view.has_learning_evidence and "+" in learning_view.learning_score_lift_value else "off",
                help="Route score adjustment derived from verified recovery evidence.",
            )
            st.caption(f"**{learning_view.learning_provenance}** • Route score lift")

        with l_col4:
            adapt_pill = (
                "pill-green" if learning_view.preferred_route_changed
                else ("pill-blue" if learning_view.has_learning_evidence else "pill-amber")
            )
            st.markdown(
                f"""
                <div style="padding-top: 4px;">
                    <div style="font-size: 0.8rem; color: #64748b; margin-bottom: 6px;">DECISION ADAPTATION</div>
                    <div><span class="{adapt_pill}" style="font-size: 0.8rem; font-weight: 700;">{learning_view.adaptation_status}</span></div>
                    <div style="font-size: 0.72rem; color: #64748b; margin-top: 6px;">**GOVERNED** • {learning_view.adaptation_summary}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Filter to relevant routes if route list is long
        display_comparisons = learning_view.route_comparisons
        if len(display_comparisons) > 5:
            # Prioritize: top after, top before, target route, and route with highest delta
            relevant_routes = {
                learning_view.top_route_before,
                learning_view.top_route_after,
            }
            if active_target_route:
                relevant_routes.add(active_target_route)
            # Add route with highest score delta
            max_delta_item = max(display_comparisons, key=lambda x: abs(x.score_delta), default=None)
            if max_delta_item:
                relevant_routes.add(max_delta_item.route)
            # Filter and supplement up to 4 routes
            filtered = [c for c in display_comparisons if c.route in relevant_routes]
            for c in display_comparisons:
                if len(filtered) >= 4:
                    break
                if c not in filtered:
                    filtered.append(c)
            display_comparisons = filtered

        # 3. Before / After Route Ranking Comparison
        st.markdown(
            """
            <div style="font-size: 0.85rem; font-weight: 700; color: #334155; margin-top: 14px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em;">
                Route Ranking: Before vs After Verified Recovery Evidence
            </div>
            """,
            unsafe_allow_html=True,
        )

        r_col1, r_col2 = st.columns(2)

        with r_col1:
            st.markdown(
                """
                <div class="fintech-card" style="height: 100%;">
                    <div style="font-size: 0.78rem; font-weight: 700; color: #64748b; margin-bottom: 8px;">
                        BEFORE LEARNING (BASELINE OBSERVED)
                    </div>
                """,
                unsafe_allow_html=True,
            )
            before_sorted = sorted(display_comparisons, key=lambda x: x.rank_before)
            for item in before_sorted:
                pref_badge = ' <span class="pill-blue" style="font-size: 0.68rem;">PREFERRED</span>' if item.is_preferred_before else ""
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #f1f5f9; font-size: 0.78rem;">
                        <div>
                            <strong>{item.rank_before}.</strong> {item.route}{pref_badge}
                        </div>
                        <div style="font-family: monospace; color: #475569; font-weight: 600;">
                            {item.score_before:.4f}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        with r_col2:
            st.markdown(
                """
                <div class="fintech-card" style="height: 100%;">
                    <div style="font-size: 0.78rem; font-weight: 700; color: #1e40af; margin-bottom: 8px;">
                        AFTER VERIFIED RECOVERY EVIDENCE
                    </div>
                """,
                unsafe_allow_html=True,
            )
            after_sorted = sorted(display_comparisons, key=lambda x: x.rank_after)
            for item in after_sorted:
                pref_badge = ' <span class="pill-green" style="font-size: 0.68rem;">PREFERRED</span>' if item.is_preferred_after else ""
                delta_str = f" <span style='color: #16a34a; font-weight: 700;'>↑ ({item.score_delta:+.4f})</span>" if item.score_delta > 0 else (f" <span style='color: #dc2626;'>↓ ({item.score_delta:+.4f})</span>" if item.score_delta < 0 else "")
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #f1f5f9; font-size: 0.78rem;">
                        <div>
                            <strong>{item.rank_after}.</strong> {item.route}{pref_badge}
                        </div>
                        <div style="font-family: monospace; color: #1e293b; font-weight: 700;">
                            {item.score_after:.4f}{delta_str}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            if not learning_view.preferred_route_changed and learning_view.has_learning_evidence:
                st.caption("Verified recovery evidence recorded. Ranking unchanged.")
            st.markdown("</div>", unsafe_allow_html=True)

        # 4. Verified Recovery Evidence Comparison Table
        table_rows = []
        for item in display_comparisons:
            table_rows.append(
                {
                    "Route": item.route,
                    "Learned Attempts": item.learned_attempts,
                    "Learned Recoveries": item.learned_recoveries,
                    "Recovery Rate": f"{item.learned_recovery_rate * 100:.1f}%" if item.learned_attempts > 0 else "0.0%",
                    "Evidence Confidence": f"{item.evidence_confidence * 100:.1f}%" if item.learned_attempts > 0 else "0.0%",
                    "Score Before": f"{item.score_before:.4f}",
                    "Score After": f"{item.score_after:.4f}",
                    "Delta": f"{item.score_delta:+.4f}" if item.score_delta != 0 else "0.0000",
                }
            )
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

        # 5. Micro-Chart Visualization (Before → After Score Lift)
        with st.expander("📊 Route Score Visualization (Before → After Lift)", expanded=False):
            for item in display_comparisons:
                b_pct = min(100, max(0, int(item.score_before * 100)))
                a_pct = min(100, max(0, int(item.score_after * 100)))
                bar_color = "#16a34a" if item.score_delta > 0 else ("#dc2626" if item.score_delta < 0 else "#64748b")
                st.markdown(
                    f"""
                    <div style="margin-bottom: 10px;">
                        <div style="font-size: 0.78rem; font-weight: 600; color: #1e293b; margin-bottom: 2px;">{item.route}</div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 0.72rem; color: #64748b; width: 45px;">Before</span>
                            <div style="flex-grow: 1; background: #e2e8f0; border-radius: 4px; height: 8px; overflow: hidden;">
                                <div style="width: {b_pct}%; background: #94a3b8; height: 100%;"></div>
                            </div>
                            <span style="font-size: 0.72rem; font-family: monospace; color: #475569; width: 50px;">{item.score_before:.4f}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px; margin-top: 2px;">
                            <span style="font-size: 0.72rem; color: #64748b; width: 45px;">After</span>
                            <div style="flex-grow: 1; background: #e2e8f0; border-radius: 4px; height: 8px; overflow: hidden;">
                                <div style="width: {a_pct}%; background: {bar_color}; height: 100%;"></div>
                            </div>
                            <span style="font-size: 0.72rem; font-family: monospace; color: #0f172a; font-weight: 700; width: 50px;">{item.score_after:.4f}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # 6. Persistent Learning Store Expander (Strictly Read-Only)
        with st.expander("📁 Persistent Learning Store (recovery_learning.csv)", expanded=False):
            st.caption("Underlying persistent CSV record store. Strictly read-only.")
            try:
                raw_history = (st.session_state.get("learning_history") or PersistentLearningHistory()).load()
                if raw_history:
                    raw_rows = [
                        {
                            "Route": r.route,
                            "Attempts": r.attempts,
                            "Recoveries": r.recoveries,
                            "Recovery Rate": f"{r.recovery_rate * 100:.1f}%",
                            "Net Value": f"₹{r.net_recovered_value:,.2f}",
                            "Confidence": f"{r.evidence_confidence * 100:.1f}%",
                        }
                        for r in raw_history
                    ]
                    st.dataframe(pd.DataFrame(raw_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No persistent recovery records stored yet.")
            except Exception as e:
                st.warning(f"Could not load persistent learning records: {e}")

    except Exception as e:
        st.warning(f"Could not load recovery learning view: {e}")



    # =========================================
    # SECTION 7 — SYSTEM EVALUATION SCORECARD
    # =========================================

    st.markdown('<div id="system-evaluation"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">📈 System Evaluation Scorecard</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Authoritative evaluation metrics measured across incident intelligence, AI decision, deterministic safety, bounded recovery, and continuous learning pipelines."
    )

    eval_view = prepare_dashboard_evaluation_scorecard(
        incident=incident,
        decision=intelligence_decision if intelligence_result else None,
        safety_decision=safety if intelligence_result else None,
        batch_result=st.session_state.get("batch_result"),
        learning_history=st.session_state.get("learning_history"),
        revenue_impact=revenue_impact_obj if revenue_impact_obj else (impact["revenue_at_risk"] if impact else 0.0),
        eligible_amount=calc_eligible_amount,
        route_candidates=route_candidates,
    )
    st.session_state["evaluation_scorecard"] = eval_view.scorecard

    # Metric Row 1: Pre-Execution & Decision Projections
    ev_col1, ev_col2, ev_col3 = st.columns(3)
    with ev_col1:
        st.metric(
            "Incident Degradation",
            eval_view.degradation_value,
            delta=f"Severity: {eval_view.scorecard.severity}",
            delta_color="off",
            help="Observed route degradation against historical baseline.",
        )
        st.caption(f"**{eval_view.degradation_provenance}** • {eval_view.degradation_sub}")

    with ev_col2:
        st.metric(
            "Revenue at Risk",
            eval_view.revenue_at_risk_value,
            delta=f"-₹{eval_view.scorecard.revenue_at_risk:,.0f} counterfactual",
            delta_color="inverse",
            help="Theoretical counterfactual revenue exposure quantified by IncidentRevenueEngine.",
        )
        st.caption(f"**{eval_view.revenue_at_risk_provenance}** • Pre-intervention risk")

    with ev_col3:
        st.metric(
            "Expected Loss Reduction",
            eval_view.expected_loss_reduction_value,
            delta=f"₹{eval_view.scorecard.expected_loss_reduction:,.0f} mitigated",
            delta_color="normal",
            help="Theoretical expected loss reduction projected by IncidentDecisionEngine.",
        )
        st.caption(f"**{eval_view.expected_loss_reduction_provenance}** • {eval_view.expected_loss_reduction_sub}")

    # Metric Row 2: Bounded Execution Outcomes
    ev_col4, ev_col5, ev_col6 = st.columns(3)
    with ev_col4:
        st.metric(
            "Recovery Rate",
            eval_view.recovery_rate_value,
            delta=f"{eval_view.scorecard.successful_recoveries:,} recovered" if eval_view.has_executed else None,
            delta_color="normal",
            help="Simulated proportion of bounded canary recovery transactions that succeeded.",
        )
        st.caption(f"**{eval_view.recovery_rate_provenance}** • {eval_view.recovery_rate_sub}")

    with ev_col5:
        st.metric(
            "Net Recovered Value",
            eval_view.net_recovered_value,
            delta=f"₹{eval_view.scorecard.net_recovered_value:,.2f} net" if eval_view.has_executed else None,
            delta_color="normal",
            help="Simulated net recovered value (Gross Recovered minus Execution Cost).",
        )
        st.caption(f"**{eval_view.net_recovered_provenance}** • {eval_view.net_recovered_sub}")

    with ev_col6:
        st.metric(
            "Recovery ROI",
            eval_view.recovery_roi_value,
            delta=f"{eval_view.recovery_roi_value} return" if eval_view.has_executed and eval_view.recovery_roi_value != "N/A" else None,
            delta_color="normal",
            help="Simulated recovery ROI (Net Value / Execution Cost). Displays N/A when execution cost is zero.",
        )
        st.caption(f"**{eval_view.recovery_roi_provenance}** • {eval_view.recovery_roi_sub}")

    # Pipeline Governance & Status Summary Card
    st.markdown(
        f"""
        <div class="fintech-card" style="margin-top: 1rem;">
            <div style="font-size: 0.82rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;">
                Pipeline Governance & Verification Summary
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; align-items: start;">
                <div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px;">SAFETY OUTCOME <span style="font-size: 0.68rem; color: #94a3b8;">({eval_view.safety_provenance})</span></div>
                    <div><span class="{eval_view.safety_pill_class}">{eval_view.safety_status_value}</span></div>
                    <div style="font-size: 0.72rem; color: #64748b; margin-top: 4px;">{eval_view.safety_reason}</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px;">SELECTED ACTION</div>
                    <div><span class="pill-blue">{eval_view.selected_action}</span></div>
                    <div style="font-size: 0.72rem; color: #64748b; margin-top: 4px;">Confidence: {eval_view.scorecard.decision_confidence * 100:.1f}%</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px;">CANARY DECISION <span style="font-size: 0.68rem; color: #94a3b8;">(SIMULATED)</span></div>
                    <div><span class="{eval_view.canary_pill_class}">{eval_view.canary_decision}</span></div>
                    <div style="font-size: 0.72rem; color: #64748b; margin-top: 4px;">Bounded canary stage</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px;">GUARDRAIL DECISION <span style="font-size: 0.68rem; color: #94a3b8;">(SIMULATED)</span></div>
                    <div><span class="{eval_view.guardrail_pill_class}">{eval_view.guardrail_decision}</span></div>
                    <div style="font-size: 0.72rem; color: #64748b; margin-top: 4px;">Circuit breaker status</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px;">FINAL RECOVERY STATUS <span style="font-size: 0.68rem; color: #94a3b8;">(SIMULATED)</span></div>
                    <div><span class="{eval_view.final_pill_class}">{eval_view.final_status}</span></div>
                    <div style="font-size: 0.72rem; color: #64748b; margin-top: 4px;">Rollback required: <span class="{eval_view.rollback_pill_class}">{eval_view.rollback_required}</span></div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px;">LEARNING EVIDENCE LIFT <span style="font-size: 0.68rem; color: #94a3b8;">({eval_view.learning_provenance})</span></div>
                    <div><span class="{eval_view.learning_pill_class}">{eval_view.learning_lift_value}</span></div>
                    <div style="font-size: 0.72rem; color: #64748b; margin-top: 4px;">{eval_view.learning_sub}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =========================================
    # SECTION 8 — AUDIT TRAIL
    # =========================================

    st.markdown('<div id="recovery-audit-trail"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">📋 Audit Trail</div>',
        unsafe_allow_html=True,
    )

    # Vertical timeline
    st.markdown(
        """
        <div class="timeline-track">
            <div class="timeline-step">
                <div class="timeline-marker timeline-marker-success"></div>
                <div style="font-weight: 600; font-size: 0.88rem; color: #0f172a;">Incident detected</div>
                <div style="font-size: 0.76rem; color: #64748b;">Sliding window detector observes anomalous route drop against baseline.</div>
            </div>
            <div class="timeline-step">
                <div class="timeline-marker timeline-marker-success"></div>
                <div style="font-weight: 600; font-size: 0.88rem; color: #0f172a;">Risk quantified</div>
                <div style="font-size: 0.76rem; color: #64748b;">Excess failures and business revenue at risk computed against historical expected failures.</div>
            </div>
            <div class="timeline-step">
                <div class="timeline-marker timeline-marker-success"></div>
                <div style="font-weight: 600; font-size: 0.88rem; color: #0f172a;">AI decision generated</div>
                <div style="font-size: 0.76rem; color: #64748b;">IncidentDecisionEngine evaluates candidate routes and determines optimal action.</div>
            </div>
            <div class="timeline-step">
                <div class="timeline-marker timeline-marker-warn"></div>
                <div style="font-weight: 600; font-size: 0.88rem; color: #0f172a;">Safety decision recorded</div>
                <div style="font-size: 0.76rem; color: #64748b;">Deterministic SafetyController verifies confidence, limits, and review requirements.</div>
            </div>
            <div class="timeline-step">
                <div class="timeline-marker"></div>
                <div style="font-weight: 600; font-size: 0.88rem; color: #0f172a;">Human approval (if applicable)</div>
                <div style="font-size: 0.76rem; color: #64748b;">Operator authorization logged for simulation when human review is required.</div>
            </div>
            <div class="timeline-step">
                <div class="timeline-marker"></div>
                <div style="font-weight: 600; font-size: 0.88rem; color: #0f172a;">Canary executed</div>
                <div style="font-size: 0.76rem; color: #64748b;">Bounded batch traffic evaluated on target alternative route.</div>
            </div>
            <div class="timeline-step">
                <div class="timeline-marker"></div>
                <div style="font-weight: 600; font-size: 0.88rem; color: #0f172a;">Guardrail evaluated</div>
                <div style="font-size: 0.76rem; color: #64748b;">Circuit breaker ensures alternative route remains healthy without degradation.</div>
            </div>
            <div class="timeline-step">
                <div class="timeline-marker"></div>
                <div style="font-weight: 600; font-size: 0.88rem; color: #0f172a;">Outcome verified</div>
                <div style="font-size: 0.76rem; color: #64748b;">Simulation results and counterfactual recoveries confirmed.</div>
            </div>
            <div class="timeline-step">
                <div class="timeline-marker timeline-marker-success"></div>
                <div style="font-weight: 600; font-size: 0.88rem; color: #0f172a;">Learning updated</div>
                <div style="font-size: 0.76rem; color: #64748b;">Route-level Bayesian evidence continuously updated in recovery learning log.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    run_an_col1, run_an_col2 = st.columns([1.2, 2.8])
    with run_an_col1:
        if st.button(
            "🚀 Run Recovery Analysis", type="primary", use_container_width=True
        ):
            with st.spinner("Executing authoritative analysis..."):
                try:
                    analysis_result = execute_orchestrated_batch_recovery(
                        transactions=transactions,
                        incident=incident,
                        decision=intelligence_result.decision,
                        safety=safety,
                        recovery=recovery,
                        payment_method=payment_method,
                        affected_bank=affected_bank,
                        device_type=device_type,
                        batch_size=50,
                        human_approved=(
                            decision_status in ("RECOVER", "ROLLBACK")
                        ),
                    )
                    st.session_state["batch_result"] = analysis_result
                    st.success("Recovery analysis recorded to audit trail.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Analysis error: {ex}")

    with run_an_col2:
        st.caption(
            "Executes end-to-end recovery evaluation through the authoritative RecoveryOrchestrator and appends the outcome to the audit log."
        )

    # Audit history table
    audit_data = load_audit_log()
    if audit_data is not None and not audit_data.empty:
        with st.expander("🔎 Detailed Governance Audit Log & Historical Records", expanded=False):
            audit_display = audit_data.copy()
            if "timestamp" in audit_display.columns:
                audit_display["timestamp"] = pd.to_datetime(
                    audit_display["timestamp"], errors="coerce"
                )

            if all(
                col in audit_display.columns
                for col in ["payment_method", "affected_bank", "device_type"]
            ):
                audit_display["route"] = (
                    audit_display["payment_method"].astype(str)
                    + " → "
                    + audit_display["affected_bank"].astype(str)
                    + " → "
                    + audit_display["device_type"].astype(str)
                )

            desired_cols = [
                "timestamp",
                "route",
                "recommended_bank",
                "policy_decision",
                "recovered_amount",
                "execution_cost",
                "net_recovered_value",
                "recovery_rate",
                "estimated_recovered_value",
            ]
            disp_cols = [c for c in desired_cols if c in audit_display.columns]

            rename_map = {
                "timestamp": "Run Time",
                "route": "Route",
                "recommended_bank": "Action",
                "policy_decision": "Status",
                "recovered_amount": "Recovered Amount",
                "execution_cost": "Execution Cost",
                "net_recovered_value": "Net Recovered Value",
                "recovery_rate": "Recovery Rate",
                "estimated_recovered_value": "Estimated Recovered Value",
            }

            formatted_audit = (
                audit_display[disp_cols]
                .sort_values("timestamp", ascending=False)
                .rename(columns=rename_map)
            )
            st.dataframe(
                formatted_audit.head(15), use_container_width=True, hide_index=True
            )
    else:
        st.info("No audit history recorded yet.")

# =========================================
# FOOTER
# =========================================

st.markdown(
    """
    <div class="footer-text">
        AI Payment Reliability Center · Simulation Environment · No real payment routing or payment processing is performed
    </div>
    """,
    unsafe_allow_html=True,
)
