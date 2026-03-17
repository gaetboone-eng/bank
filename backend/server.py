from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
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
import jwt as pyjwt
import aiohttp
import unicodedata
import re

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
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID', '')

# Enable Banking Config
ENABLE_BANKING_APP_ID = os.environ.get('ENABLE_BANKING_APP_ID', '')
ENABLE_BANKING_PRIVATE_KEY = os.environ.get('ENABLE_BANKING_PRIVATE_KEY', '')
ENABLE_BANKING_REDIRECT_URL = os.environ.get('ENABLE_BANKING_REDIRECT_URL', '')

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


# Organization Models
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
    role: str = "owner"  # owner, admin, member
    joined_at: datetime

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
    structure: Optional[str] = "Non défini"
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
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = pyjwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Get user's organization membership
        membership = await db.organization_members.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        
        # Add organization_id to user object
        user["organization_id"] = membership.get("organization_id") if membership else None
        user["org_role"] = membership.get("role") if membership else None
        
        return user
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_filter_for_user(current_user: dict) -> dict:
    """
    Get MongoDB filter based on user's organization or user_id.
    If user has organization_id, filter by organization.
    Otherwise, filter by user_id (backwards compatibility).
    """
    if current_user.get("organization_id"):
        return {"organization_id": current_user["organization_id"]}
    return get_filter_for_user(current_user)

def prepare_document_for_insert(current_user: dict, doc: dict) -> dict:
    """
    Add organization_id or user_id to document before insert.
    """
    if current_user.get("organization_id"):
        doc["organization_id"] = current_user["organization_id"]
    doc["user_id"] = current_user["id"]  # Keep for audit/history
    return doc


# ==================== ENABLE BANKING HELPERS ====================

