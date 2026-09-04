"""
Evaluation package for Razorpay AI Revenue Recovery.

Provides deterministic, judge-facing evaluation scorecards that aggregate
authoritative intelligence, decision, safety, recovery, and learning metrics.
"""

from src.evaluation.detection_benchmark import (
    BenchmarkCaseResult,
    BenchmarkScenario,
    DetectionBenchmarkResult,
    IncidentDetectionBenchmark,
    benchmark_to_detection_summary,
    create_deterministic_window,
)
from src.evaluation.evaluation_adapter import (
    DashboardEvaluationView,
    EvaluationAdapter,
    build_system_evaluation_scorecard,
    prepare_dashboard_evaluation_scorecard,
)
from src.evaluation.evaluation_snapshot import (
    EvaluationSnapshot,
    JudgeEvaluationSummary,
    MetricProvenanceCategory,
    SNAPSHOT_METRIC_PROVENANCE,
    build_evaluation_snapshot,
)
from src.evaluation.scorecard import (
    METRIC_PROVENANCE,
    SystemEvaluationScorecard,
    build_scorecard,
)

__all__ = [
    "BenchmarkCaseResult",
    "BenchmarkScenario",
    "DashboardEvaluationView",
    "DetectionBenchmarkResult",
    "EvaluationAdapter",
    "EvaluationSnapshot",
    "IncidentDetectionBenchmark",
    "JudgeEvaluationSummary",
    "METRIC_PROVENANCE",
    "MetricProvenanceCategory",
    "SNAPSHOT_METRIC_PROVENANCE",
    "SystemEvaluationScorecard",
    "benchmark_to_detection_summary",
    "build_evaluation_snapshot",
    "build_scorecard",
    "build_system_evaluation_scorecard",
    "create_deterministic_window",
    "prepare_dashboard_evaluation_scorecard",
]
