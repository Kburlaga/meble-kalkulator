import streamlit as st
import pandas as pd
import io

# Konfiguracja strony
st.set_page_config(page_title="STOLARZPRO - V20.3", page_icon="🪚", layout="wide")

# Próba importu grafiki
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.backends.backend_pdf import PdfPages
    GRAFIKA_DOSTEPNA = True
except ImportError:
    GRAFIKA_DOSTEPNA = False

# ==========================================
# 0. BAZY DANYCH I RESET
# ==========================================
BAZA_SYSTEMOW = {
    "GTV Axis Pro": {"offset_prowadnica": 37.5, "offset_front_y": 47.5},
    "Blum Antaro": {"offset_prowadnica": 37.0, "offset_front_y": 45.5}
}

BAZA_ZAWIASOW = {
    "Blum Clip Top": {"puszka_offset": 21.5}, 
    "GTV Prestige": {"puszka_offset": 22.0},
    "Hettich Sensys": {"puszka_offset": 22.5}
}

def resetuj_projekt():
    defaults = {
        'kod_pro': "PROJEKT-1", 'h_mebla': 2000, 'w_mebla': 1800, 'd_mebla': 600, 'gr_plyty': 18,
        'il_przegrod': 2, 'typ_plecow': "Nakładane", 'sys_szuflad': "GTV Axis Pro", 
        'sys_zawiasow': "Blum Clip Top", 'typ_boku': "C",
        'fuga': 3.0, 'arkusz_w': 2800, 'arkusz_h': 2070, 'rzaz': 4
    }
    for k, v in defaults.items(): st.session_state[k] = v
    
    st.session_state['moduly_sekcji'] = {} 
    st.session_state['pdf_ready'] = None
    st.session_state['szablon_ready'] = None

if 'kod_pro' not in st.session_state: resetuj_projekt()

# ==========================================
# 1. LOGIKA MODUŁÓW (CRUD)
# ==========================================
def dodaj_modul(nr_sekcji, typ, wysokosc_typ, wysokosc_mm, detale):
    if nr_sekcji not in st.session_state['moduly_sekcji']:
        st.session_state['moduly_sekcji'][nr_sekcji] = []
    
    nowy_modul = {
        'typ': typ,
        'wys_mode': wysokosc_typ,
        'wys_mm': wysokosc_mm if wysokosc_typ == 'fixed' else 0,
        'detale': detale 
    }
    st.session_state['moduly_sekcji'][nr_sekcji].append(nowy_modul)

def usun_modul(nr_sekcji, idx):
    if nr_sekcji in st.session_state['moduly_sekcji']:
        st.session_state['moduly_sekcji'][nr_sekcji].pop(idx)

# ==========================================
# 2. FUNKCJE RYSUNKOWE I SZABLONY
# ==========================================
def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], orientacja_frontu="L", kolor_tla='#e6ccb3'):
    if not GRAFIKA_DOSTEPNA: return None
    plt.close('all')
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Tło
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla)
    ax.add_patch(rect)
    
    # Otwory
    if otwory:
        for otw in otwory:
            x, y = otw[0], otw[1]
            kolor = otw[2] if len(otw) > 2 else 'red'
            
            if kolor == 'blue': 
                ax.add_patch(patches.Circle((x, y), radius=6, edgecolor='blue', facecolor='none', linestyle='--'))
                ax.add_patch(patches.Circle((x, y), radius=1, color='blue'))
            elif kolor == 'red': 
                ax.add_patch(patches.Circle((x, y), radius=3, color='red')) 
            elif kolor == 'green': 
                if "Front" in nazwa:
                    ax.add_patch(patches.Circle((x, y), radius=17.5, edgecolor='green', facecolor='#ccffcc', linewidth=1.5))
                else:
                    ax.add_patch(patches.Circle((x, y), radius=4, edgecolor='green', facecolor='white'))
            
            if len(otwory) < 60:
                ax.text(x+8, y+2, f"({x:.0f},{y:.0f})", fontsize=7, alpha=0.7)

    # Orientacja
    if orientacja_frontu == 'L':
        ax.add_patch(patches.Rectangle((-3, 0), 3, wys, color='#d62828'))
        ax.text(5, wys/2, "FRONT", rotation=90, color='#d62828', fontsize=9, weight='bold')
    elif orientacja_frontu == 'D': 
        ax.add_patch(patches.Rectangle((0, -3), szer, 3, color='#d62828'))
        ax.text(szer/2, 5, "FRONT", ha='center', color='#d62828', fontsize=9, weight='bold')
    elif orientacja_frontu == 'P':
        ax.add_patch(patches.Rectangle((szer, 0), 3, wys, color='#d62828'))
        ax.text(szer-15, wys/2, "FRONT", rotation=90, color='#d62828', fontsize=9, weight='bold')

    ax.text(szer/2, -15, f"{szer} mm", ha='center', weight='bold')
    ax.text(-15, wys/2, f"{wys} mm", va='center', rotation=90, weight='bold')
    ax.set_aspect('equal'); ax.axis('off')
    return fig

