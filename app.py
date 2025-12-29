import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

st.set_page_config(page_title="Kalkulator Meblowy PRO", page_icon="🪚", layout="wide")

# ==========================================
# 1. FUNKCJA RYSUJĄCA
# ==========================================
def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], kolor_tla='#e6ccb3'):
    fig, ax = plt.subplots(figsize=(6, 4))
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla)
    ax.add_patch(rect)
    
    ma_konfirmaty = False
    ma_prowadnice = False
    
    for otw in otwory:
        x, y = otw[0], otw[1]
        kolor = otw[2] if len(otw) > 2 else 'red'
        if kolor == 'blue': ma_konfirmaty = True
        if kolor == 'red': ma_prowadnice = True
        
        circle = patches.Circle((x, y), radius=4, edgecolor=kolor, facecolor='white', linewidth=1.5)
        ax.add_patch(circle)
        
        if len(otwory) < 25:
            label = f"({x:.1f}, {y:.1f})"
            ax.text(x + 6, y + 2, label, fontsize=7, color=kolor, weight='bold')

    legenda = []
    if ma_prowadnice: legenda.append("🔴 Czerwone: Prowadnice/Front")
    if ma_konfirmaty: legenda.append("🔵 Niebieskie: Konfirmaty")
    if legenda:
        ax.set_xlabel("Szerokość (mm)\n" + " | ".join(legenda), fontsize=9)

    ax.set_xlim(-max(szer, wys)*0.1, szer + max(szer, wys)*0.1)
    ax.set_ylim(-max(szer, wys)*0.1, wys + max(szer, wys)*0.1)
    ax.set_aspect('equal')
    ax.set_title(f"ID: {id_elementu}\n{nazwa}\n{szer:.1f} x {wys:.1f} mm", fontsize=12, weight='bold')
    ax.grid(True, linestyle='--', alpha=0.5)
    return fig

# ==========================================
# 2. BAZA DANYCH SYSTEMÓW
# ==========================================
BAZA_SYSTEMOW = {
    "GTV Axis Pro": {"base_x": 37.0, "offset_y": 47.5, "offset_x": 15.5, "red_dna_s": 75, "red_dna_d": 24, "red_tyl_s": 87, "wys_tylu": {"A": 84, "B": 116, "C": 167, "D": 199}},
    "Blum Antaro": {"base_x": 37.0, "offset_y": 45.5, "offset_x": 15.5, "red_dna_s": 75, "red_dna_d": 24, "red_tyl_s": 87, "wys_tylu": {"M": 83, "K": 115, "C": 167, "D": 200}}
}

st.title("🪚 Manager Formatek (V9 - Poprawiony Inset)")

# ==========================================
# 3. PANEL BOCZNY (INPUT)
# ==========================================
with st.sidebar:
    st.header("📋 Dane Projektu")
    KOD_PROJEKTU = st.text_input("Kod Projektu", value="RTV-01").upper()
    
    st.header("📏 Wymiary Szafki")
    H_MEBLA = st.number_input("Wysokość (mm)", value=600)
    W_MEBLA = st.number_input("Szerokość (mm)", value=1800)
    D_MEBLA = st.number_input("Głębokość (mm)", value=600)
    GR_PLYTY = st.number_input("Grubość płyty (mm)", value=18)
    
    st.header("🔨 Konstrukcja")
    typ_frontu = st.selectbox("Typ frontu", ["Nakładany", "Wpuszczany (Inset)"])
    ilosc_przegrod = st.number_input("Ilość przegród", value=2, min_value=0)
    typ_plecow = st.selectbox("Plecy (HDF)", ["Nakładane", "Wpuszczane", "Brak"])
    
    st.header("🗄️ System Szuflad")
    wybrany_sys = st.selectbox("Wybierz system:", list(BAZA_SYSTEMOW.keys()))
    params = BAZA_SYSTEMOW[wybrany_sys]
    
    # OFFSET DODATKOWY (Miejsce na odbojnik)
    KOREKTA_DODATKOWA = st.number_input("Miejsce na odbojnik/uszczelkę (mm)", value=1.0, step=0.5, help="Dystans o jaki front odstaje od korpusu (zazwyczaj 1-2mm).")
    
    # LOGIKA OBLICZANIA OFFSETU X (POPRAWIONA)
    if typ_frontu == "Wpuszczany (Inset)":
        # Baza + Front + Odbojnik
        OBBLICZONY_OFFSET_X = params["base_x"] + GR_PLYTY + KOREKTA_DODATKOWA
        st.warning(f"Tryb Wpuszczany: 37 + {GR_PLYTY} (front) + {KOREKTA_DODATKOWA} (odbojnik)")
    else:
        # Baza + Odbojnik
        OBBLICZONY_OFFSET_X = params["base_x"] + KOREKTA_DODATKOWA
        st.info(f"Tryb Nakładany: 37 + {KOREKTA_DODATKOWA} (odbojnik)")

    st.caption(f"Wymiar wiercenia X: **{OBBLICZONY_OFFSET_X:.1f} mm**")

    typ_boku_key = st.selectbox("Wysokość boku", list(params["wysokosci_tylu"].keys()), index=len(params["wysokosci_tylu"])-1)
    axis_fuga = st.number_input("Fuga (mm)", value=3.0)
    axis_ilosc = st.slider("Szuflady w sekcji", 2, 5, 2)
    axis_nl = st.selectbox("Długość (NL)", [300, 350, 400, 450, 500, 550], index=4)

