import os
import razorpay
from dotenv import load_dotenv


# =========================================
# LOAD RAZORPAY TEST CREDENTIALS
# =========================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

load_dotenv(
    os.path.join(BASE_DIR, ".env"),
    override=True
)

RAZORPAY_KEY_ID = os.getenv(
    "RAZORPAY_KEY_ID"
)

RAZORPAY_KEY_SECRET = os.getenv(
    "RAZORPAY_KEY_SECRET"
)


if not RAZORPAY_KEY_ID:
    raise RuntimeError(
        "RAZORPAY_KEY_ID is missing from .env"
    )

if not RAZORPAY_KEY_SECRET:
    raise RuntimeError(
        "RAZORPAY_KEY_SECRET is missing from .env"
    )


# =========================================
# RAZORPAY CLIENT
# =========================================

client = razorpay.Client(
    auth=(
        RAZORPAY_KEY_ID,
        RAZORPAY_KEY_SECRET
    )
)


# =========================================
# CREATE TEST ORDER
# =========================================

def create_test_order(
    amount_rupees,
    receipt=None
):
    """
    Create a Razorpay Test Mode order.

    Amount is dynamic and supplied by the user.
    """

    amount_rupees = float(
        amount_rupees
    )

    if amount_rupees <= 0:
        raise ValueError(
            "Amount must be greater than ₹0."
        )

    amount_paise = int(
        round(
            amount_rupees * 100
        )
    )

    if receipt is None:

        receipt = (
            "ai-recovery-"
            + str(amount_paise)
        )

    order_data = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt
    }

    order = client.order.create(
        data=order_data
    )

    return order


# =========================================
# FETCH PAYMENT
# =========================================

def fetch_payment(
    payment_id
):
    """
    Retrieve a Razorpay Test Mode payment.
    """

    if not payment_id:
        raise ValueError(
            "Payment ID is required."
        )

    return client.payment.fetch(
        payment_id
    )


# =========================================
# VERIFY PAYMENT SIGNATURE
# =========================================

def verify_payment(
    order_id,
    payment_id,
    signature
):
    """
    Verify Razorpay payment signature.

    This must be performed server-side.
    """

    if not order_id:
        raise ValueError(
            "Order ID is required."
        )

    if not payment_id:
        raise ValueError(
            "Payment ID is required."
        )

    if not signature:
        raise ValueError(
            "Payment signature is required."
        )

    client.utility.verify_payment_signature(
        {
            "razorpay_order_id":
                order_id,

            "razorpay_payment_id":
                payment_id,

            "razorpay_signature":
                signature
        }
    )

    return True


# =========================================
# CONNECTION TEST
# =========================================

if __name__ == "__main__":

    print("=" * 60)
    print(
        "RAZORPAY TEST MODE CHECKOUT MODULE"
    )
    print("=" * 60)

    print(
        "Credentials loaded: YES"
    )

    order = create_test_order(
        amount_rupees=500
    )

    print()
    print(
        "Test order created successfully."
    )

    print(
        f"Order ID: {order['id']}"
    )

    print(
        f"Amount: "
        f"₹{order['amount'] / 100:.2f}"
    )

    print(
        f"Currency: "
        f"{order['currency']}"
    )

    print("=" * 60)