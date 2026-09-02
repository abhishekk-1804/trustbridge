from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from backend.schemas.risk import RiskEventResponse, FraudRuleResult, MLAnomalyResult, RiskLevel

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import get_db_session_direct
from database.models import User, Account, Transaction, PaymentTransaction, AccountStatus
from engine.fraud_rules import detect_amount_spike, get_flagged_transactions
from engine.ml_fraud import score_all_transactions, evaluate_model, compare_rule_vs_ml, explain_anomaly
from engine.payment_service import assess_payment_risk

router = APIRouter()


def get_db():
    db = get_db_session_direct()
    try:
        yield db
    finally:
        db.close()


class RiskAssessRequest(BaseModel):
    user_id: int = Field(..., ge=1, description="User ID for risk assessment")
    amount: float = Field(..., gt=0, le=10_000_000, description="Payment amount in INR")
    payment_method: str = Field(default="UPI_SIMULATED", pattern="^(upi_simulated|bank_transfer_simulated|wallet_simulated)$")


@router.post("/risk/assess", response_model=dict)
async def assess_risk(
    request: RiskAssessRequest,
    db: Session = Depends(get_db)
):
    """
    Assess risk for a hypothetical payment.
    
    Body:
    {
        "user_id": 42,
        "amount": 18500,
        "payment_method": "UPI_SIMULATED"
    }
    """
    # Validate user exists
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get sender account (first active account)
    sender_account = db.query(Account).filter(
        Account.user_id == request.user_id,
        Account.status == AccountStatus.ACTIVE
    ).first()
    
    if not sender_account:
        raise HTTPException(status_code=404, detail="No active account found for user")
    
    # Need a receiver account for risk assessment
    # Use another user's account if available
    receiver_account = db.query(Account).filter(
        Account.id != sender_account.id,
        Account.status == AccountStatus.ACTIVE
    ).first()
    
    if not receiver_account:
        raise HTTPException(status_code=400, detail="No receiver account available for assessment")
    
    risk_assessment = assess_payment_risk(
        sender_account_id=sender_account.id,
        receiver_account_id=receiver_account.id,
        amount=request.amount,
        payment_method=request.payment_method,
        session=db
    )
    
    return {
        "risk_assessment": risk_assessment,
        "user": {
            "id": user.id,
            "name": user.name,
            "role": user.role.value,
        },
        "assessed_amount": request.amount,
        "assessed_method": request.payment_method,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/risk/events")
async def list_risk_events(
    limit: int = 50,
    risk_level: Optional[str] = Query(None, pattern="^(low|moderate|high)$"),
    source: Optional[str] = Query(None, pattern="^(rule|ml|both)$"),
    db: Session = Depends(get_db)
):
    """List risk events with filtering."""
    events = []
    
    # Get ML anomalies
    ml_results = score_all_transactions()
    for r in ml_results:
        if r["is_anomaly"]:
            user = db.query(User).filter(User.id == r["user_id"]).first()
            if user:
                events.append(RiskEventResponse(
                    id=r["transaction_id"],
                    user_id=r["user_id"],
                    user_name=user.name,
                    amount=r["amount"] / 100.0,
                    transaction_type="debit",
                    risk_level=RiskLevel(r["risk_level"].lower()),
                    rule_result=None,
                    ml_result=MLAnomalyResult(
                        anomaly_score=r["anomaly_score"],
                        is_anomaly=r["is_anomaly"],
                        risk_level=r["risk_level"]
                    ),
                    final_decision="anomaly detected",
                    reason=f"ML anomaly score: {r['anomaly_score']:.4f}",
                    timestamp=r["timestamp"],
                    is_ground_truth_anomaly=r["ground_truth_anomaly"],
                    ground_truth_type=r["ground_truth_type"]
                ))
    
    # Get rule-flagged transactions
    for user in db.query(User).all():
        flagged = get_flagged_transactions(user.id, db)
        for f in flagged:
            events.append(RiskEventResponse(
                id=f["transaction_id"],
                user_id=user.id,
                user_name=user.name,
                amount=f["transaction_amount"] / 100.0,
                transaction_type="debit",
                risk_level=RiskLevel.HIGH,
                rule_result=FraudRuleResult(**f),
                ml_result=None,
                final_decision="flagged",
                reason=f["reason"],
                timestamp=datetime.now(timezone.utc),
                is_ground_truth_anomaly=False,
                ground_truth_type=None
            ))
    
    # Apply filters
    if risk_level:
        events = [e for e in events if e.risk_level == RiskLevel(risk_level)]
    
    if source:
        # This is a simplified filter - in reality we'd track source better
        pass
    
    # Sort by timestamp (normalize to naive UTC for comparison)
    def _to_naive_utc(ts):
        if ts is None:
            return datetime.min.replace(tzinfo=None)
        if hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
            return ts.astimezone(timezone.utc).replace(tzinfo=None)
        return ts
    
    events.sort(key=lambda x: _to_naive_utc(x.timestamp), reverse=True)
    
    return {"events": events[:limit], "total": len(events)}


@router.get("/risk/events/{event_id}")
async def get_risk_event(event_id: int, db: Session = Depends(get_db)):
    """Get detailed risk event by ID."""
    # Try to find as transaction
    txn = db.query(Transaction).filter(Transaction.id == event_id).first()
    if not txn:
        # Try payment transaction
        payment = db.query(PaymentTransaction).filter(PaymentTransaction.id == event_id).first()
        if payment:
            return {
                "id": payment.id,
                "type": "payment",
                "reference_id": payment.reference_id,
                "amount": payment.amount / 100.0,
                "status": payment.status.value,
                "risk_decision": payment.risk_policy_decision,
                "trust_score": payment.trust_score,
                "fraud_rule_flagged": payment.fraud_rule_flagged,
                "ml_anomaly_score": payment.ml_anomaly_score,
                "created_at": payment.created_at.isoformat(),
            }
        raise HTTPException(status_code=404, detail="Risk event not found")
    
    user = db.query(User).filter(User.id == txn.user_id).first()
    
    # Get fraud rule result for this transaction
    fraud_result = detect_amount_spike(txn, db) if txn.transaction_type.value == "debit" else None
    
    # Get ML result
    ml_results = score_all_transactions()
    ml_result = next((r for r in ml_results if r["transaction_id"] == event_id), None)
    
    return {
        "id": txn.id,
        "user_id": txn.user_id,
        "user_name": user.name if user else "Unknown",
        "amount": txn.amount / 100.0,
        "type": txn.transaction_type.value,
        "status": txn.status.value,
        "merchant": txn.merchant_name,
        "category": txn.merchant_category,
        "city": txn.location_city,
        "timestamp": txn.timestamp.isoformat(),
        "is_anomaly": txn.is_anomaly,
        "anomaly_type": txn.anomaly_type,
        "fraud_rule": fraud_result,
        "ml_result": ml_result,
        "ground_truth": txn.is_anomaly,
    }


@router.get("/risk/evaluation")
async def get_model_evaluation(db: Session = Depends(get_db)):
    """Get ML model evaluation metrics."""
    eval_result = evaluate_model()
    
    # Convert numpy ints to regular ints for JSON serialization
    def convert(obj):
        if hasattr(obj, 'item'):
            return obj.item()
        elif isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert(v) for v in obj]
        return obj
    
    eval_result = convert(eval_result)
    
    return {
        "model": "Isolation Forest",
        "version": "1.0",
        "evaluation": eval_result,
        "note": "Experimental benchmark on injected anomalies. Not production performance."
    }


@router.get("/risk/comparison")
async def get_rule_vs_ml_comparison(db: Session = Depends(get_db)):
    """Get comparison between rule-based and ML detection."""
    comparison = compare_rule_vs_ml()
    return {
        "comparison": comparison,
        "description": "Rule vs ML detection comparison on current dataset"
    }


@router.get("/risk/explain/{transaction_id}")
async def explain_risk_event(transaction_id: int, db: Session = Depends(get_db)):
    """Get explainable risk drivers for a transaction."""
    explanation = explain_anomaly(transaction_id)
    return explanation