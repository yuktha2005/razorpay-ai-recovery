from datetime import timedelta

import pandas as pd

from src.live_reporting.report_generator import LiveReportGenerator
from src.live_reporting.report_schema import LiveOperationsReport
from src.live_reporting.report_store import LiveReportStore


class LiveReportStream:
    """
    Creates synthetic rolling payment-operation reports from
    historical transaction data.

    This simulates a live payment operations feed without
    connecting to production Razorpay systems.
    """

    def __init__(
        self,
        generator: LiveReportGenerator | None = None,
        store: LiveReportStore | None = None,
        window_minutes: int = 15,
    ):
        self.generator = generator or LiveReportGenerator()
        self.store = store or LiveReportStore()
        self.window_minutes = window_minutes

    def prepare_transactions(
        self,
        transactions: pd.DataFrame,
    ) -> pd.DataFrame:

        df = transactions.copy()

        if "timestamp" not in df.columns:
            raise ValueError(
                "Transaction data must contain a timestamp column."
            )

        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            errors="coerce",
        )

        df = df.dropna(subset=["timestamp"])

        if df.empty:
            raise ValueError(
                "No valid timestamps found in transaction data."
            )

        return df.sort_values("timestamp").reset_index(drop=True)

    def generate_window(
        self,
        transactions: pd.DataFrame,
        end_time=None,
        save: bool = True,
    ) -> LiveOperationsReport:

        df = self.prepare_transactions(transactions)

        if end_time is None:
            end_time = df["timestamp"].max()

        end_time = pd.Timestamp(end_time)

        start_time = end_time - timedelta(
            minutes=self.window_minutes
        )

        window = df[
            (df["timestamp"] > start_time)
            & (df["timestamp"] <= end_time)
        ].copy()

        if window.empty:
            raise ValueError(
                "No transactions found inside the requested "
                "live reporting window."
            )

        report = self.generator.generate(
            window,
            window_minutes=self.window_minutes,
        )

        if save:
            self.store.save(report)

        return report

    def generate_latest(
        self,
        transactions: pd.DataFrame,
        save: bool = True,
    ) -> LiveOperationsReport:

        df = self.prepare_transactions(transactions)

        return self.generate_window(
            transactions=df,
            end_time=df["timestamp"].max(),
            save=save,
        )
    def generate_sequence(
        self,
        transactions: pd.DataFrame,
        number_of_reports: int = 5,
        save: bool = True,
    ) -> list[LiveOperationsReport]:

        df = self.prepare_transactions(transactions)

        timestamps = df["timestamp"].drop_duplicates().sort_values()

        if len(timestamps) == 0:
            raise ValueError(
                "No timestamps available for report generation."
            )

        latest_time = timestamps.max()

        reports = []

        for index in range(number_of_reports):
            end_time = (
                latest_time
                - timedelta(
                    minutes=self.window_minutes * index
                )
            )

            try:
                report = self.generate_window(
                    transactions=df,
                    end_time=end_time,
                    save=save,
                )
            except ValueError:
                continue

            reports.append(report)

        reports.reverse()

        return reports