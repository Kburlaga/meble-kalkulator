import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import io

st.set_page_config(page_title="STOLARZPRO - V16 (DEBUG)", page_icon="🪚", layout="wide")

# ==========================================
# 0. RESETOWANIE
# ==========================================
def resetuj_projekt():
    defaults = {
        'kod_pro': "RTV-DEBUG", 'h_mebla': 600, 'w_mebla': 1800, 'd_mebla': 600, 'gr_plyty': 18,
        'il_przegrod': 2, 'typ_plecow': "Nakładane", 'sys_szuflad': "GTV Axis Pro", 'typ_boku': "C",
        'fuga': 3.0, 'nl': 500, 'arkusz_w': 2800, 'arkusz_h': 2070, 'rzaz': 4
    }
    for k, v in defaults.items():
        st.session_state[k] = v
    st.session_state['pdf_ready'] = None

if 'kod_pro' not in st.session_state:
    resetuj_projekt()

# ==========================================
# 1. FUNKCJA RYSUJĄCA
# ==========================================
def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], kolor_tla='#e6ccb3', orientacja_frontu="L", podtytul=""):
    fig, ax = plt.subplots(figsize=(10, 6))
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla)
    ax.add_patch(rect)
    
    ma_konf, ma_prow, ma_polka = False, False, False
    for otw in otwory:
        x, y = otw[0], otw[1]
        kolor = otw[2] if len(otw) > 2 else 'red'
        if kolor == 'blue': ma_konf = True
        elif kolor == 'red': ma_prow = True
        elif kolor == 'green': ma_polka = True
        circle = patches.Circle((x, y), radius=4, edgecolor=kolor, facecolor='white', linewidth=1.5)
        ax.add_patch(circle)
        if len(otwory) < 60:
            ax.text(x + 10, y + 5, f"({x:.1f}, {y:.1f})", fontsize=6, color=kolor, weight='bold')

    font_size_front = 10
    if orientacja_frontu == "L":
        ax.add_patch(patches.Rectangle((-5, 0), 5, wys, color='red', alpha=0.6))
        ax.text(-25, wys/2, "FRONT ⬅", rotation=90, va='center', color='red', weight='bold', fontsize=font_size_front)
    else:
        ax.add_patch(patches.Rectangle((szer, 0), 5, wys, color='red', alpha=0.6))
        ax.text(szer+15, wys/2, "➡ FRONT", rotation=270, va='center', color='red', weight='bold', fontsize=font_size_front)

    legenda = []
    if ma_prow: legenda.append("🔴 Prowadnice")
    if ma_konf: legenda.append("🔵 Konfirmaty")
    if ma_polka: legenda.append("🟢 Półki")
    
    opis_osi = "Szerokość (mm)\nLEGENDA: " + " | ".join(legenda) if legenda else "Szerokość (mm)"
    ax.set_xlabel(opis_osi, fontsize=9); ax.set_ylabel("Wysokość (mm)")
    margines = max(szer, wys) * 0.2
    ax.set_xlim(-margines, szer + margines); ax.set_ylim(-margines, wys + margines)
    ax.set_aspect('equal')
    
    tytul_pelny = f"ID: {id_elementu} | {nazwa}\n{podtytul}" if podtytul else f"ID: {id_elementu} | {nazwa}"
    ax.set_title(f"{tytul_pelny}\nWymiar: {szer:.1f} x {wys:.1f} mm", fontsize=12, weight='bold', pad=10)
    ax.grid(True, linestyle='--', alpha=0.5)
    return fig# 
    ==========================================
# 2. NESTING
# ==========================================
def optymalizuj_rozkroj(formatki, arkusz_w, arkusz_h, rzaz=4):
    formatki_sorted = sorted(formatki, key=lambda x: x['Szerokość [mm]'] * x['Wysokość [mm]'], reverse=True)
    arkusze = []
    aktualny_arkusz = {'elementy': [], 'zuzycie_m2': 0}
    cur_x, cur_y, max_h_row = 0, 0, 0
    
    for f in formatki_sorted:
        w, h = f['Szerokość [mm]'], f['Wysokość [mm]']
        if w > arkusz_w or h > arkusz_h: continue 
        if cur_x + w + rzaz > arkusz_w: 
            cur_x = 0; cur_y += max_h_row + rzaz; max_h_row = 0
        if cur_y + h + rzaz > arkusz_h: 
            arkusze.append(aktualny_arkusz)
            aktualny_arkusz = {'elementy': [], 'zuzycie_m2': 0}
            cur_x, cur_y, max_h_row = 0, 0, 0
        aktualny_arkusz['elementy'].append({'x': cur_x, 'y': cur_y, 'w': w, 'h': h, 'id': f['ID']})
        aktualny_arkusz['zuzycie_m2'] += (w * h) / 1000000
        cur_x += w + rzaz
        if h > max_h_row: max_h_row = h
    if aktualny_arkusz['elementy']: arkusze.append(aktualny_arkusz)
    return arkusze

