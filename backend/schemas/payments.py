from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SimulatedPaymentMethod(str, Enum):
    UPI_SIMULATED = "upi_simulated"
    BANK_TRANSFER_SIMULATED = "bank_transfer_simulated"
    WALLET_SIMULATED = "wallet_simulated"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    REVERSED = "reversed"


class TransactionType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class SimulatePaymentRequest(BaseModel):
    sender_account_id: int
    receiver_account_id: int
    amount: float
    payment_method: SimulatedPaymentMethod
    idempotency_key: str


class SimulatePaymentResponse(BaseModel):
    payment_id: int
    reference_id: str
    status: PaymentStatus
    amount: float
    sender_account_id: int
    receiver_account_id: int
    payment_method: SimulatedPaymentMethod
    trust_score: Optional[float] = None
    fraud_rule_flagged: Optional[bool] = None
    fraud_rule_reason: Optional[str] = None
    ml_anomaly_score: Optional[float] = None
    ml_is_anomaly: Optional[bool] = None
    risk_policy_decision: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class LedgerEntryResponse(BaseModel):
    id: int
    payment_transaction_id: int
    account_id: int
    entry_type: TransactionType
    amount: float
    balance_after: float
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentTransactionResponse(BaseModel):
    id: int
    reference_id: str
    idempotency_key: str
    sender_account_id: int
    receiver_account_id: int
    amount: float
    currency: str
    payment_method: SimulatedPaymentMethod
    status: PaymentStatus
    trust_score: Optional[float] = None
    fraud_rule_flagged: Optional[bool] = None
    fraud_rule_reason: Optional[str] = None
    ml_anomaly_score: Optional[float] = None
    ml_is_anomaly: Optional[bool] = None
    risk_policy_decision: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    ledger_entries: List[LedgerEntryResponse] = []

    class Config:
        from_attributes = True


class DashboardSummaryResponse(BaseModel):
    total_users: int
    total_transactions: int
    active_risk_events: int
    system_health: str
    trust_distribution: dict
    recent_transactions_count: int