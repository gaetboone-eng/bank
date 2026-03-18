import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from core.database import db
from core.auth import get_current_user, get_filter_for_user
from models.schemas import TransactionCreate, TransactionResponse
from services.matching import calculate_match_score, extract_name_words, normalize_text, match_using_learned_rules
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/transactions")


@router.post("", response_model=TransactionResponse)
async def create_transaction(tx_data: TransactionCreate, current_user: dict = Depends(get_current_user)):
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
    await db.banks.update_one({"id": tx_data.bank_id}, {"$inc": {"balance": tx_data.amount}})

    return TransactionResponse(**{**tx_doc, "transaction_date": tx_data.transaction_date, "created_at": datetime.now(timezone.utc)})


@router.get("", response_model=List[TransactionResponse])
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


@router.post("/{tx_id}/match/{tenant_id}")
async def match_transaction_to_tenant(tx_id: str, tenant_id: str, current_user: dict = Depends(get_current_user)):
    tx = await db.transactions.find_one({"id": tx_id, **get_filter_for_user(current_user)})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tenant = await db.tenants.find_one({"id": tenant_id, **get_filter_for_user(current_user)})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    await db.transactions.update_one({"id": tx_id}, {"$set": {"matched_tenant_id": tenant_id}})

    # Save matching rule
    description = tx.get("description", "")
    keywords = extract_name_words(description)
    keyword_pattern = " ".join(keywords[:5])

    existing_rule = await db.matching_rules.find_one({
        **get_filter_for_user(current_user),
        "tenant_id": tenant_id,
        "pattern": keyword_pattern
    })

    if not existing_rule and keyword_pattern:
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
    elif existing_rule:
        await db.matching_rules.update_one({"id": existing_rule["id"]}, {"$inc": {"match_count": 1}})

    # Create payment record
    tx_date = datetime.fromisoformat(tx["transaction_date"]) if isinstance(tx["transaction_date"], str) else tx["transaction_date"]
    payment_id = str(uuid.uuid4())
    await db.payments.insert_one({
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
    })

    await db.tenants.update_one(
        {"id": tenant_id},
        {"$set": {"payment_status": "paid", "last_payment_date": tx["transaction_date"]}}
    )

    return {"message": "Transaction matched to tenant", "payment_id": payment_id, "rule_saved": bool(keyword_pattern)}


@router.post("/auto-match")
async def auto_match_transactions(current_user: dict = Depends(get_current_user)):
    tenants = await db.tenants.find(get_filter_for_user(current_user), {"_id": 0}).to_list(1000)
    tenants_dict = {t["id"]: t for t in tenants}

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

        learned_rule, rule_score = await match_using_learned_rules(current_user["id"], desc, amount)
        if learned_rule and learned_rule["tenant_id"] in tenants_dict:
            best_match = tenants_dict[learned_rule["tenant_id"]]
            best_score = rule_score
            match_source = "learned_rule"

        if not best_match:
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
                            match_source = "name"

        if best_match:
            await db.transactions.update_one({"id": tx['id']}, {"$set": {"matched_tenant_id": best_match['id']}})

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
                await db.tenants.update_one(
                    {"id": best_match['id']},
                    {"$set": {"payment_status": "paid", "last_payment_date": tx_date}}
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


@router.get("/matching-rules")
async def get_matching_rules(current_user: dict = Depends(get_current_user)):
    rules = await db.matching_rules.find(
        get_filter_for_user(current_user), {"_id": 0}
    ).sort("match_count", -1).to_list(1000)
    return rules


@router.delete("/matching-rules/{rule_id}")
async def delete_matching_rule(rule_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.matching_rules.delete_one({"id": rule_id, **get_filter_for_user(current_user)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted"}
