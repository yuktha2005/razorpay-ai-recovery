import csv
from datetime import datetime
from pathlib import Path


# =========================================
# CONFIGURATION
# =========================================

BASE_DIR = Path(__file__).resolve().parent.parent

LOG_DIR = BASE_DIR / "logs"

AUDIT_FILE = LOG_DIR / "recovery_audit.csv"


# =========================================
# AUDIT COLUMNS
# =========================================

AUDIT_COLUMNS = [
    "timestamp",
    "incident_time",
    "payment_method",
    "affected_bank",
    "device_type",
    "recommended_bank",
    "policy_decision",
    "policy_approved",
    "incident_transactions",
    "failed_transactions",
    "eligible_transactions",
    "recovered_transactions",
    "remaining_failed",
    "stopped_transactions",
    "escalated_transactions",
    "success_rate_before",
    "success_rate_after",
    "success_improvement_pp",
    "expected_additional_successes",
    "estimated_recovered_value",
    "simulated_recovered_value",
    "average_transaction_value",
    "policy_reason"
]


# =========================================
# ENSURE LOG DIRECTORY
# =========================================

def ensure_log_directory():

    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


# =========================================
# CREATE AUDIT FILE
# =========================================

def initialize_audit_log():

    ensure_log_directory()

    if not AUDIT_FILE.exists():

        with open(
            AUDIT_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=AUDIT_COLUMNS
            )

            writer.writeheader()


# =========================================
# WRITE AUDIT EVENT
# =========================================

def log_recovery_event(
    incident,
    recovery,
    policy_result,
    batch_result
):
    """
    Write one complete recovery decision
    to the persistent audit log.
    """

    initialize_audit_log()

    # -------------------------------------
    # Incident information
    # -------------------------------------

    incident_time = incident.get(
        "time_window",
        ""
    )

    payment_method = incident.get(
        "payment_method",
        ""
    )

    affected_bank = incident.get(
        "bank",
        ""
    )

    device_type = incident.get(
        "device_type",
        ""
    )

    # -------------------------------------
    # Recovery information
    # -------------------------------------

    if recovery:

        recommended_bank = recovery.get(
            "alternative_bank",
            ""
        )

    else:

        recommended_bank = ""

    # -------------------------------------
    # Batch information
    # -------------------------------------

    if batch_result:

        incident_transactions = (
            batch_result.get(
                "total_transactions",
                0
            )
        )

        failed_transactions = (
            batch_result.get(
                "failed_transactions",
                0
            )
        )

        eligible_transactions = (
            batch_result.get(
                "eligible_transactions",
                0
            )
        )

        recovered_transactions = (
            batch_result.get(
                "recovered_transactions",
                0
            )
        )

        remaining_failed = (
            batch_result.get(
                "remaining_failed",
                0
            )
        )

        stopped_transactions = (
            batch_result.get(
                "stopped_transactions",
                0
            )
        )

        escalated_transactions = (
            batch_result.get(
                "escalated_transactions",
                0
            )
        )

        success_rate_before = (
            batch_result.get(
                "current_success_rate",
                0
            )
        )

        success_rate_after = (
            batch_result.get(
                "alternative_success_rate",
                0
            )
        )

        success_improvement_pp = (
            batch_result.get(
                "success_rate_improvement",
                0
            )
            * 100
        )

        expected_additional_successes = (
            batch_result.get(
                "expected_additional_successes",
                0
            )
        )

        estimated_recovered_value = (
            batch_result.get(
                "estimated_recovered_value",
                0
            )
        )

        simulated_recovered_value = (
            batch_result.get(
                "simulated_recovered_value",
                0
            )
        )

        average_transaction_value = (
            batch_result.get(
                "average_transaction_value",
                0
            )
        )

    else:

        incident_transactions = 0
        failed_transactions = 0
        eligible_transactions = 0
        recovered_transactions = 0
        remaining_failed = 0
        stopped_transactions = 0
        escalated_transactions = 0
        success_rate_before = 0
        success_rate_after = 0
        success_improvement_pp = 0
        expected_additional_successes = 0
        estimated_recovered_value = 0
        simulated_recovered_value = 0
        average_transaction_value = 0

    # -------------------------------------
    # Policy information
    # -------------------------------------

    policy_decision = policy_result.get(
        "decision",
        "STOP"
    )

    policy_approved = policy_result.get(
        "approved",
        False
    )

    policy_reason = policy_result.get(
        "reason",
        ""
    )

    # -------------------------------------
    # Create record
    # -------------------------------------

    record = {
        "timestamp":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "incident_time":
            incident_time,

        "payment_method":
            payment_method,

        "affected_bank":
            affected_bank,

        "device_type":
            device_type,

        "recommended_bank":
            recommended_bank,

        "policy_decision":
            policy_decision,

        "policy_approved":
            policy_approved,

        "incident_transactions":
            incident_transactions,

        "failed_transactions":
            failed_transactions,

        "eligible_transactions":
            eligible_transactions,

        "recovered_transactions":
            recovered_transactions,

        "remaining_failed":
            remaining_failed,

        "stopped_transactions":
            stopped_transactions,

        "escalated_transactions":
            escalated_transactions,

        "success_rate_before":
            success_rate_before,

        "success_rate_after":
            success_rate_after,

        "success_improvement_pp":
            success_improvement_pp,

        "expected_additional_successes":
            expected_additional_successes,

        "estimated_recovered_value":
            estimated_recovered_value,

        "simulated_recovered_value":
            simulated_recovered_value,

        "average_transaction_value":
            average_transaction_value,

        "policy_reason":
            policy_reason
    }

    # -------------------------------------
    # Append record
    # -------------------------------------

    with open(
        AUDIT_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=AUDIT_COLUMNS
        )

        writer.writerow(
            record
        )

    return record


# =========================================
# READ AUDIT LOG
# =========================================

def load_audit_log():

    initialize_audit_log()

    try:

        import pandas as pd

        return pd.read_csv(
            AUDIT_FILE
        )

    except Exception:

        return None


# =========================================
# DISPLAY AUDIT LOG
# =========================================

def print_audit_log():

    audit = load_audit_log()

    if audit is None:

        print(
            "\nUnable to load audit log."
        )

        return

    if audit.empty:

        print(
            "\nAudit log is empty."
        )

        return

    print("\n")
    print("=" * 80)
    print("                         AUDIT LOG")
    print("=" * 80)

    print(
        audit[
            [
                "timestamp",
                "incident_time",
                "affected_bank",
                "recommended_bank",
                "policy_decision",
                "policy_approved",
                "recovered_transactions",
                "expected_additional_successes",
                "estimated_recovered_value"
            ]
        ].to_string(
            index=False
        )
    )

    print("\n")
    print("=" * 80)


# =========================================
# STANDALONE TEST
# =========================================

if __name__ == "__main__":

    initialize_audit_log()

    print(
        "\nAudit logger initialized."
    )

    print(
        f"Audit file:"
        f" {AUDIT_FILE}"
    )

    print(
        "\nNo recovery event was written."
    )