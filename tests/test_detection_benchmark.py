import math
from unittest.mock import MagicMock
import pytest

from src.evaluation.detection_benchmark import (
    BenchmarkCaseResult,
    BenchmarkScenario,
    DetectionBenchmarkResult,
    IncidentDetectionBenchmark,
    benchmark_to_detection_summary,
    create_deterministic_window,
)
from src.intelligence.incident_intelligence import (
    IncidentAssessment,
    IncidentIntelligence,
)


def test_perfect_synthetic_classification():
    """
    1. Perfect synthetic classification.
    Verifies that when all positives are detected and all negatives are clear,
    TP>0, TN>0, FP=0, FN=0, yielding 1.0 (100%) for all metrics.
    """
    scenarios = [
        # Positive 1: Moderate degradation
        BenchmarkScenario(
            scenario_id="POS_MODERATE",
            name="Moderate Degradation",
            description="40 txns, 17.5 pp drop",
            ground_truth_incident=True,
            transactions=create_deterministic_window(
                total_transactions=40, failures=9
            ),
            baseline_success_rate=0.95,
        ),
        # Positive 2: Severe degradation
        BenchmarkScenario(
            scenario_id="POS_SEVERE",
            name="Severe Degradation",
            description="80 txns, 30 pp drop",
            ground_truth_incident=True,
            transactions=create_deterministic_window(
                total_transactions=80, failures=28
            ),
            baseline_success_rate=0.95,
        ),
        # Negative 1: Clean high volume
        BenchmarkScenario(
            scenario_id="NEG_HIGH_VOL",
            name="Clean High Volume",
            description="100 txns, 0 pp drop",
            ground_truth_incident=False,
            transactions=create_deterministic_window(
                total_transactions=100, failures=5
            ),
            baseline_success_rate=0.95,
        ),
        # Negative 2: Clean perfect
        BenchmarkScenario(
            scenario_id="NEG_PERFECT",
            name="Clean Perfect",
            description="50 txns, 0 failures",
            ground_truth_incident=False,
            transactions=create_deterministic_window(
                total_transactions=50, failures=0
            ),
            baseline_success_rate=0.95,
        ),
    ]

    benchmark = IncidentDetectionBenchmark()
    result = benchmark.run_benchmark(scenarios)

    assert result.total_cases == 4
    assert result.true_positives == 2
    assert result.true_negatives == 2
    assert result.false_positives == 0
    assert result.false_negatives == 0
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.f1_score == 1.0
    assert result.specificity == 1.0
    assert result.detection_accuracy == 1.0


def test_known_false_positive():
    """
    2. Known false positive.
    Verifies that when clean traffic is falsely flagged as an incident by a detector,
    it is correctly recorded as FP, increasing false_positives and lowering precision.
    """
    scenario = BenchmarkScenario(
        scenario_id="CLEAN_BUT_FLAGGED",
        name="Clean Traffic Falsely Flagged",
        description="Normal traffic marked clean by ground truth",
        ground_truth_incident=False,
        transactions=create_deterministic_window(
            total_transactions=50, failures=2
        ),
        baseline_success_rate=0.95,
    )

    # Mock detector that falsely fires incident_detected=True
    mock_detector = MagicMock(spec=IncidentIntelligence)
    mock_detector.assess.return_value = IncidentAssessment(
        route="UPI + Bank_A + Android",
        baseline_success_rate=0.95,
        current_success_rate=0.96,
        degradation_pp=-1.0,
        transactions_observed=50,
        failures_observed=2,
        severity="DEGRADED",
        incident_detected=True,  # False alarm!
        explanation="Simulated false alarm",
    )

    benchmark = IncidentDetectionBenchmark(detector=mock_detector)
    result = benchmark.run_benchmark([scenario])

    assert result.total_cases == 1
    assert result.true_positives == 0
    assert result.true_negatives == 0
    assert result.false_positives == 1
    assert result.false_negatives == 0
    assert result.cases[0].classification == "FP"
    assert result.precision == 0.0
    assert result.specificity == 0.0


