from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class RouteBaseline:
    route: str
    transaction_count: int
    success_count: int
    failure_count: int
    success_rate: float


class RouteBaselineBuilder:
    """
    Builds historical performance baselines for payment routes.

    A route is defined by:

        payment_method + bank + device_type

    Example:

        UPI + Bank_X + Android

    The baseline can optionally be calculated using only
    transactions that occurred before a specified timestamp.

    This is important for avoiding data leakage:
    the incident being detected must not be included
    in the baseline used to detect it.
    """

    ROUTE_COLUMNS = [
        "payment_method",
        "bank",
        "device_type",
    ]

    REQUIRED_COLUMNS = {
        "payment_method",
        "bank",
        "device_type",
        "status",
        "timestamp",
    }

    def build(
        self,
        df: pd.DataFrame,
        before: Optional[pd.Timestamp] = None,
    ) -> pd.DataFrame:
        """
        Build historical baselines for all payment routes.

        Parameters
        ----------
        df:
            Transaction dataframe.

        before:
            Optional timestamp cutoff.

            If provided, only transactions occurring BEFORE
            this timestamp are used to calculate the baseline.

        Returns
        -------
        pd.DataFrame
            One row per payment route containing:

            route
            payment_method
            bank
            device_type
            transaction_count
            success_count
            failure_count
            success_rate
        """

        # --------------------------------------------------
        # Validate required columns
        # --------------------------------------------------

        missing = self.REQUIRED_COLUMNS - set(df.columns)

        if missing:
            raise ValueError(
                f"Missing required columns: {sorted(missing)}"
            )

        # --------------------------------------------------
        # Copy input so the original dataframe is not
        # modified.
        # --------------------------------------------------

        data = df.copy()

        # --------------------------------------------------
        # Parse timestamps
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

        # --------------------------------------------------
        # Apply historical cutoff
        #
        # Only information available BEFORE the cutoff
        # is allowed to influence the baseline.
        # --------------------------------------------------

        if before is not None:

            before = pd.Timestamp(before)

            data = data[
                data["timestamp"] < before
            ].copy()

        # --------------------------------------------------
        # Make sure historical data exists
        # --------------------------------------------------

        if data.empty:
            raise ValueError(
                "No historical transactions available "
                "before the requested cutoff."
            )

        # --------------------------------------------------
        # Sort chronologically
        # --------------------------------------------------

        data = data.sort_values(
            "timestamp"
        ).reset_index(drop=True)

        # --------------------------------------------------
        # Aggregate route performance
        # --------------------------------------------------

        grouped = (
            data
            .groupby(self.ROUTE_COLUMNS)
            .agg(
                transaction_count=(
                    "status",
                    "size",
                ),

                success_count=(
                    "status",
                    lambda x: (
                        x == "SUCCESS"
                    ).sum(),
                ),

                failure_count=(
                    "status",
                    lambda x: (
                        x == "FAILED"
                    ).sum(),
                ),
            )
            .reset_index()
        )

        # --------------------------------------------------
        # Calculate historical success rate
        # --------------------------------------------------

        grouped["success_rate"] = (
            grouped["success_count"]
            / grouped["transaction_count"]
        )

        # --------------------------------------------------
        # Create human-readable route name
        # --------------------------------------------------

        grouped["route"] = (
            grouped["payment_method"]
            + " + "
            + grouped["bank"]
            + " + "
            + grouped["device_type"]
        )

        # --------------------------------------------------
        # Return columns in a predictable order
        # --------------------------------------------------

        return grouped[
            [
                "route",
                "payment_method",
                "bank",
                "device_type",
                "transaction_count",
                "success_count",
                "failure_count",
                "success_rate",
            ]
        ]


    def get_route_baseline(
        self,
        df: pd.DataFrame,
        payment_method: str,
        bank: str,
        device_type: str,
        before: Optional[pd.Timestamp] = None,
    ) -> RouteBaseline:
        """
        Get the baseline for one specific payment route.

        Example:

            UPI + Bank_X + Android

        If `before` is supplied, only historical transactions
        before that timestamp are considered.
        """

        # --------------------------------------------------
        # Build historical baselines
        # --------------------------------------------------

        baselines = self.build(
            df,
            before=before,
        )

        # --------------------------------------------------
        # Find requested route
        # --------------------------------------------------

        match = baselines[
            (baselines["payment_method"] == payment_method)
            & (baselines["bank"] == bank)
            & (
                baselines["device_type"]
                == device_type
            )
        ]

        # --------------------------------------------------
        # Route does not exist
        # --------------------------------------------------

        if match.empty:
            raise ValueError(
                "No baseline exists for the requested route."
            )

        # --------------------------------------------------
        # Extract the route record
        # --------------------------------------------------

        row = match.iloc[0]

        # --------------------------------------------------
        # Return strongly typed baseline object
        # --------------------------------------------------

        return RouteBaseline(
            route=str(row["route"]),

            transaction_count=int(
                row["transaction_count"]
            ),

            success_count=int(
                row["success_count"]
            ),

            failure_count=int(
                row["failure_count"]
            ),

            success_rate=float(
                row["success_rate"]
            ),
        )