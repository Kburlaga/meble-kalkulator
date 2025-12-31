import streamlit as st

import pandas as pd

import io

# Konfiguracja strony

st.set_page_config(page_title="STOLARZPRO - V19.5", page_icon="🪚", layout="wide")

# Próba importu grafiki (bezpieczna)

try:

    import matplotlib

    matplotlib.use('Agg')

    import matplotlib.pyplot as plt

    import matplotlib.patches as patches

    from matplotlib.backends.backend_pdf import PdfPages

    GRAFIKA_DOSTEPNA = True

except:

    GRAFIKA_DOSTEPNA = False

# ==========================================

# 0. RESETOWANIE

# ==========================================

def resetuj_projekt():

    defaults = {

        'kod_pro': "RTV-PRO", 'h_mebla': 600, 'w_mebla': 1800, 'd_mebla': 600, 'gr_plyty': 18,

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

    if not GRAFIKA_DOSTEPNA: return None

    plt.close('all')

    fig, ax = plt.subplots(figsize=(10, 6))

    

    # Rysuj Formatkę

    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla)

    ax.add_patch(rect)

    

    # Rysuj Otwory

    if otwory:

        for otw in otwory:

            # Domyślny kolor 'red' jeśli brak w krotce

            x, y = otw[0], otw[1]

            kolor = otw[2] if len(otw) > 2 else 'red'

            style = 'circle'

            

            # Różne style dla różnych typów

            if kolor == 'blue': # Konstrukcyjne

                ax.add_patch(patches.Circle((x, y), radius=6, edgecolor='blue', facecolor='none', linewidth=1.5, linestyle='--'))

                ax.add_patch(patches.Circle((x, y), radius=1, color='blue'))

            else: # Prowadnice / Półki

                ax.add_patch(patches.Circle((x, y), radius=4, edgecolor=kolor, facecolor='white', linewidth=1.5))

            

            if len(otwory) < 60:

                ax.text(x + 8, y + 2, f"({x:.0f},{y:.0f})", fontsize=7, color='black', alpha=0.7)

    # Oznaczenie Frontu (okleina czerwona)

    if orientacja_frontu == 'L':

        ax.add_patch(patches.Rectangle((-3, 0), 3, wys, color='#d62828'))

        ax.text(5, wys/2, "FRONT", rotation=90, color='#d62828', fontsize=9, weight='bold')

    elif orientacja_frontu == 'P':

        ax.add_patch(patches.Rectangle((szer, 0), 3, wys, color='#d62828'))

        ax.text(szer-15, wys/2, "FRONT", rotation=90, color='#d62828', fontsize=9, weight='bold')

    else: # Front na dole (np. dla szuflad)

        ax.add_patch(patches.Rectangle((0, -3), szer, 3, color='#d62828'))

    # Wymiary

    ax.text(szer/2, -15, f"{szer} mm", ha='center', weight='bold')

    ax.text(-15, wys/2, f"{wys} mm", va='center', rotation=90, weight='bold')

    ax.set_aspect('equal')

    ax.set_title(f"{id_elementu} | {nazwa}\n{podtytul}", fontsize=12, weight='bold')

    ax.set_xlim(-50, szer+50)

    ax.set_ylim(-50, wys+50)

    ax.axis('off')

    return fig

def rysuj_podglad_mebla(w, h, gr, n_przeg, konfig, szer_wneki):

    if not GRAFIKA_DOSTEPNA: return None

    plt.close('all')

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

                ax.text(curr_x + szer_wneki/2, yf + h_f/2, "SZUFLADA", ha='center', va='center', fontsize=8, color='#669bbc')

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

    # Prosty algorytm półkowy (Shelf Algorithm)

    formatki_sorted = sorted(formatki, key=lambda x: x['Szerokość [mm]'] * x['Wysokość [mm]'], reverse=True)

    arkusze = []

    aktualny_arkusz = {'elementy': [], 'zuzycie_m2': 0, 'odpad': 0}

    

    cur_x, cur_y = 0, 0

    max_h_row = 0

    

    for f in formatki_sorted:

        w, h = f['Szerokość [mm]'], f['Wysokość [mm]']

        

        # Sprawdź czy element w ogóle wejdzie na pusty arkusz

        if w > arkusz_w or h > arkusz_h: 

            # Spróbuj obrócić

            if h <= arkusz_w and w <= arkusz_h:

                w, h = h, w # Obrót

            else:

                continue # Element za duży

        

        # Jeśli nie mieści się w poziomie

        if cur_x + w + rzaz > arkusz_w:

            cur_x = 0

            cur_y += max_h_row + rzaz

            max_h_row = 0

            

        # Jeśli nie mieści się w pionie (nowy arkusz)

        if cur_y + h + rzaz > arkusz_h:

            arkusze.append(aktualny_arkusz)

            aktualny_arkusz = {'elementy': [], 'zuzycie_m2': 0, 'odpad': 0}

            cur_x, cur_y, max_h_row = 0, 0, 0

            

        aktualny_arkusz['elementy'].append({'x': cur_x, 'y': cur_y, 'w': w, 'h': h, 'id': f['ID']})

        aktualny_arkusz['zuzycie_m2'] += (w * h) / 1000000

        

        cur_x += w + rzaz

        if h > max_h_row: max_h_row = h

        

    if aktualny_arkusz['elementy']: arkusze.append(aktualny_arkusz)

    return arkusze