def create_enable_banking_jwt():
    """Create JWT token for Enable Banking API"""
    if not ENABLE_BANKING_APP_ID or not ENABLE_BANKING_PRIVATE_KEY:
        raise HTTPException(status_code=400, detail="Enable Banking not configured")
    
    iat = int(datetime.now(timezone.utc).timestamp())
    jwt_body = {
        "iss": "enablebanking.com",
        "aud": "api.enablebanking.com",
        "iat": iat,
        "exp": iat + 3600,
    }
    
    # Load private key using cryptography
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    
    try:
        # Check if it's a file path
        if ENABLE_BANKING_PRIVATE_KEY.startswith("/") or ENABLE_BANKING_PRIVATE_KEY.endswith(".pem"):
            with open(ENABLE_BANKING_PRIVATE_KEY, 'rb') as f:
                key_data = f.read()
        else:
            key_data = ENABLE_BANKING_PRIVATE_KEY.encode('utf-8')
        
        private_key = serialization.load_pem_private_key(
            key_data,
            password=None,
            backend=default_backend()
        )
        
        token = pyjwt.encode(
            jwt_body,
            private_key,
            algorithm="RS256",
            headers={"kid": ENABLE_BANKING_APP_ID}
        )
        return token
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating JWT: {str(e)}")

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
        **get_filter_for_user(current_user),
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
    banks = await db.banks.find(get_filter_for_user(current_user), {"_id": 0}).to_list(100)
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
        {"id": bank_id, **get_filter_for_user(current_user)},
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
    result = await db.banks.delete_one({"id": bank_id, **get_filter_for_user(current_user)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bank not found")
    return {"message": "Bank deleted"}

# ==================== TENANTS ROUTES ====================

@api_router.post("/tenants", response_model=TenantResponse)
async def create_tenant(tenant_data: TenantCreate, current_user: dict = Depends(get_current_user)):
    tenant_id = str(uuid.uuid4())
    tenant_doc = {
        "id": tenant_id,
        **get_filter_for_user(current_user),
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
    filter_query = get_filter_for_user(current_user)
    tenants = await db.tenants.find(filter_query, {"_id": 0}).to_list(1000)
    
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
    tenant = await db.tenants.find_one({"id": tenant_id, **get_filter_for_user(current_user)}, {"_id": 0})
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
        {"id": tenant_id, **get_filter_for_user(current_user)},
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
    result = await db.tenants.delete_one({"id": tenant_id, **get_filter_for_user(current_user)})
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
                    
                    # Extract structure/building information
                    structure = ""
                    if "Structure" in props and props["Structure"].get("rich_text"):
                        structure = props["Structure"]["rich_text"][0]["plain_text"] if props["Structure"]["rich_text"] else ""
                    elif "Bâtiment" in props and props["Bâtiment"].get("rich_text"):
                        structure = props["Bâtiment"]["rich_text"][0]["plain_text"] if props["Bâtiment"]["rich_text"] else ""
                    elif "Building" in props and props["Building"].get("rich_text"):
                        structure = props["Building"]["rich_text"][0]["plain_text"] if props["Building"]["rich_text"] else ""
                    elif "Structure" in props and props["Structure"].get("select"):
                        structure = props["Structure"]["select"]["name"] if props["Structure"]["select"] else ""
                    elif "Bâtiment" in props and props["Bâtiment"].get("select"):
                        structure = props["Bâtiment"]["select"]["name"] if props["Bâtiment"]["select"] else ""
                    
                    rent = props.get("Loyer Mensuel", {}).get("number", 0) or props.get("Rent", {}).get("number", 0) or props.get("Rent Amount", {}).get("number", 0) or 0
                    due_day = props.get("Due Day", {}).get("number", 1) or 1
                    
                    if name:
                        existing = await db.tenants.find_one({
                            **get_filter_for_user(current_user),
                            "notion_id": page["id"]
                        })
                        
                        tenant_data = {
                            "name": name,
                            "email": email,
                            "phone": phone,
                            "property_address": address,
                            "structure": structure or "Non défini",
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
                                **get_filter_for_user(current_user),
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
    bank = await db.banks.find_one({"id": tx_data.bank_id, **get_filter_for_user(current_user)})
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    
    tx_id = str(uuid.uuid4())
    tx_doc = {
        "id": tx_id,
        **get_filter_for_user(current_user),
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
    query = get_filter_for_user(current_user)
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
    tx = await db.transactions.find_one({"id": tx_id, **get_filter_for_user(current_user)})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    tenant = await db.tenants.find_one({"id": tenant_id, **get_filter_for_user(current_user)})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    await db.transactions.update_one({"id": tx_id}, {"$set": {"matched_tenant_id": tenant_id}})
    
    # ===== SAVE MATCHING RULE FOR FUTURE AUTO-MATCHING =====
    # Extract key patterns from transaction for future matching
    description = tx.get("description", "")
    description_normalized = normalize_text(description)
    
    # Extract unique identifier words (potential payer name)
    keywords = extract_name_words(description)
    keyword_pattern = " ".join(keywords[:5])  # Keep first 5 significant words
    
    # Check if rule already exists
    existing_rule = await db.matching_rules.find_one({
        **get_filter_for_user(current_user),
        "tenant_id": tenant_id,
        "pattern": keyword_pattern
    })
    
    if not existing_rule and keyword_pattern:
        # Save new matching rule
        await db.matching_rules.insert_one({
            "id": str(uuid.uuid4()),
            **get_filter_for_user(current_user),
            "tenant_id": tenant_id,
            "tenant_name": tenant["name"],
            "pattern": keyword_pattern,
            "original_description": description,
            "amount": tx["amount"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "match_count": 1
        })
        logger.info(f"📝 New matching rule saved: '{keyword_pattern}' → {tenant['name']}")
    elif existing_rule:
        # Increment match count
        await db.matching_rules.update_one(
            {"id": existing_rule["id"]},
            {"$inc": {"match_count": 1}}
        )
    
    # Create payment record
    tx_date = datetime.fromisoformat(tx["transaction_date"]) if isinstance(tx["transaction_date"], str) else tx["transaction_date"]
    payment_id = str(uuid.uuid4())
    payment_doc = {
        "id": payment_id,
        **get_filter_for_user(current_user),
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
    
    return {"message": "Transaction matched to tenant", "payment_id": payment_id, "rule_saved": bool(keyword_pattern)}

# ==================== AUTO-MATCHING ====================

def normalize_text(text):
    """Normalize text for comparison"""
    if not text:
        return ""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return text

def extract_name_words(text):
    """Extract potential names from transaction description"""
    text = normalize_text(text)
    stopwords = ['virement', 'sepa', 'recu', 'vir', 'inst', 'loyer', 'prlv', 'carte', 'cb',
                 'mme', 'mlle', 'monsieur', 'madame', 'mr', 'dr', 'ei', 'sci', 'scr', 
                 'instantane', 'permanent', 'credit', 'debit', 'prelvt', 'bureau', 'msp',
                 'cab', 'cabinet', 'fevrier', 'janvier', 'mars', 'avril', 'mai', 'juin',
                 '2026', '2025', '202602', '202601', 'ics', 'fr', 'sca', 'ipr', 'loy',
                 'med', 'maison', 'centre', 'mmc', 'seclin', 'docteur', 'juillet', 'aout',
                 'septembre', 'octobre', 'novembre', 'decembre']
    words = text.split()
    return [w for w in words if len(w) > 2 and w not in stopwords]

def calculate_match_score(tenant_name, transaction_desc):
    """Calculate match score between tenant name and transaction description"""
    tenant_normalized = normalize_text(tenant_name)
    tenant_parts = tenant_normalized.split()
    desc_words = extract_name_words(transaction_desc)
    desc_text = ' '.join(desc_words)
    
    score = 0
    for part in tenant_parts:
        if len(part) > 2:
            if part in desc_text:
                score += 10
            else:
                for word in desc_words:
                    if len(word) > 3 and len(part) > 3:
                        if word.startswith(part[:4]) or part.startswith(word[:4]):
                            score += 5
                            break
    return score

async def match_using_learned_rules(user_id: str, transaction_desc: str, amount: float):
    """Try to match transaction using previously learned rules"""
    desc_normalized = normalize_text(transaction_desc)
    desc_keywords = extract_name_words(transaction_desc)
    desc_pattern = " ".join(desc_keywords[:5])
    
    # Get all matching rules for this user
    rules = await db.matching_rules.find({"user_id": user_id}).to_list(1000)
    
    best_rule = None
    best_score = 0
    
    for rule in rules:
        rule_pattern = rule.get("pattern", "")
        rule_words = rule_pattern.split()
        
        # Calculate similarity score
        score = 0
        for word in rule_words:
            if word in desc_pattern:
                score += 10
            elif any(word[:4] in dw or dw[:4] in word for dw in desc_keywords if len(dw) > 3 and len(word) > 3):
                score += 5
        
        # Bonus for amount match
        rule_amount = rule.get("amount", 0)
        if rule_amount > 0:
            amount_diff = abs(amount - rule_amount) / rule_amount
            if amount_diff < 0.05:  # 5% tolerance for learned rules
                score += 15
        
        # Higher score = better match, minimum 15 for rule-based matching
        if score > best_score and score >= 15:
            best_score = score
            best_rule = rule
    
    return best_rule, best_score

@api_router.post("/transactions/auto-match")
async def auto_match_transactions(current_user: dict = Depends(get_current_user)):
    """Automatically match unmatched transactions with tenants based on learned rules, name and amount"""
    
    # Get all tenants
    tenants = await db.tenants.find(get_filter_for_user(current_user), {"_id": 0}).to_list(1000)
    tenants_dict = {t["id"]: t for t in tenants}
    
    # Get unmatched positive transactions (incoming payments)
    transactions = await db.transactions.find({
        **get_filter_for_user(current_user),
        "amount": {"$gt": 0},
        "matched_tenant_id": None
    }, {"_id": 0}).to_list(1000)
    
    matches = []
    current_month = datetime.now(timezone.utc).strftime("%B")
    current_year = datetime.now(timezone.utc).year
    
    for tx in transactions:
        desc = tx.get('description', '')
        amount = tx['amount']
        
        best_match = None
        best_score = 0
        match_source = "name"
        
        # FIRST: Try to match using learned rules (from previous manual associations)
        learned_rule, rule_score = await match_using_learned_rules(current_user["id"], desc, amount)
        if learned_rule and learned_rule["tenant_id"] in tenants_dict:
            best_match = tenants_dict[learned_rule["tenant_id"]]
            best_score = rule_score
            match_source = "learned_rule"
            logger.info(f"🎯 Rule-based match: {desc[:40]} → {best_match['name']} (score: {rule_score})")
        
        # SECOND: If no rule match, try name-based matching
        if not best_match:
            for tenant in tenants:
                rent = tenant.get('rent_amount', 0)
                if rent > 0:
                    # Check amount tolerance (15%)
                    amount_diff = abs(amount - rent) / rent
                    if amount_diff < 0.15:
                        score = calculate_match_score(tenant['name'], desc)
                        # Bonus for exact amount match
                        if amount_diff < 0.01:
                            score += 5
                        
                        if score > best_score and score >= 10:
                            best_score = score
                            best_match = tenant
                            match_source = "name"
        
        if best_match:
            # Update transaction
            await db.transactions.update_one(
                {"id": tx['id']},
                {"$set": {"matched_tenant_id": best_match['id']}}
            )
            
            # Check if payment exists for this month
            existing = await db.payments.find_one({
                "tenant_id": best_match['id'],
                "month": current_month,
                "year": current_year
            })
            
            if not existing:
                # Create payment
                payment_id = str(uuid.uuid4())
                tx_date = tx.get('transaction_date', datetime.now(timezone.utc).isoformat())
                
                await db.payments.insert_one({
                    "id": payment_id,
                    **get_filter_for_user(current_user),
                    "tenant_id": best_match['id'],
                    "amount": amount,
                    "payment_date": tx_date,
                    "bank_id": tx['bank_id'],
                    "transaction_id": tx['id'],
                    "month": current_month,
                    "year": current_year,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                
                # Update tenant status
                await db.tenants.update_one(
                    {"id": best_match['id']},
                    {"$set": {
                        "payment_status": "paid",
                        "last_payment_date": tx_date
                    }}
                )
                
                matches.append({
                    "transaction_amount": amount,
                    "tenant_name": best_match['name'],
                    "score": best_score,
                    "match_source": match_source
                })
    
    return {
        "message": f"Auto-matched {len(matches)} transactions",
        "matches": matches,
        "by_rule": len([m for m in matches if m.get("match_source") == "learned_rule"]),
        "by_name": len([m for m in matches if m.get("match_source") == "name"])
    }

# ==================== MATCHING RULES MANAGEMENT ====================

@api_router.get("/matching-rules")
async def get_matching_rules(current_user: dict = Depends(get_current_user)):
    """Get all learned matching rules"""
    rules = await db.matching_rules.find(
        get_filter_for_user(current_user),
        {"_id": 0}
    ).sort("match_count", -1).to_list(1000)
    return rules

@api_router.delete("/matching-rules/{rule_id}")
async def delete_matching_rule(rule_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a matching rule"""
    result = await db.matching_rules.delete_one({
        "id": rule_id,
        **get_filter_for_user(current_user)
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted"}

# ==================== MONTHLY PAYMENT STATUS ====================

@api_router.get("/payments/monthly-status")
async def get_monthly_payment_status(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020, le=2100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get payment status for all tenants for a specific month.
    Considers payments made from the 28th of the previous month.
    """
    from calendar import monthrange
    
    # Calculate date range: 28th of previous month to 28th of current month
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
    
    # Start date: 28th of previous month
    start_date = datetime(prev_year, prev_month, 28, 0, 0, 0, tzinfo=timezone.utc)
    
    # End date: 28th of current month (or last day if month has less than 28 days)
    last_day = min(28, monthrange(year, month)[1])
    end_date = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    
    # Get all tenants
    tenants = await db.tenants.find(
        get_filter_for_user(current_user),
        {"_id": 0}
    ).to_list(1000)
    
    # Get all payments in the date range
    payments = await db.payments.find({
        **get_filter_for_user(current_user),
        "payment_date": {
            "$gte": start_date.isoformat(),
            "$lte": end_date.isoformat()
        }
    }, {"_id": 0}).to_list(10000)
    
    # Also check transactions directly (for payments not yet in payments collection)
    transactions = await db.transactions.find({
        **get_filter_for_user(current_user),
        "amount": {"$gt": 0},
        "matched_tenant_id": {"$ne": None},
        "transaction_date": {
            "$gte": start_date.isoformat(),
            "$lte": end_date.isoformat()
        }
    }, {"_id": 0}).to_list(10000)
    
    # Build set of tenants who paid
    paid_tenant_ids = set()
    payment_details = {}
    
    for p in payments:
        tenant_id = p.get("tenant_id")
        if tenant_id:
            paid_tenant_ids.add(tenant_id)
            payment_details[tenant_id] = {
                "amount": p.get("amount"),
                "date": p.get("payment_date"),
                "source": "payment"
            }
    
    for tx in transactions:
        tenant_id = tx.get("matched_tenant_id")
        if tenant_id and tenant_id not in paid_tenant_ids:
            paid_tenant_ids.add(tenant_id)
            payment_details[tenant_id] = {
                "amount": tx.get("amount"),
                "date": tx.get("transaction_date"),
                "source": "transaction"
            }
    
    # Build response
    month_names = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                   "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    
    paid_tenants = []
    unpaid_tenants = []
    
    for tenant in tenants:
        tenant_info = {
            "id": tenant["id"],
            "name": tenant["name"],
            "rent_amount": tenant.get("rent_amount", 0),
            "property_address": tenant.get("property_address", ""),
            "phone": tenant.get("phone", ""),
            "email": tenant.get("email", "")
        }
        
        if tenant["id"] in paid_tenant_ids:
            tenant_info["payment"] = payment_details.get(tenant["id"])
            paid_tenants.append(tenant_info)
        else:
            unpaid_tenants.append(tenant_info)
    
    # Sort by name
    paid_tenants.sort(key=lambda x: x["name"])
    unpaid_tenants.sort(key=lambda x: x["name"])
    
    total_expected = sum(t.get("rent_amount", 0) for t in tenants if t.get("rent_amount", 0) > 0)
    total_paid = sum(t.get("rent_amount", 0) for t in paid_tenants)
    
    return {
        "month": month,
        "month_name": month_names[month],
        "year": year,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "summary": {
            "total_tenants": len(tenants),
            "paid_count": len(paid_tenants),
            "unpaid_count": len(unpaid_tenants),
            "total_expected": total_expected,
            "total_paid": total_paid,
            "remaining": total_expected - total_paid
        },
        "paid_tenants": paid_tenants,
        "unpaid_tenants": unpaid_tenants
    }

@api_router.get("/payments/stats-by-structure")
async def get_payment_stats_by_structure(current_user: dict = Depends(get_current_user)):
    """
    Get current month payment statistics grouped by structure/building.
    Returns progress bars data for each structure.
    """
    from calendar import monthrange
    
    now = datetime.now(timezone.utc)
    month = now.month
    year = now.year
    
    # Calculate date range: 28th of previous month to 28th of current month
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
    
    start_date = datetime(prev_year, prev_month, 28, 0, 0, 0, tzinfo=timezone.utc)
    last_day = min(28, monthrange(year, month)[1])
    end_date = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    
    # Get all tenants
    tenants = await db.tenants.find(
        get_filter_for_user(current_user),
        {"_id": 0}
    ).to_list(1000)
    
    # Get all payments in the date range
    payments = await db.payments.find({
        **get_filter_for_user(current_user),
        "payment_date": {
            "$gte": start_date.isoformat(),
            "$lte": end_date.isoformat()
        }
    }, {"_id": 0}).to_list(10000)
    
    # Also check transactions
    transactions = await db.transactions.find({
        **get_filter_for_user(current_user),
        "amount": {"$gt": 0},
        "matched_tenant_id": {"$ne": None},
        "transaction_date": {
            "$gte": start_date.isoformat(),
            "$lte": end_date.isoformat()
        }
    }, {"_id": 0}).to_list(10000)
    
    # Build set of tenants who paid
    paid_tenant_ids = set()
    for p in payments:
        if p.get("tenant_id"):
            paid_tenant_ids.add(p["tenant_id"])
    for tx in transactions:
        if tx.get("matched_tenant_id"):
            paid_tenant_ids.add(tx["matched_tenant_id"])
    
    # Group by structure
    structures = {}
    unpaid_names = []
    
    for tenant in tenants:
        structure = tenant.get("structure", "Non défini") or "Non défini"
        
        if structure not in structures:
            structures[structure] = {
                "name": structure,
                "total": 0,
                "paid": 0,
                "unpaid": 0,
                "expected_amount": 0,
                "paid_amount": 0,
                "unpaid_tenants": []
            }
        
        structures[structure]["total"] += 1
        structures[structure]["expected_amount"] += tenant.get("rent_amount", 0)
        
        if tenant["id"] in paid_tenant_ids:
            structures[structure]["paid"] += 1
            structures[structure]["paid_amount"] += tenant.get("rent_amount", 0)
        else:
            structures[structure]["unpaid"] += 1
            structures[structure]["unpaid_tenants"].append({
                "name": tenant["name"],
                "rent_amount": tenant.get("rent_amount", 0)
            })
            unpaid_names.append(tenant["name"])
    
    # Calculate percentages
    for struct in structures.values():
        struct["percentage"] = round((struct["paid"] / struct["total"] * 100) if struct["total"] > 0 else 0, 1)
    
    # Overall stats
    total_tenants = len(tenants)
    total_paid = len(paid_tenant_ids)
    total_unpaid = total_tenants - total_paid
    overall_percentage = round((total_paid / total_tenants * 100) if total_tenants > 0 else 0, 1)
    
    return {
        "overall": {
            "total": total_tenants,
            "paid": total_paid,
            "unpaid": total_unpaid,
            "percentage": overall_percentage,
            "unpaid_names": unpaid_names
        },
        "by_structure": sorted(structures.values(), key=lambda x: x["name"])
    }


@api_router.get("/payments/available-months")
async def get_available_months(current_user: dict = Depends(get_current_user)):
    """Get list of months with payment data"""
    # Get earliest and latest payment dates
    earliest = await db.payments.find_one(
        get_filter_for_user(current_user),
        sort=[("payment_date", 1)]
    )
    latest = await db.payments.find_one(
        get_filter_for_user(current_user),
        sort=[("payment_date", -1)]
    )
    
    if not earliest or not latest:
        # Return current month if no data
        now = datetime.now(timezone.utc)
        return {"months": [{"month": now.month, "year": now.year}]}
    
    # Generate list of months between earliest and latest
    from dateutil.relativedelta import relativedelta
    
    start_date = datetime.fromisoformat(earliest["payment_date"].replace("Z", "+00:00"))
    end_date = datetime.fromisoformat(latest["payment_date"].replace("Z", "+00:00"))
    
    months = []
    current = datetime(start_date.year, start_date.month, 1)
    end = datetime(end_date.year, end_date.month, 1)
    
    while current <= end:
        months.append({"month": current.month, "year": current.year})
        current += relativedelta(months=1)
    
    # Add current month if not in list
    now = datetime.now(timezone.utc)
    if {"month": now.month, "year": now.year} not in months:
        months.append({"month": now.month, "year": now.year})
    
    return {"months": sorted(months, key=lambda x: (x["year"], x["month"]), reverse=True)}

# ==================== PAYMENTS ROUTES ====================

@api_router.post("/payments", response_model=PaymentResponse)
async def create_payment(payment_data: PaymentCreate, current_user: dict = Depends(get_current_user)):
    tenant = await db.tenants.find_one({"id": payment_data.tenant_id, **get_filter_for_user(current_user)})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    payment_id = str(uuid.uuid4())
    payment_doc = {
        "id": payment_id,
        **get_filter_for_user(current_user),
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
    query = get_filter_for_user(current_user)
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
    
    tenant = await db.tenants.find_one({"id": notification.tenant_id, **get_filter_for_user(current_user)})
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
            **get_filter_for_user(current_user),
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
    tenants = await db.tenants.find(get_filter_for_user(current_user), {"_id": 0}).to_list(1000)
    banks = await db.banks.find(get_filter_for_user(current_user), {"_id": 0}).to_list(100)
    
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
    settings = await db.user_settings.find_one(get_filter_for_user(current_user), {"_id": 0})
    if not settings:
        settings = {
            **get_filter_for_user(current_user),
            "notion_api_key": "",
            "notion_database_id": "",
            "twilio_configured": bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN),
            "enable_banking_configured": bool(ENABLE_BANKING_APP_ID and ENABLE_BANKING_PRIVATE_KEY)
        }
    else:
        settings["enable_banking_configured"] = bool(ENABLE_BANKING_APP_ID and ENABLE_BANKING_PRIVATE_KEY)
    return settings

class SettingsUpdate(BaseModel):
    notion_api_key: Optional[str] = None
    notion_database_id: Optional[str] = None

@api_router.put("/settings")
async def update_settings(settings_data: SettingsUpdate, current_user: dict = Depends(get_current_user)):
    update_data = {k: v for k, v in settings_data.model_dump().items() if v is not None}
    update_data["user_id"] = current_user["id"]
    
    await db.user_settings.update_one(
        get_filter_for_user(current_user),
        {"$set": update_data},
        upsert=True
    )
    return {"message": "Settings updated"}

# ==================== ENABLE BANKING ROUTES ====================

@api_router.get("/banking/aspsps")
async def get_available_banks(country: str = "FR", current_user: dict = Depends(get_current_user)):
    """Get list of available banks for a country"""
    try:
        eb_jwt = create_enable_banking_jwt()
        headers = {"Authorization": f"Bearer {eb_jwt}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.enablebanking.com/aspsps?country={country}",
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"Enable Banking API error: {error_text}")
                
                data = await response.json()
                return data.get("aspsps", [])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching banks: {str(e)}")

@api_router.post("/banking/connect")
async def connect_bank_account(
    bank_name: str,
    bank_country: str = "FR",
    current_user: dict = Depends(get_current_user)
):
    """Start bank connection authorization flow"""
    try:
        eb_jwt = create_enable_banking_jwt()
        headers = {
            "Authorization": f"Bearer {eb_jwt}",
            "Content-Type": "application/json"
        }
        
        # Generate unique state for this authorization
        state = str(uuid.uuid4())
        
        # Store state in database to verify callback
        await db.banking_auth_states.insert_one({
            "state": state,
            **get_filter_for_user(current_user),
            "bank_name": bank_name,
            "bank_country": bank_country,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        body = {
            "access": {
                "valid_until": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
            },
            "aspsp": {
                "name": bank_name,
                "country": bank_country
            },
            "state": state,
            "redirect_url": ENABLE_BANKING_REDIRECT_URL,
            "psu_type": "personal"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.enablebanking.com/auth",
                json=body,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"Enable Banking API error: {error_text}")
                
                data = await response.json()
                return {"auth_url": data.get("url"), "state": state}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initiating bank connection: {str(e)}")

@api_router.get("/banking/callback")
async def banking_callback(code: str = Query(...), state: str = Query(...)):
    """Handle callback from bank authorization"""
    try:
        # Verify state
        auth_state = await db.banking_auth_states.find_one({"state": state})
        if not auth_state:
            raise HTTPException(status_code=400, detail="Invalid state")
        
        user_id = auth_state["user_id"]
        bank_name = auth_state["bank_name"]
        bank_country = auth_state["bank_country"]
        
        eb_jwt = create_enable_banking_jwt()
        headers = {
            "Authorization": f"Bearer {eb_jwt}",
            "Content-Type": "application/json"
        }
        
        # Create session with the code
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.enablebanking.com/sessions",
                json={"code": code},
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    # Redirect to frontend with error
                    frontend_url = ENABLE_BANKING_REDIRECT_URL.replace("/api/banking/callback", "")
                    return RedirectResponse(url=f"{frontend_url}/banks?error=authorization_failed")
                
                session_data = await response.json()
                
                # Store connected bank session
                session_id = session_data.get("session_id")
                accounts = session_data.get("accounts", [])
                
                for account in accounts:
                    connected_bank_id = str(uuid.uuid4())
                    await db.connected_banks.insert_one({
                        "id": connected_bank_id,
                        "user_id": user_id,
                        "session_id": session_id,
                        "account_uid": account.get("uid"),
                        "account_iban": account.get("account_id", {}).get("iban", ""),
                        "bank_name": bank_name,
                        "bank_country": bank_country,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "valid_until": session_data.get("access", {}).get("valid_until", "")
                    })
                
                # Clean up state
                await db.banking_auth_states.delete_one({"state": state})
                
                # Redirect to frontend success
                frontend_url = ENABLE_BANKING_REDIRECT_URL.replace("/api/banking/callback", "")
                return RedirectResponse(url=f"{frontend_url}/banks?connected=true&accounts={len(accounts)}")
    
    except HTTPException:
        raise
    except Exception as e:
        frontend_url = ENABLE_BANKING_REDIRECT_URL.replace("/api/banking/callback", "") if ENABLE_BANKING_REDIRECT_URL else ""
        return RedirectResponse(url=f"{frontend_url}/banks?error={str(e)}")

@api_router.get("/banking/connected")
async def get_connected_banks(current_user: dict = Depends(get_current_user)):
    """Get list of connected bank accounts"""
    connected = await db.connected_banks.find(
        get_filter_for_user(current_user),
        {"_id": 0}
    ).to_list(100)
    return connected

@api_router.get("/banking/accounts/{account_uid}/balances")
async def get_account_balances(account_uid: str, current_user: dict = Depends(get_current_user)):
    """Get balances for a connected account"""
    # Verify account belongs to user
    connected = await db.connected_banks.find_one({
        "account_uid": account_uid,
        **get_filter_for_user(current_user)
    })
    if not connected:
        raise HTTPException(status_code=404, detail="Account not found")
    
    try:
        eb_jwt = create_enable_banking_jwt()
        headers = {"Authorization": f"Bearer {eb_jwt}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.enablebanking.com/accounts/{account_uid}/balances",
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"Error fetching balances: {error_text}")
                
                return await response.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@api_router.get("/banking/accounts/{account_uid}/transactions")
async def get_account_transactions(
    account_uid: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get transactions for a connected account"""
    # Verify account belongs to user
    connected = await db.connected_banks.find_one({
        "account_uid": account_uid,
        **get_filter_for_user(current_user)
    })
    if not connected:
        raise HTTPException(status_code=404, detail="Account not found")
    
    try:
        eb_jwt = create_enable_banking_jwt()
        headers = {"Authorization": f"Bearer {eb_jwt}"}
        
        url = f"https://api.enablebanking.com/accounts/{account_uid}/transactions"
        params = {}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"Error fetching transactions: {error_text}")
                
                data = await response.json()
                return data.get("transactions", [])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@api_router.post("/banking/sync-transactions/{account_uid}")
async def sync_bank_transactions(account_uid: str, bank_id: str, current_user: dict = Depends(get_current_user)):
    """Sync transactions from connected bank account to local bank"""
    # Verify connected account belongs to user
    connected = await db.connected_banks.find_one({
        "account_uid": account_uid,
        **get_filter_for_user(current_user)
    })
    if not connected:
        raise HTTPException(status_code=404, detail="Connected account not found")
    
    # Verify local bank belongs to user
    bank = await db.banks.find_one({"id": bank_id, **get_filter_for_user(current_user)})
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    
    try:
        eb_jwt = create_enable_banking_jwt()
        headers = {"Authorization": f"Bearer {eb_jwt}"}
        
        # Get transactions from last 30 days
        date_from = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.enablebanking.com/accounts/{account_uid}/transactions?date_from={date_from}",
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"Error fetching transactions: {error_text}")
                
                data = await response.json()
                transactions = data.get("transactions", [])
                
                imported_count = 0
                for tx in transactions:
                    # Check if transaction already exists (by reference)
                    tx_ref = tx.get("entry_reference") or tx.get("transaction_id", "")
                    existing = await db.transactions.find_one({
                        **get_filter_for_user(current_user),
                        "reference": tx_ref
                    })
                    
                    if not existing and tx_ref:
                        # Parse amount
                        amount_data = tx.get("transaction_amount", {})
                        amount = float(amount_data.get("amount", 0))
                        
                        # Determine if credit or debit
                        if tx.get("credit_debit_indicator") == "DBIT":
                            amount = -abs(amount)
                        else:
                            amount = abs(amount)
                        
                        # Parse date
                        tx_date = tx.get("booking_date") or tx.get("value_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
                        
                        # Create transaction
                        tx_id = str(uuid.uuid4())
                        tx_doc = {
                            "id": tx_id,
                            **get_filter_for_user(current_user),
                            "bank_id": bank_id,
                            "amount": amount,
                            "description": tx.get("remittance_information", ["Imported transaction"])[0] if tx.get("remittance_information") else "Imported transaction",
                            "transaction_date": f"{tx_date}T00:00:00Z",
                            "category": "rent" if amount > 0 else "expense",
                            "reference": tx_ref,
                            "matched_tenant_id": None,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "source": "enable_banking"
                        }
                        await db.transactions.insert_one(tx_doc)
                        imported_count += 1
                
                # Update bank balance with latest
                async with session.get(
                    f"https://api.enablebanking.com/accounts/{account_uid}/balances",
                    headers=headers
                ) as bal_response:
                    if bal_response.status == 200:
                        bal_data = await bal_response.json()
                        balances = bal_data.get("balances", [])
                        if balances:
                            # Get available or booked balance
                            for bal in balances:
                                if bal.get("balance_type") in ["closingAvailable", "interimAvailable", "closingBooked"]:
                                    new_balance = float(bal.get("balance_amount", {}).get("amount", 0))
                                    await db.banks.update_one(
                                        {"id": bank_id},
                                        {"$set": {"balance": new_balance}}
                                    )
                                    break
                
                return {"message": f"Imported {imported_count} new transactions", "count": imported_count}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing transactions: {str(e)}")

@api_router.delete("/banking/connected/{connected_id}")
async def disconnect_bank(connected_id: str, current_user: dict = Depends(get_current_user)):
    """Disconnect a bank account"""
    result = await db.connected_banks.delete_one({
        "id": connected_id,
        **get_filter_for_user(current_user)
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Connected bank not found")
    return {"message": "Bank disconnected"}

# ==================== ROOT ====================

@api_router.get("/")
async def root():
    return {"message": "Tenant Ledger API", "version": "1.0.0"}

# ==================== SCHEDULED TASKS ====================

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

async def scheduled_sync_and_match():
    """Scheduled task to sync bank transactions and auto-match payments"""
    logger.info("🔄 Starting scheduled sync and match...")
    
    try:
        # Get all users with connected banks
        users_with_banks = await db.connected_banks.distinct("user_id")
        
        for user_id in users_with_banks:
            user = await db.users.find_one({"id": user_id})
            if not user:
                continue
            
            logger.info(f"Processing user: {user.get('email', user_id)}")
            
            # Get connected banks for this user
            connected_banks = await db.connected_banks.find({"user_id": user_id}).to_list(100)
            local_banks = await db.banks.find({"user_id": user_id}).to_list(100)
            
            if not local_banks:
                continue
            
            # Use first local bank as default target
            default_bank_id = local_banks[0]["id"]
            
            for connected in connected_banks:
                account_uid = connected.get("account_uid")
                if not account_uid:
                    continue
                
                try:
                    # Create Enable Banking JWT
                    if not ENABLE_BANKING_APP_ID or not ENABLE_BANKING_PRIVATE_KEY:
                        continue
                    
                    from cryptography.hazmat.primitives import serialization
                    from cryptography.hazmat.backends import default_backend
                    
                    iat = int(datetime.now(timezone.utc).timestamp())
                    jwt_body = {
                        "iss": "enablebanking.com",
                        "aud": "api.enablebanking.com",
                        "iat": iat,
                        "exp": iat + 3600,
                    }
                    
                    if ENABLE_BANKING_PRIVATE_KEY.startswith("/") or ENABLE_BANKING_PRIVATE_KEY.endswith(".pem"):
                        with open(ENABLE_BANKING_PRIVATE_KEY, 'rb') as f:
                            key_data = f.read()
                    else:
                        key_data = ENABLE_BANKING_PRIVATE_KEY.encode('utf-8')
                    
                    private_key = serialization.load_pem_private_key(key_data, password=None, backend=default_backend())
                    eb_jwt = pyjwt.encode(jwt_body, private_key, algorithm="RS256", headers={"kid": ENABLE_BANKING_APP_ID})
                    
                    headers = {"Authorization": f"Bearer {eb_jwt}"}
                    
                    # Fetch transactions from last 15 days
                    date_from = (datetime.now(timezone.utc) - timedelta(days=15)).strftime("%Y-%m-%d")
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"https://api.enablebanking.com/accounts/{account_uid}/transactions?date_from={date_from}",
                            headers=headers
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                transactions = data.get("transactions", [])
                                
                                imported = 0
                                for tx in transactions:
                                    tx_ref = tx.get("entry_reference") or tx.get("transaction_id", "")
                                    
                                    # Check if already exists
                                    existing = await db.transactions.find_one({
                                        "user_id": user_id,
                                        "reference": tx_ref
                                    })
                                    
                                    if not existing and tx_ref:
                                        amount_data = tx.get("transaction_amount", {})
                                        amount = float(amount_data.get("amount", 0))
                                        
                                        if tx.get("credit_debit_indicator") == "DBIT":
                                            amount = -abs(amount)
                                        else:
                                            amount = abs(amount)
                                        
                                        tx_date = tx.get("booking_date") or tx.get("value_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
                                        
                                        tx_id = str(uuid.uuid4())
                                        await db.transactions.insert_one({
                                            "id": tx_id,
                                            "user_id": user_id,
                                            "bank_id": default_bank_id,
                                            "amount": amount,
                                            "description": tx.get("remittance_information", ["Imported"])[0] if tx.get("remittance_information") else "Imported",
                                            "transaction_date": f"{tx_date}T00:00:00Z",
                                            "category": "rent" if amount > 0 else "expense",
                                            "reference": tx_ref,
                                            "matched_tenant_id": None,
                                            "created_at": datetime.now(timezone.utc).isoformat(),
                                            "source": "scheduled_sync"
                                        })
                                        imported += 1
                                
                                logger.info(f"  Imported {imported} new transactions for {connected.get('bank_name')}")
                
                except Exception as e:
                    logger.error(f"  Error syncing {connected.get('bank_name')}: {str(e)}")
            
            # Now auto-match for this user
            tenants = await db.tenants.find({"user_id": user_id}).to_list(1000)
            unmatched_txs = await db.transactions.find({
                "user_id": user_id,
                "amount": {"$gt": 0},
                "matched_tenant_id": None
            }).to_list(1000)
            
            current_month = datetime.now(timezone.utc).strftime("%B")
            current_year = datetime.now(timezone.utc).year
            matched_count = 0
            
            for tx in unmatched_txs:
                desc = tx.get('description', '')
                amount = tx['amount']
                
                best_match = None
                best_score = 0
                
                for tenant in tenants:
                    rent = tenant.get('rent_amount', 0)
                    if rent > 0:
                        amount_diff = abs(amount - rent) / rent
                        if amount_diff < 0.15:
                            score = calculate_match_score(tenant['name'], desc)
                            if amount_diff < 0.01:
                                score += 5
                            if score > best_score and score >= 10:
                                best_score = score
                                best_match = tenant
                
                if best_match:
                    await db.transactions.update_one(
                        {"id": tx['id']},
                        {"$set": {"matched_tenant_id": best_match['id']}}
                    )
                    
                    existing = await db.payments.find_one({
                        "tenant_id": best_match['id'],
                        "month": current_month,
                        "year": current_year
                    })
                    
                    if not existing:
                        payment_id = str(uuid.uuid4())
                        tx_date = tx.get('transaction_date', datetime.now(timezone.utc).isoformat())
                        
                        await db.payments.insert_one({
                            "id": payment_id,
                            "user_id": user_id,
                            "tenant_id": best_match['id'],
                            "amount": amount,
                            "payment_date": tx_date,
                            "bank_id": tx['bank_id'],
                            "transaction_id": tx['id'],
                            "month": current_month,
                            "year": current_year,
                            "created_at": datetime.now(timezone.utc).isoformat()
                        })
                        
                        await db.tenants.update_one(
                            {"id": best_match['id']},
                            {"$set": {"payment_status": "paid", "last_payment_date": tx_date}}
                        )
                        matched_count += 1
            
            logger.info(f"  Auto-matched {matched_count} payments for {user.get('email')}")
        
        logger.info("✅ Scheduled sync and match completed")
    
    except Exception as e:
        logger.error(f"❌ Scheduled task error: {str(e)}")

# Schedule the task to run on the 1st, 10th, and 20th of each month at 8:00 AM
scheduler.add_job(
    scheduled_sync_and_match,
    CronTrigger(day='1,10,20', hour=8, minute=0),
    id='sync_and_match',
    replace_existing=True
)

# Also allow manual trigger via API
@api_router.post("/admin/run-sync")
async def manual_sync_trigger(current_user: dict = Depends(get_current_user)):
    """Manually trigger sync and match process"""
    await scheduled_sync_and_match()
    return {"message": "Sync and match completed"}

@api_router.post("/sync/manual")
async def manual_sync(current_user: dict = Depends(get_current_user)):
    """
    Manually trigger full synchronization:
    1. Sync tenants from Notion
    2. Sync transactions from all connected banks
    3. Run auto-matching algorithm
    """
    results = {
        "notion_sync": {"success": False, "count": 0, "error": None},
        "bank_sync": {"success": False, "count": 0, "error": None},
        "matching": {"success": False, "count": 0, "error": None}
    }
    
    # 1. Sync from Notion
    try:
        notion_result = await sync_from_notion(current_user)
        results["notion_sync"]["success"] = True
        results["notion_sync"]["count"] = notion_result.get("count", 0)
    except Exception as e:
        results["notion_sync"]["error"] = str(e)
        logger.error(f"Notion sync error: {e}")
    
    # 2. Sync transactions from connected banks
    try:
        connected_banks = await db.connected_banks.find(
            get_filter_for_user(current_user),
            {"_id": 0}
        ).to_list(100)
        
        total_transactions = 0
        for bank in connected_banks:
            try:
                # Fetch recent transactions (last 30 days)
                from_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
                tx_result = await sync_bank_transactions(bank["account_uid"], current_user, from_date=from_date)
                total_transactions += tx_result.get("new_count", 0)
            except Exception as e:
                logger.error(f"Error syncing bank {bank.get('name')}: {e}")
        
        results["bank_sync"]["success"] = True
        results["bank_sync"]["count"] = total_transactions
    except Exception as e:
        results["bank_sync"]["error"] = str(e)
        logger.error(f"Bank sync error: {e}")
    
    # 3. Run auto-matching
    try:
        match_result = await auto_match_transactions(current_user)
        results["matching"]["success"] = True
        results["matching"]["count"] = match_result.get("matched_count", 0)
    except Exception as e:
        results["matching"]["error"] = str(e)
        logger.error(f"Matching error: {e}")


# ==================== ORGANIZATION MIGRATION ====================

@api_router.post("/admin/migrate-to-organization")
async def migrate_to_organization(current_user: dict = Depends(get_current_user)):
    """
    One-time migration: Create CGR organization and migrate all data
    This will:
    1. Create organization "CGR"
    2. Add all 3 users as owners
    3. Migrate all existing data to organization
    """
    try:
        # Check if organization already exists
        existing_org = await db.organizations.find_one({"name": "CGR"})
        if existing_org:
            return {"message": "Organization CGR already exists", "organization_id": existing_org["id"]}
        
        # 1. Create organization
        org_id = str(uuid.uuid4())
        organization = {
            "id": org_id,
            "name": "CGR",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "owner_ids": []
        }
        await db.organizations.insert_one(organization)
        logger.info(f"Created organization CGR with id {org_id}")
        
        # 2. Get all 3 users
        users = await db.users.find({
            "email": {"$in": [
                "gaet.boone@gmail.com",
                "romain.m@cgrbank.com",
                "clement.h@cgrbank.com"
            ]}
        }, {"_id": 0}).to_list(10)
        
        # 3. Add all users as owners to the organization
        for user in users:
            member = {
                "id": str(uuid.uuid4()),
                "user_id": user["id"],
                "organization_id": org_id,
                "role": "owner",
                "joined_at": datetime.now(timezone.utc).isoformat()
            }
            await db.organization_members.insert_one(member)
            organization["owner_ids"].append(user["id"])
            logger.info(f"Added {user['email']} as owner to CGR")
        
        # Update organization with owner_ids
        await db.organizations.update_one(
            {"id": org_id},
            {"$set": {"owner_ids": organization["owner_ids"]}}
        )
        
        # 4. Migrate data - Find gaet's user_id (the one with data)
        gaet_user = next((u for u in users if u["email"] == "gaet.boone@gmail.com"), None)
        if not gaet_user:
            raise HTTPException(status_code=404, detail="Main user not found")
        
        gaet_id = gaet_user["id"]
        
        # 5. Update all collections to use organization_id
        collections_to_migrate = [
            "tenants", "banks", "transactions", "payments",
            "connected_banks", "matching_rules"
        ]
        
        migration_stats = {}
        for collection_name in collections_to_migrate:
            collection = db[collection_name]
            
            # Update documents from gaet's user_id to organization_id
            result = await collection.update_many(
                {"user_id": gaet_id},
                {"$set": {"organization_id": org_id}}
            )
            migration_stats[collection_name] = result.modified_count
            logger.info(f"Migrated {result.modified_count} documents in {collection_name}")
        
        return {
            "message": "Migration completed successfully",
            "organization": {
                "id": org_id,
                "name": "CGR",
                "owners": [u["email"] for u in users]
            },
            "migration_stats": migration_stats
        }
        
    except Exception as e:
        logger.error(f"Migration error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

    
    return {
        "message": "Synchronisation manuelle terminée",
        "results": results
    }


@api_router.get("/admin/scheduler-status")
async def get_scheduler_status(current_user: dict = Depends(get_current_user)):
    """Get scheduler status and next run times"""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None
        })
    return {"running": scheduler.running, "jobs": jobs}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Start the scheduler on app startup"""
    scheduler.start()
    logger.info("🚀 Scheduler started - will sync on 1st, 10th, 20th of each month at 8:00 AM")

@app.on_event("shutdown")
async def shutdown_db_client():
    scheduler.shutdown()
    client.close()
