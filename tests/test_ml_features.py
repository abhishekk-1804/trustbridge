import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
from engine.ml_features import (
    build_categorical_mappings,
    extract_transaction_features,
    build_ml_dataset,
    prepare_training_data,
    FEATURE_COLUMNS
)
from database.db import get_session_direct, reset_db, init_db
from database.models import User, Account, Transaction, UserRole, TransactionType, TransactionStatus, PaymentMethod
from datetime import datetime, timedelta


@pytest.fixture(scope="function")
def db_session():
    reset_db()
    init_db()
    session = get_session_direct()
    yield session
    session.close()
    reset_db()


def create_test_user_with_txns(session, normal_amount=1000, spike_amount=None, n_txns=20):
    user = User(name="ML Test", email="ml@test.demo", role=UserRole.DELIVERY_PARTNER, account_created_at=datetime.utcnow() - timedelta(days=30), is_verified=True)
    session.add(user)
    session.flush()
    
    account = Account(user_id=user.id, balance=50000)
    session.add(account)
    session.flush()
    
    txns = []
    for i in range(n_txns):
        amount = normal_amount
        if spike_amount and i == n_txns - 1:
            amount = spike_amount
        txn = Transaction(
            user_id=user.id,
            account_id=account.id,
            amount=amount,
            transaction_type=TransactionType.DEBIT,
            status=TransactionStatus.SUCCESS,
            payment_method=PaymentMethod.UPI,
            merchant_category="Food & Dining",
            merchant_name="Test Restaurant",
            location_city="Mumbai",
            timestamp=datetime.utcnow() - timedelta(days=n_txns-i)
        )
        txns.append(txn)
    session.add_all(txns)
    session.commit()
    
    return user, txns


def test_build_categorical_mappings(db_session):
    user, txns = create_test_user_with_txns(db_session)
    
    mappings = build_categorical_mappings(db_session)
    
    assert "merchant_category" in mappings
    assert "payment_method" in mappings
    assert "location_city" in mappings
    assert "Food & Dining" in mappings["merchant_category"]
    assert "upi" in mappings["payment_method"]
    assert "Mumbai" in mappings["location_city"]


def test_extract_transaction_features(db_session):
    user, txns = create_test_user_with_txns(db_session)
    txn = txns[10]
    
    mappings = build_categorical_mappings(db_session)
    features = extract_transaction_features(txn, db_session, mappings)
    
    assert "transaction_id" in features
    assert "user_id" in features
    assert "amount" in features
    assert "historical_avg_amount" in features
    assert "amount_to_hist_avg_ratio" in features
    assert "rolling_avg_amount_20" in features
    assert "rolling_std_amount_20" in features
    assert "amount_zscore_20" in features
    assert "txn_count_last_30d" in features
    assert "txn_count_last_7d" in features
    assert "days_since_last_txn" in features
    assert "txn_type_is_debit" in features
    assert "status_is_success" in features
    assert "hour_of_day" in features
    assert "day_of_week" in features
    assert "is_weekend" in features
    assert "merchant_category_encoded" in features
    assert "payment_method_encoded" in features
    assert "city_encoded" in features
    assert "user_txn_count_total" in features
    assert "user_avg_amount_total" in features
    assert "user_std_amount_total" in features
    assert "user_failed_ratio" in features
    assert "is_anomaly" in features
    
    assert features["amount"] == 1000.0
    assert features["txn_type_is_debit"] == 1
    assert features["status_is_success"] == 1
    assert features["historical_avg_amount"] > 0


def test_extract_features_no_leakage(db_session):
    user, txns = create_test_user_with_txns(db_session, spike_amount=10000)
    spike_txn = txns[-1]
    
    mappings = build_categorical_mappings(db_session)
    features = extract_transaction_features(spike_txn, db_session, mappings)
    
    hist_avg = features["historical_avg_amount"]
    assert hist_avg == 1000.0
    
    ratio = features["amount_to_hist_avg_ratio"]
    assert ratio == 10.0


def test_build_ml_dataset(db_session):
    user, txns = create_test_user_with_txns(db_session, n_txns=30)
    
    df = build_ml_dataset(db_session, limit_per_user=30)
    
    assert len(df) > 0
    assert "transaction_id" in df.columns
    assert "user_id" in df.columns
    assert "is_anomaly" in df.columns
    assert "amount" in df.columns
    assert "historical_avg_amount" in df.columns


def test_prepare_training_data(db_session):
    user, txns = create_test_user_with_txns(db_session, n_txns=30)
    
    df = build_ml_dataset(db_session, limit_per_user=30)
    X, y, feature_cols = prepare_training_data(df)
    
    assert X.shape[0] == len(df)
    assert len(feature_cols) == X.shape[1]
    assert y is not None
    assert y.shape[0] == len(df)
    assert all(c in df.columns for c in feature_cols)
    assert not X.isnull().any().any()


def test_feature_columns_consistency(db_session):
    user, txns = create_test_user_with_txns(db_session, n_txns=10)
    
    df = build_ml_dataset(db_session, limit_per_user=10)
    X, y, feature_cols = prepare_training_data(df)
    
    for col in feature_cols:
        assert col in FEATURE_COLUMNS


def test_deterministic_features(db_session):
    user, txns = create_test_user_with_txns(db_session, n_txns=10)
    txn = txns[5]
    
    mappings = build_categorical_mappings(db_session)
    
    features1 = extract_transaction_features(txn, db_session, mappings)
    features2 = extract_transaction_features(txn, db_session, mappings)
    
    for k in features1:
        if k not in ["transaction_id", "user_id"]:
            assert features1[k] == features2[k], f"Feature {k} not deterministic"


def test_historical_stats_exclude_current(db_session):
    user, txns = create_test_user_with_txns(db_session, spike_amount=10000)
    spike_txn = txns[-1]
    
    mappings = build_categorical_mappings(db_session)
    features = extract_transaction_features(spike_txn, db_session, mappings)
    
    assert features["historical_avg_amount"] == 1000.0
    assert features["amount_to_hist_avg_ratio"] == 10.0


def test_rolling_stats_window(db_session):
    user, txns = create_test_user_with_txns(db_session, n_txns=50)
    
    mappings = build_categorical_mappings(db_session)
    features = extract_transaction_features(txns[30], db_session, mappings)
    
    assert features["rolling_avg_amount_20"] > 0
    assert features["rolling_std_amount_20"] >= 0