def generuj_szablon_a4(element, rog):
    if not GRAFIKA_DOSTEPNA: return None
    plt.close('all')
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    
    szer, wys = element['Szerokość [mm]'], element['Wysokość [mm]']
    otwory = element['wiercenia']
    
    ax.add_patch(patches.Rectangle((0, 0), szer, wys, linewidth=3, edgecolor='black', facecolor='#eee'))
    
    for otw in otwory:
        x, y = otw[0], otw[1]
        kolor = otw[2] if len(otw) > 2 else 'black'
        ax.plot([x-5, x+5], [y, y], color=kolor, linewidth=1)
        ax.plot([x, x], [y-5, y+5], color=kolor, linewidth=1)
        ax.text(x+2, y+2, f"({x:.1f}, {y:.1f})", fontsize=8, color=kolor)

    a4_w, a4_h, m = 210, 297, 10
    
    if "LD" in rog: ax.set_xlim(-m, a4_w-m); ax.set_ylim(-m, a4_h-m)
    elif "LG" in rog: ax.set_xlim(-m, a4_w-m); ax.set_ylim(wys-a4_h+m, wys+m)
    elif "PD" in rog: ax.set_xlim(szer-a4_w+m, szer+m); ax.set_ylim(-m, a4_h-m)
    elif "PG" in rog: ax.set_xlim(szer-a4_w+m, szer+m); ax.set_ylim(wys-a4_h+m, wys+m)

    ax.set_aspect('equal'); ax.grid(True, linestyle=':', alpha=0.5)
    return fig

