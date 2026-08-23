import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from decimal import Decimal
from engine.payment_service import (
    simulate_payment,
    get_payment_by_idempotency_key,
    verify_ledger_balance,
    InsufficientBalanceError,
    InvalidAmountError,
    AccountNotFoundError,
    AccountInactiveError,
    SameAccountError,
    IdempotencyError,
    RiskRejectionError,
    to_paise,
    from_paise,
    SimulatedPaymentMethod
)
from database.db import get_session_direct, reset_db, init_db
from database.models import (
    User, Account, PaymentTransaction, LedgerEntry,
    UserRole, AccountStatus, TransactionType, PaymentStatus
)
from datetime import datetime, timedelta
from data.generator import generate_synthetic_data, SEED
import random


@pytest.fixture(scope="function")
def db_session():
    reset_db()
    init_db()
    session = get_session_direct()
    yield session
    session.close()
    reset_db()


@pytest.fixture(scope="function")
def seeded_data(db_session):
    """Generate synthetic data with fixed seed for reproducible tests."""
    random.seed(SEED)
    generate_synthetic_data()
    yield db_session


@pytest.fixture(scope="function")
def test_accounts(db_session):
    """Create two test accounts with known balances."""
    user1 = User(name="Sender User", email="sender@test.demo", role=UserRole.FREELANCER, is_verified=True)
    user2 = User(name="Receiver User", email="receiver@test.demo", role=UserRole.STUDENT, is_verified=True)
    db_session.add_all([user1, user2])
    db_session.flush()
    
    account1 = Account(user_id=user1.id, balance=to_paise(Decimal("10000.00")), status=AccountStatus.ACTIVE)
    account2 = Account(user_id=user2.id, balance=to_paise(Decimal("5000.00")), status=AccountStatus.ACTIVE)
    db_session.add_all([account1, account2])
    db_session.commit()
    
    return account1, account2


def test_to_paise_conversion():
    assert to_paise(Decimal("100.00")) == 10000
    assert to_paise(Decimal("100.50")) == 10050
    assert to_paise(Decimal("0.01")) == 1
    assert to_paise(Decimal("0")) == 0


def test_from_paise_conversion():
    assert from_paise(10000) == Decimal("100.00")
    assert from_paise(10050) == Decimal("100.50")
    assert from_paise(1) == Decimal("0.01")
    assert from_paise(0) == Decimal("0")


def test_successful_payment(test_accounts):
    sender, receiver = test_accounts
    session = get_session_direct()
    
    try:
        # Re-query accounts in this session
        sender = session.query(Account).filter(Account.id == sender.id).first()
        receiver = session.query(Account).filter(Account.id == receiver.id).first()
        
        sender_balance_before = from_paise(sender.balance)
        receiver_balance_before = from_paise(receiver.balance)
        
        payment = simulate_payment(
            sender_account_id=sender.id,
            receiver_account_id=receiver.id,
            amount=Decimal("1000.00"),
            payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
            idempotency_key="test-key-001",
            session=session
        )
        
        assert payment.status.value == "completed"
        assert payment.amount == to_paise(Decimal("1000.00"))
        assert payment.sender_account_id == sender.id
        assert payment.receiver_account_id == receiver.id
        
        # Verify balances updated
        session.refresh(sender)
        session.refresh(receiver)
        
        assert from_paise(sender.balance) == sender_balance_before - Decimal("1000.00")
        assert from_paise(receiver.balance) == receiver_balance_before + Decimal("1000.00")
        
        # Verify ledger entries
        verification = verify_ledger_balance(payment.id, session)
        assert verification["is_balanced"]
        assert verification["total_debits"] == to_paise(Decimal("1000.00"))
        assert verification["total_credits"] == to_paise(Decimal("1000.00"))
        assert verification["entry_count"] == 2
        
    finally:
        session.close()


