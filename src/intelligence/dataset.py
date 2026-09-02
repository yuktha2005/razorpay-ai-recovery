from pathlib import Path
from typing import Tuple

import pandas as pd

from src.intelligence.features import PaymentFeatureEngineer


BASE_DIR = Path(__file__).resolve().parent.parent.parent

DEFAULT_DATA_PATH = BASE_DIR / "data" / "transactions.csv"


class PaymentDatasetBuilder:
    """
    Builds a chronological train/test dataset for payment
    failure prediction.

    The split is performed by time so that future transactions
    are never used to evaluate predictions about the past.
    """

    TARGET = "failure_target"

    # These columns are identifiers, raw text fields, targets,
    # or fields that could leak information available only after
    # the payment outcome.
    EXCLUDED_FEATURES = {
    "transaction_id",
    "merchant_id",
    "customer_id",
    "timestamp",
    "status",
    "failure_target",
    "incident_ground_truth",
    "error_code",
    "retry_count",
}

    CATEGORICAL_FEATURES = {
        "payment_method",
        "bank",
        "device_type",
        "location",
    }

    def __init__(
        self,
        test_fraction: float = 0.20,
    ):
        if not 0 < test_fraction < 1:
            raise ValueError(
                "test_fraction must be between 0 and 1."
            )

        self.test_fraction = test_fraction
        self.feature_engineer = PaymentFeatureEngineer()

    def load(
        self,
        path: Path = DEFAULT_DATA_PATH,
    ) -> pd.DataFrame:

        if not path.exists():
            raise FileNotFoundError(
                f"Dataset not found: {path}"
            )

        df = pd.read_csv(path)

        if df.empty:
            raise ValueError("Dataset is empty.")

        return df

    def build(
        self,
        df: pd.DataFrame,
    ) -> Tuple[
        pd.DataFrame,
        pd.Series,
        pd.DataFrame,
        pd.Series,
    ]:
        """
        Return:

        X_train
        y_train
        X_test
        y_test
        """

        # ----------------------------------------------
        # Feature engineering
        # ----------------------------------------------

        engineered = self.feature_engineer.transform(df)

        engineered = engineered.sort_values(
            "timestamp"
        ).reset_index(drop=True)

        # ----------------------------------------------
        # Chronological split
        # ----------------------------------------------

        split_index = int(
            len(engineered)
            * (1.0 - self.test_fraction)
        )

        if split_index <= 0 or split_index >= len(engineered):
            raise ValueError(
                "Invalid train/test split."
            )

        train = engineered.iloc[
            :split_index
        ].copy()

        test = engineered.iloc[
            split_index:
        ].copy()

        # ----------------------------------------------
        # Select model features
        # ----------------------------------------------

        feature_columns = [
            column
            for column in engineered.columns
            if column not in self.EXCLUDED_FEATURES
        ]

        X_train = train[feature_columns].copy()
        X_test = test[feature_columns].copy()

        y_train = train[self.TARGET].copy()
        y_test = test[self.TARGET].copy()

        # ----------------------------------------------
        # One-hot encode categorical variables
        #
        # Fit categories on training data only.
        # ----------------------------------------------

        X_train = pd.get_dummies(
            X_train,
            columns=[
                column
                for column in self.CATEGORICAL_FEATURES
                if column in X_train.columns
            ],
            dtype=float,
        )

        X_test = pd.get_dummies(
            X_test,
            columns=[
                column
                for column in self.CATEGORICAL_FEATURES
                if column in X_test.columns
            ],
            dtype=float,
        )

        # Align test columns to training columns.
        X_test = X_test.reindex(
            columns=X_train.columns,
            fill_value=0.0,
        )

        # ----------------------------------------------
        # Final numeric validation
        # ----------------------------------------------

        if X_train.isna().any().any():
            raise ValueError(
                "Training features contain NaN values."
            )

        if X_test.isna().any().any():
            raise ValueError(
                "Test features contain NaN values."
            )

        return (
            X_train,
            y_train,
            X_test,
            y_test,
        )

    def build_from_csv(
        self,
        path: Path = DEFAULT_DATA_PATH,
    ):
        df = self.load(path)

        return self.build(df)