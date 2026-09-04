import os
import sys
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    FastAPI = None
    HTTPException = None
    CORSMiddleware = None

from pydantic import BaseModel
from dotenv import load_dotenv

# -------------------------------------------------
# PATH
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

load_dotenv(BASE_DIR / ".env", override=True)


# -------------------------------------------------
# RAZORPAY
# -------------------------------------------------

try:
    import razorpay
except ImportError:
    razorpay = None


RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")


client = None
if razorpay and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    client = razorpay.Client(
        auth=(
            RAZORPAY_KEY_ID,
            RAZORPAY_KEY_SECRET,
        )
    )


# -------------------------------------------------
# APP
# -------------------------------------------------

if FastAPI is not None:
    app = FastAPI(
        title="AI Revenue Recovery - Razorpay Test API",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
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


# -------------------------------------------------
# REQUEST MODELS
# -------------------------------------------------

class OrderRequest(BaseModel):

    amount_rupees: float


class VerifyRequest(BaseModel):

    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# -------------------------------------------------
# HEALTH
# -------------------------------------------------

@app.get("/health")
def health():

    return {
        "status": "ok",
        "environment": "razorpay_test_mode",
        "service": "ai-revenue-recovery",
    }


# -------------------------------------------------
# CREATE ORDER
# -------------------------------------------------

@app.post("/create-order")
def create_order(request: OrderRequest):

    amount = float(request.amount_rupees)

    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be greater than zero.",
        )

    if amount > 100000:
        raise HTTPException(
            status_code=400,
            detail="Demo amount exceeds the configured limit.",
        )

    amount_paise = int(round(amount * 100))

    order_data = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": f"ai-recovery-{amount_paise}",
    }

    try:

        order = client.order.create(
            data=order_data
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=f"Razorpay order creation failed: {exc}",
        )

    return {
        "success": True,
        "key_id": RAZORPAY_KEY_ID,
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
    }


# -------------------------------------------------
# VERIFY PAYMENT
# -------------------------------------------------

@app.post("/verify-payment")
def verify_payment(request: VerifyRequest):

    try:

        client.utility.verify_payment_signature(
            {
                "razorpay_order_id":
                    request.razorpay_order_id,

                "razorpay_payment_id":
                    request.razorpay_payment_id,

                "razorpay_signature":
                    request.razorpay_signature,
            }
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Payment signature verification failed.",
        )

    try:

        payment = client.payment.fetch(
            request.razorpay_payment_id
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=f"Unable to retrieve payment: {exc}",
        )

    return {
        "success": True,
        "verified": True,
        "payment_id": request.razorpay_payment_id,
        "order_id": request.razorpay_order_id,
        "status": payment.get("status"),
        "amount": payment.get("amount"),
        "currency": payment.get("currency"),
        "method": payment.get("method"),
    }


# -------------------------------------------------
# RUN DIRECTLY
# -------------------------------------------------

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "razorpay_server:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )