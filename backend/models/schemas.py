from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime


# Auth
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Organization
class OrganizationCreate(BaseModel):
    name: str

class OrganizationResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    owner_ids: List[str] = []

class OrganizationMember(BaseModel):
    user_id: str
    organization_id: str
    role: str = "owner"
    joined_at: datetime


# Banks
class BankCreate(BaseModel):
    name: str
    iban: Optional[str] = None
    balance: float = 0.0
    color: str = "#064E3B"

class BankUpdate(BaseModel):
    name: Optional[str] = None
    iban: Optional[str] = None
    balance: Optional[float] = None
    color: Optional[str] = None

class BankResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    name: str
    iban: Optional[str] = None
    balance: float
    color: str
    created_at: datetime


# Tenants
class TenantCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    property_address: str
    rent_amount: float
    due_day: int = 1
    notion_id: Optional[str] = None

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    property_address: Optional[str] = None
    rent_amount: Optional[float] = None
    due_day: Optional[int] = None

class TenantResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    property_address: str
    structure: Optional[str] = "Non défini"
    rent_amount: float
    due_day: int
    notion_id: Optional[str] = None
    created_at: datetime
    payment_status: str = "pending"
    last_payment_date: Optional[datetime] = None


# Transactions
class TransactionCreate(BaseModel):
    bank_id: str
    amount: float
    description: str
    transaction_date: datetime
    category: str = "other"
    reference: Optional[str] = None

class TransactionResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    bank_id: str
    amount: float
    description: str
    transaction_date: datetime
    category: str
    reference: Optional[str] = None
    matched_tenant_id: Optional[str] = None
    created_at: datetime


# Payments
class PaymentCreate(BaseModel):
    tenant_id: str
    amount: float
    payment_date: datetime
    bank_id: str
    transaction_id: Optional[str] = None
    month: str
    year: int

class PaymentResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    tenant_id: str
    amount: float
    payment_date: datetime
    bank_id: str
    transaction_id: Optional[str] = None
    month: str
    year: int
    created_at: datetime


# Notifications
class NotificationRequest(BaseModel):
    tenant_id: str
    message: str


# Dashboard
class DashboardStats(BaseModel):
    total_tenants: int
    paid_tenants: int
    unpaid_tenants: int
    total_rent_expected: float
    total_rent_collected: float
    total_balance: float
    banks_count: int


# Settings
class SettingsUpdate(BaseModel):
    notion_api_key: Optional[str] = None
    notion_database_id: Optional[str] = None
