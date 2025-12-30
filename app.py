import streamlit as st

import matplotlib.pyplot as plt

import matplotlib.patches as patches

from matplotlib.backends.backend_pdf import PdfPages

import pandas as pd

import io

st.set_page_config(page_title="STOLARZPRO - V18 (2D Preview)", page_icon="🪚", layout="wide")

# ==========================================

# 0. RESETOWANIE

# ==========================================

def resetuj_projekt():

    defaults = {

        'kod_pro': "RTV-PRO-2D", 'h_mebla': 600, 'w_mebla': 1800, 'd_mebla': 600, 'gr_plyty': 18,

        'il_przegrod': 2, 'typ_plecow': "Nakładane", 'sys_szuflad': "GTV Axis Pro", 'typ_boku': "C",

        'fuga': 3.0, 'nl': 500, 'arkusz_w': 2800, 'arkusz_h': 2070, 'rzaz': 4

    }

    for k, v in defaults.items(): st.session_state[k] = v

    st.session_state['pdf_ready'] = None

if 'kod_pro' not in st.session_state: resetuj_projekt()

# ==========================================

# 1. FUNKCJE RYSUNKOWE (TECHNICZNE)

# ==========================================

def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], kolor_tla='#e6ccb3', orientacja_frontu="L", podtytul=""):

    fig, ax = plt.subplots(figsize=(10, 6))

    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla)

    ax.add_patch(rect)

    for otw in otwory:

        x, y, kolor = otw[0], otw[1], (otw[2] if len(otw) > 2 else 'red')

        ax.add_patch(patches.Circle((x, y), radius=4, edgecolor=kolor, facecolor='white', linewidth=1.5))

        if len(otwory) < 60:

            ax.text(x + 10, y + 5, f"({x:.1f}, {y:.1f})", fontsize=6, color=kolor, weight='bold')

    if orientacja_frontu == "L":

        ax.add_patch(patches.Rectangle((-5, 0), 5, wys, color='red', alpha=0.6))

    else:

        ax.add_patch(patches.Rectangle((szer, 0), 5, wys, color='red', alpha=0.6))

    ax.set_aspect('equal')

    ax.set_title(f"{id_elementu} | {nazwa}\n{podtytul}", fontsize=12, weight='bold')

    return fig

# WIZUALIZACJA 2D CAŁEGO MEBLA

def rysuj_podglad_mebla(w, h, gr, n_przeg, konfig, szer_wneki):

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.add_patch(patches.Rectangle((0, 0), w, h, linewidth=3, edgecolor='black', facecolor='none'))

    ax.add_patch(patches.Rectangle((0, 0), w, gr, facecolor='#d7ba9d', edgecolor='black', alpha=0.5))

    ax.add_patch(patches.Rectangle((0, h-gr), w, gr, facecolor='#d7ba9d', edgecolor='black', alpha=0.5))

    ax.add_patch(patches.Rectangle((0, gr), gr, h-2*gr, facecolor='#d7ba9d', edgecolor='black', alpha=0.5))

    ax.add_patch(patches.Rectangle((w-gr, gr), gr, h-2*gr, facecolor='#d7ba9d', edgecolor='black', alpha=0.5))

    

    curr_x = gr

    h_wew = h - 2*gr

    for idx, sekcja in enumerate(konfig):

        if idx < len(konfig) - 1:

            ax.add_patch(patches.Rectangle((curr_x + szer_wneki, gr), gr, h_wew, facecolor='gray', alpha=0.3))

        

        if sekcja['typ'] == "Szuflady":

            n = sekcja['ilosc']

            h_f = (h_wew - ((n + 1) * 3)) / n 

            for i in range(n):

                yf = gr + 3 + i*(h_f + 3)

                ax.add_patch(patches.Rectangle((curr_x+2, yf), szer_wneki-4, h_f, facecolor='#fdf0d5', edgecolor='#669bbc', linewidth=1))

                ax.add_patch(patches.Circle((curr_x + szer_wneki/2, yf + h_f*0.8), radius=5, color='black'))

        

        elif sekcja['typ'] == "Półka":

            n_p = sekcja['ilosc']

            for k in range(n_p):

                yp = gr + (k+1)*(h_wew / (n_p+1))

                ax.add_patch(patches.Rectangle((curr_x, yp), szer_wneki, 5, color='#bc6c25'))

        

        curr_x += szer_wneki + gr

    ax.set_xlim(-100, w + 100); ax.set_ylim(-100, h + 100)

    ax.set_aspect('equal')

    ax.set_title(f"WIZUALIZACJA FRONTOWA: {w}x{h}mm", fontsize=14, weight='bold')

    ax.axis('off')

    return fig

# ==========================================

# 3. INTERFEJS (SIDEBAR)

# ==========================================

