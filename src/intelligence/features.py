from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent.parent

DEFAULT_DATA_PATH = BASE_DIR / "data" / "transactions.csv"


class PaymentFeatureEngineer:
    """
    Builds leakage-safe features from historical transaction data.

    All customer and merchant behavioral features are calculated
    using transactions that occurred before the current transaction.
    """

    TARGET_COLUMN = "status"

    EXCLUDED_COLUMNS = {
        "transaction_id",
        "incident_ground_truth",
        "error_code",
        "status",
    }

    def transform(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:

        data = df.copy()

        if data.empty:
            raise ValueError("Transaction dataset is empty.")

        required_columns = {
            "customer_id",
            "merchant_id",
            "amount",
            "timestamp",
            "status",
        }

        missing = required_columns - set(data.columns)

        if missing:
            raise ValueError(
                f"Missing required columns: {sorted(missing)}"
            )

        # --------------------------------------------------
        # Timestamp
        # --------------------------------------------------

        data["timestamp"] = pd.to_datetime(
    data["timestamp"],
    format="mixed",
    errors="coerce",
)

        if data["timestamp"].isna().any():
            raise ValueError(
                "Dataset contains invalid timestamps."
            )

        # Preserve deterministic ordering for identical timestamps.
        data["_original_order"] = np.arange(len(data))

        data = data.sort_values(
            ["timestamp", "_original_order"]
        ).reset_index(drop=True)

        # --------------------------------------------------
        # Target
        # --------------------------------------------------

        data["failure_target"] = (
            data["status"].eq("FAILED").astype(int)
        )

        # --------------------------------------------------
        # Global historical defaults
        # --------------------------------------------------

        global_failure_rate = data["failure_target"].mean()
        global_average_amount = data["amount"].mean()

        # --------------------------------------------------
        # Temporal features
        # --------------------------------------------------

        data["hour"] = data["timestamp"].dt.hour

        data["day_of_week"] = (
            data["timestamp"].dt.dayofweek
        )

        data["is_weekend"] = (
            data["day_of_week"] >= 5
        ).astype(int)

        # --------------------------------------------------
        # Customer historical features
        # --------------------------------------------------

        customer = data.groupby(
            "customer_id",
            sort=False,
        )

        data["customer_previous_count"] = (
            customer.cumcount()
        )

        data["customer_previous_failures"] = (
            customer["failure_target"]
            .cumsum()
            .sub(data["failure_target"])
        )

        data["customer_previous_failure_rate"] = (
            data["customer_previous_failures"]
            / data["customer_previous_count"].replace(
                0,
                np.nan,
            )
        )

        data["customer_previous_avg_amount"] = (
            customer["amount"]
            .expanding()
            .mean()
            .reset_index(
                level=0,
                drop=True,
            )
            .groupby(
                data["customer_id"]
            )
            .shift(1)
            .reset_index(
                level=0,
                drop=True,
            )
        )

        # --------------------------------------------------
        # Merchant historical features
        # --------------------------------------------------

        merchant = data.groupby(
            "merchant_id",
            sort=False,
        )

        data["merchant_previous_count"] = (
            merchant.cumcount()
        )

        data["merchant_previous_failures"] = (
            merchant["failure_target"]
            .cumsum()
            .sub(data["failure_target"])
        )

        data["merchant_previous_failure_rate"] = (
            data["merchant_previous_failures"]
            / data["merchant_previous_count"].replace(
                0,
                np.nan,
            )
        )

        data["merchant_previous_avg_amount"] = (
            merchant["amount"]
            .expanding()
            .mean()
            .reset_index(
                level=0,
                drop=True,
            )
            .groupby(
                data["merchant_id"]
            )
            .shift(1)
            .reset_index(
                level=0,
                drop=True,
            )
        )

        # --------------------------------------------------
        # Safe defaults for first observations
        # --------------------------------------------------

        data["customer_previous_failure_rate"] = (
            data["customer_previous_failure_rate"]
            .fillna(global_failure_rate)
        )

        data["merchant_previous_failure_rate"] = (
            data["merchant_previous_failure_rate"]
            .fillna(global_failure_rate)
        )

        data["customer_previous_avg_amount"] = (
            data["customer_previous_avg_amount"]
            .fillna(global_average_amount)
        )

        data["merchant_previous_avg_amount"] = (
            data["merchant_previous_avg_amount"]
            .fillna(global_average_amount)
        )

        # --------------------------------------------------
        # Amount-relative features
        # --------------------------------------------------

        data["amount_vs_customer_average"] = (
            data["amount"]
            / data["customer_previous_avg_amount"]
            .replace(0, np.nan)
        ).replace(
            [np.inf, -np.inf],
            np.nan,
        ).fillna(1.0)

        data["amount_vs_merchant_average"] = (
            data["amount"]
            / data["merchant_previous_avg_amount"]
            .replace(0, np.nan)
        ).replace(
            [np.inf, -np.inf],
            np.nan,
        ).fillna(1.0)

        # --------------------------------------------------
        # Cleanup
        # --------------------------------------------------

        data = data.drop(
            columns=["_original_order"],
        )

        return data