import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from database.models import User, Account, Transaction, UserRole, TransactionType, TransactionStatus, PaymentMethod
from database.db import init_db, drop_db, get_session_direct, reset_db
from sqlalchemy import inspect


@pytest.fixture(scope="function")
def db_session():
    reset_db()
    session = get_session_direct()
    yield session
    session.close()
    drop_db()


def test_database_tables_created(db_session):
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()
    
    assert "users" in tables
    assert "accounts" in tables
    assert "transactions" in tables


def test_user_model_creation(db_session):
    user = User(
        name="Test User",
        email="test@trustbridge.demo",
        role=UserRole.DELIVERY_PARTNER,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    
    assert user.id is not None
    assert user.name == "Test User"
    assert user.role == UserRole.DELIVERY_PARTNER


def test_account_model_creation(db_session):
    user = User(
        name="Test User",
        email="test2@trustbridge.demo",
        role=UserRole.FREELANCER
    )
    db_session.add(user)
    db_session.flush()
    
    account = Account(
        user_id=user.id,
        account_type="savings",
        balance=10000.0,
        currency="INR"
    )
    db_session.add(account)
    db_session.commit()
    
    assert account.id is not None
    assert account.user_id == user.id
    assert account.balance == 10000.0


def test_transaction_model_creation(db_session):
    user = User(
        name="Test User",
        email="test3@trustbridge.demo",
        role=UserRole.STUDENT
    )
    db_session.add(user)
    db_session.flush()
    
    account = Account(
        user_id=user.id,
        account_type="savings",
        balance=5000.0
    )
    db_session.add(account)
    db_session.flush()
    
    txn = Transaction(
        user_id=user.id,
        account_id=account.id,
        amount=1500.0,
        transaction_type=TransactionType.DEBIT,
        status=TransactionStatus.SUCCESS,
        payment_method=PaymentMethod.UPI,
        merchant_category="Food & Dining",
        merchant_name="Test Restaurant",
        location_city="Mumbai",
        description="Test transaction"
    )
    db_session.add(txn)
    db_session.commit()
    
    assert txn.id is not None
    assert txn.amount == 1500.0
    assert txn.transaction_type == TransactionType.DEBIT
    assert txn.status == TransactionStatus.SUCCESS


def test_user_account_relationship(db_session):
    user = User(name="Rel User", email="rel@test.demo", role=UserRole.DELIVERY_PARTNER)
    db_session.add(user)
    db_session.flush()
    
    account1 = Account(user_id=user.id, balance=1000)
    account2 = Account(user_id=user.id, balance=2000)
    db_session.add_all([account1, account2])
    db_session.commit()
    
    assert len(user.accounts) == 2


def test_user_transaction_relationship(db_session):
    user = User(name="Txn User", email="txn@test.demo", role=UserRole.FREELANCER)
    db_session.add(user)
    db_session.flush()
    
    account = Account(user_id=user.id, balance=5000)
    db_session.add(account)
    db_session.flush()
    
    txns = [
        Transaction(user_id=user.id, account_id=account.id, amount=1000, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.UPI),
        Transaction(user_id=user.id, account_id=account.id, amount=2000, transaction_type=TransactionType.DEBIT, status=TransactionStatus.SUCCESS, payment_method=PaymentMethod.CARD),
    ]
    db_session.add_all(txns)
    db_session.commit()
    
    assert len(user.transactions) == 2