def test_insufficient_balance(test_accounts):
    sender, receiver = test_accounts
    session = get_session_direct()
    
    try:
        # Re-query accounts in this session
        sender = session.query(Account).filter(Account.id == sender.id).first()
        receiver = session.query(Account).filter(Account.id == receiver.id).first()
        
        sender_balance_before = from_paise(sender.balance)
        receiver_balance_before = from_paise(receiver.balance)
        
        with pytest.raises(InsufficientBalanceError) as exc_info:
            simulate_payment(
                sender_account_id=sender.id,
                receiver_account_id=receiver.id,
                amount=Decimal("20000.00"),  # More than sender has
                payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
                idempotency_key="test-key-insufficient",
                session=session
            )
        
        assert exc_info.value.code == "INSUFFICIENT_BALANCE"
        
        # Verify balances unchanged
        session.refresh(sender)
        session.refresh(receiver)
        assert from_paise(sender.balance) == sender_balance_before
        assert from_paise(receiver.balance) == receiver_balance_before
        
    finally:
        session.close()


def test_invalid_amount(test_accounts):
    sender, receiver = test_accounts
    session = get_session_direct()
    
    try:
        with pytest.raises(InvalidAmountError) as exc_info:
            simulate_payment(
                sender_account_id=sender.id,
                receiver_account_id=receiver.id,
                amount=Decimal("-100.00"),
                payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
                idempotency_key="test-key-invalid",
                session=session
            )
        
        assert exc_info.value.code == "INVALID_AMOUNT"
        
        with pytest.raises(InvalidAmountError) as exc_info2:
            simulate_payment(
                sender_account_id=sender.id,
                receiver_account_id=receiver.id,
                amount=Decimal("0"),
                payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
                idempotency_key="test-key-zero",
                session=session
            )
        
        assert exc_info2.value.code == "INVALID_AMOUNT"
        
    finally:
        session.close()


def test_nonexistent_sender(test_accounts):
    _, receiver = test_accounts
    session = get_session_direct()
    
    try:
        with pytest.raises(AccountNotFoundError) as exc_info:
            simulate_payment(
                sender_account_id=99999,
                receiver_account_id=receiver.id,
                amount=Decimal("100.00"),
                payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
                idempotency_key="test-key-no-sender",
                session=session
            )
        
        assert exc_info.value.code == "ACCOUNT_NOT_FOUND"
        
    finally:
        session.close()


def test_nonexistent_receiver(test_accounts):
    sender, _ = test_accounts
    session = get_session_direct()
    
    try:
        with pytest.raises(AccountNotFoundError) as exc_info:
            simulate_payment(
                sender_account_id=sender.id,
                receiver_account_id=99999,
                amount=Decimal("100.00"),
                payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
                idempotency_key="test-key-no-receiver",
                session=session
            )
        
        assert exc_info.value.code == "ACCOUNT_NOT_FOUND"
        
    finally:
        session.close()


def test_same_account(test_accounts):
    sender, _ = test_accounts
    session = get_session_direct()
    
    try:
        with pytest.raises(SameAccountError) as exc_info:
            simulate_payment(
                sender_account_id=sender.id,
                receiver_account_id=sender.id,
                amount=Decimal("100.00"),
                payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
                idempotency_key="test-key-same",
                session=session
            )
        
        assert exc_info.value.code == "SAME_ACCOUNT"
        
    finally:
        session.close()


def test_inactive_sender_account(test_accounts):
    sender, receiver = test_accounts
    session = get_session_direct()
    
    try:
        # Re-query accounts in this session and freeze sender
        sender = session.query(Account).filter(Account.id == sender.id).first()
        receiver = session.query(Account).filter(Account.id == receiver.id).first()
        
        sender.status = AccountStatus.FROZEN
        session.commit()
        
        with pytest.raises(AccountInactiveError) as exc_info:
            simulate_payment(
                sender_account_id=sender.id,
                receiver_account_id=receiver.id,
                amount=Decimal("100.00"),
                payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
                idempotency_key="test-key-frozen",
                session=session
            )
        
        assert exc_info.value.code == "ACCOUNT_INACTIVE"
        
    finally:
        session.close()


