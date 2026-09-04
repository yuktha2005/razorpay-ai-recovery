import csv
from datetime import datetime
from pathlib import Path

import pandas as pd


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
    "audit_event_type",

    "incident_time",
    "payment_method",
    "affected_bank",
    "device_type",

    "recommended_bank",

    "policy_decision",
    "policy_approved",
    "policy_reason",
    "human_review_required",

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

    "guardrail_decision",
    "guardrail_reason",
    "recovery_healthy",
    "rollback_required",

    "attempted_amount",
    "recovered_amount",
    "execution_cost",
    "net_recovered_value",
    "recovery_rate"
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
# CREATE / MIGRATE AUDIT FILE
# =========================================

def initialize_audit_log():

    ensure_log_directory()

    # -------------------------------------
    # New audit file
    # -------------------------------------

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

        return


    # -------------------------------------
    # Existing audit file
    # -------------------------------------
    #
    # If an older version of the audit file
    # exists, migrate it to the new schema
    # while preserving previous records.
    # -------------------------------------

    try:

        with open(
            AUDIT_FILE,
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            existing_rows = list(reader)

            existing_columns = (
                reader.fieldnames or []
            )

        missing_columns = [
            column
            for column in AUDIT_COLUMNS
            if column not in existing_columns
        ]

        if not missing_columns:

            return


        # ---------------------------------
        # Add missing fields
        # ---------------------------------

        for row in existing_rows:

            for column in missing_columns:

                # Safe defaults for migrated
                # historical records.

                if column == "audit_event_type":

                    row[column] = "RECOVERY_DECISION"

                elif column == "human_review_required":

                    row[column] = "False"

                elif column == "guardrail_decision":

                    row[column] = "NOT_RECORDED"

                elif column == "guardrail_reason":

                    row[column] = ""

                elif column == "recovery_healthy":

                    row[column] = ""

                elif column == "rollback_required":

                    row[column] = "False"

                else:

                    row[column] = ""


        # ---------------------------------
        # Rewrite using new schema
        # ---------------------------------

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

            for row in existing_rows:

                writer.writerow(
                    {
                        column:
                            row.get(
                                column,
                                ""
                            )
                        for column
                        in AUDIT_COLUMNS
                    }
                )

    except Exception as exc:

        print(
            "\n⚠️ Audit migration warning:"
        )

        print(
            str(exc)
        )


# =========================================
# SAFE VALUE HELPERS
# =========================================

def _get(dictionary, key, default=""):

    if not dictionary:

        return default

    return dictionary.get(
        key,
        default
    )


def _to_percentage(value):

    if value is None:

        return 0

    try:

        value = float(value)

    except (
        TypeError,
        ValueError
    ):

        return 0

    # Convert decimal rates such as
    # 0.9581 into 95.81.

    if 0 <= value <= 1:

        return value * 100

    return value


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

    Captures:

        • incident context
        • recovery recommendation
        • policy decision
        • human escalation
        • batch outcome
        • guardrail status
        • rollback requirement
    """

    initialize_audit_log()


    # =====================================
    # INCIDENT INFORMATION
    # =====================================

    incident_time = _get(
        incident,
        "time_window"
    )

    payment_method = _get(
        incident,
        "payment_method"
    )

    affected_bank = _get(
        incident,
        "bank"
    )

    device_type = _get(
        incident,
        "device_type"
    )


    # =====================================
    # RECOVERY INFORMATION
    # =====================================

    recommended_bank = _get(
        recovery,
        "alternative_bank"
    )


    # =====================================
    # BATCH INFORMATION
    # =====================================

    incident_transactions = _get(
        batch_result,
        "total_transactions",
        0
    )

    failed_transactions = _get(
        batch_result,
        "failed_transactions",
        0
    )

    eligible_transactions = _get(
        batch_result,
        "eligible_transactions",
        0
    )

    recovered_transactions = _get(
        batch_result,
        "recovered_transactions",
        0
    )

    remaining_failed = _get(
        batch_result,
        "remaining_failed",
        0
    )

    stopped_transactions = _get(
        batch_result,
        "stopped_transactions",
        0
    )

    escalated_transactions = _get(
        batch_result,
        "escalated_transactions",
        0
    )


    # =====================================
    # SUCCESS METRICS
    # =====================================

    success_rate_before = _to_percentage(
        _get(
            batch_result,
            "current_success_rate",
            0
        )
    )

    success_rate_after = _to_percentage(
        _get(
            batch_result,
            "alternative_success_rate",
            0
        )
    )


    success_improvement_pp = _get(
        batch_result,
        "success_rate_improvement",
        0
    )

    try:

        success_improvement_pp = (
            float(
                success_improvement_pp
            )
            * 100
        )

    except (
        TypeError,
        ValueError
    ):

        success_improvement_pp = 0


    expected_additional_successes = _get(
        batch_result,
        "expected_additional_successes",
        0
    )

    estimated_recovered_value = _get(
        batch_result,
        "estimated_recovered_value",
        0
    )

    simulated_recovered_value = _get(
        batch_result,
        "simulated_recovered_value",
        0
    )

    average_transaction_value = _get(
        batch_result,
        "average_transaction_value",
        0
    )


    # =====================================
    # POLICY INFORMATION
    # =====================================

    policy_decision = _get(
        policy_result,
        "decision",
        "STOP"
    )

    policy_approved = _get(
        policy_result,
        "approved",
        False
    )

    policy_reason = _get(
        policy_result,
        "reason",
        ""
    )

    human_review_required = _get(
        policy_result,
        "human_review_required",
        False
    )


    # =====================================
    # GUARDRAIL INFORMATION
    # =====================================

    guardrail_decision = _get(
        batch_result,
        "guardrail_decision",
        "NOT_APPLICABLE"
    )

    guardrail_reason = _get(
        batch_result,
        "guardrail_reason",
        ""
    )

    recovery_healthy = _get(
        batch_result,
        "recovery_healthy",
        False
    )

    rollback_required = _get(
        batch_result,
        "rollback_required",
        False
    )


    # =====================================
    # FINANCIAL OUTCOME METRICS
    # =====================================

    attempted_amount = _get(
        batch_result,
        "attempted_amount",
        ""
    )

    recovered_amount = _get(
        batch_result,
        "recovered_amount",
        ""
    )

    execution_cost = _get(
        batch_result,
        "execution_cost",
        ""
    )

    net_recovered_value = _get(
        batch_result,
        "net_recovered_value",
        ""
    )

    recovery_rate = _get(
        batch_result,
        "recovery_rate",
        ""
    )


    # =====================================
    # AUDIT EVENT TYPE
    # =====================================

    if rollback_required:

        audit_event_type = "ROLLBACK"

    elif policy_decision == "ESCALATE":

        audit_event_type = "ESCALATION"

    elif policy_decision == "STOP":

        audit_event_type = "STOP"

    elif policy_decision == "RECOVER":

        audit_event_type = "RECOVERY_DECISION"

    else:

        audit_event_type = "POLICY_EVENT"


    # =====================================
    # CREATE RECORD
    # =====================================

    record = {

        "timestamp":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "audit_event_type":
            audit_event_type,


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

        "policy_reason":
            policy_reason,

        "human_review_required":
            human_review_required,


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


        "guardrail_decision":
            guardrail_decision,

        "guardrail_reason":
            guardrail_reason,

        "recovery_healthy":
            recovery_healthy,

        "rollback_required":
            rollback_required,

        "attempted_amount":
            attempted_amount,

        "recovered_amount":
            recovered_amount,

        "execution_cost":
            execution_cost,

        "net_recovered_value":
            net_recovered_value,

        "recovery_rate":
            recovery_rate
    }


    # =====================================
    # APPEND RECORD
    # =====================================

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
        return pd.read_csv(
            AUDIT_FILE
        )

    except Exception as exc:

        print(
            f"\n⚠️ Unable to load audit log: {exc}"
        )

        return None


# =========================================
# AUDIT SUMMARY
# =========================================

def get_audit_summary():

    audit = load_audit_log()

    if audit is None or audit.empty:

        return {
            "recovery_runs": 0,
            "approved": 0,
            "stopped": 0,
            "escalated": 0,
            "rollbacks": 0,
            "recovered_transactions": 0,
            "simulated_recovered_value": 0
        }


    def count_value(column, value):

        if column not in audit.columns:

            return 0

        return int(
            (
                audit[column]
                .astype(str)
                .str.upper()
                == str(value).upper()
            ).sum()
        )


    recovered_transactions = 0

    if "recovered_transactions" in audit.columns:

        recovered_transactions = int(
            pd.to_numeric(
                audit[
                    "recovered_transactions"
                ],
                errors="coerce"
            )
            .fillna(0)
            .sum()
        )


    simulated_value = 0

    if "simulated_recovered_value" in audit.columns:

        simulated_value = float(
            pd.to_numeric(
                audit[
                    "simulated_recovered_value"
                ],
                errors="coerce"
            )
            .fillna(0)
            .sum()
        )


    return {

        "recovery_runs":
            len(audit),

        "approved":
            count_value(
                "policy_decision",
                "RECOVER"
            ),

        "stopped":
            count_value(
                "policy_decision",
                "STOP"
            ),

        "escalated":
            count_value(
                "policy_decision",
                "ESCALATE"
            ),

        "rollbacks":
            count_value(
                "audit_event_type",
                "ROLLBACK"
            ),

        "recovered_transactions":
            recovered_transactions,

        "simulated_recovered_value":
            simulated_value
    }


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
    print("=" * 110)
    print("                         AUDIT LOG")
    print("=" * 110)


    display_columns = [

        "timestamp",

        "audit_event_type",

        "affected_bank",

        "recommended_bank",

        "policy_decision",

        "policy_approved",

        "human_review_required",

        "recovered_transactions",

        "expected_additional_successes",

        "estimated_recovered_value",

        "simulated_recovered_value",

        "guardrail_decision",

        "rollback_required"
    ]


    available_columns = [

        column

        for column in display_columns

        if column in audit.columns
    ]


    print(
        audit[
            available_columns
        ].to_string(
            index=False
        )
    )


    print("\n")
    print("=" * 110)


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


    summary = get_audit_summary()


    print("\nAudit summary:")

    print(
        f"  Recovery runs:"
        f" {summary['recovery_runs']}"
    )

    print(
        f"  Approved:"
        f" {summary['approved']}"
    )

    print(
        f"  Stopped:"
        f" {summary['stopped']}"
    )

    print(
        f"  Escalated:"
        f" {summary['escalated']}"
    )

    print(
        f"  Rollbacks:"
        f" {summary['rollbacks']}"
    )

    print(
        f"  Recovered transactions:"
        f" {summary['recovered_transactions']}"
    )

    print(
        f"  Simulated recovered value:"
        f" ₹{summary['simulated_recovered_value']:,.2f}"
    )


    print(
        "\nNo recovery event was written."
    )