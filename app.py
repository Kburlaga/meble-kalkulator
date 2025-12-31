import streamlit as st

import matplotlib.pyplot as plt

import matplotlib.patches as patches

from matplotlib.backends.backend_pdf import PdfPages

import pandas as pd

import io

st.set_page_config(page_title="STOLARZPRO - V19.1", page_icon="🪚", layout="wide")

# ==========================================

# 0. RESETOWANIE

# ==========================================

def resetuj_projekt():

    defaults = {

        'kod_pro': "RTV-MIRROR", 'h_mebla': 600, 'w_mebla': 1800, 'd_mebla': 600, 'gr_plyty': 18,

        'il_przegrod': 2, 'typ_plecow': "Nakładane", 'sys_szuflad': "GTV Axis Pro", 'typ_boku': "C",

        'fuga': 3.0, 'nl': 500, 'arkusz_w': 2800, 'arkusz_h': 2070, 'rzaz': 4

    }

    for k, v in defaults.items(): st.session_state[k] = v

    st.session_state['pdf_ready'] = None

if 'kod_pro' not in st.session_state: resetuj_projekt()

# ==========================================

# 1. FUNKCJE RYSUNKOWE I LOGICZNE

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

    

    # Oznaczenie Frontu

    if orientacja_frontu == 'L': # Front z lewej (x=0)

        ax.add_patch(patches.Rectangle((-5, 0), 5, wys, color='red', alpha=0.5))

        ax.text(5, wys/2, "FRONT", rotation=90, color='red', fontsize=8)

    else: # Front z prawej (x=MAX)

        ax.add_patch(patches.Rectangle((szer, 0), 5, wys, color='red', alpha=0.5))

        ax.text(szer-15, wys/2, "FRONT", rotation=90, color='red', fontsize=8)

    ax.set_aspect('equal')

    ax.set_title(f"{id_elementu} | {nazwa}\n{podtytul}", fontsize=12, weight='bold')

    return fig

def rysuj_podglad_mebla(w, h, gr, n_przeg, konfig, szer_wneki):

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.add_patch(patches.Rectangle((0, 0), w, h, linewidth=3, edgecolor='black', facecolor='none'))

    ax.add_patch(patches.Rectangle((0, 0), w, gr, facecolor='#d7ba9d', edgecolor='black'))

    ax.add_patch(patches.Rectangle((0, h-gr), w, gr, facecolor='#d7ba9d', edgecolor='black'))

    ax.add_patch(patches.Rectangle((0, gr), gr, h-2*gr, facecolor='#d7ba9d', edgecolor='black'))

    ax.add_patch(patches.Rectangle((w-gr, gr), gr, h-2*gr, facecolor='#d7ba9d', edgecolor='black'))

    

    curr_x = gr

    h_wew = h - 2*gr

    

    for idx, sekcja in enumerate(konfig):

        if idx < len(konfig) - 1:

            ax.add_patch(patches.Rectangle((curr_x + szer_wneki, gr), gr, h_wew, facecolor='gray', alpha=0.3))

        

        if sekcja['typ'] == "Szuflady" and sekcja['ilosc'] > 0:

            n = sekcja['ilosc']

            h_f = (h_wew - ((n + 1) * 3)) / n 

            for i in range(n):

                yf = gr + 3 + i*(h_f + 3)

                ax.add_patch(patches.Rectangle((curr_x+2, yf), szer_wneki-4, h_f, facecolor='#fdf0d5', edgecolor='#669bbc', linewidth=1))

                ax.add_patch(patches.Circle((curr_x + szer_wneki/2, yf + h_f*0.8), radius=5, color='black'))

        elif sekcja['typ'] == "Półka":

             cnt = sekcja['ilosc']

             if sekcja['custom_str']:

                 try: cnt = len([x for x in sekcja['custom_str'].split(',') if x.strip()])

                 except: pass

             if cnt > 0:

                 gap = (h_wew - cnt*gr) / (cnt + 1)

                 for k in range(cnt):

                     yp = gr + (k+1)*gap + k*gr

                     ax.add_patch(patches.Rectangle((curr_x, yp), szer_wneki, 5, color='#bc6c25'))

        curr_x += szer_wneki + gr

    ax.set_xlim(-100, w + 100); ax.set_ylim(-100, h + 100)

    ax.set_aspect('equal')

    ax.axis('off')

    return fig

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

# 3. INTERFEJS (SIDEBAR)