# ==========================================

# 3. INTERFEJS

# ==========================================

BAZA_SYSTEMOW = {

    "GTV Axis Pro": {"offset_prowadnica": 37.5, "offset_front_y": 47.5, "offset_front_x": 15.5},

    "Blum Antaro": {"offset_prowadnica": 37.0, "offset_front_y": 45.5, "offset_front_x": 15.5}

}

with st.sidebar:

    st.title("🪚 STOLARZPRO V19.5")

    if st.button("🗑️ RESET", type="primary"): resetuj_projekt(); st.rerun()

    st.markdown("---")

    KOD_PROJEKTU = st.text_input("Nazwa", key='kod_pro').upper()

    c1, c2 = st.columns(2)

    H_MEBLA, W_MEBLA = c1.number_input("Wys.", key='h_mebla'), c2.number_input("Szer.", key='w_mebla')

    D_MEBLA, GR_PLYTY = c1.number_input("Głęb.", key='d_mebla'), c2.number_input("Grubość", key='gr_plyty')

    

    st.markdown("---")

    ilosc_przegrod = st.number_input("Przegrody", min_value=0, key='il_przegrod')

    ilosc_sekcji = ilosc_przegrod + 1

    konfiguracja = []

    

    for i in range(ilosc_sekcji):

        with st.expander(f"Sekcja {i+1}", expanded=True):

            typ = st.selectbox(f"Typ", ["Szuflady", "Półka", "Pusta"], key=f"typ_{i}", label_visibility="collapsed")

            det = {'typ': typ, 'ilosc': 0, 'custom_str': ''}

            if typ == "Szuflady": det['ilosc'] = st.number_input(f"Ilość", 1, 5, 2, key=f"ile_{i}")

            elif typ == "Półka":

                c_a, c_b = st.columns([1, 2])

                det['ilosc'] = c_a.number_input(f"Ile?", 1, 10, 1, key=f"ile_p_{i}")

                det['custom_str'] = c_b.text_input("Odstępy", key=f"cust_{i}")

            konfiguracja.append(det)

            

    st.markdown("---")

    sys_k = st.selectbox("System", list(BAZA_SYSTEMOW.keys()), key='sys_szuflad')

    params = BAZA_SYSTEMOW[sys_k]

# ==========================================

# 4. LOGIKA GŁÓWNA

# ==========================================

szer_wew_total = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)

szer_jednej_wneki = szer_wew_total / ilosc_sekcji if ilosc_sekcji > 0 else 0

wys_wewnetrzna = H_MEBLA - (2 * GR_PLYTY)

lista_elementow = []

def dodaj_element(nazwa, szer, wys, gr, material="18mm KORPUS", uwagi="", wiercenia=[], orientacja="L"):

    count = sum(1 for x in lista_elementow if x['Nazwa'] == nazwa) + 1

    skrot = nazwa[:3].upper() + ("-L" if orientacja=='L' else "-P" if orientacja=='P' else "")

    ident = f"{KOD_PROJEKTU}-{skrot}-{count}"

    lista_elementow.append({

        "ID": ident, "Nazwa": nazwa, 

        "Szerokość [mm]": round(szer, 1), "Wysokość [mm]": round(wys, 1), 

        "Grubość [mm]": gr, "Materiał": material, 

        "Uwagi": uwagi, "wiercenia": wiercenia, "orientacja": orientacja

    })

# --- OBLICZANIE OTWORÓW ---

