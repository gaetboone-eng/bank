import uuid
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ..core.database import db
from ..core.auth import get_current_user, get_filter_for_user
from ..core.config import ENABLE_BANKING_APP_ID, ENABLE_BANKING_PRIVATE_KEY
from ..services.matching import calculate_match_score

logger = logging.getLogger(__name__)
router = APIRouter()

scheduler = AsyncIOScheduler()


async def scheduled_sync_and_match():
    logger.info("🔄 Starting scheduled sync and match...")
    try:
        users_with_banks = await db.connected_banks.distinct("user_id")

        for user_id in users_with_banks:
            user = await db.users.find_one({"id": user_id})
            if not user:
                continue

            connected_banks = await db.connected_banks.find({"user_id": user_id}).to_list(100)
            local_banks = await db.banks.find({"user_id": user_id}).to_list(100)

            if not local_banks:
                continue

            default_bank_id = local_banks[0]["id"]

            for connected in connected_banks:
                account_uid = connected.get("account_uid")
                if not account_uid:
                    continue
                if not ENABLE_BANKING_APP_ID or not ENABLE_BANKING_PRIVATE_KEY:
                    continue

                try:
                    import aiohttp
                    import jwt as pyjwt
                    from cryptography.hazmat.primitives import serialization
                    from cryptography.hazmat.backends import default_backend

                    iat = int(datetime.now(timezone.utc).timestamp())
                    jwt_body = {"iss": "enablebanking.com", "aud": "api.enablebanking.com", "iat": iat, "exp": iat + 3600}

                    key_data = open(ENABLE_BANKING_PRIVATE_KEY, 'rb').read() if (
                        ENABLE_BANKING_PRIVATE_KEY.startswith("/") or ENABLE_BANKING_PRIVATE_KEY.endswith(".pem")
                    ) else ENABLE_BANKING_PRIVATE_KEY.encode('utf-8')

                    private_key = serialization.load_pem_private_key(key_data, password=None, backend=default_backend())
                    eb_jwt = pyjwt.encode(jwt_body, private_key, algorithm="RS256", headers={"kid": ENABLE_BANKING_APP_ID})
                    headers = {"Authorization": f"Bearer {eb_jwt}"}

                    date_from = (datetime.now(timezone.utc) - timedelta(days=15)).strftime("%Y-%m-%d")

                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"https://api.enablebanking.com/accounts/{account_uid}/transactions?date_from={date_from}",
                            headers=headers
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                imported = 0
                                for tx in data.get("transactions", []):
                                    tx_ref = tx.get("entry_reference") or tx.get("transaction_id", "")
                                    existing = await db.transactions.find_one({"user_id": user_id, "reference": tx_ref})
                                    if not existing and tx_ref:
                                        amount_data = tx.get("transaction_amount", {})
                                        amount = float(amount_data.get("amount", 0))
                                        if tx.get("credit_debit_indicator") == "DBIT":
                                            amount = -abs(amount)
                                        else:
                                            amount = abs(amount)
                                        tx_date = tx.get("booking_date") or tx.get("value_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
                                        await db.transactions.insert_one({
                                            "id": str(uuid.uuid4()),
                                            "user_id": user_id,
                                            "bank_id": default_bank_id,
                                            "amount": amount,
                                            "description": " | ".join(tx.get("remittance_information", ["Imported"])) if tx.get("remittance_information") else "Imported",
                                            "transaction_date": f"{tx_date}T00:00:00Z",
                                            "category": "rent" if amount > 0 else "expense",
                                            "reference": tx_ref,
                                            "matched_tenant_id": None,
                                            "created_at": datetime.now(timezone.utc).isoformat(),
                                            "source": "scheduled_sync"
                                        })
                                        imported += 1
                                logger.info(f"  Imported {imported} transactions for {connected.get('bank_name')}")

                except Exception as e:
                    logger.error(f"  Error syncing {connected.get('bank_name')}: {str(e)}")

            # Auto-match for this user
            tenants = await db.tenants.find({"user_id": user_id}).to_list(1000)
            unmatched_txs = await db.transactions.find({"user_id": user_id, "amount": {"$gt": 0}, "matched_tenant_id": None}).to_list(1000)

            current_month = datetime.now(timezone.utc).strftime("%B")
            current_year = datetime.now(timezone.utc).year
            matched_count = 0

            for tx in unmatched_txs:
                best_match, best_score = None, 0
                for tenant in tenants:
                    rent = tenant.get('rent_amount', 0)
                    if rent > 0:
                        amount_diff = abs(tx['amount'] - rent) / rent
                        if amount_diff < 0.15:
                            score = calculate_match_score(tenant['name'], tx.get('description', ''))
                            if amount_diff < 0.01:
                                score += 5
                            if score > best_score and score >= 10:
                                best_score = score
                                best_match = tenant

                if best_match:
                    await db.transactions.update_one({"id": tx['id']}, {"$set": {"matched_tenant_id": best_match['id']}})
                    existing = await db.payments.find_one({"tenant_id": best_match['id'], "month": current_month, "year": current_year})
                    if not existing:
                        tx_date = tx.get('transaction_date', datetime.now(timezone.utc).isoformat())
                        await db.payments.insert_one({
                            "id": str(uuid.uuid4()),
                            "user_id": user_id,
                            "tenant_id": best_match['id'],
                            "amount": tx['amount'],
                            "payment_date": tx_date,
                            "bank_id": tx['bank_id'],
                            "transaction_id": tx['id'],
                            "month": current_month,
                            "year": current_year,
                            "created_at": datetime.now(timezone.utc).isoformat()
                        })
                        await db.tenants.update_one({"id": best_match['id']}, {"$set": {"payment_status": "paid", "last_payment_date": tx_date}})
                        matched_count += 1

            logger.info(f"  Auto-matched {matched_count} payments for {user.get('email')}")

        logger.info("✅ Scheduled sync and match completed")

    except Exception as e:
        logger.error(f"❌ Scheduled task error: {str(e)}")


# Schedule: 1st, 10th, 20th of each month at 8:00 AM
scheduler.add_job(
    scheduled_sync_and_match,
    CronTrigger(day='1,10,20', hour=8, minute=0),
    id='sync_and_match',
    replace_existing=True
)


@router.post("/sync/manual")
async def manual_sync(current_user: dict = Depends(get_current_user)):
    from .tenants import sync_from_notion
    from .transactions import auto_match_transactions
    from .banking import sync_bank_transactions

    results = {
        "notion_sync": {"success": False, "count": 0, "error": None},
        "bank_sync": {"success": False, "count": 0, "error": None},
        "matching": {"success": False, "count": 0, "error": None}
    }

    try:
        notion_result = await sync_from_notion(current_user)
        results["notion_sync"]["success"] = True
        results["notion_sync"]["count"] = notion_result.get("count", 0)
    except Exception as e:
        results["notion_sync"]["error"] = str(e)

    try:
        connected_banks = await db.connected_banks.find(get_filter_for_user(current_user), {"_id": 0}).to_list(100)
        total_transactions = 0
        for bank in connected_banks:
            try:
                connected_iban = bank.get("account_iban", "").replace(" ", "")
                all_local_banks = await db.banks.find(get_filter_for_user(current_user), {"_id": 0}).to_list(100)
                bank_doc = next((b for b in all_local_banks if b.get("iban", "").replace(" ", "") == connected_iban), None)
                if not bank_doc and all_local_banks:
                    bank_doc = all_local_banks[0]
                if bank_doc:
                    tx_result = await sync_bank_transactions(bank["account_uid"], bank_doc["id"], current_user)
                    total_transactions += tx_result.get("count", 0)
            except Exception as e:
                logger.error(f"Error syncing bank {bank.get('bank_name')}: {e}")
        results["bank_sync"]["success"] = True
        results["bank_sync"]["count"] = total_transactions
    except Exception as e:
        results["bank_sync"]["error"] = str(e)

    try:
        match_result = await auto_match_transactions(current_user)
        results["matching"]["success"] = True
        results["matching"]["count"] = len(match_result.get("matches", []))
    except Exception as e:
        results["matching"]["error"] = str(e)

    return {"message": "Synchronisation manuelle terminée", "results": results}


@router.post("/admin/run-sync")
async def manual_sync_trigger(current_user: dict = Depends(get_current_user)):
    await scheduled_sync_and_match()
    return {"message": "Sync and match completed"}


@router.get("/admin/scheduler-status")
async def get_scheduler_status(current_user: dict = Depends(get_current_user)):
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({"id": job.id, "next_run": job.next_run_time.isoformat() if job.next_run_time else None})
    return {"running": scheduler.running, "jobs": jobs}


@router.post("/admin/migrate-to-organization")
async def migrate_to_organization(current_user: dict = Depends(get_current_user)):
    existing_org = await db.organizations.find_one({"name": "CGR"})
    if existing_org:
        return {"message": "Organization CGR already exists", "organization_id": existing_org["id"]}

    org_id = str(uuid.uuid4())
    organization = {"id": org_id, "name": "CGR", "created_at": datetime.now(timezone.utc).isoformat(), "owner_ids": []}
    await db.organizations.insert_one(organization)

    users = await db.users.find({
        "email": {"$in": ["gaet.boone@gmail.com", "romain.m@cgrbank.com", "clement.h@cgrbank.com"]}
    }, {"_id": 0}).to_list(10)

    for user in users:
        await db.organization_members.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "organization_id": org_id,
            "role": "owner",
            "joined_at": datetime.now(timezone.utc).isoformat()
        })
        organization["owner_ids"].append(user["id"])

    await db.organizations.update_one({"id": org_id}, {"$set": {"owner_ids": organization["owner_ids"]}})

    gaet_user = next((u for u in users if u["email"] == "gaet.boone@gmail.com"), None)
    if not gaet_user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Main user not found")

    collections_to_migrate = ["tenants", "banks", "transactions", "payments", "connected_banks", "matching_rules"]
    migration_stats = {}
    for collection_name in collections_to_migrate:
        result = await db[collection_name].update_many({"user_id": gaet_user["id"]}, {"$set": {"organization_id": org_id}})
        migration_stats[collection_name] = result.modified_count

    return {
        "message": "Migration completed successfully",
        "organization": {"id": org_id, "name": "CGR", "owners": [u["email"] for u in users]},
        "migration_stats": migration_stats
    }