def test_known_false_negative():
    """
    3. Known false negative.
    Verifies that when an actual degradation is not detected (e.g. WATCH advisory
    below DEGRADED automation threshold), it is recorded as FN and lowers recall.
    """
    # 25 txns with 7 pp drop -> detector gives WATCH, but incident_detected=False
    scenario = BenchmarkScenario(
        scenario_id="MILD_INCIDENT_MISSED",
        name="Mild Incident Missed By Automation",
        description="Real 7 pp degradation treated as advisory WATCH",
        ground_truth_incident=True,
        transactions=create_deterministic_window(
            total_transactions=25, failures=3
        ),
        baseline_success_rate=0.95,
    )

    benchmark = IncidentDetectionBenchmark()
    result = benchmark.run_benchmark([scenario])

    assert result.total_cases == 1
    assert result.true_positives == 0
    assert result.true_negatives == 0
    assert result.false_positives == 0
    assert result.false_negatives == 1
    assert result.cases[0].classification == "FN"
    assert result.cases[0].resulting_detector_severity == "WATCH"
    assert result.recall == 0.0


def test_precision_calculation():
    """
    4. Precision calculation.
    Verifies Precision = TP / (TP + FP).
    E.g. 3 TP and 1 FP -> 3/4 = 0.75.
    """
    # 3 true positives
    positives = [
        BenchmarkScenario(
            scenario_id=f"TP_{i}",
            name="Real Degradation",
            description="Confirmed incident",
            ground_truth_incident=True,
            transactions=create_deterministic_window(
                total_transactions=60, failures=25
            ),
            baseline_success_rate=0.95,
        )
        for i in range(3)
    ]

    # 1 clean scenario evaluated with a mock false alarm
    fp_scenario = BenchmarkScenario(
        scenario_id="FP_1",
        name="Clean Traffic",
        description="Clean traffic falsely flagged",
        ground_truth_incident=False,
        transactions=create_deterministic_window(
            total_transactions=50, failures=0
        ),
        baseline_success_rate=0.95,
    )

    # Hybrid detector: fires True for everything
    mock_detector = MagicMock(spec=IncidentIntelligence)
    mock_detector.assess.return_value = IncidentAssessment(
        route="UPI + Bank_A + Android",
        baseline_success_rate=0.95,
        current_success_rate=0.60,
        degradation_pp=35.0,
        transactions_observed=50,
        failures_observed=20,
        severity="CRITICAL",
        incident_detected=True,
        explanation="Always fires",
    )

    benchmark = IncidentDetectionBenchmark(detector=mock_detector)
    result = benchmark.run_benchmark(positives + [fp_scenario])

    assert result.true_positives == 3
    assert result.false_positives == 1
    assert result.precision == 0.75  # 3 / (3 + 1)


def test_recall_calculation():
    """
    5. Recall calculation.
    Verifies Recall = TP / (TP + FN).
    E.g. 3 TP and 1 FN -> 3/4 = 0.75.
    """
    # 3 detectable incidents (CRITICAL)
    tps = [
        BenchmarkScenario(
            scenario_id=f"TP_{i}",
            name="Severe Incident",
            description="80 txns, 28 failures",
            ground_truth_incident=True,
            transactions=create_deterministic_window(
                total_transactions=80, failures=28
            ),
            baseline_success_rate=0.95,
        )
        for i in range(3)
    ]

    # 1 mild incident that detector flags as WATCH (incident_detected=False) -> FN
    fn = BenchmarkScenario(
        scenario_id="FN_1",
        name="Mild Incident",
        description="25 txns, 3 failures -> WATCH",
        ground_truth_incident=True,
        transactions=create_deterministic_window(
            total_transactions=25, failures=3
        ),
        baseline_success_rate=0.95,
    )

    benchmark = IncidentDetectionBenchmark()
    result = benchmark.run_benchmark(tps + [fn])

    assert result.true_positives == 3
    assert result.false_negatives == 1
    assert result.recall == 0.75  # 3 / (3 + 1)


