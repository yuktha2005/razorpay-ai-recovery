"""
AI Revenue Recovery
Recovery Executor

Executes ONLY actions approved by the Recovery Agent's
safety decision.

Current version:
    TEST / SIMULATION MODE

No real customer payment is automatically charged.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Any
import json
from pathlib import Path


# =========================================================
# CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

LOG_DIR = BASE_DIR / "logs"

RECOVERY_FILE = (
    LOG_DIR / "recovery_attempts.jsonl"
)


# =========================================================
# RECOVERY RESULT
# =========================================================

@dataclass
class RecoveryResult:

    attempt_id: str

    payment_id: str

    order_id: str

    action: str

    status: str

    execution_allowed: bool

    simulated: bool

    amount_rupees: float

    message: str

    created_at: str

    def to_dict(self) -> Dict[str, Any]:

        return asdict(self)


# =========================================================
# RECOVERY EXECUTOR
# =========================================================

class RecoveryExecutor:

    """
    Executes approved recovery actions.

    IMPORTANT:
    This class does not decide whether an action is safe.

    The caller must provide:
        execution_allowed=True
    """

    def __init__(self):

        LOG_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

    # -----------------------------------------------------
    # Generate attempt ID
    # -----------------------------------------------------

    def _generate_attempt_id(
        self,
        payment_id: str
    ) -> str:

        timestamp = (
            datetime.now(
                timezone.utc
            )
            .strftime("%Y%m%d%H%M%S")
        )

        return (
            f"recovery_{payment_id}_{timestamp}"
        )

    # -----------------------------------------------------
    # Store recovery attempt
    # -----------------------------------------------------

    def _store_result(
        self,
        result: RecoveryResult
    ):

        with open(
            RECOVERY_FILE,
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                json.dumps(
                    result.to_dict(),
                    ensure_ascii=False
                )
                + "\n"
            )

    # -----------------------------------------------------
    # Execute recovery
    # -----------------------------------------------------

    def execute(
        self,
        agent_decision: Dict[str, Any]
    ) -> RecoveryResult:

        payment = agent_decision.get(
            "payment",
            {}
        )

        payment_id = payment.get(
            "payment_id",
            "unknown"
        )

        order_id = payment.get(
            "order_id",
            "unknown"
        )

        amount = float(
            payment.get(
                "amount_rupees",
                0
            )
        )

        action = agent_decision.get(
            "proposed_action",
            "UNKNOWN"
        )

        execution_allowed = (
            agent_decision.get(
                "execution_allowed",
                False
            )
        )

        attempt_id = (
            self._generate_attempt_id(
                payment_id
            )
        )

        created_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        # -------------------------------------------------
        # SAFETY GATE
        # -------------------------------------------------

        if not execution_allowed:

            result = RecoveryResult(

                attempt_id=attempt_id,

                payment_id=payment_id,

                order_id=order_id,

                action=action,

                status="BLOCKED",

                execution_allowed=False,

                simulated=True,

                amount_rupees=amount,

                message=(
                    "Recovery blocked because "
                    "the safety controller did "
                    "not approve execution."
                ),

                created_at=created_at
            )

            self._store_result(result)

            return result

        # -------------------------------------------------
        # ACTION VALIDATION
        # -------------------------------------------------

        allowed_actions = {

            "RETRY_PAYMENT",

            "CUSTOMER_RETRY",

            "CUSTOMER_RETRY_LATER"

        }

        if action not in allowed_actions:

            result = RecoveryResult(

                attempt_id=attempt_id,

                payment_id=payment_id,

                order_id=order_id,

                action=action,

                status="REJECTED",

                execution_allowed=True,

                simulated=True,

                amount_rupees=amount,

                message=(
                    "Action is not supported "
                    "by the recovery executor."
                ),

                created_at=created_at
            )

            self._store_result(result)

            return result

        # -------------------------------------------------
        # SIMULATED EXECUTION
        # -------------------------------------------------

        if action == "RETRY_PAYMENT":

            message = (
                "Recovery retry created. "
                "A new customer payment attempt "
                "can now be initiated."
            )

        elif action == "CUSTOMER_RETRY":

            message = (
                "Customer retry action created. "
                "Customer should retry using "
                "the available payment method."
            )

        else:

            message = (
                "Customer retry-later action created. "
                "Immediate repeated retries are avoided."
            )

        result = RecoveryResult(

            attempt_id=attempt_id,

            payment_id=payment_id,

            order_id=order_id,

            action=action,

            status="RECOVERY_ATTEMPT_CREATED",

            execution_allowed=True,

            simulated=True,

            amount_rupees=amount,

            message=message,

            created_at=created_at
        )

        self._store_result(result)

        return result


# =========================================================
# DEMO
# =========================================================

if __name__ == "__main__":

    executor = RecoveryExecutor()

    approved_decision = {

        "agent":
            "AI Revenue Recovery Agent",

        "payment": {

            "payment_id":
                "pay_agent_test_001",

            "order_id":
                "order_agent_test_001",

            "amount_rupees":
                750,

            "currency":
                "INR",

            "payment_status":
                "failed",

            "payment_method":
                "netbanking",

            "failure_reason":
                "bank timeout",

            "revenue_at_risk":
                750

        },

        "proposed_action":
            "RETRY_PAYMENT",

        "safety_decision":
            "RECOVER",

        "execution_allowed":
            True
    }

    result = executor.execute(
        approved_decision
    )

    print("=" * 70)
    print("AI REVENUE RECOVERY — EXECUTOR")
    print("=" * 70)

    print(
        f"Attempt ID       : "
        f"{result.attempt_id}"
    )

    print(
        f"Payment ID       : "
        f"{result.payment_id}"
    )

    print(
        f"Amount           : "
        f"₹{result.amount_rupees:.2f}"
    )

    print(
        f"Action           : "
        f"{result.action}"
    )

    print(
        f"Status           : "
        f"{result.status}"
    )

    print(
        f"Execution allowed: "
        f"{result.execution_allowed}"
    )

    print(
        f"Simulated        : "
        f"{result.simulated}"
    )

    print(
        f"Message          : "
        f"{result.message}"
    )

    print("=" * 70)