def rysuj_podglad_mebla(w, h, gr, n_przeg, moduly_sekcji, szer_wneki):
    if not GRAFIKA_DOSTEPNA: return None
    plt.close('all')
    fig, ax = plt.subplots(figsize=(12, 8))

    ax.add_patch(patches.Rectangle((0, 0), w, h, linewidth=3, edgecolor='black', facecolor='none'))
    ax.add_patch(patches.Rectangle((0, 0), w, gr, facecolor='#d7ba9d', edgecolor='black'))
    ax.add_patch(patches.Rectangle((0, h-gr), w, gr, facecolor='#d7ba9d', edgecolor='black'))
    ax.add_patch(patches.Rectangle((0, gr), gr, h-2*gr, facecolor='#d7ba9d', edgecolor='black'))
    ax.add_patch(patches.Rectangle((w-gr, gr), gr, h-2*gr, facecolor='#d7ba9d', edgecolor='black'))
    
    curr_x = gr
    h_wew = h - 2*gr
    
    for i in range(n_przeg + 1):
        if i < n_przeg:
            ax.add_patch(patches.Rectangle((curr_x + szer_wneki, gr), gr, h_wew, facecolor='gray', alpha=0.3))
        
        moduly = moduly_sekcji.get(i, [])
        if moduly:
            fixed_h_sum = sum(m['wys_mm'] for m in moduly if m['wys_mode'] == 'fixed')
            auto_count = sum(1 for m in moduly if m['wys_mode'] == 'auto')
            auto_h = (h_wew - fixed_h_sum) / auto_count if auto_count > 0 else 0
            
            curr_y = gr 
            
            for mod in moduly:
                h_mod = mod['wys_mm'] if mod['wys_mode'] == 'fixed' else auto_h
                
                ax.add_patch(patches.Rectangle((curr_x, curr_y), szer_wneki, h_mod, facecolor='none', edgecolor='black', linestyle=':', alpha=0.5))
                
                det = mod['detale']
                if mod['typ'] == "Szuflady":
                    n = det.get('ilosc', 2)
                    if n > 0:
                        h_f = (h_mod - ((n-1)*3)) / n
                        for k in range(n):
                            yf = curr_y + k*(h_f+3)
                            ax.add_patch(patches.Rectangle((curr_x+2, yf), szer_wneki-4, h_f, facecolor='#fdf0d5', edgecolor='#669bbc'))
                            ax.text(curr_x + szer_wneki/2, yf + h_f/2, "SZUFLADA", ha='center', va='center', fontsize=7, color='#669bbc')

                elif mod['typ'] == "Półki":
                    n = det.get('ilosc', 1)
                    if n > 0:
                        gap = h_mod / (n + 1)
                        for k in range(n):
                            yp = curr_y + (k+1)*gap
                            ax.add_patch(patches.Rectangle((curr_x, yp), szer_wneki, 5, color='#bc6c25'))

                elif mod['typ'] == "Drążek":
                    ax.add_patch(patches.Rectangle((curr_x+5, curr_y + h_mod - 60), szer_wneki-10, 15, facecolor='silver', edgecolor='black'))
                    ax.text(curr_x + szer_wneki/2, curr_y + h_mod/2, "DRĄŻEK", ha='center', alpha=0.3, rotation=45)

                if det.get('drzwi'):
                     ax.add_patch(patches.Rectangle((curr_x+1, curr_y+1), szer_wneki-2, h_mod-2, 
                                                  facecolor='green', alpha=0.1, edgecolor='green', linestyle='--'))
                     ax.text(curr_x + szer_wneki/2, curr_y + h_mod/2, "DRZWI", ha='center', color='green', fontweight='bold', alpha=0.5)

                curr_y += h_mod

        curr_x += szer_wneki + gr

    ax.set_xlim(-100, w + 100); ax.set_ylim(-100, h + 100)
    ax.set_aspect('equal'); ax.axis('off')
    return fig

