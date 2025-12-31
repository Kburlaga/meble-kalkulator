import streamlit as st

import matplotlib.pyplot as plt

import matplotlib.patches as patches

import pandas as pd

import io

st.set_page_config(page_title="STOLARZPRO - V18.4", page_icon="🪚", layout="wide")

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

# 1. FUNKCJE RYSUNKOWE

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

    ax.set_aspect('equal')

    ax.set_title(f"{id_elementu} | {nazwa}\n{podtytul}", fontsize=12, weight='bold')

    return fig

def rysuj_podglad_mebla(w, h, gr, n_przeg, konfig, szer_wneki):

    fig, ax = plt.subplots(figsize=(12, 6))

    # Obrys

    ax.add_patch(patches.Rectangle((0, 0), w, h, linewidth=3, edgecolor='black', facecolor='none'))

    # Wieńce i boki

    ax.add_patch(patches.Rectangle((0, 0), w, gr, facecolor='#d7ba9d', edgecolor='black'))

    ax.add_patch(patches.Rectangle((0, h-gr), w, gr, facecolor='#d7ba9d', edgecolor='black'))

    ax.add_patch(patches.Rectangle((0, gr), gr, h-2*gr, facecolor='#d7ba9d', edgecolor='black'))

    ax.add_patch(patches.Rectangle((w-gr, gr), gr, h-2*gr, facecolor='#d7ba9d', edgecolor='black'))

    

    curr_x = gr

    h_wew = h - 2*gr

    

    for idx, sekcja in enumerate(konfig):

        # Przegroda

        if idx < len(konfig) - 1:

            ax.add_patch(patches.Rectangle((curr_x + szer_wneki, gr), gr, h_wew, facecolor='gray', alpha=0.3))

        

        # Zawartość

        if sekcja['typ'] == "Szuflady":

            n = sekcja['ilosc']

            if n > 0:

                h_f = (h_wew - ((n + 1) * 3)) / n 

                for i in range(n):

                    yf = gr + 3 + i*(h_f + 3)

                    ax.add_patch(patches.Rectangle((curr_x+2, yf), szer_wneki-4, h_f, facecolor='#fdf0d5', edgecolor='#669bbc', linewidth=1))

                    ax.add_patch(patches.Circle((curr_x + szer_wneki/2, yf + h_f*0.8), radius=5, color='black'))

        

        elif sekcja['typ'] == "Półka":

            y_h = []

            custom_str = sekcja.get('custom_str', '')

            n_p = sekcja['ilosc']

            

            if custom_str and len(custom_str.strip()) > 0:

                try:

                    y_h = [float(x.strip()) for x in custom_str.split(',') if x.strip()]

                except: pass

            elif n_p > 0:

                gap = (h_wew - n_p*gr) / (n_p + 1)

                y_h = [(k+1)*gap + k*gr for k in range(n_p)]

            

            for y_pos in y_h:

                ax.add_patch(patches.Rectangle((curr_x, gr + y_pos), szer_wneki, 5, color='#bc6c25'))

        

        curr_x += szer_wneki + gr

    ax.set_xlim(-100, w + 100); ax.set_ylim(-100, h + 100)

    ax.set_aspect('equal')

    ax.axis('off')

    return fig

# ==========================================

# 3. INTERFEJS (SIDEBAR)

# ==========================================

BAZA_SYSTEMOW = {

    "GTV Axis Pro": {"offset_prowadnica": 37.5, "offset_front_y": 47.5, "offset_front_x": 15.5},

    "Blum Antaro": {"offset_prowadnica": 37.0, "offset_front_y": 45.5, "offset_front_x": 15.5}

}

