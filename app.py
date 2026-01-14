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
    "GTV Axis Pro": {"offset_prowadnica": 37, "offset_front_y": 48},
    "Blum Antaro": {"offset_prowadnica": 37, "offset_front_y": 46}
}

BAZA_ZAWIASOW = {
    "Blum Clip Top": {"puszka_offset": 22}, 
    "GTV Prestige": {"puszka_offset": 22},
    "Hettich Sensys": {"puszka_offset": 23}
}

# ==========================================
# 1. INICJALIZACJA STANU
# ==========================================
def init_state():
    defaults = {
        'kod_pro': "SZAFKA", 
        'h_mebla': 1000, 
        'w_mebla': 600, 
        'd_mebla': 300, 
        'gr_plyty': 18,
        'il_przegrod': 0,
        'typ_konstrukcji': "Wieńce Wpuszczane",
        'typ_plecow': "HDF 3mm (Nakładane)", # Domyślny typ
        'moduly_sekcji': {}, 
        'pdf_ready': None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# Skróty zmiennych (do odczytu)
H_MEBLA = st.session_state['h_mebla']
W_MEBLA = st.session_state['w_mebla']
D_MEBLA = st.session_state['d_mebla']
GR_PLYTY = st.session_state['gr_plyty']
TYP_KONSTRUKCJI = st.session_state.get('typ_konstrukcji', "Wieńce Wpuszczane")
TYP_PLECOW = st.session_state.get('typ_plecow', "HDF 3mm (Nakładane)")
ilosc_przegrod = st.session_state['il_przegrod']
ilosc_sekcji = ilosc_przegrod + 1
KOD_PROJEKTU = st.session_state['kod_pro'].upper().replace(" ", "_")

# ==========================================
# 2. LOGIKA MODUŁÓW
# ==========================================
def usun_modul(nr_sekcji, idx):
    current_data = copy.deepcopy(st.session_state['moduly_sekcji'])
    if nr_sekcji in current_data:
        current_data[nr_sekcji].pop(idx)
        st.session_state['moduly_sekcji'] = current_data
        st.toast(f"Usunięto element z sekcji {nr_sekcji+1}")

def dodaj_modul_akcja(nr_sekcji, typ, tryb_wys, wys_mm, ilosc, drzwi, polki_stale):
    current_data = copy.deepcopy(st.session_state['moduly_sekcji'])
    
    if nr_sekcji not in current_data:
        current_data[nr_sekcji] = []
    
    detale = {
        'ilosc': int(ilosc), 
        'drzwi': drzwi,
        'fixed': polki_stale
    }
    
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
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # Kolorystyka zależna od materiału
    if "HDF" in nazwa: kolor_tla = '#d9d9d9' # Szary dla HDF
    
    plt.title(f"{id_elementu}\n[{nazwa}]", fontsize=16, weight='bold', pad=20, color='#333333')

    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla, zorder=1)
    ax.add_patch(rect)
    
    if otwory:
        for otw in otwory:
            x, y = otw[0], otw[1]
            kolor_kod = otw[2] if len(otw) > 2 else 'red'
            
            if kolor_kod == 'blue': 
                ax.add_patch(patches.Circle((x, y), radius=6, edgecolor='blue', facecolor='white', linewidth=2, zorder=20))
                ax.plot([x-3, x+3], [y, y], color='blue', linewidth=1)
                ax.plot([x, x], [y-3, y+3], color='blue', linewidth=1)
                
            elif kolor_kod == 'red': 
                ax.add_patch(patches.Circle((x, y), radius=4, color='red', zorder=20))
                
            elif kolor_kod == 'green': 
                r = 17.5 if "Front" in nazwa else 4
                ax.add_patch(patches.Circle((x, y), radius=r, edgecolor='green', facecolor='white', linewidth=1.5, zorder=20))

    offset_front = 60 
    
    # Orientacja (Tylko jeśli to nie HDF/Plecy)
    if "Plecy" not in nazwa:
        if orientacja_frontu == 'L':
            ax.add_patch(patches.Rectangle((-5, 0), 5, wys, color='#d62828', zorder=5))
            ax.text(offset_front, wys/2, "FRONT", rotation=90, color='#d62828', weight='bold', zorder=15, ha='center', va='center', fontsize=14)
        elif orientacja_frontu == 'D': 
            ax.add_patch(patches.Rectangle((0, -5), szer, 5, color='#d62828', zorder=5))
            ax.text(szer/2, offset_front, "FRONT", ha='center', va='center', color='#d62828', weight='bold', zorder=15, fontsize=14)
        elif orientacja_frontu == 'P':
            ax.add_patch(patches.Rectangle((szer, 0), 5, wys, color='#d62828', zorder=5))
            ax.text(szer-offset_front, wys/2, "FRONT", rotation=90, color='#d62828', weight='bold', zorder=15, ha='center', va='center', fontsize=14)

    dist_dim = 120
    ax.text(szer/2, -dist_dim, f"{szer:.0f} mm", ha='center', weight='bold', fontsize=12)
    ax.text(-dist_dim, wys/2, f"{wys:.0f} mm", va='center', rotation=90, weight='bold', fontsize=12)
    
    margin = 200
    ax.set_xlim(-margin, szer + margin)
    ax.set_ylim(-margin, wys + margin)
    ax.set_aspect('equal'); ax.axis('off')
    return fig

