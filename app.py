import streamlit as st
import pandas as pd
import io
import copy
import json
import textwrap
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages

# ==========================================
# KONFIGURACJA STRONY
# ==========================================
st.set_page_config(page_title="STOLARZPRO - V20.3", page_icon="🪚", layout="wide")
GRAFIKA_DOSTEPNA = True

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
# 1. ZARZĄDZANIE STANEM
# ==========================================
def init_state():
    defaults = {
        'kod_pro': "SZAFKA", 
        'h_mebla': 1000, 'w_mebla': 600, 'd_mebla': 300, 'gr_plyty': 18,
        'il_przegrod': 0,
        'typ_konstrukcji': "Wieńce Wpuszczane",
        'typ_plecow': "HDF 3mm (Nakładane)",
        'moduly_sekcji': {}, 
        'pdf_ready': None,
        'cena_korpus': 50.0, 'cena_front': 70.0, 'cena_hdf': 15.0, 'cena_okl': 2.0
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ==========================================
# 2. DEFINICJE FUNKCJI POMOCNICZYCH
# ==========================================
def export_project_to_json():
    data = {
        'kod_pro': st.session_state['kod_pro'],
        'h_mebla': st.session_state['h_mebla'],
        'w_mebla': st.session_state['w_mebla'],
        'd_mebla': st.session_state['d_mebla'],
        'gr_plyty': st.session_state['gr_plyty'],
        'il_przegrod': st.session_state['il_przegrod'],
        'typ_konstrukcji': st.session_state.get('typ_konstrukcji'),
        'typ_plecow': st.session_state.get('typ_plecow'),
        'moduly_sekcji': st.session_state['moduly_sekcji'],
        'ceny': {
            'korpus': st.session_state['cena_korpus'],
            'front': st.session_state['cena_front'],
            'hdf': st.session_state['cena_hdf'],
            'okl': st.session_state['cena_okl']
        }
    }
    return json.dumps(data, indent=4)

def load_project_from_json(uploaded_file):
    try:
        data = json.load(uploaded_file)
        st.session_state['kod_pro'] = data.get('kod_pro', "PROJEKT")
        st.session_state['h_mebla'] = data.get('h_mebla', 1000)
        st.session_state['w_mebla'] = data.get('w_mebla', 600)
        st.session_state['d_mebla'] = data.get('d_mebla', 300)
        st.session_state['gr_plyty'] = data.get('gr_plyty', 18)
        st.session_state['il_przegrod'] = data.get('il_przegrod', 0)
        st.session_state['typ_konstrukcji'] = data.get('typ_konstrukcji', "Wieńce Nakładane")
        st.session_state['typ_plecow'] = data.get('typ_plecow', "HDF 3mm (Nakładane)")
        raw_moduly = data.get('moduly_sekcji', {})
        st.session_state['moduly_sekcji'] = {int(k): v for k, v in raw_moduly.items()}
        ceny = data.get('ceny', {})
        st.session_state['cena_korpus'] = ceny.get('korpus', 50.0)
        st.session_state['cena_front'] = ceny.get('front', 70.0)
        st.session_state['cena_hdf'] = ceny.get('hdf', 15.0)
        st.session_state['cena_okl'] = ceny.get('okl', 2.0)
        st.toast("✅ Projekt wczytany pomyślnie!")
    except Exception as e:
        st.error(f"Błąd pliku: {e}")

def usun_modul(nr_sekcji, idx):
    current_data = copy.deepcopy(st.session_state['moduly_sekcji'])
    if nr_sekcji in current_data:
        current_data[nr_sekcji].pop(idx)
        st.session_state['moduly_sekcji'] = current_data
        st.toast(f"Usunięto element z sekcji {nr_sekcji+1}")

def dodaj_modul_akcja(nr_sekcji, typ, tryb_wys, wys_mm, ilosc, drzwi, polki_stale):
    current_data = copy.deepcopy(st.session_state['moduly_sekcji'])
    if nr_sekcji not in current_data: current_data[nr_sekcji] = []
    detale = {'ilosc': int(ilosc), 'drzwi': drzwi, 'fixed': polki_stale}
    nowy_modul = {
        'typ': typ,
        'wys_mode': 'auto' if "AUTO" in tryb_wys else 'fixed',
        'wys_mm': float(wys_mm) if "Fixed" in tryb_wys else 0,
        'detale': detale 
    }
    current_data[nr_sekcji].append(nowy_modul)
    st.session_state['moduly_sekcji'] = current_data
    st.toast(f"✅ Dodano {typ} do Sekcji {nr_sekcji+1}")

def get_unique_id(nazwa_baza, counts_dict, kod_projektu):
    key = nazwa_baza.upper().replace(" ", "_")
    map_keys = {"BOK LEWY": "BOK_L", "BOK PRAWY": "BOK_P", "WIENIEC GÓRNY": "WIENIEC_G", "WIENIEC DOLNY": "WIENIEC_D", "PRZEGRODA": "PRZEG", "FRONT SZUFLADY": "FR_SZUF", "DNO SZUFLADY": "DNO_SZUF", "TYŁ SZUFLADY": "TYL_SZUF"}
    short_key = key
    for k_map, v_map in map_keys.items():
        if k_map.replace(" ", "_") in key:
            short_key = key.replace(k_map.replace(" ", "_"), v_map)
            break
    current = counts_dict.get(short_key, 0) + 1
    counts_dict[short_key] = current
    return f"{kod_projektu}_{short_key}"

def opisz_oklejanie(nazwa, szer_el, wys_el):
    n = nazwa.upper()
    if "FRONT" in n or "DRZWI" in n: return "4 krawędzie (2mm)"
    elif "WIENIEC" in n or "PÓŁKA" in n or "PRZEGRODA" in n:
        return "1 Długa (Przód)" if szer_el >= wys_el else "1 Krótka (Przód)"
    elif "BOK" in n: return "1 Długa + 2 Krótkie (Przód+Góra+Dół)"
    return "Brak" if "DNO" in n or "TYŁ" in n or "PLECY" in n else "Wg uznania"

# ==========================================
# 3. INTERFEJS GŁÓWNY (SIDEBAR)
# ==========================================
with st.sidebar:
    st.title("🪚 STOLARZPRO V20.3")
    c_dl, c_upl = st.columns(2)
    c_dl.download_button("Pobierz .JSON", export_project_to_json(), f"projekt.json", "application/json")
    uploaded = c_upl.file_uploader("Wczytaj", type=['json'], label_visibility="collapsed")
    if uploaded: load_project_from_json(uploaded)
    if st.button("🗑️ NOWY PROJEKT", type="primary"): st.session_state.clear(); st.rerun()
    st.markdown("---")
    st.text_input("Nazwa", key="kod_pro")
    st.selectbox("Typ", ["Wieńce Nakładane", "Wieńce Wpuszczane"], key="typ_konstrukcji")
    st.selectbox("Plecy", ["HDF 3mm (Nakładane)", "Płyta 18mm (Wpuszczana)", "Płyta 16mm (Wpuszczana)", "Brak"], key="typ_plecow")
    c1, c2 = st.columns(2); c1.number_input("Wysokość", key="h_mebla"); c2.number_input("Szerokość", key="w_mebla")
    c1.number_input("Głębokość", key="d_mebla"); c2.number_input("Grubość", key="gr_plyty"); st.number_input("Przegrody", key="il_przegrod")
    with st.expander("💰 Ceny"):
        st.number_input("Płyta Korpus", value=50.0, key='cena_korpus')
        st.number_input("Płyta Front", value=70.0, key='cena_front')
        st.number_input("HDF", value=15.0, key='cena_hdf')
        st.number_input("Oklejanie (zł/mb)", value=2.0, key='cena_okl')
    st.markdown("### 2. Moduły")
    aktualna_ilosc_sekcji = st.session_state['il_przegrod'] + 1
    tabs_sekcji = st.tabs([f"Sekcja {i+1}" for i in range(aktualna_ilosc_sekcji)])
    for i, tab in enumerate(tabs_sekcji):
        with tab:
            m_sekcji = st.session_state['moduly_sekcji'].get(i, [])
            if m_sekcji:
                for idx, mod in enumerate(m_sekcji):
                    c_del, c_info = st.columns([1, 4])
                    if c_del.button("X", key=f"del_{i}_{idx}"): usun_modul(i, idx); st.rerun()
                    c_info.markdown(f"{mod['typ']}")
            with st.form(key=f"form_add_{i}"):
                f_typ = st.selectbox("Typ", ["Półki", "Szuflady", "Drążek", "Pusta"])
                f_tryb = st.selectbox("Wysokość", ["Fixed (mm)", "AUTO"])
                f_wys = st.number_input("Wysokość (mm)", 100, 2000, 600)
                f_il = st.number_input("Ilość", 1, 10, 1)
                c_a, c_b = st.columns(2)
                f_d = c_a.checkbox("Drzwi?"); f_s = False
                if f_typ == "Półki": f_s = c_b.checkbox("Stałe?")
                if st.form_submit_button("Dodaj"): dodaj_modul_akcja(i, f_typ, f_tryb, f_wys, f_il, f_d, f_s); st.rerun()
    st.markdown("---"); c_s1, c_s2 = st.columns(2)
    sys_k = c_s1.selectbox("Prowadnice", list(BAZA_SYSTEMOW.keys()))
    zaw_k = c_s2.selectbox("Zawiasy", list(BAZA_ZAWIASOW.keys()))

# ==========================================
# 4. ZMIENNE GLOBALNE I OBLICZENIA
# ==========================================
PARAMS_SZUFLAD = BAZA_SYSTEMOW[sys_k]
PARAMS_ZAWIAS = BAZA_ZAWIASOW[zaw_k]
H_MEBLA = st.session_state['h_mebla']; W_MEBLA = st.session_state['w_mebla']; D_MEBLA = st.session_state['d_mebla']; GR_PLYTY = st.session_state['gr_plyty']
TYP_KONSTRUKCJI = st.session_state.get('typ_konstrukcji', "Wieńce Nakładane"); TYP_PLECOW = st.session_state.get('typ_plecow', "HDF 3mm (Nakładane)")
ILOSC_PRZEGROD = st.session_state['il_przegrod']; N_SEKCJI = ILOSC_PRZEGROD + 1
KOD_PROJEKTU = st.session_state['kod_pro'].upper().replace(" ", "_")

if "Wpuszczane" in TYP_KONSTRUKCJI:
    WYS_BOKU = H_MEBLA; SZER_WIENCA = W_MEBLA - (2*GR_PLYTY) - (ILOSC_PRZEGROD*GR_PLYTY)
    if ILOSC_PRZEGROD > 0: SZER_WIENCA = W_MEBLA - (2*GR_PLYTY)
    SZER_WEW_TOTAL = SZER_WIENCA - (ILOSC_PRZEGROD*GR_PLYTY)
else:
    WYS_BOKU = H_MEBLA - (2*GR_PLYTY); SZER_WIENCA = W_MEBLA
    SZER_WEW_TOTAL = W_MEBLA - (2*GR_PLYTY) - (ILOSC_PRZEGROD*GR_PLYTY)

SZER_JEDNEJ_WNEKI = SZER_WEW_TOTAL / N_SEKCJI if N_SEKCJI > 0 else 0
WYS_WEWNETRZNA = H_MEBLA - (2*GR_PLYTY)
GR_PLECOW = 18 if "18mm" in TYP_PLECOW else (16 if "16mm" in TYP_PLECOW else 0)
GLEBOKOSC_WEWNETRZNA = D_MEBLA - GR_PLECOW

lista_elementow = []; counts_dict = {}

def dodaj_element_do_listy(nazwa, szer, wys, gr, mat, wiercenia, ori):
    ident = get_unique_id(nazwa, counts_dict, KOD_PROJEKTU)
    okl = opisz_oklejanie(nazwa, szer, wys)
    lista_elementow.append({"ID": ident, "Nazwa": nazwa, "Szerokość [mm]": int(round(szer)), "Wysokość [mm]": int(round(wys)), "Grubość [mm]": gr, "Materiał": mat, "Oklejanie": okl, "wiercenia": wiercenia, "orientacja": ori})

def gen_wiercenia_boku(moduly, is_mirror=False):
    otwory = []
    if is_mirror: x_f = D_MEBLA-37.0; x_b = D_MEBLA-(37.0+224.0); x_plecy_ref = GR_PLECOW/2
    else: x_f = 37.0; x_b = 37.0+224.0; x_plecy_ref = D_MEBLA-(GR_PLECOW/2)
    if "Wpuszczane" in TYP_KONSTRUKCJI: xt = 50.0 if is_mirror else D_MEBLA-50.0; otwory += [(x_f, GR_PLYTY/2, 'blue'), (xt, GR_PLYTY/2, 'blue'), (x_f, H_MEBLA-GR_PLYTY/2, 'blue'), (xt, H_MEBLA-GR_PLYTY/2, 'blue')]
    if GR_PLECOW > 0:
        for k in range(int(H_MEBLA/400)+2):
            yp = 50 + k*((H_MEBLA-100)/(int(H_MEBLA/400)+1)); 
            if yp>GR_PLYTY and yp<H_MEBLA-GR_PLYTY: otwory.append((x_plecy_ref, yp, 'blue'))
    curr_y = GR_PLYTY; ha = (WYS_WEWNETRZNA - sum(m['wys_mm'] for m in moduly if m['wys_mode'] == 'fixed')) / max(1, sum(1 for m in moduly if m['wys_mode'] == 'auto'))
    for m in moduly:
        hm = m['wys_mm'] if m['wys_mode'] == 'fixed' else ha
        det = m['detale']
        if m != moduly[0]: yw=curr_y+GR_PLYTY/2; xt=50.0 if is_mirror else D_MEBLA-50.0; otwory+=[(x_f, yw, 'blue'), (xt, yw, 'blue')]; curr_y+=GR_PLYTY
        if det.get('drzwi'): otwory+=[(x_f, curr_y+100, 'green'), (x_f, curr_y+hm-100, 'green')]
        if m['typ'] == "Szuflady":
            for k in range(det.get('ilosc', 2)): ys=curr_y+k*((hm-(det.get('ilosc')-1)*3)/det.get('ilosc')+3)+3+PARAMS_SZUFLAD["offset_prowadnica"]; otwory+=[(x_f, ys, 'red'), (x_b, ys, 'red')]
        elif m['typ'] == "Półki":
            for k in range(det.get('ilosc', 1)): yp=curr_y+(k+1)*(hm/(det.get('ilosc')+1)); xb=(50.0 if is_mirror else D_MEBLA-50.0) if det.get('fixed') else (50.0 if is_mirror else D_MEBLA-GR_PLECOW-50.0); otwory+=[(x_f, yp, 'blue' if det.get('fixed') else 'green'), (xb, yp, 'blue' if det.get('fixed') else 'green')]
        curr_y += hm
    return otwory

def run_generator():
    global lista_elementow; lista_elementow = [] 
    if "HDF" in TYP_PLECOW: dodaj_element_do_listy("Plecy (HDF)", W_MEBLA-4, H_MEBLA-4, 3, "3mm HDF", [], "X")
    elif GR_PLECOW > 0: dodaj_element_do_listy("Plecy (Płyta)", (W_MEBLA if "Nakładane" in TYP_KONSTRUKCJI else SZER_WEW_TOTAL+(ILOSC_PRZEGROD*GR_PLYTY)), WYS_WEWNETRZNA, GR_PLECOW, f"{GR_PLECOW}mm KORPUS", [], "X")
    dodaj_element_do_listy("Bok Lewy", D_MEBLA, WYS_BOKU, GR_PLYTY, "18mm KORPUS", gen_wiercenia_boku(st.session_state['moduly_sekcji'].get(0, []), False), "L")
    dodaj_element_do_listy("Bok Prawy", D_MEBLA, WYS_BOKU, GR_PLYTY, "18mm KORPUS", gen_wiercenia_boku(st.session_state['moduly_sekcji'].get(N_SEKCJI-1, []), True), "P")
    dodaj_element_do_listy("Wieniec Górny", SZER_WIENCA, GLEBOKOSC_WEWNETRZNA, GR_PLYTY, "18mm KORPUS", [], "L")
    dodaj_element_do_listy("Wieniec Dolny", SZER_WIENCA, GLEBOKOSC_WEWNETRZNA, GR_PLYTY, "18mm KORPUS", [], "L")
    for i in range(ILOSC_PRZEGROD): dodaj_element_do_listy(f"Przegroda {i+1}", D_MEBLA, WYS_WEWNETRZNA, GR_PLYTY, "18mm KORPUS", gen_wiercenia_boku(st.session_state['moduly_sekcji'].get(i, []), True)+gen_wiercenia_boku(st.session_state['moduly_sekcji'].get(i+1, []), False), "L")
    for i in range(N_SEKCJI):
        moduly = st.session_state['moduly_sekcji'].get(i, [])
        ha = (WYS_WEWNETRZNA - sum(m['wys_mm'] for m in moduly if m['wys_mode'] == 'fixed')) / max(1, sum(1 for m in moduly if m['wys_mode'] == 'auto'))
        for idx, mod in enumerate(moduly):
            if idx > 0: dodaj_element_do_listy(f"Wieniec Środkowy (Sekcja {i+1})", SZER_JEDNEJ_WNEKI, GLEBOKOSC_WEWNETRZNA, GR_PLYTY, "18mm KORPUS", [], "L")
            hm = mod['wys_mm'] if mod['wys_mode'] == 'fixed' else ha; det = mod['detale']
            if det.get('drzwi'): dodaj_element_do_listy(f"Drzwi (Sekcja {i+1})", SZER_JEDNEJ_WNEKI-4, hm-4, 18, "18mm FRONT", [], "L")
            if mod['typ'] == "Szuflady":
                hf = (hm - ((det.get('ilosc')-1)*3)) / det.get('ilosc')
                for k in range(det.get('ilosc')):
                    dodaj_element_do_listy(f"Front Szuflady {k+1} (Sekcja {i+1})", SZER_JEDNEJ_WNEKI-4, hf, 18, "18mm KORPUS" if det.get('drzwi') else "18mm FRONT", [], "D")
                    dodaj_element_do_listy(f"Dno Szuflady {k+1} (Sekcja {i+1})", SZER_JEDNEJ_WNEKI-71, 476, 3, "3mm HDF", [], "D")
                    dodaj_element_do_listy(f"Tył Szuflady {k+1} (Sekcja {i+1})", SZER_JEDNEJ_WNEKI-83, 150, 16, "16mm BIAŁA", [], "D")
            elif mod['typ'] == "Półki":
                wp = SZER_JEDNEJ_WNEKI - (0 if det.get('fixed') else 2)
                if det.get('drzwi') and not det.get('fixed'): wp -= 10
                dp = GLEBOKOSC_WEWNETRZNA if det.get('fixed') else (GLEBOKOSC_WEWNETRZNA - 20)
                for k in range(det.get('ilosc')): dodaj_element_do_listy(f"{'Półka Stała' if det.get('fixed') else 'Półka Ruchoma'} {k+1} (Sekcja {i+1})", wp, dp, 18, "18mm KORPUS", [], "L")

run_generator()
df = pd.DataFrame(lista_elementow)

# ==========================================
# 5. INSTRUKCJE I RYSUNKI
# ==========================================
def generuj_instrukcje_tekst():
    konf = 0; wkr = 0
    if "Wpuszczane" in TYP_KONSTRUKCJI: konf += 8 + (4 * ILOSC_PRZEGROD)
    if "Płyta" in TYP_PLECOW: konf += 4 * (int(H_MEBLA/400)+1)
    for s in st.session_state['moduly_sekcji'].values():
        if len(s) > 1: konf += 4 * (len(s)-1)
        for m in s:
            if m['typ']=="Półki" and m['detale'].get('fixed'): konf+=4*m['detale'].get('ilosc')
            if m['typ']=="Szuflady": wkr+=8*m['detale'].get('ilosc')
            if m['detale'].get('drzwi'): wkr+=8
    if "HDF" in TYP_PLECOW: wkr += int((2*H_MEBLA + 2*W_MEBLA)/150)
    
    return f"""INSTRUKCJA MONTAŻU: {KOD_PROJEKTU}
------------------------------------------------------------
LISTA ZAKUPOWA (SZACUNEK):
[ ] Konfirmaty: ok. {konf} szt.
[ ] Wkręty 3.5x16: ok. {wkr} szt.
------------------------------------------------------------
KROK 0: TRASOWANIE
1. Użyj rysunków PDF do zaznaczenia linii przerywanych na bokach.
2. Przecięcia linii to punkty wiercenia.

KROK 1: WIERCENIE
1. Punkty NIEBIESKIE: Wierć przelotowo (fi 5/7mm) pod konfirmaty.
2. Punkty CZERWONE/ZIELONE: Puntuj (fi 2mm) pod wkręty.

KROK 2: MONTAŻ BOKÓW
1. Przykręć prowadnice i zawiasy do leżących boków.

KROK 3: SKŁADANIE KORPUSU
1. Skręć wieńce z bokami. Sprawdź kąty.

KROK 4: FINAŁ
1. Montaż pleców i frontów."""

def rysuj_instrukcje_pdf(tekst):
    plt.close('all'); fig, ax = plt.subplots(figsize=(8.27, 11.69)); ax.axis('off')
    ax.text(0.05, 0.95, "\n".join([textwrap.fill(l, 85) for l in tekst.split('\n')]), ha='left', va='top', fontsize=10, family='monospace')
    return fig

# FIX: FRONT BARDZO DALEKO (250mm), DUŻE MARGINESY (350mm)
def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], orientacja_frontu="L", kolor_tla='#e6ccb3', figsize=(10, 7)):
    plt.close('all'); fig, ax = plt.subplots(figsize=figsize)
    if "HDF" in nazwa: kolor_tla = '#d9d9d9'
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla, zorder=1); ax.add_patch(rect)
    
    # Header
    fig.text(0.5, 0.96, nazwa.upper(), ha='center', va='top', fontsize=18, weight='bold')
    fig.text(0.5, 0.93, id_elementu, ha='center', va='top', fontsize=10, color='#555', family='monospace')

    if otwory:
        ux = sorted(list(set([o[0] for o in otwory]))); uy = sorted(list(set([o[1] for o in otwory])))
        for yl in uy:
            ax.plot([-500, szer+500], [yl, yl], color='#444', linestyle='--', linewidth=0.4, alpha=0.6)
            ax.text(-25, yl, f"Y:{yl:.0f}", ha='right', va='center', fontsize=7, color='#444')
            ax.text(szer+25, yl, f"{yl:.0f}", ha='left', va='center', fontsize=7, color='#444')
        for xl in ux:
            ax.plot([xl, xl], [-500, wys+500], color='#444', linestyle='--', linewidth=0.4, alpha=0.6)
            ax.text(xl, -30, f"X:{xl:.0f}", ha='center', va='top', fontsize=7, color='#444', rotation=90)
        for i, (x,y,c) in enumerate(sorted(otwory, key=lambda k: (k[1], k[0]))):
            if c=='blue': ax.add_patch(patches.Circle((x,y), 6, edgecolor='blue', facecolor='white', lw=2))
            elif c=='red': ax.add_patch(patches.Circle((x,y), 4, color='red'))
            elif c=='green': ax.add_patch(patches.Circle((x,y), 17.5 if "Front" in nazwa else 4, edgecolor='green', facecolor='white', lw=1.5))
            ax.add_patch(patches.Circle((x+12, y+12), 9, color='black', zorder=40))
            ax.text(x+12, y+12, str(i+1), color='white', ha='center', va='center', fontsize=9, weight='bold', zorder=41)

    # Front logic
    is_h = "WIENIEC" in nazwa.upper() or "PÓŁKA" in nazwa.upper(); dist = 250 # FIX: 25cm odstępu
    if "Plecy" not in nazwa:
        if is_h: 
            ax.add_patch(patches.Rectangle((0, -5), szer, 5, color='#d62828'))
            ax.text(szer/2, -dist, "FRONT", ha='center', va='center', color='#d62828', weight='bold', fontsize=16)
        else:
            if orientacja_frontu == 'L': ax.add_patch(patches.Rectangle((-5,0), 5, wys, color='#d62828')); ax.text(-dist, wys/2, "FRONT", rotation=90, color='#d62828', weight='bold', fontsize=16, ha='center', va='center')
            elif orientacja_frontu == 'P': ax.add_patch(patches.Rectangle((szer,0), 5, wys, color='#d62828')); ax.text(szer+dist, wys/2, "FRONT", rotation=270, color='#d62828', weight='bold', fontsize=16, ha='center', va='center')
            elif orientacja_frontu == 'D': ax.add_patch(patches.Rectangle((0, -5), szer, 5, color='#d62828')); ax.text(szer/2, -dist, "FRONT", ha='center', va='center', color='#d62828', weight='bold', fontsize=16)

    # Dims
    ax.text(szer/2, wys+150, f"{szer:.0f} mm", ha='center', weight='bold', fontsize=14)
    ax.text(szer+150, wys/2, f"{wys:.0f} mm", va='center', rotation=90, weight='bold', fontsize=14)
    
    # Margins
    mx = max(szer*0.3, 350); my = max(wys*0.2, 250)
    ax.set_xlim(-mx, szer+mx); ax.set_ylim(-my, wys+my)
    plt.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.02); ax.set_aspect('equal'); ax.axis('off'); return fig