def test_f1_calculation():
    """
    6. F1 calculation.
    Verifies F1 = 2 * P * R / (P + R).
    With TP=3, FP=1, FN=1 -> P = 0.75, R = 0.75 -> F1 = 0.75.
    """
    # 3 TPs, 1 FP, 1 FN
    scenarios = []

    # 3 real incidents detected
    for i in range(3):
        scenarios.append(
            BenchmarkScenario(
                scenario_id=f"TP_{i}",
                name="Real Outage",
                description="80 txns, 28 failures",
                ground_truth_incident=True,
                transactions=create_deterministic_window(
                    total_transactions=80, failures=28
                ),
                baseline_success_rate=0.95,
            )
        )

    # 1 real incident missed (FN: WATCH status)
    scenarios.append(
        BenchmarkScenario(
            scenario_id="FN_WATCH",
            name="Missed Watch",
            description="25 txns, 3 failures",
            ground_truth_incident=True,
            transactions=create_deterministic_window(
                total_transactions=25, failures=3
            ),
            baseline_success_rate=0.95,
        )
    )

    # 1 clean traffic falsely detected (FP via mock wrapper)
    class CustomDetector:
        def __init__(self):
            self.real = IncidentIntelligence()

        def assess(self, df, baseline_success_rate=None):
            if len(df) == 100:  # The FP scenario
                return IncidentAssessment(
                    route="UPI + Bank_FP + Android",
                    baseline_success_rate=0.95,
                    current_success_rate=0.95,
                    degradation_pp=0.0,
                    transactions_observed=100,
                    failures_observed=5,
                    severity="DEGRADED",
                    incident_detected=True,  # False alarm
                    explanation="Injected FP",
                )
            return self.real.assess(df, baseline_success_rate)

    scenarios.append(
        BenchmarkScenario(
            scenario_id="FP_CLEAN",
            name="Clean High Volume",
            description="Clean traffic that gets false alarm",
            ground_truth_incident=False,
            transactions=create_deterministic_window(
                total_transactions=100, failures=5
            ),
            baseline_success_rate=0.95,
        )
    )

    benchmark = IncidentDetectionBenchmark(detector=CustomDetector())
    result = benchmark.run_benchmark(scenarios)

    assert result.true_positives == 3
    assert result.false_positives == 1
    assert result.false_negatives == 1
    assert result.precision == 0.75
    assert result.recall == 0.75
    assert result.f1_score == 0.75


def test_specificity_calculation():
    """
    7. Specificity calculation.
    Verifies Specificity = TN / (TN + FP).
    E.g. 3 TN and 1 FP -> 3/4 = 0.75.
    """
    scenarios = []

    # 3 clean negatives correctly identified
    for i in range(3):
        scenarios.append(
            BenchmarkScenario(
                scenario_id=f"TN_{i}",
                name="Clean Traffic",
                description="Clean traffic",
                ground_truth_incident=False,
                transactions=create_deterministic_window(
                    total_transactions=50, failures=1
                ),
                baseline_success_rate=0.95,
            )
        )

    # 1 clean traffic falsely flagged
    class FPDetector:
        def __init__(self):
            self.real = IncidentIntelligence()

        def assess(self, df, baseline_success_rate=None):
            if len(df) == 99:
                return IncidentAssessment(
                    route="UPI + Bank_X + Android",
                    baseline_success_rate=0.95,
                    current_success_rate=0.95,
                    degradation_pp=0.0,
                    transactions_observed=99,
                    failures_observed=0,
                    severity="CRITICAL",
                    incident_detected=True,
                    explanation="Forced FP",
                )
            return self.real.assess(df, baseline_success_rate)

    scenarios.append(
        BenchmarkScenario(
            scenario_id="FP_CASE",
            name="Clean Traffic Flagged",
            description="Clean 99 txns flagged",
            ground_truth_incident=False,
            transactions=create_deterministic_window(
                total_transactions=99, failures=0
            ),
            baseline_success_rate=0.95,
        )
    )

    benchmark = IncidentDetectionBenchmark(detector=FPDetector())
    result = benchmark.run_benchmark(scenarios)

    assert result.true_negatives == 3
    assert result.false_positives == 1
    assert result.specificity == 0.75  # 3 / (3 + 1)


def test_zero_denominator_protection():
    """
    8. Zero denominator protection.
    Verifies that when denominators are zero (e.g. empty suite, zero positives,
    or zero negatives), all metrics return 0.0 safely without ZeroDivisionError,
    NaN, or Inf.
    """
    benchmark = IncidentDetectionBenchmark()

    # Empty scenario suite
    result = benchmark.run_benchmark([])
    assert result.total_cases == 0
    assert result.precision == 0.0
    assert result.recall == 0.0
    assert result.f1_score == 0.0
    assert result.specificity == 0.0
    assert result.detection_accuracy == 0.0

    # Only clean negatives (no positives: TP=0, FP=0, FN=0)
    clean_scenario = BenchmarkScenario(
        scenario_id="CLEAN_ONLY",
        name="Clean",
        description="Clean",
        ground_truth_incident=False,
        transactions=create_deterministic_window(
            total_transactions=50, failures=0
        ),
        baseline_success_rate=0.95,
    )
    result_clean = benchmark.run_benchmark([clean_scenario])
    assert result_clean.true_positives == 0
    assert result_clean.false_positives == 0
    assert result_clean.precision == 0.0
    assert result_clean.recall == 0.0
    assert result_clean.f1_score == 0.0
    assert result_clean.specificity == 1.0
    assert result_clean.detection_accuracy == 1.0


