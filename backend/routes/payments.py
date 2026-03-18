import uuid
from calendar import monthrange
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from ..core.database import db
from ..core.auth import get_current_user, get_filter_for_user
from ..models.schemas import PaymentCreate, PaymentResponse

router = APIRouter(prefix="/payments")

ACTIVE_STATUS_FILTER = {"$nin": ["resilié", "resilie", "terminated", "inactive"]}

MONTH_NAMES_FR = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]


def _get_date_range(month: int, year: int):
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year

    start_date = datetime(prev_year, prev_month, 28, 0, 0, 0, tzinfo=timezone.utc)
    last_day = min(28, monthrange(year, month)[1])
    end_date = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start_date, end_date


@router.post("", response_model=PaymentResponse)
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
        {"$set": {"payment_status": "paid", "last_payment_date": payment_data.payment_date.isoformat()}}
    )
    return PaymentResponse(**{**payment_doc, "payment_date": payment_data.payment_date, "created_at": datetime.now(timezone.utc)})


@router.get("", response_model=List[PaymentResponse])
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


@router.get("/monthly-status")
async def get_monthly_payment_status(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020, le=2100),
    current_user: dict = Depends(get_current_user)
):
    start_date, end_date = _get_date_range(month, year)

    tenants = await db.tenants.find(
        {**get_filter_for_user(current_user), "status": ACTIVE_STATUS_FILTER},
        {"_id": 0}
    ).to_list(1000)

    payments = await db.payments.find({
        **get_filter_for_user(current_user),
        "payment_date": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}
    }, {"_id": 0}).to_list(10000)

    transactions = await db.transactions.find({
        **get_filter_for_user(current_user),
        "amount": {"$gt": 0},
        "matched_tenant_id": {"$ne": None},
        "transaction_date": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}
    }, {"_id": 0}).to_list(10000)

    paid_tenant_ids = set()
    payment_details = {}

    for p in payments:
        tenant_id = p.get("tenant_id")
        if tenant_id:
            paid_tenant_ids.add(tenant_id)
            payment_details[tenant_id] = {"amount": p.get("amount"), "date": p.get("payment_date"), "source": "payment"}

    for tx in transactions:
        tenant_id = tx.get("matched_tenant_id")
        if tenant_id and tenant_id not in paid_tenant_ids:
            paid_tenant_ids.add(tenant_id)
            payment_details[tenant_id] = {"amount": tx.get("amount"), "date": tx.get("transaction_date"), "source": "transaction"}

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

    paid_tenants.sort(key=lambda x: x["name"])
    unpaid_tenants.sort(key=lambda x: x["name"])

    total_expected = sum(t.get("rent_amount", 0) for t in tenants if t.get("rent_amount", 0) > 0)
    total_paid = sum(t.get("rent_amount", 0) for t in paid_tenants)

    return {
        "month": month,
        "month_name": MONTH_NAMES_FR[month],
        "year": year,
        "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
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


@router.get("/stats-by-structure")
async def get_payment_stats_by_structure(current_user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    start_date, end_date = _get_date_range(now.month, now.year)

    tenants = await db.tenants.find(
        {**get_filter_for_user(current_user), "status": ACTIVE_STATUS_FILTER},
        {"_id": 0}
    ).to_list(1000)

    payments = await db.payments.find({
        **get_filter_for_user(current_user),
        "payment_date": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}
    }, {"_id": 0}).to_list(10000)

    transactions = await db.transactions.find({
        **get_filter_for_user(current_user),
        "amount": {"$gt": 0},
        "matched_tenant_id": {"$ne": None},
        "transaction_date": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}
    }, {"_id": 0}).to_list(10000)

    paid_tenant_ids = set()
    for p in payments:
        if p.get("tenant_id"):
            paid_tenant_ids.add(p["tenant_id"])
    for tx in transactions:
        if tx.get("matched_tenant_id"):
            paid_tenant_ids.add(tx["matched_tenant_id"])

    structures = {}
    unpaid_names = []

    for tenant in tenants:
        structure = tenant.get("structure", "Non défini") or "Non défini"
        if structure not in structures:
            structures[structure] = {"name": structure, "total": 0, "paid": 0, "unpaid": 0,
                                     "expected_amount": 0, "paid_amount": 0, "unpaid_tenants": []}

        structures[structure]["total"] += 1
        structures[structure]["expected_amount"] += tenant.get("rent_amount", 0)

        if tenant["id"] in paid_tenant_ids:
            structures[structure]["paid"] += 1
            structures[structure]["paid_amount"] += tenant.get("rent_amount", 0)
        else:
            structures[structure]["unpaid"] += 1
            structures[structure]["unpaid_tenants"].append({"name": tenant["name"], "rent_amount": tenant.get("rent_amount", 0)})
            unpaid_names.append(tenant["name"])

    for struct in structures.values():
        struct["percentage"] = round((struct["paid"] / struct["total"] * 100) if struct["total"] > 0 else 0, 1)

    total_tenants = len(tenants)
    total_paid = len(paid_tenant_ids)

    return {
        "overall": {
            "total": total_tenants,
            "paid": total_paid,
            "unpaid": total_tenants - total_paid,
            "percentage": round((total_paid / total_tenants * 100) if total_tenants > 0 else 0, 1),
            "unpaid_names": unpaid_names
        },
        "by_structure": sorted(structures.values(), key=lambda x: x["name"])
    }


@router.get("/available-months")
async def get_available_months(current_user: dict = Depends(get_current_user)):
    from dateutil.relativedelta import relativedelta

    earliest = await db.payments.find_one(get_filter_for_user(current_user), sort=[("payment_date", 1)])
    latest = await db.payments.find_one(get_filter_for_user(current_user), sort=[("payment_date", -1)])

    if not earliest or not latest:
        now = datetime.now(timezone.utc)
        return {"months": [{"month": now.month, "year": now.year}]}

    start_date = datetime.fromisoformat(earliest["payment_date"].replace("Z", "+00:00"))
    end_date = datetime.fromisoformat(latest["payment_date"].replace("Z", "+00:00"))

    months = []
    current = datetime(start_date.year, start_date.month, 1)
    end = datetime(end_date.year, end_date.month, 1)

    while current <= end:
        months.append({"month": current.month, "year": current.year})
        current += relativedelta(months=1)

    now = datetime.now(timezone.utc)
    if {"month": now.month, "year": now.year} not in months:
        months.append({"month": now.month, "year": now.year})

    return {"months": sorted(months, key=lambda x: (x["year"], x["month"]), reverse=True)}