def rysuj_tabele_strona(id_e, n, o):
    plt.close('all'); fig, ax = plt.subplots(figsize=(8.27, 11.69)); ax.axis('off')
    fig.text(0.5, 0.95, "TABELA WIERCEŃ", ha='center', weight='bold', size=16)
    fig.text(0.5, 0.92, f"Element: {n}", ha='center', size=12)
    fig.text(0.5, 0.90, f"ID: {id_e}", ha='center', size=10, family='monospace', color='#555')
    td = []
    for i, (x,y,c) in enumerate(sorted(o, key=lambda k: (k[1], k[0]))):
        t = "Konfirmat" if c=='blue' else ("Prowadnica" if c=='red' else "Podpórka/Zawias")
        td.append([str(i+1), f"{x:.1f}", f"{y:.1f}", t])
    if td:
        tb = ax.table(cellText=td, colLabels=["Nr", "X", "Y", "Typ"], loc='top', bbox=[0.1, 0.05, 0.8, 0.8]); tb.auto_set_font_size(False); tb.set_fontsize(10)
        for (r,c), cell in tb.get_celld().items():
            cell.set_height(0.04); 
            if r==0: cell.set_facecolor('#333'); cell.set_text_props(color='white', weight='bold')
            elif r%2==0: cell.set_facecolor('#f4f4f4')
    else: ax.text(0.5, 0.5, "Brak otworów", ha='center')
    return fig