def test_idempotency(test_accounts):
    sender, receiver = test_accounts
    session = get_session_direct()
    
    try:
        # Re-query accounts in this session
        sender = session.query(Account).filter(Account.id == sender.id).first()
        receiver = session.query(Account).filter(Account.id == receiver.id).first()
        
        # First payment
        payment1 = simulate_payment(
            sender_account_id=sender.id,
            receiver_account_id=receiver.id,
            amount=Decimal("500.00"),
            payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
            idempotency_key="idem-key-001",
            session=session
        )
        
        # Second payment with same idempotency key
        with pytest.raises(IdempotencyError) as exc_info:
            simulate_payment(
                sender_account_id=sender.id,
                receiver_account_id=receiver.id,
                amount=Decimal("500.00"),
                payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
                idempotency_key="idem-key-001",  # Same key
                session=session
            )
        
        assert exc_info.value.code == "IDEMPOTENCY_VIOLATION"
        assert exc_info.value.existing_transaction_id == payment1.id
        
        # Verify only one payment was processed
        payments = session.query(PaymentTransaction).filter(
            PaymentTransaction.idempotency_key == "idem-key-001"
        ).all()
        assert len(payments) == 1
        
        # Verify balance only deducted once
        sender = session.query(Account).filter(Account.id == sender.id).first()
        assert from_paise(sender.balance) == Decimal("9500.00")  # 10000 - 500
        
    finally:
        session.close()


def test_idempotency_database_constraint(test_accounts):
    """Test that database-level unique constraint on idempotency_key works."""
    sender, receiver = test_accounts
    session = get_session_direct()
    
    try:
        # Create first payment directly
        payment1 = PaymentTransaction(
            reference_id="TEST001",
            idempotency_key="db-constraint-key",
            sender_account_id=sender.id,
            receiver_account_id=receiver.id,
            amount=to_paise(Decimal("100.00")),
            payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
            status=PaymentStatus.COMPLETED
        )
        session.add(payment1)
        session.commit()
        
        # Try to create second payment with same idempotency key via service
        with pytest.raises(IdempotencyError):
            simulate_payment(
                sender_account_id=sender.id,
                receiver_account_id=receiver.id,
                amount=Decimal("200.00"),
                payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
                idempotency_key="db-constraint-key",
                session=session
            )
        
    finally:
        session.close()


def test_ledger_balance_verification(test_accounts):
    sender, receiver = test_accounts
    session = get_session_direct()
    
    try:
        # Re-query accounts in this session
        sender = session.query(Account).filter(Account.id == sender.id).first()
        receiver = session.query(Account).filter(Account.id == receiver.id).first()
        
        payment = simulate_payment(
            sender_account_id=sender.id,
            receiver_account_id=receiver.id,
            amount=Decimal("2500.00"),
            payment_method=SimulatedPaymentMethod.BANK_TRANSFER_SIMULATED,
            idempotency_key="test-ledger-001",
            session=session
        )
        
        verification = verify_ledger_balance(payment.id, session)
        
        assert verification["is_balanced"]
        assert verification["total_debits"] == to_paise(Decimal("2500.00"))
        assert verification["total_credits"] == to_paise(Decimal("2500.00"))
        assert verification["entry_count"] == 2
        
        # Check debit entry
        debit_entry = next(e for e in verification["entries"] if e["entry_type"] == "debit")
        assert debit_entry["account_id"] == sender.id
        assert debit_entry["amount"] == to_paise(Decimal("2500.00"))
        
        # Check credit entry
        credit_entry = next(e for e in verification["entries"] if e["entry_type"] == "credit")
        assert credit_entry["account_id"] == receiver.id
        assert credit_entry["amount"] == to_paise(Decimal("2500.00"))
        
    finally:
        session.close()


