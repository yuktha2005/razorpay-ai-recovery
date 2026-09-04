"""
Evaluation snapshot module for Razorpay AI Revenue Recovery.

Bridges isolated incident detection benchmarks, authoritative system evaluation
scorecards, and judge-facing evaluation summaries with strict provenance tracking.

Architecture:
- The detection benchmark remains an isolated, independent evaluator.
- Runtime decision-making NEVER consumes benchmark ground truth or metrics.
- Metric provenance is strictly categorized as:
  * OBSERVED: Ground-truth runtime incident telemetry.
  * THEORETICAL / COUNTERFACTUAL: Pre-intervention risk and mathematical loss projections.
  * SIMULATED: Bounded canary and circuit-breaker batch execution outcomes.
  * GOVERNED / EVALUATED: Deterministic safety policy decisions and constraints.
  * LEARNED: Outcome-driven Bayesian evidence and routing lift.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional

from src.evaluation.detection_benchmark import (
    DetectionBenchmarkResult,
    IncidentDetectionBenchmark,
)
from src.evaluation.evaluation_adapter import build_system_evaluation_scorecard
from src.evaluation.scorecard import (
    METRIC_PROVENANCE,
    SystemEvaluationScorecard,
    build_scorecard,
)


class MetricProvenanceCategory(str, Enum):
    """Authoritative semantic categories for metric provenance."""

    OBSERVED = "OBSERVED"
    THEORETICAL = "THEORETICAL / COUNTERFACTUAL"
    SIMULATED = "SIMULATED"
    GOVERNED = "GOVERNED / EVALUATED"
    LEARNED = "LEARNED"


# Complete provenance dictionary for all snapshot fields
SNAPSHOT_METRIC_PROVENANCE: Dict[str, str] = {
    # 1. DETECTION (EVALUATED / BENCHMARK)
    "benchmark_total_cases": "GOVERNED / EVALUATED",
    "benchmark_tp": "GOVERNED / EVALUATED",
    "benchmark_tn": "GOVERNED / EVALUATED",
    "benchmark_fp": "GOVERNED / EVALUATED",
    "benchmark_fn": "GOVERNED / EVALUATED",
    "benchmark_precision": "GOVERNED / EVALUATED",
    "benchmark_recall": "GOVERNED / EVALUATED",
    "benchmark_f1": "GOVERNED / EVALUATED",
    "benchmark_specificity": "GOVERNED / EVALUATED",
    "benchmark_accuracy": "GOVERNED / EVALUATED",
    # 2. INCIDENT (OBSERVED)
    "degradation_percentage_points": "OBSERVED",
    "severity": "OBSERVED",
    "transactions_observed": "OBSERVED",
    "incident_detected": "OBSERVED",
    # 3. FINANCIAL (THEORETICAL vs SIMULATED)
    "revenue_at_risk": "THEORETICAL / COUNTERFACTUAL",
    "eligible_amount": "THEORETICAL / COUNTERFACTUAL",
    "expected_loss_before": "THEORETICAL / COUNTERFACTUAL",
    "expected_loss_after": "THEORETICAL / COUNTERFACTUAL",
    "expected_loss_reduction": "THEORETICAL / COUNTERFACTUAL",
    "expected_loss_reduction_percentage": "THEORETICAL / COUNTERFACTUAL",
    "attempted_amount": "SIMULATED",
    "recovered_amount": "SIMULATED",
    "execution_cost": "SIMULATED",
    "net_recovered_value": "SIMULATED",
    "recovery_rate": "SIMULATED",
    "recovery_roi": "SIMULATED",
    # 4. DECISION (GOVERNED / EVALUATED)
    "selected_action": "GOVERNED / EVALUATED",
    "decision_confidence": "GOVERNED / EVALUATED",
    # 5. RECOVERY (SIMULATED)
    "attempted_transactions": "SIMULATED",
    "successful_recoveries": "SIMULATED",
    "failed_recoveries": "SIMULATED",
    "canary_decision": "SIMULATED",
    "guardrail_decision": "SIMULATED",
    "rollback_required": "SIMULATED",
    "final_status": "SIMULATED",
    # 6. SAFETY (GOVERNED / EVALUATED)
    "safety_allowed": "GOVERNED / EVALUATED",
    "human_review_required": "GOVERNED / EVALUATED",
    "safety_reason": "GOVERNED / EVALUATED",
    # 7. LEARNING (LEARNED)
    "learned_attempts": "LEARNED",
    "learned_recoveries": "LEARNED",
    "learned_recovery_rate": "LEARNED",
    "learning_evidence_confidence": "LEARNED",
    "route_score_before_learning": "LEARNED",
    "route_score_after_learning": "LEARNED",
    "learning_score_delta": "LEARNED",
    "decision_changed_after_learning": "LEARNED",
}


@dataclass
class JudgeEvaluationSummary:
    """
    Formatted, deterministic evaluation summary structured across the 5 core pillars.
    """

    # 1. Incident Detection Benchmark
    detection_precision: float
    detection_recall: float
    detection_f1: float
    detection_specificity: float
    detection_accuracy: float
    detection_confusion_matrix: Dict[str, int]

    # 2. Financial Impact
    revenue_at_risk_display: str
    net_recovered_display: str
    recovery_rate_display: str
    recovery_roi_display: str

    # 3. Decision Quality
    expected_loss_reduction_display: str
    decision_confidence_display: str
    selected_action: str

    # 4. Safety
    safety_status: str
    human_review_status: str
    guardrail_status: str
    rollback_status: str

    # 5. Learning
    learning_evidence_display: str
    score_lift_display: str
    decision_changed_display: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationSnapshot:
    """
    Unified, deterministic evaluation snapshot bridging detection benchmarks,
    financial metrics, decision governance, bounded recovery, and closed-loop learning.
    """

    # 1. Detection Benchmark Metrics
    benchmark_total_cases: int
    benchmark_tp: int
    benchmark_tn: int
    benchmark_fp: int
    benchmark_fn: int
    benchmark_precision: float
    benchmark_recall: float
    benchmark_f1: float
    benchmark_specificity: float
    benchmark_accuracy: float

    # 2. Incident Telemetry (OBSERVED)
    degradation_percentage_points: float
    severity: str
    transactions_observed: int
    incident_detected: bool

    # 3. Financial Economics (THEORETICAL vs SIMULATED)
    revenue_at_risk: float
    eligible_amount: float
    expected_loss_before: float
    expected_loss_after: float
    expected_loss_reduction: float
    expected_loss_reduction_percentage: float
    attempted_amount: float
    recovered_amount: float
    execution_cost: float
    net_recovered_value: float
    recovery_rate: float
    recovery_roi: Optional[float]

    # 4. Decision Quality (GOVERNED / EVALUATED)
    selected_action: str
    decision_confidence: float

    # 5. Bounded Recovery Execution (SIMULATED)
    attempted_transactions: int
    successful_recoveries: int
    failed_recoveries: int
    canary_decision: str
    guardrail_decision: str
    rollback_required: bool
    final_status: str

    # 6. Safety Policy Controls (GOVERNED / EVALUATED)
    safety_allowed: bool
    human_review_required: bool
    safety_reason: str

    # 7. Closed-Loop Learning (LEARNED)
    learned_attempts: int
    learned_recoveries: int
    learned_recovery_rate: float
    learning_evidence_confidence: float
    route_score_before_learning: float
    route_score_after_learning: float
    learning_score_delta: float
    decision_changed_after_learning: bool

    # Retain reference to underlying authoritative scorecard
    scorecard: Optional[SystemEvaluationScorecard] = None
    benchmark_result: Optional[DetectionBenchmarkResult] = None

    @classmethod
    def get_provenance(cls, metric_name: str) -> str:
        """Retrieve authoritative provenance category for a given metric field."""
        return SNAPSHOT_METRIC_PROVENANCE.get(metric_name, "UNSPECIFIED")

    @property
    def has_executed(self) -> bool:
        """True if bounded recovery simulation has executed transactions."""
        return self.attempted_transactions > 0

    @property
    def has_learning_evidence(self) -> bool:
        """True if verified learning evidence has been accumulated."""
        return self.learned_attempts > 0

    @property
    def precision(self) -> float:
        return self.benchmark_precision

    @property
    def recall(self) -> float:
        return self.benchmark_recall

    @property
    def f1(self) -> float:
        return self.benchmark_f1

    @property
    def specificity(self) -> float:
        return self.benchmark_specificity

    @property
    def accuracy(self) -> float:
        return self.benchmark_accuracy

    @property
    def detection(self) -> Dict[str, Any]:
        """Detection pillar dictionary."""
        return {
            "total_cases": self.benchmark_total_cases,
            "true_positives": self.benchmark_tp,
            "true_negatives": self.benchmark_tn,
            "false_positives": self.benchmark_fp,
            "false_negatives": self.benchmark_fn,
            "precision": self.benchmark_precision,
            "recall": self.benchmark_recall,
            "f1": self.benchmark_f1,
            "specificity": self.benchmark_specificity,
            "accuracy": self.benchmark_accuracy,
            "provenance": MetricProvenanceCategory.GOVERNED.value,
        }

    @property
    def financial(self) -> Dict[str, Any]:
        """Financial pillar dictionary."""
        return {
            "revenue_at_risk": self.revenue_at_risk,
            "eligible_amount": self.eligible_amount,
            "expected_loss_before": self.expected_loss_before,
            "expected_loss_after": self.expected_loss_after,
            "expected_loss_reduction": self.expected_loss_reduction,
            "attempted_amount": self.attempted_amount,
            "recovered_amount": self.recovered_amount,
            "execution_cost": self.execution_cost,
            "net_recovered_value": self.net_recovered_value,
            "recovery_rate": self.recovery_rate,
            "recovery_roi": self.recovery_roi,
            "has_executed": self.has_executed,
        }

    @property
    def decision(self) -> Dict[str, Any]:
        """Decision pillar dictionary."""
        return {
            "selected_action": self.selected_action,
            "confidence": self.decision_confidence,
            "expected_loss_reduction": self.expected_loss_reduction,
            "expected_loss_reduction_percentage": self.expected_loss_reduction_percentage,
        }

    @property
    def safety(self) -> Dict[str, Any]:
        """Safety pillar dictionary."""
        return {
            "allowed": self.safety_allowed,
            "requires_human_review": self.human_review_required,
            "reason": self.safety_reason,
            "canary_decision": self.canary_decision,
            "guardrail_decision": self.guardrail_decision,
            "rollback_required": self.rollback_required,
            "final_status": self.final_status,
        }

    @property
    def learning(self) -> Dict[str, Any]:
        """Learning pillar dictionary."""
        return {
            "learned_attempts": self.learned_attempts,
            "learned_recoveries": self.learned_recoveries,
            "learned_recovery_rate": self.learned_recovery_rate,
            "learning_evidence_confidence": self.learning_evidence_confidence,
            "route_score_before_learning": self.route_score_before_learning,
            "route_score_after_learning": self.route_score_after_learning,
            "learning_score_delta": self.learning_score_delta,
            "decision_changed_after_learning": self.decision_changed_after_learning,
            "has_learning_evidence": self.has_learning_evidence,
        }

    def to_summary(self) -> JudgeEvaluationSummary:
        """
        Generate a clean, formatted JudgeEvaluationSummary exposing the strongest
        metrics across all 5 pillars in the requested judge presentation hierarchy.
        """
        # Financial formatting
        rev_risk_str = f"₹{self.revenue_at_risk:,.2f}"
        if self.has_executed:
            net_rec_str = f"₹{self.net_recovered_value:,.2f}"
            rec_rate_str = f"{self.recovery_rate * 100:.1f}%"
            if self.recovery_roi is not None and not math.isnan(self.recovery_roi):
                roi_str = f"{self.recovery_roi:.1f}x"
            else:
                roi_str = "ROI: N/A — no execution cost recorded"
        else:
            net_rec_str = "Not executed"
            rec_rate_str = "Not executed"
            roi_str = "N/A"

        # Decision formatting
        loss_red_str = (
            f"₹{self.expected_loss_reduction:,.2f} ({self.expected_loss_reduction_percentage:.1f}%)"
            if self.expected_loss_reduction > 0
            else "₹0.00 (0.0%)"
        )
        conf_str = f"{self.decision_confidence * 100:.1f}%"

        # Safety formatting
        if self.safety_allowed:
            safety_st = "ALLOWED"
        elif self.human_review_required:
            safety_st = "HUMAN_REVIEW_REQUIRED"
        else:
            safety_st = "BLOCKED"

        human_st = "Required" if self.human_review_required else "Not required"
        rollback_st = "TRIGGERED" if self.rollback_required else "None"

        # Learning formatting
        if self.has_learning_evidence:
            learn_ev_str = (
                f"{self.learned_recoveries}/{self.learned_attempts} "
                f"({self.learned_recovery_rate * 100:.1f}% recovery, {self.learning_evidence_confidence * 100:.1f}% confidence)"
            )
            score_lift_str = f"{self.learning_score_delta:+.4f}"
        else:
            learn_ev_str = "No verified recovery evidence"
            score_lift_str = "No lift measured"

        decision_ch_str = "YES" if self.decision_changed_after_learning else "NO"

        return JudgeEvaluationSummary(
            detection_precision=self.benchmark_precision,
            detection_recall=self.benchmark_recall,
            detection_f1=self.benchmark_f1,
            detection_specificity=self.benchmark_specificity,
            detection_accuracy=self.benchmark_accuracy,
            detection_confusion_matrix={
                "TP": self.benchmark_tp,
                "TN": self.benchmark_tn,
                "FP": self.benchmark_fp,
                "FN": self.benchmark_fn,
            },
            revenue_at_risk_display=rev_risk_str,
            net_recovered_display=net_rec_str,
            recovery_rate_display=rec_rate_str,
            recovery_roi_display=roi_str,
            expected_loss_reduction_display=loss_red_str,
            decision_confidence_display=conf_str,
            selected_action=self.selected_action,
            safety_status=safety_st,
            human_review_status=human_st,
            guardrail_status=self.guardrail_decision,
            rollback_status=rollback_st,
            learning_evidence_display=learn_ev_str,
            score_lift_display=score_lift_str,
            decision_changed_display=decision_ch_str,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary."""
        d = asdict(self)
        d.pop("scorecard", None)
        d.pop("benchmark_result", None)
        return d