def rysuj_nesting(els):
    els = sorted(els, key=lambda x: x['h'], reverse=True)
    fig = plt.figure(figsize=(10, 10)); ax = fig.add_subplot(111)
    ax.add_patch(patches.Rectangle((0,0), 2800, 2070, facecolor='#eee', edgecolor='black'))
    cx, cy, ch = 0, 0, 0
    for i, e in enumerate(els):
        w, h = e['w']+4, e['h']+4
        if cx+w > 2800: cx=0; cy+=ch; ch=0
        if cy+h > 2070: break
        ax.add_patch(patches.Rectangle((cx, cy), w-4, h-4, facecolor='#d7ba9d', alpha=0.8, edgecolor='black'))
        fs = 8 if min(w,h)>100 else 6; rot = 90 if h>w else 0
        ax.text(cx+w/2, cy+h/2, f"#{i+1}\n{e['w']}x{e['h']}", ha='center', va='center', fontsize=fs, rotation=rot)
        cx+=w; ch=max(ch, h)
    ax.set_xlim(0, 2800); ax.set_ylim(0, 2070); ax.set_aspect('equal'); ax.axis('off'); ax.set_title("Rozkrój (Poglądowy)", size=14)
    return fig

def rysuj_podglad_mebla(w, h, gr, n_p, ms, sw, tk):
    plt.close('all'); fig, ax = plt.subplots(figsize=(12, 8)); ax.axis('off'); ax.set_aspect('equal')
    ax.set_xlim(-100, w+100); ax.set_ylim(-100, h+100); ax.set_title("WIZUALIZACJA", size=18, weight='bold')
    if "Wpuszczane" in tk: r=[(0,0,gr,h), (w-gr,0,gr,h), (gr,h-gr,w-2*gr,gr), (gr,0,w-2*gr,gr)]
    else: r=[(0,0,w,gr), (0,h-gr,w,gr), (0,gr,gr,h-2*gr), (w-gr,gr,gr,h-2*gr)]
    for rx,ry,rw,rh in r: ax.add_patch(patches.Rectangle((rx,ry), rw, rh, facecolor='#d7ba9d', edgecolor='black'))
    cx = gr
    for i in range(n_p+1):
        if i < n_p: ax.add_patch(patches.Rectangle((cx+sw, gr), gr, h-2*gr, facecolor='gray', alpha=0.5))
        cy = gr; m_list = ms.get(i, [])
        ha = (h-2*gr - sum(m['wys_mm'] for m in m_list if m['wys_mode']=='fixed')) / max(1, sum(1 for m in m_list if m['wys_mode']=='auto'))
        for idx, m in enumerate(m_list):
            if idx>0: ax.add_patch(patches.Rectangle((cx, cy), sw, gr, facecolor='#d7ba9d', edgecolor='black')); cy+=gr
            hm = m['wys_mm'] if m['wys_mode']=='fixed' else ha
            if m['typ'] == "Półki":
                g = hm/(m['detale'].get('ilosc')+1)
                for k in range(m['detale'].get('ilosc')): ax.add_patch(patches.Rectangle((cx, cy+(k+1)*g), sw, gr, color='#8B4513'))
            ax.add_patch(patches.Rectangle((cx, cy), sw, hm, fill=False, edgecolor='black', ls=':', alpha=0.3)); cy+=hm
        cx += sw + gr
    return fig

