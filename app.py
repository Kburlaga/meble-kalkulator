import streamlit as st
import pandas as pd
import io
import copy 

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
# 0. BAZY DANYCH
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

# ==========================================
# 1. INICJALIZACJA STANU
# ==========================================
def init_state():
    defaults = {
        'kod_pro': "PROJEKT-1", 
        'h_mebla': 2000, 
        'w_mebla': 1800, 
        'd_mebla': 600, 
        'gr_plyty': 18,
        'il_przegrod': 2,
        'moduly_sekcji': {}, 
        'pdf_ready': None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# Skróty
H_MEBLA = st.session_state['h_mebla']
W_MEBLA = st.session_state['w_mebla']
D_MEBLA = st.session_state['d_mebla']
GR_PLYTY = st.session_state['gr_plyty']
ilosc_przegrod = st.session_state['il_przegrod']
ilosc_sekcji = ilosc_przegrod + 1
KOD_PROJEKTU = st.session_state['kod_pro'].upper()

# ==========================================
# 2. LOGIKA MODUŁÓW
# ==========================================
def usun_modul(nr_sekcji, idx):
    current_data = copy.deepcopy(st.session_state['moduly_sekcji'])
    if nr_sekcji in current_data:
        current_data[nr_sekcji].pop(idx)
        st.session_state['moduly_sekcji'] = current_data
        st.toast(f"Usunięto element z sekcji {nr_sekcji+1}")

def dodaj_modul_akcja(nr_sekcji, typ, tryb_wys, wys_mm, ilosc, drzwi):
    current_data = copy.deepcopy(st.session_state['moduly_sekcji'])
    
    if nr_sekcji not in current_data:
        current_data[nr_sekcji] = []
    
    detale = {'ilosc': int(ilosc), 'drzwi': drzwi}
    nowy_modul = {
        'typ': typ,
        'wys_mode': 'auto' if "AUTO" in tryb_wys else 'fixed',
        'wys_mm': float(wys_mm) if "Fixed" in tryb_wys else 0,
        'detale': detale 
    }
    
    current_data[nr_sekcji].append(nowy_modul)
    st.session_state['moduly_sekcji'] = current_data
    st.toast(f"✅ Dodano {typ} do Sekcji {nr_sekcji+1}")

# ==========================================
# 3. RYSOWANIE
# ==========================================
def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], orientacja_frontu="L", kolor_tla='#e6ccb3'):
    if not GRAFIKA_DOSTEPNA: return None
    plt.close('all')
    fig, ax = plt.subplots(figsize=(10, 6))
    
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla, zorder=1)
    ax.add_patch(rect)
    
    if otwory:
        for otw in otwory:
            x, y = otw[0], otw[1]
            kolor_kod = otw[2] if len(otw) > 2 else 'red'
            
            if kolor_kod == 'blue': 
                ax.add_patch(patches.Circle((x, y), radius=5, edgecolor='blue', facecolor='white', linewidth=1.5, zorder=20))
            elif kolor_kod == 'red': 
                ax.add_patch(patches.Circle((x, y), radius=4, color='red', zorder=20))
                if len(otwory) < 40: ax.text(x+6, y, "Prowadnica", fontsize=7, color='red', zorder=25)
            elif kolor_kod == 'green': 
                r = 17.5 if "Front" in nazwa else 4
                ax.add_patch(patches.Circle((x, y), radius=r, edgecolor='green', facecolor='white', linewidth=1.5, zorder=20))
            
            if len(otwory) < 50:
                ax.text(x+5, y+5, f"({x:.0f},{y:.0f})", fontsize=7, alpha=0.7, zorder=21)

    if orientacja_frontu == 'L':
        ax.add_patch(patches.Rectangle((-5, 0), 5, wys, color='#d62828', zorder=5))
        ax.text(10, wys/2, "FRONT", rotation=90, color='#d62828', weight='bold', zorder=15)
    elif orientacja_frontu == 'D': 
        ax.add_patch(patches.Rectangle((0, -5), szer, 5, color='#d62828', zorder=5))
        ax.text(szer/2, 10, "FRONT", ha='center', color='#d62828', weight='bold', zorder=15)
    elif orientacja_frontu == 'P':
        ax.add_patch(patches.Rectangle((szer, 0), 5, wys, color='#d62828', zorder=5))
        ax.text(szer-20, wys/2, "FRONT", rotation=90, color='#d62828', weight='bold', zorder=15)

    ax.text(szer/2, -30, f"{szer} mm", ha='center', weight='bold')
    ax.text(-30, wys/2, f"{wys} mm", va='center', rotation=90, weight='bold')
    
    ax.set_xlim(-60, szer + 60)
    ax.set_ylim(-60, wys + 60)
    ax.set_aspect('equal'); ax.axis('off')
    return fig

