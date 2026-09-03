import json
from dataclasses import asdict
from pathlib import Path

from src.live_reporting.report_schema import LiveOperationsReport


class LiveReportStore:

    def __init__(
        self,
        directory: str = "data/live_reports",
    ):
        self.directory = Path(directory)
        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        report: LiveOperationsReport,
    ) -> Path:

        path = self.directory / (
            f"{report.report_id}.json"
        )

        with path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                asdict(report),
                file,
                indent=2,
            )

        return path

    def latest(self) -> Path | None:

        reports = sorted(
            self.directory.glob("LIVE-*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        return reports[0] if reports else None