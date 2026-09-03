from dataclasses import dataclass, field
from typing import List


@dataclass
class RouteHealth:
    route: str
    payment_method: str
    bank: str
    device_type: str
    transactions: int
    failures: int
    success_rate: float
    baseline_success_rate: float
    degradation_pp: float
    severity: str


@dataclass
class LiveOperationsReport:
    report_id: str
    generated_at: str
    window_minutes: int

    total_transactions: int
    total_failures: int
    overall_success_rate: float
    baseline_success_rate: float

    revenue_at_risk: float
    failed_amount: float

    routes_monitored: int
    healthy_routes: int
    degraded_routes: int
    critical_routes: int

    top_degraded_route: str
    route_health: List[RouteHealth] = field(default_factory=list)