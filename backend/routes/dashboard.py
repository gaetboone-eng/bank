from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from ..core.database import db
from ..core.auth import get_current_user, get_filter_for_user
from ..core.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, ENABLE_BANKING_APP_ID, ENABLE_BANKING_PRIVATE_KEY
from ..models.schemas import DashboardStats, SettingsUpdate

router = APIRouter()

ACTIVE_STATUS_FILTER = {"$nin": ["resilié", "resilie", "terminated", "inactive"]}


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    all_tenants = await db.tenants.find(get_filter_for_user(current_user), {"_id": 0}).to_list(1000)
    tenants = [t for t in all_tenants if t.get("status", "").lower() not in ["resilié", "resilie", "terminated", "inactive"]]
    banks = await db.banks.find(get_filter_for_user(current_user), {"_id": 0}).to_list(100)

    current_month = datetime.now(timezone.utc).strftime("%B")
    current_year = datetime.now(timezone.utc).year

    total_rent_expected = sum(t.get("rent_amount", 0) for t in tenants)
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


@router.get("/dashboard/monthly-history")
async def get_monthly_history(current_user: dict = Depends(get_current_user)):
    from dateutil.relativedelta import relativedelta

    active_tenants = await db.tenants.find(
        {**get_filter_for_user(current_user), "status": ACTIVE_STATUS_FILTER},
        {"_id": 0, "id": 1}
    ).to_list(1000)
    active_ids = {t["id"] for t in active_tenants}
    total_active = len(active_ids)

    month_names_fr = {1: "Jan", 2: "Fév", 3: "Mar", 4: "Avr", 5: "Mai", 6: "Jun",
                      7: "Jul", 8: "Aoû", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Déc"}
    month_names_en = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May",
                      6: "June", 7: "July", 8: "August", 9: "September", 10: "October",
                      11: "November", 12: "December"}

    history = []
    now = datetime.now(timezone.utc)

    for i in range(5, -1, -1):
        target = now - relativedelta(months=i)
        m, y = target.month, target.year
        paid_ids = await db.payments.distinct(
            "tenant_id",
            {"month": month_names_en[m], "year": y, "tenant_id": {"$in": list(active_ids)}}
        )
        paid = len(paid_ids)
        history.append({
            "month": month_names_fr[m],
            "year": y,
            "label": f"{month_names_fr[m]} {str(y)[2:]}",
            "paid": paid,
            "total": total_active,
            "unpaid": total_active - paid,
            "percentage": round((paid / total_active * 100), 1) if total_active > 0 else 0
        })

    return {"history": history}


@router.get("/settings")
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


@router.put("/settings")
async def update_settings(settings_data: SettingsUpdate, current_user: dict = Depends(get_current_user)):
    update_data = {k: v for k, v in settings_data.model_dump().items() if v is not None}
    update_data["user_id"] = current_user["id"]
    await db.user_settings.update_one(
        get_filter_for_user(current_user),
        {"$set": update_data},
        upsert=True
    )
    return {"message": "Settings updated"}
