from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from backend.schemas.payments import (
    SimulatePaymentRequest, 
    SimulatePaymentResponse,
    PaymentTransactionResponse,
    LedgerEntryResponse
)
from backend.schemas.risk import RiskAssessment

from backend.database import get_db_session
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_session_direct
from database.models import Account, PaymentTransaction, LedgerEntry, SimulatedPaymentMethod, PaymentStatus
from engine.payment_service import (
    simulate_payment, 
    get_payment_by_idempotency_key,
    get_payment_by_reference,
    verify_ledger_balance,
    get_account_payments
)
from engine.payment_service import (
    InsufficientBalanceError,
    InvalidAmountError,
    AccountNotFoundError,
    AccountInactiveError,
    SameAccountError,
    IdempotencyError,
    RiskRejectionError
)

router = APIRouter()


def get_db():
    db = get_session_direct()
    try:
        yield db
    finally:
        db.close()


@router.post("/payments/simulate", response_model=SimulatePaymentResponse)
async def simulate_payment_endpoint(
    request: SimulatePaymentRequest,
    db: Session = Depends(get_db)
):
    """Simulate a payment with full risk assessment and ledger."""
    try:
        payment = simulate_payment(
            sender_account_id=request.sender_account_id,
            receiver_account_id=request.receiver_account_id,
            amount=request.amount,
            payment_method=request.payment_method,
            idempotency_key=request.idempotency_key,
            session=db
        )
        
        return SimulatePaymentResponse(
            payment_id=payment.id,
            reference_id=payment.reference_id,
            status=payment.status,
            amount=payment.amount / 100.0,
            sender_account_id=payment.sender_account_id,
            receiver_account_id=payment.receiver_account_id,
            payment_method=payment.payment_method,
            trust_score=payment.trust_score,
            fraud_rule_flagged=payment.fraud_rule_flagged,
            fraud_rule_reason=payment.fraud_rule_reason,
            ml_anomaly_score=payment.ml_anomaly_score,
            ml_is_anomaly=payment.ml_is_anomaly,
            risk_policy_decision=payment.risk_policy_decision,
            failure_reason=payment.failure_reason,
            created_at=payment.created_at,
            completed_at=payment.completed_at,
        )
    except InsufficientBalanceError as e:
        raise HTTPException(status_code=400, detail={"error": e.message, "code": e.code, "balance": float(e.balance), "amount": float(e.amount)})
    except InvalidAmountError as e:
        raise HTTPException(status_code=400, detail={"error": e.message, "code": e.code, "amount": float(e.amount)})
    except AccountNotFoundError as e:
        raise HTTPException(status_code=404, detail={"error": e.message, "code": e.code, "account_id": e.account_id})
    except AccountInactiveError as e:
        raise HTTPException(status_code=400, detail={"error": e.message, "code": e.code, "account_id": e.account_id, "status": e.status})
    except SameAccountError as e:
        raise HTTPException(status_code=400, detail={"error": e.message, "code": e.code, "account_id": e.account_id})
    except IdempotencyError as e:
        raise HTTPException(status_code=409, detail={"error": e.message, "code": e.code, "idempotency_key": e.idempotency_key, "existing_transaction_id": e.existing_transaction_id})
    except RiskRejectionError as e:
        raise HTTPException(status_code=403, detail={"error": e.message, "code": e.code, "risk_assessment": e.risk_assessment})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e), "code": "UNEXPECTED_ERROR"})


