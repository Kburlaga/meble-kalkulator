# export_cnc.py
# Eksport listy elementów do CSV (STOLARZPRO)

import csv


def export_cnc(korpus, filepath):
    """
    Zapisuje elementy do CSV dla maszyny CNC.
    """
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["ID", "Nazwa", "Szerokość [mm]", "Wysokość [mm]", "Grubość [mm]", "Uwagi"])
        
        for e in korpus.elementy:
            writer.writerow([e.id, e.nazwa, f"{e.szer:.1f}", f"{e.wys:.1f}", f"{e.gr:.1f}", e.uwagi])