def otwory_boczne(sekcja, mirror=False):

    otwory = []

    x_pos = D_MEBLA - 37.0 if mirror else 37.0 # Prowadnice/Podpórki są 37mm od frontu

    if sekcja['typ'] == "Szuflady" and sekcja['ilosc'] > 0:

        h_f = (wys_wewnetrzna - ((sekcja['ilosc'] + 1) * 3)) / sekcja['ilosc']

        for i in range(sekcja['ilosc']):

            y = i*(h_f + 3) + 3 + params["offset_prowadnica"]

            otwory.append((x_pos, y, 'red'))

    elif sekcja['typ'] == "Półka":

        cnt = sekcja['ilosc']

        if sekcja['custom_str']:

             try: cnt = len([x for x in sekcja['custom_str'].split(',') if x.strip()])

             except: pass

        if cnt > 0:

            gap = (wys_wewnetrzna - cnt*18) / (cnt + 1)

            for k in range(cnt):

                y = (k+1)*gap + k*18 - 2

                otwory.append((x_pos, y, 'green')) # Przód

                otwory.append((D_MEBLA - x_pos, y, 'green')) # Tył (symetrycznie)

    return otwory

def otwory_montazowe_poziome(szer, gl, typ="wieniec"):

    # Generuje otwory montażowe na krawędziach elementu (np. wieńca lub półki)

    otw = []

    # Standard: 37mm od krawędzi przedniej i tylnej, 9mm od boku (połowa płyty 18mm)

    y_front = 37

    y_back = gl - 37

    # Lewa krawędź

    otw.append((9, y_front, 'blue'))

    otw.append((9, y_back, 'blue'))

    # Prawa krawędź

    otw.append((szer-9, y_front, 'blue'))

    otw.append((szer-9, y_back, 'blue'))

    return otw

# --- KONSTRUKCJA ---

# 1. KORPUS

otw_L = otwory_boczne(konfiguracja[0], mirror=False)

dodaj_element("Bok Lewy", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "18mm KORPUS", "", otw_L, "L")

otw_P = otwory_boczne(konfiguracja[-1], mirror=True)

dodaj_element("Bok Prawy", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "18mm KORPUS", "", otw_P, "P")

for i in range(ilosc_przegrod):

    o1 = otwory_boczne(konfiguracja[i], mirror=False) # Lewa strona przegrody

    o2 = otwory_boczne(konfiguracja[i+1], mirror=False) # Prawa strona

    dodaj_element("Przegroda", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "18mm KORPUS", f"Sekcje {i+1}/{i+2}", o1+o2, "L")

# Wieńce (z otworami montażowymi do boków)

otw_W = otwory_montazowe_poziome(W_MEBLA, D_MEBLA)

dodaj_element("Wieniec Górny", W_MEBLA, D_MEBLA, GR_PLYTY, "18mm KORPUS", "", otw_W, "L")

dodaj_element("Wieniec Dolny", W_MEBLA, D_MEBLA, GR_PLYTY, "18mm KORPUS", "", otw_W, "L")

# 2. WNĘTRZE

for idx, k in enumerate(konfiguracja):

    if k['typ'] == "Szuflady" and k['ilosc'] > 0:

        h_f = (wys_wewnetrzna - ((k['ilosc'] + 1) * 3)) / k['ilosc']

        for _ in range(k['ilosc']):

            dodaj_element("Front Szuflady", szer_jednej_wneki-4, h_f, 18, "18mm FRONT", f"S{idx+1}", [], "D")

            # Elementy 16mm

            dodaj_element("Dno Szuflady", szer_jednej_wneki-75, 476, 16, "16mm DNO", "", [], "D")

            dodaj_element("Tył Szuflady", szer_jednej_wneki-87, 167, 16, "16mm TYŁ", "", [], "D")

            

    elif k['typ'] == "Półka":

        cnt = k['ilosc']

        if k['custom_str']:

             try: cnt = len([x for x in k['custom_str'].split(',') if x.strip()])

             except: pass

        # Półki mają otwory na krawędziach (do bolców/mimośrodów)

        otw_polka = otwory_montazowe_poziome(szer_jednej_wneki-2, D_MEBLA-20)

        for _ in range(cnt):

            dodaj_element("Półka", szer_jednej_wneki-2, D_MEBLA-20, 18, "18mm KORPUS", f"S{idx+1}", otw_polka, "L")

# --- TABS ---

df = pd.DataFrame(lista_elementow)

