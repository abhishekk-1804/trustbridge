from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TransactionType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class TransactionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


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


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class RiskDecision(str, Enum):
    PROCEED = "proceed"
    FLAG = "flag"
    REJECT = "reject"


class FraudRuleResult(BaseModel):
    flagged: bool
    risk_level: str
    reason: str
    transaction_id: Optional[int] = None
    transaction_amount: Optional[float] = Field(
        None, description="Transaction amount in minor units (paise)."
    )
    reference_average: Optional[float] = Field(
        None, description="Baseline reference average in minor units (paise)."
    )
    ratio: Optional[float] = None
    multiplier_used: Optional[float] = None


class MLAnomalyResult(BaseModel):
    anomaly_score: float
    is_anomaly: bool
    risk_level: str


class RiskAssessment(BaseModel):
    trust_score: float
    trust_components: Dict[str, Any] = {}
    fraud_rule: Optional[FraudRuleResult] = None
    ml_anomaly: Optional[MLAnomalyResult] = None
    risk_level: RiskLevel
    risk_drivers: List[str] = []
    risk_decision: RiskDecision


class TransactionResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    transaction_type: TransactionType
    status: TransactionStatus
    payment_method: str
    merchant_category: Optional[str] = None
    merchant_name: Optional[str] = None
    location_city: Optional[str] = None
    description: Optional[str] = None
    timestamp: datetime
    is_anomaly: bool
    anomaly_type: Optional[str] = None

    class Config:
        from_attributes = True


class RiskEventResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    amount: float
    transaction_type: TransactionType
    risk_level: RiskLevel
    rule_result: Optional[FraudRuleResult] = None
    ml_result: Optional[MLAnomalyResult] = None
    final_decision: str
    reason: str
    timestamp: datetime
    is_ground_truth_anomaly: bool
    ground_truth_type: Optional[str] = None

    class Config:
        from_attributes = True


class AssessRiskRequest(BaseModel):
    user_id: int
    amount: float
    payment_method: SimulatedPaymentMethod


class AssessRiskResponse(BaseModel):
    risk_assessment: RiskAssessment
    user: dict


class CaseStatus(str, Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    DISMISSED = "dismissed"


class CaseDecision(str, Enum):
    TRUE_POSITIVE = "true_positive"
    FALSE_POSITIVE = "false_positive"
    INCONCLUSIVE = "inconclusive"
    ESCALATED = "escalated"


class RiskEventType(str, Enum):
    TRANSACTION = "transaction"
    PAYMENT = "payment"


class InvestigationCaseCreate(BaseModel):
    risk_event_id: int
    risk_event_type: RiskEventType


class InvestigationCaseUpdate(BaseModel):
    status: Optional[CaseStatus] = None
    notes: Optional[str] = None
    decision: Optional[CaseDecision] = None


class InvestigationCaseResponse(BaseModel):
    id: int
    risk_event_id: int
    risk_event_type: RiskEventType
    status: CaseStatus
    analyst_id: Optional[int] = None
    notes: Optional[str] = None
    decision: Optional[CaseDecision] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    case_id: int
    user_id: Optional[int] = None
    action: str
    old_state: Optional[str] = None
    new_state: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True