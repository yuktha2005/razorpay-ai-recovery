import math
from unittest.mock import MagicMock
import pytest

from src.decision.incident_decision_engine import IncidentDecisionEngine
from src.evaluation.detection_benchmark import (
    DetectionBenchmarkResult,
    IncidentDetectionBenchmark,
)
from src.evaluation.evaluation_snapshot import (
    EvaluationSnapshot,
    JudgeEvaluationSummary,
    MetricProvenanceCategory,
    SNAPSHOT_METRIC_PROVENANCE,
    build_evaluation_snapshot,
)
from src.evaluation.scorecard import SystemEvaluationScorecard, build_scorecard
from src.models.domain import Decision, SafetyDecision
from src.recovery.recovery_orchestrator import RecoveryOrchestrator


def test_snapshot_construction_from_scorecard():
    """
    1. Snapshot construction from an authoritative SystemEvaluationScorecard.
    Verifies that all fields are mapped faithfully.
    """
    scorecard = build_scorecard(
        degradation_percentage_points=25.0,
        severity="CRITICAL",
        transactions_observed=100,
        incident_detected=True,
        revenue_at_risk=24000.0,
        eligible_amount=8000.0,
        attempted_amount=8000.0,
        recovered_amount=7680.0,
        execution_cost=250.0,
        net_recovered_value=7430.0,
        recovery_rate=0.96,
        recovery_roi=29.72,
        expected_loss_before=24000.0,
        expected_loss_after=2400.0,
        expected_loss_reduction=21600.0,
        expected_loss_reduction_percentage=90.0,
        decision_confidence=0.95,
        selected_action="ROUTE_SWITCH:UPI + Bank_B + Android",
        attempted_transactions=10,
        successful_recoveries=9,
        failed_recoveries=1,
        canary_decision="EXPAND",
        guardrail_decision="CONTINUE",
        rollback_required=False,
        final_status="RECOVERED",
        safety_allowed=True,
        human_review_required=False,
        safety_reason="Safe bounded recovery",
        learned_attempts=10,
        learned_recoveries=9,
        learned_recovery_rate=0.9,
        learning_evidence_confidence=0.85,
        route_score_before_learning=0.85,
        route_score_after_learning=0.92,
        learning_score_delta=0.07,
        decision_changed_after_learning=False,
    )

    benchmark_res = DetectionBenchmarkResult(
        total_cases=10,
        true_positives=4,
        true_negatives=4,
        false_positives=0,
        false_negatives=2,
        precision=1.0,
        recall=0.6667,
        f1_score=0.8,
        specificity=1.0,
        detection_accuracy=0.8,
    )

    snapshot = build_evaluation_snapshot(
        scorecard=scorecard,
        benchmark_result=benchmark_res,
    )

    assert snapshot.benchmark_total_cases == 10
    assert snapshot.benchmark_tp == 4
    assert snapshot.benchmark_tn == 4
    assert snapshot.benchmark_precision == 1.0
    assert snapshot.benchmark_f1 == 0.8
    assert snapshot.degradation_percentage_points == 25.0
    assert snapshot.severity == "CRITICAL"
    assert snapshot.revenue_at_risk == 24000.0
    assert snapshot.net_recovered_value == 7430.0
    assert snapshot.recovery_roi == 29.72
    assert snapshot.selected_action == "ROUTE_SWITCH:UPI + Bank_B + Android"
    assert snapshot.safety_allowed is True
    assert snapshot.learning_score_delta == 0.07
    assert snapshot.has_executed is True
    assert snapshot.has_learning_evidence is True


def test_benchmark_metrics_transfer_and_confusion_matrix():
    """
    2. Benchmark metrics transfer & confusion matrix preservation.
    """
    benchmark_res = DetectionBenchmarkResult(
        total_cases=8,
        true_positives=3,
        true_negatives=3,
        false_positives=1,
        false_negatives=1,
        precision=0.75,
        recall=0.75,
        f1_score=0.75,
        specificity=0.75,
        detection_accuracy=0.75,
    )

    snapshot = build_evaluation_snapshot(
        scorecard=None,
        benchmark_result=benchmark_res,
        run_detection_benchmark_if_none=False,
    )

    assert snapshot.precision == 0.75
    assert snapshot.recall == 0.75
    assert snapshot.f1 == 0.75
    assert snapshot.specificity == 0.75
    assert snapshot.accuracy == 0.75
    assert snapshot.benchmark_tp == 3
    assert snapshot.benchmark_tn == 3
    assert snapshot.benchmark_fp == 1
    assert snapshot.benchmark_fn == 1

    summary = snapshot.to_summary()
    assert summary.detection_confusion_matrix == {
        "TP": 3,
        "TN": 3,
        "FP": 1,
        "FN": 1,
    }
    assert summary.detection_f1 == 0.75