def generuj_szablon_a4(element, rog):
    if not GRAFIKA_DOSTEPNA: return None
    plt.close('all')
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    
    szer, wys = element['Szerokość [mm]'], element['Wysokość [mm]']
    otwory = element['wiercenia']
    
    plt.title(f"SZABLON: {element['ID']} ({rog})", fontsize=14, pad=10)

    ax.add_patch(patches.Rectangle((0, 0), szer, wys, linewidth=3, edgecolor='black', facecolor='#eee', zorder=1))
    
    for otw in otwory:
        x, y = otw[0], otw[1]
        kolor = otw[2] if len(otw) > 2 else 'black'
        s = 10
        ax.plot([x-s, x+s], [y, y], color=kolor, linewidth=1.5, zorder=10)
        ax.plot([x, x], [y-s, y+s], color=kolor, linewidth=1.5, zorder=10)
        ax.text(x+5, y+5, f"({x:.0f}, {y:.0f})", fontsize=9, color=kolor, zorder=20, weight='bold')

    a4_w, a4_h, m = 210, 297, 10
    
    if "LD" in rog: ax.set_xlim(-m, a4_w-m); ax.set_ylim(-m, a4_h-m)
    elif "LG" in rog: ax.set_xlim(-m, a4_w-m); ax.set_ylim(wys-a4_h+m, wys+m)
    elif "PD" in rog: ax.set_xlim(szer-a4_w+m, szer+m); ax.set_ylim(-m, a4_h-m)
    elif "PG" in rog: ax.set_xlim(szer-a4_w+m, szer+m); ax.set_ylim(wys-a4_h+m, wys+m)

    ax.set_aspect('equal'); ax.grid(True, linestyle=':', alpha=0.5)
    return fig

