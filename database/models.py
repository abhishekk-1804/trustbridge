from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, Text
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
    balance = Column(Float, default=0.0)
    currency = Column(String(3), default="INR")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")

    def __repr__(self):
        return f"<Account(id={self.id}, user_id={self.user_id}, balance={self.balance})>"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    amount = Column(Float, nullable=False)
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

    def __repr__(self):
        return f"<Transaction(id={self.id}, user_id={self.user_id}, amount={self.amount}, type={self.transaction_type.value})>"