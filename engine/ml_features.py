from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.models import Transaction, User
import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "amount",
    "historical_avg_amount",
    "amount_to_hist_avg_ratio",
    "rolling_avg_amount_20",
    "amount_to_rolling_avg_ratio",
    "rolling_std_amount_20",
    "amount_zscore_20",
    "txn_count_last_30d",
    "txn_count_last_7d",
    "total_debit_amount_last_30d",
    "avg_debit_amount_last_30d",
    "days_since_last_txn",
    "txn_type_is_debit",
    "status_is_success",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "merchant_category_encoded",
    "payment_method_encoded",
    "city_encoded",
    "user_txn_count_total",
    "user_avg_amount_total",
    "user_std_amount_total",
    "user_failed_ratio",
]


def _get_historical_stats(user_id: int, session: Session, before_timestamp: datetime, exclude_txn_id: Optional[int] = None) -> Dict[str, float]:
    query = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.status == "SUCCESS",
        Transaction.timestamp < before_timestamp
    )
    
    if exclude_txn_id:
        query = query.filter(Transaction.id != exclude_txn_id)
    
    transactions = query.all()
    
    if not transactions:
        return {
            "historical_avg": 0.0,
            "historical_std": 0.0,
            "historical_count": 0
        }
    
    amounts = [t.amount for t in transactions]
    return {
        "historical_avg": np.mean(amounts),
        "historical_std": np.std(amounts) if len(amounts) > 1 else 0.0,
        "historical_count": len(amounts)
    }


def _get_rolling_stats(user_id: int, session: Session, before_timestamp: datetime, window: int = 20, exclude_txn_id: Optional[int] = None) -> Dict[str, float]:
    query = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.status == "SUCCESS",
        Transaction.timestamp < before_timestamp
    ).order_by(Transaction.timestamp.desc())
    
    if exclude_txn_id:
        query = query.filter(Transaction.id != exclude_txn_id)
    
    transactions = query.limit(window).all()
    
    if not transactions:
        return {
            "rolling_avg": 0.0,
            "rolling_std": 0.0,
            "rolling_count": 0
        }
    
    amounts = [t.amount for t in transactions]
    return {
        "rolling_avg": np.mean(amounts),
        "rolling_std": np.std(amounts) if len(amounts) > 1 else 0.0,
        "rolling_count": len(amounts)
    }


def _get_recent_activity(user_id: int, session: Session, before_timestamp: datetime, days: int) -> Dict[str, float]:
    cutoff = before_timestamp - timedelta(days=days)
    
    query = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.timestamp >= cutoff,
        Transaction.timestamp < before_timestamp
    )
    
    transactions = query.all()
    
    if not transactions:
        return {
            "txn_count": 0,
            "total_debit_amount": 0.0,
            "avg_debit_amount": 0.0
        }
    
    debit_txns = [t for t in transactions if t.transaction_type.value == "DEBIT"]
    
    return {
        "txn_count": len(transactions),
        "total_debit_amount": sum(t.amount for t in debit_txns),
        "avg_debit_amount": np.mean([t.amount for t in debit_txns]) if debit_txns else 0.0
    }


def _get_days_since_last_txn(user_id: int, session: Session, before_timestamp: datetime, exclude_txn_id: Optional[int] = None) -> float:
    query = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.timestamp < before_timestamp
    ).order_by(Transaction.timestamp.desc())
    
    if exclude_txn_id:
        query = query.filter(Transaction.id != exclude_txn_id)
    
    last_txn = query.first()
    
    if not last_txn:
        return 365.0
    
    delta = before_timestamp - last_txn.timestamp
    return delta.total_seconds() / 86400.0


def _get_user_global_stats(user_id: int, session: Session, before_timestamp: datetime, exclude_txn_id: Optional[int] = None) -> Dict[str, float]:
    query = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.timestamp < before_timestamp
    )
    
    if exclude_txn_id:
        query = query.filter(Transaction.id != exclude_txn_id)
    
    transactions = query.all()
    
    if not transactions:
        return {
            "total_count": 0,
            "avg_amount": 0.0,
            "std_amount": 0.0,
            "failed_ratio": 0.0
        }
    
    amounts = [t.amount for t in transactions]
    failed = sum(1 for t in transactions if t.status.value == "FAILED")
    
    return {
        "total_count": len(transactions),
        "avg_amount": np.mean(amounts),
        "std_amount": np.std(amounts) if len(amounts) > 1 else 0.0,
        "failed_ratio": failed / len(transactions)
    }


def _encode_categorical(value: str, mapping: Dict[str, int]) -> int:
    return mapping.get(value, -1)


