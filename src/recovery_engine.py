import pandas as pd


# =========================================
# CONFIGURATION
# =========================================

DATA_PATH = "data/transactions.csv"

INCIDENT_START = pd.Timestamp(
    "2026-07-23 19:00:00"
)

INCIDENT_END = pd.Timestamp(
    "2026-07-23 20:00:00"
)

AFFECTED_METHOD = "UPI"
AFFECTED_BANK = "Bank_X"
AFFECTED_DEVICE = "Android"

MIN_HISTORICAL_TRANSACTIONS = 100


# =========================================
# LOAD DATA
# =========================================

transactions = pd.read_csv(DATA_PATH)

transactions["timestamp"] = pd.to_datetime(
    transactions["timestamp"],
    format="mixed"
)


# =========================================
# INCIDENT ROUTE
# =========================================

incident_route = transactions[
    (transactions["timestamp"] >= INCIDENT_START)
    & (transactions["timestamp"] < INCIDENT_END)
    & (transactions["payment_method"] == AFFECTED_METHOD)
    & (transactions["bank"] == AFFECTED_BANK)
    & (transactions["device_type"] == AFFECTED_DEVICE)
].copy()


# =========================================
# HISTORICAL DATA
#
# Exclude the incident window so that the
# incident does not influence the baseline
# or recovery recommendation.
# =========================================

historical = transactions[
    ~(
        (transactions["timestamp"] >= INCIDENT_START)
        & (transactions["timestamp"] < INCIDENT_END)
    )
].copy()


# =========================================
# HISTORICAL ALTERNATIVE BANK PERFORMANCE
#
# Compare banks using the same payment
# method AND device type as the affected
# route.
#
# Example:
# UPI + Android
# =========================================

route_performance = (
    historical[
        (historical["payment_method"] == AFFECTED_METHOD)
        & (historical["device_type"] == AFFECTED_DEVICE)
    ]
    .groupby("bank")
    .agg(
        transactions=(
            "transaction_id",
            "count"
        ),

        successes=(
            "status",
            lambda x: (x == "SUCCESS").sum()
        )
    )
    .reset_index()
)


# =========================================
# HISTORICAL SUCCESS RATE
# =========================================

route_performance["success_rate"] = (
    route_performance["successes"]
    / route_performance["transactions"]
)


# =========================================
# REMOVE CURRENTLY DEGRADED BANK
# =========================================

alternatives = route_performance[
    route_performance["bank"] != AFFECTED_BANK
].copy()


# =========================================
# REQUIRE SUFFICIENT HISTORY
# =========================================

alternatives = alternatives[
    alternatives["transactions"]
    >= MIN_HISTORICAL_TRANSACTIONS
].copy()


# =========================================
# RANK ALTERNATIVE BANKS
#
# Primary criterion:
#   Historical success rate
#
# Secondary criterion:
#   Historical transaction volume
# =========================================

alternatives = alternatives.sort_values(
    [
        "success_rate",
        "transactions"
    ],
    ascending=[
        False,
        False
    ]
)


# =========================================
# CURRENT INCIDENT PERFORMANCE
# =========================================

if incident_route.empty:

    print("\nNo transactions found for the affected route.")

else:

    current_success_rate = (
        incident_route["status"] == "SUCCESS"
    ).mean()


    # =====================================
    # BEST ALTERNATIVE
    # =====================================

    if alternatives.empty:

        print("\nNo suitable alternative route found.")

    else:

        best = alternatives.iloc[0]

        alternative_success_rate = (
            best["success_rate"]
        )

        transaction_count = len(
            incident_route
        )


        # =================================
        # EXPECTED SUCCESS IMPROVEMENT
        # =================================

        current_expected_successes = (
            transaction_count
            * current_success_rate
        )

        alternative_expected_successes = (
            transaction_count
            * alternative_success_rate
        )

        additional_successes = (
            alternative_expected_successes
            - current_expected_successes
        )


        # =================================
        # HISTORICAL AFFECTED-ROUTE VALUE
        #
        # Use historical UPI + Bank_X +
        # Android transactions so the
        # recovery estimate is consistent
        # with the integrated agent.
        # =================================

        historical_route = historical[
            (historical["payment_method"] == AFFECTED_METHOD)
            & (historical["bank"] == AFFECTED_BANK)
            & (historical["device_type"] == AFFECTED_DEVICE)
        ].copy()


        if historical_route.empty:

            print(
                "\nUnable to estimate recovered revenue:"
                " no historical affected-route data."
            )

        else:

            average_amount = (
                historical_route["amount"].mean()
            )

            estimated_recovered_revenue = (
                max(0, additional_successes)
                * average_amount
            )


            # =================================
            # DISPLAY
            # =================================

            print("\n=========================================")
            print("PAYMENT RECOVERY ENGINE")
            print("=========================================")

            print("\nAffected route:")

            print(
                f"{AFFECTED_METHOD} → "
                f"{AFFECTED_BANK} → "
                f"{AFFECTED_DEVICE}"
            )


            print("\nIncident window:")

            print(
                f"{INCIDENT_START} → "
                f"{INCIDENT_END}"
            )


            print("\nIncident transactions:")

            print(
                transaction_count
            )


            print("\nCurrent success rate:")

            print(
                f"{current_success_rate * 100:.2f}%"
            )


            print("\nRecommended alternative bank:")

            print(
                best["bank"]
            )


            print("\nAlternative historical success rate:")

            print(
                f"{alternative_success_rate * 100:.2f}%"
            )


            print("\nHistorical comparable transactions:")

            print(
                int(best["transactions"])
            )


            print("\nPotential additional successful payments:")

            print(
                f"{additional_successes:.1f}"
            )


            print("\nEstimated recoverable revenue:")

            print(
                f"₹{estimated_recovered_revenue:,.2f}"
            )


            print("\nRecommended action:")

            print(
                f"Temporarily reduce routing to "
                f"{AFFECTED_BANK} and prefer "
                f"{best['bank']} for eligible "
                f"{AFFECTED_METHOD} + "
                f"{AFFECTED_DEVICE} traffic."
            )