tabs = st.tabs(["📋 LISTA", "📐 RYSUNKI / PDF", "🗺️ ROZKRÓJ", "👁️ WIZUALIZACJA 2D"])

with tabs[0]:

    st.dataframe(df.drop(columns=['wiercenia', 'orientacja']), use_container_width=False)

with tabs[1]:

    if not GRAFIKA_DOSTEPNA:

        st.error("Błąd grafiki.")

    else:

        c1, c2 = st.columns([1,3])

        with c1:

            if st.button("📄 Generuj PDF"):

                pdf_buffer = io.BytesIO()

                with PdfPages(pdf_buffer) as pdf:

                    for el in lista_elementow:

                        fig = rysuj_element(el['Szerokość [mm]'], el['Wysokość [mm]'], el['ID'], el['Nazwa'], el['wiercenia'], el.get('orientacja', 'L'))

                        if fig: pdf.savefig(fig); plt.close(fig)

                st.session_state['pdf_ready'] = pdf_buffer

            

            if st.session_state.get('pdf_ready'):

                st.download_button("💾 Pobierz PDF", st.session_state['pdf_ready'].getvalue(), "projekt.pdf", "application/pdf")

        

        sel = st.selectbox("Wybierz element:", [e['ID'] for e in lista_elementow])

        it = next(x for x in lista_elementow if x['ID'] == sel)

        st.pyplot(rysuj_element(it['Szerokość [mm]'], it['Wysokość [mm]'], it['ID'], it['Nazwa'], it['wiercenia'], it.get('orientacja', 'L')))

with tabs[2]:

    if not GRAFIKA_DOSTEPNA: st.error("Błąd grafiki.")

    else:

        st.header("Optymalizacja Rozkroju")

        

        # 1. PŁYTA 18mm

        p18 = [x for x in lista_elementow if "18mm" in x['Materiał']]

        st.subheader(f"🟦 Płyta 18mm (Elementów: {len(p18)})")

        if st.button("Oblicz 18mm"):

            wyniki = optymalizuj_rozkroj(p18, 2800, 2070)

            st.success(f"Potrzebne arkusze: {len(wyniki)}")

            for i, ark in enumerate(wyniki):

                st.markdown(f"**Arkusz {i+1}** (Zużycie: {ark['zuzycie_m2']:.2f} m2)")

                fig, ax = plt.subplots(figsize=(8, 5))

                ax.add_patch(patches.Rectangle((0,0), 2800, 2070, facecolor='#eee', edgecolor='black'))

                for el in ark['elementy']:

                    ax.add_patch(patches.Rectangle((el['x'], el['y']), el['w'], el['h'], facecolor='#bc6c25', edgecolor='white'))

                    if el['w'] > 150: ax.text(el['x']+el['w']/2, el['y']+el['h']/2, el['id'], ha='center', fontsize=6, color='white')

                ax.set_xlim(-50, 2850); ax.set_ylim(-50, 2150); ax.set_aspect('equal'); ax.axis('off')

                st.pyplot(fig)

        # 2. PŁYTA 16mm

        p16 = [x for x in lista_elementow if "16mm" in x['Materiał']]

        if p16:

            st.markdown("---")

            st.subheader(f"🟩 Płyta 16mm (Elementów: {len(p16)})")

            if st.button("Oblicz 16mm"):

                wyniki16 = optymalizuj_rozkroj(p16, 2800, 2070)

                st.success(f"Potrzebne arkusze: {len(wyniki16)}")

                for i, ark in enumerate(wyniki16):

                    fig, ax = plt.subplots(figsize=(8, 5))

                    ax.add_patch(patches.Rectangle((0,0), 2800, 2070, facecolor='#eee', edgecolor='black'))

                    for el in ark['elementy']:

                        ax.add_patch(patches.Rectangle((el['x'], el['y']), el['w'], el['h'], facecolor='#606c38', edgecolor='white'))

                        if el['w'] > 150: ax.text(el['x']+el['w']/2, el['y']+el['h']/2, el['id'], ha='center', fontsize=6, color='white')

                    ax.set_xlim(-50, 2850); ax.set_ylim(-50, 2150); ax.set_aspect('equal'); ax.axis('off')

                    st.pyplot(fig)

with tabs[3]:

    if GRAFIKA_DOSTEPNA:

        st.subheader("Podgląd frontowy")

        st.pyplot(rysuj_podglad_mebla(W_MEBLA, H_MEBLA, GR_PLYTY, ilosc_przegrod, konfiguracja, szer_jednej_wneki))