def generuj_szablon_a4(element, rog):
    if not GRAFIKA_DOSTEPNA: return None
    plt.close('all')
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    
    szer, wys = element['Szerokość [mm]'], element['Wysokość [mm]']
    otwory = element['wiercenia']
    
    ax.add_patch(patches.Rectangle((0, 0), szer, wys, linewidth=3, edgecolor='black', facecolor='#eee', zorder=1))
    
    for otw in otwory:
        x, y = otw[0], otw[1]
        kolor = otw[2] if len(otw) > 2 else 'black'
        ax.plot([x-8, x+8], [y, y], color=kolor, linewidth=2, zorder=10)
        ax.plot([x, x], [y-8, y+8], color=kolor, linewidth=2, zorder=10)
        ax.text(x+4, y+4, f"({x:.1f}, {y:.1f})", fontsize=10, color=kolor, zorder=20)

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

    # Obrys mebla
    ax.add_patch(patches.Rectangle((0, 0), w, h, linewidth=3, edgecolor='black', facecolor='none', zorder=5))
    ax.add_patch(patches.Rectangle((0, 0), w, gr, facecolor='#d7ba9d', edgecolor='black', zorder=5))
    ax.add_patch(patches.Rectangle((0, h-gr), w, gr, facecolor='#d7ba9d', edgecolor='black', zorder=5))
    ax.add_patch(patches.Rectangle((0, gr), gr, h-2*gr, facecolor='#d7ba9d', edgecolor='black', zorder=5))
    ax.add_patch(patches.Rectangle((w-gr, gr), gr, h-2*gr, facecolor='#d7ba9d', edgecolor='black', zorder=5))
    
    curr_x = gr
    h_wew = h - 2*gr
    
    for i in range(n_przeg + 1):
        if i < n_przeg:
            ax.add_patch(patches.Rectangle((curr_x + szer_wneki, gr), gr, h_wew, facecolor='gray', alpha=0.3, zorder=1))
        
        moduly = moduly_sekcji.get(i, [])
        if moduly:
            fixed_h_sum = sum(m['wys_mm'] for m in moduly if m['wys_mode'] == 'fixed')
            auto_count = sum(1 for m in moduly if m['wys_mode'] == 'auto')
            auto_h = (h_wew - fixed_h_sum) / auto_count if auto_count > 0 else 0
            
            curr_y = gr 
            
            for mod in moduly:
                h_mod = mod['wys_mm'] if mod['wys_mode'] == 'fixed' else auto_h
                
                # FIX: Przycięcie wizualne do obrysu wnętrza (żeby front nie wystawał)
                # Obliczamy ile miejsca zostało do sufitu
                space_left = (h - gr) - curr_y
                # Rysujemy nie wyżej niż sufit
                h_vis = min(h_mod, space_left) if space_left > 0 else 0
                
                # Ramka modułu (pomocnicza)
                ax.add_patch(patches.Rectangle((curr_x, curr_y), szer_wneki, h_vis, facecolor='none', edgecolor='black', linestyle=':', alpha=0.3, zorder=2))
                
                det = mod['detale']
                if mod['typ'] == "Szuflady":
                    n = det.get('ilosc', 2)
                    if n > 0:
                        h_f = (h_vis - ((n-1)*3)) / n
                        for k in range(n):
                            yf = curr_y + k*(h_f+3)
                            # Fronty szuflad - rysujemy używając h_vis (przyciętej)
                            ax.add_patch(patches.Rectangle((curr_x+2, yf), szer_wneki-4, h_f, facecolor='#f4e1d2', edgecolor='#669bbc', zorder=10))
                            ax.text(curr_x + szer_wneki/2, yf + h_f/2, "SZUFLADA", ha='center', va='center', fontsize=8, color='#004488', zorder=11, fontweight='bold')

                elif mod['typ'] == "Półki":
                    n = det.get('ilosc', 1)
                    if n > 0:
                        gap = h_vis / (n + 1)
                        for k in range(n):
                            yp = curr_y + (k+1)*gap
                            ax.add_patch(patches.Rectangle((curr_x, yp), szer_wneki, gr, color='#8B4513', zorder=10))

                elif mod['typ'] == "Drążek":
                    ax.add_patch(patches.Rectangle((curr_x+5, curr_y + h_vis - 60), szer_wneki-10, 15, facecolor='silver', edgecolor='black', zorder=10))
                    ax.text(curr_x + szer_wneki/2, curr_y + h_vis/2, "DRĄŻEK", ha='center', alpha=0.5, rotation=45, zorder=10)

                if det.get('drzwi'):
                     ax.add_patch(patches.Rectangle((curr_x+1, curr_y+1), szer_wneki-2, h_vis-2, 
                                                  facecolor='green', alpha=0.1, edgecolor='green', linestyle='--', zorder=15))
                     ax.text(curr_x + szer_wneki/2, curr_y + h_vis/2, "DRZWI", ha='center', color='green', fontweight='bold', alpha=0.8, zorder=16)

                curr_y += h_mod

        curr_x += szer_wneki + gr

    ax.set_xlim(-100, w + 100); ax.set_ylim(-100, h + 100)
    ax.set_aspect('equal'); ax.axis('off')
    return fig