BAZA_SYSTEMOW = {

    "GTV Axis Pro": {"offset_prowadnica": 37.5, "offset_front_y": 47.5, "offset_front_x": 15.5, "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87, "wysokosci_tylu": {"A": 84, "B": 116, "C": 167, "D": 199}},

    "Blum Antaro": {"offset_prowadnica": 37.0, "offset_front_y": 45.5, "offset_front_x": 15.5, "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87, "wysokosci_tylu": {"M": 83, "K": 115, "C": 167, "D": 200}}

}

with st.sidebar:

    st.title("🪚 STOLARZPRO V18")

    if st.button("🗑️ RESET", type="primary", use_container_width=True): resetuj_projekt(); st.rerun()

    st.markdown("---")

    st.header("1. Gabaryty")

    KOD_PROJEKTU = st.text_input("Nazwa", key='kod_pro').upper()

    c1, c2 = st.columns(2)

    H_MEBLA, W_MEBLA = c1.number_input("Wys.", key='h_mebla'), c2.number_input("Szer.", key='w_mebla')

    D_MEBLA, GR_PLYTY = c1.number_input("Głęb.", key='d_mebla'), c2.number_input("Grubość", key='gr_plyty')

    st.header("2. Wnętrze")

    ilosc_przegrod = st.number_input("Przegrody", min_value=0, key='il_przegrod')

    ilosc_sekcji = ilosc_przegrod + 1

    konfiguracja = []

    for i in range(ilosc_sekcji):

        with st.expander(f"Sekcja {i+1}", expanded=True):

            typ = st.selectbox(f"Typ #{i+1}", ["Szuflady", "Półka", "Pusta"], key=f"typ_{i}")

            det = {'typ': typ, 'ilosc': 0, 'custom_str': ''}

            if typ == "Szuflady": det['ilosc'] = st.number_input(f"Ilość #{i+1}", 1, 5, 2, key=f"ile_{i}")

            elif typ == "Półka":

                c_a, c_b = st.columns([1, 2])

                det['ilosc'] = c_a.number_input(f"Ile?", 1, 10, 1, key=f"ile_p_{i}")

                det['custom_str'] = c_b.text_input("Custom", key=f"cust_{i}")

            konfiguracja.append(det)

    st.header("3. Detale")

    sys_k = st.selectbox("System", list(BAZA_SYSTEMOW.keys()), key='sys_szuflad')

    params = BAZA_SYSTEMOW[sys_k]

    typ_boku_key = st.selectbox("Bok", list(params["wysokosci_tylu"].keys()), index=2, key='typ_boku')

    axis_fuga = st.number_input("Fuga", key='fuga')

    axis_nl = st.selectbox("NL", [300,350,400,450,500,550], index=4, key='nl')

    typ_plecow = st.selectbox("Plecy", ["Nakładane", "Wpuszczane", "Brak"], key='typ_plecow')

    st.header("4. Rozkrój")

    ARKUSZ_W, ARKUSZ_H = st.number_input("Ark.W", key='arkusz_w'), st.number_input("Ark.H", key='arkusz_h')

    RZAZ = st.number_input("Rzaz", key='rzaz')

# ==========================================

# 4. LOGIKA GŁÓWNA

# ==========================================

szer_wew_total = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)

szer_jednej_wneki = szer_wew_total / ilosc_sekcji

wys_wewnetrzna = H_MEBLA - (2 * GR_PLYTY)

lista_elementow = []

def dodaj_element(nazwa, szer, wys, gr, material, uwagi="", wiercenia=[], orientacja="L", strony_do_druku=None):

    kategoria_mat = "18mm KORPUS" if nazwa in ["Bok Lewy", "Bok Prawy", "Wieniec Górny", "Wieniec Dolny", "Przegroda", "Półka"] else "INNE"

    if nazwa == "Front Szuflady": kategoria_mat = "18mm FRONT"

    elif nazwa in ["Dno Szuflady", "Tył Szuflady"]: kategoria_mat = "16mm WNĘTRZE"

    elif nazwa == "Plecy HDF": kategoria_mat = "3mm HDF"

    count = sum(1 for x in lista_elementow if x['typ'] == nazwa) + 1

    skroty = {"Bok Lewy": "BOK-L", "Bok Prawy": "BOK-P", "Przegroda": "PRZEG", "Front Szuflady": "FR", "Półka": "POLKA"}

    ident = f"{KOD_PROJEKTU}-{skroty.get(nazwa, 'EL')}-{count}"

    lista_elementow.append({"ID": ident, "Nazwa": nazwa, "typ": nazwa, "Szerokość [mm]": round(szer, 1), "Wysokość [mm]": round(wys, 1), "Grubość [mm]": gr, "Materiał": kategoria_mat, "Uwagi": uwagi, "wiercenia": wiercenia, "orientacja": orientacja, "strony_do_druku": strony_do_druku})

def daj_otwory_dla_sekcji(typ_sekcji, ilosc, strona_plyty, custom_str=""):

    otwory = []

    off_x = 37.0 if strona_plyty == 'L' else (D_MEBLA - 37.0)

    off_x2 = 261.0 if strona_plyty == 'L' else (D_MEBLA - 261.0)

    if typ_sekcji == "Szuflady":

        h_f = (wys_wewnetrzna - ((ilosc + 1) * axis_fuga)) / ilosc

        for i in range(ilosc):

            y = i*(h_f + axis_fuga) + axis_fuga + params["offset_prowadnica"]

            otwory.extend([(off_x, y, 'red'), (off_x2, y, 'red')])

    elif typ_sekcji == "Półka":

        y_h = []

        if custom_str:

            try: y_h = [float(x.strip()) - 2.0 for x in custom_str.split(',') if x.strip()]

            except: st.error("Błąd Custom!")

        elif ilosc > 0:

            gap = (wys_wewnetrzna - ilosc*GR_PLYTY) / (ilosc + 1)

            y_h = [(k+1)*gap + k*GR_PLYTY - 2.0 for k in range(ilosc)]

        for y in y_h: otwory.extend([(off_x, y, 'green'), ((D_MEBLA-37.0 if strona_plyty=='L' else 37.0), y, 'green')])

    return otwory

# --- BUDOWA ---

otw_L = daj_otwory_dla_sekcji(konfiguracja[0]['typ'], konfiguracja[0]['ilosc'], 'P', konfiguracja[0]['custom_str'])

dodaj_element("Bok Lewy", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "", "", otw_L, "P")

otw_P = daj_otwory_dla_sekcji(konfiguracja[-1]['typ'], konfiguracja[-1]['ilosc'], 'L', konfiguracja[-1]['custom_str'])

dodaj_element("Bok Prawy", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "", "", otw_P, "L")

for i in range(ilosc_przegrod):

    oL, oP = daj_otwory_dla_sekcji(konfiguracja[i]['typ'], konfiguracja[i]['ilosc'], 'L', konfiguracja[i]['custom_str']), daj_otwory_dla_sekcji(konfiguracja[i+1]['typ'], konfiguracja[i+1]['ilosc'], 'L', konfiguracja[i+1]['custom_str'])

    strony = [{'tytul': f"Strona L (S{i+1})", 'otwory': oL}, {'tytul': f"Strona P (S{i+2})", 'otwory': oP}]

    dodaj_element("Przegroda", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "", f"S{i+1}|S{i+2}", oL+oP, "L", strony)

dodaj_element("Wieniec Górny", W_MEBLA, D_MEBLA, GR_PLYTY, "", "")

dodaj_element("Wieniec Dolny", W_MEBLA, D_MEBLA, GR_PLYTY, "", "")

for idx, k in enumerate(konfiguracja):

    if k['typ'] == "Szuflady":

        h_f = (wys_wewnetrzna - ((k['ilosc'] + 1) * axis_fuga)) / k['ilosc']

        w_f = szer_jednej_wneki - (2 * axis_fuga)

        for _ in range(k['ilosc']):

            dodaj_element("Front Szuflady", w_f, h_f, 18, "", f"S{idx+1}", [(15, 47, 'red'), (15, 79, 'red')])

    elif k['typ'] == "Półka":

        for _ in range(k['ilosc']): dodaj_element("Półka", szer_jednej_wneki-2, D_MEBLA-20, 18, "", f"S{idx+1}")

# --- TABS ---

df = pd.DataFrame(lista_elementow)

tabs = st.tabs(["📋 LISTA", "📐 RYSUNKI", "🗺️ ROZKRÓJ", "👁️ WIZUALIZACJA 2D"])

with tabs[0]: st.dataframe(df.drop(columns=['wiercenia','orientacja','strony_do_druku']), use_container_width=True)

with tabs[1]:

    sel = st.selectbox("Element:", [e['ID'] for e in lista_elementow if e['wiercenia'] or e['Nazwa']=='Front Szuflady'])

    it = next(x for x in lista_elementow if x['ID'] == sel)

    if it.get('strony_do_druku'):

        s = st.radio("Strona:", ["Lewa", "Prawa"], horizontal=True)

        idx = 0 if s=="Lewa" else 1

        st.pyplot(rysuj_element(it['Szerokość [mm]'], it['Wysokość [mm]'], it['ID'], it['Nazwa'], it['strony_do_druku'][idx]['otwory'], podtytul=it['strony_do_druku'][idx]['tytul']))

    else: st.pyplot(rysuj_element(it['Szerokość [mm]'], it['Wysokość [mm]'], it['ID'], it['Nazwa'], it['wiercenia']))

with tabs[3]:

    st.subheader("Podgląd frontowy szafki")

    st.pyplot(rysuj_podglad_mebla(W_MEBLA, H_MEBLA, GR_PLYTY, ilosc_przegrod, konfiguracja, szer_jednej_wneki))

```
