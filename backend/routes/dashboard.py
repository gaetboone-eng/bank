from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from core.database import db
from core.auth import get_current_user, get_filter_for_user
from core.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, ENABLE_BANKING_APP_ID, ENABLE_BANKING_PRIVATE_KEY
from models.schemas import DashboardStats, SettingsUpdate
from services.categorization import CATEGORIES, CATEGORIES_LIST, normalize_category

router = APIRouter()

ACTIVE_STATUS_FILTER = {"$nin": ["resilié", "resilie", "terminated", "inactive"]}

INCOME_CATEGORIES = {"loyer_encaisse", "autre_recette", "rent", "deposit"}
NEUTRAL_CATEGORIES = {"virement_interne"}


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


@router.get("/dashboard/cashflow-history")
async def get_cashflow_history(current_user: dict = Depends(get_current_user)):
    from dateutil.relativedelta import relativedelta

    month_names_fr = {1: "Jan", 2: "Fév", 3: "Mar", 4: "Avr", 5: "Mai", 6: "Jun",
                      7: "Jul", 8: "Aoû", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Déc"}
    month_names_en = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May",
                      6: "June", 7: "July", 8: "August", 9: "September", 10: "October",
                      11: "November", 12: "December"}

    tenants = await db.tenants.find(
        {**get_filter_for_user(current_user), "status": ACTIVE_STATUS_FILTER},
        {"_id": 0}
    ).to_list(1000)

    tenant_map = {t["id"]: t for t in tenants}
    structures = sorted(list(set(t.get("structure", "Non défini") or "Non défini" for t in tenants)))

    now = datetime.now(timezone.utc)
    history = []

    for i in range(5, -1, -1):
        target = now - relativedelta(months=i)
        m, y = target.month, target.year
        month_en = month_names_en[m]

        payments = await db.payments.find({
            **get_filter_for_user(current_user),
            "month": month_en,
            "year": y
        }, {"_id": 0}).to_list(1000)

        structure_amounts = {s: 0.0 for s in structures}
        total = 0.0

        for payment in payments:
            tenant = tenant_map.get(payment["tenant_id"])
            if tenant:
                struct = tenant.get("structure", "Non défini") or "Non défini"
                amount = payment.get("amount", 0)
                structure_amounts[struct] = structure_amounts.get(struct, 0) + amount
                total += amount

        entry = {
            "label": f"{month_names_fr[m]} {str(y)[2:]}",
            "month": month_en,
            "year": y,
            "total": round(total, 2),
        }
        for struct in structures:
            entry[struct] = round(structure_amounts.get(struct, 0.0), 2)

        history.append(entry)

    # Late tenants: missing current month, with count of consecutive missed months
    current_month_en = month_names_en[now.month]
    paid_this_month = await db.payments.distinct(
        "tenant_id",
        {**get_filter_for_user(current_user), "month": current_month_en, "year": now.year}
    )
    paid_set = set(paid_this_month)

    late_tenants = []
    for tenant in tenants:
        if tenant["id"] not in paid_set:
            months_late = 0
            for j in range(1, 7):
                check = now - relativedelta(months=j)
                check_month_en = month_names_en[check.month]
                payment = await db.payments.find_one({
                    "tenant_id": tenant["id"],
                    "month": check_month_en,
                    "year": check.year
                })
                if payment:
                    break
                months_late += 1

            late_tenants.append({
                "id": tenant["id"],
                "name": tenant["name"],
                "structure": tenant.get("structure", "Non défini") or "Non défini",
                "rent_amount": tenant.get("rent_amount", 0),
                "months_late": months_late
            })

    late_tenants.sort(key=lambda x: (-x["months_late"], x["name"]))

    return {
        "history": history,
        "structures": structures,
        "late_tenants": late_tenants
    }



# ── Constantes associés ──────────────────────────────────────────────────────