@router.get("/payments", response_model=List[PaymentTransactionResponse])
async def list_payments(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all payment transactions."""
    query = db.query(PaymentTransaction).order_by(PaymentTransaction.created_at.desc())
    
    if status:
        query = query.filter(PaymentTransaction.status == status)
    
    payments = query.offset(offset).limit(limit).all()
    
    return [
        PaymentTransactionResponse(
            id=p.id,
            reference_id=p.reference_id,
            idempotency_key=p.idempotency_key,
            sender_account_id=p.sender_account_id,
            receiver_account_id=p.receiver_account_id,
            amount=p.amount / 100.0,
            currency=p.currency,
            payment_method=p.payment_method,
            status=p.status,
            trust_score=p.trust_score,
            fraud_rule_flagged=p.fraud_rule_flagged,
            fraud_rule_reason=p.fraud_rule_reason,
            ml_anomaly_score=p.ml_anomaly_score,
            ml_is_anomaly=p.ml_is_anomaly,
            risk_policy_decision=p.risk_policy_decision,
            failure_reason=p.failure_reason,
            created_at=p.created_at,
            completed_at=p.completed_at,
            ledger_entries=[
                LedgerEntryResponse(
                    id=le.id,
                    payment_transaction_id=le.payment_transaction_id,
                    account_id=le.account_id,
                    entry_type=le.entry_type,
                    amount=le.amount / 100.0,
                    balance_after=le.balance_after / 100.0,
                    description=le.description,
                    created_at=le.created_at,
                )
                for le in p.ledger_entries
            ]
        )
        for p in payments
    ]


@router.get("/payments/{payment_id}", response_model=PaymentTransactionResponse)
async def get_payment(payment_id: int, db: Session = Depends(get_db)):
    """Get a single payment by ID."""
    payment = db.query(PaymentTransaction).filter(PaymentTransaction.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return PaymentTransactionResponse(
        id=payment.id,
        reference_id=payment.reference_id,
        idempotency_key=payment.idempotency_key,
        sender_account_id=payment.sender_account_id,
        receiver_account_id=payment.receiver_account_id,
        amount=payment.amount / 100.0,
        currency=payment.currency,
        payment_method=payment.payment_method,
        status=payment.status,
        trust_score=payment.trust_score,
        fraud_rule_flagged=payment.fraud_rule_flagged,
        fraud_rule_reason=payment.fraud_rule_reason,
        ml_anomaly_score=payment.ml_anomaly_score,
        ml_is_anomaly=payment.ml_is_anomaly,
        risk_policy_decision=payment.risk_policy_decision,
        failure_reason=payment.failure_reason,
        created_at=payment.created_at,
        completed_at=payment.completed_at,
        ledger_entries=[
            LedgerEntryResponse(
                id=le.id,
                payment_transaction_id=le.payment_transaction_id,
                account_id=le.account_id,
                entry_type=le.entry_type,
                amount=le.amount / 100.0,
                balance_after=le.balance_after / 100.0,
                description=le.description,
                created_at=le.created_at,
            )
            for le in payment.ledger_entries
        ]
    )


@router.get("/payments/by-idempotency/{idempotency_key}", response_model=PaymentTransactionResponse)
async def get_payment_by_idempotency(idempotency_key: str, db: Session = Depends(get_db)):
    """Get payment by idempotency key."""
    payment = get_payment_by_idempotency_key(idempotency_key, db)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return PaymentTransactionResponse(
        id=payment.id,
        reference_id=payment.reference_id,
        idempotency_key=payment.idempotency_key,
        sender_account_id=payment.sender_account_id,
        receiver_account_id=payment.receiver_account_id,
        amount=payment.amount / 100.0,
        currency=payment.currency,
        payment_method=payment.payment_method,
        status=payment.status,
        trust_score=payment.trust_score,
        fraud_rule_flagged=payment.fraud_rule_flagged,
        fraud_rule_reason=payment.fraud_rule_reason,
        ml_anomaly_score=payment.ml_anomaly_score,
        ml_is_anomaly=payment.ml_is_anomaly,
        risk_policy_decision=payment.risk_policy_decision,
        failure_reason=payment.failure_reason,
        created_at=payment.created_at,
        completed_at=payment.completed_at,
        ledger_entries=[
            LedgerEntryResponse(
                id=le.id,
                payment_transaction_id=le.payment_transaction_id,
                account_id=le.account_id,
                entry_type=le.entry_type,
                amount=le.amount / 100.0,
                balance_after=le.balance_after / 100.0,
                description=le.description,
                created_at=le.created_at,
            )
            for le in payment.ledger_entries
        ]
    )


@router.get("/payments/by-reference/{reference_id}", response_model=PaymentTransactionResponse)
async def get_payment_by_ref(reference_id: str, db: Session = Depends(get_db)):
    """Get payment by reference ID."""
    payment = db.query(PaymentTransaction).filter(PaymentTransaction.reference_id == reference_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return PaymentTransactionResponse(
        id=payment.id,
        reference_id=payment.reference_id,
        idempotency_key=payment.idempotency_key,
        sender_account_id=payment.sender_account_id,
        receiver_account_id=payment.receiver_account_id,
        amount=payment.amount / 100.0,
        currency=payment.currency,
        payment_method=payment.payment_method,
        status=payment.status,
        trust_score=payment.trust_score,
        fraud_rule_flagged=payment.fraud_rule_flagged,
        fraud_rule_reason=payment.fraud_rule_reason,
        ml_anomaly_score=payment.ml_anomaly_score,
        ml_is_anomaly=payment.ml_is_anomaly,
        risk_policy_decision=payment.risk_policy_decision,
        failure_reason=payment.failure_reason,
        created_at=payment.created_at,
        completed_at=payment.completed_at,
        ledger_entries=[
            LedgerEntryResponse(
                id=le.id,
                payment_transaction_id=le.payment_transaction_id,
                account_id=le.account_id,
                entry_type=le.entry_type,
                amount=le.amount / 100.0,
                balance_after=le.balance_after / 100.0,
                description=le.description,
                created_at=le.created_at,
            )
            for le in payment.ledger_entries
        ]
    )


@router.get("/ledger/{payment_id}", response_model=List[LedgerEntryResponse])
async def get_ledger_for_payment(payment_id: int, db: Session = Depends(get_db)):
    """Get ledger entries for a payment."""
    payment = db.query(PaymentTransaction).filter(PaymentTransaction.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return [
        LedgerEntryResponse(
            id=le.id,
            payment_transaction_id=le.payment_transaction_id,
            account_id=le.account_id,
            entry_type=le.entry_type,
            amount=le.amount / 100.0,
            balance_after=le.balance_after / 100.0,
            description=le.description,
            created_at=le.created_at,
        )
        for le in payment.ledger_entries
    ]


@router.get("/ledger/{payment_id}/verify")
async def verify_ledger(payment_id: int, db: Session = Depends(get_db)):
    """Verify ledger balance for a payment."""
    result = verify_ledger_balance(payment_id, db)
    return result


@router.get("/accounts/{account_id}/payments")
async def get_account_payments(account_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """Get payments for an account."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    result = get_account_payments(account_id, db, limit=limit)
    
    return {
        "account_id": account_id,
        "sent": [
            {
                "id": p.id,
                "reference_id": p.reference_id,
                "amount": p.amount / 100.0,
                "status": p.status.value,
                "payment_method": p.payment_method.value,
                "receiver_account_id": p.receiver_account_id,
                "created_at": p.created_at.isoformat(),
            }
            for p in result["sent"][:limit]
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
            }
            for p in result["received"][:limit]
        ]
    }