import os
import hmac
import hashlib
import json
import requests

from dotenv import load_dotenv

load_dotenv(override=True)

secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")

body = json.dumps(
    {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_lifecycle_001",
                    "order_id": "order_lifecycle_001",
                    "amount": 75000,
                    "currency": "INR",
                    "status": "captured",
                    "method": "netbanking"
                }
            }
        }
    },
    separators=(",", ":")
).encode()

signature = hmac.new(
    secret.encode(),
    body,
    hashlib.sha256
).hexdigest()

response = requests.post(
    "http://127.0.0.1:8001/webhook/razorpay",
    data=body,
    headers={
        "Content-Type": "application/json",
        "X-Razorpay-Signature": signature,
        "x-razorpay-event-id": "lifecycle-captured-999"
    }
)

print("HTTP:", response.status_code)

print(
    json.dumps(
        response.json(),
        indent=2
    )
)
