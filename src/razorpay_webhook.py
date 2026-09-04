import os
import sys
import json
import hashlib
import hmac
import requests
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv

try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    FastAPI = None
    Request = None
    HTTPException = None
    CORSMiddleware = None

# =========================================================
# PATH CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv(
    BASE_DIR / ".env",
    override=True
)

WEBHOOK_SECRET = os.getenv(
    "RAZORPAY_WEBHOOK_SECRET", ""
)

RAZORPAY_KEY_ID = os.getenv(
    "RAZORPAY_KEY_ID", ""
)

RAZORPAY_KEY_SECRET = os.getenv(
    "RAZORPAY_KEY_SECRET", ""
)


# =========================================================
# PROJECT MODULES
# =========================================================

from src.recovery_agent import RecoveryAgent
from src.recovery_executor import RecoveryExecutor
from src.recovery_tracker import RecoveryTracker


# =========================================================
# FASTAPI
# =========================================================

if FastAPI is not None:
    app = FastAPI(
        title="AI Revenue Recovery - Razorpay Webhook",
        version="1.0.0"
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5500",
            "http://localhost:5500",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    class _DummyApp:
        def post(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
        def get(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    app = _DummyApp()

recovery_agent = RecoveryAgent()
recovery_executor = RecoveryExecutor()
recovery_tracker = RecoveryTracker()


# =========================================================
# LOCAL STORAGE
# =========================================================

LOG_DIR = BASE_DIR / "logs"

EVENT_FILE = (
    LOG_DIR /
    "razorpay_webhook_events.jsonl"
)

PROCESSED_EVENT_FILE = (
    LOG_DIR /
    "processed_webhook_events.txt"
)


def ensure_log_directory():
    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


# =========================================================
# IDEMPOTENCY
# =========================================================

def event_already_processed(event_id):

    if not event_id:
        return False

    if not PROCESSED_EVENT_FILE.exists():
        return False

    with open(
        PROCESSED_EVENT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        for line in file:

            if line.strip() == event_id:
                return True

    return False


def mark_event_processed(event_id):

    if not event_id:
        return

    ensure_log_directory()

    with open(
        PROCESSED_EVENT_FILE,
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            event_id + "\n"
        )


# =========================================================
# SIGNATURE VERIFICATION
# =========================================================

def verify_webhook_signature(
    raw_body,
    received_signature
):

    if not received_signature:
        return False

    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(
        expected_signature,
        received_signature
    )


# =========================================================
# EVENT STORAGE
# =========================================================

def store_webhook_event(
    event_id,
    event_type,
    payload
):

    ensure_log_directory()

    record = {

        "received_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "event_id":
            event_id,

        "event":
            event_type,

        "payload":
            payload

    }

    with open(
        EVENT_FILE,
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            json.dumps(
                record,
                ensure_ascii=False
            )
            + "\n"
        )


# =========================================================
# PAYMENT EXTRACTION
# =========================================================

def extract_payment_information(payload):

    payment_entity = (
        payload
        .get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )

    return {

        "payment_id":
            payment_entity.get("id"),

        "order_id":
            payment_entity.get("order_id"),

        "amount":
            payment_entity.get("amount"),

        "currency":
            payment_entity.get("currency"),

        "status":
            payment_entity.get("status"),

        "method":
            payment_entity.get("method"),

        "email":
            payment_entity.get("email"),

        "contact":
            payment_entity.get("contact"),

        "failure_reason":
            (
                payment_entity.get(
                    "error_description"
                )
                or
                payment_entity.get(
                    "error_reason"
                )
                or
                payment_entity.get(
                    "error_code"
                )
                or
                ""
            )

    }


# =========================================================
# REVENUE EVENT
# =========================================================

def build_revenue_event(
    event_type,
    payment
):

    amount_paise = (
        payment.get("amount") or 0
    )

    amount_rupees = (
        float(amount_paise) / 100
    )

    revenue_at_risk = (
        amount_rupees
        if event_type == "payment.failed"
        else 0.0
    )

    return {

        "event_type":
            event_type,

        "payment_id":
            payment.get("payment_id"),

        "order_id":
            payment.get("order_id"),

        "amount_rupees":
            amount_rupees,

        "currency":
            payment.get("currency"),

        "payment_status":
            payment.get("status"),

        "payment_method":
            payment.get("method"),

        "failure_reason":
            payment.get("failure_reason"),

        "revenue_at_risk":
            revenue_at_risk,

        "recovery_required":
            event_type == "payment.failed"

    }


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():

    return {

        "status":
            "ok",

        "service":
            "razorpay-webhook",

        "message":
            "Webhook receiver is running",

        "webhook_endpoint":
            "/webhook/razorpay"

    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {

        "status":
            "ok",

        "service":
            "razorpay-webhook",

        "environment":
            "test"

    }

@app.post("/create-order")
async def create_order(request: Request):
    """
    Create a Razorpay Test Mode order for the browser checkout page.

    Expected JSON:
        {"amount_rupees": 500}
    """

    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=500,
            detail=(
                "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET "
                "must be configured in .env"
            )
        )

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON body."
        )

    try:
        amount_rupees = float(
            data.get("amount_rupees")
        )
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="amount_rupees must be a number."
        )

    if amount_rupees <= 0:
        raise HTTPException(
            status_code=400,
            detail="amount_rupees must be greater than 0."
        )

    if amount_rupees > 100000:
        raise HTTPException(
            status_code=400,
            detail="Demo amount cannot exceed ₹100,000."
        )

    amount_paise = int(
        round(amount_rupees * 100)
    )

    try:
        response = requests.post(
            "https://api.razorpay.com/v1/orders",
            auth=(
                RAZORPAY_KEY_ID,
                RAZORPAY_KEY_SECRET
            ),
            json={
                "amount": amount_paise,
                "currency": "INR",
                "receipt": (
                    "ai_recovery_"
                    + datetime.now(
                        timezone.utc
                    ).strftime("%Y%m%d%H%M%S%f")
                ),
                "notes": {
                    "source": "ai_revenue_recovery_demo"
                }
            },
            timeout=15
        )

    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to reach Razorpay: {exc}"
        )

    if not response.ok:
        try:
            error_data = response.json()
        except ValueError:
            error_data = {}

        description = (
            error_data
            .get("error", {})
            .get("description")
            or "Razorpay order creation failed."
        )

        raise HTTPException(
            status_code=response.status_code,
            detail=description
        )

    order = response.json()

    return {
        "key_id": RAZORPAY_KEY_ID,
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "status": order.get("status"),
        "receipt": order.get("receipt")
    }


@app.post("/verify-payment")
async def verify_payment(request: Request):
    """
    Verify the Razorpay Checkout payment signature.

    Expected JSON:
        {
            "razorpay_order_id": "...",
            "razorpay_payment_id": "...",
            "razorpay_signature": "..."
        }
    """

    if not RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=500,
            detail="RAZORPAY_KEY_SECRET is missing from .env"
        )

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON body."
        )

    order_id = data.get(
        "razorpay_order_id"
    )

    payment_id = data.get(
        "razorpay_payment_id"
    )

    received_signature = data.get(
        "razorpay_signature"
    )

    if not order_id or not payment_id or not received_signature:
        raise HTTPException(
            status_code=400,
            detail=(
                "razorpay_order_id, "
                "razorpay_payment_id and "
                "razorpay_signature are required."
            )
        )

    verification_message = (
        f"{order_id}|{payment_id}"
    ).encode("utf-8")

    expected_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode("utf-8"),
        verification_message,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(
        expected_signature,
        received_signature
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay payment signature."
        )

    payment_details = {}

    try:
        payment_response = requests.get(
            (
                "https://api.razorpay.com/v1/payments/"
                + payment_id
            ),
            auth=(
                RAZORPAY_KEY_ID,
                RAZORPAY_KEY_SECRET
            ),
            timeout=15
        )

        if payment_response.ok:
            payment_details = (
                payment_response.json()
            )

    except requests.RequestException:
        # Signature verification already succeeded.
        # Payment API lookup is only used to enrich the response.
        payment_details = {}

    return {
        "verified": True,
        "order_id": order_id,
        "payment_id": payment_id,
        "amount": payment_details.get(
            "amount"
        ),
        "currency": payment_details.get(
            "currency",
            "INR"
        ),
        "status": payment_details.get(
            "status",
            "verified"
        ),
        "method": payment_details.get(
            "method"
        )
    }


