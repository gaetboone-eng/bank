import uuid
import aiohttp
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from ..core.database import db
from ..core.auth import get_current_user, get_filter_for_user
from ..core.config import NOTION_API_KEY, NOTION_DATABASE_ID
from ..models.schemas import TenantCreate, TenantUpdate, TenantResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tenants")


def _parse_tenant_dates(tenant: dict) -> dict:
    if isinstance(tenant.get("created_at"), str):
        tenant["created_at"] = datetime.fromisoformat(tenant["created_at"])
    if tenant.get("last_payment_date") and isinstance(tenant["last_payment_date"], str):
        tenant["last_payment_date"] = datetime.fromisoformat(tenant["last_payment_date"])
    return tenant


@router.post("", response_model=TenantResponse)
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


@router.get("", response_model=List[TenantResponse])
async def get_tenants(current_user: dict = Depends(get_current_user), include_resilié: bool = False):
    filter_query = get_filter_for_user(current_user)
    if not include_resilié:
        filter_query = {**filter_query, "status": {"$nin": ["resilié", "resilie", "terminated", "inactive"]}}
    tenants = await db.tenants.find(filter_query, {"_id": 0}).to_list(1000)

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
        result.append(TenantResponse(**_parse_tenant_dates(tenant)))
    return result


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str, current_user: dict = Depends(get_current_user)):
    tenant = await db.tenants.find_one({"id": tenant_id, **get_filter_for_user(current_user)}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse(**_parse_tenant_dates(tenant))


@router.put("/{tenant_id}", response_model=TenantResponse)
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
    return TenantResponse(**_parse_tenant_dates(result))


@router.delete("/{tenant_id}")
async def delete_tenant(tenant_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.tenants.delete_one({"id": tenant_id, **get_filter_for_user(current_user)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"message": "Tenant deleted"}


@router.post("/sync-notion")
async def sync_from_notion(current_user: dict = Depends(get_current_user)):
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        raise HTTPException(status_code=400, detail="Notion API not configured.")

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
                notion_ids_seen = set()

                for page in results:
                    props = page.get("properties", {})

                    name = ""
                    if "Name" in props and props["Name"].get("title"):
                        name = props["Name"]["title"][0]["plain_text"] if props["Name"]["title"] else ""

                    email = props.get("Email", {}).get("email", "")
                    phone = props.get("Phone", {}).get("phone_number", "")

                    address = ""
                    if "Address" in props and props["Address"].get("rich_text"):
                        address = props["Address"]["rich_text"][0]["plain_text"] if props["Address"]["rich_text"] else ""

                    structure = ""
                    for field in ["Structure", "Bâtiment", "Building"]:
                        if field in props:
                            if props[field].get("rich_text"):
                                structure = props[field]["rich_text"][0]["plain_text"] if props[field]["rich_text"] else ""
                                break
                            elif props[field].get("select"):
                                structure = props[field]["select"]["name"] if props[field]["select"] else ""
                                break

                    rent = (props.get("Loyer Mensuel", {}).get("number", 0)
                            or props.get("Rent", {}).get("number", 0)
                            or props.get("Rent Amount", {}).get("number", 0) or 0)
                    due_day = props.get("Due Day", {}).get("number", 1) or 1

                    status_raw = ""
                    for status_field in ["Statut", "Status", "Etat"]:
                        if status_field in props:
                            sel = props[status_field].get("select")
                            if sel:
                                status_raw = sel.get("name", "").lower()
                                break

                    if status_raw in ["résilié", "resilié", "resilie", "terminated", "inactif", "inactive"]:
                        status = "resilié"
                    elif status_raw in ["actif", "active", "en cours"]:
                        status = "actif"
                    else:
                        status = None

                    if name:
                        notion_ids_seen.add(page["id"])
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
                            "notion_id": page["id"],
                        }
                        if status is not None:
                            tenant_data["status"] = status

                        if existing:
                            await db.tenants.update_one({"id": existing["id"]}, {"$set": tenant_data})
                        else:
                            await db.tenants.insert_one({
                                "id": str(uuid.uuid4()),
                                **get_filter_for_user(current_user),
                                **tenant_data,
                                "created_at": datetime.now(timezone.utc).isoformat(),
                                "payment_status": "pending",
                                "last_payment_date": None
                            })
                        synced_count += 1

                # Mark tenants removed from Notion as resilié
                deactivated_count = 0
                if notion_ids_seen:
                    db_tenants = await db.tenants.find(
                        {**get_filter_for_user(current_user), "notion_id": {"$exists": True, "$ne": None}},
                        {"_id": 0, "id": 1, "notion_id": 1, "name": 1, "status": 1}
                    ).to_list(1000)
                    for t in db_tenants:
                        if t.get("notion_id") and t["notion_id"] not in notion_ids_seen:
                            if t.get("status") != "resilié":
                                await db.tenants.update_one({"id": t["id"]}, {"$set": {"status": "resilié"}})
                                deactivated_count += 1

                return {"message": f"Synced {synced_count} tenants from Notion", "count": synced_count, "deactivated": deactivated_count}

    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")