# ==========================================
# 3. INTERFEJS GŁÓWNY (SIDEBAR)
# ==========================================
with st.sidebar:
    st.title("🪚 STOLARZPRO V20.3")
    if st.button("🗑️ NOWY PROJEKT", type="primary"): resetuj_projekt(); st.rerun()
    
    st.markdown("### 1. Gabaryty")
    KOD_PROJEKTU = st.text_input("Nazwa", st.session_state['kod_pro']).upper()
    c1, c2 = st.columns(2)
    H_MEBLA, W_MEBLA = c1.number_input("Wysokość", value=st.session_state['h_mebla']), c2.number_input("Szerokość", value=st.session_state['w_mebla'])
    D_MEBLA, GR_PLYTY = c1.number_input("Głębokość", value=st.session_state['d_mebla']), c2.number_input("Grubość płyty", value=st.session_state['gr_plyty'])
    
    ilosc_przegrod = st.number_input("Ilość przegród pionowych", min_value=0, value=st.session_state['il_przegrod'])
    ilosc_sekcji = ilosc_przegrod + 1

    st.markdown("### 2. Konfigurator Modułowy")
    st.info("Buduj sekcje od dołu do góry. Użyj 'AUTO' żeby wypełnić resztę miejsca.")

    tabs_sekcji = st.tabs([f"Sekcja {i+1}" for i in range(ilosc_sekcji)])
    
    for i, tab in enumerate(tabs_sekcji):
        with tab:
            if i in st.session_state['moduly_sekcji'] and st.session_state['moduly_sekcji'][i]:
                st.write("🔽 Dół szafy")
                for idx, mod in enumerate(st.session_state['moduly_sekcji'][i]):
                    opis = f"**{idx+1}. {mod['typ']}**"
                    if mod['wys_mode'] == 'fixed': opis += f" ({mod['wys_mm']}mm)"
                    else: opis += " (AUTO)"
                    
                    c_del, c_info = st.columns([1, 4])
                    if c_del.button("❌", key=f"del_{i}_{idx}"):
                        usun_modul(i, idx); st.rerun()
                    c_info.markdown(opis)
                st.write("🔼 Góra szafy")
                st.markdown("---")
            
            c_typ, c_wys = st.columns([2, 1])
            new_typ = c_typ.selectbox("Typ", ["Półki", "Szuflady", "Drążek", "Pusta"], key=f"new_typ_{i}")
            wys_opt = c_wys.selectbox("Wysokość", ["Fixed (mm)", "AUTO (Reszta)"], key=f"wys_opt_{i}")
            
            new_wys_mm = 0
            if wys_opt == "Fixed (mm)":
                new_wys_mm = st.number_input("Ile mm?", 100, 2000, 600, key=f"h_mm_{i}")
            
            detale = {'ilosc': 0, 'drzwi': False}
            if new_typ == "Szuflady":
                detale['ilosc'] = st.number_input("Ile szuflad?", 1, 6, 2, key=f"det_sz_{i}")
            elif new_typ == "Półki":
                detale['ilosc'] = st.number_input("Ile półek?", 1, 10, 2, key=f"det_pl_{i}")
            
            if new_typ in ["Półki", "Drążek", "Pusta"]:
                detale['drzwi'] = st.checkbox("Zamknij drzwiami?", key=f"det_dr_{i}")

            if st.button("➕ Dodaj Moduł", key=f"add_{i}"):
                dodaj_modul(i, new_typ, 'auto' if "AUTO" in wys_opt else 'fixed', new_wys_mm, detale)
                st.rerun()

    st.markdown("---")
    st.markdown("### 3. Okucia")
    c_s1, c_s2 = st.columns(2)
    sys_k = c_s1.selectbox("Prowadnice", list(BAZA_SYSTEMOW.keys()))
    zaw_k = c_s2.selectbox("Zawiasy", list(BAZA_ZAWIASOW.keys()))
    params_szuflad = BAZA_SYSTEMOW[sys_k]
    params_zawias = BAZA_ZAWIASOW[zaw_k]

# ==========================================
# 4. SILNIK OBLICZENIOWY (GENERATOR LISTY)
# ==========================================
szer_wew_total = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)
szer_jednej_wneki = szer_wew_total / ilosc_sekcji if ilosc_sekcji > 0 else 0
wys_wewnetrzna = H_MEBLA - (2 * GR_PLYTY)

lista_elementow = []

def dodaj_el(nazwa, szer, wys, gr, mat="18mm KORPUS", wiercenia=[], ori="L"):
    idx = len(lista_elementow) + 1
    ident = f"{KOD_PROJEKTU}-{idx}"
    lista_elementow.append({
        "ID": ident, "Nazwa": nazwa, "Szerokość [mm]": round(szer, 1), "Wysokość [mm]": round(wys, 1),
        "Grubość [mm]": gr, "Materiał": mat, "wiercenia": wiercenia, "orientacja": ori
    })

def gen_wiercenia_boku(moduly, is_mirror=False):
    otwory = []
    offset_2 = 224.0
    x_f = D_MEBLA - 37.0 if is_mirror else 37.0
    x_b = D_MEBLA - (37.0 + offset_2) if is_mirror else 37.0 + offset_2
    
    fixed_sum = sum(m['wys_mm'] for m in moduly if m['wys_mode'] == 'fixed')
    auto_cnt = sum(1 for m in moduly if m['wys_mode'] == 'auto')
    h_auto = (wys_wewnetrzna - fixed_sum) / auto_cnt if auto_cnt > 0 else 0
    
    curr_y = 0 
    
    for mod in moduly:
        h_mod = mod['wys_mm'] if mod['wys_mode'] == 'fixed' else h_auto
        det = mod['detale']
        
        # DRZWI (Prowadniki)
        if det.get('drzwi'):
            otwory.append((x_f, curr_y + 100, 'green'))
            otwory.append((x_f, curr_y + h_mod - 100, 'green'))

        # SZUFLADY
        if mod['typ'] == "Szuflady":
            n = det.get('ilosc', 2)
            h_front = (h_mod - ((n-1)*3)) / n
            for k in range(n):
                y_slide = curr_y + k*(h_front+3) + 3 + params_szuflad["offset_prowadnica"]
                otwory.append((x_f, y_slide, 'red'))
                otwory.append((x_b, y_slide, 'red'))
        
        # PÓŁKI
        elif mod['typ'] == "Półki":
            n = det.get('ilosc', 1)
            gap = h_mod / (n + 1)
            for k in range(n):
                y_p = curr_y + (k+1)*gap
                otwory.append((x_f, y_p, 'green'))
                otwory.append((D_MEBLA - x_f, y_p, 'green'))
                
        # DRĄŻEK
        elif mod['typ'] == "Drążek":
            y_dr = curr_y + h_mod - 60
            otwory.append((D_MEBLA/2, y_dr, 'green'))

        curr_y += h_mod
        
    return otwory

