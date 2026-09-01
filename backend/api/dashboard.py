from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from datetime import datetime, timedelta

from backend.database import get_db_session
from backend.schemas.dashboard import DashboardSummaryResponse
from backend.schemas.users import UserListResponse, UserResponse
from backend.schemas.risk import RiskEventResponse
from backend.schemas.payments import DashboardSummaryResponse as PaymentsDashboardSummary

# Import existing engines - use backend.database for correct DB path
from backend.database import get_db_session_direct
from database.models import User, Account, Transaction, PaymentTransaction, LedgerEntry
from engine.trust_score import calculate_trust_score, get_all_users
from engine.fraud_rules import get_flagged_transactions, detect_amount_spike
from engine.ml_fraud import score_all_transactions, evaluate_model, compare_rule_vs_ml
from engine.payment_service import simulate_payment, verify_ledger_balance

router = APIRouter()


def get_db():
    db = get_db_session_direct()
    try:
        yield db
    finally:
        db.close()


# Cache ML results to avoid recomputing
_ml_cache = {"results": None, "timestamp": None}
ML_CACHE_TTL = 30  # seconds


def get_cached_ml_results():
    """Get cached ML results or compute new ones."""
    import time
    now = time.time()
    if _ml_cache["results"] is not None and (now - _ml_cache["timestamp"]) < ML_CACHE_TTL:
        return _ml_cache["results"]
    
    results = score_all_transactions()
    _ml_cache["results"] = results
    _ml_cache["timestamp"] = now
    return results


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(db: Session = Depends(get_db)):
    """Get overall dashboard summary metrics."""
    total_users = db.query(User).count()
    total_transactions = db.query(Transaction).count()
    
    # Get risk events (flagged transactions from rules + ML)
    ml_results = get_cached_ml_results()
    active_risk_events = sum(1 for r in ml_results if r["is_anomaly"])
    
    # Add rule-flagged transactions
    rule_flagged = 0
    users_list = db.query(User).all()
    for user in users_list:
        flagged = get_flagged_transactions(user.id, db)
        rule_flagged += len(flagged)
    
    # Avoid double counting - just use ML for now
    active_risk_events = max(active_risk_events, rule_flagged)
    
    # Trust distribution
    trust_scores = []
    for user in db.query(User).all():
        ts = calculate_trust_score(user.id, db)
        trust_scores.append(ts["trust_score"])
    
    trust_dist = {"high": 0, "medium": 0, "low": 0}
    for score in trust_scores:
        if score >= 80:
            trust_dist["high"] += 1
        elif score >= 60:
            trust_dist["medium"] += 1
        else:
            trust_dist["low"] += 1
    
    # Recent transactions count (last 24 hours) - use a wider window for demo data
    recent_cutoff = datetime.utcnow() - timedelta(days=365)
    recent_transactions = db.query(Transaction).filter(
        Transaction.timestamp >= recent_cutoff
    ).count()
    
    return DashboardSummaryResponse(
        total_users=total_users,
        total_transactions=total_transactions,
        active_risk_events=active_risk_events,
        system_health="healthy",
        trust_distribution=trust_dist,
        recent_transactions_count=recent_transactions,
    )


@router.get("/dashboard/risk-activity")
async def get_risk_activity(db: Session = Depends(get_db)):
    """Get risk activity data for charts (last 7 days)."""
    ml_results = get_cached_ml_results()
    
    # Group ML anomalies by date
    from collections import defaultdict
    risk_by_date = defaultdict(int)
    txn_by_date = defaultdict(int)
    
    for r in ml_results:
        if r["is_anomaly"]:
            date_str = r["timestamp"].date().isoformat()
            risk_by_date[date_str] += 1
    
    # Get transaction counts by date
    transactions = db.query(Transaction).all()
    for t in transactions:
        date_str = t.timestamp.date().isoformat()
        txn_by_date[date_str] += 1
    
    days = 7
    data = []
    for i in range(days):
        date = datetime.utcnow().date() - timedelta(days=i)
        date_str = date.isoformat()
        data.append({
            "date": date_str,
            "risk_events": risk_by_date.get(date_str, 0),
            "transactions": txn_by_date.get(date_str, 0)
        })
    
    return {"data": list(reversed(data))}


@router.get("/dashboard/live-risk-feed")
async def get_live_risk_feed(limit: int = 10, db: Session = Depends(get_db)):
    """Get live feed of recent risk events."""
    events = []
    
    # Get ML anomalies
    ml_results = get_cached_ml_results()
    for r in ml_results:
        if r["is_anomaly"]:
            user = db.query(User).filter(User.id == r["user_id"]).first()
            if user:
                events.append({
                    "id": r["transaction_id"],
                    "user_id": r["user_id"],
                    "user_name": user.name,
                    "amount": r["amount"] / 100.0,  # Convert from paise
                    "risk_level": r["risk_level"],
                    "source": "ml",
                    "timestamp": r["timestamp"].isoformat() if hasattr(r["timestamp"], "isoformat") else str(r["timestamp"]),
                    "reason": f"ML anomaly score: {r['anomaly_score']:.4f}"
                })
    
    # Get rule-flagged transactions
    for user in db.query(User).all():
        flagged = get_flagged_transactions(user.id, db)
        for f in flagged:
            events.append({
                "id": f["transaction_id"],
                "user_id": user.id,
                "user_name": user.name,
                "amount": f["transaction_amount"] / 100.0,  # Convert from paise
                "risk_level": f["risk_level"],
                "source": "rule",
                "timestamp": datetime.utcnow().isoformat(),
                "reason": f["reason"]
            })
    
    # Sort by timestamp descending and limit
    events.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"events": events[:limit]}


@router.get("/dashboard/recent-transactions")
async def get_recent_transactions(limit: int = 20, db: Session = Depends(get_db)):
    """Get recent transactions across all users."""
    transactions = db.query(Transaction).order_by(
        Transaction.timestamp.desc()
    ).limit(limit).all()
    
    return {
        "transactions": [
            {
                "id": t.id,
                "user_id": t.user_id,
                "amount": t.amount / 100.0,  # Convert from paise
                "type": t.transaction_type.value,
                "status": t.status.value,
                "merchant": t.merchant_name,
                "category": t.merchant_category,
                "city": t.location_city,
                "timestamp": t.timestamp.isoformat(),
                "is_anomaly": t.is_anomaly,
            }
            for t in transactions
        ]
    }