import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from src.intelligence.incident_intelligence import (
    IncidentAssessment,
    IncidentIntelligence,
)


def _safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division returning default if denominator is zero or invalid."""
    if denominator == 0 or math.isnan(denominator) or math.isinf(denominator):
        return default
    try:
        val = numerator / denominator
        if math.isnan(val) or math.isinf(val):
            return default
        return val
    except (ZeroDivisionError, ValueError, TypeError):
        return default


@dataclass
class BenchmarkCaseResult:
    """
    Evaluation result for a single incident detection scenario.

    Ground truth comes strictly from the benchmark scenario definition,
    never from the detector's output.
    """

    case_id: str
    description: str
    ground_truth_incident: bool
    detector_incident_detected: bool
    classification: str  # "TP", "TN", "FP", "FN"
    observed_success_rate: float
    baseline_success_rate: float
    degradation_percentage_points: float
    transaction_count: int
    resulting_detector_severity: str
    expected_severity: Optional[str] = None
    route: str = ""

    @property
    def expected_incident(self) -> bool:
        return self.ground_truth_incident

    @property
    def detected_incident(self) -> bool:
        return self.detector_incident_detected

    @property
    def detected_severity(self) -> str:
        return self.resulting_detector_severity

    @property
    def passed(self) -> bool:
        return self.classification in ("TP", "TN")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DetectionBenchmarkResult:
    """
    Deterministic evaluation results across an incident detection benchmark suite.
    """

    total_cases: int
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    specificity: float
    detection_accuracy: float
    cases: List[BenchmarkCaseResult] = field(default_factory=list)

    @property
    def f1(self) -> float:
        return self.f1_score

    @property
    def case_results(self) -> List[BenchmarkCaseResult]:
        return self.cases

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkScenario:
    """
    Specification of a single benchmark scenario with independent ground truth.
    """

    scenario_id: str
    name: str
    description: str
    ground_truth_incident: bool
    transactions: pd.DataFrame
    baseline_success_rate: float
    expected_severity: Optional[str] = None
    route_name: Optional[str] = None


def create_deterministic_window(
    total_transactions: int,
    failures: int,
    route: str = "UPI + Bank_A + Android",
    window_minutes: int = 15,
    base_timestamp: str = "2026-07-23 19:15:00",
) -> pd.DataFrame:
    """
    Create a deterministic payment window DataFrame without random numbers
    or wall-clock time dependencies.
    """
    parts = [p.strip() for p in route.split("+")]
    payment_method = parts[0] if len(parts) > 0 else "UPI"
    bank = parts[1] if len(parts) > 1 else "Bank_A"
    device_type = parts[2] if len(parts) > 2 else "Android"

    end_time = pd.Timestamp(base_timestamp)
    start_time = end_time - pd.Timedelta(minutes=window_minutes)

    if total_transactions > 1:
        timestamps = pd.date_range(
            start=start_time + pd.Timedelta(seconds=1),
            end=end_time,
            periods=total_transactions,
        )
    elif total_transactions == 1:
        timestamps = [end_time]
    else:
        timestamps = []

    failures = min(total_transactions, max(0, failures))
    successes = total_transactions - failures
    statuses = ["SUCCESS"] * successes + ["FAILED"] * failures

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "status": statuses,
            "payment_method": payment_method,
            "bank": bank,
            "device_type": device_type,
        }
    )


class IncidentDetectionBenchmark:
    """
    Deterministic evaluation harness for the IncidentIntelligence detector.

    Measures how accurately the detector distinguishes clean traffic from
    controlled injected incidents without circular ground-truth definitions.
    """

    def __init__(
        self,
        detector: Optional[IncidentIntelligence] = None,
        default_baseline_success_rate: float = 0.95,
    ):
        self.detector = detector or IncidentIntelligence()
        self.default_baseline = default_baseline_success_rate

    @staticmethod
    def build_default_scenarios(
        baseline_success_rate: float = 0.95,
    ) -> List[BenchmarkScenario]:
        """
        Build a compact, deterministic suite of 10 benchmark scenarios covering:
        1. Clean high-volume window
        2. Clean perfect health window
        3. Clean background noise window
        4. Clean low-volume window
        5. Moderate degradation (DEGRADED threshold)
        6. Severe degradation (CRITICAL threshold)
        7. Acute outage (CRITICAL threshold)
        8. Mild degradation (WATCH threshold behavior)
        9. Boundary: degraded degradation below min transactions threshold
        10. Boundary: near-critical just reaching degraded transaction threshold
        """
        scenarios = []

        # 1. Clean healthy high volume
        df1 = create_deterministic_window(
            total_transactions=100,
            failures=5,  # 95.0% success rate -> 0.0 pp drop
            route="UPI + Bank_A + Android",
        )
        scenarios.append(
            BenchmarkScenario(
                scenario_id="CLEAN_HIGH_VOLUME",
                name="Clean High-Volume Traffic",
                description="Normal traffic matching 95.0% baseline across 100 transactions.",
                ground_truth_incident=False,
                transactions=df1,
                baseline_success_rate=baseline_success_rate,
                expected_severity="NORMAL",
            )
        )

        # 2. Clean perfect health
        df2 = create_deterministic_window(
            total_transactions=60,
            failures=0,  # 100% success rate -> negative degradation
            route="UPI + Bank_B + Android",
        )
        scenarios.append(
            BenchmarkScenario(
                scenario_id="CLEAN_PERFECT_HEALTH",
                name="Clean Perfect Health Traffic",
                description="Zero failures across 60 transactions exceeding baseline.",
                ground_truth_incident=False,
                transactions=df2,
                baseline_success_rate=baseline_success_rate,
                expected_severity="NORMAL",
            )
        )

        # 3. Clean background noise
        df3 = create_deterministic_window(
            total_transactions=50,
            failures=4,  # 92.0% success rate -> 3.0 pp drop (< 5 pp WATCH threshold)
            route="UPI + Bank_C + Android",
        )
        scenarios.append(
            BenchmarkScenario(
                scenario_id="CLEAN_BACKGROUND_NOISE",
                name="Clean Traffic with Minor Fluctuations",
                description="Minor 3.0 pp fluctuation under normal operational noise.",
                ground_truth_incident=False,
                transactions=df3,
                baseline_success_rate=baseline_success_rate,
                expected_severity="NORMAL",
            )
        )

        # 4. Clean low volume
        df4 = create_deterministic_window(
            total_transactions=18,
            failures=1,  # 94.44% success rate -> 0.56 pp drop
            route="UPI + Bank_D + Android",
        )
        scenarios.append(
            BenchmarkScenario(
                scenario_id="CLEAN_LOW_VOLUME",
                name="Clean Low-Volume Traffic",
                description="Normal low-volume route with 1 failure in 18 transactions.",
                ground_truth_incident=False,
                transactions=df4,
                baseline_success_rate=baseline_success_rate,
                expected_severity="NORMAL",
            )
        )

        # 5. Moderate degradation
        df5 = create_deterministic_window(
            total_transactions=40,
            failures=9,  # 77.5% success rate -> 17.5 pp drop (>= 10 pp, >= 30 txns)
            route="UPI + Bank_E + Android",
        )
        scenarios.append(
            BenchmarkScenario(
                scenario_id="MODERATE_DEGRADATION",
                name="Moderate Route Degradation",
                description="17.5 pp degradation across 40 transactions crossing DEGRADED threshold.",
                ground_truth_incident=True,
                transactions=df5,
                baseline_success_rate=baseline_success_rate,
                expected_severity="DEGRADED",
            )
        )

        # 6. Severe degradation (Critical)
        df6 = create_deterministic_window(
            total_transactions=80,
            failures=28,  # 65.0% success rate -> 30.0 pp drop (>= 20 pp, >= 50 txns)
            route="UPI + Bank_F + Android",
        )
        scenarios.append(
            BenchmarkScenario(
                scenario_id="SEVERE_DEGRADATION_CRITICAL",
                name="Severe Route Degradation",
                description="30.0 pp degradation across 80 transactions crossing CRITICAL threshold.",
                ground_truth_incident=True,
                transactions=df6,
                baseline_success_rate=baseline_success_rate,
                expected_severity="CRITICAL",
            )
        )

        # 7. Acute outage (Critical)
        df7 = create_deterministic_window(
            total_transactions=60,
            failures=45,  # 25.0% success rate -> 70.0 pp drop
            route="UPI + Bank_G + Android",
        )
        scenarios.append(
            BenchmarkScenario(
                scenario_id="ACUTE_OUTAGE_CRITICAL",
                name="Acute Bank Gateway Outage",
                description="70.0 pp collapse in success rate indicating major gateway incident.",
                ground_truth_incident=True,
                transactions=df7,
                baseline_success_rate=baseline_success_rate,
                expected_severity="CRITICAL",
            )
        )

        # 8. Mild degradation (WATCH behavior)
        df8 = create_deterministic_window(
            total_transactions=25,
            failures=3,  # 88.0% success rate -> 7.0 pp drop (>= 5 pp, >= 20 txns)
            route="UPI + Bank_H + Android",
        )
        scenarios.append(
            BenchmarkScenario(
                scenario_id="MILD_DEGRADATION_WATCH",
                name="Mild Route Degradation (Watch Status)",
                description="7.0 pp drop across 25 transactions crossing WATCH threshold (advisory).",
                ground_truth_incident=True,
                transactions=df8,
                baseline_success_rate=baseline_success_rate,
                expected_severity="WATCH",
            )
        )

        # 9. Boundary: degraded degradation below min transactions threshold
        df9 = create_deterministic_window(
            total_transactions=25,
            failures=4,  # 84.0% success rate -> 11.0 pp drop (>= 10 pp, BUT txns < 30)
            route="UPI + Bank_I + Android",
        )
        scenarios.append(
            BenchmarkScenario(
                scenario_id="BOUNDARY_BELOW_TXN_THRESHOLD",
                name="Degraded Drop with Insufficient Volume",
                description="11.0 pp drop but only 25 transactions (insufficient for DEGRADED, stays WATCH).",
                ground_truth_incident=True,
                transactions=df9,
                baseline_success_rate=baseline_success_rate,
                expected_severity="WATCH",
            )
        )

        # 10. Boundary: near-critical just reaching degraded threshold
        df10 = create_deterministic_window(
            total_transactions=50,
            failures=11,  # 78.0% success rate -> 17.0 pp drop (>= 10 pp and >= 30 txns, but < 20 pp)
            route="UPI + Bank_J + Android",
        )
        scenarios.append(
            BenchmarkScenario(
                scenario_id="BOUNDARY_REACHING_DEGRADED",
                name="Volume Sufficient for Degraded Classification",
                description="17.0 pp drop with 50 transactions correctly categorized as DEGRADED.",
                ground_truth_incident=True,
                transactions=df10,
                baseline_success_rate=baseline_success_rate,
                expected_severity="DEGRADED",
            )
        )

        return scenarios

    def evaluate_scenario(
        self,
        scenario: BenchmarkScenario,
    ) -> BenchmarkCaseResult:
        """
        Evaluate a single scenario against the detector.

        Preserves independent ground truth without circular dependency.
        """
        assessment: IncidentAssessment = self.detector.assess(
            scenario.transactions,
            baseline_success_rate=scenario.baseline_success_rate,
        )

        # Ground truth is strictly from scenario definition
        gt = scenario.ground_truth_incident
        pred = assessment.incident_detected

        if gt and pred:
            classification = "TP"
        elif not gt and not pred:
            classification = "TN"
        elif not gt and pred:
            classification = "FP"
        else:  # gt and not pred
            classification = "FN"

        return BenchmarkCaseResult(
            case_id=scenario.scenario_id,
            description=scenario.description,
            ground_truth_incident=gt,
            detector_incident_detected=pred,
            classification=classification,
            observed_success_rate=float(round(assessment.current_success_rate, 4)),
            baseline_success_rate=float(round(assessment.baseline_success_rate, 4)),
            degradation_percentage_points=float(round(assessment.degradation_pp, 2)),
            transaction_count=int(assessment.transactions_observed),
            resulting_detector_severity=assessment.severity,
            expected_severity=scenario.expected_severity,
            route=assessment.route,
        )

    def run_benchmark(
        self,
        scenarios: Optional[List[BenchmarkScenario]] = None,
    ) -> DetectionBenchmarkResult:
        """
        Execute the benchmark suite and compute deterministic classification metrics.
        """
        if scenarios is None:
            scenarios = self.build_default_scenarios(
                baseline_success_rate=self.default_baseline
            )

        case_results = []
        tp = 0
        tn = 0
        fp = 0
        fn = 0

        for scenario in scenarios:
            case_res = self.evaluate_scenario(scenario)
            case_results.append(case_res)
            if case_res.classification == "TP":
                tp += 1
            elif case_res.classification == "TN":
                tn += 1
            elif case_res.classification == "FP":
                fp += 1
            elif case_res.classification == "FN":
                fn += 1

        total_cases = len(scenarios)

        # Metrics with safe zero-denominator protection
        precision = round(_safe_divide(tp, tp + fp, 0.0), 4)
        recall = round(_safe_divide(tp, tp + fn, 0.0), 4)
        f1_score = round(
            _safe_divide(2 * precision * recall, precision + recall, 0.0), 4
        )
        specificity = round(_safe_divide(tn, tn + fp, 0.0), 4)
        accuracy = round(_safe_divide(tp + tn, total_cases, 0.0), 4)

        return DetectionBenchmarkResult(
            total_cases=total_cases,
            true_positives=tp,
            true_negatives=tn,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            specificity=specificity,
            detection_accuracy=accuracy,
            cases=case_results,
        )


def benchmark_to_detection_summary(
    result: DetectionBenchmarkResult,
) -> Dict[str, Any]:
    """
    Helper converting a DetectionBenchmarkResult into a summary dictionary.
    """
    return {
        "total_cases": result.total_cases,
        "true_positives": result.true_positives,
        "true_negatives": result.true_negatives,
        "false_positives": result.false_positives,
        "false_negatives": result.false_negatives,
        "precision": result.precision,
        "recall": result.recall,
        "f1_score": result.f1_score,
        "specificity": result.specificity,
        "detection_accuracy": result.detection_accuracy,
    }
