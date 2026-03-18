import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from core.database import db
from core.auth import get_current_user, get_filter_for_user
from models.schemas import BankCreate, BankUpdate, BankResponse

router = APIRouter(prefix="/banks")


@router.post("", response_model=BankResponse)
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
    if current_user.get("organization_id"):
        bank_doc["organization_id"] = current_user["organization_id"]

    await db.banks.insert_one(bank_doc)
    return BankResponse(**{**bank_doc, "created_at": datetime.now(timezone.utc)})


@router.get("", response_model=List[BankResponse])
async def get_banks(current_user: dict = Depends(get_current_user)):
    banks = await db.banks.find(get_filter_for_user(current_user), {"_id": 0}).to_list(100)
    result = []
    for bank in banks:
        if isinstance(bank.get("created_at"), str):
            bank["created_at"] = datetime.fromisoformat(bank["created_at"])
        result.append(BankResponse(**bank))
    return result


@router.put("/{bank_id}", response_model=BankResponse)
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


@router.delete("/{bank_id}")
async def delete_bank(bank_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.banks.delete_one({"id": bank_id, **get_filter_for_user(current_user)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bank not found")
    return {"message": "Bank deleted"}
