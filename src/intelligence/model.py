from dataclasses import dataclass
from typing import List

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler


@dataclass
class ModelMetrics:
    roc_auc: float
    pr_auc: float
    precision: float
    recall: float
    f1: float


class PaymentFailureModel:
    """
    Baseline supervised-learning model for payment failure
    probability prediction.

    The model predicts:

        P(payment failure)

    It does not execute payments or make recovery decisions.
    """

    def __init__(
        self,
        random_state: int = 42,
    ):
        self.scaler = StandardScaler()

        self.model = LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=random_state,
        )

        self.feature_names: List[str] = []

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
    ):
        self.feature_names = list(
            X_train.columns
        )

        X_scaled = self.scaler.fit_transform(
            X_train
        )

        self.model.fit(
            X_scaled,
            y_train,
        )

        return self

    def predict_probability(
        self,
        X: pd.DataFrame,
    ):
        self._validate_features(X)

        X_scaled = self.scaler.transform(X)

        return self.model.predict_proba(
            X_scaled
        )[:, 1]

    def predict(
        self,
        X: pd.DataFrame,
        threshold: float = 0.50,
    ):
        probabilities = self.predict_probability(X)

        return (
            probabilities >= threshold
        ).astype(int)

    def evaluate(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        threshold: float = 0.50,
    ) -> ModelMetrics:

        probabilities = self.predict_probability(
            X_test
        )

        predictions = (
            probabilities >= threshold
        ).astype(int)

        return ModelMetrics(
            roc_auc=roc_auc_score(
                y_test,
                probabilities,
            ),
            pr_auc=average_precision_score(
                y_test,
                probabilities,
            ),
            precision=precision_score(
                y_test,
                predictions,
                zero_division=0,
            ),
            recall=recall_score(
                y_test,
                predictions,
                zero_division=0,
            ),
            f1=f1_score(
                y_test,
                predictions,
                zero_division=0,
            ),
        )

    def _validate_features(
        self,
        X: pd.DataFrame,
    ):
        incoming_features = list(
            X.columns
        )

        if incoming_features != self.feature_names:
            raise ValueError(
                "Feature columns do not match "
                "the columns used during training."
            )