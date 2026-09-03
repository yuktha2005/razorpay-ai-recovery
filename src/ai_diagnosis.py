import os
import json
import pandas as pd

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from google import genai
from google.genai import types


# =========================================
# ENVIRONMENT
# =========================================

load_dotenv()

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)


# =========================================
# AI RESPONSE SCHEMA
# =========================================

class AIDiagnosis(BaseModel):

    primary_diagnosis: str

    severity: str = Field(
        description="Must be LOW, MEDIUM, HIGH, or CRITICAL"
    )

    confidence: float = Field(
        ge=0,
        le=100
    )

    evidence: list[str]

    dominant_failure_pattern: str

    affected_route_dimensions: list[str]

    recommended_investigation: list[str]

    route_specific_problem: bool


# =========================================
# BUILD DIAGNOSIS CONTEXT
# =========================================

def build_diagnosis_context(
    df,
    incident
):
    """
    Build structured evidence for the AI diagnosis.

    The AI receives evidence generated from the
    transaction dataset rather than the entire dataset.
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

    # -----------------------------------------
    # INCIDENT ROUTE DATA
    # -----------------------------------------

    incident_data = df[
        (df["timestamp"] >= incident_start)
        &
        (df["timestamp"] < incident_end)
        &
        (df["payment_method"] == payment_method)
        &
        (df["bank"] == bank)
        &
        (df["device_type"] == device_type)
    ].copy()

    # -----------------------------------------
    # FAILURE DATA
    # -----------------------------------------

    failures = incident_data[
        incident_data["status"] == "FAILED"
    ].copy()

    # -----------------------------------------
    # FAILURE REASONS
    # -----------------------------------------

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

    total_failures = len(
        failures
    )

    failure_reason_data = []

    if total_failures > 0:

        for error_code, count in (
            failure_reasons.items()
        ):

            failure_reason_data.append(
                {
                    "error_code":
                        str(error_code),

                    "failures":
                        int(count),

                    "percentage":
                        round(
                            count
                            / total_failures
                            * 100,
                            2
                        )
                }
            )

    # -----------------------------------------
    # FINAL CONTEXT
    # -----------------------------------------

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
                (
                    round(
                        total_failures
                        / len(incident_data),
                        4
                    )
                    if len(incident_data) > 0
                    else 0.0
                ),

            "reasons":
                failure_reason_data
        }
    }

    return context


# =========================================
# CREATE AI PROMPT
# =========================================

def create_diagnosis_prompt(
    context
):
    """
    Create an evidence-grounded prompt.

    Gemini is responsible only for diagnosis.
    It cannot authorize or execute recovery.
    """

    route = context["route"]

    incident = context["incident"]

    failures = context["failures"]

    failure_reasons = json.dumps(
        failures["reasons"],
        indent=2
    )

    prompt = f"""
You are an AI payment reliability diagnosis agent.

Your task is to diagnose a payment reliability
incident using ONLY the evidence supplied below.

You are a diagnosis and reasoning component.

You are NOT authorized to:

- execute payment routing
- move money
- modify transactions
- approve recovery
- bypass policy controls
- directly select or authorize a recovery bank

A separate deterministic policy engine makes
the final recovery decision.

PAYMENT ROUTE

Payment method:
{route['payment_method']}

Bank:
{route['bank']}

Device:
{route['device_type']}


INCIDENT

Time window:
{incident['time_window']}

Transactions:
{incident['transactions']}

Current success rate:
{incident['success_rate'] * 100:.2f}%

Historical baseline:
{incident['baseline_success_rate'] * 100:.2f}%

Degradation:
{incident['degradation_percentage_points']:.2f} percentage points


FAILURE INFORMATION

Total failures:
{failures['total']}

Failure rate:
{failures['failure_rate'] * 100:.2f}%

Failure reasons:

{failure_reasons}


TASK

Produce a structured diagnosis containing:

1. Primary diagnosis
2. Severity
3. Confidence from 0 to 100
4. Evidence supporting the diagnosis
5. Dominant failure pattern
6. Affected route dimensions
7. Recommended investigation
8. Whether the evidence indicates a route-specific problem

Severity MUST be exactly one of:

LOW
MEDIUM
HIGH
CRITICAL

IMPORTANT:

Use only supplied evidence.

Do not invent transaction facts.

Do not invent failure reasons.

Do not recommend a specific recovery bank.

Do not authorize recovery.

Do not execute an action.

