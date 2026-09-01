from dataclasses import dataclass
from typing import Optional


@dataclass
class PaymentFeatures:
    """
    Features used by the payment-loss risk engine.

    These features are intentionally independent from
    the ML model so that the model can be replaced later.
    """

    amount_rupees: float
    historical_average_rupees: float = 0.0
    previous_failures: int = 0
    previous_disputes: int = 0
    transactions_last_5_minutes: int = 1
    transactions_last_1_hour: int = 1
    new_device: bool = False
    new_location: bool = False
    delivery_confirmed: bool = True
    customer_age_days: int = 365
    merchant_dispute_rate: float = 0.0

    @property
    def amount_deviation_ratio(self) -> float:
        if self.historical_average_rupees <= 0:
            return 1.0

        return self.amount_rupees / self.historical_average_rupees

    @property
    def velocity_5m(self) -> int:
        return max(0, self.transactions_last_5_minutes)

    @property
    def velocity_1h(self) -> int:
        return max(0, self.transactions_last_1_hour)