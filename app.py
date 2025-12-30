import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import io

st.set_page_config(page_title="STOLARZPRO - Master", page_icon="🪚", layout="wide")

# ==========================================
# 1. FUNKCJA RYSUJĄCA (ARCHITEKT)
# ==========================================
def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], kolor_tla='#e6ccb3'):
    """
    Rysuje formatkę z otworami.
    """
    # Ustawiamy rozmiar pod A4 poziomo (mniej więcej)
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Rysujemy Płytę
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla)
    ax.add_patch(rect)
    
    # Rysujemy Otwory
    ma_konf = False
    ma_prow = False
    
    for otw in otwory:
        x, y = otw[0], otw[1]
        kolor = otw[2] if len(otw) > 2 else 'red'
        if kolor == 'blue': ma_konf = True
        if kolor == 'red': ma_prow = True
        
        circle = patches.Circle((x, y), radius=4, edgecolor=kolor, facecolor='white', linewidth=1.5)
        ax.add_patch(circle)
        
        # Etykiety przy otworach (żeby nie zamazać rysunku przy dużej ilości)
        if len(otwory) < 40:
            ax.text(x + 6, y + 2, f"({x:.1f}, {y:.1f})", fontsize=7, color=kolor, weight='bold')

    # Legenda
    legenda = []
    if ma_prow: legenda.append("🔴 Czerwone: Prowadnice/Front")
    if ma_konf: legenda.append("🔵 Niebieskie: Konfirmaty (Konstrukcja)")
    
    opis_osi = "Szerokość (mm)"
    if legenda:
        opis_osi += "\nLEGENDA: " + "  |  ".join(legenda)
        
    ax.set_xlabel(opis_osi, fontsize=9)
    ax.set_ylabel("Wysokość (mm)")

    # Marginesy i widok
    margines = max(szer, wys) * 0.1
    ax.set_xlim(-margines, szer + margines)
    ax.set_ylim(-margines, wys + margines)
    ax.set_aspect('equal')
    
    ax.set_title(f"ID: {id_elementu} | {nazwa}\nWymiar: {szer:.1f} x {wys:.1f} mm", fontsize=12, weight='bold', pad=10)
    ax.grid(True, linestyle='--', alpha=0.5)
    
    return fig

# ==========================================
# 2. ALGORYTM NESTINGU (ROZKROJU)
# ==========================================
def optymalizuj_rozkroj(formatki, arkusz_w, arkusz_h, rzaz=4):
    # Sortujemy od największej
    formatki_sorted = sorted(formatki, key=lambda x: x['Szerokość [mm]'] * x['Wysokość [mm]'], reverse=True)
    
    arkusze = []
    aktualny_arkusz = {'elementy': [], 'zuzycie_m2': 0}
    
    cur_x, cur_y = 0, 0
    max_h_row = 0
    
    for f in formatki_sorted:
        w, h = f['Szerokość [mm]'], f['Wysokość [mm]']
        
        # 1. Czy mieści się w rzędzie?
        if cur_x + w + rzaz > arkusz_w:
            cur_x = 0
            cur_y += max_h_row + rzaz
            max_h_row = 0
            
        # 2. Czy mieści się na wysokość w arkuszu?
        if cur_y + h + rzaz > arkusz_h:
            arkusze.append(aktualny_arkusz)
            aktualny_arkusz = {'elementy': [], 'zuzycie_m2': 0}
            cur_x, cur_y = 0, 0
            max_h_row = 0
            
        aktualny_arkusz['elementy'].append({'x': cur_x, 'y': cur_y, 'w': w, 'h': h, 'id': f['ID']})
        aktualny_arkusz['zuzycie_m2'] += (w * h) / 1000000
        
        cur_x += w + rzaz
        if h > max_h_row: max_h_row = h
            
    if aktualny_arkusz['elementy']:
        arkusze.append(aktualny_arkusz)
        
    return arkusze

# ==========================================
# 3. BAZA SYSTEMÓW SZUFLAD
# ==========================================
BAZA_SYSTEMOW = {
    "GTV Axis Pro": {
        "opis": "Pełny wysuw, cichy domyk",
        "offset_prowadnica": 37.5, "offset_front_y": 47.5, "offset_front_x": 15.5,
        "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87,
        "wysokosci_tylu": {"A": 84, "B": 116, "C": 167, "D": 199}
    },
    "Blum Antaro": {
        "opis": "Standard Blum",
        "offset_prowadnica": 37.0, "offset_front_y": 45.5, "offset_front_x": 15.5,
        "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87,
        "wysokosci_tylu": {"M": 83, "K": 115, "C": 167, "D": 200}
    },
    "GTV Modern Box": {
        "opis": "Szary klasyk",
        "offset_prowadnica": 37.0, "offset_front_y": 45.0, "offset_front_x": 15.5,
        "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87,
        "wysokosci_tylu": {"A": 84, "B": 135, "C": 199, "D": 224}
    }
}

