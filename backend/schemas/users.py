from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    DELIVERY_PARTNER = "delivery_partner"
    FREELANCER = "freelancer"
    STUDENT = "student"


class AccountStatus(str, Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class AccountResponse(BaseModel):
    id: int
    user_id: int
    account_type: str
    balance: float
    currency: str
    status: AccountStatus
    created_at: datetime

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: UserRole


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    account_created_at: datetime
    is_verified: bool
    accounts: List[AccountResponse] = []

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int