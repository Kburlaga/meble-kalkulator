import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import io

st.set_page_config(page_title="STOLARZPRO - V11 (Multi-Materiał)", page_icon="🪚", layout="wide")

# ==========================================
# 0. ZARZĄDZANIE STANEM (RESET)
# ==========================================
def resetuj_projekt():
    defaults = {
        'kod_pro': "RTV-SALON", 'h_mebla': 600, 'w_mebla': 1800, 'd_mebla': 600, 'gr_plyty': 18,
        'il_przegrod': 2, 'typ_plecow': "Nakładane", 'sys_szuflad': "GTV Axis Pro", 'typ_boku': "C",
        'fuga': 3.0, 'il_szuflad': 2, 'nl': 500, 'arkusz_w': 2800, 'arkusz_h': 2070, 'rzaz': 4
    }
    for k, v in defaults.items(): st.session_state[k] = v
    st.session_state['pdf_ready'] = None

# Inicjalizacja
if 'kod_pro' not in st.session_state: resetuj_projekt()

# ==========================================
# 1. FUNKCJA RYSUJĄCA
# ==========================================
def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], kolor_tla='#e6ccb3'):
    fig, ax = plt.subplots(figsize=(10, 6))
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla)
    ax.add_patch(rect)
    
    ma_konf, ma_prow = False, False
    for otw in otwory:
        x, y = otw[0], otw[1]
        kolor = otw[2] if len(otw) > 2 else 'red'
        if kolor == 'blue': ma_konf = True
        if kolor == 'red': ma_prow = True
        circle = patches.Circle((x, y), radius=4, edgecolor=kolor, facecolor='white', linewidth=1.5)
        ax.add_patch(circle)
        if len(otwory) < 40:
            ax.text(x + 12, y + 5, f"({x:.1f}, {y:.1f})", fontsize=8, color=kolor, weight='bold')

    legenda = []
    if ma_prow: legenda.append("🔴 Czerwone: Prowadnice/Front")
    if ma_konf: legenda.append("🔵 Niebieskie: Konfirmaty")
    opis_osi = "Szerokość (mm)\nLEGENDA: " + "  |  ".join(legenda) if legenda else "Szerokość (mm)"
    
    ax.set_xlabel(opis_osi, fontsize=9); ax.set_ylabel("Wysokość (mm)")
    margines = max(szer, wys) * 0.1
    ax.set_xlim(-margines, szer + margines); ax.set_ylim(-margines, wys + margines)
    ax.set_aspect('equal')
    ax.set_title(f"ID: {id_elementu} | {nazwa}\nWymiar: {szer:.1f} x {wys:.1f} mm", fontsize=12, weight='bold', pad=10)
    ax.grid(True, linestyle='--', alpha=0.5)
    return fig

