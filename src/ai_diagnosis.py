import pandas as pd


# =========================================
# AI DIAGNOSIS ENGINE
# =========================================

def build_diagnosis_context(df, incident):
    """
    Prepare structured evidence for an AI model.

    The function does not make the recovery decision.
    It only collects evidence that can be passed to
    a local LLM.
    """

    if incident is None:
        return None

    incident_start = pd.Timestamp(
        incident["time_window"]
    )

    incident_end = (
        incident_start
        + pd.Timedelta(hours=1)
    )

    payment_method = (
        incident["payment_method"]
    )

    bank = incident["bank"]

    device_type = (
        incident["device_type"]
    )

    # -------------------------------------
    # Incident transactions
    # -------------------------------------

    incident_data = df[
        (df["timestamp"] >= incident_start)
        &
        (df["timestamp"] < incident_end)
        &
        (df["payment_method"]
         == payment_method)
        &
        (df["bank"] == bank)
        &
        (df["device_type"]
         == device_type)
    ].copy()

    # -------------------------------------
    # Failure analysis
    # -------------------------------------

    failures = incident_data[
        incident_data["status"] == "FAILED"
    ].copy()

    if "error_code" in failures.columns:

        failure_reasons = (
            failures
            .groupby("error_code")
            .size()
            .sort_values(
                ascending=False
            )
        )

    else:

        failure_reasons = pd.Series(
            dtype="int64"
        )

    # -------------------------------------
    # Failure percentages
    # -------------------------------------

    total_failures = len(
        failures
    )

    failure_reason_data = []

    if total_failures > 0:

        for error_code, count in (
            failure_reasons.items()
        ):

            failure_reason_data.append({
                "error_code":
                    error_code,

                "failures":
                    int(count),

                "percentage":
                    round(
                        count
                        / total_failures
                        * 100,
                        2
                    )
            })

    # -------------------------------------
    # Context
    # -------------------------------------

    context = {

        "route": {
            "payment_method":
                payment_method,

            "bank":
                bank,

            "device_type":
                device_type
        },

        "incident": {

            "time_window":
                str(incident_start),

            "transactions":
                int(
                    incident[
                        "transactions"
                    ]
                ),

            "success_rate":
                float(
                    incident[
                        "success_rate"
                    ]
                ),

            "baseline_success_rate":
                float(
                    incident[
                        "baseline_success_rate"
                    ]
                ),

            "degradation_percentage_points":
                float(
                    incident[
                        "degradation_percentage_points"
                    ]
                )
        },

        "failures": {

            "total":
                int(total_failures),

            "failure_rate":
                round(
                    total_failures
                    / len(incident_data),
                    4
                )
                if len(incident_data) > 0
                else 0.0,

            "reasons":
                failure_reason_data
        }
    }

    return context


# =========================================
# LOCAL AI PROMPT
# =========================================

def create_diagnosis_prompt(
    diagnosis_context
):
    """
    Create a structured prompt for a local LLM.

    The model is instructed to diagnose the
    incident using only supplied evidence.
    """

    if diagnosis_context is None:
        return None

    route = diagnosis_context[
        "route"
    ]

    incident = diagnosis_context[
        "incident"
    ]

    failures = diagnosis_context[
        "failures"
    ]

    prompt = f"""
You are a payment reliability diagnosis agent.

Analyze the following payment incident.

IMPORTANT:
- Use only the supplied evidence.
- Do not invent transaction facts.
- Do not recommend executing payment routing.
- Do not bypass policy controls.
- Your task is diagnosis and explanation only.

PAYMENT ROUTE
Payment method: {route['payment_method']}
Bank: {route['bank']}
Device: {route['device_type']}

INCIDENT
Time window: {incident['time_window']}
Transactions: {incident['transactions']}
Current success rate: {incident['success_rate'] * 100:.2f}%
Historical baseline: {incident['baseline_success_rate'] * 100:.2f}%
Degradation: {incident['degradation_percentage_points']:.2f} percentage points

FAILURES
Total failures: {failures['total']}
Failure rate: {failures['failure_rate'] * 100:.2f}%

Failure reasons:
{failures['reasons']}

Return a structured diagnosis containing:

1. Primary diagnosis
2. Severity: LOW, MEDIUM, HIGH, or CRITICAL
3. Confidence from 0 to 100
4. Evidence supporting the diagnosis
5. Dominant failure pattern
6. Affected route dimensions
7. Recommended investigation
8. Whether the evidence suggests a route-specific problem

Do not make a recovery decision.
"""

    return prompt.strip()


# =========================================
# DETERMINISTIC FALLBACK
# =========================================