def gen_konstrukcja():
    boki_h = wys_wewnetrzna
    
    # Bok Lewy
    otw_L = gen_wiercenia_boku(st.session_state['moduly_sekcji'].get(0, []), False)
    dodaj_el("Bok Lewy", D_MEBLA, boki_h, GR_PLYTY, "18mm KORPUS", otw_L, "L")
    
    # Bok Prawy
    otw_P = gen_wiercenia_boku(st.session_state['moduly_sekcji'].get(ilosc_sekcji-1, []), True)
    dodaj_el("Bok Prawy", D_MEBLA, boki_h, GR_PLYTY, "18mm KORPUS", otw_P, "P")
    
    # Wieńce
    otw_W = [(9, 37, 'blue'), (9, D_MEBLA-37, 'blue'), (W_MEBLA-9, 37, 'blue'), (W_MEBLA-9, D_MEBLA-37, 'blue')]
    dodaj_el("Wieniec Górny", W_MEBLA, D_MEBLA, GR_PLYTY, "18mm KORPUS", [], "L")
    dodaj_el("Wieniec Dolny", W_MEBLA, D_MEBLA, GR_PLYTY, "18mm KORPUS", [], "L")
    
    # Przegrody
    for i in range(ilosc_przegrod):
        mod_L = st.session_state['moduly_sekcji'].get(i, [])
        mod_R = st.session_state['moduly_sekcji'].get(i+1, [])
        otw = gen_wiercenia_boku(mod_L, True) + gen_wiercenia_boku(mod_R, False) 
        dodaj_el(f"Przegroda {i+1}", D_MEBLA, boki_h, GR_PLYTY, "18mm KORPUS", otw, "L")

    # Wypełnienie Modułami
    for i in range(ilosc_sekcji):
        moduly = st.session_state['moduly_sekcji'].get(i, [])
        
        fixed_sum = sum(m['wys_mm'] for m in moduly if m['wys_mode'] == 'fixed')
        auto_cnt = sum(1 for m in moduly if m['wys_mode'] == 'auto')
        h_auto = (wys_wewnetrzna - fixed_sum) / auto_cnt if auto_cnt > 0 else 0
        
        for mod in moduly:
            h_mod = mod['wys_mm'] if mod['wys_mode'] == 'fixed' else h_auto
            det = mod['detale']
            
            # DRZWI
            if det.get('drzwi'):
                h_drzwi = h_mod - 4
                w_drzwi = szer_jednej_wneki - 4
                off_p = params_zawias['puszka_offset']
                otw_drzwi = [(off_p, 100, 'green'), (off_p, h_drzwi-100, 'green')]
                dodaj_el(f"Drzwi Sekcja {i+1}", w_drzwi, h_drzwi, 18, "18mm FRONT", otw_drzwi, "L")
            
            # WNĘTRZE
            is_inner = det.get('drzwi', False) 
            
            if mod['typ'] == "Szuflady":
                n = det.get('ilosc', 2)
                h_f = (h_mod - ((n-1)*3)) / n
                
                mat_f = "18mm KORPUS" if is_inner else "18mm FRONT"
                nazwa_f = "Front Szuflady Wew." if is_inner else "Front Szuflady"
                w_f = szer_jednej_wneki - (10 if is_inner else 4) 
                
                for _ in range(n):
                    dodaj_el(nazwa_f, w_f, h_f, 18, mat_f, [], "D")
                    dodaj_el("Dno Szuflady", w_f-71, 476, 3, "3mm HDF", [], "D")
                    dodaj_el("Tył Szuflady", w_f-83, 150, 16, "16mm BIAŁA", [], "D")

            elif mod['typ'] == "Półki":
                n = det.get('ilosc', 1)
                w_p = szer_jednej_wneki - 2
                if is_inner: w_p -= 10 
                
                otw_p = [(9, 37, 'blue'), (9, D_MEBLA-50, 'blue'), (w_p-9, 37, 'blue'), (w_p-9, D_MEBLA-50, 'blue')]
                for _ in range(n):
                    dodaj_el("Półka", w_p, D_MEBLA-20, 18, "18mm KORPUS", otw_p, "L")

