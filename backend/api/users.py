from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from backend.schemas.users import UserListResponse, UserResponse
from backend.schemas.risk import RiskAssessment
from backend.schemas.payments import PaymentTransactionResponse

from backend.database import get_db_session
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_session_direct
from database.models import User, Account, Transaction, PaymentTransaction
from engine.trust_score import calculate_trust_score, get_all_users, get_user_transactions
from engine.fraud_rules import get_flagged_transactions

router = APIRouter()


def get_db():
    db = get_session_direct()
    try:
        yield db
    finally:
        db.close()


@router.get("/users", response_model=UserListResponse)
async def list_users(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """List all users with pagination."""
    query = db.query(User).order_by(User.id)
    total = query.count()
    users = query.offset(offset).limit(limit).all()
    
    return UserListResponse(
        users=[UserResponse.from_orm(u) for u in users],
        total=total
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get a single user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_orm(user)


@router.get("/users/{user_id}/trust")
async def get_user_trust(user_id: int, db: Session = Depends(get_db)):
    """Get trust score and components for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    trust_data = calculate_trust_score(user_id, db)
    
    return {
        "user_id": user_id,
        "user_name": user.name,
        "trust_score": trust_data["trust_score"],
        "verdict": (
            "Highly Reliable" if trust_data["trust_score"] > 85 else
            "Moderate Risk" if trust_data["trust_score"] > 70 else
            "High Risk"
        ),
        "components": trust_data["components"],
    }


@router.get("/users/{user_id}/transactions")
async def get_user_transactions_api(
    user_id: int, 
    limit: int = 50, 
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get transactions for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    transactions = get_user_transactions(user_id, db, limit=limit + offset)
    transactions = transactions[offset:offset + limit]
    
    # Get flagged transactions for risk display
    flagged = get_flagged_transactions(user_id, db)
    flagged_ids = {f["transaction_id"] for f in flagged}
    
    return {
        "transactions": [
            {
                "id": t.id,
                "amount": t.amount / 100.0,
                "type": t.transaction_type.value,
                "status": t.status.value,
                "payment_method": t.payment_method.value,
                "merchant_category": t.merchant_category,
                "merchant_name": t.merchant_name,
                "location_city": t.location_city,
                "description": t.description,
                "timestamp": t.timestamp.isoformat(),
                "is_anomaly": t.is_anomaly,
                "anomaly_type": t.anomaly_type,
                "risk_flag": "high" if t.id in flagged_ids else "low",
            }
            for t in transactions
        ],
        "total": len(get_user_transactions(user_id, db)),
        "flagged_count": len(flagged),
    }


@router.get("/users/{user_id}/payments")
async def get_user_payments(user_id: int, db: Session = Depends(get_db)):
    """Get payment transactions for a user (sent and received)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get account IDs for this user
    accounts = db.query(Account).filter(Account.user_id == user_id).all()
    account_ids = [a.id for a in accounts]
    
    # Get payments where user is sender or receiver
    sent_payments = db.query(PaymentTransaction).filter(
        PaymentTransaction.sender_account_id.in_(account_ids)
    ).order_by(PaymentTransaction.created_at.desc()).all()
    
    received_payments = db.query(PaymentTransaction).filter(
        PaymentTransaction.receiver_account_id.in_(account_ids)
    ).order_by(PaymentTransaction.created_at.desc()).all()
    
    return {
        "sent": [
            {
                "id": p.id,
                "reference_id": p.reference_id,
                "amount": p.amount / 100.0,
                "status": p.status.value,
                "payment_method": p.payment_method.value,
                "receiver_account_id": p.receiver_account_id,
                "created_at": p.created_at.isoformat(),
                "completed_at": p.completed_at.isoformat() if p.completed_at else None,
                "trust_score": p.trust_score,
                "risk_decision": p.risk_policy_decision,
            }
            for p in sent_payments
        ],
        "received": [
            {
                "id": p.id,
                "reference_id": p.reference_id,
                "amount": p.amount / 100.0,
                "status": p.status.value,
                "payment_method": p.payment_method.value,
                "sender_account_id": p.sender_account_id,
                "created_at": p.created_at.isoformat(),
                "completed_at": p.completed_at.isoformat() if p.completed_at else None,
            }
            for p in received_payments
        ]
    }