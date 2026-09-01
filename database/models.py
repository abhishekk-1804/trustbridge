from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, Text, BigInteger, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class UserRole(PyEnum):
    DELIVERY_PARTNER = "delivery_partner"
    FREELANCER = "freelancer"
    STUDENT = "student"


class TransactionType(PyEnum):
    DEBIT = "debit"
    CREDIT = "credit"


class TransactionStatus(PyEnum):
    SUCCESS = "success"
    FAILED = "failed"


class PaymentMethod(PyEnum):
    UPI = "upi"
    CARD = "card"
    NET_BANKING = "net_banking"
    WALLET = "wallet"


class AccountStatus(PyEnum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class PaymentStatus(PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    REVERSED = "reversed"


class SimulatedPaymentMethod(PyEnum):
    UPI_SIMULATED = "upi_simulated"
    BANK_TRANSFER_SIMULATED = "bank_transfer_simulated"
    WALLET_SIMULATED = "wallet_simulated"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    account_created_at = Column(DateTime, default=datetime.utcnow)
    is_verified = Column(Boolean, default=False)

    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', role={self.role.value})>"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_type = Column(String(50), default="savings")
    balance = Column(BigInteger, default=0)  # Stored in minor units (paise for INR)
    currency = Column(String(3), default="INR")
    status = Column(Enum(AccountStatus), default=AccountStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")
    sent_payments = relationship("PaymentTransaction", foreign_keys="PaymentTransaction.sender_account_id", back_populates="sender_account")
    received_payments = relationship("PaymentTransaction", foreign_keys="PaymentTransaction.receiver_account_id", back_populates="receiver_account")
    ledger_entries = relationship("LedgerEntry", back_populates="account")

    def get_balance_decimal(self) -> Decimal:
        """Return balance as Decimal in major units (rupees)."""
        return Decimal(self.balance) / Decimal(100)

    def set_balance_decimal(self, amount: Decimal):
        """Set balance from Decimal in major units (rupees)."""
        self.balance = int(amount * Decimal(100))

    def __repr__(self):
        return f"<Account(id={self.id}, user_id={self.user_id}, balance={self.balance}, status={self.status.value})>"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    amount = Column(BigInteger, nullable=False)  # Stored in minor units (paise)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.SUCCESS)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    merchant_category = Column(String(100))
    merchant_name = Column(String(150))
    location_city = Column(String(100))
    description = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_anomaly = Column(Boolean, default=False)
    anomaly_type = Column(String(50), nullable=True)

    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")

    def get_amount_decimal(self) -> Decimal:
        return Decimal(self.amount) / Decimal(100)

    def __repr__(self):
        return f"<Transaction(id={self.id}, user_id={self.user_id}, amount={self.amount}, type={self.transaction_type.value})>"


class PaymentTransaction(Base):
    """Simulated payment transaction between two accounts."""
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reference_id = Column(String(64), unique=True, nullable=False, index=True)  # Human-readable reference
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)  # For idempotency
    
    sender_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    receiver_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    amount = Column(BigInteger, nullable=False)  # Stored in minor units (paise)
    currency = Column(String(3), default="INR")
    
    payment_method = Column(Enum(SimulatedPaymentMethod, values_callable=lambda x: [e.value for e in x]), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Risk assessment at time of payment
    trust_score = Column(Float, nullable=True)
    fraud_rule_flagged = Column(Boolean, default=False)
    fraud_rule_reason = Column(Text, nullable=True)
    ml_anomaly_score = Column(Float, nullable=True)
    ml_is_anomaly = Column(Boolean, default=False)
    risk_policy_decision = Column(String(50), nullable=True)  # "proceed", "flag", "reject"
    
    failure_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    sender_account = relationship("Account", foreign_keys=[sender_account_id], back_populates="sent_payments")
    receiver_account = relationship("Account", foreign_keys=[receiver_account_id], back_populates="received_payments")
    ledger_entries = relationship("LedgerEntry", back_populates="payment_transaction", cascade="all, delete-orphan")

    def get_amount_decimal(self) -> Decimal:
        return Decimal(self.amount) / Decimal(100)

    def __repr__(self):
        return f"<PaymentTransaction(id={self.id}, ref={self.reference_id}, amount={self.amount}, status={self.status.value})>"


class LedgerEntry(Base):
    """Double-entry ledger entry for a payment transaction."""
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_transaction_id = Column(Integer, ForeignKey("payment_transactions.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    
    entry_type = Column(Enum(TransactionType), nullable=False)  # DEBIT or CREDIT
    amount = Column(BigInteger, nullable=False)  # Stored in minor units (always positive)
    balance_after = Column(BigInteger, nullable=False)  # Account balance after this entry
    
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    payment_transaction = relationship("PaymentTransaction", back_populates="ledger_entries")
    account = relationship("Account", back_populates="ledger_entries")

    def get_amount_decimal(self) -> Decimal:
        return Decimal(self.amount) / Decimal(100)

    def get_balance_after_decimal(self) -> Decimal:
        return Decimal(self.balance_after) / Decimal(100)

    def __repr__(self):
        return f"<LedgerEntry(id={self.id}, payment_id={self.payment_transaction_id}, account_id={self.account_id}, type={self.entry_type.value}, amount={self.amount})>"