import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from data.generator import generate_synthetic_data, get_user_transaction_counts, USER_PROFILES, SEED
from database.db import get_session_direct, reset_db
from database.models import User, Account, Transaction, TransactionStatus, TransactionType


@pytest.fixture(scope="function")
def clean_db():
    reset_db()
    yield
    reset_db()


def test_synthetic_data_generation(clean_db):
    generate_synthetic_data()
    
    session = get_session_direct()
    try:
        users = session.query(User).all()
        assert len(users) == 3
        
        for user in users:
            assert user.name in [p["name"] for p in USER_PROFILES]
            assert user.email is not None
            assert user.is_verified is True
        
        accounts = session.query(Account).all()
        assert len(accounts) == 3
        
        transactions = session.query(Transaction).all()
        assert len(transactions) > 100
        assert len(transactions) < 500
        
        anomaly_count = sum(1 for t in transactions if t.is_anomaly)
        assert anomaly_count >= 1
        
        for txn in transactions:
            if txn.is_anomaly:
                assert txn.anomaly_type == "AMOUNT_SPIKE"
                assert txn.amount > 5000
    finally:
        session.close()


def test_deterministic_generation(clean_db):
    import random
    from data.generator import SEED
    
    random.seed(SEED)
    generate_synthetic_data()
    
    session = get_session_direct()
    try:
        txns_first = session.query(Transaction).all()
        amounts_first = [(t.user_id, t.amount, t.timestamp) for t in txns_first]
    finally:
        session.close()
    
    reset_db()
    random.seed(SEED)
    generate_synthetic_data()
    
    session = get_session_direct()
    try:
        txns_second = session.query(Transaction).all()
        amounts_second = [(t.user_id, t.amount, t.timestamp) for t in txns_second]
    finally:
        session.close()
    
    assert len(amounts_first) == len(amounts_second)
    for (uid1, amt1, ts1), (uid2, amt2, ts2) in zip(amounts_first, amounts_second):
        assert uid1 == uid2
        assert amt1 == amt2


def test_user_transaction_counts(clean_db):
    generate_synthetic_data()
    counts = get_user_transaction_counts()
    
    assert len(counts) == 3
    for name, count in counts.items():
        assert count > 0
        assert count < 200
    
    total = sum(counts.values())
    assert total > 300
    assert total < 500


def test_anomaly_injected_per_user(clean_db):
    generate_synthetic_data()
    
    session = get_session_direct()
    try:
        users = session.query(User).all()
        
        for user in users:
            anomalies = session.query(Transaction).filter(
                Transaction.user_id == user.id,
                Transaction.is_anomaly == True
            ).all()
            
            profile = next(p for p in USER_PROFILES if p["name"] == user.name)
            expected_idx = profile["anomaly_txn_idx"]
            txns_per_user = len(session.query(Transaction).filter(Transaction.user_id == user.id).all())
            
            if expected_idx < txns_per_user:
                assert len(anomalies) == 1, f"User {user.name} should have 1 anomaly at index {expected_idx}, has {len(anomalies)}"
                assert anomalies[0].anomaly_type == "AMOUNT_SPIKE"
    finally:
        session.close()


def test_transaction_fields_populated(clean_db):
    generate_synthetic_data()
    
    session = get_session_direct()
    try:
        transactions = session.query(Transaction).all()
        
        for txn in transactions:
            assert txn.amount > 0
            assert txn.transaction_type in [TransactionType.DEBIT, TransactionType.CREDIT]
            assert txn.status in [TransactionStatus.SUCCESS, TransactionStatus.FAILED]
            assert txn.payment_method is not None
            assert txn.merchant_category is not None
            assert txn.merchant_name is not None
            assert txn.location_city is not None
            assert txn.timestamp is not None
            assert isinstance(txn.is_anomaly, bool)
    finally:
        session.close()