def build_evaluation_snapshot(
    scorecard: Optional[SystemEvaluationScorecard] = None,
    benchmark_result: Optional[DetectionBenchmarkResult] = None,
    # Raw pipeline inputs if scorecard is not pre-constructed
    incident: Optional[Any] = None,
    decision: Optional[Any] = None,
    safety_decision: Optional[Any] = None,
    orchestration_result: Optional[Any] = None,
    learning_context: Optional[Any] = None,
    route_score_before: Optional[Any] = None,
    route_score_after: Optional[Any] = None,
    revenue_impact: Optional[Any] = None,
    eligible_amount: Optional[float] = None,
    run_detection_benchmark_if_none: bool = True,
) -> EvaluationSnapshot:
    """
    Construct a deterministic EvaluationSnapshot from a SystemEvaluationScorecard
    and an isolated DetectionBenchmarkResult.

    Parameters
    ----------
    scorecard : Optional[SystemEvaluationScorecard]
        Authoritative system scorecard. If None, built from provided pipeline inputs.
    benchmark_result : Optional[DetectionBenchmarkResult]
        Isolated benchmark result. If None and run_detection_benchmark_if_none is True,
        computed independently via IncidentDetectionBenchmark.
    incident ... eligible_amount : Optional[Any]
        Fallback pipeline stage inputs to build scorecard if not directly provided.
    run_detection_benchmark_if_none : bool
        Whether to execute the deterministic benchmark if benchmark_result is None.

    Returns
    -------
    EvaluationSnapshot
        Complete, unified evaluation snapshot with provenance tracking.
    """
    # 1. Resolve authoritative SystemEvaluationScorecard
    if scorecard is None:
        if incident is not None:
            scorecard = build_system_evaluation_scorecard(
                incident=incident,
                decision=decision,
                safety_decision=safety_decision,
                orchestration_result=orchestration_result,
                learning_context=learning_context,
                route_score_before=route_score_before,
                route_score_after=route_score_after,
                revenue_impact=revenue_impact,
                eligible_amount=eligible_amount,
            )
        else:
            scorecard = build_scorecard(
                degradation_percentage_points=0.0,
                severity="NORMAL",
                transactions_observed=0,
                incident_detected=False,
                revenue_at_risk=0.0,
                eligible_amount=0.0,
                attempted_amount=0.0,
                recovered_amount=0.0,
                execution_cost=0.0,
                net_recovered_value=0.0,
                recovery_rate=0.0,
                recovery_roi=None,
                expected_loss_before=0.0,
                expected_loss_after=0.0,
                expected_loss_reduction=0.0,
                expected_loss_reduction_percentage=0.0,
                decision_confidence=0.0,
                selected_action="MONITOR",
                attempted_transactions=0,
                successful_recoveries=0,
                failed_recoveries=0,
                canary_decision="NOT_APPLICABLE",
                guardrail_decision="NOT_RECORDED",
                rollback_required=False,
                final_status="NOT_EXECUTED",
                safety_allowed=True,
                human_review_required=False,
                safety_reason="No incident evaluated",
                learned_attempts=0,
                learned_recoveries=0,
                learned_recovery_rate=0.0,
                learning_evidence_confidence=0.0,
                route_score_before_learning=0.0,
                route_score_after_learning=0.0,
                learning_score_delta=0.0,
                decision_changed_after_learning=False,
            )

    # 2. Resolve isolated DetectionBenchmarkResult
    if benchmark_result is None:
        if run_detection_benchmark_if_none:
            benchmark = IncidentDetectionBenchmark()
            benchmark_result = benchmark.run_benchmark()
        else:
            benchmark_result = DetectionBenchmarkResult(
                total_cases=0,
                true_positives=0,
                true_negatives=0,
                false_positives=0,
                false_negatives=0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                specificity=0.0,
                detection_accuracy=0.0,
            )

    # 3. Assemble unified EvaluationSnapshot
    return EvaluationSnapshot(
        benchmark_total_cases=int(benchmark_result.total_cases),
        benchmark_tp=int(benchmark_result.true_positives),
        benchmark_tn=int(benchmark_result.true_negatives),
        benchmark_fp=int(benchmark_result.false_positives),
        benchmark_fn=int(benchmark_result.false_negatives),
        benchmark_precision=float(benchmark_result.precision),
        benchmark_recall=float(benchmark_result.recall),
        benchmark_f1=float(benchmark_result.f1_score),
        benchmark_specificity=float(benchmark_result.specificity),
        benchmark_accuracy=float(benchmark_result.detection_accuracy),
        degradation_percentage_points=float(scorecard.degradation_percentage_points),
        severity=str(scorecard.severity),
        transactions_observed=int(scorecard.transactions_observed),
        incident_detected=bool(scorecard.incident_detected),
        revenue_at_risk=float(scorecard.revenue_at_risk),
        eligible_amount=float(scorecard.eligible_amount),
        expected_loss_before=float(scorecard.expected_loss_before),
        expected_loss_after=float(scorecard.expected_loss_after),
        expected_loss_reduction=float(scorecard.expected_loss_reduction),
        expected_loss_reduction_percentage=float(
            scorecard.expected_loss_reduction_percentage
        ),
        attempted_amount=float(scorecard.attempted_amount),
        recovered_amount=float(scorecard.recovered_amount),
        execution_cost=float(scorecard.execution_cost),
        net_recovered_value=float(scorecard.net_recovered_value),
        recovery_rate=float(scorecard.recovery_rate),
        recovery_roi=(
            float(scorecard.recovery_roi)
            if scorecard.recovery_roi is not None
            and not math.isnan(scorecard.recovery_roi)
            else None
        ),
        selected_action=str(scorecard.selected_action),
        decision_confidence=float(scorecard.decision_confidence),
        attempted_transactions=int(scorecard.attempted_transactions),
        successful_recoveries=int(scorecard.successful_recoveries),
        failed_recoveries=int(scorecard.failed_recoveries),
        canary_decision=str(scorecard.canary_decision),
        guardrail_decision=str(scorecard.guardrail_decision),
        rollback_required=bool(scorecard.rollback_required),
        final_status=str(scorecard.final_status),
        safety_allowed=bool(scorecard.safety_allowed),
        human_review_required=bool(scorecard.human_review_required),
        safety_reason=str(scorecard.safety_reason),
        learned_attempts=int(scorecard.learned_attempts),
        learned_recoveries=int(scorecard.learned_recoveries),
        learned_recovery_rate=float(scorecard.learned_recovery_rate),
        learning_evidence_confidence=float(scorecard.learning_evidence_confidence),
        route_score_before_learning=float(scorecard.route_score_before_learning),
        route_score_after_learning=float(scorecard.route_score_after_learning),
        learning_score_delta=float(scorecard.learning_score_delta),
        decision_changed_after_learning=bool(
            scorecard.decision_changed_after_learning
        ),
        scorecard=scorecard,
        benchmark_result=benchmark_result,
    )
