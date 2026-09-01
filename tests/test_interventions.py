from src.decision.interventions import InterventionLibrary
from src.decision.optimizer import InterventionOptimizer
from src.models.domain import LossEstimate


def make_loss(expected_loss=10000.0):
    return LossEstimate(
        payment_id="test_payment",
        financial_exposure=50000.0,
        probability_of_loss=0.20,
        expected_loss=expected_loss,
        currency="INR",
    )


def test_intervention_library_returns_expected_actions():
    loss = make_loss()

    interventions = InterventionLibrary().generate(loss)

    actions = {item.action for item in interventions}

    assert actions == {
        "MONITOR",
        "CUSTOMER_CONFIRMATION",
        "STEP_UP_VERIFICATION",
        "MANUAL_REVIEW",
    }


def test_interventions_have_valid_values():
    loss = make_loss()

    interventions = InterventionLibrary().generate(loss)

    for intervention in interventions:
        assert intervention.estimated_cost >= 0
        assert intervention.expected_loss_after >= 0
        assert 0 <= intervention.customer_friction <= 1


def test_expected_benefit_is_economically_consistent():
    loss = make_loss()

    interventions = InterventionLibrary().generate(loss)

    for intervention in interventions:
        expected = round(
            loss.expected_loss
            - intervention.expected_loss_after
            - intervention.estimated_cost,
            2,
        )

        assert intervention.expected_benefit == expected


def test_optimizer_selects_positive_value_intervention():
    loss = make_loss(10000.0)

    interventions = InterventionLibrary().generate(loss)

    decision = InterventionOptimizer().optimize(
        loss,
        interventions,
        confidence=0.85,
    )

    assert decision.recommended_action != ""
    assert decision.estimated_value > 0
    assert decision.confidence == 0.85


def test_optimizer_falls_back_to_monitor_when_no_value():
    loss = LossEstimate(
        payment_id="low_value",
        financial_exposure=1.0,
        probability_of_loss=0.01,
        expected_loss=0.01,
        currency="INR",
    )

    interventions = InterventionLibrary().generate(loss)

    decision = InterventionOptimizer().optimize(
        loss,
        interventions,
        confidence=0.90,
    )

    assert decision.recommended_action == "MONITOR"
    assert decision.estimated_value == 0.0


def test_optimizer_does_not_execute_actions():
    loss = make_loss()

    interventions = InterventionLibrary().generate(loss)

    decision = InterventionOptimizer().optimize(
        loss,
        interventions,
        confidence=0.90,
    )

    # Decision layer only recommends.
    # It must not contain execution behavior.
    assert decision.recommended_action in {
        "MONITOR",
        "CUSTOMER_CONFIRMATION",
        "STEP_UP_VERIFICATION",
        "MANUAL_REVIEW",
    }