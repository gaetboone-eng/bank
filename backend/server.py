from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import aiohttp

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Twilio Config
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_WHATSAPP_FROM = os.environ.get('TWILIO_WHATSAPP_FROM', '')

# Notion Config
NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')
"

"
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID', '')

# Create the main app
app = FastAPI(title="Tenant Ledger - Banking Assistant")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

security = HTTPBearer()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

# Auth Models
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

# Bank Models
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
    user_id: str
    name: str
    iban: Optional[str] = None
    balance: float
    color: str
    created_at: datetime

# Tenant Models
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
    user_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    property_address: str
    rent_amount: float
    due_day: int
    notion_id: Optional[str] = None
    created_at: datetime
    payment_status: str = "pending"
    last_payment_date: Optional[datetime] = None

# Transaction Models
class TransactionCreate(BaseModel):
    bank_id: str
    amount: float
    description: str
    transaction_date: datetime
    category: str = "other"
    reference: Optional[str] = None

class TransactionResponse(BaseModel):
    id: str
    user_id: str
    bank_id: str
    amount: float
    description: str
    transaction_date: datetime
    category: str
    reference: Optional[str] = None
    matched_tenant_id: Optional[str] = None
    created_at: datetime

# Payment Models
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
    user_id: str
    tenant_id: str
    amount: float
    payment_date: datetime
    bank_id: str
    transaction_id: Optional[str] = None
    month: str
    year: int
    created_at: datetime

# Notification Models
class NotificationRequest(BaseModel):
    tenant_id: str
    message: str

# Dashboard Stats
class DashboardStats(BaseModel):
    total_tenants: int
    paid_tenants: int
    unpaid_tenants: int
    total_rent_expected: float
    total_rent_collected: float
    total_balance: float
    banks_count: int

# ==================== AUTH HELPERS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "name": user_data.name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    
    token = create_token(user_id)
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=user_data.email,
            name=user_data.name,
            created_at=datetime.now(timezone.utc)
        )
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user["id"])
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            created_at=datetime.fromisoformat(user["created_at"]) if isinstance(user["created_at"], str) else user["created_at"]
        )
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        created_at=datetime.fromisoformat(current_user["created_at"]) if isinstance(current_user["created_at"], str) else current_user["created_at"]
    )

# ==================== BANKS ROUTES ====================

