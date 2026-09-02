import csv
from pathlib import Path
from typing import List, Dict


BASE_DIR = Path(__file__).resolve().parent.parent.parent

LOG_DIR = BASE_DIR / "logs"

LEARNING_FILE = LOG_DIR / "recovery_learning.csv"


LEARNING_COLUMNS = [
    "timestamp",
    "route",
    "attempts",
    "recoveries",
    "recovery_rate",
    "recovered_value",
    "execution_cost",
    "net_recovered_value",
    "evidence_confidence",
]


def ensure_learning_directory():
    """
    Make sure the learning-log directory exists.
    """

    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def initialize_learning_store():
    """
    Create the persistent learning CSV if it does not exist.
    """

    ensure_learning_directory()

    if LEARNING_FILE.exists():
        return

    with open(
        LEARNING_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=LEARNING_COLUMNS,
        )

        writer.writeheader()


def save_route_learning(stats, timestamp):
    """
    Persist one verified route-learning result.

    This function stores an observation rather than replacing
    previous observations.
    """

    initialize_learning_store()

    record = {
        "timestamp": timestamp,
        "route": stats.route,
        "attempts": stats.attempts,
        "recoveries": stats.recoveries,
        "recovery_rate": stats.recovery_rate,
        "recovered_value": stats.total_recovered_value,
        "execution_cost": stats.total_execution_cost,
        "net_recovered_value": stats.net_recovered_value,
        "evidence_confidence": stats.evidence_confidence,
    }

    with open(
        LEARNING_FILE,
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=LEARNING_COLUMNS,
        )

        writer.writerow(record)

    return record


def load_learning_history() -> List[Dict]:
    """
    Load all persisted learning observations.
    """

    initialize_learning_store()

    with open(
        LEARNING_FILE,
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(file)

        return list(reader)