# ==========================================
# 4. INTERFEJS I LOGIKA (CORE)
# ==========================================
with st.sidebar:
    st.title("🪚 STOLARZPRO")
    st.markdown("---")
    
    st.header("1. Projekt")
    KOD_PROJEKTU = st.text_input("Kod Projektu", value="RTV-SALON").upper()
    
    st.header("2. Wymiary Szafki")
    H_MEBLA = st.number_input("Wysokość (mm)", value=600)
    W_MEBLA = st.number_input("Szerokość (mm)", value=1800)
    D_MEBLA = st.number_input("Głębokość (mm)", value=600)
    GR_PLYTY = st.number_input("Grubość płyty (mm)", value=18)
    
    st.header("3. Konstrukcja")
    ilosc_przegrod = st.number_input("Ilość przegród", value=2, min_value=0)
    typ_plecow = st.selectbox("Plecy (HDF)", ["Nakładane", "Wpuszczane", "Brak"])
    
    st.header("4. System Szuflad")
    opcje_sys = list(BAZA_SYSTEMOW.keys()) + ["Custom"]
    wybrany_sys = st.selectbox("Model:", opcje_sys)
    
    if wybrany_sys == "Custom":
        params = {"offset_prowadnica": 37.5, "offset_front_y": 47.5, "offset_front_x": 15.5,
                  "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87,
                  "wysokosci_tylu": {"Custom": 167}}
        typ_boku_key = "Custom"
    else:
        params = BAZA_SYSTEMOW[wybrany_sys]
        boki_list = list(params["wysokosci_tylu"].keys())
        typ_boku_key = st.selectbox("Wysokość boku", boki_list, index=len(boki_list)-1)

    axis_fuga = st.number_input("Fuga frontów (mm)", value=3.0)
    axis_ilosc = st.slider("Szuflady w sekcji", 1, 5, 2)
    axis_nl = st.selectbox("Długość (NL)", [300, 350, 400, 450, 500, 550], index=4)
    
    st.markdown("---")
    st.header("5. Parametry Rozkroju")
    ARKUSZ_W = st.number_input("Szer. arkusza", value=2800)
    ARKUSZ_H = st.number_input("Wys. arkusza", value=2070)
    RZAZ = st.number_input("Rzaz piły", value=4)

# --- OBLICZENIA LOGICZNE ---
ilosc_sekcji = ilosc_przegrod + 1
szer_wew_total = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)
szer_jednej_wneki = szer_wew_total / ilosc_sekcji
wys_wewnetrzna = H_MEBLA - (2 * GR_PLYTY)

st.info(f"📏 Światło wnęki na szuflady: **{szer_jednej_wneki:.1f} mm**")

lista_elementow = []

def dodaj_element(nazwa, szer, wys, gr, material, uwagi="", wiercenia=[]):
    count = sum(1 for x in lista_elementow if x['typ'] == nazwa) + 1
    
    skroty = {"Bok Lewy": "BOK-L", "Bok Prawy": "BOK-P", "Wieniec Górny": "WIEN-G", 
              "Wieniec Dolny": "WIEN-D", "Przegroda": "PRZEG", "Plecy HDF": "HDF",
              "Front Szuflady": "FR", "Dno Szuflady": "DNO", "Tył Szuflady": "TYL"}
    kod = skroty.get(nazwa, "EL")
    
    if nazwa in ["Bok Lewy", "Bok Prawy", "Wieniec Górny", "Wieniec Dolny"]:
        ident = f"{KOD_PROJEKTU}-{kod}"
    else:
        ident = f"{KOD_PROJEKTU}-{kod}-{count}"

    lista_elementow.append({
        "ID": ident, "Nazwa": nazwa, "typ": nazwa,
        "Szerokość [mm]": round(szer, 1), "Wysokość [mm]": round(wys, 1),
        "Grubość [mm]": gr, "Materiał": material, "Uwagi": uwagi, "wiercenia": wiercenia
    })

# --- A. GENEROWANIE KORPUSU ---
# 1. Wiercenia w BOKACH (Czerwone - Prowadnice)
wiercenia_prow = []
akt_h = 0
h_frontu = (wys_wewnetrzna - ((axis_ilosc + 1) * axis_fuga)) / axis_ilosc

for i in range(axis_ilosc):
    pos = akt_h + axis_fuga + params["offset_prowadnica"]
    wiercenia_prow.append(pos)
    akt_h += axis_fuga + h_frontu

otwory_bok = []
for y in wiercenia_prow:
    otwory_bok.append((37.0, y, 'red'))
    otwory_bok.append((261.0, y, 'red'))

dodaj_element("Bok Lewy", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "Płyta 18mm", "Okleina G/D/P", otwory_bok)
dodaj_element("Bok Prawy", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "Płyta 18mm", "Okleina G/D/P", otwory_bok)

# 2. Wiercenia w WIEŃCACH (Niebieskie - Konfirmaty)
otwory_wien = []
y_k1, y_k2 = 50, D_MEBLA - 50 # 5cm od krawędzi

# Łączenie z bokami
otwory_wien.extend([(GR_PLYTY/2, y_k1, 'blue'), (GR_PLYTY/2, y_k2, 'blue')])
otwory_wien.extend([(W_MEBLA-GR_PLYTY/2, y_k1, 'blue'), (W_MEBLA-GR_PLYTY/2, y_k2, 'blue')])

# Łączenie z przegrodami
cx = GR_PLYTY
for i in range(ilosc_przegrod):
    cx += szer_jednej_wneki
    otwory_wien.extend([(cx+GR_PLYTY/2, y_k1, 'blue'), (cx+GR_PLYTY/2, y_k2, 'blue')])
    cx += GR_PLYTY

dodaj_element("Wieniec Górny", W_MEBLA, D_MEBLA, GR_PLYTY, "Płyta 18mm", "Okleina dookoła", otwory_wien)
dodaj_element("Wieniec Dolny", W_MEBLA, D_MEBLA, GR_PLYTY, "Płyta 18mm", "Okleina dookoła", otwory_wien)

# 3. Przegrody
dodaj_element("Przegroda", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "Płyta 18mm", "Wiercenia 2-stronne", otwory_bok)

# 4. Plecy
hdf_h = H_MEBLA - 4 if typ_plecow == "Nakładane" else H_MEBLA - 20
hdf_w = W_MEBLA - 4 if typ_plecow == "Nakładane" else W_MEBLA - 20
if typ_plecow != "Brak":
    dodaj_element("Plecy HDF", hdf_w, hdf_h, 3, "HDF 3mm", typ_plecow)

# --- B. GENEROW