# ==========================================

BAZA_SYSTEMOW = {

    "GTV Axis Pro": {"offset_prowadnica": 37.5, "offset_front_y": 47.5, "offset_front_x": 15.5},

    "Blum Antaro": {"offset_prowadnica": 37.0, "offset_front_y": 45.5, "offset_front_x": 15.5}

}

with st.sidebar:

    st.title("🪚 STOLARZPRO V19.1")

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

            if typ == "Szuflady": det['ilosc'] = st.number_input(f"Ilość #{i+1}", 1, 5, 2, key=f"ile_{i}")

            elif typ == "Półka":

                c_a, c_b = st.columns([1, 2])

                det['ilosc'] = c_a.number_input(f"Ile?", 1, 10, 1, key=f"ile_p_{i}")

                det['custom_str'] = c_b.text_input("Odstępy (opcja)", key=f"cust_{i}")

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

def dodaj_element(nazwa, szer, wys, gr, material="18mm KORPUS", uwagi="", wiercenia=[], orientacja="L"):

    count = sum(1 for x in lista_elementow if x['Nazwa'] == nazwa) + 1

    ident = f"{KOD_PROJEKTU}-{nazwa[:3].upper()}-{count}"

    lista_elementow.append({"ID": ident, "Nazwa": nazwa, "Szerokość [mm]": round(szer, 1), "Wysokość [mm]": round(wys, 1), "Grubość [mm]": gr, "Materiał": material, "Uwagi": uwagi, "wiercenia": wiercenia, "orientacja": orientacja})

def oblicz_otwory(sekcja, mirror=False):

    otwory = []

    # Standard: 37mm od Frontu. Mirror: D_MEBLA - 37mm

    x_pos = D_MEBLA - 37.0 if mirror else 37.0

    x_pos_2 = D_MEBLA - 261.0 if mirror else 261.0

    

    if sekcja['typ'] == "Szuflady" and sekcja['ilosc'] > 0:

        h_f = (wys_wewnetrzna - ((sekcja['ilosc'] + 1) * 3)) / sekcja['ilosc']

        for i in range(sekcja['ilosc']):

            y = i*(h_f + 3) + 3 + params["offset_prowadnica"]

            otwory.append((x_pos, y, 'red')) # Prowadnica

            # Druga dziura prowadnicy (opcjonalnie)

            # otwory.append((x_pos_2, y, 'red')) 

            

    elif sekcja['typ'] == "Półka":

        cnt = sekcja['ilosc']

        if sekcja['custom_str']:

             try: cnt = len([x for x in sekcja['custom_str'].split(',') if x.strip()])

             except: pass

        if cnt > 0:

            gap = (wys_wewnetrzna - cnt*18) / (cnt + 1)

            for k in range(cnt):

                y = (k+1)*gap + k*18 - 2 # 2mm pod półką

                otwory.append((x_pos, y, 'green')) # Podpórka

                otwory.append((x_pos_2, y, 'green')) # Podpórka tył

    return otwory

# BUDOWA MEBLA Z WIERCEŃIAMI

# 1. BOK LEWY (Obsługuje Sekcję 1). Front = x=0. Wiercenia 37mm.

otw_L = oblicz_otwory(konfiguracja[0], mirror=False)

dodaj_element("Bok Lewy", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "18mm KORPUS", "", otw_L, "L")

# 2. BOK PRAWY (Obsługuje Ostatnią Sekcję). Front = x=MAX. Wiercenia D-37mm (Lustro).

otw_P = oblicz_otwory(konfiguracja[-1], mirror=True)

dodaj_element("Bok Prawy", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "18mm KORPUS", "", otw_P, "P")

# 3. PRZEGRODY (Obsługują L i P).

for i in range(ilosc_przegrod):

    # Przegroda obsługuje sekcję z lewej (i) oraz z prawej (i+1)

    # Dla maszyny CNC traktujemy to jako nałożone otwory

    # Lewa strona przegrody = Standard 37mm

    # Prawa strona przegrody = Też 37mm (bo formatka jest obracana)

    # Ale dla wizualizacji "przeźroczystej" nałożymy oba schematy

    o1 = oblicz_otwory(konfiguracja[i], mirror=False)

    o2 = oblicz_otwory(konfiguracja[i+1], mirror=False) 

    # Uwaga: Przegrody wew. zazwyczaj mają 37mm z obu stron.

    dodaj_element("Przegroda", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "18mm KORPUS", f"Sekcje {i+1}/{i+2}", o1+o2, "L")

