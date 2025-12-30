# export_pdf.py
# Eksport listy elementów do PDF (STOLARZPRO)

from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4


def export_pdf(korpus, filepath):
    """
    Tworzy PDF z listą elementów mebla.
    """

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(filepath, pagesize=A4)

    elements = []

    # Tytuł
    elements.append(Paragraph("STOLARZPRO – lista elementów", styles["Title"]))
    elements.append(Spacer(1, 12))

    # Nagłówki tabeli
    data = [
        ["ID", "Nazwa", "Szerokość [mm]", "Wysokość [mm]", "Grubość [mm]", "Uwagi"]
    ]

    # Dane
    for e in korpus.elementy:
        data.append(
            [
                e.id,
                e.nazwa,
                f"{e.szer:.1f}",
                f"{e.wys:.1f}",
                f"{e.gr:.1f}",
                e.uwagi,
            ]
        )

    table = Table(data, repeatRows=1)
    elements.append(table)

    doc.build(elements)