# --- Obliczenia światła ---
ilosc_sekcji = ilosc_przegrod + 1
szer_wewnetrzna_total = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)
szer_jednej_wneki = szer_wewnetrzna_total / ilosc_sekcji
wys_wewnetrzna = H_MEBLA - (2 * GR_PLYTY)

# ==========================================
# 4. GENEROWANIE LISTY
# ==========================================
lista_elementow = []

def dodaj_element(nazwa, szer, wys, gr, mat, uwagi="", wiercenia=[]):
    count = sum(1 for x in lista_elementow if x['typ'] == nazwa) + 1
    skroty = {"Bok Lewy": "BOK-L", "Bok Prawy": "BOK-P", "Wieniec Górny": "WIEN-G", "Wieniec Dolny": "WIEN-D", "Przegroda": "PRZEG", "Plecy HDF": "HDF", "Front Szuflady": "FR", "Dno Szuflady": "DNO", "Tył Szuflady": "TYL"}
    ident = f"{KOD_PROJEKTU}-{skroty.get(nazwa, 'EL')}" + (f"-{count}" if nazwa not in skroty.values() else "")
    lista_elementow.append({"ID": ident, "Nazwa": nazwa, "Szerokość [mm]": round(szer, 1), "Wysokość [mm]": round(wys, 1), "Grubość [mm]": gr, "Materiał": mat, "Uwagi": uwagi, "typ": nazwa, "wiercenia": wiercenia})

# Wiercenia boku (Czerwone)
h_frontu = (wys_wewnetrzna - ((axis_ilosc + 1) * axis_fuga)) / axis_ilosc
akt_h = 0
otwory_bok = []
for i in range(axis_ilosc):
    pos_y = akt_h + axis_fuga + 37.0 
    otwory_bok.append((OBBLICZONY_OFFSET_X, pos_y, 'red'))
    otwory_bok.append((OBBLICZONY_OFFSET_X + 224, pos_y, 'red'))
    akt_h += axis_fuga + h_frontu

dodaj_element("Bok Lewy", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", "", otwory_bok)
dodaj_element("Bok Prawy", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", "", otwory_bok)

# Wieńce (Niebieskie)
otwory_wien = [(GR_PLYTY/2, 50, 'blue'), (GR_PLYTY/2, D_MEBLA-50, 'blue'), (W_MEBLA-GR_PLYTY/2, 50, 'blue'), (W_MEBLA-GR_PLYTY/2, D_MEBLA-50, 'blue')]
curr_x = GR_PLYTY
for i in range(ilosc_przegrod):
    curr_x += szer_jednej_wneki
    otwory_wien.extend([(curr_x + GR_PLYTY/2, 50, 'blue'), (curr_x + GR_PLYTY/2, D_MEBLA-50, 'blue')])
    curr_x += GR_PLYTY
dodaj_element("Wieniec Górny", W_MEBLA, D_MEBLA, GR_PLYTY, "Płyta 18mm", "", otwory_wien)
dodaj_element("Wieniec Dolny", W_MEBLA, D_MEBLA, GR_PLYTY, "Płyta 18mm", "", otwory_wien)
dodaj_element("Przegroda", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", "Obustronne", otwory_bok)

if typ_plecow != "Brak":
    dodaj_element("Plecy HDF", W_MEBLA-4, H_MEBLA-4, 3, "HDF 3mm", typ_plecow)

# Fronty
w_frontu = szer_jednej_wneki - (2 * axis_fuga)
otwory_fr = [(params["offset_x"], params["offset_y"], 'red'), (params["offset_x"], params["offset_y"]+32, 'red'), (w_frontu-params["offset_x"], params["offset_y"], 'red'), (w_frontu-params["offset_x"], params["offset_y"]+32, 'red')]
for s in range(ilosc_sekcji):
    for sz in range(axis_ilosc):
        dodaj_element("Front Szuflady", w_frontu, h_frontu, 18, "Płyta 18mm", f"Sekcja {s+1}", otwory_fr)
        dodaj_element("Dno Szuflady", axis_nl - 24, szer_jednej_wneki - 75, 16, "Płyta 16mm")
        dodaj_element("Tył Szuflady", szer_jednej_wneki - 87, params["wys_tylu"][typ_boku_key], 16, "Płyta 16mm")

# ==========================================
# 5. WYŚWIETLANIE
# ==========================================
tab1, tab2 = st.tabs(["📋 LISTA", "📐 RYSUNKI"])
with tab1:
    st.dataframe(pd.DataFrame(lista_elementow).drop(columns=['typ', 'wiercenia']), use_container_width=True, hide_index=True)
with tab2:
    el_id = st.selectbox("Wybierz element:", [e['ID'] for e in lista_elementow if e['wiercenia']])
    item = next(e for e in lista_elementow if e['ID'] == el_id)
    st.pyplot(rysuj_element(item['Szerokość [mm]'], item['Wysokość [mm]'], item['ID'], item['Nazwa'], item['wiercenia']))
