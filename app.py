import json
import streamlit as st
import pandas as pd
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
    page_title="AI Payment Reliability Center",
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
</style>
""",
    unsafe_allow_html=True,
)


# =========================================
# SIDEBAR
# =========================================

with st.sidebar:
    st.markdown(
        """
        <div style="font-size: 1.35rem; font-weight: 700; color: #0f172a; line-height: 1.15; margin-bottom: 2px;">
            AI Payment<br><span style="color: #0284c7;">Reliability</span>
        </div>
        <div style="font-size: 0.8rem; color: #64748b; margin-bottom: 12px;">Reliability & Recovery Console</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**Demo Scenario**")
    scenario_name = st.selectbox(
        "Select scenario",
        list_scenarios(),
        index=0,
        label_visibility="collapsed",
        help="Counterfactual validation scenarios without live payment execution.",
    )

    selected_scenario = get_scenario(scenario_name)
    scenario_view = scenario_summary(scenario_name)
    scenario_control = evaluate_scenario_control(scenario_name)

    st.caption(f"{scenario_view['description']}")

    st.markdown("---")

    st.markdown(
        """
        **Navigation**
        - [• Overview](#system-overview)
        - [• Decision Intelligence](#ai-decision-intelligence)
        - [• Recovery Control](#recovery-control)
        - [• Learning](#recovery-learning)
        - [• Audit Trail](#recovery-audit-trail)
        """
    )

    st.markdown("---")

    st.markdown(
        """
        <div style="background: #f1f5f9; padding: 10px 12px; border-radius: 8px; font-size: 0.8rem;">
            <div style="color: #0284c7; font-weight: 700;">⚙ SIMULATION MODE</div>
            <div style="color: #334155; margin-top: 4px;">Environment: <b>Demo</b></div>
            <div style="color: #334155;">Safety: <b>Enforced</b></div>
            <div style="color: #64748b; font-size: 0.72rem; margin-top: 4px;">No live routing performed</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================
# HEADER
# =========================================

st.markdown(
    """
    <div class="header-bar">
        <div>
            <div class="product-title">AI PAYMENT RELIABILITY CENTER</div>
            <div class="product-subtitle">Detect revenue risk. Decide safely. Recover within bounds.</div>
        </div>
        <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
            <span class="badge-sim">⚙ SIMULATION MODE</span>
            <span class="badge-status">⚙ System Operational</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
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
# SECTION 1 — SYSTEM OVERVIEW
# =========================================

st.markdown('<div id="system-overview"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">📊 System Overview</div>', unsafe_allow_html=True)

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

    st.markdown(
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
        """,
        unsafe_allow_html=True,
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

    st.markdown(
        '<div class="section-title">'
        '📈 Incident Timeline'
        '</div>',
        unsafe_allow_html=True
    )


    timeline = transactions.copy()

    timeline["timestamp"] = pd.to_datetime(
        timeline["timestamp"],
        format="mixed"
    )

    timeline["hour"] = (
        timeline["timestamp"]
        .dt.floor("1h")
    )


    hourly = (
        timeline
        .groupby("hour")
        .agg(
            transactions=(
                "transaction_id",
                "count"
            ),

            successful=(
                "status",
                lambda x:
                (x == "SUCCESS").sum()
            )
        )
        .reset_index()
    )


    hourly["success_rate"] = (
        hourly["successful"]
        / hourly["transactions"]
        * 100
    )


    hourly = hourly.sort_values(
        "hour"
    )


    # Focus the timeline around the detected incident so
    # the degradation is immediately visible during a demo.
    timeline_start = incident_start - pd.Timedelta(hours=12)
    timeline_end = incident_start + pd.Timedelta(hours=12)

    focused_hourly = hourly[
        (hourly["hour"] >= timeline_start)
        &
        (hourly["hour"] <= timeline_end)
    ].copy()

    if not focused_hourly.empty:

        st.line_chart(
            focused_hourly.set_index("hour")[
                "success_rate"
            ],
            height=300,
            use_container_width=True
        )

    else:

        st.line_chart(
            hourly.set_index("hour")[
                "success_rate"
            ],
            height=300,
            use_container_width=True
        )


    incident_row = hourly[
        hourly["hour"] == incident_start
    ]


    if not incident_row.empty:

        incident_rate = float(
            incident_row.iloc[0][
                "success_rate"
            ]
        )

        st.error(
            f"🔴 Incident detected at "
            f"{incident_start.strftime('%Y-%m-%d %H:%M')} — "
            f"overall system success rate during this hour: "
            f"{incident_rate:.2f}%"
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

        st.markdown(
            "### AI Evidence"
        )


        for evidence in ai_diagnosis[
            "evidence"
        ]:

            st.markdown(
                f"• {evidence}"
            )


        st.markdown(
            "### Recommended Investigation"
        )


        for item in ai_diagnosis[
            "recommended_investigation"
        ]:

            st.markdown(
                f"• {item}"
            )


        st.caption(
            "AI diagnosis is advisory. "
            "Recovery authorization remains controlled "
            "by the policy engine."
        )


    # =====================================
    # BUSINESS IMPACT
    # =====================================

    st.divider()


    st.markdown(
        '<div class="section-title">'
        '💰 Business Impact'
        '</div>',
        unsafe_allow_html=True
    )


    impact = calculate_revenue_impact(
        transactions,
        incident
    )


    if impact:

        col1, col2, col3 = st.columns(3)


        with col1:

            st.metric(
                "Actual Failures",
                f"{impact['actual_failures']:,}"
            )


        with col2:

            st.metric(
                "Excess Failures",
                f"{impact['excess_failures']:.1f}"
            )


        with col3:

            st.metric(
                "Revenue at Risk",
                f"₹{impact['revenue_at_risk']:,.0f}"
            )

# =====================================
# DECISION INTELLIGENCE
# =====================================

st.markdown(
    '<div class="section-title">'
    '🧠 Decision Intelligence'
    '</div>',
    unsafe_allow_html=True
)

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

    decision_engine = IncidentDecisionEngine()

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

    # =====================================

    st.markdown(
        '<div class="section-title">'
        '⚡ Recovery Recommendation'
        '</div>',
        unsafe_allow_html=True
    )

    st.info(
        "🤖 Gemini provides advisory incident diagnosis. "
        "Recovery selection is performed by the deterministic recovery engine, "
        "and authorization is enforced by the policy engine."
    )


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
    # RECOVERY INFORMATION
    # =====================================

    if recovery:

        simulation_preview = (
            simulate_recovery(
                transactions,
                incident,
                recovery
            )
        )


        st.markdown(
            '<div class="recovery-card">',
            unsafe_allow_html=True
        )


        col1, col2, col3 = st.columns(3)


        with col1:

            st.metric(
                "Current Bank",
                affected_bank
            )


        with col2:

            st.metric(
                "Proposed Bank",
                recovery[
                    "alternative_bank"
                ]
            )


        with col3:

            st.metric(
                "Historical Success",
                f"{recovery['alternative_success_rate'] * 100:.2f}%"
            )


        expected_improvement = (
            recovery["alternative_success_rate"]
            - incident["success_rate"]
        ) * 100

        st.markdown(
            f"""
<div class="explanation-card">

<b>Why {recovery['alternative_bank']}?</b>

<br><br>

The recovery engine evaluated historical
<b>{payment_method} + {device_type}</b>
traffic and identified
<b>{recovery['alternative_bank']}</b>
as the strongest eligible alternative.

<br><br>

<b>Current route:</b>
{affected_bank}
<br>

<b>Alternative route:</b>
{recovery['alternative_bank']}
<br>

<b>Current success rate:</b>
{incident_success:.2f}%
<br>

<b>Historical alternative success rate:</b>
{recovery['alternative_success_rate'] * 100:.2f}%
<br>

<b>Expected improvement:</b>
{expected_improvement:.2f} percentage points

<br><br>

The recommendation is subject to all
policy safety checks before any simulated
recovery action is permitted.

</div>
""",
            unsafe_allow_html=True
        )


        if simulation_preview:

            c1, c2 = st.columns(2)


            with c1:

                st.metric(
                    "Potential Additional Successes",
                    f"+{simulation_preview['additional_successes']}"
                )


            with c2:

                st.metric(
                    "Estimated Recoverable Value",
                    f"₹{simulation_preview['estimated_recovered_value']:,.2f}"
                )


        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    else:

        st.warning(
            "No suitable recovery recommendation is currently available."
        )


    # =====================================
    # POLICY DISPLAY
    # =====================================

    st.markdown(
        '<div class="section-title">'
        '🛡️ Recovery Policy Gate'
        '</div>',
        unsafe_allow_html=True
    )


    decision = policy_result[
        "decision"
    ]


    if decision == "RECOVER":

        st.markdown(
            f"""
<div class="policy-recover">

<h3>🟢 RECOVER — Approved</h3>

<b>Decision:</b> {decision}

<br><br>

<b>Policy reason:</b><br>
{policy_result['reason']}

</div>
""",
            unsafe_allow_html=True
        )


    elif decision == "ESCALATE":

        st.markdown(
            f"""
<div class="policy-escalate">

<h3>🟡 ESCALATE — Human Review Required</h3>

<b>Decision:</b> {decision}

<br><br>

<b>Policy reason:</b><br>
{policy_result['reason']}

</div>
""",
            unsafe_allow_html=True
        )


    elif decision == "ROLLBACK":

        st.markdown(
            f"""
<div class="policy-stop">

<h3>↩️ ROLLBACK — Recovery Reversed</h3>

<b>Decision:</b> {decision}

<br><br>

<b>Policy reason:</b><br>
{policy_result['reason']}

</div>
""",
            unsafe_allow_html=True
        )


    elif decision == "CONTINUE":

        st.success(
            f"🟢 **CONTINUE — No Recovery Required**\n\n"
            f"{policy_result['reason']}"
        )


    else:

        st.markdown(
            f"""
<div class="policy-stop">

<h3>🔴 STOP — Recovery Blocked</h3>

<b>Decision:</b> {decision}

<br><br>

<b>Policy reason:</b><br>
{policy_result['reason']}

</div>
""",
            unsafe_allow_html=True
        )


    # =====================================
    # POLICY CHECKS
    # =====================================

    if policy_result["checks"]:

        st.markdown(
            "### Policy Checks"
        )


        policy_rows = []


        for check in policy_result[
            "checks"
        ]:

            policy_rows.append({
                "Status":
                    "✅ PASS"
                    if check["passed"]
                    else
                    "❌ FAIL",

                "Policy Check":
                    check["check"],

                "Value":
                    check["value"],

                "Threshold":
                    check["threshold"]
            })


        policy_df = pd.DataFrame(
            policy_rows
        )


        st.dataframe(
            policy_df,
            use_container_width=True,
            hide_index=True
        )


        passed_checks = sum(
            check["passed"]
            for check in policy_result[
                "checks"
            ]
        )


        total_checks = len(
            policy_result["checks"]
        )


        st.caption(
            f"{passed_checks}/{total_checks} "
            f"policy checks passed."
        )


    # =====================================
    # RECOMMENDED ACTION
    # =====================================

    if recovery:

        if decision == "RECOVER":

            st.success(
                f"⚡ Approved action: Prefer "
                f"{recovery['alternative_bank']} "
                f"for eligible "
                f"{payment_method} + "
                f"{device_type} traffic."
            )


        elif decision == "ESCALATE":

            st.warning(
                "⚠️ Automated recovery is not approved. "
                "Human review is required before routing changes."
            )


        elif decision == "ROLLBACK":

            st.error(
                "↩️ Recovery is blocked because the simulated "
                "alternative route breached its guardrail."
            )


        elif decision == "CONTINUE":

            st.success(
                "🟢 No automated recovery is required for this scenario."
            )


        else:

            st.error(
                "🛑 Automated recovery is blocked "
                "by the policy engine."
            )


    # =====================================
    # ALTERNATIVE ROUTE ANALYSIS
    # =====================================

    st.markdown(
        '<div class="section-title">'
        '🏦 Alternative Route Analysis'
        '</div>',
        unsafe_allow_html=True
    )


    historical = transactions[
        ~(
            (transactions["timestamp"] >= incident_start)
            &
            (transactions["timestamp"] < incident_end)
        )
    ].copy()


    route_data = historical[
        (historical["payment_method"]
         == payment_method)
        &
        (historical["device_type"]
         == device_type)
    ].copy()


    route_comparison = (
        route_data
        .groupby("bank")
        .agg(
            transactions=(
                "transaction_id",
                "count"
            ),

            successful=(
                "status",
                lambda x:
                (x == "SUCCESS").sum()
            ),

            failed=(
                "status",
                lambda x:
                (x == "FAILED").sum()
            )
        )
        .reset_index()
    )


    if not route_comparison.empty:

        route_comparison["success_rate"] = (
            route_comparison["successful"]
            / route_comparison["transactions"]
            * 100
        )


        route_comparison = (
            route_comparison[
                route_comparison["transactions"]
                >= 100
            ]
            .copy()
        )


        route_comparison = (
            route_comparison
            .sort_values(
                "success_rate",
                ascending=False
            )
        )


        def get_route_status(bank):

            if bank == affected_bank:

                return "🔴 Degraded"


            if (
                recovery
                and bank
                == recovery[
                    "alternative_bank"
                ]
            ):

                if decision == "RECOVER":

                    return "🟢 Recommended"

                elif decision == "ESCALATE":

                    return "🟡 Proposed"

                else:

                    return "⚪ Blocked"


            return "Normal"


        route_comparison[
            "status"
        ] = (
            route_comparison[
                "bank"
            ].apply(
                get_route_status
            )
        )


        display_routes = (
            route_comparison.rename(
                columns={
                    "bank":
                        "Bank",

                    "transactions":
                        "Transactions",

                    "successful":
                        "Successful",

                    "failed":
                        "Failed",

                    "success_rate":
                        "Success Rate (%)",

                    "status":
                        "Route Status"
                }
            )
        )


        st.dataframe(
            display_routes[
                [
                    "Bank",
                    "Transactions",
                    "Successful",
                    "Failed",
                    "Success Rate (%)",
                    "Route Status"
                ]
            ].style.format({
                "Success Rate (%)":
                    "{:.2f}"
            }),
            use_container_width=True,
            hide_index=True
        )


    else:

        st.info(
            "No sufficient historical alternative "
            "route data available."
        )


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

    rec_action = intelligence_decision.recommended_action
    conf_str = f"{intelligence_decision.confidence * 100:.0f}%"

    d_col1, d_col2 = st.columns([1.5, 1])

    with d_col1:
        st.markdown(
            f"""
            <div class="decision-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-size: 0.78rem; font-weight: 700; color: #0284c7; text-transform: uppercase;">
                        AI Recommendation
                    </div>
                    <span class="pill-blue">CONFIDENCE: {conf_str}</span>
                </div>
                <div style="font-size: 1.35rem; font-weight: 700; color: #0f172a; margin-bottom: 12px;">
                    {rec_action}
                </div>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; padding-top: 10px; border-top: 1px solid #f1f5f9;">
                    <div>
                        <div style="font-size: 0.72rem; color: #64748b;">Expected Loss Before</div>
                        <div style="font-size: 1rem; font-weight: 600; color: #64748b;">₹{intelligence_decision.expected_loss_before:,.0f}</div>
                    </div>
                    <div>
                        <div style="font-size: 0.72rem; color: #64748b;">Expected Loss After</div>
                        <div style="font-size: 1rem; font-weight: 600; color: #059669;">₹{intelligence_decision.expected_loss_after:,.0f}</div>
                    </div>
                    <div>
                        <div style="font-size: 0.72rem; color: #64748b;">Estimated Recovery</div>
                        <div style="font-size: 1rem; font-weight: 700; color: #0284c7;">₹{intelligence_decision.estimated_value:,.0f}*</div>
                    </div>
                </div>
                <div style="font-size: 0.72rem; color: #94a3b8; margin-top: 8px;">*Simulated counterfactual projection</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with d_col2:
        gemini_diag = (
            ai_diagnosis["primary_diagnosis"]
            if ai_diagnosis
            else "AI advisory diagnosis based on observed telemetry."
        )
        st.markdown(
            f"""
            <div class="fintech-card">
                <div style="font-size: 0.82rem; font-weight: 700; color: #0f172a; margin-bottom: 6px;">
                    Why This Decision?
                </div>
                <div style="font-size: 0.82rem; color: #475569; line-height: 1.5; margin-bottom: 10px;">
                    {intelligence_decision.explanation}
                </div>
                <div style="font-size: 0.75rem; color: #64748b; background: #f8fafc; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0;">
                    <b>Advisory Evidence:</b> {gemini_diag}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
    p_col1, p_col2, p_col3, p_col4 = st.columns(4)

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
                "Canary Decision",
                batch_result.get("canary_decision", "NOT_APPLICABLE"),
                help="Bounded canary evaluation result.",
            )
        with p_col4:
            st.metric(
                "Guardrail Status",
                batch_result.get("guardrail_decision", "NOT_RECORDED"),
                help="Circuit breaker guardrail decision for route safety.",
            )
    else:
        with p_col1:
            st.metric("Recovery Rate", "Not executed")
        with p_col2:
            st.metric("Recovery ROI", "ROI: N/A — no execution cost recorded")
        with p_col3:
            st.metric("Canary Decision", "PENDING")
        with p_col4:
            st.metric("Guardrail Status", "PENDING")


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
    # SECTION 6 — CONTINUOUS LEARNING
    # =========================================

    st.markdown('<div id="recovery-learning"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">🧠 Recovery Learning</div>',
        unsafe_allow_html=True,
    )

    try:
        history_loader = PersistentLearningHistory()
        learned_routes = history_loader.load()

        if learned_routes:
            l1, l2, l3, l4 = st.columns(4)
            with l1:
                st.metric("Learned Routes", f"{len(learned_routes)}")
            with l2:
                st.metric(
                    "Total Attempts",
                    f"{sum(r.attempts for r in learned_routes):,}",
                )
            with l3:
                st.metric(
                    "Verified Recoveries",
                    f"{sum(r.recoveries for r in learned_routes):,}",
                )
            with l4:
                st.metric(
                    "Net Recovered Value",
                    f"₹{sum(r.net_recovered_value for r in learned_routes):,.2f}",
                )

            st.caption(
                "Recovery outcomes continuously update route-level evidence used by future recovery decisions."
            )

            learning_rows = []
            for r in learned_routes:
                learning_rows.append(
                    {
                        "Route": r.route,
                        "Attempts": r.attempts,
                        "Recoveries": r.recoveries,
                        "Recovery Rate": f"{r.recovery_rate * 100:.1f}%",
                        "Net Value": f"₹{r.net_recovered_value:,.2f}",
                        "Evidence Confidence": f"{r.evidence_confidence * 100:.1f}%",
                    }
                )
            st.dataframe(
                pd.DataFrame(learning_rows),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No route learning observations recorded yet.")
    except Exception as e:
        st.warning(f"Could not load recovery learning history: {e}")


    # =========================================
    # SECTION 7 — AUDIT TRAIL
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
        st.markdown("**Decision History Log**")
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
