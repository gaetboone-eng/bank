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
        return user
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

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
                    
                    rent = props.get("Loyer Mensuel", {}).get("number", 0) or props.get("Rent", {}).get("number", 0) or props.get("Rent Amount", {}).get("number", 0) or 0
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

@api_router.post("/transactions/auto-match")
async def auto_match_transactions(current_user: dict = Depends(get_current_user)):
    """Automatically match unmatched transactions with tenants based on name and amount"""
    
    # Get all tenants
    tenants = await db.tenants.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(1000)
    
    # Get unmatched positive transactions (incoming payments)
    transactions = await db.transactions.find({
        "user_id": current_user["id"],
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
                    "user_id": current_user["id"],
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
                    "score": best_score
                })
    
    return {
        "message": f"Auto-matched {len(matches)} transactions",
        "matches": matches
    }

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
        {"user_id": current_user["id"]},
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
            "user_id": current_user["id"],
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
        {"user_id": current_user["id"]},
        {"_id": 0}
    ).to_list(100)
    return connected

@api_router.get("/banking/accounts/{account_uid}/balances")
async def get_account_balances(account_uid: str, current_user: dict = Depends(get_current_user)):
    """Get balances for a connected account"""
    # Verify account belongs to user
    connected = await db.connected_banks.find_one({
        "account_uid": account_uid,
        "user_id": current_user["id"]
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
        "user_id": current_user["id"]
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
        "user_id": current_user["id"]
    })
    if not connected:
        raise HTTPException(status_code=404, detail="Connected account not found")
    
    # Verify local bank belongs to user
    bank = await db.banks.find_one({"id": bank_id, "user_id": current_user["id"]})
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
                        "user_id": current_user["id"],
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
                            "user_id": current_user["id"],
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
        "user_id": current_user["id"]
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Connected bank not found")
    return {"message": "Bank disconnected"}

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