Do not bypass the policy engine.
"""

    return prompt.strip()


# =========================================
# GEMINI CLIENT
# =========================================

def get_gemini_client():

    if not GEMINI_API_KEY:

        return None

    return genai.Client(
        api_key=GEMINI_API_KEY,
        http_options=types.HttpOptions(
            timeout=10000
        )
    )


# =========================================
# REAL GEMINI DIAGNOSIS
# =========================================

def run_gemini_diagnosis(
    context
):
    """
    Call Gemini through the Interactions API.

    Gemini produces diagnosis only.
    """

    client = get_gemini_client()

    if client is None:

        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    prompt = create_diagnosis_prompt(
        context
    )

    interaction = client.interactions.create(
        model="gemini-3.6-flash",

        input=prompt,

        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema":
                AIDiagnosis.model_json_schema()
        },

        store=False
    )

    # -----------------------------------------
    # READ RESPONSE
    # -----------------------------------------

    output_text = getattr(
        interaction,
        "output_text",
        None
    )

    if not output_text:

        raise RuntimeError(
            "Gemini returned an empty response."
        )

    # -----------------------------------------
    # VALIDATE JSON
    # -----------------------------------------

    try:

        diagnosis = (
            AIDiagnosis.model_validate_json(
                output_text
            )
        )

    except ValidationError as error:

        raise RuntimeError(
            f"Invalid Gemini diagnosis: {error}"
        )

    # -----------------------------------------
    # VALIDATE ENUM-LIKE SEVERITY
    # -----------------------------------------

    valid_severities = {
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL"
    }

    if diagnosis.severity not in valid_severities:

        raise RuntimeError(
            "Gemini returned an invalid severity."
        )

    return diagnosis


# =========================================
# SAFE FALLBACK
# =========================================

def fallback_diagnosis(
    context
):
    """
    Evidence-based fallback used when Gemini
    is unavailable or returns invalid output.
    """

    incident = context[
        "incident"
    ]

    route = context[
        "route"
    ]

    failures = context[
        "failures"
    ]

    degradation = (
        incident[
            "degradation_percentage_points"
        ]
    )

    failure_rate = (
        failures[
            "failure_rate"
        ]
    )

    reasons = failures[
        "reasons"
    ]

    # -----------------------------------------
    # SEVERITY
    # -----------------------------------------

    if degradation >= 25:

        severity = "CRITICAL"

    elif degradation >= 15:

        severity = "HIGH"

    elif degradation >= 10:

        severity = "MEDIUM"

    else:

        severity = "LOW"

    # -----------------------------------------
    # CONFIDENCE
    # -----------------------------------------

    if degradation >= 20:

        confidence = 99

    elif degradation >= 15:

        confidence = 95

    elif degradation >= 10:

        confidence = 90

    else:

        confidence = 80

    # -----------------------------------------
    # DOMINANT FAILURE
    # -----------------------------------------

    if reasons:

        dominant_reason = (
            reasons[0]["error_code"]
        )

        dominant_percentage = (
            reasons[0]["percentage"]
        )

    else:

        dominant_reason = "UNKNOWN"

        dominant_percentage = 0.0

    # -----------------------------------------
    # EVIDENCE
    # -----------------------------------------

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

    return AIDiagnosis(

        primary_diagnosis=(
            f"Route-specific degradation detected "
            f"on {route['payment_method']} → "
            f"{route['bank']} → "
            f"{route['device_type']}."
        ),

        severity=severity,

        confidence=confidence,

        evidence=evidence,

        dominant_failure_pattern=
            dominant_reason,

        affected_route_dimensions=[

            route["payment_method"],

            route["bank"],

            route["device_type"]
        ],

        recommended_investigation=[

            "Inspect affected bank performance.",

            "Compare comparable alternative routes.",

            "Review dominant failure reasons.",

            "Validate recovery through policy controls."
        ],

        route_specific_problem=True
    )


# =========================================
# MAIN DIAGNOSIS FUNCTION
# =========================================

def diagnose_incident(
    df,
    incident
):
    """
    Generate a diagnosis using Gemini.

    If Gemini is unavailable, safely fall back
    to deterministic evidence-based diagnosis.
    """

    context = build_diagnosis_context(
        df,
        incident
    )

    if context is None:

        return None

    # -----------------------------------------
    # TRY REAL AI
    # -----------------------------------------

    try:

        diagnosis = run_gemini_diagnosis(
            context
        )

        result = diagnosis.model_dump()

        result["source"] = "gemini"

        return result

    # -----------------------------------------
    # SAFE FALLBACK
    # -----------------------------------------

    except Exception as error:

        print(
            "\n⚠️ Gemini diagnosis unavailable."
        )

        print(
            f"Reason: {error}"
        )

        print(
            "Using evidence-based fallback."
        )

        diagnosis = fallback_diagnosis(
            context
        )

        result = diagnosis.model_dump()

        result["source"] = (
            "evidence_based_fallback"
        )

        return result


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

    print(
        "=" * 60
    )

    print(
        "                 AI DIAGNOSIS"
    )

    print(
        "=" * 60
    )

    print(
        "\nAI source:"
    )

    print(
        diagnosis.get(
            "source",
            "unknown"
        )
    )

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
        f"{diagnosis['confidence']:.0f}%"
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

    print(
        "=" * 60
    )


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
        "Running Gemini AI diagnosis..."
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