def rysuj_podglad_mebla(w, h, gr, n_przeg, moduly_sekcji, szer_wneki, typ_konstr):
    if not GRAFIKA_DOSTEPNA: return None
    plt.close('all')
    fig, ax = plt.subplots(figsize=(12, 8))
    
    plt.title(f"WIZUALIZACJA: {KOD_PROJEKTU}\n{typ_konstr}", fontsize=18, weight='bold', pad=20)

    # Obrys mebla
    if "Wpuszczane" in typ_konstr:
        ax.add_patch(patches.Rectangle((0, 0), gr, h, facecolor='#d7ba9d', edgecolor='black', zorder=5))
        ax.add_patch(patches.Rectangle((w-gr, 0), gr, h, facecolor='#d7ba9d', edgecolor='black', zorder=5))
        ax.add_patch(patches.Rectangle((gr, h-gr), w-2*gr, gr, facecolor='#d7ba9d', edgecolor='black', zorder=5))
        ax.add_patch(patches.Rectangle((gr, 0), w-2*gr, gr, facecolor='#d7ba9d', edgecolor='black', zorder=5))
    else:
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
            
            for idx, mod in enumerate(moduly):
                if idx > 0:
                    ax.add_patch(patches.Rectangle((curr_x, curr_y), szer_wneki, gr, facecolor='#d7ba9d', edgecolor='black', zorder=15))
                    curr_y += gr
                
                h_mod = mod['wys_mm'] if mod['wys_mode'] == 'fixed' else auto_h
                space_left = (h - gr) - curr_y
                h_vis = min(h_mod, space_left) if space_left > 0 else 0
                
                det = mod['detale']
                if mod['typ'] == "Półki":
                    n = det.get('ilosc', 1)
                    if n > 0:
                        gap = h_vis / (n + 1)
                        for k in range(n):
                            yp = curr_y + (k+1)*gap
                            color_p = '#8B4513' if not det.get('fixed') else '#d7ba9d'
                            ax.add_patch(patches.Rectangle((curr_x, yp), szer_wneki, gr, color=color_p, zorder=10))

                # Ramka modułu
                ax.add_patch(patches.Rectangle((curr_x, curr_y), szer_wneki, h_vis, facecolor='none', edgecolor='black', linestyle=':', alpha=0.3, zorder=2))
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
    
    st.selectbox("Typ konstrukcji", ["Wieńce Nakładane", "Wieńce Wpuszczane"], key="typ_konstrukcji")
    
    # NOWOŚĆ: WYBÓR PLECÓW
    st.selectbox("Rodzaj Pleców", ["HDF 3mm (Nakładane)", "Płyta 18mm (Wpuszczana)", "Płyta 16mm (Wpuszczana)", "Brak"], key="typ_plecow")
    
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
                    typ_opis = mod['typ']
                    if mod['detale'].get('fixed'): typ_opis += " (STAŁE)"
                    
                    opis = f"**{idx+1}. {typ_opis}**"
                    if mod['wys_mode'] == 'fixed': opis += f" ({mod['wys_mm']}mm)"
                    else: opis += " (AUTO)"
                    
                    c_del, c_info = st.columns([1, 4])
                    if c_del.button("❌", key=f"del_{i}_{idx}"):
                        usun_modul(i, idx)
                        st.rerun()
                    c_info.markdown(opis)
                st.write("🔼 Góra szafy")
                st.markdown("---")
            
            with st.form(key=f"form_add_{i}"):
                st.write("➕ Dodaj nowy moduł")
                c_f1, c_f2 = st.columns(2)
                f_typ = c_f1.selectbox("Typ", ["Półki", "Szuflady", "Drążek", "Pusta"])
                f_tryb = c_f2.selectbox("Wysokość", ["Fixed (mm)", "AUTO (Reszta)"])
                
                f_wys_mm = st.number_input("Wysokość (jeśli Fixed)", 100, 2000, 600)
                f_ilosc = st.number_input("Ilość (Szuflad/Półek)", 1, 10, 1)
                
                c_ch1, c_ch2 = st.columns(2)
                f_drzwi = c_ch1.checkbox("Drzwi?")
                f_stale = False
                if f_typ == "Półki":
                    f_stale = c_ch2.checkbox("Półki stałe (Konfirmaty)?")
                
                submit = st.form_submit_button("Dodaj Moduł")
                
                if submit:
                    dodaj_modul_akcja(i, f_typ, f_tryb, f_wys_mm, f_ilosc, f_drzwi, f_stale)
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
typ_konstr_val = st.session_state.get('typ_konstrukcji', "Wieńce Nakładane")
typ_plecow_val = st.session_state.get('typ_plecow', "HDF 3mm (Nakładane)")
n_przegrod_val = st.session_state['il_przegrod']
n_sekcji_val = n_przegrod_val + 1

# 1. Obliczenie Korpusu Zewnętrznego
if "Wpuszczane" in typ_konstr_val:
    wys_boku = h_mebla_val
    szer_wienca = w_mebla_val - (2 * gr_plyty_val) - (n_przegrod_val * gr_plyty_val)
    if n_przegrod_val > 0:
        szer_wienca = w_mebla_val - (2 * gr_plyty_val) 
    szer_wew_total = szer_wienca - (n_przegrod_val * gr_plyty_val)
else:
    wys_boku = h_mebla_val - (2 * gr_plyty_val)
    szer_wienca = w_mebla_val
    szer_wew_total = w_mebla_val - (2 * gr_plyty_val) - (n_przegrod_val * gr_plyty_val)

szer_jednej_wneki = szer_wew_total / n_sekcji_val if n_sekcji_val > 0 else 0
wys_wewnetrzna = h_mebla_val - (2 * gr_plyty_val)

# 2. Obliczenie Grubości Pleców (Zabieranej głębokości)
gr_plecow = 0
if "18mm" in typ_plecow_val: gr_plecow = 18
elif "16mm" in typ_plecow_val: gr_plecow = 16
# HDF nakładany nie zabiera głębokości wewnętrznej (montowany na zewnątrz)

# Głębokość dostępna dla półek/szuflad
glebokosc_wewnetrzna = d_mebla_val - gr_plecow