def test_provenance_categories_strictly_maintained():
    """
    3. Provenance categories are strictly maintained across all fields.
    """
    # 1. OBSERVED
    assert (
        SNAPSHOT_METRIC_PROVENANCE["degradation_percentage_points"]
        == MetricProvenanceCategory.OBSERVED.value
    )
    assert (
        SNAPSHOT_METRIC_PROVENANCE["transactions_observed"]
        == MetricProvenanceCategory.OBSERVED.value
    )

    # 2. THEORETICAL / COUNTERFACTUAL
    assert (
        SNAPSHOT_METRIC_PROVENANCE["revenue_at_risk"]
        == MetricProvenanceCategory.THEORETICAL.value
    )
    assert (
        SNAPSHOT_METRIC_PROVENANCE["expected_loss_before"]
        == MetricProvenanceCategory.THEORETICAL.value
    )
    assert (
        SNAPSHOT_METRIC_PROVENANCE["expected_loss_reduction"]
        == MetricProvenanceCategory.THEORETICAL.value
    )

    # 3. SIMULATED
    assert (
        SNAPSHOT_METRIC_PROVENANCE["recovered_amount"]
        == MetricProvenanceCategory.SIMULATED.value
    )
    assert (
        SNAPSHOT_METRIC_PROVENANCE["net_recovered_value"]
        == MetricProvenanceCategory.SIMULATED.value
    )
    assert (
        SNAPSHOT_METRIC_PROVENANCE["recovery_rate"]
        == MetricProvenanceCategory.SIMULATED.value
    )
    assert (
        SNAPSHOT_METRIC_PROVENANCE["recovery_roi"]
        == MetricProvenanceCategory.SIMULATED.value
    )

    # 4. GOVERNED / EVALUATED
    assert (
        SNAPSHOT_METRIC_PROVENANCE["safety_allowed"]
        == MetricProvenanceCategory.GOVERNED.value
    )
    assert (
        SNAPSHOT_METRIC_PROVENANCE["human_review_required"]
        == MetricProvenanceCategory.GOVERNED.value
    )

    # 5. LEARNED
    assert (
        SNAPSHOT_METRIC_PROVENANCE["learning_score_delta"]
        == MetricProvenanceCategory.LEARNED.value
    )
    assert (
        SNAPSHOT_METRIC_PROVENANCE["decision_changed_after_learning"]
        == MetricProvenanceCategory.LEARNED.value
    )

    assert (
        EvaluationSnapshot.get_provenance("revenue_at_risk")
        == "THEORETICAL / COUNTERFACTUAL"
    )
    assert EvaluationSnapshot.get_provenance("net_recovered_value") == "SIMULATED"


def test_unexecuted_recovery_state_preserves_none_roi():
    """
    4. Unexecuted recovery state keeps ROI as None and displays N/A.
    """
    scorecard = build_scorecard(
        degradation_percentage_points=15.0,
        severity="DEGRADED",
        transactions_observed=50,
        incident_detected=True,
        revenue_at_risk=10000.0,
        eligible_amount=5000.0,
        attempted_amount=0.0,
        recovered_amount=0.0,
        execution_cost=0.0,
        net_recovered_value=0.0,
        recovery_rate=0.0,
        recovery_roi=None,  # Unexecuted
        expected_loss_before=10000.0,
        expected_loss_after=2000.0,
        expected_loss_reduction=8000.0,
        expected_loss_reduction_percentage=80.0,
        decision_confidence=0.90,
        selected_action="ROUTE_SWITCH:UPI + Bank_B + Android",
        attempted_transactions=0,
        successful_recoveries=0,
        failed_recoveries=0,
        canary_decision="PENDING",
        guardrail_decision="PENDING",
        rollback_required=False,
        final_status="NOT_EXECUTED",
        safety_allowed=False,
        human_review_required=True,
        safety_reason="Human review required",
        learned_attempts=0,
        learned_recoveries=0,
        learned_recovery_rate=0.0,
        learning_evidence_confidence=0.0,
        route_score_before_learning=0.80,
        route_score_after_learning=0.80,
        learning_score_delta=0.0,
        decision_changed_after_learning=False,
    )

    snapshot = build_evaluation_snapshot(
        scorecard=scorecard,
        run_detection_benchmark_if_none=False,
    )

    assert snapshot.has_executed is False
    assert snapshot.recovery_roi is None
    assert snapshot.attempted_transactions == 0

    summary = snapshot.to_summary()
    assert summary.net_recovered_display == "Not executed"
    assert summary.recovery_rate_display == "Not executed"
    assert summary.recovery_roi_display == "N/A"
    assert summary.safety_status == "HUMAN_REVIEW_REQUIRED"