ASSOCIES_PARTS = {
    "Gaetan": {
        "🏥 Seclin": 0.366,
        "🏢 Armentières": 0.33,
        "🏘️ La Madeleine": 0.33,
        "🏭 Roncq": 0.0,
        "Hem": 0.0,
    },
    "Romain": {
        "🏥 Seclin": 0.316,
        "🏢 Armentières": 0.33,
        "🏘️ La Madeleine": 0.33,
        "🏭 Roncq": 0.5,
        "Hem": 0.5,
    },
    "Clément": {
        "🏥 Seclin": 0.316,
        "🏢 Armentières": 0.33,
        "🏘️ La Madeleine": 0.33,
        "🏭 Roncq": 0.5,
        "Hem": 0.5,
    },
}

BANK_TO_STRUCTURE = {
    "seclin":      "🏥 Seclin",
    "armentieres": "🏢 Armentières",
    "armentières": "🏢 Armentières",
    "madeleine":   "🏘️ La Madeleine",
    "roncq":       "🏭 Roncq",
    "hem":         "Hem",
}

def _bank_to_structure(bank_name: str) -> str:
    name = bank_name.lower()
    for key, struct in BANK_TO_STRUCTURE.items():
        if key in name:
            return struct
    return bank_name


@router.get("/dashboard/structure-cashflow")
async def get_structure_cashflow(current_user: dict = Depends(get_current_user)):
    """Cashflow par structure depuis le 1er janvier (loyers - dépenses) + répartition associés."""
    from dateutil.relativedelta import relativedelta

    now = datetime.now(timezone.utc)
    jan_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)

    # Récupérer toutes les banques
    banks = await db.banks.find(get_filter_for_user(current_user), {"_id": 0}).to_list(100)
    bank_map = {b["id"]: b for b in banks}

    # Toutes les transactions depuis jan 1 (hors dépôts de garantie)
    EXCLUDE_KEYWORDS = [
        "depot de garantie", "depot garantie", "caution",
        "dg loyer", "garantie locative"
    ]
    all_txs = await db.transactions.find(
        {
            **get_filter_for_user(current_user),
            "transaction_date": {"$gte": jan_start.isoformat()}
        },
        {"_id": 0}
    ).to_list(10000)
    transactions = [
        tx for tx in all_txs
        if not any(kw in (tx.get("description") or "").lower() for kw in EXCLUDE_KEYWORDS)
    ]

    # Grouper par structure
    structure_data = {}
    for tx in transactions:
        bank = bank_map.get(tx.get("bank_id", ""), {})
        struct = _bank_to_structure(bank.get("name", ""))
        amount = tx.get("amount", 0)

        if struct not in structure_data:
            structure_data[struct] = {"loyers": 0.0, "depenses": 0.0, "transactions": 0}

        if amount > 0:
            structure_data[struct]["loyers"] += amount
        else:
            structure_data[struct]["depenses"] += abs(amount)
        structure_data[struct]["transactions"] += 1

    # Construire résultat par structure
    structures_result = []
    for struct, data in structure_data.items():
        cashflow = data["loyers"] - data["depenses"]
        structures_result.append({
            "structure": struct,
            "loyers": round(data["loyers"], 2),
            "depenses": round(data["depenses"], 2),
            "cashflow": round(cashflow, 2),
            "transactions": data["transactions"],
        })
    structures_result.sort(key=lambda x: x["structure"])

    # Total global
    total_loyers   = sum(s["loyers"]   for s in structures_result)
    total_depenses = sum(s["depenses"] for s in structures_result)
    total_cashflow = total_loyers - total_depenses

    # Répartition par associé
    associes_result = []
    for associe, parts in ASSOCIES_PARTS.items():
        total_associe = 0.0
        detail = []
        for struct_data in structures_result:
            struct = struct_data["structure"]
            part = parts.get(struct, 0.0)
            montant = round(struct_data["cashflow"] * part, 2)
            total_associe += montant
            detail.append({
                "structure": struct,
                "part_pct": round(part * 100, 1),
                "cashflow_structure": struct_data["cashflow"],
                "montant": montant,
            })
        associes_result.append({
            "nom": associe,
            "total": round(total_associe, 2),
            "detail": detail,
            "parts": {k: round(v * 100, 1) for k, v in parts.items()},
        })

    # Historique mensuel depuis jan (global + par structure pour calcul associés)
    monthly = []
    monthly_structure = {}  # label -> struct -> {loyers, depenses}
    m = jan_start
    while m <= now:
        m_end = (m + relativedelta(months=1))
        label = m.strftime("%b %y")
        month_txs = [
            tx for tx in transactions
            if m.isoformat() <= tx.get("transaction_date", "") < m_end.isoformat()
        ]
        m_loyers   = sum(tx["amount"] for tx in month_txs if tx["amount"] > 0)
        m_depenses = sum(abs(tx["amount"]) for tx in month_txs if tx["amount"] < 0)
        monthly.append({
            "label": label,
            "loyers": round(m_loyers, 2),
            "depenses": round(m_depenses, 2),
            "cashflow": round(m_loyers - m_depenses, 2),
        })
        # Décomposer par structure pour ce mois
        m_struct = {}
        for tx in month_txs:
            bank = bank_map.get(tx.get("bank_id", ""), {})
            struct = _bank_to_structure(bank.get("name", ""))
            amount = tx.get("amount", 0)
            if struct not in m_struct:
                m_struct[struct] = {"loyers": 0.0, "depenses": 0.0}
            if amount > 0:
                m_struct[struct]["loyers"] += amount
            else:
                m_struct[struct]["depenses"] += abs(amount)
        monthly_structure[label] = m_struct
        m = m_end

    # Cashflow annuel par associé + breakdown mensuel
    for assoc in associes_result:
        annual = 0.0
        for struct_data in structures_result:
            struct = struct_data["structure"]
            part = ASSOCIES_PARTS[assoc["nom"]].get(struct, 0.0)
            annual += struct_data["cashflow"] * part
        assoc["annuel"] = round(annual, 2)

        # Mensuel par associé
        assoc_monthly = []
        for m_data in monthly:
            lbl = m_data["label"]
            m_struct = monthly_structure.get(lbl, {})
            m_total = 0.0
            for struct, cf_data in m_struct.items():
                struct_cf = cf_data["loyers"] - cf_data["depenses"]
                part = ASSOCIES_PARTS[assoc["nom"]].get(struct, 0.0)
                m_total += struct_cf * part
            assoc_monthly.append({"label": lbl, "cashflow": round(m_total, 2)})
        assoc["monthly"] = assoc_monthly

    return {
        "period": f"Depuis le 01/01/{now.year}",
        "oldest_transaction": "16/02/2026",
        "structures": structures_result,
        "total": {
            "loyers": round(total_loyers, 2),
            "depenses": round(total_depenses, 2),
            "cashflow": round(total_cashflow, 2),
        },
        "associes": associes_result,
        "monthly": monthly,
    }