def test_deterministic_repeated_benchmark():
    """
    9. Deterministic repeated benchmark.
    Running the benchmark multiple times on the same code/data produces
    strictly identical results without random drift.
    """
    benchmark = IncidentDetectionBenchmark()

    run1 = benchmark.run_benchmark()
    run2 = benchmark.run_benchmark()

    assert run1.total_cases == run2.total_cases
    assert run1.true_positives == run2.true_positives
    assert run1.true_negatives == run2.true_negatives
    assert run1.false_positives == run2.false_positives
    assert run1.false_negatives == run2.false_negatives
    assert run1.precision == run2.precision
    assert run1.recall == run2.recall
    assert run1.f1_score == run2.f1_score
    assert run1.specificity == run2.specificity
    assert run1.detection_accuracy == run2.detection_accuracy

    for c1, c2 in zip(run1.cases, run2.cases):
        assert c1.case_id == c2.case_id
        assert c1.classification == c2.classification
        assert c1.degradation_percentage_points == c2.degradation_percentage_points
        assert c1.resulting_detector_severity == c2.resulting_detector_severity


def test_boundary_scenario_behavior():
    """
    10. Boundary scenario behavior.
    Verifies that volume and degradation thresholds behave deterministically:
    - 25 txns with 11 pp drop: reaches degradation >= 10.0, BUT txns < 30 -> stays WATCH, detected=False.
    - 30 txns with 11 pp drop: reaches degradation >= 10.0 and txns >= 30 -> DEGRADED, detected=True.
    - 49 txns with 25 pp drop: reaches degradation >= 20.0, BUT txns < 50 -> DEGRADED (not CRITICAL).
    - 50 txns with 25 pp drop: reaches degradation >= 20.0 and txns >= 50 -> CRITICAL.
    """
    detector = IncidentIntelligence()

    # 1. 25 txns, 11 pp drop: txns < 30 -> stays WATCH
    df_watch_bound = create_deterministic_window(
        total_transactions=25, failures=4
    )  # SR = 21/25 = 84% -> drop = 11.0 pp
    res1 = detector.assess(df_watch_bound, baseline_success_rate=0.95)
    assert res1.severity == "WATCH"
    assert res1.incident_detected is False

    # 2. 30 txns, 11 pp drop: txns >= 30 -> DEGRADED
    df_deg_bound = create_deterministic_window(
        total_transactions=30, failures=5
    )  # SR = 25/30 = 83.33% -> drop = 11.67 pp
    res2 = detector.assess(df_deg_bound, baseline_success_rate=0.95)
    assert res2.severity == "DEGRADED"
    assert res2.incident_detected is True

    # 3. 49 txns, 25 pp drop: txns 49 < 50 -> DEGRADED (not CRITICAL)
    df_near_crit = create_deterministic_window(
        total_transactions=49, failures=15
    )  # SR = 34/49 = 69.39% -> drop = 25.61 pp
    res3 = detector.assess(df_near_crit, baseline_success_rate=0.95)
    assert res3.severity == "DEGRADED"
    assert res3.incident_detected is True

    # 4. 50 txns, 25 pp drop: txns 50 >= 50 and drop >= 20 -> CRITICAL
    df_crit_bound = create_deterministic_window(
        total_transactions=50, failures=15
    )  # SR = 35/50 = 70.00% -> drop = 25.00 pp
    res4 = detector.assess(df_crit_bound, baseline_success_rate=0.95)
    assert res4.severity == "CRITICAL"
    assert res4.incident_detected is True