# ==========================================
# 4. INTERFEJS GŁÓWNY (SIDEBAR)
# ==========================================
with st.sidebar:
    st.title("🪚 STOLARZPRO V20.3")
    
    if st.button("🗑️ NOWY PROJEKT", type="primary"): 
        st.session_state.clear()
        st.rerun()
    
    st.markdown("### 1. Gabaryty")
    st.text_input("Nazwa", key="kod_pro")
    
    c1, c2 = st.columns(2)
    c1.number_input("Wysokość", key="h_mebla")
    c2.number_input("Szerokość", key="w_mebla")
    c1.number_input("Głębokość", key="d_mebla")
    c2.number_input("Grubość płyty", key="gr_plyty")
    
    st.number_input("Ilość przegród pionowych", min_value=0, key="il_przegrod")

    st.markdown("### 2. Konfigurator Modułowy")
    st.info("Buduj sekcje od dołu do góry.")

    aktualna_ilosc_sekcji = st.session_state['il_przegrod'] + 1
    tabs_sekcji = st.tabs([f"Sekcja {i+1}" for i in range(aktualna_ilosc_sekcji)])
    
    for i, tab in enumerate(tabs_sekcji):
        with tab:
            m_sekcji = st.session_state['moduly_sekcji'].get(i, [])
            
            if m_sekcji:
                st.write("🔽 Dół szafy")
                for idx, mod in enumerate(m_sekcji):
                    opis = f"**{idx+1}. {mod['typ']}**"
                    if mod['wys_mode'] == 'fixed': opis += f" ({mod['wys_mm']}mm)"
                    else: opis += " (AUTO)"
                    
                    c_del, c_info = st.columns([1, 4])
                    if c_del.button("❌", key=f"del_{i}_{idx}"):
                        usun_modul(i, idx)
                        st.rerun()
                    c_info.markdown(opis)
                st.write("🔼 Góra szafy")
                st.markdown("---")
            else:
                st.caption("Brak modułów w tej sekcji.")
            
            with st.form(key=f"form_add_{i}"):
                st.write("➕ Dodaj nowy moduł")
                c_f1, c_f2 = st.columns(2)
                f_typ = c_f1.selectbox("Typ", ["Półki", "Szuflady", "Drążek", "Pusta"])
                f_tryb = c_f2.selectbox("Wysokość", ["Fixed (mm)", "AUTO (Reszta)"])
                
                f_wys_mm = st.number_input("Wysokość (jeśli Fixed)", 100, 2000, 600)
                f_ilosc = st.number_input("Ilość (Szuflad/Półek)", 1, 10, 2)
                f_drzwi = st.checkbox("Zamknij drzwiami?")
                
                submit = st.form_submit_button("Dodaj Moduł")
                
                if submit:
                    dodaj_modul_akcja(i, f_typ, f_tryb, f_wys_mm, f_ilosc, f_drzwi)
                    st.rerun()

    st.markdown("---")
    st.markdown("### 3. Okucia")
    c_s1, c_s2 = st.columns(2)
    sys_k = c_s1.selectbox("Prowadnice", list(BAZA_SYSTEMOW.keys()))
    zaw_k = c_s2.selectbox("Zawiasy", list(BAZA_ZAWIASOW.keys()))
    
