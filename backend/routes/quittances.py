import io
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from core.database import db
from core.auth import get_current_user, get_filter_for_user
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/quittances")

MONTHS_FR = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
             "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

BAILLEUR = {
    "nom": "SCI C2GR",
    "adresse": "1 rue des Entrepreneurs, 59000 Lille",
    "siret": "En cours",
}


def generate_quittance_pdf(tenant: dict, payment: dict, month: int, year: int) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    PRIMARY = colors.HexColor("#1a1a2e")
    ACCENT  = colors.HexColor("#4f46e5")
    LIGHT   = colors.HexColor("#f8f7ff")
    GRAY    = colors.HexColor("#6b7280")
    GREEN   = colors.HexColor("#10b981")

    title_style = ParagraphStyle("Title", parent=styles["Normal"],
        fontSize=22, fontName="Helvetica-Bold", textColor=PRIMARY,
        alignment=TA_CENTER, spaceAfter=4)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"],
        fontSize=11, fontName="Helvetica", textColor=ACCENT,
        alignment=TA_CENTER, spaceAfter=2)
    section_style = ParagraphStyle("Section", parent=styles["Normal"],
        fontSize=10, fontName="Helvetica-Bold", textColor=PRIMARY, spaceAfter=4)
    body_style = ParagraphStyle("Body", parent=styles["Normal"],
        fontSize=9.5, fontName="Helvetica", textColor=colors.HexColor("#374151"),
        spaceAfter=3, leading=14)
    small_gray = ParagraphStyle("SmallGray", parent=styles["Normal"],
        fontSize=8, fontName="Helvetica", textColor=GRAY, spaceAfter=2)
    legal_style = ParagraphStyle("Legal", parent=styles["Normal"],
        fontSize=8, fontName="Helvetica-Oblique", textColor=GRAY,
        alignment=TA_CENTER, spaceAfter=2, leading=11)

    story = []

    # ── En-tête ──────────────────────────────────────────────────────────────
    story.append(Paragraph("QUITTANCE DE LOYER", title_style))
    story.append(Paragraph(f"{MONTHS_FR[month]} {year}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=14))

    # ── Bailleur / Locataire ─────────────────────────────────────────────────
    bailleur_data = [
        [Paragraph("<b>BAILLEUR</b>", section_style), Paragraph("<b>LOCATAIRE</b>", section_style)],
        [Paragraph(BAILLEUR["nom"], body_style), Paragraph(tenant.get("name", ""), body_style)],
        [Paragraph(BAILLEUR["adresse"], small_gray),
         Paragraph(tenant.get("property_address", "—") or "—", small_gray)],
        [Paragraph(f"SIRET : {BAILLEUR['siret']}", small_gray),
         Paragraph(f"Tél : {tenant.get('phone','—') or '—'}", small_gray)],
        [Paragraph("", small_gray),
         Paragraph(f"Email : {tenant.get('email','—') or '—'}", small_gray)],
    ]

    bailleur_table = Table(bailleur_data, colWidths=[8.5*cm, 8.5*cm])
    bailleur_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#f0f0ff")),
        ("BACKGROUND", (1, 1), (1, -1), colors.white),
        ("BOX",        (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("LINEAFTER",  (0, 0), (0, -1),  0.5, colors.HexColor("#e5e7eb")),
        ("LINEBEFORE", (1, 0), (1, -1),  0.5, colors.HexColor("#e5e7eb")),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(bailleur_table)
    story.append(Spacer(1, 14))

    # ── Bien loué ───────────────────────────────────────────────────────────
    story.append(Paragraph("BIEN LOUÉ", section_style))
    adresse_bien = tenant.get("property_address", "—") or "—"
    structure    = tenant.get("structure", "—") or "—"
    story.append(Paragraph(f"{adresse_bien} — {structure}", body_style))
    story.append(Spacer(1, 10))

    # ── Période ─────────────────────────────────────────────────────────────
    from calendar import monthrange
    last_day = monthrange(year, month)[1]
    period_start = f"01/{month:02d}/{year}"
    period_end   = f"{last_day}/{month:02d}/{year}"

    story.append(Paragraph("PÉRIODE", section_style))
    story.append(Paragraph(f"Du {period_start} au {period_end}", body_style))
    story.append(Spacer(1, 10))

    # ── Détail des montants ──────────────────────────────────────────────────
    loyer_nu   = float(tenant.get("rent_amount", 0))
    charges    = float(tenant.get("charges", 0) or 0)
    total      = loyer_nu + charges

    amount_data = [
        [Paragraph("<b>Désignation</b>", ParagraphStyle("H", parent=body_style, textColor=colors.white)),
         Paragraph("<b>Montant</b>", ParagraphStyle("H", parent=body_style, textColor=colors.white, alignment=TA_RIGHT))],
        [Paragraph("Loyer hors charges", body_style),
         Paragraph(f"{loyer_nu:.2f} €", ParagraphStyle("R", parent=body_style, alignment=TA_RIGHT))],
    ]

    if charges > 0:
        amount_data.append([
            Paragraph("Charges locatives", body_style),
            Paragraph(f"{charges:.2f} €", ParagraphStyle("R", parent=body_style, alignment=TA_RIGHT))
        ])

    amount_data.append([
        Paragraph("<b>TOTAL</b>", ParagraphStyle("T", parent=body_style, fontName="Helvetica-Bold")),
        Paragraph(f"<b>{total:.2f} €</b>",
                  ParagraphStyle("T", parent=body_style, fontName="Helvetica-Bold", alignment=TA_RIGHT))
    ])

    n_rows = len(amount_data)
    amount_table = Table(amount_data, colWidths=[13*cm, 4*cm])
    ts = TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),    ACCENT),
        ("BACKGROUND",    (0, n_rows-1), (-1, n_rows-1), LIGHT),
        ("BOX",           (0, 0), (-1, -1),   0.5, colors.HexColor("#e5e7eb")),
        ("LINEBELOW",     (0, 0), (-1, -2),   0.3, colors.HexColor("#e5e7eb")),
        ("LINEABOVE",     (0, n_rows-1), (-1, n_rows-1), 1, ACCENT),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
    ])
    amount_table.setStyle(ts)
    story.append(amount_table)
    story.append(Spacer(1, 14))

    # ── Paiement ─────────────────────────────────────────────────────────────
    if payment:
        pay_date = payment.get("payment_date", "")
        if isinstance(pay_date, str):
            try:
                pay_date = datetime.fromisoformat(pay_date.replace("Z", "+00:00")).strftime("%d/%m/%Y")
            except:
                pass
        pay_amount = float(payment.get("amount", total))
        story.append(Paragraph("PAIEMENT REÇU", section_style))

        pay_data = [
            [Paragraph("Date de paiement", body_style), Paragraph(str(pay_date), body_style)],
            [Paragraph("Montant réglé", body_style),    Paragraph(f"{pay_amount:.2f} €", body_style)],
            [Paragraph("Mode de règlement", body_style), Paragraph("Virement bancaire", body_style)],
        ]
        pay_table = Table(pay_data, colWidths=[6*cm, 11*cm])
        pay_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0fdf4")),
            ("TEXTCOLOR",  (0, 0), (0, -1), GREEN),
            ("BOX",        (0, 0), (-1, -1), 0.5, colors.HexColor("#d1fae5")),
            ("LINEBELOW",  (0, 0), (-1, -2), 0.3, colors.HexColor("#d1fae5")),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 12),
            ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ]))
        story.append(pay_table)
    story.append(Spacer(1, 18))

    # ── Attestation légale ────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb"), spaceAfter=10))
    today_str = datetime.now().strftime("%d/%m/%Y")
    story.append(Paragraph(
        f"Je soussigné(e), représentant(e) de <b>{BAILLEUR['nom']}</b>, "
        f"donne quittance à <b>{tenant.get('name','')}</b> "
        f"pour le paiement de la somme de <b>{total:.2f} €</b> "
        f"correspondant au loyer et aux charges du mois de <b>{MONTHS_FR[month]} {year}</b> "
        f"pour le bien situé à <b>{adresse_bien}</b>.",
        legal_style
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Fait le {today_str}", legal_style))
    story.append(Spacer(1, 20))

    # ── Signature ───────────────────────────────────────────────────────────
    sig_data = [[
        Paragraph("Signature du bailleur", small_gray),
        Paragraph("", small_gray),
    ]]
    sig_table = Table(sig_data, colWidths=[8.5*cm, 8.5*cm])
    sig_table.setStyle(TableStyle([
        ("LINEABOVE", (0,0),(0,0), 0.5, GRAY),
        ("TOPPADDING", (0,0),(-1,-1), 20),
    ]))
    story.append(sig_table)

    # ── Pied de page ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb"), spaceAfter=6))
    story.append(Paragraph(
        f"Document généré automatiquement par CGR Bank • {BAILLEUR['nom']} • {today_str}",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7, textColor=GRAY, alignment=TA_CENTER)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


@router.get("/{tenant_id}")
async def get_quittance(
    tenant_id: str,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020, le=2100),
    current_user: dict = Depends(get_current_user)
):
    tenant = await db.tenants.find_one(
        {"id": tenant_id, **get_filter_for_user(current_user)},
        {"_id": 0}
    )
    if not tenant:
        raise HTTPException(status_code=404, detail="Locataire introuvable")

    from calendar import monthrange
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year
    start_date = datetime(prev_year, prev_month, 28, tzinfo=timezone.utc)
    last_day = min(28, monthrange(year, month)[1])
    end_date   = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    payment = await db.payments.find_one(
        {
            "tenant_id": tenant_id,
            **get_filter_for_user(current_user),
            "payment_date": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}
        },
        {"_id": 0},
        sort=[("payment_date", -1)]
    )

    if not payment:
        transaction = await db.transactions.find_one(
            {
                "matched_tenant_id": tenant_id,
                **get_filter_for_user(current_user),
                "amount": {"$gt": 0},
                "transaction_date": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}
            },
            {"_id": 0},
            sort=[("transaction_date", -1)]
        )
        if transaction:
            payment = {
                "amount": transaction["amount"],
                "payment_date": transaction["transaction_date"]
            }

    pdf_bytes = generate_quittance_pdf(tenant, payment, month, year)

    tenant_name_safe = tenant.get("name", "locataire").replace(" ", "_").replace("/", "-")
    filename = f"quittance_{tenant_name_safe}_{MONTHS_FR[month]}_{year}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
