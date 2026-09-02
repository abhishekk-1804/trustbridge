from pydantic import BaseModel
from typing import Dict, List, Optional


class DashboardSummaryResponse(BaseModel):
    total_users: int
    total_transactions: int
    active_risk_events: int
    system_health: str
    trust_distribution: Dict[str, int]
    recent_transactions_count: int


class RiskActivityPoint(BaseModel):
    date: str
    risk_events: int
    transactions: int


class LiveRiskEvent(BaseModel):
    id: int
    user_id: int
    user_name: str
    amount: float
    risk_level: str
    source: str
    timestamp: str
    reason: str


class RecentTransaction(BaseModel):
    id: int
    user_id: int
    amount: float
    type: str
    status: str
    merchant: Optional[str] = None
    category: Optional[str] = None
    city: Optional[str] = None
    timestamp: str
    is_anomaly: bool


class RiskActivityResponse(BaseModel):
    data: List[RiskActivityPoint]


class LiveRiskFeedResponse(BaseModel):
    events: List[LiveRiskEvent]


class RecentTransactionsResponse(BaseModel):
    transactions: List[RecentTransaction]