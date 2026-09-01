from dataclasses import dataclass


@dataclass
class OutcomeEvaluation:
    payment_id: str
    predicted_action: str
    actual_action: str
    expected_loss: float
    actual_loss: float
    recovered_amount: float
    loss_prevented: float
    prediction_status: str
    financial_error: float
    explanation: str


class OutcomeEvaluator:
    """
    Compares an AI decision with the actual intervention outcome.

    This component does not modify payments or execute actions.
    It produces feedback that can later be used for model
    calibration and learning.
    """

    def evaluate(
        self,
        payment_id: str,
        predicted_action: str,
        expected_loss: float,
        actual_action: str,
        actual_loss: float,
        recovered_amount: float,
        loss_prevented: float,
    ) -> OutcomeEvaluation:

        expected_loss = max(
            0.0,
            float(expected_loss),
        )

        actual_loss = max(
            0.0,
            float(actual_loss),
        )

        recovered_amount = max(
            0.0,
            float(recovered_amount),
        )

        loss_prevented = max(
            0.0,
            float(loss_prevented),
        )

        # ------------------------------------------
        # Financial prediction error
        # ------------------------------------------

        financial_error = round(
            actual_loss - expected_loss,
            2,
        )

        # ------------------------------------------
        # Determine outcome
        # ------------------------------------------

        if actual_action != predicted_action:
            prediction_status = "ACTION_CHANGED"

            explanation = (
                "The executed action differed from the "
                "AI's original recommendation."
            )

        elif actual_loss <= expected_loss:
            prediction_status = "SUCCESS"

            explanation = (
                "Actual financial loss was at or below "
                "the predicted expected loss."
            )

        else:
            prediction_status = "UNDERPREDICTED_LOSS"

            explanation = (
                "Actual financial loss exceeded the "
                "predicted expected loss."
            )

        return OutcomeEvaluation(
            payment_id=payment_id,
            predicted_action=predicted_action,
            actual_action=actual_action,
            expected_loss=expected_loss,
            actual_loss=actual_loss,
            recovered_amount=recovered_amount,
            loss_prevented=loss_prevented,
            prediction_status=prediction_status,
            financial_error=financial_error,
            explanation=explanation,
        )