dodaj_element("Wieniec Górny", W_MEBLA, D_MEBLA, GR_PLYTY)

dodaj_element("Wieniec Dolny", W_MEBLA, D_MEBLA, GR_PLYTY)

# ELEMENTY WEWNĘTRZNE

for idx, k in enumerate(konfiguracja):

    if k['typ'] == "Szuflady" and k['ilosc'] > 0:

        h_f = (wys_wewnetrzna - ((k['ilosc'] + 1) * 3)) / k['ilosc']

        for _ in range(k['ilosc']):

            dodaj_element("Front Szuflady", szer_jednej_wneki-4, h_f, 18, "18mm FRONT", f"Sekcja {idx+1}")

            dodaj_element("Dno Szuflady", szer_jednej_wneki-75, 476, 16, "16mm DNO")

            dodaj_element("Tył Szuflady", szer_jednej_wneki-87, 167, 16, "16mm TYŁ")

    elif k['typ'] == "Półka":

        cnt = k['ilosc']

        if k['custom_str']:

             try: cnt = len([x for x in k['custom_str'].split(',') if x.strip()])

             except: pass

        for _ in range(cnt):

            dodaj_element("Półka", szer_jednej_wneki-2, D_MEBLA-20, 18, "18mm KORPUS", f"Sekcja {idx+1}")

# --- TABS ---

df = pd.DataFrame(lista_elementow)

tabs = st.tabs(["📋 LISTA", "📐 RYSUNKI / PDF", "🗺️ ROZKRÓJ", "👁️ WIZUALIZACJA 2D"])

with tabs[0]:

    st.subheader("Lista elementów")

    st.dataframe(df.drop(columns=['wiercenia', 'orientacja']), use_container_width=True)

with tabs[1]:

    st.subheader("Dokumentacja")

    col1, col2 = st.columns([1,3])

    with col1:

        if st.button("Generuj PDF"):

            pdf_buffer = io.BytesIO()

            with PdfPages(pdf_buffer) as pdf:

                for el in lista_elementow:

                    fig = rysuj_element(el['Szerokość [mm]'], el['Wysokość [mm]'], el['ID'], el['Nazwa'], el['wiercenia'], orientacja_frontu=el.get('orientacja', 'L'))

                    pdf.savefig(fig); plt.close(fig)

            st.session_state['pdf_ready'] = pdf_buffer

            st.success("Gotowe!")

        if st.session_state.get('pdf_ready'):

            st.download_button("Pobierz PDF", st.session_state['pdf_ready'].getvalue(), "projekt.pdf", "application/pdf")

    

    sel = st.selectbox("Podgląd elementu:", [e['ID'] for e in lista_elementow])

    it = next(x for x in lista_elementow if x['ID'] == sel)

    st.pyplot(rysuj_element(it['Szerokość [mm]'], it['Wysokość [mm]'], it['ID'], it['Nazwa'], it['wiercenia'], orientacja_frontu=it.get('orientacja', 'L')))

with tabs[2]:

    st.subheader("Optymalizacja Rozkroju (Płyta 18mm)")

    if st.button("Oblicz Rozkrój"):

        p18 = [x for x in lista_elementow if "18mm" in x['Materiał']]

        wyniki = optymalizuj_rozkroj(p18, 2800, 2070)

        st.success(f"Potrzebne arkusze: {len(wyniki)}")

        for i, ark in enumerate(wyniki):

            fig, ax = plt.subplots(figsize=(10, 6))

            ax.add_patch(patches.Rectangle((0,0), 2800, 2070, facecolor='#f0f0f0', edgecolor='black'))

            for el in ark['elementy']:

                ax.add_patch(patches.Rectangle((el['x'], el['y']), el['w'], el['h'], facecolor='#e6ccb3', edgecolor='black'))

                if el['w'] > 200: ax.text(el['x']+el['w']/2, el['y']+el['h']/2, el['id'], ha='center', fontsize=6)

            ax.set_xlim(-100, 2900); ax.set_ylim(-100, 2200); ax.set_aspect('equal')

            st.pyplot(fig)

with tabs[3]:

    st.subheader("Podgląd frontowy szafki")

    st.pyplot(rysuj_podglad_mebla(W_MEBLA, H_MEBLA, GR_PLYTY, ilosc_przegrod, konfiguracja, szer_jednej_wneki))