# ==========================================
# 2. ALGORYTM NESTINGU
# ==========================================
def optymalizuj_rozkroj(formatki, arkusz_w, arkusz_h, rzaz=4):
    # Sortujemy od największych
    formatki_sorted = sorted(formatki, key=lambda x: x['Szerokość [mm]'] * x['Wysokość [mm]'], reverse=True)
    arkusze = []
    aktualny_arkusz = {'elementy': [], 'zuzycie_m2': 0}
    cur_x, cur_y, max_h_row = 0, 0, 0
    
    for f in formatki_sorted:
        w, h = f['Szerokość [mm]'], f['Wysokość [mm]']
        # Sprawdzenie czy element w ogóle mieści się na arkuszu
        if w > arkusz_w or h > arkusz_h: continue # Pomijamy za duże elementy

        if cur_x + w + rzaz > arkusz_w: # Nowy rząd
            cur_x = 0; cur_y += max_h_row + rzaz; max_h_row = 0
        if cur_y + h + rzaz > arkusz_h: # Nowy arkusz
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
# 3. DANE SYSTEMÓW
# ==========================================
BAZA_SYSTEMOW = {
    "GTV Axis Pro": {"offset_prowadnica": 37.5, "offset_front_y": 47.5, "offset_front_x": 15.5, "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87, "wysokosci_tylu": {"A": 84, "B": 116, "C": 167, "D": 199}},
    "Blum Antaro": {"offset_prowadnica": 37.0, "offset_front_y": 45.5, "offset_front_x": 15.5, "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87, "wysokosci_tylu": {"M": 83, "K": 115, "C": 167, "D": 200}},
    "GTV Modern Box": {"offset_prowadnica": 37.0, "offset_front_y": 45.0, "offset_front_x": 15.5, "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87, "wysokosci_tylu": {"A": 84, "B": 135, "C": 199, "D": 224}}
}

# ==========================================
# 4. SIDEBAR
# ==========================================
with st.sidebar:
    st.title("🪚 STOLARZPRO")
    st.button("🗑️ RESET PROJEKTU", on_click=resetuj_projekt, type="primary", use_container_width=True)
    st.markdown("---")
    
    st.header("1. Projekt")
    KOD_PROJEKTU = st.text_input("Nazwa", key='kod_pro').upper()
    
    st.header("2. Wymiary Korpusu")
    c1, c2 = st.columns(2)
    with c1:
        H_MEBLA = st.number_input("Wys.", key='h_mebla')
        D_MEBLA = st.number_input("Głęb.", key='d_mebla')
    with c2:
        W_MEBLA = st.number_input("Szer.", key='w_mebla')
        GR_PLYTY = st.number_input("Gr. Płyty", key='gr_plyty')
    
    st.header("3. Konstrukcja")
    ilosc_przegrod = st.number_input("Przegrody", min_value=0, key='il_przegrod')
    typ_plecow = st.selectbox("Plecy", ["Nakładane", "Wpuszczane", "Brak"], key='typ_plecow')
    
    st.header("4. Szuflady")
    opcje_sys = list(BAZA_SYSTEMOW.keys()) + ["Custom"]
    wybrany_sys = st.selectbox("System", opcje_sys, key='sys_szuflad')
    
    if wybrany_sys == "Custom":
        params = {"offset_prowadnica": 37.5, "offset_front_y": 47.5, "offset_front_x": 15.5, "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87, "wysokosci_tylu": {"Custom": 167}}
        typ_boku_key = "Custom"
    else:
        params = BAZA_SYSTEMOW[wybrany_sys]
        boki_list = list(params["wysokosci_tylu"].keys())
        idx = 0
        if st.session_state['typ_boku'] in boki_list: idx = boki_list.index(st.session_state['typ_boku'])
        else: idx = len(boki_list)-1
        typ_boku_key = st.selectbox("Bok", boki_list, index=idx, key='typ_boku')

    c3, c4 = st.columns(2)
    with c3: axis_fuga = st.number_input("Fuga", key='fuga')
    with c4: axis_ilosc = st.slider("Ilość", 1, 5, key='il_szuflad')
    
    idx_nl = 4
    if st.session_state['nl'] in [300,350,400,450,500,550]: idx_nl = [300,350,400,450,500,550].index(st.session_state['nl'])
    axis_nl = st.selectbox("Długość", [300,350,400,450,500,550], index=idx_nl, key='nl')
    
    st.markdown("---")
    st.header("5. Ustawienia Piły")
    ARKUSZ_W = st.number_input("Szer. płyty", key='arkusz_w')
    ARKUSZ_H = st.number_input("Wys. płyty", key='arkusz_h')
    RZAZ = st.number_input("Rzaz", key='rzaz')

# ==========================================
# 5. LOGIKA & GENEROWANIE ELEMENTÓW
# ==========================================
ilosc_sekcji = ilosc_przegrod + 1
szer_wew_total = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)
szer_jednej_wneki = szer_wew_total / ilosc_sekcji
wys_wewnetrzna = H_MEBLA - (2 * GR_PLYTY)

lista_elementow = []

def dodaj_element(nazwa, szer, wys, gr, material, uwagi="", wiercenia=[]):
    # Automatyczne przypisanie kategorii materiałowej
    kategoria_mat = ""
    if nazwa in ["Bok Lewy", "Bok Prawy", "Wieniec Górny", "Wieniec Dolny", "Przegroda"]:
        kategoria_mat = "18mm KORPUS"
        kolor_tla = '#e6ccb3' # Drewno
    elif nazwa == "Front Szuflady":
        kategoria_mat = "18mm FRONT"
        kolor_tla = '#d4a373' # Ciemniejsze drewno
    elif nazwa in ["Dno Szuflady", "Tył Szuflady"]:
        kategoria_mat = "16mm WNĘTRZE"
        kolor_tla = '#ffffff' # Biały
    elif nazwa == "Plecy HDF":
        kategoria_mat = "3mm HDF"
        kolor_tla = '#8d99ae' # Szary
    else:
        kategoria_mat = "INNE"
        kolor_tla = '#e6ccb3'

    count = sum(1 for x in lista_elementow if x['typ'] == nazwa) + 1
    skroty = {"Bok Lewy": "BOK-L", "Bok Prawy": "BOK-P", "Wieniec Górny": "WIEN-G", "Wieniec Dolny": "WIEN-D", "Przegroda": "PRZEG", "Plecy HDF": "HDF", "Front Szuflady": "FR", "Dno Szuflady": "DNO", "Tył Szuflady": "TYL"}
    kod = skroty.get(nazwa, "EL")
    ident = f"{KOD_PROJEKTU}-{kod}" if nazwa in ["Bok Lewy", "Bok Prawy", "Wieniec Górny", "Wieniec Dolny"] else f"{KOD_PROJEKTU}-{kod}-{count}"
    
    lista_elementow.append({
        "ID": ident, "Nazwa": nazwa, "typ": nazwa, 
        "Szerokość [mm]": round(szer, 1), "Wysokość [mm]": round(wys, 1), 
        "Grubość [mm]": gr, "Materiał": kategoria_mat, 
        "Uwagi": uwagi, "wiercenia": wiercenia, "kolor_tla": kolor_tla
    })

# --- OBLICZENIA WIERCEŃ ---
wiercenia_prow = []
akt_h = 0
h_frontu = (wys_wewnetrzna - ((axis_ilosc + 1) * axis_fuga)) / axis_ilosc
for i in range(axis_ilosc):
    pos = akt_h + axis_fuga + params["offset_prowadnica"]
    wiercenia_prow.append(pos)
    akt_h += axis_fuga + h_frontu

otwory_bok = [(37.0, y, 'red') for y in wiercenia_prow] + [(261.0, y, 'red') for y in wiercenia_prow]

# --- KORPUS ---
dodaj_element("Bok Lewy", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "", "", otwory_bok)
dodaj_element("Bok Prawy", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "", "", otwory_bok)

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

for i in range(ilosc_przegrod):
    dodaj_element("Przegroda", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "", "2-str", otwory_bok)

# --- PLECY ---
hdf_h = H_MEBLA - 4 if typ_plecow == "Nakładane" else H_MEBLA - 20
hdf_w = W_MEBLA - 4 if typ_plecow == "Nakładane" else W_MEBLA - 20
if typ_plecow != "Brak": dodaj_element("Plecy HDF", hdf_w, hdf_h, 3, "")

# --- SZUFLADY ---
czy_wszystkie = st.sidebar.checkbox("Szuflady w każdej sekcji?", value=True)
sekcje_do_wypelnienia = ilosc_sekcji if czy_wszystkie else 1
w_fr = szer_jednej_wneki - (2 * axis_fuga)
dno_w, dno_l = szer_jednej_wneki - params["redukcja_dna_szer"], axis_nl - params["redukcja_dna_dl"]
tyl_w, tyl_h = szer_jednej_wneki - params["redukcja_tyl_szer"], params["wysokosci_tylu"][typ_boku_key]
wx, wy = params["offset_front_x"] - axis_fuga, params["offset_front_y"]
otw_front = [(wx, wy, 'red'), (wx, wy+32, 'red'), (w_fr-wx, wy, 'red'), (w_fr-wx, wy+32, 'red')]

for s in range(sekcje_do_wypelnienia):
    for sz in range(axis_ilosc):
        dodaj_element("Front Szuflady", w_fr, h_frontu, 18, "", f"S{s+1}", otw_front)
        dodaj_element("Dno Szuflady", dno_l, dno_w, 16, "", "")
        dodaj_element("Tył Szuflady", tyl_w, tyl_h, 16, "", "")

# ==========================================
# 6. WIDOKI (TABS)
# ==========================================
df = pd.DataFrame(lista_elementow)
t1, t2, t3 = st.tabs(["📋 LISTA", "📐 DOKUMENTACJA", "🗺️ ROZKRÓJ (NESTING)"])

with t1:
    st.subheader(f"Projekt: {KOD_PROJEKTU}")
    # Grupowanie po materiale
    for mat in sorted(df['Materiał'].unique()):
        st.caption(f"Kategoria: {mat}")
        sub_df = df[df['Materiał'] == mat].drop(columns=['typ','wiercenia','kolor_tla'])
        st.dataframe(sub_df, hide_index=True, use_container_width=True)
    
    st.divider()
    st.download_button("📥 Pobierz Pełną Listę (CSV)", df.drop(columns=['typ','wiercenia','kolor_tla']).to_csv(index=False).encode('utf-8'), f'{KOD_PROJEKTU}.csv', 'text/csv')

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
                        fig = rysuj_element(e['Szerokość [mm]'], e['Wysokość [mm]'], e['ID'], e['Nazwa'], e['wiercenia'], e['kolor_tla'])
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
        st.pyplot(rysuj_element(it['Szerokość [mm]'], it['Wysokość [mm]'], it['ID'], it['Nazwa'], it['wiercenia'], it['kolor_tla']))

with t3:
    st.subheader("Optymalizacja Rozkroju (Nesting)")
    st.info(f"Symulacja dla płyty: {ARKUSZ_W}x{ARKUSZ_H} mm (Rzaz: {RZAZ}mm)")
    
    if st.button("Uruchom Rozkrój"):
        # Unikalne materiały
        materialy = sorted(df['Materiał'].unique())
        
        for mat in materialy:
            st.markdown(f"### 🪚 {mat}")
            czesci = [x for x in lista_elementow if x['Materiał'] == mat]
            
            if not czesci:
                st.write("Brak elementów.")
                continue
                
            wynik = optymalizuj_rozkroj(czesci, ARKUSZ_W, ARKUSZ_H, RZAZ)
            st.success(f"Ilość arkuszy: {len(wynik)}")
            
            # Rysowanie arkuszy dla danego materiału
            for i, ark in enumerate(wynik):
                fig, ax = plt.subplots(figsize=(10, 6))
                # Tło arkusza
                ax.add_patch(patches.Rectangle((0,0), ARKUSZ_W, ARKUSZ_H, facecolor='#f0f0f0', edgecolor='black'))
                
                # Elementy
                for e in ark['elementy']:
                    # Pobieramy kolor przypisany do elementu z listy głównej
                    orig = next(x for x in lista_elementow if x['ID'] == e['id'])
                    ax.add_patch(patches.Rectangle((e['x'], e['y']), e['w'], e['h'], facecolor=orig['kolor_tla'], edgecolor='black', alpha=0.8))
                    
                    if e['w']>100 and e['h']>50:
                        ax.text(e['x']+e['w']/2, e['y']+e['h']/2, e['id'], ha='center', va='center', fontsize=6, rotation=0)
                
                ax.set_xlim(-100, ARKUSZ_W+100); ax.set_ylim(-100, ARKUSZ_H+100); ax.set_aspect('equal')
                ax.set_title(f"{mat} | Arkusz {i+1} | Odpad: {100 - (ark['zuzycie_m2'] / ((ARKUSZ_W*ARKUSZ_H)/1000000) * 100):.1f}%")
                st.pyplot(fig)
