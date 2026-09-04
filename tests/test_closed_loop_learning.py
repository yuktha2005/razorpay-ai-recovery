"""
End-to-End Closed-Loop Learning Integration Tests.

Validates the full recovery-learning lifecycle:
    Incident 1
        ↓
    Initial route ranking (Route A preferred)
        ↓
    Recovery executes on Route B (bounded execution simulation)
        ↓
    Outcome verification (actual transaction amounts verified)
        ↓
    Learning engine updates route evidence (Bayesian evidence update)
        ↓
    Learning state is persisted to disk
        ↓
    Incident 2
        ↓
    PersistentLearningHistory reloads verified historical recovery evidence
        ↓
    RouteScorer incorporates learned evidence
        ↓
    Route ranking changes
        ↓
    Decision selects Route B based on outcome-based route intelligence
"""

import pytest
from src.decision.incident_decision_engine import IncidentDecisionEngine
from src.intelligence.route_scoring import rank_routes
from src.models.domain import Decision, SafetyDecision
from src.recovery.bounded_executor import BoundedRecoveryExecutor
from src.recovery.recovery_orchestrator import RecoveryOrchestrator
from src.tracking.learning_history import PersistentLearningHistory
from src.tracking.recovery_outcome import RecoveryOutcomeVerifier


def _make_recovery_decision(action: str, estimated_value: float = 10000.0) -> Decision:
    return Decision(
        payment_id="INCIDENT:UPI + Bank_Degraded + Android",
        recommended_action=action,
        confidence=0.85,
        expected_loss_before=15000.0,
        expected_loss_after=3000.0,
        estimated_value=estimated_value,
        explanation="Bounded recovery execution decision",
    )


