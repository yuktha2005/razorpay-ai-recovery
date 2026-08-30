"""
AI Revenue Recovery
Recovery Case & Outcome Tracker

Tracks:
- Revenue at risk
- Recovery attempts
- Recovered revenue
- Failed recovery attempts
- Escalations
- Recovery rate
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

LOG_DIR = BASE_DIR / "logs"
CASES_FILE = LOG_DIR / "recovery_cases.json"


# =========================================================
# TRACKER
# =========================================================

class RecoveryTracker:

    def __init__(self):

        LOG_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        # Create the file if it doesn't exist.
        if not CASES_FILE.exists():
            self._save_cases({})


    # =====================================================
    # FILE OPERATIONS
    # =====================================================

    def _load_cases(self) -> Dict[str, Any]:

        if not CASES_FILE.exists():
            return {}

        try:

            with open(
                CASES_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

                if isinstance(data, dict):
                    return data

                return {}

        except (
            json.JSONDecodeError,
            OSError
        ):

            return {}


    def _save_cases(
        self,
        cases: Dict[str, Any]
    ) -> None:

        LOG_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        temp_file = CASES_FILE.with_suffix(
            ".tmp"
        )

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                cases,
                file,
                indent=2,
                ensure_ascii=False
            )

        # Replace the old file atomically.
        temp_file.replace(
            CASES_FILE
        )


    # =====================================================
    # CREATE CASE
    # =====================================================

    def create_case(
        self,
        payment_id: str,
        order_id: str,
        amount_rupees: float,
        risk_level: str,
        proposed_action: str
    ) -> Dict[str, Any]:

        if not payment_id:

            raise ValueError(
                "payment_id is required"
            )

        cases = self._load_cases()

        # -------------------------------------------------
        # Idempotency
        # -------------------------------------------------

        if payment_id in cases:
            return cases[payment_id]

        now = datetime.now(
            timezone.utc
        ).isoformat()

        case = {

            "payment_id":
                payment_id,

            "order_id":
                order_id,

            "amount_rupees":
                float(amount_rupees),

            "revenue_at_risk":
                float(amount_rupees),

            "risk_level":
                risk_level,

            "proposed_action":
                proposed_action,

            "recovery_attempted":
                False,

            "recovery_attempt_id":
                None,

            "recovery_action":
                None,

            "recovery_status":
                "OPEN",

            "recovered_amount":
                0.0,

            "created_at":
                now,

            "updated_at":
                now

        }

        cases[payment_id] = case

        self._save_cases(
            cases
        )

        return case


    # =====================================================
    # RECORD RECOVERY ATTEMPT
    # =====================================================

    def record_attempt(
        self,
        payment_id: str,
        attempt_id: str,
        action: str
    ) -> Optional[Dict[str, Any]]:

        cases = self._load_cases()

        if payment_id not in cases:
            return None

        case = cases[payment_id]

        case["recovery_attempted"] = True

        case["recovery_attempt_id"] = (
            attempt_id
        )

        case["recovery_action"] = (
            action
        )

        case["recovery_status"] = (
            "RECOVERY_ATTEMPTED"
        )

        case["updated_at"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        self._save_cases(
            cases
        )

        return case


    # =====================================================
    # MARK RECOVERED
    # =====================================================

    def mark_recovered(
        self,
        payment_id: str,
        recovered_amount: float
    ) -> Optional[Dict[str, Any]]:

        cases = self._load_cases()

        if payment_id not in cases:
            return None

        case = cases[payment_id]

        recovered = max(
            0.0,
            float(recovered_amount)
        )

        # Never record more than the original
        # amount at risk.
        recovered = min(
            recovered,
            float(
                case["revenue_at_risk"]
            )
        )

        case["recovered_amount"] = (
            recovered
        )

        case["recovery_status"] = (
            "RECOVERED"
        )

        case["updated_at"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        self._save_cases(
            cases
        )

        return case


    # =====================================================
    # MARK FAILED
    # =====================================================

    def mark_failed(
        self,
        payment_id: str
    ) -> Optional[Dict[str, Any]]:

        cases = self._load_cases()

        if payment_id not in cases:
            return None

        case = cases[payment_id]

        case["recovery_status"] = (
            "FAILED"
        )

        case["updated_at"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        self._save_cases(
            cases
        )

        return case


    # =====================================================
    # MARK ESCALATED
    # =====================================================

    def mark_escalated(
        self,
        payment_id: str
    ) -> Optional[Dict[str, Any]]:

        cases = self._load_cases()

        if payment_id not in cases:
            return None

        case = cases[payment_id]

        case["recovery_status"] = (
            "ESCALATED"
        )

        case["updated_at"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        self._save_cases(
            cases
        )

        return case


    # =====================================================
    # GET CASE
    # =====================================================

    def get_case(
        self,
        payment_id: str
    ) -> Optional[Dict[str, Any]]:

        cases = self._load_cases()

        return cases.get(
            payment_id
        )


    # =====================================================
    # GET ALL CASES
    # =====================================================

    def get_all_cases(self):

        cases = self._load_cases()

        return list(
            cases.values()
        )


    # =====================================================
    # DASHBOARD METRICS
    # =====================================================

    def get_metrics(
        self
    ) -> Dict[str, Any]:

        cases = self._load_cases()

        total_cases = len(
            cases
        )

        revenue_at_risk = sum(
            float(
                case.get(
                    "revenue_at_risk",
                    0
                )
            )
            for case in cases.values()
        )

        recovered_revenue = sum(
            float(
                case.get(
                    "recovered_amount",
                    0
                )
            )
            for case in cases.values()
        )

        recovery_attempts = sum(
            1
            for case in cases.values()
            if case.get(
                "recovery_attempted",
                False
            )
        )

        successful_recoveries = sum(
            1
            for case in cases.values()
            if case.get(
                "recovery_status"
            ) == "RECOVERED"
        )

        failed_recoveries = sum(
            1
            for case in cases.values()
            if case.get(
                "recovery_status"
            ) == "FAILED"
        )

        escalated_cases = sum(
            1
            for case in cases.values()
            if case.get(
                "recovery_status"
            ) == "ESCALATED"
        )

        open_cases = sum(
            1
            for case in cases.values()
            if case.get(
                "recovery_status"
            ) in [
                "OPEN",
                "RECOVERY_ATTEMPTED"
            ]
        )

        if revenue_at_risk > 0:

            recovery_rate = (
                recovered_revenue
                / revenue_at_risk
            ) * 100

        else:

            recovery_rate = 0.0

        return {

            "total_cases":
                total_cases,

            "revenue_at_risk":
                round(
                    revenue_at_risk,
                    2
                ),

            "recovered_revenue":
                round(
                    recovered_revenue,
                    2
                ),

            "recovery_attempts":
                recovery_attempts,

            "successful_recoveries":
                successful_recoveries,

            "failed_recoveries":
                failed_recoveries,

            "escalated_cases":
                escalated_cases,

            "open_cases":
                open_cases,

            "recovery_rate_percent":
                round(
                    recovery_rate,
                    2
                )

        }


# =========================================================
# DIRECT TEST
# =========================================================

if __name__ == "__main__":

    tracker = RecoveryTracker()

    print("=" * 70)
    print("RECOVERY TRACKER TEST")
    print("=" * 70)

    case = tracker.create_case(
        payment_id="tracker_test_001",
        order_id="order_tracker_test_001",
        amount_rupees=750,
        risk_level="MEDIUM",
        proposed_action="RETRY_PAYMENT"
    )

    print("\nCASE CREATED")
    print("-" * 70)
    print(
        json.dumps(
            case,
            indent=2
        )
    )

    attempt = tracker.record_attempt(
        payment_id="tracker_test_001",
        attempt_id="attempt_tracker_001",
        action="RETRY_PAYMENT"
    )

    print("\nATTEMPT RECORDED")
    print("-" * 70)
    print(
        json.dumps(
            attempt,
            indent=2
        )
    )

    recovered = tracker.mark_recovered(
        payment_id="tracker_test_001",
        recovered_amount=750
    )

    print("\nRECOVERED")
    print("-" * 70)
    print(
        json.dumps(
            recovered,
            indent=2
        )
    )

    print("\nMETRICS")
    print("-" * 70)
    print(
        json.dumps(
            tracker.get_metrics(),
            indent=2
        )
    )

    print("=" * 70)