def fallback_diagnosis(
    diagnosis_context
):
    """
    Safe fallback when no local LLM is available.

    This is deliberately evidence-based and
    does not execute any recovery action.
    """

    incident = diagnosis_context[
        "incident"
    ]

    route = diagnosis_context[
        "route"
    ]

    failures = diagnosis_context[
        "failures"
    ]

    degradation = (
        incident[
            "degradation_percentage_points"
        ]
    )

    failure_rate = (
        failures["failure_rate"]
    )

    reasons = failures[
        "reasons"
    ]

    # -------------------------------------
    # Severity
    # -------------------------------------

    if degradation >= 25:

        severity = "CRITICAL"

    elif degradation >= 15:

        severity = "HIGH"

    elif degradation >= 10:

        severity = "MEDIUM"

    else:

        severity = "LOW"

    # -------------------------------------
    # Confidence
    # -------------------------------------

    if degradation >= 20:

        confidence = 99

    elif degradation >= 15:

        confidence = 95

    elif degradation >= 10:

        confidence = 90

    else:

        confidence = 80

    # -------------------------------------
    # Dominant failure reason
    # -------------------------------------

    if reasons:

        dominant_reason = (
            reasons[0]["error_code"]
        )

        dominant_percentage = (
            reasons[0]["percentage"]
        )

    else:

        dominant_reason = (
            "UNKNOWN"
        )

        dominant_percentage = 0.0

    # -------------------------------------
    # Diagnosis
    # -------------------------------------

    primary_diagnosis = (
        f"Route-specific degradation detected "
        f"on {route['payment_method']} → "
        f"{route['bank']} → "
        f"{route['device_type']}."
    )

    evidence = [

        (
            f"Success rate declined from "
            f"{incident['baseline_success_rate'] * 100:.2f}% "
            f"to "
            f"{incident['success_rate'] * 100:.2f}%."
        ),

        (
            f"Observed degradation is "
            f"{degradation:.2f} percentage points."
        ),

        (
            f"Observed failure rate is "
            f"{failure_rate * 100:.2f}%."
        )
    ]

    if dominant_reason != "UNKNOWN":

        evidence.append(
            f"{dominant_reason} represents "
            f"{dominant_percentage:.2f}% "
            f"of observed failures."
        )

    return {

        "primary_diagnosis":
            primary_diagnosis,

        "severity":
            severity,

        "confidence":
            confidence,

        "evidence":
            evidence,

        "dominant_failure_pattern":
            dominant_reason,

        "affected_route_dimensions":
            [
                route["payment_method"],
                route["bank"],
                route["device_type"]
            ],

        "recommended_investigation":
            [
                "Inspect affected bank performance.",
                "Compare comparable alternative routes.",
                "Review dominant failure reasons.",
                "Validate recovery through policy controls."
            ],

        "route_specific_problem":
            True,

        "source":
            "evidence_based_fallback"
    }


# =========================================
# MAIN DIAGNOSIS FUNCTION
# =========================================

def diagnose_incident(
    df,
    incident
):
    """
    Generate an AI diagnosis context and
    evidence-grounded fallback diagnosis.

    The interface is intentionally designed
    so a local LLM can be inserted later.
    """

    context = build_diagnosis_context(
        df,
        incident
    )

    if context is None:
        return None

    prompt = create_diagnosis_prompt(
        context
    )

    diagnosis = fallback_diagnosis(
        context
    )

    diagnosis[
        "prompt"
    ] = prompt

    return diagnosis


# =========================================
# DISPLAY
# =========================================

def print_diagnosis(
    diagnosis
):

    if diagnosis is None:

        print(
            "\nNo diagnosis available."
        )

        return

    print("\n")
    print("=" * 60)
    print("                 AI DIAGNOSIS")
    print("=" * 60)

    print(
        "\nPrimary diagnosis:"
    )

    print(
        diagnosis[
            "primary_diagnosis"
        ]
    )

    print(
        "\nSeverity:"
    )

    print(
        diagnosis[
            "severity"
        ]
    )

    print(
        "\nConfidence:"
    )

    print(
        f"{diagnosis['confidence']}%"
    )

    print(
        "\nDominant failure pattern:"
    )

    print(
        diagnosis[
            "dominant_failure_pattern"
        ]
    )

    print(
        "\nEvidence:"
    )

    for evidence in diagnosis[
        "evidence"
    ]:

        print(
            f"  • {evidence}"
        )

    print(
        "\nRecommended investigation:"
    )

    for item in diagnosis[
        "recommended_investigation"
    ]:

        print(
            f"  • {item}"
        )

    print(
        "\nRoute-specific problem:"
    )

    print(
        diagnosis[
            "route_specific_problem"
        ]
    )

    print("\n")
    print("=" * 60)


# =========================================
# STANDALONE TEST
# =========================================

def run_test():

    from agent import (
        load_data,
        detect_incident
    )

    print(
        "\nLoading transaction data..."
    )

    df = load_data()

    print(
        "Detecting incident..."
    )

    incident = detect_incident(
        df
    )

    if incident is None:

        print(
            "\nNo incident detected."
        )

        return

    print(
        "Generating AI diagnosis..."
    )

    diagnosis = diagnose_incident(
        df,
        incident
    )

    print_diagnosis(
        diagnosis
    )


# =========================================
# MAIN
# =========================================

if __name__ == "__main__":

    run_test()