# ==========================================
# 6. UI
# ==========================================
tabs = st.tabs(["📋 LISTA", "📐 RYSUNKI", "🛠️ INSTRUKCJA", "💰 KOSZTORYS", "🗺️ ROZKRÓJ", "👁️ WIZUALIZACJA"])

with tabs[0]: 
    df_disp = df.drop(columns=['wiercenia', 'orientacja'])
    st.download_button("💾 CSV", df_disp.to_csv(index=False).encode('utf-8-sig'), f"{KOD_PROJEKTU}.csv", "text/csv")
    st.dataframe(df_disp, use_container_width=True)

with tabs[1]:
    if st.button("📄 GENERUJ PDF"):
        buf = io.BytesIO()
        with PdfPages(buf) as pdf:
            for el in lista_elementow:
                plt.clf()
                fs = (11.69, 8.27) if el['Szerokość [mm]'] > el['Wysokość [mm]'] else (8.27, 11.69)
                o = 'landscape' if el['Szerokość [mm]'] > el['Wysokość [mm]'] else 'portrait'
                pdf.savefig(rysuj_element(el['Szerokość [mm]'], el['Wysokość [mm]'], el['ID'], el['Nazwa'], el['wiercenia'], el['orientacja'], figsize=fs), orientation=o)
                if el['wiercenia']: pdf.savefig(rysuj_tabele_strona(el['ID'], el['Nazwa'], el['wiercenia']), orientation='portrait')
            pdf.savefig(rysuj_instrukcje_pdf(generuj_instrukcje_tekst()), orientation='portrait')
        st.session_state['pdf_ready'] = buf
    if st.session_state['pdf_ready']: st.download_button("POBIERZ PDF", st.session_state['pdf_ready'].getvalue(), "projekt.pdf", "application/pdf")
    
    s = st.selectbox("Podgląd", [e['ID'] for e in lista_elementow])
    el = next(x for x in lista_elementow if x['ID']==s)
    st.pyplot(rysuj_element(el['Szerokość [mm]'], el['Wysokość [mm]'], el['ID'], el['Nazwa'], el['wiercenia'], el['orientacja']))

with tabs[2]: st.text(generuj_instrukcje_tekst())
with tabs[3]:
    st.write(f"RAZEM (Płyta): {sum(x['Szerokość [mm]']*x['Wysokość [mm]'] for x in lista_elementow if 'KORPUS' in x['Materiał'])/1000000:.2f} m2")
with tabs[4]:
    ek = [{"w":x['Szerokość [mm]'], "h":x['Wysokość [mm]'], "nazwa":x['ID']} for x in lista_elementow if "KORPUS" in x['Materiał']]
    if ek: st.pyplot(rysuj_nesting([{"w":x['Szerokość [mm]'], "h":x['Wysokość [mm]'], "nazwa":x['ID']} for x in lista_elementow if "KORPUS" in x['Materiał']]))
with tabs[5]: st.pyplot(rysuj_podglad_mebla(W_MEBLA, H_MEBLA, GR_PLYTY, ILOSC_PRZEGROD, st.session_state['moduly_sekcji'], SZER_JEDNEJ_WNEKI, TYP_KONSTRUKCJI))