def test_closed_loop_learning_end_to_end(tmp_path, monkeypatch):
    """
    Full end-to-end lifecycle test proving that verified historical recovery
    evidence from bounded recovery execution is persisted, reloaded, and
    changes the incident decision for subsequent incidents.
    """
    # ------------------------------------------------------------------
    # Step 0: Isolate persistent learning storage in temporary directory
    # ------------------------------------------------------------------
    learning_file = tmp_path / "recovery_learning.csv"
    monkeypatch.setattr("src.tracking.learning_store.LEARNING_FILE", learning_file)
    monkeypatch.setattr("src.tracking.learning_store.LOG_DIR", tmp_path)

    # ------------------------------------------------------------------
    # Step 1: Define baseline candidate routes
    #
    # Route A: 100 observed transactions, 90 successes (90.0% observed)
    # Route B: 100 observed transactions, 80 successes (80.0% observed)
    # ------------------------------------------------------------------
    route_a_name = "UPI + Bank_A + Android"
    route_b_name = "UPI + Bank_B + Android"

    baseline_candidates = [
        {"route": route_a_name, "transactions": 100, "successes": 90},
        {"route": route_b_name, "transactions": 100, "successes": 80},
    ]

    # ------------------------------------------------------------------
    # Step 2: Incident 1 - Initial Route Ranking and Decision
    #
    # With no prior historical recovery evidence, Route A is preferred
    # because of higher observed success rate and higher Bayesian score.
    # ------------------------------------------------------------------
    fresh_history_initial = PersistentLearningHistory()
    engine_1 = IncidentDecisionEngine(learning_history=fresh_history_initial)

    incident_params = dict(
        incident_route="UPI + Bank_Degraded + Android",
        transactions_affected=200,
        failures_observed=70,
        baseline_success_rate=0.95,
        current_success_rate=0.65,
        severity="CRITICAL",
        average_transaction_value=1500.0,
        route_candidates=baseline_candidates,
    )

    result_1 = engine_1.evaluate(**incident_params)

    # Incident 1 assertions: Route A is preferred
    assert result_1.ranked_routes[0].route == route_a_name
    assert result_1.ranked_routes[1].route == route_b_name

    pre_learning_score_a = result_1.ranked_routes[0].score
    pre_learning_score_b = result_1.ranked_routes[1].score
    assert pre_learning_score_a > pre_learning_score_b

    assert result_1.decision.recommended_action == f"ROUTE_SWITCH:{route_a_name}"
    assert result_1.ranked_routes[0].learned_attempts == 0
    assert result_1.ranked_routes[1].learned_attempts == 0

    # ------------------------------------------------------------------
    # Step 3: Bounded Recovery Execution on Route B
    #
    # Execute a bounded recovery batch using the real RecoveryOrchestrator.
    # We supply 150 deterministic transactions with distinct amounts to
    # demonstrate actual transaction amount tracking and strong recovery.
    # ------------------------------------------------------------------
    transaction_amounts = [500.0 + (i * 25.0) for i in range(150)]
    expected_total_amount = sum(transaction_amounts)

    orchestrator = RecoveryOrchestrator(
        executor=BoundedRecoveryExecutor(
            max_transactions=150,
            canary_percentage=1.0,
            recovery_budget=500000.0,
        )
    )

    recovery_action = f"ROUTE_SWITCH:{route_b_name}"
    recovery_decision = _make_recovery_decision(
        action=recovery_action,
        estimated_value=expected_total_amount,
    )
    recovery_safety = SafetyDecision(
        payment_id="INCIDENT:UPI + Bank_Degraded + Android",
        action=recovery_action,
        allowed=True,
        reason="Recovery action passed safety controls",
        requires_human_review=False,
    )

    orchestration_result = orchestrator.execute(
        decision=recovery_decision,
        safety_decision=recovery_safety,
        transaction_amounts=transaction_amounts,
        simulated_success_rate=1.0,
    )

    # ------------------------------------------------------------------
    # Step 4: Verify recovery outcome and transaction amount aggregation
    # ------------------------------------------------------------------
    exec_res = orchestration_result.execution_result
    outcome = orchestration_result.recovery_outcome

    assert exec_res.attempted_transactions == 150
    assert exec_res.successful_recoveries == 150
    assert exec_res.failed_recoveries == 0
    assert outcome.outcome_status == "RECOVERED"

    # Verify actual recovered amounts match sum of successful transaction amounts
    assert len(exec_res.successful_transaction_amounts) == 150
    assert outcome.recovered_amount == sum(exec_res.successful_transaction_amounts)
    assert outcome.recovered_amount == expected_total_amount

    # Verify execution cost calculation (150 txns * ₹25 = ₹3750)
    assert exec_res.estimated_cost == 150 * 25.0
    assert outcome.execution_cost == exec_res.estimated_cost
    assert outcome.net_recovered_value == expected_total_amount - (150 * 25.0)

    # ------------------------------------------------------------------
    # Step 5: Verify persistence to disk
    # ------------------------------------------------------------------
    assert learning_file.exists(), "Persistent learning store file must exist after execution."

    # ------------------------------------------------------------------
    # Step 6: Incident 2 - Reload learning history & re-evaluate
    #
    # Create a fresh PersistentLearningHistory instance pointed at the store.
    # ------------------------------------------------------------------
    fresh_history = PersistentLearningHistory()
    persisted_stats = fresh_history.load()

    assert len(persisted_stats) == 1
    stats_b = persisted_stats[0]
    assert stats_b.route == route_b_name
    assert stats_b.attempts == 150
    assert stats_b.recoveries == 150

    # Evaluate Incident 2 with the SAME baseline route telemetry
    engine_2 = IncidentDecisionEngine(learning_history=fresh_history)
    result_2 = engine_2.evaluate(**incident_params)

    # ------------------------------------------------------------------
    # Step 7: Verify all 9 Closed-Loop Learning Requirements
    # ------------------------------------------------------------------
    route_b_score = result_2.ranked_routes[0]
    route_a_score = result_2.ranked_routes[1]

    # 1. Route A's baseline score is unchanged by Route B's learning
    assert route_a_score.route == route_a_name
    assert route_a_score.score == pre_learning_score_a
    assert route_a_score.transactions == 100
    assert route_a_score.successes == 90
    assert route_a_score.learned_attempts == 0
    assert route_a_score.learned_recoveries == 0

    # 2. Route B has learned_attempts > 0
    assert route_b_score.learned_attempts == 150
    assert route_b_score.learned_attempts > 0

    # 3. Route B has learned_recoveries > 0
    assert route_b_score.learned_recoveries == 150
    assert route_b_score.learned_recoveries > 0

    # 4. Route B's effective transactions = baseline + learned attempts
    assert route_b_score.transactions == 100 + 150
    assert route_b_score.transactions == 250

    # 5. Route B's effective successes = baseline + learned recoveries
    assert route_b_score.successes == 80 + 150
    assert route_b_score.successes == 230

    # 6. Route B's score increases compared with its pre-learning score
    assert route_b_score.score > pre_learning_score_b

    # 7. Route B overtakes Route A when the learned evidence is strong enough
    assert route_b_score.score > route_a_score.score
    assert result_2.ranked_routes[0].route == route_b_name

    # 8. Incident 2 can therefore select Route B
    assert result_2.decision.recommended_action == f"ROUTE_SWITCH:{route_b_name}"
    assert result_2.decision.confidence > result_1.decision.confidence

    # 9. The result is deterministic
    result_2_repeat = engine_2.evaluate(**incident_params)
    assert result_2_repeat.decision.recommended_action == result_2.decision.recommended_action
    assert result_2_repeat.decision.confidence == result_2.decision.confidence
    assert result_2_repeat.ranked_routes[0].score == result_2.ranked_routes[0].score
    assert result_2_repeat.ranked_routes[1].score == result_2.ranked_routes[1].score


