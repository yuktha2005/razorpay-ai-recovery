try:
    import razorpay
except ImportError:
    razorpay = None

from dotenv import load_dotenv


# Load local environment variables
load_dotenv()


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


def create_test_order(
    amount_rupees,
    receipt="ai-recovery-test"
):
    """
    Create a Razorpay Test Mode order.

    amount_rupees:
        Amount in INR.

    Returns:
        Razorpay order response.
    """

    if amount_rupees <= 0:
        raise ValueError(
            "Order amount must be greater than zero."
        )

    amount_paise = int(
        round(amount_rupees * 100)
    )

    order_data = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
    }

    return client.order.create(
        data=order_data
    )


def get_test_payment(payment_id):
    """
    Retrieve a payment from Razorpay Test Mode.
    """

    if not payment_id:
        raise ValueError(
            "payment_id is required."
        )

    return client.payment.fetch(
        payment_id
    )


if __name__ == "__main__":

    print("=" * 60)
    print("RAZORPAY TEST MODE CONNECTION")
    print("=" * 60)

    print(
        f"Key ID loaded: "
        f"{RAZORPAY_KEY_ID[:12]}..."
    )

    order = create_test_order(
        amount_rupees=500,
        receipt="recovery-demo-001"
    )

    print()
    print("Test order created successfully.")
    print(
        f"Order ID: {order['id']}"
    )
    print(
        f"Amount: ₹{order['amount'] / 100:.2f}"
    )
    print(
        f"Currency: {order['currency']}"
    )

    print("=" * 60)
    