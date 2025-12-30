import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import io

st.set_page_config(page_title="STOLARZPRO - V14 (Modularna)", page_icon="🪚", layout="wide")

# ==========================================
# 0. RESETOWANIE I STANY
# ==========================================
def resetuj_projekt():
    defaults = {
        'kod_pro': "RTV-MODUL", 'h_mebla': 600, 'w_mebla': 1800, 'd_mebla': 600, 'gr_plyty': 18,
        'il_przegrod': 2, 'typ_plecow': "Nakładane", 'sys_szuflad': "GTV Axis Pro", 'typ_boku': "C",
        'fuga': 3.0, 'nl': 500, 'arkusz_w': 2800, 'arkusz_h': 2070, 'rzaz': 4,
        'konfig_sekcji': {} # Słownik do trzymania ustawień per sekcja
    }
    for k, v in defaults.items(): st.session_state[k] = v
    st.session_state['pdf_ready'] = None

if 'kod_pro' not in st.session_state: resetuj_projekt()

# ==========================================
# 1. FUNKCJA RYSUJĄCA (ZAAWANSOWANA)
# ==========================================
def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], kolor_tla='#e6ccb3', orientacja_frontu="L"):
    """
    Rysuje element z zaznaczeniem frontu i typami otworów.
    orientacja_frontu: 'L' (lewa krawędź to front), 'P' (prawa to front)
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Płyta
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla)
    ax.add_patch(rect)
    
    # Otwory
    ma_konf, ma_prow, ma_polka = False, False, False
    for otw in otwory:
        x, y = otw[0], otw[1]
        kolor = otw[2] if len(otw) > 2 else 'red'
        
        if kolor == 'blue': ma_konf = True
        elif kolor == 'red': ma_prow = True
        elif kolor == 'green': ma_polka = True
        
        # Rysujemy kropkę
        circle = patches.Circle((x, y), radius=4, edgecolor=kolor, facecolor='white', linewidth=1.5)
        ax.add_patch(circle)
        
        # Etykieta (tylko jeśli nie ma tłoku)
        if len(otwory) < 60:
            ax.text(x + 10, y + 5, f"({x:.1f}, {y:.1f})", fontsize=6, color=kolor, weight='bold')

    # OZNACZENIE FRONTU
    font_size_front = 10
    if orientacja_frontu == "L": # Front po lewej (X=0)
        ax.add_patch(patches.Rectangle((-5, 0), 5, wys, color='red', alpha=0.6))
        ax.text(-25, wys/2, "FRONT ⬅", rotation=90, va='center', color='red', weight='bold', fontsize=font_size_front)
    else: # Front po prawej (X=Szer)
        ax.add_patch(patches.Rectangle((szer, 0), 5, wys, color='red', alpha=0.6))
        ax.text(szer+15, wys/2, "➡ FRONT", rotation=270, va='center', color='red', weight='bold', fontsize=font_size_front)

    # Legenda
    legenda = []
    if ma_prow: legenda.append("🔴 Prowadnice")
    if ma_konf: legenda.append("🔵 Konfirmaty")
    if ma_polka: legenda.append("🟢 Półki")
    
    opis_osi = "Szerokość (mm)\nLEGENDA: " + " | ".join(legenda) if legenda else "Szerokość (mm)"
    ax.set_xlabel(opis_osi, fontsize=9); ax.set_ylabel("Wysokość (mm)")
    
    margines = max(szer, wys) * 0.2
    ax.set_xlim(-margines, szer + margines); ax.set_ylim(-margines, wys + margines)
    ax.set_aspect('equal')
    ax.set_title(f"ID: {id_elementu} | {nazwa}\nWymiar: {szer:.1f} x {wys:.1f} mm", fontsize=12, weight='bold', pad=10)
    ax.grid(True, linestyle='--', alpha=0.5)
    return fig

# ==========================================
# 2. NESTING (BEZ ZMIAN)
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
# 3. SIDEBAR & KONFIGURACJA MODUŁOWA
# ==========================================
BAZA_SYSTEMOW = {
    "GTV Axis Pro": {"offset_prowadnica": 37.5, "offset_front_y": 47.5, "offset_front_x": 15.5, "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87, "wysokosci_tylu": {"A": 84, "B": 116, "C": 167, "D": 199}},
    "Blum Antaro": {"offset_prowadnica": 37.0, "offset_front_y": 45.5, "offset_front_x": 15.5, "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87, "wysokosci_tylu": {"M": 83, "K": 115, "C": 167, "D": 200}}
}

with st.sidebar:
    st.title("🪚 STOLARZPRO")
    st.button("🗑️ RESET", on_click=resetuj_projekt, type="primary", use_container_width=True)
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
    st.subheader(f"🎛️ Konfiguracja Modułów ({ilosc_sekcji})")
    
    # DYNAMICZNY GENERATOR MODUŁÓW
    # Tworzymy listę konfiguracji dla każdej sekcji
    konfiguracja = []
    
    for i in range(ilosc_sekcji):
        with st.expander(f"Sekcja {i+1} (od lewej)", expanded=True):
            typ = st.selectbox(f"Typ zawartości #{i+1}", ["Szuflady", "Półka", "Pusta"], key=f"typ_{i}")
            
            detale = {'typ': typ, 'ilosc': 0}
            if typ == "Szuflady":
                ile = st.number_input(f"Ilość szuflad #{i+1}", 1, 5, 2, key=f"ile_{i}")
                detale['ilosc'] = ile
            elif typ == "Półka":
                detale['ilosc'] = 1 # Domyślnie 1 półka
                
            konfiguracja.append(detale)
            
    st.markdown("---")
    st.header("3. Detale Techniczne")
    opcje_sys = list(BAZA_SYSTEMOW.keys())
    wybrany_sys = st.selectbox("System szuflad", opcje_sys, key='sys_szuflad')
    params = BAZA_SYSTEMOW[wybrany_sys]
    typ_boku_key = st.selectbox("Wysokość boku szuflady", list(params["wysokosci_tylu"].keys()), index=2, key='typ_boku')
    
    axis_fuga = st.number_input("Fuga frontów", key='fuga')
    axis_nl = st.selectbox("Długość prowadnicy (NL)", [300,350,400,450,500,550], index=4, key='nl')
    
    typ_plecow = st.selectbox("Plecy", ["Nakładane", "Wpuszczane", "Brak"], key='typ_plecow')
    
    st.header("4. Rozkrój")
    ARKUSZ_W = st.number_input("Szer. arkusza", key='arkusz_w')
    ARKUSZ_H = st.number_input("Wys. arkusza", key='arkusz_h')
    RZAZ = st.number_input("Rzaz", key='rzaz')

# ==========================================
# 4. SILNIK OBLICZENIOWY
# ==========================================
szer_wew_total = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)
szer_jednej_wneki = szer_wew_total / ilosc_sekcji
wys_wewnetrzna = H_MEBLA - (2 * GR_PLYTY)

lista_elementow = []

def dodaj_element(nazwa, szer, wys, gr, material, uwagi="", wiercenia=[], orientacja="L"):
    # Kolory i kategorie
    kategoria_mat, kolor_tla = "INNE", '#e6ccb3'
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
        "Uwagi": uwagi, "wiercenia": wiercenia, "kolor_tla": kolor_tla, "orientacja": orientacja
    })

# --- FUNKCJA GENERUJĄCA OTWORY DLA DANEJ SEKCJI ---
def daj_otwory_dla_sekcji(typ_sekcji, ilosc, strona_plyty):
    """
    Zwraca listę współrzędnych Y dla danej konfiguracji.
    strona_plyty: 'L' (wiercimy przy X=37), 'P' (wiercimy przy X=Szer-37)
    """
    otwory = []
    offset_x = 37.0 if strona_plyty == 'L' else (D_MEBLA - 37.0)
    offset_x_2 = 261.0 if strona_plyty == 'L' else (D_MEBLA - 261.0)
    
    if typ_sekcji == "Szuflady":
        h_frontu = (wys_wewnetrzna - ((ilosc + 1) * axis_fuga)) / ilosc
        akt_h = 0
        for i in range(ilosc):
            y = akt_h + axis_fuga + params["offset_prowadnica"]
            otwory.append((offset_x, y, 'red'))
            otwory.append((offset_x_2, y, 'red'))
            akt_h += axis_fuga + h_frontu
            
    elif typ_sekcji == "Półka":
        y = wys_wewnetrzna / 2
        otwory.append((offset_x, y, 'green'))
        # Dla półki drugi otwór jest z tyłu, więc odwracamy logikę dla drugiego X
        x_tyl = (D_MEBLA - 37.0) if strona_plyty == 'L' else 37.0
        otwory.append((x_tyl, y, 'green'))
        
    return otwory

# --- A. GENEROWANIE KONSTRUKCJI (ŚCIANY PIONOWE) ---

# 1. BOK LEWY (Zamyka Sekcję 1 od lewej)
# Patrzy na Sekcję 0 (pierwszą).
# Orientacja: Front P (bo to lewy bok szafki).
# Wiercenia: Muszą pasować do Sekcji 0, ale umieszczone na "Prawej" stronie płyty (wewnętrznej).
# W naszej logice 'rysuj_element': Orientacja 'P' ma front przy X=Szer. Wiercenia dla sekcji powinny być od strony frontu.
otwory_bok_L = daj_otwory_dla_sekcji(konfiguracja[0]['typ'], konfiguracja[0]['ilosc'], 'P')
dodaj_element("Bok Lewy", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "", "", otwory_bok_L, "P")

# 2. BOK PRAWY (Zamyka Sekcję Ostatnią od prawej)
# Patrzy na Sekcję -1 (ostatnią).
# Orientacja: Front L (bo to prawy bok szafki).
otwory_bok_P = daj_otwory_dla_sekcji(konfiguracja[-1]['typ'], konfiguracja[-1]['ilosc'], 'L')
dodaj_element("Bok Prawy", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "", "", otwory_bok_P, "L")

# 3. PRZEGRODY (Rozdzielają Sekcje)
for i in range(ilosc_przegrod):
    # Przegroda nr 'i' rozdziela Sekcję 'i' (z lewej) i Sekcję 'i+1' (z prawej).
    
    # Lewa strona przegrody (Front L): Obsługuje Sekcję 'i' (która jest po lewej od przegrody? Nie!)
    # Czekaj. Przegroda stoi we wnętrzu.
    # Lewa ściana przegrody (patrząc od przodu) "patrzy" w lewo -> na Sekcję 'i'.
    # Prawa ściana przegrody "patrzy" w prawo -> na Sekcję 'i+1'.
    
    # Wiercenia Lewe (dla Sekcji 'i'):
    # Ponieważ lewa ściana przegrody jest "Prawą ścianą wnęki nr i", wiercenia są jak w Boku Prawym (X=37, Front L).
    otwory_lewa_strona = daj_otwory_dla_sekcji(konfiguracja[i]['typ'], konfiguracja[i]['ilosc'], 'L')
    
    # Wiercenia Prawe (dla Sekcji 'i+1'):
    # Prawa ściana przegrody jest "Lewą ścianą wnęki nr i+1", wiercenia jak w Boku Lewym (X=Szer-37, Front P).
    # Ale uwaga: Rysujemy płytę 2D. Otwory z obu stron lądują na jednym rysunku ("prześwietlenie").
    # Więc po prostu sumujemy listy otworów.
    otwory_prawa_strona = daj_otwory_dla_sekcji(konfiguracja[i+1]['typ'], konfiguracja[i+1]['ilosc'], 'P')
    
    wszystkie_otwory = otwory_lewa_strona + otwory_prawa_strona
    
    # Orientacja wizualna: Przyjmijmy 'L' jako standard dla przegród, ale front jest po obu stronach ten sam.
    dodaj_element("Przegroda", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "", f"Między S{i+1} a S{i+2}", wszystkie_otwory, "L")

# --- B. WIEŃCE I PLECY (STANDARD) ---
otwory_wien = []
y_k1, y_k2 = 50, D_MEBLA - 50
otwory_wien.extend([(GR_PLYTY/2, y_k1, 'blue'), (GR_PLYTY/2, y_k2, 'blue')])
otwory_wien.extend([(W_MEBLA-GR_PLYTY/2, y_k1, 'blue'), (W_MEBLA-GR_PLYTY/2, y_k2, 'blue')])
cx = GR_PLYTY
for i in range(ilosc_przegrod):
    cx += szer_jednej_wneki
    otwory_wien.extend([(cx+GR_PLYTY/2, y_k1, 'blue'), (cx+GR_PLYTY/2, y_k2, 'blue')])
    cx += GR_PLYTY
dodaj_element("Wieniec Górny", W_MEBLA, D_MEBLA, GR_PLYTY, "", "", otwory_wien)
dodaj_element("Wieniec Dolny", W_MEBLA, D_MEBLA, GR_PLYTY, "", "", otwory_wien)

hdf_h = H_MEBLA - 4 if typ_plecow == "Nakładane" else H_MEBLA - 20
hdf_w = W_MEBLA - 4 if typ_plecow == "Nakładane" else W_MEBLA - 20
if typ_plecow != "Brak": dodaj_element("Plecy HDF", hdf_w, hdf_h, 3, "")

# --- C. WYPEŁNIENIE SEKCJI (ZAWARTOŚĆ) ---
for idx, konfig in enumerate(konfiguracja):
    typ = konfig['typ']
    ilosc = konfig['ilosc']
    nr_sekcji = idx + 1
    
    if typ == "Szuflady":
        h_frontu = (wys_wewnetrzna - ((ilosc + 1) * axis_fuga)) / ilosc
        w_fr = szer_jednej_wneki - (2 * axis_fuga)
        
        # Wymiary wnętrza
        dno_w = szer_jednej_wneki - params["redukcja_dna_szer"]
        dno_l = axis_nl - params["redukcja_dna_dl"]
        tyl_w = szer_jednej_wneki - params["redukcja_tyl_szer"]
        tyl_h = params["wysokosci_tylu"][typ_boku_key]
        
        # Wiercenia we froncie
        wx, wy = params["offset_front_x"] - axis_fuga, params["offset_front_y"]
        otw_front = [(wx, wy, 'red'), (wx, wy+32, 'red'), (w_fr-wx, wy, 'red'), (w_fr-wx, wy+32, 'red')]
        
        for sz in range(ilosc):
            dodaj_element("Front Szuflady", w_fr, h_frontu, 18, "", f"Sekcja {nr_sekcji}", otw_front)
            dodaj_element("Dno Szuflady", dno_l, dno_w, 16, "", "")
            dodaj_element("Tył Szuflady", tyl_w, tyl_h, 16, "", "")
            
    elif typ == "Półka":
        w_polki = szer_jednej_wneki - 2
        d_polki = D_MEBLA - 20
        dodaj_element("Półka", w_polki, d_polki, 18, "", f"Sekcja {nr_sekcji}", [])

# ==========================================
# 5. PREZENTACJA DANYCH
# ==========================================
df = pd.DataFrame(lista_elementow)
t1, t2, t3 = st.tabs(["📋 LISTA", "📐 DOKUMENTACJA", "🗺️ ROZKRÓJ"])

with t1:
    st.subheader(f"Projekt: {KOD_PROJEKTU}")
    for mat in sorted(df['Materiał'].unique()):
        st.caption(f"Kategoria: {mat}")
        st.dataframe(df[df['Materiał'] == mat].drop(columns=['typ','wiercenia','kolor_tla','orientacja']), hide_index=True, use_container_width=True)
    st.download_button("📥 Pobierz Pełną Listę (CSV)", df.drop(columns=['typ','wiercenia','kolor_tla','orientacja']).to_csv(index=False).encode('utf-8'), f'{KOD_PROJEKTU}.csv', 'text/csv')

with t2:
    st.subheader("🖨️ Dokumentacja")
    col1, col2 = st.columns([1,2])
    with col1:
        if st.button("🚀 GENERUJ PDF", type="primary"):
            with st.spinner("Generowanie..."):
                pdf_buffer = io.BytesIO()
                with PdfPages(pdf_buffer) as pdf:
                    els = [e for e in lista_elementow if e['wiercenia'] or e['Nazwa'] == 'Front Szuflady']
                    for e in els:
                        fig = rysuj_element(e['Szerokość [mm]'], e['Wysokość [mm]'], e['ID'], e['Nazwa'], e['wiercenia'], e['kolor_tla'], e['orientacja'])
                        pdf.savefig(fig); plt.close(fig)
                    pdf_buffer.seek(0)
                    st.session_state['pdf_ready'] = pdf_buffer
    with col2:
        if st.session_state.get('pdf_ready'):
            st.success("Gotowe!")
            st.download_button("📥 POBIERZ PDF", st.session_state['pdf_ready'], f"{KOD_PROJEKTU}_Rysunki.pdf", "application/pdf")
    
    st.divider()
    st.caption("Podgląd elementu:")
    ids = [r['ID'] for r in lista_elementow if r['wiercenia'] or r['Nazwa']=='Front Szuflady']
    if ids:
        sel = st.selectbox("Wybierz:", ids)
        it = next(x for x in lista_elementow if x['ID'] == sel)
        st.pyplot(rysuj_element(it['Szerokość [mm]'], it['Wysokość [mm]'], it['ID'], it['Nazwa'], it['wiercenia'], it['kolor_tla'], it['orientacja']))

with t3:
    st.subheader("Optymalizacja Rozkroju")
    if st.button("Uruchom Rozkrój"):
        materialy = sorted(df['Materiał'].unique())
        for mat in materialy:
            st.markdown(f"### 🪚 {mat}")
            czesci = [x for x in lista_elementow if x['Materiał'] == mat]
            if not czesci: continue
            wynik = optymalizuj_rozkroj(czesci, ARKUSZ_W, ARKUSZ_H, RZAZ)
            st.success(f"Ilość arkuszy: {len(wynik)}")
            for i, ark in enumerate(wynik):
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.add_patch(patches.Rectangle((0,0), ARKUSZ_W, ARKUSZ_H, facecolor='#f0f0f0', edgecolor='black'))
                for e in ark['elementy']:
                    orig = next(x for x in lista_elementow if x['ID'] == e['id'])
                    ax.add_patch(patches.Rectangle((e['x'], e['y']), e['w'], e['h'], facecolor=orig['kolor_tla'], edgecolor='black', alpha=0.8))
                    if e['w']>100 and e['h']>50:
                        ax.text(e['x']+e['w']/2, e['y']+e['h']/2, e['id'], ha='center', va='center', fontsize=6)
                ax.set_xlim(-100, ARKUSZ_W+100); ax.set_ylim(-100, ARKUSZ_H+100); ax.set_aspect('equal')
                st.pyplot(fig)