gen_konstrukcja()

# ==========================================
# 5. WIDOK GŁÓWNY (TABS)
# ==========================================
df = pd.DataFrame(lista_elementow)
tabs = st.tabs(["📋 LISTA", "📐 RYSUNKI", "🎯 SZABLONY 1:1", "🗺️ ROZKRÓJ", "👁️ WIZUALIZACJA"])

with tabs[0]: st.dataframe(df.drop(columns=['wiercenia', 'orientacja']), use_container_width=True)

with tabs[1]:
    if GRAFIKA_DOSTEPNA:
        c1, c2 = st.columns([1,3])
        if c1.button("📄 Generuj PDF (Całość)"):
            buf = io.BytesIO()
            with PdfPages(buf) as pdf:
                for el in lista_elementow:
                    # FIX: Jawnie nazwane argumenty
                    fig = rysuj_element(
                        szer=el['Szerokość [mm]'], 
                        wys=el['Wysokość [mm]'], 
                        id_elementu=el['ID'], 
                        nazwa=el['Nazwa'], 
                        otwory=el['wiercenia'], 
                        orientacja_frontu=el['orientacja']
                    )
                    if fig: pdf.savefig(fig); plt.close(fig)
            st.session_state['pdf_ready'] = buf
        
        if st.session_state['pdf_ready']:
            c1.download_button("💾 Pobierz PDF", st.session_state['pdf_ready'].getvalue(), "projekt.pdf", "application/pdf")

        sel = c2.selectbox("Wybierz element:", [e['ID'] for e in lista_elementow])
        it = next(x for x in lista_elementow if x['ID'] == sel)
        
        # FIX: Jawnie nazwane argumenty
        st.pyplot(rysuj_element(
            szer=it['Szerokość [mm]'], 
            wys=it['Wysokość [mm]'], 
            id_elementu=it['ID'], 
            nazwa=it['Nazwa'], 
            otwory=it['wiercenia'], 
            orientacja_frontu=it['orientacja']
        ))

with tabs[2]:
    st.info("Szablony 1:1 do druku A4.")
    c1, c2 = st.columns(2)
    el_sz = c1.selectbox("Element", [e['ID'] for e in lista_elementow], key='sz_sel')
    rog = c2.selectbox("Róg", ["Lewy-Dół (LD)", "Lewy-Góra (LG)", "Prawy-Dół (PD)", "Prawy-Góra (PG)"])
    item = next(x for x in lista_elementow if x['ID'] == el_sz)
    st.pyplot(generuj_szablon_a4(item, rog))

with tabs[3]:
    st.write("Prosta optymalizacja (poglądowo)")
    for mat in ["18mm KORPUS", "18mm FRONT", "16mm BIAŁA", "3mm HDF"]:
        el_mat = [x for x in lista_elementow if x['Materiał'] == mat]
        if el_mat:
            st.caption(f"Materiał: {mat} ({len(el_mat)} szt.)")
            area = sum(x['Szerokość [mm]']*x['Wysokość [mm]'] for x in el_mat) / 1000000
            st.progress(min(area/5.7, 1.0), text=f"Szacowane zużycie: {area:.2f} m2")

with tabs[4]:
    if GRAFIKA_DOSTEPNA:
        st.pyplot(rysuj_podglad_mebla(W_MEBLA, H_MEBLA, GR_PLYTY, ilosc_przegrod, st.session_state['moduly_sekcji'], szer_jednej_wneki))