with st.sidebar:

    st.title("🪚 STOLARZPRO V18.4")

    if st.button("🗑️ RESET", type="primary", use_container_width=True): resetuj_projekt(); st.rerun()

    

    st.header("1. Gabaryty")

    KOD_PROJEKTU = st.text_input("Nazwa", key='kod_pro').upper()

    H_MEBLA, W_MEBLA = st.number_input("Wys.", key='h_mebla'), st.number_input("Szer.", key='w_mebla')

    D_MEBLA, GR_PLYTY = st.number_input("Głęb.", key='d_mebla'), st.number_input("Grubość", key='gr_plyty')

    

    st.header("2. Wnętrze")

    ilosc_przegrod = st.number_input("Przegrody", min_value=0, key='il_przegrod')

    ilosc_sekcji = ilosc_przegrod + 1

    konfiguracja = []

    

    for i in range(ilosc_sekcji):

        with st.expander(f"Sekcja {i+1}", expanded=True):

            typ = st.selectbox(f"Typ #{i+1}", ["Szuflady", "Półka", "Pusta"], key=f"typ_{i}")

            det = {'typ': typ, 'ilosc': 0, 'custom_str': ''}

            

            if typ == "Szuflady":

                det['ilosc'] = st.number_input(f"Ilość #{i+1}", 1, 5, 2, key=f"ile_{i}")

            elif typ == "Półka":

                c_a, c_b = st.columns([1, 2])

                det['ilosc'] = c_a.number_input(f"Ile?", 1, 10, 1, key=f"ile_p_{i}")

                det['custom_str'] = c_b.text_input("Custom (mm)", placeholder="np. 200, 400", key=f"cust_{i}")

                

                if det['custom_str']:

                    st.caption("⚠️ Tryb 'Custom' nadpisuje licznik!")

            

            konfiguracja.append(det)

    st.header("3. Detale")

    sys_k = st.selectbox("System", list(BAZA_SYSTEMOW.keys()), key='sys_szuflad')

    params = BAZA_SYSTEMOW[sys_k]

    axis_fuga = st.number_input("Fuga", key='fuga')

# ==========================================

# 4. LOGIKA GŁÓWNA

# ==========================================

szer_wew_total = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)

szer_jednej_wneki = szer_wew_total / ilosc_sekcji if ilosc_sekcji > 0 else 0

wys_wewnetrzna = H_MEBLA - (2 * GR_PLYTY)

lista_elementow = []

def dodaj_element(nazwa, szer, wys, gr, uwagi="", wiercenia=[]):

    count = sum(1 for x in lista_elementow if x['Nazwa'] == nazwa) + 1

    ident = f"{KOD_PROJEKTU}-{nazwa[:3].upper()}-{count}"

    lista_elementow.append({"ID": ident, "Nazwa": nazwa, "Szerokość [mm]": round(szer, 1), "Wysokość [mm]": round(wys, 1), "Grubość [mm]": gr, "Uwagi": uwagi, "wiercenia": wiercenia})

# BUDOWA KORPUSU

dodaj_element("Bok Lewy", D_MEBLA, wys_wewnetrzna, GR_PLYTY)

dodaj_element("Bok Prawy", D_MEBLA, wys_wewnetrzna, GR_PLYTY)

for i in range(ilosc_przegrod): dodaj_element("Przegroda", D_MEBLA, wys_wewnetrzna, GR_PLYTY)

dodaj_element("Wieniec Górny", W_MEBLA, D_MEBLA, GR_PLYTY)

dodaj_element("Wieniec Dolny", W_MEBLA, D_MEBLA, GR_PLYTY)

# ZAWARTOŚĆ SEKCI

for idx, k in enumerate(konfiguracja):

    if k['typ'] == "Szuflady" and k['ilosc'] > 0:

        h_f = (wys_wewnetrzna - ((k['ilosc'] + 1) * 3)) / k['ilosc']

        for _ in range(k['ilosc']):

            dodaj_element("Front Szuflady", szer_jednej_wneki-4, h_f, 18, f"Sekcja {idx+1}")

    elif k['typ'] == "Półka":

        cnt = k['ilosc']

        if k['custom_str']:

             try: cnt = len([x for x in k['custom_str'].split(',') if x.strip()])

             except: pass

        for _ in range(cnt):

            dodaj_element("Półka", szer_jednej_wneki-2, D_MEBLA-20, 18, f"Sekcja {idx+1}")

# --- TABS ---

df = pd.DataFrame(lista_elementow)

tabs = st.tabs(["📋 LISTA", "📐 RYSUNKI", "🗺️ ROZKRÓJ", "👁️ WIZUALIZACJA 2D"])

with tabs[0]:

    st.subheader("Lista elementów")

    st.dataframe(df.drop(columns=['wiercenia']), use_container_width=True)

with tabs[1]:

    st.info("Wybierz element z listy, aby zobaczyć wiercenia.")

with tabs[2]:

    st.info("Moduł rozkroju w przygotowaniu.")

with tabs[3]:

    st.subheader("Podgląd frontowy szafki")

    st.pyplot(rysuj_podglad_mebla(W_MEBLA, H_MEBLA, GR_PLYTY, ilosc_przegrod, konfiguracja, szer_jednej_wneki))
