"""
TrustBridge Payment Service

Simulated payment processing with:
- Idempotency
- Double-entry ledger
- Atomic transactions
- Risk engine integration
- Balance validation
"""
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database.models import (
    User, Account, PaymentTransaction, LedgerEntry,
    AccountStatus, PaymentStatus, SimulatedPaymentMethod, TransactionType
)
from database.db import get_session_direct
from engine.trust_score import calculate_trust_score
from engine.fraud_rules import detect_amount_spike
from engine.ml_fraud import predict_anomaly, explain_anomaly
from engine.ml_features import extract_transaction_features, build_categorical_mappings
import uuid


class PaymentError(Exception):
    """Base exception for payment errors."""
    def __init__(self, message: str, code: str = "PAYMENT_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class InsufficientBalanceError(PaymentError):
    def __init__(self, balance: Decimal, amount: Decimal):
        super().__init__(f"Insufficient balance: {balance} < {amount}", "INSUFFICIENT_BALANCE")
        self.balance = balance
        self.amount = amount


class InvalidAmountError(PaymentError):
    def __init__(self, amount: Decimal):
        super().__init__(f"Invalid amount: {amount}", "INVALID_AMOUNT")
        self.amount = amount


class AccountNotFoundError(PaymentError):
    def __init__(self, account_id: int):
        super().__init__(f"Account not found: {account_id}", "ACCOUNT_NOT_FOUND")
        self.account_id = account_id


class AccountInactiveError(PaymentError):
    def __init__(self, account_id: int, status: str):
        super().__init__(f"Account {account_id} is not active: {status}", "ACCOUNT_INACTIVE")
        self.account_id = account_id
        self.status = status


class SameAccountError(PaymentError):
    def __init__(self, account_id: int):
        super().__init__(f"Sender and receiver cannot be the same account: {account_id}", "SAME_ACCOUNT")
        self.account_id = account_id


class IdempotencyError(PaymentError):
    def __init__(self, idempotency_key: str, existing_transaction_id: int):
        super().__init__(
            f"Duplicate idempotency key: {idempotency_key}. Transaction {existing_transaction_id} already exists.",
            "IDEMPOTENCY_VIOLATION"
        )
        self.idempotency_key = idempotency_key
        self.existing_transaction_id = existing_transaction_id


class RiskRejectionError(PaymentError):
    def __init__(self, reason: str, risk_assessment: Dict[str, Any]):
        super().__init__(f"Payment rejected by risk policy: {reason}", "RISK_REJECTION")
        self.risk_assessment = risk_assessment


def generate_reference_id() -> str:
    """Generate a human-readable payment reference."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique = uuid.uuid4().hex[:8].upper()
    return f"TB{timestamp}{unique}"


def to_paise(amount: Decimal) -> int:
    """Convert Decimal rupees to integer paise."""
    return int(amount * Decimal(100))


def from_paise(paise: int) -> Decimal:
    """Convert integer paise to Decimal rupees."""
    return Decimal(paise) / Decimal(100)


def assess_payment_risk(
    sender_account_id: int,
    receiver_account_id: int,
    amount: Decimal,
    payment_method: SimulatedPaymentMethod,
    session: Session
) -> Dict[str, Any]:
    """
    Assess payment risk using existing TrustBridge risk intelligence.
    
    Returns structured risk assessment for the payment.
    """
    # Get sender's trust score
    sender_account = session.query(Account).filter(Account.id == sender_account_id).first()
    if not sender_account:
        return {"error": "Sender account not found"}
    
    user_id = sender_account.user_id
    trust_score_data = calculate_trust_score(user_id, session)
    trust_score = trust_score_data.get("trust_score", 0)
    
    # Create a temporary transaction-like object for fraud rule check
    # We'll use the sender's latest transaction pattern
    from database.models import Transaction
    latest_txn = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT"
    ).order_by(Transaction.timestamp.desc()).first()
    
    fraud_rule_result = None
    if latest_txn:
        # Create a mock transaction for the payment amount to check rules
        class MockTxn:
            def __init__(self, user_id, amount, txn_id):
                self.user_id = user_id
                self.amount = amount
                self.id = txn_id
                self.transaction_type = TransactionType.DEBIT
        
        mock_txn = MockTxn(user_id, to_paise(amount), 0)
        fraud_rule_result = detect_amount_spike(mock_txn, session)
    
    # ML anomaly prediction
    # Create features for the payment
    categorical_mappings = build_categorical_mappings(session)
    payment_features = {
        "amount": float(amount),
        "transaction_type": "debit",
        "status": "success",
        "payment_method": payment_method.value,
        "merchant_category": "Payment Transfer",
        "merchant_name": "Account Transfer",
        "location_city": "Unknown",
        "timestamp": datetime.utcnow(),
        "user_id": user_id,
        "is_anomaly": False,
        "anomaly_type": None
    }
    # We need to add historical features - simplified for demo
    # In production, we'd compute proper historical features
    
    ml_result = None
    try:
        ml_result = predict_anomaly(payment_features)
    except Exception:
        ml_result = {"anomaly_score": 0.0, "is_anomaly": False, "risk_level": "LOW"}
    
    # Risk policy decision
    risk_level = "LOW"
    risk_drivers = []
    
    if fraud_rule_result and isinstance(fraud_rule_result, dict) and fraud_rule_result.get("flagged"):
        risk_level = "HIGH"
        risk_drivers.append(f"Amount spike rule: {fraud_rule_result.get('reason')}")
    
    if ml_result and isinstance(ml_result, dict) and ml_result.get("is_anomaly"):
        if risk_level != "HIGH":
            risk_level = "MODERATE"
        risk_drivers.append(f"ML anomaly detected (score: {ml_result.get('anomaly_score', 0):.4f})")
    
    if trust_score < 50:
        risk_level = "HIGH"
        risk_drivers.append(f"Low trust score: {trust_score:.1f}")
    elif trust_score < 70:
        if risk_level == "LOW":
            risk_level = "MODERATE"
        risk_drivers.append(f"Moderate trust score: {trust_score:.1f}")
    
    # Simple deterministic risk policy
    if risk_level == "HIGH":
        risk_decision = "reject"
    elif risk_level == "MODERATE":
        risk_decision = "flag"
    else:
        risk_decision = "proceed"
    
    return {
        "trust_score": trust_score,
        "trust_components": trust_score_data.get("components", {}),
        "fraud_rule": fraud_rule_result,
        "ml_anomaly": ml_result,
        "risk_level": risk_level,
        "risk_drivers": risk_drivers,
        "risk_decision": risk_decision
    }


def create_ledger_entries(
    payment: PaymentTransaction,
    sender_balance_before: int,
    receiver_balance_before: int,
    session: Session
) -> Tuple[LedgerEntry, LedgerEntry]:
    """
    Create double-entry ledger entries for a completed payment.
    
    Returns (debit_entry, credit_entry)
    """
    amount = payment.amount
    
    # Sender: DEBIT
    sender_balance_after = sender_balance_before - amount
    debit_entry = LedgerEntry(
        payment_transaction_id=payment.id,
        account_id=payment.sender_account_id,
        entry_type=TransactionType.DEBIT,
        amount=amount,
        balance_after=sender_balance_after,
        description=f"Payment to account {payment.receiver_account_id} (ref: {payment.reference_id})"
    )
    
    # Receiver: CREDIT
    receiver_balance_after = receiver_balance_before + amount
    credit_entry = LedgerEntry(
        payment_transaction_id=payment.id,
        account_id=payment.receiver_account_id,
        entry_type=TransactionType.CREDIT,
        amount=amount,
        balance_after=receiver_balance_after,
        description=f"Payment from account {payment.sender_account_id} (ref: {payment.reference_id})"
    )
    
    session.add_all([debit_entry, credit_entry])
    
    return debit_entry, credit_entry


def verify_ledger_balance(payment_transaction_id: int, session: Session) -> Dict[str, Any]:
    """
    Verify that ledger entries for a payment are balanced.
    
    Returns verification result with details.
    """
    entries = session.query(LedgerEntry).filter(
        LedgerEntry.payment_transaction_id == payment_transaction_id
    ).all()
    
    total_debits = sum(e.amount for e in entries if e.entry_type == TransactionType.DEBIT)
    total_credits = sum(e.amount for e in entries if e.entry_type == TransactionType.CREDIT)
    
    is_balanced = total_debits == total_credits
    
    return {
        "payment_transaction_id": payment_transaction_id,
        "total_debits": total_debits,
        "total_credits": total_credits,
        "is_balanced": is_balanced,
        "entry_count": len(entries),
        "entries": [
            {
                "account_id": e.account_id,
                "entry_type": e.entry_type.value,
                "amount": e.amount,
                "balance_after": e.balance_after
            }
            for e in entries
        ]
    }


def simulate_payment(
    sender_account_id: int,
    receiver_account_id: int,
    amount: Decimal,
    payment_method: SimulatedPaymentMethod,
    idempotency_key: str,
    session: Optional[Session] = None
) -> PaymentTransaction:
    """
    Execute a simulated payment with full risk assessment, idempotency, and double-entry ledger.
    
    Args:
        sender_account_id: Source account ID
        receiver_account_id: Destination account ID
        amount: Payment amount in major units (rupees)
        payment_method: Simulated payment method
        idempotency_key: Unique key for idempotency
        session: Optional existing session (will create new if not provided)
    
    Returns:
        PaymentTransaction: The completed payment transaction
    
    Raises:
        PaymentError: For various payment failures
    """
    if amount <= 0:
        raise InvalidAmountError(amount)
    
    if sender_account_id == receiver_account_id:
        raise SameAccountError(sender_account_id)
    
    amount_paise = to_paise(amount)
    reference_id = generate_reference_id()
    
    # Handle session management
    close_session = False
    if session is None:
        session = get_session_direct()
        close_session = True
    
    try:
        # Check idempotency first
        existing = session.query(PaymentTransaction).filter(
            PaymentTransaction.idempotency_key == idempotency_key
        ).first()
        if existing:
            raise IdempotencyError(idempotency_key, existing.id)
        
        # Validate accounts
        sender_account = session.query(Account).filter(Account.id == sender_account_id).first()
        if not sender_account:
            raise AccountNotFoundError(sender_account_id)
        
        receiver_account = session.query(Account).filter(Account.id == receiver_account_id).first()
        if not receiver_account:
            raise AccountNotFoundError(receiver_account_id)
        
        # Check account status
        if sender_account.status != AccountStatus.ACTIVE:
            raise AccountInactiveError(sender_account_id, sender_account.status.value)
        if receiver_account.status != AccountStatus.ACTIVE:
            raise AccountInactiveError(receiver_account_id, receiver_account.status.value)
        
        # Check sufficient balance
        sender_balance = sender_account.balance
        if sender_balance < amount_paise:
            raise InsufficientBalanceError(from_paise(sender_balance), amount)
        
        # Risk assessment
        risk_assessment = assess_payment_risk(
            sender_account_id, receiver_account_id, amount, payment_method, session
        )
        
        # Apply risk policy
        risk_decision = risk_assessment.get("risk_decision", "proceed")
        if risk_decision == "reject":
            fraud_rule = risk_assessment.get("fraud_rule")
            ml_anomaly = risk_assessment.get("ml_anomaly")
            risk_drivers = risk_assessment.get("risk_drivers", ["High risk"])
            
            payment = PaymentTransaction(
                reference_id=reference_id,
                idempotency_key=idempotency_key,
                sender_account_id=sender_account_id,
                receiver_account_id=receiver_account_id,
                amount=amount_paise,
                currency="INR",
                payment_method=payment_method,
                status=PaymentStatus.REJECTED,
                trust_score=risk_assessment.get("trust_score"),
                fraud_rule_flagged=fraud_rule.get("flagged", False) if isinstance(fraud_rule, dict) else False,
                fraud_rule_reason=fraud_rule.get("reason") if isinstance(fraud_rule, dict) else None,
                ml_anomaly_score=ml_anomaly.get("anomaly_score") if isinstance(ml_anomaly, dict) else None,
                ml_is_anomaly=ml_anomaly.get("is_anomaly", False) if isinstance(ml_anomaly, dict) else False,
                risk_policy_decision=risk_decision,
                failure_reason=f"Risk policy: {risk_decision} - {'; '.join(risk_drivers)}",
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            session.add(payment)
            session.commit()
            raise RiskRejectionError(risk_assessment.get("risk_drivers", ["High risk"])[0], risk_assessment)
        
        # Execute payment atomically
        # Capture balances before
        sender_balance_before = sender_account.balance
        receiver_balance_before = receiver_account.balance
        
        # Update balances
        sender_account.balance = sender_balance_before - amount_paise
        receiver_account.balance = receiver_balance_before + amount_paise
        
        # Create payment transaction
        fraud_rule = risk_assessment.get("fraud_rule")
        ml_anomaly = risk_assessment.get("ml_anomaly")
        
        payment = PaymentTransaction(
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            sender_account_id=sender_account_id,
            receiver_account_id=receiver_account_id,
            amount=amount_paise,
            currency="INR",
            payment_method=payment_method,
            status=PaymentStatus.COMPLETED,
            trust_score=risk_assessment.get("trust_score"),
            fraud_rule_flagged=fraud_rule.get("flagged", False) if isinstance(fraud_rule, dict) else False,
            fraud_rule_reason=fraud_rule.get("reason") if isinstance(fraud_rule, dict) else None,
            ml_anomaly_score=ml_anomaly.get("anomaly_score") if isinstance(ml_anomaly, dict) else None,
            ml_is_anomaly=ml_anomaly.get("is_anomaly", False) if isinstance(ml_anomaly, dict) else False,
            risk_policy_decision=risk_decision,
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        session.add(payment)
        session.flush()  # Get payment.id
        
        # Create double-entry ledger entries
        create_ledger_entries(payment, sender_balance_before, receiver_balance_before, session)
        
        session.commit()
        
        return payment
        
    except PaymentError:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        # Check if it's an idempotency key violation
        if "idempotency_key" in str(e).lower() or "unique constraint" in str(e).lower():
            existing = session.query(PaymentTransaction).filter(
                PaymentTransaction.idempotency_key == idempotency_key
            ).first()
            if existing:
                raise IdempotencyError(idempotency_key, existing.id)
        raise PaymentError(f"Database integrity error: {str(e)}", "INTEGRITY_ERROR")
    except Exception as e:
        session.rollback()
        raise PaymentError(f"Unexpected error: {str(e)}", "UNEXPECTED_ERROR")
    finally:
        if close_session:
            session.close()


def get_payment_by_idempotency_key(idempotency_key: str, session: Session) -> Optional[PaymentTransaction]:
    """Retrieve a payment by its idempotency key."""
    return session.query(PaymentTransaction).filter(
        PaymentTransaction.idempotency_key == idempotency_key
    ).first()


def get_payment_by_reference(reference_id: str, session: Session) -> Optional[PaymentTransaction]:
    """Retrieve a payment by its reference ID."""
    return session.query(PaymentTransaction).filter(
        PaymentTransaction.reference_id == reference_id
    ).first()


def get_account_payments(account_id: int, session: Session, limit: int = 50) -> list:
    """Get payments for an account (sent or received)."""
    sent = session.query(PaymentTransaction).filter(
        PaymentTransaction.sender_account_id == account_id
    ).order_by(PaymentTransaction.created_at.desc()).limit(limit).all()
    
    received = session.query(PaymentTransaction).filter(
        PaymentTransaction.receiver_account_id == account_id
    ).order_by(PaymentTransaction.created_at.desc()).limit(limit).all()
    
    return {"sent": sent, "received": received}