# ==========================================
# 5. SILNIK OBLICZENIOWY
# ==========================================
params_szuflad = BAZA_SYSTEMOW[sys_k]
params_zawias = BAZA_ZAWIASOW[zaw_k]
h_mebla_val = st.session_state['h_mebla']
w_mebla_val = st.session_state['w_mebla']
d_mebla_val = st.session_state['d_mebla']
gr_plyty_val = st.session_state['gr_plyty']
n_przegrod_val = st.session_state['il_przegrod']
n_sekcji_val = n_przegrod_val + 1

szer_wew_total = w_mebla_val - (2 * gr_plyty_val) - (n_przegrod_val * gr_plyty_val)
szer_jednej_wneki = szer_wew_total / n_sekcji_val if n_sekcji_val > 0 else 0
wys_wewnetrzna = h_mebla_val - (2 * gr_plyty_val)

lista_elementow = []

def dodaj_el(nazwa, szer, wys, gr, mat="18mm KORPUS", wiercenia=[], ori="L"):
    idx = len(lista_elementow) + 1
    ident = f"{st.session_state['kod_pro']}-{idx}"
    lista_elementow.append({
        "ID": ident, "Nazwa": nazwa, "Szerokość [mm]": round(szer, 1), "Wysokość [mm]": round(wys, 1),
        "Grubość [mm]": gr, "Materiał": mat, "wiercenia": wiercenia, "orientacja": ori
    })

def gen_wiercenia_boku(moduly, is_mirror=False):
    otwory = []
    x_f = 37.0
    x_b = 37.0 + 224.0
    
    fixed_sum = sum(m['wys_mm'] for m in moduly if m['wys_mode'] == 'fixed')
    auto_cnt = sum(1 for m in moduly if m['wys_mode'] == 'auto')
    h_auto = (wys_wewnetrzna - fixed_sum) / auto_cnt if auto_cnt > 0 else 0
    
    curr_y = 0 
    
    for mod in moduly:
        h_mod = mod['wys_mm'] if mod['wys_mode'] == 'fixed' else h_auto
        det = mod['detale']
        
        if det.get('drzwi'):
            otwory.append((x_f, curr_y + 100, 'green'))
            otwory.append((x_f, curr_y + h_mod - 100, 'green'))

        if mod['typ'] == "Szuflady":
            n = det.get('ilosc', 2)
            if n > 0:
                h_front = (h_mod - ((n-1)*3)) / n
                for k in range(n):
                    y_slide = curr_y + k*(h_front+3) + 3 + params_szuflad["offset_prowadnica"]
                    otwory.append((x_f, y_slide, 'red'))
                    otwory.append((x_b, y_slide, 'red'))
        
        elif mod['typ'] == "Półki":
            n = det.get('ilosc', 1)
            if n > 0:
                gap = h_mod / (n + 1)
                for k in range(n):
                    y_p = curr_y + (k+1)*gap
                    otwory.append((x_f, y_p, 'green'))
                    otwory.append((d_mebla_val - 50, y_p, 'green'))
                
        elif mod['typ'] == "Drążek":
            y_dr = curr_y + h_mod - 60
            otwory.append((d_mebla_val/2, y_dr, 'green'))

        curr_y += h_mod
        
    return otwory

