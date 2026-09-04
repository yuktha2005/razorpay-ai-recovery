"""
Demo Package for Razorpay AI Revenue Recovery.

Provides deterministic, judge-ready end-to-end demonstration scenarios
and runners orchestrating the existing payment reliability and recovery architecture.
"""

from src.demo.demo_scenario import (
    CANONICAL_HAPPY_PATH,
    DEMO_SCENARIOS,
    DEFAULT_DEMO_CANDIDATES,
    FAILURE_SAFETY_BLOCKED,
    FAILURE_UNPROFITABLE_ROLLBACK,
    DemoScenario,
    get_demo_scenario,
    list_demo_scenarios,
)
from src.demo.demo_runner import (
    DemoPhase,
    DemoRunResult,
    DemoRunner,
    LifecycleEvent,
    PhaseResult,
    format_demo_report,
)
from src.demo.demo_ui import (
    build_demo_view_model,
    get_phase_status,
    get_phase_icon,
    get_phase_css_class,
    get_financial_display,
    get_learning_display,
    get_reevaluation_display,
    get_closed_loop_learning_flow,
    get_final_status_bar,
    PROVENANCE_OBSERVED,
    PROVENANCE_THEORETICAL,
    PROVENANCE_SIMULATED,
    PROVENANCE_GOVERNED,
    PROVENANCE_LEARNED,
)

__all__ = [
    "CANONICAL_HAPPY_PATH",
    "DEMO_SCENARIOS",
    "DEFAULT_DEMO_CANDIDATES",
    "FAILURE_SAFETY_BLOCKED",
    "FAILURE_UNPROFITABLE_ROLLBACK",
    "DemoScenario",
    "get_demo_scenario",
    "list_demo_scenarios",
    "DemoPhase",
    "DemoRunner",
    "DemoRunResult",
    "LifecycleEvent",
    "PhaseResult",
    "format_demo_report",
    "build_demo_view_model",
    "get_phase_status",
    "get_phase_icon",
    "get_phase_css_class",
    "get_financial_display",
    "get_learning_display",
    "get_reevaluation_display",
    "get_closed_loop_learning_flow",
    "get_final_status_bar",
    "PROVENANCE_OBSERVED",
    "PROVENANCE_THEORETICAL",
    "PROVENANCE_SIMULATED",
    "PROVENANCE_GOVERNED",
    "PROVENANCE_LEARNED",
]