@router.get("/dashboard/financial-summary")
async def get_financial_summary(current_user: dict = Depends(get_current_user)):
    """
    Résumé financier style Indy:
    - KPIs YTD: CA, Charges, Résultat, Trésorerie
    - Tableau mensuel (12 derniers mois): CA / Charges / Résultat
    - Répartition des charges par catégorie
    - Dernières transactions
    """
    from dateutil.relativedelta import relativedelta

    now = datetime.now(timezone.utc)
    year_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)

    month_names_fr = {1: "Jan", 2: "Fév", 3: "Mar", 4: "Avr", 5: "Mai", 6: "Jun",
                      7: "Jul", 8: "Aoû", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Déc"}

    # Fetch all transactions for the current year
    all_tx = await db.transactions.find(
        {**get_filter_for_user(current_user),
         "transaction_date": {"$gte": year_start.isoformat()}},
        {"_id": 0}
    ).sort("transaction_date", -1).to_list(5000)

    # Normalize categories
    for tx in all_tx:
        raw_cat = tx.get("category", "")
        tx["_norm_cat"] = normalize_category(raw_cat) if raw_cat else ("loyer_encaisse" if tx.get("amount", 0) > 0 else "frais_divers")

    # YTD KPIs
    ytd_ca = sum(tx["amount"] for tx in all_tx if tx["_norm_cat"] in INCOME_CATEGORIES and tx["_norm_cat"] not in NEUTRAL_CATEGORIES)
    ytd_charges = abs(sum(tx["amount"] for tx in all_tx if tx.get("amount", 0) < 0 and tx["_norm_cat"] not in NEUTRAL_CATEGORIES))
    ytd_resultat = ytd_ca - ytd_charges

    # Bank balances (trésorerie)
    banks = await db.banks.find(get_filter_for_user(current_user), {"_id": 0}).to_list(100)
    tresorerie = sum(b.get("balance", 0) for b in banks)

    # Monthly table (current year months up to now)
    monthly = []
    for month_num in range(1, now.month + 1):
        month_start = datetime(now.year, month_num, 1, tzinfo=timezone.utc)
        if month_num < 12:
            month_end = datetime(now.year, month_num + 1, 1, tzinfo=timezone.utc)
        else:
            month_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)

        month_tx = [
            tx for tx in all_tx
            if month_start.isoformat() <= tx.get("transaction_date", "") < month_end.isoformat()
        ]

        m_ca = sum(tx["amount"] for tx in month_tx if tx["_norm_cat"] in INCOME_CATEGORIES and tx["_norm_cat"] not in NEUTRAL_CATEGORIES)
        m_charges = abs(sum(tx["amount"] for tx in month_tx if tx.get("amount", 0) < 0 and tx["_norm_cat"] not in NEUTRAL_CATEGORIES))
        m_resultat = m_ca - m_charges

        monthly.append({
            "month": month_num,
            "label": month_names_fr[month_num],
            "ca": round(m_ca, 2),
            "charges": round(m_charges, 2),
            "resultat": round(m_resultat, 2),
            "is_current": month_num == now.month
        })

    # Expense breakdown by category (YTD)
    expense_tx = [tx for tx in all_tx if tx.get("amount", 0) < 0 and tx["_norm_cat"] not in NEUTRAL_CATEGORIES]
    category_totals = {}
    for tx in expense_tx:
        cat = tx["_norm_cat"]
        category_totals[cat] = category_totals.get(cat, 0) + abs(tx["amount"])

    expense_breakdown = []
    for cat_key, total in sorted(category_totals.items(), key=lambda x: -x[1]):
        cat_info = CATEGORIES.get(cat_key, CATEGORIES.get("frais_divers"))
        expense_breakdown.append({
            "category": cat_key,
            "label": cat_info["label"],
            "color": cat_info["color"],
            "total": round(total, 2),
            "percentage": round(total / ytd_charges * 100, 1) if ytd_charges > 0 else 0
        })

    # Recent transactions (last 10)
    recent_tx = []
    for tx in all_tx[:15]:
        cat_info = CATEGORIES.get(tx["_norm_cat"], CATEGORIES.get("frais_divers"))
        # Get bank name
        bank = next((b for b in banks if b.get("id") == tx.get("bank_id")), None)
        recent_tx.append({
            "id": tx.get("id"),
            "description": tx.get("description", ""),
            "amount": tx.get("amount", 0),
            "transaction_date": tx.get("transaction_date", ""),
            "category": tx["_norm_cat"],
            "category_label": cat_info["label"],
            "category_color": cat_info["color"],
            "bank_name": bank.get("name", "") if bank else "",
            "bank_color": bank.get("color", "#64748b") if bank else "#64748b",
            "matched_tenant_id": tx.get("matched_tenant_id")
        })

    # Categories list for frontend
    return {
        "kpis": {
            "ca": round(ytd_ca, 2),
            "charges": round(ytd_charges, 2),
            "resultat": round(ytd_resultat, 2),
            "tresorerie": round(tresorerie, 2)
        },
        "monthly": monthly,
        "expense_breakdown": expense_breakdown,
        "recent_transactions": recent_tx,
        "categories": CATEGORIES_LIST
    }


@router.get("/dashboard/expense-breakdown")
async def get_expense_breakdown(current_user: dict = Depends(get_current_user)):
    """Répartition des dépenses par catégorie (compatibilité legacy)."""
    summary = await get_financial_summary(current_user)
    return {"breakdown": summary["expense_breakdown"]}


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