def gen_konstrukcja():
    boki_h = wys_wewnetrzna
    
    otw_L = gen_wiercenia_boku(st.session_state['moduly_sekcji'].get(0, []), False)
    dodaj_el("Bok Lewy", d_mebla_val, boki_h, gr_plyty_val, "18mm KORPUS", otw_L, "L")
    
    otw_P = gen_wiercenia_boku(st.session_state['moduly_sekcji'].get(n_sekcji_val-1, []), True)
    dodaj_el("Bok Prawy", d_mebla_val, boki_h, gr_plyty_val, "18mm KORPUS", otw_P, "P")
    
    dodaj_el("Wieniec Górny", w_mebla_val, d_mebla_val, gr_plyty_val, "18mm KORPUS", [], "L")
    dodaj_el("Wieniec Dolny", w_mebla_val, d_mebla_val, gr_plyty_val, "18mm KORPUS", [], "L")
    
    for i in range(n_przegrod_val):
        mod_L = st.session_state['moduly_sekcji'].get(i, [])
        mod_R = st.session_state['moduly_sekcji'].get(i+1, [])
        otw = gen_wiercenia_boku(mod_L, True) + gen_wiercenia_boku(mod_R, False) 
        dodaj_el(f"Przegroda {i+1}", d_mebla_val, boki_h, gr_plyty_val, "18mm KORPUS", otw, "L")

    for i in range(n_sekcji_val):
        moduly = st.session_state['moduly_sekcji'].get(i, [])
        
        fixed_sum = sum(m['wys_mm'] for m in moduly if m['wys_mode'] == 'fixed')
        auto_cnt = sum(1 for m in moduly if m['wys_mode'] == 'auto')
        h_auto = (wys_wewnetrzna - fixed_sum) / auto_cnt if auto_cnt > 0 else 0
        
        for mod in moduly:
            h_mod = mod['wys_mm'] if mod['wys_mode'] == 'fixed' else h_auto
            det = mod['detale']
            
            if det.get('drzwi'):
                h_drzwi = h_mod - 4
                w_drzwi = szer_jednej_wneki - 4
                off_p = params_zawias['puszka_offset']
                otw_drzwi = [(off_p, 100, 'green'), (off_p, h_drzwi-100, 'green')]
                dodaj_el(f"Drzwi Sekcja {i+1}", w_drzwi, h_drzwi, 18, "18mm FRONT", otw_drzwi, "L")
            
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
                
                otw_p = [(9, 37, 'blue'), (9, d_mebla_val-50, 'blue'), (w_p-9, 37, 'blue'), (w_p-9, d_mebla_val-50, 'blue')]
                for _ in range(n):
                    dodaj_el("Półka", w_p, d_mebla_val-20, 18, "18mm KORPUS", otw_p, "L")

gen_konstrukcja()

# ==========================================
# 6. WIDOK GŁÓWNY (TABS)
# ==========================================
df = pd.DataFrame(lista_elementow)
tabs = st.tabs(["📋 LISTA", "📐 RYSUNKI", "🎯 SZABLONY 1:1", "🗺️ ROZKRÓJ", "👁️ WIZUALIZACJA"])

with tabs[0]: 
    st.dataframe(df.drop(columns=['wiercenia', 'orientacja']), width="stretch")

with tabs[1]:
    if GRAFIKA_DOSTEPNA:
        c1, c2 = st.columns([1,3])
        if c1.button("📄 Generuj PDF (Całość)"):
            buf = io.BytesIO()
            with PdfPages(buf) as pdf:
                for el in lista_elementow:
                    plt.clf()
                    fig = rysuj_element(
                        szer=el['Szerokość [mm]'], 
                        wys=el['Wysokość [mm]'], 
                        id_elementu=el['ID'], 
                        nazwa=el['Nazwa'], 
                        otwory=el['wiercenia'], 
                        orientacja_frontu=el['orientacja']
                    )
                    if fig: 
                        pdf.savefig(fig)
                        plt.close(fig) 
            st.session_state['pdf_ready'] = buf
        
        if st.session_state['pdf_ready']:
            c1.download_button("💾 Pobierz PDF", st.session_state['pdf_ready'].getvalue(), "projekt.pdf", "application/pdf")

        sel = c2.selectbox("Wybierz element:", [e['ID'] for e in lista_elementow])
        it = next(x for x in lista_elementow if x['ID'] == sel)
        
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
        st.pyplot(rysuj_podglad_mebla(w_mebla_val, h_mebla_val, gr_plyty_val, ilosc_przegrod, st.session_state['moduly_sekcji'], szer_jednej_wneki))
