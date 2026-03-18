import uuid
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from ..core.database import db
from ..core.auth import get_current_user, get_filter_for_user
from ..core.config import ENABLE_BANKING_REDIRECT_URL
from ..services.enable_banking import create_enable_banking_jwt
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/banking")


@router.get("/aspsps")
async def get_available_banks(country: str = "FR", current_user: dict = Depends(get_current_user)):
    try:
        eb_jwt = create_enable_banking_jwt()
        headers = {"Authorization": f"Bearer {eb_jwt}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.enablebanking.com/aspsps?country={country}", headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"Enable Banking API error: {error_text}")
                data = await response.json()
                return data.get("aspsps", [])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching banks: {str(e)}")


@router.post("/connect")
async def connect_bank_account(bank_name: str, bank_country: str = "FR", current_user: dict = Depends(get_current_user)):
    try:
        eb_jwt = create_enable_banking_jwt()
        headers = {"Authorization": f"Bearer {eb_jwt}", "Content-Type": "application/json"}
        state = str(uuid.uuid4())

        auth_state_doc = {
            "state": state,
            "user_id": current_user["id"],
            "bank_name": bank_name,
            "bank_country": bank_country,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        if current_user.get("organization_id"):
            auth_state_doc["organization_id"] = current_user["organization_id"]
        await db.banking_auth_states.insert_one(auth_state_doc)

        body = {
            "access": {"valid_until": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()},
            "aspsp": {"name": bank_name, "country": bank_country},
            "state": state,
            "redirect_url": ENABLE_BANKING_REDIRECT_URL,
            "psu_type": "personal"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.enablebanking.com/auth", json=body, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"Enable Banking API error: {error_text}")
                data = await response.json()
                return {"auth_url": data.get("url"), "state": state}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initiating bank connection: {str(e)}")


@router.get("/callback")
async def banking_callback(code: str = Query(...), state: str = Query(...)):
    frontend_url = ENABLE_BANKING_REDIRECT_URL.replace("/api/banking/callback", "") if ENABLE_BANKING_REDIRECT_URL else ""
    try:
        auth_state = await db.banking_auth_states.find_one({"state": state})
        if not auth_state:
            return RedirectResponse(url=f"{frontend_url}/banks?error=session_invalide_veuillez_recommencer")

        user_id = auth_state.get("user_id")
        if not user_id:
            return RedirectResponse(url=f"{frontend_url}/banks?error=session_expiree_veuillez_reconnectez_vous")

        organization_id = auth_state.get("organization_id")
        bank_name = auth_state["bank_name"]
        bank_country = auth_state["bank_country"]

        eb_jwt = create_enable_banking_jwt()
        headers = {"Authorization": f"Bearer {eb_jwt}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.enablebanking.com/sessions", json={"code": code}, headers=headers) as response:
                if response.status != 200:
                    await db.banking_auth_states.delete_one({"state": state})
                    return RedirectResponse(url=f"{frontend_url}/banks?error=authorization_failed")

                session_data = await response.json()
                session_id = session_data.get("session_id")
                accounts = session_data.get("accounts", [])

                for account in accounts:
                    connected_bank_doc = {
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "session_id": session_id,
                        "account_uid": account.get("uid"),
                        "account_iban": account.get("account_id", {}).get("iban", ""),
                        "bank_name": bank_name,
                        "bank_country": bank_country,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "valid_until": session_data.get("access", {}).get("valid_until", "")
                    }
                    if organization_id:
                        connected_bank_doc["organization_id"] = organization_id
                    await db.connected_banks.insert_one(connected_bank_doc)

                await db.banking_auth_states.delete_one({"state": state})
                return RedirectResponse(url=f"{frontend_url}/banks?connected=true&accounts={len(accounts)}")

    except Exception as e:
        logger.error(f"Banking callback error: {str(e)}")
        return RedirectResponse(url=f"{frontend_url}/banks?error={str(e)}")


@router.get("/connected")
async def get_connected_banks(current_user: dict = Depends(get_current_user)):
    connected = await db.connected_banks.find(get_filter_for_user(current_user), {"_id": 0}).to_list(100)
    return connected


@router.get("/accounts/{account_uid}/balances")
async def get_account_balances(account_uid: str, current_user: dict = Depends(get_current_user)):
    connected = await db.connected_banks.find_one({"account_uid": account_uid, **get_filter_for_user(current_user)})
    if not connected:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        eb_jwt = create_enable_banking_jwt()
        headers = {"Authorization": f"Bearer {eb_jwt}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.enablebanking.com/accounts/{account_uid}/balances", headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"Error fetching balances: {error_text}")
                return await response.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/accounts/{account_uid}/transactions")
async def get_account_transactions(
    account_uid: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    connected = await db.connected_banks.find_one({"account_uid": account_uid, **get_filter_for_user(current_user)})
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


@router.post("/sync-transactions/{account_uid}")
async def sync_bank_transactions(account_uid: str, bank_id: str, current_user: dict = Depends(get_current_user)):
    connected = await db.connected_banks.find_one({"account_uid": account_uid, **get_filter_for_user(current_user)})
    if not connected:
        raise HTTPException(status_code=404, detail="Connected account not found")

    bank = await db.banks.find_one({"id": bank_id, **get_filter_for_user(current_user)})
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")

    try:
        eb_jwt = create_enable_banking_jwt()
        headers = {"Authorization": f"Bearer {eb_jwt}"}
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
                    tx_ref = tx.get("entry_reference") or tx.get("transaction_id", "")
                    existing = await db.transactions.find_one({**get_filter_for_user(current_user), "reference": tx_ref})

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
                            **get_filter_for_user(current_user),
                            "bank_id": bank_id,
                            "amount": amount,
                            "description": " | ".join(tx.get("remittance_information", ["Imported transaction"])) if tx.get("remittance_information") else "Imported transaction",
                            "transaction_date": f"{tx_date}T00:00:00Z",
                            "category": "rent" if amount > 0 else "expense",
                            "reference": tx_ref,
                            "matched_tenant_id": None,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "source": "enable_banking"
                        })
                        imported_count += 1

            # Update balance
            async with session.get(f"https://api.enablebanking.com/accounts/{account_uid}/balances", headers=headers) as bal_response:
                if bal_response.status == 200:
                    bal_data = await bal_response.json()
                    for bal in bal_data.get("balances", []):
                        if bal.get("balance_type") in ["closingAvailable", "interimAvailable", "closingBooked"]:
                            new_balance = float(bal.get("balance_amount", {}).get("amount", 0))
                            await db.banks.update_one({"id": bank_id}, {"$set": {"balance": new_balance}})
                            break

            return {"message": f"Imported {imported_count} new transactions", "count": imported_count}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing transactions: {str(e)}")


@router.delete("/connected/{connected_id}")
async def disconnect_bank(connected_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.connected_banks.delete_one({"id": connected_id, **get_filter_for_user(current_user)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Connected bank not found")
    return {"message": "Bank disconnected"}


@router.post("/import-all")
async def import_all_enable_banking_accounts(current_user: dict = Depends(get_current_user)):
    try:
        filter_query = get_filter_for_user(current_user)
        connected_banks = await db.connected_banks.find(filter_query, {"_id": 0}).to_list(100)

        if not connected_banks:
            return {"message": "No connected banks found", "imported": 0, "existing": 0}

        imported_count = 0
        existing_count = 0
        banks_created = []

        eb_jwt = create_enable_banking_jwt()
        headers = {"Authorization": f"Bearer {eb_jwt}", "Content-Type": "application/json"}

        for connected in connected_banks:
            account_uid = connected.get("account_uid")
            account_iban = connected.get("account_iban", "")
            bank_name = connected.get("bank_name", "Unknown Bank")
            session_id = connected.get("session_id")
            normalized_iban = account_iban.replace(" ", "")

            all_local_banks = await db.banks.find(filter_query, {"_id": 0}).to_list(100)
            existing_bank = next(
                (b for b in all_local_banks if b.get("iban", "").replace(" ", "") == normalized_iban), None
            )

            if existing_bank:
                existing_count += 1
                continue

            balance = 0.0
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://api.enablebanking.com/accounts/{account_uid}/balances", headers=headers
                    ) as response:
                        if response.status == 200:
                            bal_data = await response.json()
                            for bal in bal_data.get("balances", []):
                                bal_type = bal.get("balance_type") or bal.get("balanceType", "")
                                if bal_type in ["closingBooked", "XPCD", "interimAvailable", "closingAvailable"]:
                                    amt = bal.get("balance_amount") or bal.get("balanceAmount") or {}
                                    balance = float(amt.get("amount", 0))
                                    break
            except Exception as e:
                logger.warning(f"Could not fetch balance for {account_uid}: {str(e)}")

            iban_suffix = normalized_iban[-4:] if normalized_iban else ""
            bank_id = str(uuid.uuid4())
            bank_doc = {
                "id": bank_id,
                "user_id": current_user["id"],
                "name": f"{bank_name} ...{iban_suffix}",
                "iban": account_iban,
                "balance": balance,
                "color": "#10B981",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "enable_banking_account_uid": account_uid,
                "enable_banking_session_id": session_id
            }
            if current_user.get("organization_id"):
                bank_doc["organization_id"] = current_user["organization_id"]

            await db.banks.insert_one(bank_doc)
            banks_created.append({k: v for k, v in bank_doc.items() if k != "_id"})
            imported_count += 1

        return {
            "message": f"Import completed: {imported_count} new bank(s), {existing_count} already exist",
            "imported": imported_count,
            "existing": existing_count,
            "banks": banks_created
        }

    except Exception as e:
        logger.error(f"Error in import_all: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