def test_rollback_on_failure(test_accounts):
    """Test that failed payment rolls back all changes."""
    sender, receiver = test_accounts
    session = get_session_direct()
    
    try:
        # Re-query accounts in this session
        sender = session.query(Account).filter(Account.id == sender.id).first()
        receiver = session.query(Account).filter(Account.id == receiver.id).first()
        
        sender_balance_before = from_paise(sender.balance)
        receiver_balance_before = from_paise(receiver.balance)
        
        # Check that sender/receiver balances are unchanged after a failed validation
        with pytest.raises(InvalidAmountError):
            simulate_payment(
                sender_account_id=sender.id,
                receiver_account_id=receiver.id,
                amount=Decimal("-500.00"),
                payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
                idempotency_key="rollback-test-1",
                session=session
            )
        
        sender = session.query(Account).filter(Account.id == sender.id).first()
        receiver = session.query(Account).filter(Account.id == receiver.id).first()
        assert from_paise(sender.balance) == sender_balance_before
        assert from_paise(receiver.balance) == receiver_balance_before
        
    finally:
        session.close()


def test_sender_balance_decreases_correctly(test_accounts):
    sender, receiver = test_accounts
    session = get_session_direct()
    
    try:
        # Re-query accounts in this session
        sender = session.query(Account).filter(Account.id == sender.id).first()
        receiver = session.query(Account).filter(Account.id == receiver.id).first()
        
        initial_balance = from_paise(sender.balance)
        payment_amount = Decimal("1234.56")
        
        simulate_payment(
            sender_account_id=sender.id,
            receiver_account_id=receiver.id,
            amount=payment_amount,
            payment_method=SimulatedPaymentMethod.WALLET_SIMULATED,
            idempotency_key="balance-test-1",
            session=session
        )
        
        sender = session.query(Account).filter(Account.id == sender.id).first()
        expected_balance = initial_balance - payment_amount
        actual_balance = from_paise(sender.balance)
        
        assert actual_balance == expected_balance
        
    finally:
        session.close()


def test_receiver_balance_increases_correctly(test_accounts):
    sender, receiver = test_accounts
    session = get_session_direct()
    
    try:
        # Re-query accounts in this session
        sender = session.query(Account).filter(Account.id == sender.id).first()
        receiver = session.query(Account).filter(Account.id == receiver.id).first()
        
        initial_balance = from_paise(receiver.balance)
        payment_amount = Decimal("789.01")
        
        simulate_payment(
            sender_account_id=sender.id,
            receiver_account_id=receiver.id,
            amount=payment_amount,
            payment_method=SimulatedPaymentMethod.WALLET_SIMULATED,
            idempotency_key="balance-test-2",
            session=session
        )
        
        receiver = session.query(Account).filter(Account.id == receiver.id).first()
        expected_balance = initial_balance + payment_amount
        actual_balance = from_paise(receiver.balance)
        
        assert actual_balance == expected_balance
        
    finally:
        session.close()


def test_failed_payment_does_not_modify_balances(test_accounts):
    sender, receiver = test_accounts
    session = get_session_direct()
    
    try:
        # Re-query accounts in this session
        sender = session.query(Account).filter(Account.id == sender.id).first()
        receiver = session.query(Account).filter(Account.id == receiver.id).first()
        
        sender_balance_before = from_paise(sender.balance)
        receiver_balance_before = from_paise(receiver.balance)
        
        # Trigger a validation failure (insufficient balance)
        try:
            simulate_payment(
                sender_account_id=sender.id,
                receiver_account_id=receiver.id,
                amount=Decimal("999999.00"),
                payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
                idempotency_key="fail-test-1",
                session=session
            )
        except InsufficientBalanceError:
            pass
        
        sender = session.query(Account).filter(Account.id == sender.id).first()
        receiver = session.query(Account).filter(Account.id == receiver.id).first()
        
        assert from_paise(sender.balance) == sender_balance_before
        assert from_paise(receiver.balance) == receiver_balance_before
        
    finally:
        session.close()