# =========================================================
# DASHBOARD API
# =========================================================

@app.get("/dashboard/metrics")
def dashboard_metrics():
    """
    Return aggregate recovery metrics for the dashboard.
    """

    return recovery_tracker.get_metrics()


@app.get("/dashboard/cases")
def dashboard_cases():
    """
    Return all recovery cases for the dashboard.
    """

    cases = recovery_tracker.get_all_cases()

    # Newest cases first
    cases = sorted(
        cases,
        key=lambda case: case.get(
            "updated_at",
            ""
        ),
        reverse=True
    )

    return {
        "total": len(cases),
        "cases": cases
    }
# =========================================================
# DASHBOARD — LATEST AI DECISION
# =========================================================

@app.get("/dashboard/ai-decision")
def dashboard_ai_decision():
    """
    Return the latest AI recovery decision recorded
    in the webhook event log.
    """

    if not EVENT_FILE.exists():
        return {
            "available": False,
            "decision": None
        }

    latest_decision = None

    with open(
        EVENT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            decision = record.get(
                "payload",
                {}
            ).get(
                "agent_decision"
            )

            if decision:
                latest_decision = decision

    if latest_decision is None:
        return {
            "available": False,
            "decision": None
        }

    risk = latest_decision.get(
        "risk_assessment",
        {}
    )

    system_state = latest_decision.get(
        "system_state",
        {}
    )

    return {
        "available": True,

        "decision": {
            "payment_id":
                latest_decision
                .get("payment", {})
                .get("payment_id"),

            "failure_category":
                risk.get(
                    "failure_category"
                ),

            "risk_score":
                risk.get(
                    "risk_score"
                ),

            "risk_level":
                risk.get(
                    "risk_level"
                ),

            "recommended_action":
                risk.get(
                    "recommended_action"
                ),

            "reason":
                risk.get(
                    "reason"
                ),

            "ai_confidence":
                system_state.get(
                    "ai_confidence"
                ),

            "safety_decision":
                latest_decision.get(
                    "safety_decision"
                ),

            "safety_reason":
                latest_decision.get(
                    "safety_reason"
                ),

            "execution_allowed":
                latest_decision.get(
                    "execution_allowed"
                )
        }
    }
# =========================================================
# RAZORPAY WEBHOOK
# =========================================================

@app.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request
):

    # -----------------------------------------------------
    # 1. READ RAW BODY
    # -----------------------------------------------------

    raw_body = await request.body()

    received_signature = (
        request.headers.get(
            "X-Razorpay-Signature"
        )
    )

    event_id = (
        request.headers.get(
            "x-razorpay-event-id"
        )
    )

    # -----------------------------------------------------
    # 2. VERIFY SIGNATURE
    # -----------------------------------------------------

    if not verify_webhook_signature(
        raw_body,
        received_signature
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid webhook signature."
        )

    # -----------------------------------------------------
    # 3. PARSE JSON
    # -----------------------------------------------------

    try:

        payload = json.loads(
            raw_body.decode("utf-8")
        )

    except json.JSONDecodeError:

        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload."
        )

    event_type = (
        payload.get("event")
        or "unknown"
    )

    # -----------------------------------------------------
    # 4. IDEMPOTENCY
    # -----------------------------------------------------

    if event_already_processed(
        event_id
    ):

        return {

            "received": True,

            "verified": True,

            "duplicate": True,

            "event_id": event_id,

            "event": event_type

        }

    # -----------------------------------------------------
    # 5. EXTRACT PAYMENT
    # -----------------------------------------------------

    payment = (
        extract_payment_information(
            payload
        )
    )

    # -----------------------------------------------------
    # 6. BUILD REVENUE EVENT
    # -----------------------------------------------------

    revenue_event = (
        build_revenue_event(
            event_type,
            payment
        )
    )

    # =====================================================
    # PAYMENT FAILED
    # =====================================================

    agent_decision = None
    recovery_result = None
    recovery_case = None

    if event_type == "payment.failed":

        # -------------------------------------------------
        # RUN RECOVERY AGENT
        # -------------------------------------------------

        agent_decision = (
            recovery_agent.evaluate(
                revenue_event
            )
        )

        # -------------------------------------------------
        # CREATE RECOVERY CASE
        # -------------------------------------------------

        risk = (
            agent_decision[
                "risk_assessment"
            ]
        )

        recovery_case = (
            recovery_tracker.create_case(

                payment_id=
                    revenue_event[
                        "payment_id"
                    ],

                order_id=
                    revenue_event[
                        "order_id"
                    ],

                amount_rupees=
                    revenue_event[
                        "amount_rupees"
                    ],

                risk_level=
                    risk[
                        "risk_level"
                    ],

                proposed_action=
                    agent_decision[
                        "proposed_action"
                    ]

            )
        )

        # -------------------------------------------------
        # RUN EXECUTOR
        # -------------------------------------------------

        recovery_result = (
            recovery_executor.execute(
                agent_decision
            )
        )

        # -------------------------------------------------
        # RECORD RECOVERY ATTEMPT
        # -------------------------------------------------

        if recovery_result.status == (
            "RECOVERY_ATTEMPT_CREATED"
        ):

            recovery_case = (
                recovery_tracker.record_attempt(

                    payment_id=
                        revenue_event[
                            "payment_id"
                        ],

                    attempt_id=
                        recovery_result.attempt_id,

                    action=
                        recovery_result.action

                )
            )

        # -------------------------------------------------
        # HANDLE ESCALATION
        # -------------------------------------------------

        elif (
            agent_decision[
                "safety_decision"
            ]
            == "ESCALATE"
        ):

            recovery_case = (
                recovery_tracker.mark_escalated(

                    revenue_event[
                        "payment_id"
                    ]

                )
            )

        # -------------------------------------------------
        # HANDLE BLOCKED ACTION
        # -------------------------------------------------

        elif recovery_result.status in [
            "BLOCKED",
            "REJECTED"
        ]:

            recovery_case = (
                recovery_tracker.mark_failed(

                    revenue_event[
                        "payment_id"
                    ]

                )
            )

    # =====================================================
    # PAYMENT CAPTURED
    # =====================================================

    elif event_type == "payment.captured":

        payment_id = (
            revenue_event[
                "payment_id"
            ]
        )

        amount_rupees = (
            revenue_event[
                "amount_rupees"
            ]
        )

        # -------------------------------------------------
        # Check whether this payment was associated
        # with an existing recovery case.
        # -------------------------------------------------

        recovery_case = (
            recovery_tracker.mark_recovered(

                payment_id=
                    payment_id,

                recovered_amount=
                    amount_rupees

            )
        )

    # =====================================================
    # STORE EVENT
    # =====================================================

    store_webhook_event(

        event_id,

        event_type,

        {

            "raw_event":
                payload,

            "revenue_event":
                revenue_event,

            "agent_decision":
                agent_decision,

            "recovery_result":
                (
                    recovery_result.to_dict()
                    if recovery_result
                    else None
                ),

            "recovery_case":
                recovery_case

        }

    )

    # -----------------------------------------------------
    # MARK EVENT PROCESSED
    # -----------------------------------------------------

    mark_event_processed(
        event_id
    )

    # =====================================================
    # TERMINAL OUTPUT
    # =====================================================

    print("\n" + "=" * 75)

    print(
        "AI REVENUE RECOVERY — WEBHOOK"
    )

    print("=" * 75)

    print(
        f"Event ID       : {event_id}"
    )

    print(
        f"Event          : {event_type}"
    )

    print(
        f"Payment ID     : "
        f"{revenue_event.get('payment_id')}"
    )

    print(
        f"Order ID       : "
        f"{revenue_event.get('order_id')}"
    )

    print(
        f"Amount         : "
        f"₹{revenue_event.get('amount_rupees', 0):.2f}"
    )

    print(
        f"Payment Status : "
        f"{revenue_event.get('payment_status')}"
    )

    print(
        f"Revenue Risk   : "
        f"₹{revenue_event.get('revenue_at_risk', 0):.2f}"
    )

    if agent_decision:

        risk = (
            agent_decision[
                "risk_assessment"
            ]
        )

        print("\n" + "-" * 75)
        print("RECOVERY AGENT")
        print("-" * 75)

        print(
            f"Failure Category : "
            f"{risk['failure_category']}"
        )

        print(
            f"Risk Score       : "
            f"{risk['risk_score']}"
        )

        print(
            f"Risk Level       : "
            f"{risk['risk_level']}"
        )

        print(
            f"Proposed Action  : "
            f"{agent_decision['proposed_action']}"
        )

        print(
            f"Safety Decision  : "
            f"{agent_decision['safety_decision']}"
        )

        print(
            f"Execution Allowed: "
            f"{agent_decision['execution_allowed']}"
        )

    if recovery_result:

        print("\n" + "-" * 75)
        print("RECOVERY EXECUTOR")
        print("-" * 75)

        print(
            f"Attempt ID       : "
            f"{recovery_result.attempt_id}"
        )

        print(
            f"Status           : "
            f"{recovery_result.status}"
        )

        print(
            f"Simulated        : "
            f"{recovery_result.simulated}"
        )

    if recovery_case:

        print("\n" + "-" * 75)
        print("RECOVERY TRACKER")
        print("-" * 75)

        print(
            f"Case Status      : "
            f"{recovery_case.get('recovery_status')}"
        )

        print(
            f"Revenue at Risk  : "
            f"₹{recovery_case.get('revenue_at_risk', 0):.2f}"
        )

        print(
            f"Recovered        : "
            f"₹{recovery_case.get('recovered_amount', 0):.2f}"
        )

    print("=" * 75 + "\n")

    # =====================================================
    # RESPONSE
    # =====================================================

    return {

        "received": True,

        "verified": True,

        "duplicate": False,

        "event_id":
            event_id,

        "event":
            event_type,

        "revenue_event":
            revenue_event,

        "agent_decision":
            agent_decision,

        "recovery_result":
            (
                recovery_result.to_dict()
                if recovery_result
                else None
            ),

        "recovery_case":
            recovery_case

    }


# =========================================================
# LOCAL RUNNER
# =========================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "razorpay_webhook:app",
        host="127.0.0.1",
        port=8001,
        reload=False
    )