from typing import List
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from database.models import User, Transaction, TransactionStatus


def calculate_payment_reliability(transactions: List[Transaction]) -> float:
    if not transactions:
        return 50.0

    total = len(transactions)
    successful = sum(1 for t in transactions if t.status == TransactionStatus.SUCCESS)
    failed = total - successful

    reliability = (successful / total) * 100 if total > 0 else 50.0
    return reliability


def calculate_transaction_consistency(transactions: List[Transaction]) -> float:
    if len(transactions) < 3:
        return 50.0

    debit_amounts = [t.amount for t in transactions if t.transaction_type.value == "debit"]
    if len(debit_amounts) < 3:
        return 50.0

    mean_amount = sum(debit_amounts) / len(debit_amounts)
    if mean_amount == 0:
        return 50.0

    variance = sum((x - mean_amount) ** 2 for x in debit_amounts) / len(debit_amounts)
    std_dev = variance ** 0.5

    cv = std_dev / mean_amount if mean_amount > 0 else 1.0
    consistency = max(0, 100 - (cv * 50))

    return min(100, consistency)


def calculate_account_behaviour(transactions: List[Transaction], account_created_at: datetime) -> float:
    if not transactions:
        return 50.0

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    days_active = max(1, (now - account_created_at).days)
    txn_count = len(transactions)

    txn_per_day = txn_count / days_active

    if txn_per_day >= 0.5:
        activity_score = 100
    elif txn_per_day >= 0.2:
        activity_score = 80
    elif txn_per_day >= 0.1:
        activity_score = 60
    else:
        activity_score = 40

    recent_cutoff = now - timedelta(days=30)
    recent_txns = [t for t in transactions if t.timestamp >= recent_cutoff]
    recent_ratio = len(recent_txns) / txn_count if txn_count > 0 else 0

    recency_bonus = min(20, recent_ratio * 40)

    return min(100, activity_score + recency_bonus)


def calculate_trust_score(user_id: int, session: Session) -> dict:
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        return {
            "trust_score": 0,
            "payment_reliability": 0,
            "transaction_consistency": 0,
            "account_behaviour": 0,
            "components": {}
        }

    transactions = session.query(Transaction).filter(Transaction.user_id == user_id).all()

    payment_reliability = calculate_payment_reliability(transactions)
    transaction_consistency = calculate_transaction_consistency(transactions)
    account_behaviour = calculate_account_behaviour(transactions, user.account_created_at)

    weights = {
        "payment_reliability": 0.40,
        "transaction_consistency": 0.35,
        "account_behaviour": 0.25
    }

    trust_score = (
        payment_reliability * weights["payment_reliability"] +
        transaction_consistency * weights["transaction_consistency"] +
        account_behaviour * weights["account_behaviour"]
    )

    trust_score = max(0, min(100, trust_score))

    return {
        "trust_score": round(trust_score, 1),
        "payment_reliability": round(payment_reliability, 1),
        "transaction_consistency": round(transaction_consistency, 1),
        "account_behaviour": round(account_behaviour, 1),
        "components": {
            "payment_reliability": {
                "score": round(payment_reliability, 1),
                "weight": weights["payment_reliability"],
                "contribution": round(payment_reliability * weights["payment_reliability"], 1)
            },
            "transaction_consistency": {
                "score": round(transaction_consistency, 1),
                "weight": weights["transaction_consistency"],
                "contribution": round(transaction_consistency * weights["transaction_consistency"], 1)
            },
            "account_behaviour": {
                "score": round(account_behaviour, 1),
                "weight": weights["account_behaviour"],
                "contribution": round(account_behaviour * weights["account_behaviour"], 1)
            }
        }
    }


def get_user_transactions(user_id: int, session: Session, limit: int = 50) -> List[Transaction]:
    return session.query(Transaction).filter(
        Transaction.user_id == user_id
    ).order_by(Transaction.timestamp.desc()).limit(limit).all()


def get_all_users(session: Session) -> List[User]:
    return session.query(User).all()