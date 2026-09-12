"""
pdf_export.py - Generazione del catalogo prodotti in PDF per il cliente.
"""

import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

ACCENT = colors.HexColor("#2F6F5E")   # verde/petrolio elegante
LIGHT = colors.HexColor("#F2F5F4")


def export_catalog(products, filepath, company_name="", show_code=True):
    """
    products: lista di sqlite3.Row (o dict) con almeno name, category, sale_price, code
    filepath: percorso .pdf di destinazione
    """
    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        topMargin=20 * mm, bottomMargin=18 * mm,
        leftMargin=16 * mm, rightMargin=16 * mm,
        title="Catalogo Prodotti",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCustom", parent=styles["Title"], textColor=ACCENT, fontSize=22, spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"], textColor=colors.grey, fontSize=10, spaceAfter=14,
    )
    cat_style = ParagraphStyle(
        "Category", parent=styles["Heading2"], textColor=ACCENT, fontSize=13,
        spaceBefore=14, spaceAfter=6,
    )

    story = []
    story.append(Paragraph(company_name or "Catalogo Prodotti", title_style))
    story.append(Paragraph(
        f"Aggiornato al {datetime.date.today().strftime('%d/%m/%Y')}",
        subtitle_style,
    ))

    # Raggruppa per categoria per un catalogo piu' leggibile
    by_cat = {}
    for p in products:
        cat = (p["category"] or "Altro").strip() or "Altro"
        by_cat.setdefault(cat, []).append(p)

    header = ["Codice", "Articolo", "Prezzo"] if show_code else ["Articolo", "Prezzo"]

    for cat in sorted(by_cat.keys()):
        story.append(Paragraph(cat, cat_style))
        rows = [header]
        for p in sorted(by_cat[cat], key=lambda r: (r["name"] or "").lower()):
            price = p["sale_price"] if p["sale_price"] is not None else 0
            price_str = f"€ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if show_code:
                rows.append([p["code"] or "-", p["name"], price_str])
            else:
                rows.append([p["name"], price_str])

        col_widths = [28 * mm, 105 * mm, 30 * mm] if show_code else [140 * mm, 30 * mm]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DADFDD")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 4))

    doc.build(story)
    return filepath