def test_payment_obtains_risk_information(test_accounts, seeded_data):
    """Test that payment service obtains risk information from existing engines."""
    sender, receiver = test_accounts
    session = get_session_direct()
    
    try:
        payment = simulate_payment(
            sender_account_id=sender.id,
            receiver_account_id=receiver.id,
            amount=Decimal("100.00"),
            payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
            idempotency_key="risk-info-test-1",
            session=session
        )
        
        assert payment.trust_score is not None
        assert payment.fraud_rule_flagged is not None
        assert payment.ml_anomaly_score is not None
        assert payment.ml_is_anomaly is not None
        assert payment.risk_policy_decision in ["proceed", "flag", "reject"]
        
    finally:
        session.close()


def test_high_risk_transaction_follows_policy(seeded_data):
    """Test that high-risk transaction follows documented risk policy."""
    session = get_session_direct()
    
    try:
        # Find the account with the injected anomaly (Raj's account)
        sender = session.query(Account).filter(Account.id == 1).first()  # Raj's account
        receiver = session.query(Account).filter(Account.id == 2).first()  # Priya's account
        
        if sender and receiver:
            # Make a large payment from the account with the amount spike anomaly
            # This should trigger the fraud rule and be rejected
            try:
                payment = simulate_payment(
                    sender_account_id=sender.id,
                    receiver_account_id=receiver.id,
                    amount=Decimal("15000.00"),  # Large amount likely to trigger rules
                    payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
                    idempotency_key="high-risk-test-1",
                    session=session
                )
                # If we get here, payment was not rejected
                assert payment.status.value == "completed"
                assert payment.risk_policy_decision in ["proceed", "flag"]
            except RiskRejectionError as e:
                # Payment was rejected by risk policy - this is expected for high-risk transactions
                assert e.code == "RISK_REJECTION"
                assert e.risk_assessment is not None
                assert e.risk_assessment.get("risk_decision") == "reject"
        
    finally:
        session.close()


def test_multiple_payments_ledger_integrity(test_accounts):
    """Test that multiple payments maintain ledger integrity."""
    sender, receiver = test_accounts
    session = get_session_direct()
    
    try:
        # Re-query accounts in this session
        sender = session.query(Account).filter(Account.id == sender.id).first()
        receiver = session.query(Account).filter(Account.id == receiver.id).first()
        
        amounts = [Decimal("100.00"), Decimal("200.00"), Decimal("50.00")]
        
        for i, amount in enumerate(amounts):
            simulate_payment(
                sender_account_id=sender.id,
                receiver_account_id=receiver.id,
                amount=amount,
                payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
                idempotency_key=f"multi-test-{i}",
                session=session
            )
        
        # Verify each payment's ledger
        payments = session.query(PaymentTransaction).filter(
            PaymentTransaction.sender_account_id == sender.id
        ).all()
        
        total_debits = 0
        total_credits = 0
        
        for payment in payments:
            verification = verify_ledger_balance(payment.id, session)
            assert verification["is_balanced"]
            total_debits += verification["total_debits"]
            total_credits += verification["total_credits"]
        
        assert total_debits == total_credits
        assert total_debits == to_paise(sum(amounts))
        
    finally:
        session.close()


def test_different_payment_methods(test_accounts):
    """Test all simulated payment methods work."""
    sender, receiver = test_accounts
    session = get_session_direct()
    
    try:
        # Re-query accounts in this session
        sender = session.query(Account).filter(Account.id == sender.id).first()
        receiver = session.query(Account).filter(Account.id == receiver.id).first()
        
        methods = [
            SimulatedPaymentMethod.UPI_SIMULATED,
            SimulatedPaymentMethod.BANK_TRANSFER_SIMULATED,
            SimulatedPaymentMethod.WALLET_SIMULATED
        ]
        
        for i, method in enumerate(methods):
            payment = simulate_payment(
                sender_account_id=sender.id,
                receiver_account_id=receiver.id,
                amount=Decimal("100.00"),
                payment_method=method,
                idempotency_key=f"method-test-{i}",
                session=session
            )
            
            assert payment.payment_method == method
            assert payment.status.value == "completed"
        
    finally:
        session.close()


