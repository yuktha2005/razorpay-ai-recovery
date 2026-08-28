import pandas as pd

from agent import (
    load_data,
    detect_incident,
    recommend_recovery
)


# =========================================
# RECOVERY SIMULATOR
# =========================================

def simulate_recovery(df, incident, recovery):

    if incident is None:
        return None

    if recovery is None:
        return None

    # =====================================
    # INCIDENT WINDOW
    # =====================================

    incident_start = pd.Timestamp(
        incident["time_window"]
    )

    incident_end = (
        incident_start
        + pd.Timedelta(hours=1)
    )

    # =====================================
    # INCIDENT VALUES
    # =====================================

    transactions = int(
        incident["transactions"]
    )

    current_success_rate = float(
        incident["success_rate"]
    )

    current_successes = round(
        transactions
        * current_success_rate
    )

    current_failures = (
        transactions
        - current_successes
    )

    # =====================================
    # ALTERNATIVE ROUTE
    # =====================================

    alternative_bank = (
        recovery["alternative_bank"]
    )

    alternative_success_rate = float(
        recovery["alternative_success_rate"]
    )

    # =====================================
    # SIMULATED OUTCOME
    # =====================================

    simulated_successes = round(
        transactions
        * alternative_success_rate
    )

    simulated_failures = (
        transactions
        - simulated_successes
    )

    # =====================================
    # ADDITIONAL SUCCESSES
    #
    # Use the same expected-value logic
    # as recommend_recovery().
    # =====================================

    expected_current_successes = (
        transactions
        * current_success_rate
    )

    expected_alternative_successes = (
        transactions
        * alternative_success_rate
    )

    expected_additional_successes = max(
        0,
        expected_alternative_successes
        - expected_current_successes
    )

    # Display-friendly rounded value
    additional_successes = round(
        expected_additional_successes
    )

    # =====================================
    # HISTORICAL TRANSACTION VALUE
    #
    # IMPORTANT:
    # Exclude the incident window so the
    # simulator uses exactly the same
    # valuation basis as agent.py.
    # =====================================

    historical = df[
        ~(
            (df["timestamp"] >= incident_start)
            & (df["timestamp"] < incident_end)
        )
    ].copy()

    route_data = historical[
        (historical["payment_method"]
         == incident["payment_method"])
        &
        (historical["bank"]
         == incident["bank"])
        &
        (historical["device_type"]
         == incident["device_type"])
    ].copy()

    if route_data.empty:

        return None

    # =====================================
    # HISTORICAL AVERAGE TRANSACTION VALUE
    # =====================================

    average_amount = (
        route_data["amount"].mean()
    )

    # =====================================
    # ESTIMATED RECOVERED VALUE
    #
    # Use the same expected additional
    # successes as the recovery engine.
    # =====================================

    estimated_recovered_value = max(
        0,
        expected_additional_successes
        * average_amount
    )

    # =====================================
    # SUCCESS IMPROVEMENT
    # =====================================

    success_rate_improvement = (
        alternative_success_rate
        - current_success_rate
    )

    return {
        "transactions":
            transactions,

        "current_bank":
            incident["bank"],

        "alternative_bank":
            alternative_bank,

        "before_success_rate":
            current_success_rate,

        "after_success_rate":
            alternative_success_rate,

        "before_successes":
            current_successes,

        "after_successes":
            simulated_successes,

        "before_failures":
            current_failures,

        "after_failures":
            simulated_failures,

        "additional_successes":
            additional_successes,

        "expected_additional_successes":
            expected_additional_successes,

        "success_rate_improvement":
            success_rate_improvement,

        "average_transaction_value":
            average_amount,

        "estimated_recovered_value":
            estimated_recovered_value
    }


# =========================================
# DISPLAY SIMULATION
# =========================================

def run_simulation():

    df = load_data()

    incident = detect_incident(df)

    if incident is None:

        print(
            "\nNo incident available for simulation."
        )

        return

    recovery = recommend_recovery(
        df,
        incident
    )

    if recovery is None:

        print(
            "\nNo recovery route available."
        )

        return

    result = simulate_recovery(
        df,
        incident,
        recovery
    )

    if result is None:

        print(
            "\nUnable to calculate simulation."
        )

        return

    # =====================================
    # HEADER
    # =====================================

    print("\n")
    print("=" * 55)
    print("              RECOVERY SIMULATION")
    print("=" * 55)

    # =====================================
    # ROUTES
    # =====================================

    print("\nAffected route:")

    print(
        f"{incident['payment_method']}"
        f" → {incident['bank']}"
        f" → {incident['device_type']}"
    )

    print("\nRecommended route:")

    print(
        f"{incident['payment_method']}"
        f" → {result['alternative_bank']}"
        f" → {incident['device_type']}"
    )

    # =====================================
    # BEFORE
    # =====================================

    print("\n-----------------------------------------")
    print("BEFORE RECOVERY")
    print("-----------------------------------------")

    print(
        f"Success rate:"
        f" {result['before_success_rate'] * 100:.2f}%"
    )

    print(
        f"Successful payments:"
        f" {result['before_successes']}"
    )

    print(
        f"Failed payments:"
        f" {result['before_failures']}"
    )

    # =====================================
    # AFTER
    # =====================================

    print("\n-----------------------------------------")
    print("AFTER RECOVERY — SIMULATED")
    print("-----------------------------------------")

    print(
        f"Success rate:"
        f" {result['after_success_rate'] * 100:.2f}%"
    )

    print(
        f"Successful payments:"
        f" {result['after_successes']}"
    )

    print(
        f"Failed payments:"
        f" {result['after_failures']}"
    )

    # =====================================
    # OUTCOME
    # =====================================

    print("\n-----------------------------------------")
    print("RECOVERY OUTCOME")
    print("-----------------------------------------")

    print(
        f"Success improvement:"
        f" +{result['success_rate_improvement'] * 100:.2f} pp"
    )

    print(
        f"Additional successful payments:"
        f" +{result['additional_successes']}"
    )

    print(
        f"Estimated recovered value:"
        f" ₹{result['estimated_recovered_value']:,.2f}"
    )

    # =====================================
    # ACTION
    # =====================================

    print("\nRecommended action:")

    print(
        f"Temporarily prefer "
        f"{result['alternative_bank']} "
        f"for eligible "
        f"{incident['payment_method']} + "
        f"{incident['device_type']} traffic."
    )

    print("\n")
    print("=" * 55)


# =========================================
# MAIN
# =========================================

if __name__ == "__main__":
    run_simulation()