def test_outcome_verifier_uses_actual_successful_transaction_amounts():
    """
    Verifies that RecoveryOutcomeVerifier strictly uses the sum of individual
    successful transaction amounts when supplied by the executor.
    """
    verifier = RecoveryOutcomeVerifier()

    transaction_amounts = [1250.50, 430.00, 999.00, 2500.00]
    successful_amounts = [1250.50, 999.00]  # 2 of 4 succeeded with specific amounts

    outcome = verifier.verify(
        transaction_amounts=transaction_amounts,
        successful_recoveries=2,
        failed_recoveries=2,
        execution_cost=50.0,
        successful_transaction_amounts=successful_amounts,
    )

    expected_recovered = 1250.50 + 999.00
    assert outcome.recovered_amount == sum(successful_amounts)
    assert outcome.recovered_amount == expected_recovered
    assert outcome.net_recovered_value == expected_recovered - 50.0
    assert outcome.outcome_status == "RECOVERED"


def test_closed_loop_bayesian_conservatism_with_modest_evidence(tmp_path, monkeypatch):
    """
    Demonstrates Bayesian evidence updates: a small recovery sample improves
    a route's score, but Bayesian prior shrinkage prevents a small sample
    from immediately overturning a high-confidence, mature route.
    """
    learning_file = tmp_path / "recovery_learning.csv"
    monkeypatch.setattr("src.tracking.learning_store.LEARNING_FILE", learning_file)
    monkeypatch.setattr("src.tracking.learning_store.LOG_DIR", tmp_path)

    route_a = "UPI + Bank_A + Android"
    route_b = "UPI + Bank_B + Android"

    # Route A has mature track record: 100 txns, 90 successes (90%)
    # Route B has lower track record: 100 txns, 80 successes (80%)
    candidates = [
        {"route": route_a, "transactions": 100, "successes": 90},
        {"route": route_b, "transactions": 100, "successes": 80},
    ]

    engine_base = IncidentDecisionEngine()
    res_base = engine_base.evaluate(
        incident_route="UPI + Degraded + Android",
        transactions_affected=100,
        failures_observed=30,
        baseline_success_rate=0.95,
        current_success_rate=0.70,
        severity="CRITICAL",
        average_transaction_value=1000.0,
        route_candidates=candidates,
    )

    base_b_score = next(r.score for r in res_base.ranked_routes if r.route == route_b)

    # Execute a small 5-attempt recovery for Route B
    orchestrator = RecoveryOrchestrator(
        executor=BoundedRecoveryExecutor(
            max_transactions=5,
            canary_percentage=1.0,
            recovery_budget=5000.0,
        )
    )

    action = f"ROUTE_SWITCH:{route_b}"
    orchestrator.execute(
        decision=_make_recovery_decision(action, estimated_value=5000.0),
        safety_decision=SafetyDecision(
            payment_id="INCIDENT:DEGRADED",
            action=action,
            allowed=True,
            reason="Safety allowed",
            requires_human_review=False,
        ),
        transaction_amounts=[1000.0] * 5,
        simulated_success_rate=1.0,
    )

    fresh_history = PersistentLearningHistory()
    engine_learned = IncidentDecisionEngine(learning_history=fresh_history)
    res_learned = engine_learned.evaluate(
        incident_route="UPI + Degraded + Android",
        transactions_affected=100,
        failures_observed=30,
        baseline_success_rate=0.95,
        current_success_rate=0.70,
        severity="CRITICAL",
        average_transaction_value=1000.0,
        route_candidates=candidates,
    )

    learned_b = next(r for r in res_learned.ranked_routes if r.route == route_b)
    learned_a = next(r for r in res_learned.ranked_routes if r.route == route_a)

    # Route B's score increases due to 5 verified recoveries
    assert learned_b.learned_attempts == 5
    assert learned_b.learned_recoveries == 5
    assert learned_b.transactions == 105
    assert learned_b.successes == 85
    assert learned_b.score > base_b_score

    # But 5 recoveries on a route with 80% baseline (85/105 = 80.95%)
    # does not prematurely overtake Route A (90% over 100 transactions),
    # verifying conservative Bayesian shrinkage!
    assert learned_a.score > learned_b.score
    assert res_learned.decision.recommended_action == f"ROUTE_SWITCH:{route_a}"