def test_ground_truth_independent_of_detector_output():
    """
    11. Ground truth is strictly independent of detector output.
    PROVES that changing the detector's output does NOT change the ground truth label!
    """
    scenario_clean = BenchmarkScenario(
        scenario_id="CLEAN_TEST",
        name="Clean",
        description="Clean traffic",
        ground_truth_incident=False,
        transactions=create_deterministic_window(
            total_transactions=50, failures=1
        ),
        baseline_success_rate=0.95,
    )

    scenario_incident = BenchmarkScenario(
        scenario_id="INCIDENT_TEST",
        name="Incident",
        description="Real incident",
        ground_truth_incident=True,
        transactions=create_deterministic_window(
            total_transactions=60, failures=30
        ),
        baseline_success_rate=0.95,
    )

    # Detector A: Always returns incident_detected = False
    detector_always_false = MagicMock(spec=IncidentIntelligence)
    detector_always_false.assess.return_value = IncidentAssessment(
        route="UPI + Bank_A + Android",
        baseline_success_rate=0.95,
        current_success_rate=0.95,
        degradation_pp=0.0,
        transactions_observed=50,
        failures_observed=0,
        severity="NORMAL",
        incident_detected=False,
        explanation="Always False",
    )

    # Detector B: Always returns incident_detected = True
    detector_always_true = MagicMock(spec=IncidentIntelligence)
    detector_always_true.assess.return_value = IncidentAssessment(
        route="UPI + Bank_A + Android",
        baseline_success_rate=0.95,
        current_success_rate=0.50,
        degradation_pp=45.0,
        transactions_observed=50,
        failures_observed=25,
        severity="CRITICAL",
        incident_detected=True,
        explanation="Always True",
    )

    bench_false = IncidentDetectionBenchmark(detector=detector_always_false)
    bench_true = IncidentDetectionBenchmark(detector=detector_always_true)

    # Evaluate CLEAN scenario under both detectors:
    res_clean_under_false = bench_false.evaluate_scenario(scenario_clean)
    res_clean_under_true = bench_true.evaluate_scenario(scenario_clean)

    # CRITICAL ASSERTION: Ground truth label remains False in both!
    assert res_clean_under_false.ground_truth_incident is False
    assert res_clean_under_true.ground_truth_incident is False
    # But classification flips based on detector output:
    assert res_clean_under_false.classification == "TN"
    assert res_clean_under_true.classification == "FP"

    # Evaluate INCIDENT scenario under both detectors:
    res_inc_under_false = bench_false.evaluate_scenario(scenario_incident)
    res_inc_under_true = bench_true.evaluate_scenario(scenario_incident)

    # CRITICAL ASSERTION: Ground truth label remains True in both!
    assert res_inc_under_false.ground_truth_incident is True
    assert res_inc_under_true.ground_truth_incident is True
    # But classification flips based on detector output:
    assert res_inc_under_false.classification == "FN"
    assert res_inc_under_true.classification == "TP"


def test_no_nan_or_inf_metrics():
    """
    12. No NaN/Inf metrics.
    Verifies that running default benchmark produces completely valid,
    non-NaN and non-Inf float metrics.
    """
    benchmark = IncidentDetectionBenchmark()
    result = benchmark.run_benchmark()

    summary = benchmark_to_detection_summary(result)

    for metric_name, value in summary.items():
        if isinstance(value, float):
            assert not math.isnan(
                value
            ), f"Metric '{metric_name}' is NaN!"
            assert not math.isinf(
                value
            ), f"Metric '{metric_name}' is Inf!"

    # Also verify default benchmark performance is realistic and sensible
    assert result.total_cases == 10
    assert result.false_positives == 0  # 100% precision on clean traffic
    assert result.precision == 1.0
    assert result.recall > 0.60
    assert result.detection_accuracy >= 0.75


def test_accuracy_calculation():
    """
    13. Accuracy calculation.
    Verifies Accuracy = (TP + TN) / total_cases.
    E.g. TP=2, TN=3, FP=1, FN=1 -> 5/7 = 0.7143.
    """
    scenarios = []
    # 2 TPs
    for i in range(2):
        scenarios.append(
            BenchmarkScenario(
                scenario_id=f"TP_{i}",
                name="Severe",
                description="80 txns, 28 fails",
                ground_truth_incident=True,
                transactions=create_deterministic_window(80, 28),
                baseline_success_rate=0.95,
            )
        )
    # 3 TNs
    for i in range(3):
        scenarios.append(
            BenchmarkScenario(
                scenario_id=f"TN_{i}",
                name="Clean",
                description="50 txns, 1 fail",
                ground_truth_incident=False,
                transactions=create_deterministic_window(50, 1),
                baseline_success_rate=0.95,
            )
        )
    # 1 FN (WATCH status: incident_detected=False)
    scenarios.append(
        BenchmarkScenario(
            scenario_id="FN_WATCH",
            name="Watch",
            description="25 txns, 3 fails",
            ground_truth_incident=True,
            transactions=create_deterministic_window(25, 3),
            baseline_success_rate=0.95,
        )
    )
    # 1 FP (mock)
    class FPDetector:
        def __init__(self):
            self.real = IncidentIntelligence()

        def assess(self, df, baseline_success_rate=None):
            if len(df) == 77:
                return IncidentAssessment(
                    route="UPI + Bank_FP + Android",
                    baseline_success_rate=0.95,
                    current_success_rate=0.95,
                    degradation_pp=0.0,
                    transactions_observed=77,
                    failures_observed=0,
                    severity="CRITICAL",
                    incident_detected=True,
                    explanation="Injected FP",
                )
            return self.real.assess(df, baseline_success_rate)

    scenarios.append(
        BenchmarkScenario(
            scenario_id="FP_MOCK",
            name="Clean 77",
            description="Clean 77 txns",
            ground_truth_incident=False,
            transactions=create_deterministic_window(77, 0),
            baseline_success_rate=0.95,
        )
    )

    benchmark = IncidentDetectionBenchmark(detector=FPDetector())
    result = benchmark.run_benchmark(scenarios)

    assert result.total_cases == 7
    assert result.true_positives == 2
    assert result.true_negatives == 3
    assert result.false_positives == 1
    assert result.false_negatives == 1
    expected_acc = round((2 + 3) / 7, 4)
    assert result.detection_accuracy == expected_acc