def build_categorical_mappings(session: Session) -> Dict[str, Dict[str, int]]:
    categories = session.query(Transaction.merchant_category).distinct().all()
    category_mapping = {c[0]: i for i, c in enumerate(categories) if c[0]}
    
    payment_methods = session.query(Transaction.payment_method).distinct().all()
    payment_mapping = {p[0].value: i for i, p in enumerate(payment_methods) if p[0]}
    
    cities = session.query(Transaction.location_city).distinct().all()
    city_mapping = {c[0]: i for i, c in enumerate(cities) if c[0]}
    
    return {
        "merchant_category": category_mapping,
        "payment_method": payment_mapping,
        "location_city": city_mapping
    }


def extract_transaction_features(transaction: Transaction, session: Session, categorical_mappings: Optional[Dict] = None) -> Dict[str, Any]:
    user_id = transaction.user_id
    before_ts = transaction.timestamp
    txn_id = transaction.id
    
    hist_stats = _get_historical_stats(user_id, session, before_ts, exclude_txn_id=txn_id)
    rolling_stats = _get_rolling_stats(user_id, session, before_ts, window=20, exclude_txn_id=txn_id)
    recent_30d = _get_recent_activity(user_id, session, before_ts, days=30)
    recent_7d = _get_recent_activity(user_id, session, before_ts, days=7)
    user_global = _get_user_global_stats(user_id, session, before_ts, exclude_txn_id=txn_id)
    days_since_last = _get_days_since_last_txn(user_id, session, before_ts, exclude_txn_id=txn_id)
    
    if categorical_mappings is None:
        categorical_mappings = build_categorical_mappings(session)
    
    amount = transaction.amount
    hist_avg = hist_stats["historical_avg"]
    rolling_avg = rolling_stats["rolling_avg"]
    rolling_std = rolling_stats["rolling_std"]
    
    features = {
        "transaction_id": transaction.id,
        "user_id": user_id,
        "is_anomaly": transaction.is_anomaly,
        "anomaly_type": transaction.anomaly_type,
        "amount": amount,
        "historical_avg_amount": hist_avg,
        "amount_to_hist_avg_ratio": amount / hist_avg if hist_avg > 0 else 0.0,
        "rolling_avg_amount_20": rolling_avg,
        "amount_to_rolling_avg_ratio": amount / rolling_avg if rolling_avg > 0 else 0.0,
        "rolling_std_amount_20": rolling_std,
        "amount_zscore_20": (amount - rolling_avg) / rolling_std if rolling_std > 0 else 0.0,
        "txn_count_last_30d": recent_30d["txn_count"],
        "txn_count_last_7d": recent_7d["txn_count"],
        "total_debit_amount_last_30d": recent_30d["total_debit_amount"],
        "avg_debit_amount_last_30d": recent_30d["avg_debit_amount"],
        "days_since_last_txn": days_since_last,
        "txn_type_is_debit": 1 if transaction.transaction_type.value == "debit" else 0,
        "status_is_success": 1 if transaction.status.value == "success" else 0,
        "hour_of_day": before_ts.hour,
        "day_of_week": before_ts.weekday(),
        "is_weekend": 1 if before_ts.weekday() >= 5 else 0,
        "merchant_category_encoded": _encode_categorical(transaction.merchant_category or "", categorical_mappings.get("merchant_category", {})),
        "payment_method_encoded": _encode_categorical(transaction.payment_method.value, categorical_mappings.get("payment_method", {})),
        "city_encoded": _encode_categorical(transaction.location_city or "", categorical_mappings.get("location_city", {})),
        "user_txn_count_total": user_global["total_count"],
        "user_avg_amount_total": user_global["avg_amount"],
        "user_std_amount_total": user_global["std_amount"],
        "user_failed_ratio": user_global["failed_ratio"],
    }
    
    return features


def build_ml_dataset(session: Session, limit_per_user: Optional[int] = None) -> pd.DataFrame:
    users = session.query(User).all()
    all_features = []
    categorical_mappings = build_categorical_mappings(session)
    
    for user in users:
        query = session.query(Transaction).filter(
            Transaction.user_id == user.id
        ).order_by(Transaction.timestamp.asc())
        
        if limit_per_user:
            query = query.limit(limit_per_user)
        
        transactions = query.all()
        
        for txn in transactions:
            features = extract_transaction_features(txn, session, categorical_mappings)
            all_features.append(features)
    
    df = pd.DataFrame(all_features)
    return df


def prepare_training_data(df: pd.DataFrame) -> tuple:
    feature_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
    X = df[feature_cols].fillna(0)
    y = df["is_anomaly"].astype(int) if "is_anomaly" in df.columns else None
    return X, y, feature_cols


def get_feature_importance_names() -> List[str]:
    return FEATURE_COLUMNS.copy()