@api_router.post("/banks", response_model=BankResponse)
async def create_bank(bank_data: BankCreate, current_user: dict = Depends(get_current_user)):
    bank_id = str(uuid.uuid4())
    bank_doc = {
        "id": bank_id,
        "user_id": current_user["id"],
        "name": bank_data.name,
        "iban": bank_data.iban,
        "balance": bank_data.balance,
        "color": bank_data.color,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.banks.insert_one(bank_doc)
    return BankResponse(**{**bank_doc, "created_at": datetime.now(timezone.utc)})

@api_router.get("/banks", response_model=List[BankResponse])
async def get_banks(current_user: dict = Depends(get_current_user)):
    banks = await db.banks.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(100)
    result = []
    for bank in banks:
        if isinstance(bank.get("created_at"), str):
            bank["created_at"] = datetime.fromisoformat(bank["created_at"])
        result.append(BankResponse(**bank))
    return result

@api_router.put("/banks/{bank_id}", response_model=BankResponse)
async def update_bank(bank_id: str, bank_data: BankUpdate, current_user: dict = Depends(get_current_user)):
    update_data = {k: v for k, v in bank_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    result = await db.banks.find_one_and_update(
        {"id": bank_id, "user_id": current_user["id"]},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Bank not found")
    
    result.pop("_id", None)
    if isinstance(result.get("created_at"), str):
        result["created_at"] = datetime.fromisoformat(result["created_at"])
    return BankResponse(**result)

@api_router.delete("/banks/{bank_id}")
async def delete_bank(bank_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.banks.delete_one({"id": bank_id, "user_id": current_user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bank not found")
    return {"message": "Bank deleted"}

# ==================== TENANTS ROUTES ====================

@api_router.post("/tenants", response_model=TenantResponse)
async def create_tenant(tenant_data: TenantCreate, current_user: dict = Depends(get_current_user)):
    tenant_id = str(uuid.uuid4())
    tenant_doc = {
        "id": tenant_id,
        "user_id": current_user["id"],
        "name": tenant_data.name,
        "email": tenant_data.email,
        "phone": tenant_data.phone,
        "property_address": tenant_data.property_address,
        "rent_amount": tenant_data.rent_amount,
        "due_day": tenant_data.due_day,
        "notion_id": tenant_data.notion_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "payment_status": "pending",
        "last_payment_date": None
    }
    await db.tenants.insert_one(tenant_doc)
    return TenantResponse(**{**tenant_doc, "created_at": datetime.now(timezone.utc)})

@api_router.get("/tenants", response_model=List[TenantResponse])
async def get_tenants(current_user: dict = Depends(get_current_user)):
    tenants = await db.tenants.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(1000)
    
    # Check payment status for current month
    current_month = datetime.now(timezone.utc).strftime("%B")
    current_year = datetime.now(timezone.utc).year
    
    result = []
    for tenant in tenants:
        payment = await db.payments.find_one({
            "tenant_id": tenant["id"],
            "month": current_month,
            "year": current_year
        }, {"_id": 0})
        
        tenant["payment_status"] = "paid" if payment else "pending"
        
        if isinstance(tenant.get("created_at"), str):
            tenant["created_at"] = datetime.fromisoformat(tenant["created_at"])
        if tenant.get("last_payment_date") and isinstance(tenant["last_payment_date"], str):
            tenant["last_payment_date"] = datetime.fromisoformat(tenant["last_payment_date"])
        
        result.append(TenantResponse(**tenant))
    return result

@api_router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str, current_user: dict = Depends(get_current_user)):
    tenant = await db.tenants.find_one({"id": tenant_id, "user_id": current_user["id"]}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if isinstance(tenant.get("created_at"), str):
        tenant["created_at"] = datetime.fromisoformat(tenant["created_at"])
    if tenant.get("last_payment_date") and isinstance(tenant["last_payment_date"], str):
        tenant["last_payment_date"] = datetime.fromisoformat(tenant["last_payment_date"])
    
    return TenantResponse(**tenant)

@api_router.put("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(tenant_id: str, tenant_data: TenantUpdate, current_user: dict = Depends(get_current_user)):
    update_data = {k: v for k, v in tenant_data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    result = await db.tenants.find_one_and_update(
        {"id": tenant_id, "user_id": current_user["id"]},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    result.pop("_id", None)
    if isinstance(result.get("created_at"), str):
        result["created_at"] = datetime.fromisoformat(result["created_at"])
    if result.get("last_payment_date") and isinstance(result["last_payment_date"], str):
        result["last_payment_date"] = datetime.fromisoformat(result["last_payment_date"])
    return TenantResponse(**result)

@api_router.delete("/tenants/{tenant_id}")
async def delete_tenant(tenant_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.tenants.delete_one({"id": tenant_id, "user_id": current_user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"message": "Tenant deleted"}

# ==================== NOTION SYNC ====================

@api_router.post("/tenants/sync-notion")
async def sync_from_notion(current_user: dict = Depends(get_current_user)):
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        raise HTTPException(status_code=400, detail="Notion API not configured. Please add NOTION_API_KEY and NOTION_DATABASE_ID to settings.")
    
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
                headers=headers,
                json={}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"Notion API error: {error_text}")
                
                data = await response.json()
                results = data.get("results", [])
                
                synced_count = 0
                for page in results:
                    props = page.get("properties", {})
                    
                    # Extract data from Notion properties
                    name = ""
                    if "Name" in props and props["Name"].get("title"):
                        name = props["Name"]["title"][0]["plain_text"] if props["Name"]["title"] else ""
                    
                    email = props.get("Email", {}).get("email", "")
                    phone = props.get("Phone", {}).get("phone_number", "")
                    
                    address = ""
                    if "Address" in props and props["Address"].get("rich_text"):
                        address = props["Address"]["rich_text"][0]["plain_text"] if props["Address"]["rich_text"] else ""
                    
                    rent = props.get("Rent", {}).get("number", 0) or props.get("Rent Amount", {}).get("number", 0) or 0
                    due_day = props.get("Due Day", {}).get("number", 1) or 1
                    
                    if name:
                        existing = await db.tenants.find_one({
                            "user_id": current_user["id"],
                            "notion_id": page["id"]
                        })
                        
                        tenant_data = {
                            "name": name,
                            "email": email,
                            "phone": phone,
                            "property_address": address,
                            "rent_amount": rent,
                            "due_day": due_day,
                            "notion_id": page["id"]
                        }
                        
                        if existing:
                            await db.tenants.update_one(
                                {"id": existing["id"]},
                                {"$set": tenant_data}
                            )
                        else:
                            tenant_id = str(uuid.uuid4())
                            await db.tenants.insert_one({
                                "id": tenant_id,
                                "user_id": current_user["id"],
                                **tenant_data,
                                "created_at": datetime.now(timezone.utc).isoformat(),
                                "payment_status": "pending",
                                "last_payment_date": None
                            })
                        synced_count += 1
                
                return {"message": f"Synced {synced_count} tenants from Notion", "count": synced_count}
    
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")

# ==================== TRANSACTIONS ROUTES ====================

@api_router.post("/transactions", response_model=TransactionResponse)
async def create_transaction(tx_data: TransactionCreate, current_user: dict = Depends(get_current_user)):
    # Verify bank belongs to user
    bank = await db.banks.find_one({"id": tx_data.bank_id, "user_id": current_user["id"]})
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    
    tx_id = str(uuid.uuid4())
    tx_doc = {
        "id": tx_id,
        "user_id": current_user["id"],
        "bank_id": tx_data.bank_id,
        "amount": tx_data.amount,
        "description": tx_data.description,
        "transaction_date": tx_data.transaction_date.isoformat(),
        "category": tx_data.category,
        "reference": tx_data.reference,
        "matched_tenant_id": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.transactions.insert_one(tx_doc)
    
    # Update bank balance
    await db.banks.update_one(
        {"id": tx_data.bank_id},
        {"$inc": {"balance": tx_data.amount}}
    )
    
    return TransactionResponse(**{
        **tx_doc,
        "transaction_date": tx_data.transaction_date,
        "created_at": datetime.now(timezone.utc)
    })

@api_router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(bank_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {"user_id": current_user["id"]}
    if bank_id:
        query["bank_id"] = bank_id
    
    transactions = await db.transactions.find(query, {"_id": 0}).sort("transaction_date", -1).to_list(1000)
    result = []
    for tx in transactions:
        if isinstance(tx.get("created_at"), str):
            tx["created_at"] = datetime.fromisoformat(tx["created_at"])
        if isinstance(tx.get("transaction_date"), str):
            tx["transaction_date"] = datetime.fromisoformat(tx["transaction_date"])
        result.append(TransactionResponse(**tx))
    return result

@api_router.post("/transactions/{tx_id}/match/{tenant_id}")
async def match_transaction_to_tenant(tx_id: str, tenant_id: str, current_user: dict = Depends(get_current_user)):
    tx = await db.transactions.find_one({"id": tx_id, "user_id": current_user["id"]})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    tenant = await db.tenants.find_one({"id": tenant_id, "user_id": current_user["id"]})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    await db.transactions.update_one({"id": tx_id}, {"$set": {"matched_tenant_id": tenant_id}})
    
    # Create payment record
    tx_date = datetime.fromisoformat(tx["transaction_date"]) if isinstance(tx["transaction_date"], str) else tx["transaction_date"]
    payment_id = str(uuid.uuid4())
    payment_doc = {
        "id": payment_id,
        "user_id": current_user["id"],
        "tenant_id": tenant_id,
        "amount": tx["amount"],
        "payment_date": tx["transaction_date"],
        "bank_id": tx["bank_id"],
        "transaction_id": tx_id,
        "month": tx_date.strftime("%B"),
        "year": tx_date.year,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.payments.insert_one(payment_doc)
    
    # Update tenant payment status
    await db.tenants.update_one(
        {"id": tenant_id},
        {"$set": {
            "payment_status": "paid",
            "last_payment_date": tx["transaction_date"]
        }}
    )
    
    return {"message": "Transaction matched to tenant", "payment_id": payment_id}

# ==================== PAYMENTS ROUTES ====================

@api_router.post("/payments", response_model=PaymentResponse)
async def create_payment(payment_data: PaymentCreate, current_user: dict = Depends(get_current_user)):
    tenant = await db.tenants.find_one({"id": payment_data.tenant_id, "user_id": current_user["id"]})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    payment_id = str(uuid.uuid4())
    payment_doc = {
        "id": payment_id,
        "user_id": current_user["id"],
        "tenant_id": payment_data.tenant_id,
        "amount": payment_data.amount,
        "payment_date": payment_data.payment_date.isoformat(),
        "bank_id": payment_data.bank_id,
        "transaction_id": payment_data.transaction_id,
        "month": payment_data.month,
        "year": payment_data.year,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.payments.insert_one(payment_doc)
    
    await db.tenants.update_one(
        {"id": payment_data.tenant_id},
        {"$set": {
            "payment_status": "paid",
            "last_payment_date": payment_data.payment_date.isoformat()
        }}
    )
    
    return PaymentResponse(**{**payment_doc, "payment_date": payment_data.payment_date, "created_at": datetime.now(timezone.utc)})

@api_router.get("/payments", response_model=List[PaymentResponse])
async def get_payments(tenant_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {"user_id": current_user["id"]}
    if tenant_id:
        query["tenant_id"] = tenant_id
    
    payments = await db.payments.find(query, {"_id": 0}).sort("payment_date", -1).to_list(1000)
    result = []
    for p in payments:
        if isinstance(p.get("created_at"), str):
            p["created_at"] = datetime.fromisoformat(p["created_at"])
        if isinstance(p.get("payment_date"), str):
            p["payment_date"] = datetime.fromisoformat(p["payment_date"])
        result.append(PaymentResponse(**p))
    return result

# ==================== WHATSAPP NOTIFICATIONS ====================

@api_router.post("/notifications/whatsapp")
async def send_whatsapp_notification(notification: NotificationRequest, current_user: dict = Depends(get_current_user)):
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise HTTPException(status_code=400, detail="Twilio not configured. Please add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM to settings.")
    
    tenant = await db.tenants.find_one({"id": notification.tenant_id, "user_id": current_user["id"]})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if not tenant.get("phone"):
        raise HTTPException(status_code=400, detail="Tenant has no phone number")
    
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        message = client.messages.create(
            body=notification.message,
            from_=f"whatsapp:{TWILIO_WHATSAPP_FROM}",
            to=f"whatsapp:{tenant['phone']}"
        )
        
        # Log notification
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "tenant_id": notification.tenant_id,
            "message": notification.message,
            "status": message.status,
            "sid": message.sid,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {"message": "WhatsApp notification sent", "sid": message.sid, "status": message.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send WhatsApp: {str(e)}")

# ==================== DASHBOARD ====================

@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    tenants = await db.tenants.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(1000)
    banks = await db.banks.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(100)
    
    current_month = datetime.now(timezone.utc).strftime("%B")
    current_year = datetime.now(timezone.utc).year
    
    total_rent_expected = sum(t.get("rent_amount", 0) for t in tenants)
    
    # Count paid tenants for current month
    paid_count = 0
    total_collected = 0
    for tenant in tenants:
        payment = await db.payments.find_one({
            "tenant_id": tenant["id"],
            "month": current_month,
            "year": current_year
        })
        if payment:
            paid_count += 1
            total_collected += payment.get("amount", 0)
    
    total_balance = sum(b.get("balance", 0) for b in banks)
    
    return DashboardStats(
        total_tenants=len(tenants),
        paid_tenants=paid_count,
        unpaid_tenants=len(tenants) - paid_count,
        total_rent_expected=total_rent_expected,
        total_rent_collected=total_collected,
        total_balance=total_balance,
        banks_count=len(banks)
    )

# ==================== SETTINGS ====================

@api_router.get("/settings")
async def get_settings(current_user: dict = Depends(get_current_user)):
    settings = await db.user_settings.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not settings:
        settings = {
            "user_id": current_user["id"],
            "notion_api_key": "",
            "notion_database_id": "",
            "twilio_configured": bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN)
        }
    return settings

class SettingsUpdate(BaseModel):
    notion_api_key: Optional[str] = None
    notion_database_id: Optional[str] = None

@api_router.put("/settings")
async def update_settings(settings_data: SettingsUpdate, current_user: dict = Depends(get_current_user)):
    update_data = {k: v for k, v in settings_data.model_dump().items() if v is not None}
    update_data["user_id"] = current_user["id"]
    
    await db.user_settings.update_one(
        {"user_id": current_user["id"]},
        {"$set": update_data},
        upsert=True
    )
    return {"message": "Settings updated"}

# ==================== ROOT ====================

@api_router.get("/")
async def root():
    return {"message": "Tenant Ledger API", "version": "1.0.0"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