def test_zero_execution_cost_with_zero_recovered():
    """
    5. Execution cost zero with non-executed returns explicit N/A.
    """
    snapshot = build_evaluation_snapshot(
        scorecard=None,
        run_detection_benchmark_if_none=False,
    )
    summary = snapshot.to_summary()
    assert summary.recovery_roi_display == "N/A"
    assert summary.net_recovered_display == "Not executed"


def test_no_nan_or_inf_in_snapshot():
    """
    6. No NaN or Inf across all numeric snapshot and summary fields.
    """
    snapshot = build_evaluation_snapshot(run_detection_benchmark_if_none=True)
    summary = snapshot.to_summary()

    snapshot_dict = snapshot.to_dict()
    for k, v in snapshot_dict.items():
        if isinstance(v, float):
            assert not math.isnan(v), f"Snapshot field '{k}' is NaN!"
            assert not math.isinf(v), f"Snapshot field '{k}' is Inf!"

    summary_dict = summary.to_dict()
    for k, v in summary_dict.items():
        if isinstance(v, float):
            assert not math.isnan(v), f"Summary field '{k}' is NaN!"
            assert not math.isinf(v), f"Summary field '{k}' is Inf!"


def test_benchmark_independence_and_no_decision_leakage():
    """
    7. Benchmark is completely isolated — running the benchmark produces NO side-effects
    on runtime decision engine or route scoring.
    """
    engine = IncidentDecisionEngine()
    # Baseline evaluation before benchmark
    eval_before = engine.evaluate(
        incident_route="UPI + Bank_A + Android",
        transactions_affected=50,
        failures_observed=20,
        baseline_success_rate=0.95,
        current_success_rate=0.60,
        severity="DEGRADED",
        average_transaction_value=500.0,
        route_candidates=[
            {
                "route": "UPI + Bank_B + Android",
                "transactions": 50,
                "successes": 48,
            }
        ],
    )

    # Run independent benchmark multiple times
    benchmark = IncidentDetectionBenchmark()
    res1 = benchmark.run_benchmark()
    res2 = benchmark.run_benchmark()

    # Re-evaluate runtime decision
    eval_after = engine.evaluate(
        incident_route="UPI + Bank_A + Android",
        transactions_affected=50,
        failures_observed=20,
        baseline_success_rate=0.95,
        current_success_rate=0.60,
        severity="DEGRADED",
        average_transaction_value=500.0,
        route_candidates=[
            {
                "route": "UPI + Bank_B + Android",
                "transactions": 50,
                "successes": 48,
            }
        ],
    )

    assert (
        eval_before.decision.recommended_action
        == eval_after.decision.recommended_action
    )
    assert eval_before.decision.confidence == eval_after.decision.confidence
    assert (
        eval_before.safety_decision.allowed
        == eval_after.safety_decision.allowed
    )


def test_judge_summary_hierarchy_and_pillars():
    """
    8. Judge summary exposes metrics in the exact requested hierarchy:
    1. Incident Detection
    2. Financial Impact
    3. Decision Quality
    4. Safety
    5. Learning
    """
    snapshot = build_evaluation_snapshot(run_detection_benchmark_if_none=True)
    summary = snapshot.to_summary()

    # Pillar 1: Detection
    assert summary.detection_precision >= 0.0
    assert summary.detection_recall >= 0.0
    assert summary.detection_f1 >= 0.0
    assert summary.detection_specificity >= 0.0

    # Pillar 2: Financial
    assert "₹" in summary.revenue_at_risk_display
    assert summary.net_recovered_display is not None

    # Pillar 3: Decision
    assert summary.selected_action is not None
    assert "%" in summary.decision_confidence_display

    # Pillar 4: Safety
    assert summary.safety_status in ("ALLOWED", "BLOCKED", "HUMAN_REVIEW_REQUIRED")
    assert summary.guardrail_status is not None

    # Pillar 5: Learning
    assert summary.score_lift_display is not None
    assert summary.decision_changed_display in ("YES", "NO")