def test_app_live_flow_learning_history_wiring(tmp_path, monkeypatch):
    """
    Verifies that the app's live flow wiring:
    - safely handles fresh installation / empty learning history
    - uses the exact same PersistentLearningHistory state in both the
      decision engine and Section 6 learning summary
    - updates route decisions once verified recovery evidence is persisted
    """
    learning_file = tmp_path / "recovery_learning.csv"
    monkeypatch.setattr("src.tracking.learning_store.LEARNING_FILE", learning_file)
    monkeypatch.setattr("src.tracking.learning_store.LOG_DIR", tmp_path)

    # 1. Fresh installation / empty store
    learning_history = PersistentLearningHistory()
    loaded_routes = learning_history.load()
    evidence_route_count = len(loaded_routes) if loaded_routes else 0
    assert evidence_route_count == 0
    assert loaded_routes == []

    # 2. Decision engine instantiated with learning_history as in app.py
    decision_engine = IncidentDecisionEngine(learning_history=learning_history)

    candidates = [
        {"route": "UPI + Bank_A + Android", "transactions": 50, "successes": 45},
        {"route": "UPI + Bank_B + Android", "transactions": 50, "successes": 40},
    ]

    res_initial = decision_engine.evaluate(
        incident_route="UPI + Degraded + Android",
        transactions_affected=100,
        failures_observed=25,
        baseline_success_rate=0.95,
        current_success_rate=0.75,
        severity="CRITICAL",
        average_transaction_value=1200.0,
        route_candidates=candidates,
    )

    assert res_initial.decision.recommended_action == "ROUTE_SWITCH:UPI + Bank_A + Android"
    assert res_initial.ranked_routes[0].learned_attempts == 0
    assert res_initial.ranked_routes[1].learned_attempts == 0

    # 3. Simulate recovery executed on Bank_B
    orchestrator = RecoveryOrchestrator(
        executor=BoundedRecoveryExecutor(
            max_transactions=100,
            canary_percentage=1.0,
            recovery_budget=100000.0,
        )
    )
    orchestrator.execute(
        decision=_make_recovery_decision("ROUTE_SWITCH:UPI + Bank_B + Android", estimated_value=50000.0),
        safety_decision=SafetyDecision(
            payment_id="INCIDENT:DEGRADED",
            action="ROUTE_SWITCH:UPI + Bank_B + Android",
            allowed=True,
            reason="Approved",
            requires_human_review=False,
        ),
        transaction_amounts=[500.0] * 100,
        simulated_success_rate=1.0,
    )

    # 4. Same PersistentLearningHistory loader as Section 6 in app.py
    history_loader = learning_history
    updated_routes = history_loader.load()
    evidence_route_count = len(updated_routes) if updated_routes else 0
    assert evidence_route_count == 1
    assert updated_routes[0].route == "UPI + Bank_B + Android"
    assert updated_routes[0].attempts == 100
    assert updated_routes[0].recoveries == 100

    # 5. Subsequent evaluation in live flow automatically incorporates learned evidence
    res_subsequent = decision_engine.evaluate(
        incident_route="UPI + Degraded + Android",
        transactions_affected=100,
        failures_observed=25,
        baseline_success_rate=0.95,
        current_success_rate=0.75,
        severity="CRITICAL",
        average_transaction_value=1200.0,
        route_candidates=candidates,
    )

    assert res_subsequent.ranked_routes[0].route == "UPI + Bank_B + Android"
    assert res_subsequent.decision.recommended_action == "ROUTE_SWITCH:UPI + Bank_B + Android"
    assert res_subsequent.ranked_routes[0].learned_attempts == 100
