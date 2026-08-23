import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from engine.trust_score import (
    calculate_payment_reliability,
    calculate_transaction_consistency,
    calculate_account_behaviour,
    calculate_trust_score
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


def test_payment_reliability_all_success(db_session):
    txns = [
        Transaction(amount=1000, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI),
        Transaction(amount=2000, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.CARD),
        Transaction(amount=1500, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI),
    ]
    score = calculate_payment_reliability(txns)
    assert score == 100.0


def test_payment_reliability_with_failures(db_session):
    txns = [
        Transaction(amount=1000, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI),
        Transaction(amount=2000, transaction_type=TransactionType.DEBIT, status=TransactionStatus.FAILED, payment_method=PaymentMethod.CARD),
        Transaction(amount=1500, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI),
        Transaction(amount=500, transaction_type=TransactionType.DEBIT, status=TransactionStatus.FAILED, payment_method=PaymentMethod.UPI),
    ]
    score = calculate_payment_reliability(txns)
    assert score == 50.0


def test_payment_reliability_empty(db_session):
    score = calculate_payment_reliability([])
    assert score == 50.0


def test_transaction_consistency_low_variance(db_session):
    txns = [
        Transaction(amount=1000, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI),
        Transaction(amount=1050, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI),
        Transaction(amount=950, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI),
        Transaction(amount=1020, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI),
    ]
    score = calculate_transaction_consistency(txns)
    assert score > 80


def test_transaction_consistency_high_variance(db_session):
    txns = [
        Transaction(amount=1000, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI),
        Transaction(amount=10000, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI),
        Transaction(amount=500, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI),
        Transaction(amount=20000, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI),
    ]
    score = calculate_transaction_consistency(txns)
    assert score < 50


def test_transaction_consistency_insufficient_data(db_session):
    txns = [
        Transaction(amount=1000, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI),
        Transaction(amount=2000, transaction_type=TransactionType.CREDIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI),
    ]
    score = calculate_transaction_consistency(txns)
    assert score == 50.0


def test_account_behaviour_active_user(db_session):
    created_at = datetime.utcnow() - timedelta(days=30)
    txns = [Transaction(amount=1000, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI, timestamp=datetime.utcnow() - timedelta(days=i)) for i in range(20)]
    
    score = calculate_account_behaviour(txns, created_at)
    assert score >= 80


def test_account_behaviour_inactive_user(db_session):
    created_at = datetime.utcnow() - timedelta(days=365)
    txns = [Transaction(amount=1000, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI, timestamp=created_at + timedelta(days=i*30)) for i in range(5)]
    
    score = calculate_account_behaviour(txns, created_at)
    assert score < 80


def test_account_behaviour_empty(db_session):
    created_at = datetime.utcnow() - timedelta(days=30)
    score = calculate_account_behaviour([], created_at)
    assert score == 50.0


def test_calculate_trust_score_integration(db_session):
    user = User(name="Trust Test", email="trust@test.demo", role=UserRole.DELIVERY_PARTNER, account_created_at=datetime.utcnow() - timedelta(days=60), is_verified=True)
    db_session.add(user)
    db_session.flush()
    
    account = Account(user_id=user.id, balance=10000)
    db_session.add(account)
    db_session.flush()
    
    txns = []
    for i in range(30):
        txn = Transaction(
            user_id=user.id,
            account_id=account.id,
            amount=1500 + (i * 10),
            transaction_type=TransactionType.DEBIT,
            status=TransactionStatus.SUCCESS,
            payment_method=PaymentMethod.UPI,
            timestamp=datetime.utcnow() - timedelta(days=30-i)
        )
        txns.append(txn)
    db_session.add_all(txns)
    db_session.commit()
    
    result = calculate_trust_score(user.id, db_session)
    
    assert "trust_score" in result
    assert 0 <= result["trust_score"] <= 100
    assert "payment_reliability" in result
    assert "transaction_consistency" in result
    assert "account_behaviour" in result
    assert "components" in result
    
    for comp_name, comp_data in result["components"].items():
        assert "score" in comp_data
        assert "weight" in comp_data
        assert "contribution" in comp_data
        assert comp_data["weight"] > 0


def test_calculate_trust_score_nonexistent_user(db_session):
    result = calculate_trust_score(99999, db_session)
    assert result["trust_score"] == 0


def test_trust_score_deterministic(db_session):
    user = User(name="Det Test", email="det@test.demo", role=UserRole.FREELANCER, account_created_at=datetime.utcnow() - timedelta(days=30), is_verified=True)
    db_session.add(user)
    db_session.flush()
    
    account = Account(user_id=user.id, balance=20000)
    db_session.add(account)
    db_session.flush()
    
    for i in range(20):
        txn = Transaction(
            user_id=user.id,
            account_id=account.id,
            amount=2000,
            transaction_type=TransactionType.DEBIT,
            status=TransactionStatus.SUCCESS,
            payment_method=PaymentMethod.UPI,
            timestamp=datetime.utcnow() - timedelta(days=20-i)
        )
        db_session.add(txn)
    db_session.commit()
    
    result1 = calculate_trust_score(user.id, db_session)
    result2 = calculate_trust_score(user.id, db_session)
    
    assert result1["trust_score"] == result2["trust_score"]