# ==========================================
# 3. KONFIGURACJA (SIDEBAR)
# ==========================================
BAZA_SYSTEMOW = {
    "GTV Axis Pro": {"offset_prowadnica": 37.5, "offset_front_y": 47.5, "offset_front_x": 15.5, "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87, "wysokosci_tylu": {"A": 84, "B": 116, "C": 167, "D": 199}},
    "Blum Antaro": {"offset_prowadnica": 37.0, "offset_front_y": 45.5, "offset_front_x": 15.5, "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87, "wysokosci_tylu": {"M": 83, "K": 115, "C": 167, "D": 200}}
}

with st.sidebar:
    st.title("🪚 STOLARZPRO V16")
    st.caption("Tryb: DEBUG / PRO")
    if st.button("🗑️ RESET USTAWIEŃ", type="primary", use_container_width=True):
        resetuj_projekt()
        st.rerun()

    st.markdown("---")
    st.header("1. Wymiary Gabarytowe")
    KOD_PROJEKTU = st.text_input("Nazwa", key='kod_pro').upper()
    c1, c2 = st.columns(2)
    H_MEBLA = c1.number_input("Wysokość", key='h_mebla')
    W_MEBLA = c2.number_input("Szerokość", key='w_mebla')
    D_MEBLA = c1.number_input("Głębokość", key='d_mebla')
    GR_PLYTY = c2.number_input("Grubość Płyty", key='gr_plyty')
    
    st.header("2. Podział Wnętrza")
    ilosc_przegrod = st.number_input("Ilość pionowych przegród", min_value=0, key='il_przegrod')
    ilosc_sekcji = ilosc_przegrod + 1
    
    st.markdown("---")
    st.subheader(f"🎛️ Moduły ({ilosc_sekcji})")
    
    konfiguracja = []
    for i in range(ilosc_sekcji):
        with st.expander(f"Sekcja {i+1}", expanded=True):
            typ = st.selectbox(f"Typ zawartości #{i+1}", ["Szuflady", "Półka", "Pusta"], key=f"typ_{i}")
            detale = {'typ': typ, 'ilosc': 0}
            if typ == "Szuflady":
                detale['ilosc'] = st.number_input(f"Ilość szuflad #{i+1}", 1, 5, 2, key=f"ile_{i}")
            elif typ == "Półka":
                detale['ilosc'] = 1
            konfiguracja.append(detale)

    st.markdown("---")
    st.header("3. Detale Techniczne")
    sys_k = st.selectbox("System szuflad", list(BAZA_SYSTEMOW.keys()), key='sys_szuflad')
    params = BAZA_SYSTEMOW[sys_k]
    typ_boku_key = st.selectbox("Wys. boku", list(params["wysokosci_tylu"].keys()), index=2, key='typ_boku')
    axis_fuga = st.number_input("Fuga frontów", key='fuga')
    axis_nl = st.selectbox("NL (Długość)", [300,350,400,450,500,550], index=4, key='nl')
    typ_plecow = st.selectbox("Plecy", ["Nakładane", "Wpuszczane", "Brak"], key='typ_plecow')
    
    st.header("4. Rozkrój")
    ARKUSZ_W = st.number_input("Szer. arkusza", key='arkusz_w')
    ARKUSZ_H = st.number_input("Wys. arkusza", key='arkusz_h')
    RZAZ = st.number_input("Rzaz", key='rzaz')

# ==========================================
# 4. LOGIKA GŁÓWNA
# ==========================================
szer_wew_total = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)
szer_jednej_wneki = szer_wew_total / ilosc_sekcji
wys_wewnetrzna = H_MEBLA - (2 * GR_PLYTY)
lista_elementow = []

def dodaj_element(nazwa, szer, wys, gr, material, uwagi="", wiercenia=[], orientacja="L", strony_do_druku=None):
    kategoria_mat, kolor_tla = "INNE", '#e6ccb3'
    # Półka ruchoma idzie do materiału KORPUS
    if nazwa in ["Bok Lewy", "Bok Prawy", "Wieniec Górny", "Wieniec Dolny", "Przegroda", "Półka"]:
        kategoria_mat = "18mm KORPUS"; kolor_tla = '#e6ccb3'
    elif nazwa == "Front Szuflady":
        kategoria_mat = "18mm FRONT"; kolor_tla = '#d4a373'
    elif nazwa in ["Dno Szuflady", "Tył Szuflady"]:
        kategoria_mat = "16mm WNĘTRZE"; kolor_tla = '#ffffff'
    elif nazwa == "Plecy HDF":
        kategoria_mat = "3mm HDF"; kolor_tla = '#8d99ae'

    count = sum(1 for x in lista_elementow if x['typ'] == nazwa) + 1
    skroty = {"Bok Lewy": "BOK-L", "Bok Prawy": "BOK-P", "Przegroda": "PRZEG", "Front Szuflady": "FR", "Półka": "POLKA"}
    kod = skroty.get(nazwa, "EL")
    ident = f"{KOD_PROJEKTU}-{kod}" if nazwa in ["Bok Lewy", "Bok Prawy"] else f"{KOD_PROJEKTU}-{kod}-{count}"
    
    lista_elementow.append({
        "ID": ident, "Nazwa": nazwa, "typ": nazwa, 
        "Szerokość [mm]": round(szer, 1), "Wysokość [mm]": round(wys, 1), 
        "Grubość [mm]": gr, "Materiał": kategoria_mat, 
        "Uwagi": uwagi, "wiercenia": wiercenia, "kolor_tla": kolor_tla, "orientacja": orientacja,
        "strony_do_druku": strony_do_druku
    })

def daj_otwory_dla_sekcji(typ_sekcji, ilosc, strona_plyty, custom_str=""):
    otwory = []
    # Parametry wierceń bocznych (System 32mm)
    offset_x = 37.0 if strona_plyty == 'L' else (D_MEBLA - 37.0)
    offset_x_2 = 261.0 if strona_plyty == 'L' else (D_MEBLA - 261.0)
    
    # OFFSET DLA PODPÓRKI (Kluczowa poprawka)
    # Wiercimy 2mm PONIŻEJ dolnej płaszczyzny półki, żeby uwzględnić grubość kołnierza podpórki
    offset_podporka = 2.0 
    
    if typ_sekcji == "Szuflady":
        h_frontu = (wys_wewnetrzna - ((ilosc + 1) * axis_fuga)) / ilosc
        akt_h = 0
        for i in range(ilosc):
            y = akt_h + axis_fuga + params["offset_prowadnica"]
            otwory.append((offset_x, y, 'red'))
            otwory.append((offset_x_2, y, 'red'))
            akt_h += axis_fuga + h_frontu
            
    elif typ_sekcji == "Półka":
        y_holes = [] # Tu zbieramy współrzędne otworów (nie środków płyt!)
        
        # 1. Tryb Custom (użytkownik wpisał np. "200, 300")
        if custom_str and len(custom_str.strip()) > 0:
            try:
                wymiary = [float(x.strip()) for x in custom_str.split(',') if x.strip()]
                current_y = 0
                for w in wymiary:
                    y_dol_polki = current_y + w
                    # Wiercimy POD półką
                    y_holes.append(y_dol_polki - offset_podporka)
                    current_y = y_dol_polki + GR_PLYTY
            except:
                st.error("Błąd formatu wymiarów custom (użyj kropki dla ułamków)!")

        # 2. Tryb Auto (Równe odstępy)
        elif ilosc > 0:
            total_shelf_thickness = ilosc * GR_PLYTY
            space_for_gaps = wys_wewnetrzna - total_shelf_thickness
            gap_height = space_for_gaps / (ilosc + 1)
            
            for k in range(ilosc):
                # Obliczamy gdzie fizycznie wypada spód półki
                y_dol = (k + 1) * gap_height + (k * GR_PLYTY)
                # Wiercimy niżej o offset podpórki
                y_holes.append(y_dol - offset_podporka)
        
        # Generowanie punktów wierceń dla półek (zielone)
        for y in y_holes:
            otwory.append((offset_x, y, 'green'))
            x_tyl = (D_MEBLA - 37.0) if strona_plyty == 'L' else 37.0
            otwory.append((x_tyl, y, 'green'))
            
    return otwory