lista_elementow = []
counts_dict = {}

def get_unique_id(nazwa_baza):
    key = nazwa_baza.upper()
    if "BOK" in key: key = "BOK"
    elif "WIENIEC" in key: key = "WIENIEC"
    elif "PRZEGRODA" in key: key = "PRZEGRODA"
    elif "FRONT" in key: key = "FRONT"
    elif "PÓŁKA" in key: key = "POLKA"
    elif "PLECY" in key: key = "PLECY"
    elif "DRZWI" in key: key = "DRZWI"
    elif "DNO" in key: key = "DNO"
    elif "TYŁ" in key: key = "TYL"
    else: key = key.replace(" ", "_")
    
    current = counts_dict.get(key, 0) + 1
    counts_dict[key] = current
    return f"{KOD_PROJEKTU}_{key}_{current}"

def dodaj_el(nazwa, szer, wys, gr, mat="18mm KORPUS", wiercenia=[], ori="L"):
    ident = get_unique_id(nazwa)
    lista_elementow.append({
        "ID": ident, "Nazwa": nazwa, "Szerokość [mm]": round(szer, 1), "Wysokość [mm]": round(wys, 1),
        "Grubość [mm]": gr, "Materiał": mat, "wiercenia": wiercenia, "orientacja": ori
    })

def gen_wiercenia_boku(moduly, is_mirror=False):
    otwory = []
    x_f = 37.0
    x_b = 37.0 + 224.0
    
    # Wiercenia Konstrukcyjne
    if "Wpuszczane" in typ_konstr_val:
        otwory.append((x_f, gr_plyty_val/2, 'blue'))
        otwory.append((d_mebla_val - 50, gr_plyty_val/2, 'blue'))
        otwory.append((x_f, h_mebla_val - gr_plyty_val/2, 'blue'))
        otwory.append((d_mebla_val - 50, h_mebla_val - gr_plyty_val/2, 'blue'))

    fixed_sum = sum(m['wys_mm'] for m in moduly if m['wys_mode'] == 'fixed')
    ilosc_wiencow_sr = max(0, len(moduly) - 1)
    h_dostepne = wys_wewnetrzna - (ilosc_wiencow_sr * gr_plyty_val)
    auto_cnt = sum(1 for m in moduly if m['wys_mode'] == 'auto')
    h_auto = (h_dostepne - fixed_sum) / auto_cnt if auto_cnt > 0 else 0
    
    curr_y = gr_plyty_val 
    
    for idx, mod in enumerate(moduly):
        if idx > 0:
            y_wieniec = curr_y + gr_plyty_val/2
            otwory.append((x_f, y_wieniec, 'blue'))
            otwory.append((d_mebla_val - 50, y_wieniec, 'blue'))
            curr_y += gr_plyty_val
            
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
            is_fixed = det.get('fixed', False)
            if n > 0:
                gap = h_mod / (n + 1)
                for k in range(n):
                    y_p = curr_y + (k+1)*gap
                    depth_drill = glebokosc_wewnetrzna if is_fixed else d_mebla_val # Konfirmat wchodzi w półkę
                    if is_fixed:
                        otwory.append((x_f, y_p, 'blue'))
                        otwory.append((d_mebla_val - 50, y_p, 'blue'))
                    else:
                        otwory.append((x_f, y_p, 'green'))
                        otwory.append((depth_drill - 50, y_p, 'green'))
                
        elif mod['typ'] == "Drążek":
            y_dr = curr_y + h_mod - 60
            otwory.append((d_mebla_val/2, y_dr, 'green'))

        curr_y += h_mod
        
    return otwory