def test_existing_stage1_tests_still_pass():
    """Verify Stage 1 models still work with new schema."""
    from tests.test_models import (
        test_database_tables_created,
        test_user_model_creation,
        test_account_model_creation,
        test_transaction_model_creation
    )
    from database.db import get_session_direct, reset_db, init_db
    
    reset_db()
    init_db()
    session = get_session_direct()
    
    try:
        test_database_tables_created(session)
        test_user_model_creation(session)
        test_account_model_creation(session)
        test_transaction_model_creation(session)
    finally:
        session.close()
        reset_db()


def test_existing_stage2_ml_tests_still_pass():
    """Verify Stage 2 ML models still work with new schema."""
    from tests.test_ml_features import test_extract_transaction_features
    from database.db import get_session_direct, reset_db, init_db
    from data.generator import generate_synthetic_data, SEED
    import random
    
    reset_db()
    init_db()
    random.seed(SEED)
    generate_synthetic_data()
    
    session = get_session_direct()
    
    try:
        test_extract_transaction_features(session)
    finally:
        session.close()
        reset_db()


def test_verify_ledger_balance_edge_cases():
    """Test ledger verification with various scenarios."""
    from database.db import get_session_direct, reset_db, init_db
    from database.models import User, Account, PaymentTransaction, LedgerEntry, SimulatedPaymentMethod, PaymentStatus, UserRole, AccountStatus, TransactionType
    from decimal import Decimal
    import random
    
    reset_db()
    init_db()
    session = get_session_direct()
    
    try:
        user1 = User(name="Test1", email="t1@test.demo", role=UserRole.FREELANCER, is_verified=True)
        user2 = User(name="Test2", email="t2@test.demo", role=UserRole.STUDENT, is_verified=True)
        session.add_all([user1, user2])
        session.flush()
        
        acc1 = Account(user_id=user1.id, balance=to_paise(Decimal("1000")), status=AccountStatus.ACTIVE)
        acc2 = Account(user_id=user2.id, balance=to_paise(Decimal("1000")), status=AccountStatus.ACTIVE)
        session.add_all([acc1, acc2])
        session.commit()
        
        # Create a payment with ledger entries manually
        payment = PaymentTransaction(
            reference_id="MANUAL001",
            idempotency_key="manual-key-001",
            sender_account_id=acc1.id,
            receiver_account_id=acc2.id,
            amount=to_paise(Decimal("100")),
            payment_method=SimulatedPaymentMethod.UPI_SIMULATED,
            status=PaymentStatus.COMPLETED,
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        session.add(payment)
        session.flush()
        
        # Add ledger entries manually
        le1 = LedgerEntry(
            payment_transaction_id=payment.id,
            account_id=acc1.id,
            entry_type=TransactionType.DEBIT,
            amount=to_paise(Decimal("100")),
            balance_after=to_paise(Decimal("900"))
        )
        le2 = LedgerEntry(
            payment_transaction_id=payment.id,
            account_id=acc2.id,
            entry_type=TransactionType.CREDIT,
            amount=to_paise(Decimal("100")),
            balance_after=to_paise(Decimal("1100"))
        )
        session.add_all([le1, le2])
        session.commit()
        
        verification = verify_ledger_balance(payment.id, session)
        assert verification["is_balanced"]
        assert verification["total_debits"] == to_paise(Decimal("100"))
        assert verification["total_credits"] == to_paise(Decimal("100"))
        
    finally:
        session.close()
        reset_db()