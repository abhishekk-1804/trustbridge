from typing import List, Optional
from sqlalchemy.orm import Session
from database.models import Transaction


def calculate_historical_average(user_id: int, session: Session, exclude_txn_id: Optional[int] = None) -> float:
    query = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.status == "SUCCESS"
    )
    
    if exclude_txn_id:
        query = query.filter(Transaction.id != exclude_txn_id)
    
    transactions = query.all()
    
    if not transactions:
        return 0.0
    
    total = sum(t.amount for t in transactions)
    return total / len(transactions)


def calculate_rolling_average(user_id: int, session: Session, window: int = 20, exclude_txn_id: Optional[int] = None) -> float:
    query = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.status == "SUCCESS"
    ).order_by(Transaction.timestamp.desc())
    
    if exclude_txn_id:
        query = query.filter(Transaction.id != exclude_txn_id)
    
    transactions = query.limit(window).all()
    
    if not transactions:
        return 0.0
    
    total = sum(t.amount for t in transactions)
    return total / len(transactions)


def detect_amount_spike(transaction: Transaction, session: Session, multiplier: float = 3.0) -> dict:
    user_id = transaction.user_id
    
    hist_avg = calculate_historical_average(user_id, session, exclude_txn_id=transaction.id)
    rolling_avg = calculate_rolling_average(user_id, session, window=20, exclude_txn_id=transaction.id)
    
    reference_avg = rolling_avg if rolling_avg > 0 else hist_avg
    
    if reference_avg == 0:
        return {
            "flagged": False,
            "risk_level": "LOW",
            "reason": "Insufficient transaction history for comparison",
            "transaction_id": transaction.id,
            "transaction_amount": transaction.amount,
            "reference_average": 0.0,
            "ratio": 0.0,
            "multiplier_used": multiplier
        }
    
    ratio = transaction.amount / reference_avg
    flagged = ratio > multiplier
    
    if flagged:
        risk_level = "HIGH"
        reason = f"Transaction amount (Rs.{transaction.amount:.2f}) is {ratio:.1f}x the user's normal average (Rs.{reference_avg:.2f})"
    else:
        risk_level = "LOW"
        reason = f"Transaction amount (Rs.{transaction.amount:.2f}) is within normal range ({ratio:.1f}x average)"
    
    return {
        "flagged": flagged,
        "risk_level": risk_level,
        "reason": reason,
        "transaction_id": transaction.id,
        "transaction_amount": round(transaction.amount, 2),
        "reference_average": round(reference_avg, 2),
        "ratio": round(ratio, 2),
        "multiplier_used": multiplier
    }


def check_all_transactions(user_id: int, session: Session, multiplier: float = 3.0) -> List[dict]:
    transactions = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT"
    ).order_by(Transaction.timestamp.desc()).all()
    
    results = []
    for txn in transactions:
        result = detect_amount_spike(txn, session, multiplier)
        results.append(result)
    
    return results


def get_flagged_transactions(user_id: int, session: Session, multiplier: float = 3.0) -> List[dict]:
    all_results = check_all_transactions(user_id, session, multiplier)
    return [r for r in all_results if r["flagged"]]