def test_correct_scenario_count_and_composition():
    """
    14. Correct scenario count and composition.
    Verifies that the default benchmark contains exactly 10 deterministic scenarios:
    - 4 clean healthy routes (expected_incident=False)
    - 4 injected incident routes (expected_incident=True)
    - 2 boundary condition scenarios (expected_incident=True)
    """
    scenarios = IncidentDetectionBenchmark.build_default_scenarios()
    assert len(scenarios) == 10

    clean_count = sum(1 for s in scenarios if not s.ground_truth_incident)
    incident_count = sum(1 for s in scenarios if s.ground_truth_incident)

    assert clean_count == 4
    assert incident_count == 6  # 4 explicit incidents + 2 boundary test incidents

    scenario_ids = [s.scenario_id for s in scenarios]
    assert "CLEAN_HIGH_VOLUME" in scenario_ids
    assert "CLEAN_PERFECT_HEALTH" in scenario_ids
    assert "CLEAN_BACKGROUND_NOISE" in scenario_ids
    assert "CLEAN_LOW_VOLUME" in scenario_ids
    assert "MODERATE_DEGRADATION" in scenario_ids
    assert "SEVERE_DEGRADATION_CRITICAL" in scenario_ids
    assert "ACUTE_OUTAGE_CRITICAL" in scenario_ids
    assert "MILD_DEGRADATION_WATCH" in scenario_ids
    assert "BOUNDARY_BELOW_TXN_THRESHOLD" in scenario_ids
    assert "BOUNDARY_REACHING_DEGRADED" in scenario_ids


def test_severity_classification_distinct_from_incident_label():
    """
    15. Severity classification is not confused with ground-truth incident label.
    Verifies that advisory severity levels (WATCH vs DEGRADED vs CRITICAL)
    do not redefine whether a case is an incident in ground truth.
    """
    benchmark = IncidentDetectionBenchmark()
    result = benchmark.run_benchmark()

    # Find the MILD_DEGRADATION_WATCH case
    watch_cases = [c for c in result.cases if c.case_id == "MILD_DEGRADATION_WATCH"]
    assert len(watch_cases) == 1
    case = watch_cases[0]

    # Ground truth incident is True (real 7 pp degradation)
    assert case.ground_truth_incident is True
    # Detector classified it with advisory WATCH severity
    assert case.resulting_detector_severity == "WATCH"
    # But detector does not authorize automated recovery (incident_detected=False)
    assert case.detector_incident_detected is False
    # Therefore it is recorded as a False Negative from an automated recovery perspective
    assert case.classification == "FN"


def test_result_aliases_and_case_result_properties():
    """
    16. Convenience properties and aliases.
    Verifies f1, case_results, expected_incident, detected_incident, detected_severity, passed.
    """
    benchmark = IncidentDetectionBenchmark()
    result = benchmark.run_benchmark()

    assert result.f1 == result.f1_score
    assert len(result.case_results) == result.total_cases

    for case in result.case_results:
        assert case.expected_incident == case.ground_truth_incident
        assert case.detected_incident == case.detector_incident_detected
        assert case.detected_severity == case.resulting_detector_severity
        assert case.passed == (case.classification in ("TP", "TN"))
