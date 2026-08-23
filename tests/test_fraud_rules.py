import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from engine.fraud_rules import (
    calculate_historical_average,
    calculate_rolling_average,
    detect_amount_spike,
    check_all_transactions,
    get_flagged_transactions
)
from database.models import User, Account, Transaction, UserRole, TransactionType, TransactionStatus, PaymentMethod
from database.db import get_session_direct, reset_db, init_db
from datetime import datetime, timedelta


@pytest.fixture(scope="function")
def db_session():
    reset_db()
    init_db()
    session = get_session_direct()
    yield session
    session.close()
    reset_db()


def create_test_user_with_txns(session, normal_amount=1000, spike_amount=None):
    user = User(name="Fraud Test", email="fraud@test.demo", role=UserRole.DELIVERY_PARTNER, account_created_at=datetime.utcnow() - timedelta(days=30), is_verified=True)
    session.add(user)
    session.flush()
    
    account = Account(user_id=user.id, balance=50000)
    session.add(account)
    session.flush()
    
    txns = []
    for i in range(20):
        amount = normal_amount
        if spike_amount and i == 19:
            amount = spike_amount
        txn = Transaction(
            user_id=user.id,
            account_id=account.id,
            amount=amount,
            transaction_type=TransactionType.DEBIT,
            status=TransactionStatus.SUCCESS,
            payment_method=PaymentMethod.UPI,
            timestamp=datetime.utcnow() - timedelta(days=20-i)
        )
        txns.append(txn)
    session.add_all(txns)
    session.commit()
    
    return user, txns


def test_historical_average_normal(db_session):
    user, txns = create_test_user_with_txns(db_session, normal_amount=1000)
    
    avg = calculate_historical_average(user.id, db_session)
    
    assert avg == 1000.0


def test_historical_average_excludes_transaction(db_session):
    user, txns = create_test_user_with_txns(db_session, normal_amount=1000, spike_amount=10000)
    
    spike_txn = txns[-1]
    avg = calculate_historical_average(user.id, db_session, exclude_txn_id=spike_txn.id)
    
    assert avg == 1000.0


def test_rolling_average_normal(db_session):
    user, txns = create_test_user_with_txns(db_session, normal_amount=2000)
    
    avg = calculate_rolling_average(user.id, db_session, window=10)
    
    assert avg == 2000.0


def test_detect_amount_spike_not_flagged(db_session):
    user, txns = create_test_user_with_txns(db_session, normal_amount=1000)
    
    normal_txn = txns[10]
    result = detect_amount_spike(normal_txn, db_session, multiplier=3.0)
    
    assert result["flagged"] is False
    assert result["risk_level"] == "LOW"
    assert result["ratio"] < 3.0


def test_detect_amount_spike_flagged(db_session):
    user, txns = create_test_user_with_txns(db_session, normal_amount=1000, spike_amount=5000)
    
    spike_txn = txns[-1]
    result = detect_amount_spike(spike_txn, db_session, multiplier=3.0)
    
    assert result["flagged"] is True
    assert result["risk_level"] == "HIGH"
    assert result["ratio"] > 3.0
    assert result["transaction_amount"] == 5000
    assert result["reference_average"] == 1000


def test_detect_amount_spike_insufficient_history(db_session):
    user = User(name="New User", email="new@test.demo", role=UserRole.STUDENT, account_created_at=datetime.utcnow() - timedelta(days=5), is_verified=True)
    db_session.add(user)
    db_session.flush()
    
    account = Account(user_id=user.id, balance=5000)
    db_session.add(account)
    db_session.flush()
    
    txn = Transaction(
        user_id=user.id,
        account_id=account.id,
        amount=5000,
        transaction_type=TransactionType.DEBIT,
        status=TransactionStatus.SUCCESS,
        payment_method=PaymentMethod.UPI
    )
    db_session.add(txn)
    db_session.commit()
    
    result = detect_amount_spike(txn, db_session, multiplier=3.0)
    
    assert result["flagged"] is False
    assert result["reference_average"] == 0.0
    assert "Insufficient transaction history" in result["reason"]


def test_check_all_transactions(db_session):
    user, txns = create_test_user_with_txns(db_session, normal_amount=1000, spike_amount=5000)
    
    results = check_all_transactions(user.id, db_session, multiplier=3.0)
    
    assert len(results) == 20
    flagged_count = sum(1 for r in results if r["flagged"])
    assert flagged_count == 1
    assert results[0]["flagged"] is True


def test_get_flagged_transactions(db_session):
    user, txns = create_test_user_with_txns(db_session, normal_amount=1000, spike_amount=5000)
    
    flagged = get_flagged_transactions(user.id, db_session, multiplier=3.0)
    
    assert len(flagged) == 1
    assert flagged[0]["transaction_id"] == txns[-1].id
    assert flagged[0]["risk_level"] == "HIGH"


def test_get_flagged_transactions_none(db_session):
    user, txns = create_test_user_with_txns(db_session, normal_amount=1000)
    
    flagged = get_flagged_transactions(user.id, db_session, multiplier=3.0)
    
    assert len(flagged) == 0


def test_fraud_rule_detects_injected_anomaly():
    from data.generator import generate_synthetic_data, USER_PROFILES, SEED
    import random
    from database.db import reset_db, get_session_direct
    from database.models import User, Transaction
    
    reset_db()
    random.seed(SEED)
    generate_synthetic_data()
    
    session = get_session_direct()
    try:
        users = session.query(User).all()
        
        for user in users:
            flagged = get_flagged_transactions(user.id, session, multiplier=3.0)
            
            profile = next(p for p in USER_PROFILES if p["name"] == user.name)
            expected_idx = profile["anomaly_txn_idx"]
            
            txns = session.query(Transaction).filter(Transaction.user_id == user.id).all()
            
            if expected_idx < len(txns):
                anomaly_txn = next((t for t in txns if t.is_anomaly), None)
                
                if anomaly_txn:
                    assert len(flagged) >= 1, f"User {user.name} has injected anomaly but no transactions flagged"
                    
                    flagged_ids = [f["transaction_id"] for f in flagged]
                    assert anomaly_txn.id in flagged_ids, f"Injected anomaly transaction {anomaly_txn.id} not flagged for user {user.name}"
    finally:
        session.close()


def test_fraud_rule_multiplier_threshold(db_session):
    user, txns = create_test_user_with_txns(db_session, normal_amount=1000, spike_amount=2500)
    
    spike_txn = txns[-1]
    
    result_2x = detect_amount_spike(spike_txn, db_session, multiplier=2.0)
    result_3x = detect_amount_spike(spike_txn, db_session, multiplier=3.0)
    result_4x = detect_amount_spike(spike_txn, db_session, multiplier=4.0)
    
    assert result_2x["flagged"] is True
    assert result_3x["flagged"] is False
    assert result_4x["flagged"] is False