def gen_konstrukcja():
    global counts_dict
    counts_dict = {}
    
    # 1. Plecy (Dodajemy jako pierwsze lub osobno)
    if "HDF" in typ_plecow_val:
        dodaj_el("Plecy (HDF)", w_mebla_val-4, h_mebla_val-4, 3, "3mm HDF", [], "X")
    elif "18mm" in typ_plecow_val:
        # Plecy wpuszczane (między bokami, od góry do dołu wewnątrz wieńców wpuszczanych)
        # Przyjmujemy: Szer = Szer wew korpusu, Wys = Wys wew korpusu
        dodaj_el("Plecy (Płyta)", szer_wew_total + (n_przegrod_val*gr_plyty_val), wys_wewnetrzna, 18, "18mm KORPUS", [], "X")
    elif "16mm" in typ_plecow_val:
        dodaj_el("Plecy (Płyta)", szer_wew_total + (n_przegrod_val*gr_plyty_val), wys_wewnetrzna, 16, "16mm BIAŁA", [], "X")

    # 2. Korpus
    otw_L = gen_wiercenia_boku(st.session_state['moduly_sekcji'].get(0, []), False)
    dodaj_el("Bok Lewy", d_mebla_val, wys_boku, gr_plyty_val, "18mm KORPUS", otw_L, "L")
    
    otw_P = gen_wiercenia_boku(st.session_state['moduly_sekcji'].get(n_sekcji_val-1, []), True)
    dodaj_el("Bok Prawy", d_mebla_val, wys_boku, gr_plyty_val, "18mm KORPUS", otw_P, "P")
    
    dodaj_el("Wieniec Górny", szer_wienca, d_mebla_val, gr_plyty_val, "18mm KORPUS", [], "L")
    dodaj_el("Wieniec Dolny", szer_wienca, d_mebla_val, gr_plyty_val, "18mm KORPUS", [], "L")
    
    for i in range(n_przegrod_val):
        mod_L = st.session_state['moduly_sekcji'].get(i, [])
        mod_R = st.session_state['moduly_sekcji'].get(i+1, [])
        otw = gen_wiercenia_boku(mod_L, True) + gen_wiercenia_boku(mod_R, False) 
        dodaj_el(f"Przegroda {i+1}", d_mebla_val, wys_wewnetrzna, gr_plyty_val, "18mm KORPUS", otw, "L")

    # 3. Wypełnienie
    for i in range(n_sekcji_val):
        moduly = st.session_state['moduly_sekcji'].get(i, [])
        
        fixed_sum = sum(m['wys_mm'] for m in moduly if m['wys_mode'] == 'fixed')
        ilosc_wiencow = max(0, len(moduly) - 1)
        h_dostepne = wys_wewnetrzna - (ilosc_wiencow * gr_plyty_val)
        auto_cnt = sum(1 for m in moduly if m['wys_mode'] == 'auto')
        h_auto = (h_dostepne - fixed_sum) / auto_cnt if auto_cnt > 0 else 0
        
        for idx, mod in enumerate(moduly):
            if idx > 0:
                dodaj_el(f"Wieniec Środkowy (Sekcja {i+1})", szer_jednej_wneki, glebokosc_wewnetrzna, gr_plyty_val, "18mm KORPUS", [], "L")
                
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
                    # Dno i tył skrócone o głębokość pleców
                    dodaj_el("Dno Szuflady", w_f-71, 476, 3, "3mm HDF", [], "D")
                    dodaj_el("Tył Szuflady", w_f-83, 150, 16, "16mm BIAŁA", [], "D")

            elif mod['typ'] == "Półki":
                n = det.get('ilosc', 1)
                is_fixed = det.get('fixed', False)
                luz = 2 if not is_fixed else 0 
                w_p = szer_jednej_wneki - luz
                if is_inner and not is_fixed: w_p -= 10 
                
                # Głębokość półki: zawsze -20 od dostępnej głębokości (czyli D_MEBLA - GR_PLECOW - 20)
                d_polki = glebokosc_wewnetrzna if is_fixed else (glebokosc_wewnetrzna - 20)
                
                for _ in range(n):
                    typ_nazwa = "Półka Stała" if is_fixed else "Półka Ruchoma"
                    dodaj_el(typ_nazwa, w_p, d_polki, 18, "18mm KORPUS", [], "L")

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
        fig_vis = rysuj_podglad_mebla(w_mebla_val, h_mebla_val, gr_plyty_val, ilosc_przegrod, st.session_state['moduly_sekcji'], szer_jednej_wneki, typ_konstr_val)
        st.pyplot(fig_vis)
        
        buf_vis = io.BytesIO()
        orient = 'landscape' if w_mebla_val > h_mebla_val else 'portrait'
        paper_size = (11.69, 8.27) if orient == 'landscape' else (8.27, 11.69)
        
        fig_vis.set_size_inches(paper_size)
        with PdfPages(buf_vis) as pdf:
            pdf.savefig(fig_vis, orientation=orient, bbox_inches='tight')
        
        st.download_button(
            label="📄 Pobierz Wizualizację (PDF A4)",
            data=buf_vis.getvalue(),
            file_name=f"WIZUALIZACJA_{KOD_PROJEKTU}.pdf",
            mime="application/pdf"
        )
