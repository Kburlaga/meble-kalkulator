import streamlit as st
import pandas as pd
import io
import copy
import json
import textwrap  # Do zawijania tekstu w PDF
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages

# Konfiguracja strony
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
# 1. ZARZĄDZANIE STANEM I PROJEKTEM
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

# ==========================================
# 3. INTERFEJS GŁÓWNY
# ==========================================
with st.sidebar:
    st.title("🪚 STOLARZPRO V20.3")
    
    st.markdown("### 💾 Projekt")
    c_dl, c_upl = st.columns(2)
    json_data = export_project_to_json()
    c_dl.download_button("Pobierz .JSON", json_data, file_name=f"projekt_{st.session_state['kod_pro']}.json", mime='application/json')
    uploaded_file = c_upl.file_uploader("Wczytaj", type=['json'], label_visibility="collapsed")
    if uploaded_file: load_project_from_json(uploaded_file)
    
    if st.button("🗑️ NOWY PROJEKT", type="primary"): 
        st.session_state.clear()
        st.rerun()
    
    st.markdown("---")
    
    st.markdown("### 1. Gabaryty")
    st.text_input("Nazwa", key="kod_pro")
    st.selectbox("Typ konstrukcji", ["Wieńce Nakładane", "Wieńce Wpuszczane"], key="typ_konstrukcji")
    st.selectbox("Rodzaj Pleców", ["HDF 3mm (Nakładane)", "Płyta 18mm (Wpuszczana)", "Płyta 16mm (Wpuszczana)", "Brak"], key="typ_plecow")
    
    c1, c2 = st.columns(2)
    c1.number_input("Wysokość", key="h_mebla")
    c2.number_input("Szerokość", key="w_mebla")
    c1.number_input("Głębokość", key="d_mebla")
    c2.number_input("Grubość płyty", key="gr_plyty")
    st.number_input("Ilość przegród pionowych", min_value=0, key="il_przegrod")

    with st.expander("💰 Ustawienia Cen (PLN/m2)"):
        st.number_input("Płyta Korpus", value=50.0, key='cena_korpus')
        st.number_input("Płyta Front", value=70.0, key='cena_front')
        st.number_input("HDF", value=15.0, key='cena_hdf')
        st.number_input("Oklejanie (zł/mb)", value=2.0, key='cena_okl')

    st.markdown("### 2. Konfigurator Modułowy")
    aktualna_ilosc_sekcji = st.session_state['il_przegrod'] + 1
    tabs_sekcji = st.tabs([f"Sekcja {i+1}" for i in range(aktualna_ilosc_sekcji)])
    
    for i, tab in enumerate(tabs_sekcji):
        with tab:
            m_sekcji = st.session_state['moduly_sekcji'].get(i, [])
            if m_sekcji:
                st.write("🔽 Dół szafy")
                for idx, mod in enumerate(m_sekcji):
                    typ_opis = mod['typ'] + (" (STAŁE)" if mod['detale'].get('fixed') else "")
                    opis = f"**{idx+1}. {typ_opis}**" + (f" ({mod['wys_mm']}mm)" if mod['wys_mode'] == 'fixed' else " (AUTO)")
                    
                    c_del, c_info = st.columns([1, 4])
                    if c_del.button("❌", key=f"del_{i}_{idx}"):
                        usun_modul(i, idx)
                        st.rerun()
                    c_info.markdown(opis)
                st.write("🔼 Góra szafy")
                st.markdown("---")
            
            with st.form(key=f"form_add_{i}"):
                c_f1, c_f2 = st.columns(2)
                f_typ = c_f1.selectbox("Typ", ["Półki", "Szuflady", "Drążek", "Pusta"])
                f_tryb = c_f2.selectbox("Wysokość", ["Fixed (mm)", "AUTO (Reszta)"])
                f_wys_mm = st.number_input("Wysokość (Fixed)", 100, 2000, 600)
                f_ilosc = st.number_input("Ilość", 1, 10, 1)
                c_ch1, c_ch2 = st.columns(2)
                f_drzwi = c_ch1.checkbox("Drzwi?")
                f_stale = False
                if f_typ == "Półki":
                    f_stale = c_ch2.checkbox("Półki stałe (Konfirmaty)?")
                
                if st.form_submit_button("Dodaj Moduł"):
                    dodaj_modul_akcja(i, f_typ, f_tryb, f_wys_mm, f_ilosc, f_drzwi, f_stale)
                    st.rerun()

    st.markdown("---")
    st.markdown("### 3. Okucia")
    c_s1, c_s2 = st.columns(2)
    sys_k = c_s1.selectbox("Prowadnice", list(BAZA_SYSTEMOW.keys()))
    zaw_k = c_s2.selectbox("Zawiasy", list(BAZA_ZAWIASOW.keys()))

# ==========================================
# 4. GLOBALNE ZMIENNE (PRZED FUNKCJAMI)
# ==========================================
params_szuflad = BAZA_SYSTEMOW[sys_k]
params_zawias = BAZA_ZAWIASOW[zaw_k]
H_MEBLA = st.session_state['h_mebla']
W_MEBLA = st.session_state['w_mebla']
D_MEBLA = st.session_state['d_mebla']
GR_PLYTY = st.session_state['gr_plyty']
TYP_KONSTRUKCJI = st.session_state.get('typ_konstrukcji', "Wieńce Nakładane")
TYP_PLECOW = st.session_state.get('typ_plecow', "HDF 3mm (Nakładane)")
ilosc_przegrod = st.session_state['il_przegrod']
n_sekcji_val = ilosc_przegrod + 1
KOD_PROJEKTU = st.session_state['kod_pro'].upper().replace(" ", "_")

if "Wpuszczane" in TYP_KONSTRUKCJI:
    wys_boku = H_MEBLA
    szer_wienca = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)
    if ilosc_przegrod > 0: szer_wienca = W_MEBLA - (2 * GR_PLYTY) 
    szer_wew_total = szer_wienca - (ilosc_przegrod * GR_PLYTY)
else:
    wys_boku = H_MEBLA - (2 * GR_PLYTY)
    szer_wienca = W_MEBLA
    szer_wew_total = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)

szer_jednej_wneki = szer_wew_total / n_sekcji_val if n_sekcji_val > 0 else 0
wys_wewnetrzna = H_MEBLA - (2 * GR_PLYTY)

gr_plecow = 0
if "18mm" in TYP_PLECOW: gr_plecow = 18
elif "16mm" in TYP_PLECOW: gr_plecow = 16

glebokosc_wewnetrzna = D_MEBLA - gr_plecow

lista_elementow = []
counts_dict = {}

# ==========================================
# 5. FUNKCJE GENERUJĄCE
# ==========================================

def get_unique_id(nazwa_baza):
    key = nazwa_baza.upper().replace(" ", "_")
    if "BOK" in key: key = "BOK"
    elif "WIENIEC" in key: key = "WIENIEC"
    elif "PRZEGRODA" in key: key = "PRZEGRODA"
    elif "FRONT" in key: key = "FRONT"
    elif "PÓŁKA" in key: key = "POLKA"
    elif "PLECY" in key: key = "PLECY"
    elif "DRZWI" in key: key = "DRZWI"
    elif "DNO" in key: key = "DNO"
    elif "TYŁ" in key: key = "TYL"
    current = counts_dict.get(key, 0) + 1
    counts_dict[key] = current
    return f"{KOD_PROJEKTU}_{key}_{current}"

def opisz_oklejanie(nazwa, szer_el, wys_el):
    n = nazwa.upper()
    if "FRONT" in n or "DRZWI" in n: return "4 krawędzie (2mm)"
    elif "WIENIEC" in n or "PÓŁKA" in n or "PRZEGRODA" in n:
        if szer_el >= wys_el: return "1 Długa (Przód)"
        else: return "1 Krótka (Przód)"
    elif "BOK" in n: return "1 Długa + 2 Krótkie (Przód+Góra+Dół)"
    return "Brak" if "DNO" in n or "TYŁ" in n or "PLECY" in n else "Wg uznania"

def dodaj_el(nazwa, szer, wys, gr, mat, wiercenia, ori):
    ident = get_unique_id(nazwa)
    oklejanie = opisz_oklejanie(nazwa, szer, wys)
    lista_elementow.append({
        "ID": ident, "Nazwa": nazwa, 
        "Szerokość [mm]": int(round(szer, 0)), "Wysokość [mm]": int(round(wys, 0)),
        "Grubość [mm]": gr, "Materiał": mat, "Oklejanie": oklejanie,
        "wiercenia": wiercenia, "orientacja": ori
    })

def gen_wiercenia_boku(moduly, is_mirror=False):
    otwory = []
    if is_mirror:
        x_f = D_MEBLA - 37.0
        x_b = D_MEBLA - (37.0 + 224.0)
        x_plecy_ref = gr_plecow / 2
    else:
        x_f = 37.0
        x_b = 37.0 + 224.0
        x_plecy_ref = D_MEBLA - (gr_plecow / 2)

    if "Wpuszczane" in TYP_KONSTRUKCJI:
        x_wt = 50.0 if is_mirror else D_MEBLA - 50.0
        otwory.append((x_f, GR_PLYTY/2, 'blue'))
        otwory.append((x_wt, GR_PLYTY/2, 'blue'))
        otwory.append((x_f, H_MEBLA - GR_PLYTY/2, 'blue'))
        otwory.append((x_wt, H_MEBLA - GR_PLYTY/2, 'blue'))

    if gr_plecow > 0:
        ilosc_otw_plecy = int(H_MEBLA / 400) + 1
        step_plecy = (H_MEBLA - 100) / ilosc_otw_plecy
        for k in range(ilosc_otw_plecy + 1):
            y_plecy = 50 + k * step_plecy
            if y_plecy > GR_PLYTY and y_plecy < (H_MEBLA - GR_PLYTY):
                otwory.append((x_plecy_ref, y_plecy, 'blue'))
    
    curr_y = GR_PLYTY
    fixed_sum = sum(m['wys_mm'] for m in moduly if m['wys_mode'] == 'fixed')
    auto_cnt = sum(1 for m in moduly if m['wys_mode'] == 'auto')
    h_auto = (wys_wewnetrzna - fixed_sum) / max(1, auto_cnt)
    
    for idx, mod in enumerate(moduly):
        h_mod = mod['wys_mm'] if mod['wys_mode'] == 'fixed' else h_auto
        if idx > 0:
            y_wieniec = curr_y + GR_PLYTY/2
            x_wt = 50.0 if is_mirror else D_MEBLA - 50.0
            otwory.append((x_f, y_wieniec, 'blue'))
            otwory.append((x_wt, y_wieniec, 'blue'))
            curr_y += GR_PLYTY
            
        det = mod['detale']
        if det.get('drzwi'):
            otwory.append((x_f, curr_y + 100, 'green'))
            otwory.append((x_f, curr_y + h_mod - 100, 'green'))

        if mod['typ'] == "Szuflady":
            n = det.get('ilosc', 2)
            if n > 0:
                h_front = (h_mod - ((n-1)*3)) / n
                for k in range(n):
                    ys = curr_y + k*(h_front+3) + 3 + params_szuflad["offset_prowadnica"]
                    otwory.append((x_f, ys, 'red'))
                    otwory.append((x_b, ys, 'red'))
        
        elif mod['typ'] == "Półki":
            n = det.get('ilosc', 1)
            if n > 0:
                gap = h_mod / (n + 1)
                for k in range(n):
                    yp = curr_y + (k+1)*gap
                    x_back_hole = (50.0 if is_mirror else D_MEBLA - 50.0) if det.get('fixed') else ((50.0 if is_mirror else (D_MEBLA - gr_plecow) - 50.0))
                    color = 'blue' if det.get('fixed') else 'green'
                    otwory.append((x_f, yp, color))
                    otwory.append((x_back_hole, yp, color))
        curr_y += h_mod
    return otwory

def gen_konstrukcja():
    global counts_dict
    counts_dict = {}
    if "HDF" in TYP_PLECOW: dodaj_el("Plecy (HDF)", W_MEBLA-4, H_MEBLA-4, 3, "3mm HDF", [], "X")
    elif gr_plecow > 0:
        szer_plecow = W_MEBLA if "Nakładane" in TYP_KONSTRUKCJI else szer_wew_total + (ilosc_przegrod*GR_PLYTY)
        dodaj_el("Plecy (Płyta)", szer_plecow, wys_wewnetrzna, gr_plecow, f"{gr_plecow}mm KORPUS", [], "X")
    
    otw_L = gen_wiercenia_boku(st.session_state['moduly_sekcji'].get(0, []), False)
    dodaj_el("Bok Lewy", D_MEBLA, wys_boku, GR_PLYTY, "18mm KORPUS", otw_L, "L")
    otw_P = gen_wiercenia_boku(st.session_state['moduly_sekcji'].get(n_sekcji_val-1, []), True)
    dodaj_el("Bok Prawy", D_MEBLA, wys_boku, GR_PLYTY, "18mm KORPUS", otw_P, "P")
    dodaj_el("Wieniec Górny", szer_wienca, glebokosc_wewnetrzna, GR_PLYTY, "18mm KORPUS", [], "L")
    dodaj_el("Wieniec Dolny", szer_wienca, glebokosc_wewnetrzna, GR_PLYTY, "18mm KORPUS", [], "L")
    
    for i in range(ilosc_przegrod):
        mod_L = st.session_state['moduly_sekcji'].get(i, [])
        mod_R = st.session_state['moduly_sekcji'].get(i+1, [])
        otw = gen_wiercenia_boku(mod_L, True) + gen_wiercenia_boku(mod_R, False)
        dodaj_el(f"Przegroda {i+1}", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "18mm KORPUS", otw, "L")

    for i in range(n_sekcji_val):
        moduly = st.session_state['moduly_sekcji'].get(i, [])
        fixed_sum = sum(m['wys_mm'] for m in moduly if m['wys_mode'] == 'fixed')
        auto_cnt = sum(1 for m in moduly if m['wys_mode'] == 'auto')
        h_auto = (wys_wewnetrzna - fixed_sum) / max(1, auto_cnt)
        
        for idx, mod in enumerate(moduly):
            if idx > 0: dodaj_el(f"Wieniec Środkowy (Sekcja {i+1})", szer_jednej_wneki, glebokosc_wewnetrzna, GR_PLYTY, "18mm KORPUS", [], "L")
            h_mod = mod['wys_mm'] if mod['wys_mode'] == 'fixed' else h_auto
            det = mod['detale']
            if det.get('drzwi'): dodaj_el(f"Drzwi Sekcja {i+1}", szer_jednej_wneki-4, h_mod-4, 18, "18mm FRONT", [], "L")
            is_inner = det.get('drzwi', False)
            if mod['typ'] == "Szuflady":
                n = det.get('ilosc', 2)
                h_f = (h_mod - ((n-1)*3)) / n
                mat_f = "18mm KORPUS" if is_inner else "18mm FRONT"
                for _ in range(n):
                    dodaj_el("Front Szuflady", szer_jednej_wneki-4, h_f, 18, mat_f, [], "D")
                    dodaj_el("Dno Szuflady", szer_jednej_wneki-71, 476, 3, "3mm HDF", [], "D")
                    dodaj_el("Tył Szuflady", szer_jednej_wneki-83, 150, 16, "16mm BIAŁA", [], "D")
            elif mod['typ'] == "Półki":
                n = det.get('ilosc', 1)
                is_fixed = det.get('fixed', False)
                w_p = szer_jednej_wneki - (0 if is_fixed else 2)
                if is_inner and not is_fixed: w_p -= 10
                d_p = glebokosc_wewnetrzna if is_fixed else (glebokosc_wewnetrzna - 20)
                for _ in range(n):
                    typ_nazwa = "Półka Stała" if is_fixed else "Półka Ruchoma"
                    dodaj_el(typ_nazwa, w_p, d_p, 18, "18mm KORPUS", [], "L")

gen_konstrukcja()

# ==========================================
# 6. GENERATOR INSTRUKCJI (NOWOŚĆ)
# ==========================================
def generuj_instrukcje_tekst():
    steps = []
    steps.append(f"INSTRUKCJA MONTAŻU: {KOD_PROJEKTU}")
    steps.append(f"Wymiary: {H_MEBLA}x{W_MEBLA}x{D_MEBLA}mm | Konstrukcja: {TYP_KONSTRUKCJI}")
    steps.append("-" * 40)
    
    # KROK 1: PRZYGOTOWANIE
    steps.append("KROK 1: PRZYGOTOWANIE BOKÓW")
    steps.append("1. Połóż Bok Lewy i Prawy na płaskiej, czystej powierzchni.")
    
    has_szuflady = any("Szuflady" in m['typ'] for s in st.session_state['moduly_sekcji'].values() for m in s)
    has_drzwi = any(m['detale'].get('drzwi') for s in st.session_state['moduly_sekcji'].values() for m in s)
    
    if has_szuflady:
        steps.append("2. Przykręć prowadnice szuflad w zaznaczonych CZERWONYCH punktach.")
        steps.append("   Pamiętaj o cofnięciu prowadnicy 37mm od krawędzi frontowej.")
    if has_drzwi:
        steps.append("3. Przykręć prowadniki zawiasów w zaznaczonych ZIELONYCH punktach.")
        
    steps.append("-" * 40)
    
    # KROK 2: KORPUS
    steps.append("KROK 2: SKŁADANIE KORPUSU")
    if "Wpuszczane" in TYP_KONSTRUKCJI:
        steps.append("1. Postaw jeden z boków na krawędzi tylnej.")
        steps.append("2. Wieniec Dolny i Górny montujemy POMIĘDZY boki.")
        steps.append("3. Skręć boki z wieńcami używając konfirmatów (Otwory NIEBIESKIE).")
    else:
        steps.append("1. Wieniec Dolny i Górny nakładamy NA boki.")
        steps.append("2. Skręć wieńce z bokami od góry i dołu.")
        
    # Wieńce środkowe
    if len(st.session_state['moduly_sekcji']) > 0:
        for s_idx, moduly in st.session_state['moduly_sekcji'].items():
            if len(moduly) > 1:
                steps.append(f"3. W sekcji {s_idx+1}: Zamontuj wieniec/półkę stałą między modułami.")
    
    steps.append("-" * 40)
    
    # KROK 3: PLECY
    steps.append("KROK 3: MONTAŻ PLECÓW")
    if "HDF" in TYP_PLECOW:
        steps.append("1. Wyrównaj przekątne korpusu (muszą być równe!).")
        steps.append("2. Przybij plecy HDF gwoździami lub przykręć wkrętami 3x16.")
    elif "Płyta" in TYP_PLECOW:
        steps.append("1. Wsuń formatkę pleców do wnętrza korpusu.")
        steps.append("2. Przykręć plecy konfirmatami przez boki (otwory na tylnej krawędzi).")
    else:
        steps.append("Mebel bez pleców - pomiń ten krok.")
        
    steps.append("-" * 40)
    
    # KROK 4: WYPOSAŻENIE
    steps.append("KROK 4: WYPOSAŻENIE I FRONTY")
    if has_szuflady:
        steps.append("1. Złóż skrzynki szuflad (Boki + Dno + Tył).")
        steps.append("2. Przykręć fronty do skrzynek szuflad.")
        steps.append("3. Wsuń szuflady w prowadnice.")
    
    steps.append("4. Włóż półki ruchome na podpórki.")
    
    if has_drzwi:
        steps.append("5. Przykręć puszki zawiasów do drzwi.")
        steps.append("6. Zatrzaśnij zawiasy na prowadnikach i wyreguluj szczeliny.")
        
    steps.append("-" * 40)
    steps.append("GOTOWE! Twój mebel jest złożony.")
    
    return "\n".join(steps)

def rysuj_instrukcje_pdf(tekst):
    plt.close('all')
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis('off')
    
    # Zawijanie tekstu
    wrapped_text = "\n".join([textwrap.fill(line, width=80) for line in tekst.split('\n')])
    
    ax.text(0.05, 0.95, wrapped_text, ha='left', va='top', fontsize=10, family='monospace', linespacing=1.5)
    return fig

# ==========================================
# 7. RYSOWANIE (RYSUNEK + TABELA)
# ==========================================
def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], orientacja_frontu="L", kolor_tla='#e6ccb3', figsize=(10, 7)):
    plt.close('all')
    fig, ax = plt.subplots(figsize=figsize)
    if "HDF" in nazwa: kolor_tla = '#d9d9d9'
    ax.set_title(f"{id_elementu}\n[{nazwa}]", fontsize=16, weight='bold', pad=20, color='#333333')
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla, zorder=1)
    ax.add_patch(rect)
    
    if otwory:
        unique_x = sorted(list(set([o[0] for o in otwory])))
        unique_y = sorted(list(set([o[1] for o in otwory])))
        for y_line in unique_y:
            ax.plot([-500, szer+500], [y_line, y_line], color='#666666', linestyle='--', linewidth=0.5, alpha=0.5, zorder=2)
            ax.text(5, y_line+2, f"Y:{y_line:.0f}", ha='left', va='bottom', fontsize=6, color='#444')
            ax.text(szer-5, y_line+2, f"{y_line:.0f}", ha='right', va='bottom', fontsize=6, color='#444')
        for x_line in unique_x:
            ax.plot([x_line, x_line], [-500, wys+500], color='#666666', linestyle='--', linewidth=0.5, alpha=0.5, zorder=2)
            ax.text(x_line+2, 5, f"{x_line:.0f}", ha='left', va='bottom', fontsize=6, color='#444', rotation=90)
        
        otwory_sorted = sorted(otwory, key=lambda k: (k[1], k[0]))
        for i, otw in enumerate(otwory_sorted):
            x, y = otw[0], otw[1]
            kolor_kod = otw[2] if len(otw) > 2 else 'red'
            nr = i + 1
            if kolor_kod == 'blue': 
                ax.add_patch(patches.Circle((x, y), radius=6, edgecolor='blue', facecolor='white', linewidth=2, zorder=20))
                ax.plot([x-3, x+3], [y, y], color='blue', linewidth=1); ax.plot([x, x], [y-3, y+3], color='blue', linewidth=1)
            elif kolor_kod == 'red': 
                ax.add_patch(patches.Circle((x, y), radius=4, color='red', zorder=20))
            elif kolor_kod == 'green': 
                r = 17.5 if "Front" in nazwa else 4
                ax.add_patch(patches.Circle((x, y), radius=r, edgecolor='green', facecolor='white', linewidth=1.5, zorder=20))
            ax.add_patch(patches.Circle((x + 12, y + 12), radius=8, color='black', zorder=40))
            ax.text(x + 12, y + 12, str(nr), color='white', ha='center', va='center', fontsize=8, weight='bold', zorder=41)

    is_poziomy = "WIENIEC" in nazwa.upper() or "PÓŁKA" in nazwa.upper()
    if "Plecy" not in nazwa:
        if is_poziomy:
            ax.add_patch(patches.Rectangle((0, -5), szer, 5, color='#d62828', zorder=5))
            ax.text(szer/2, 20, "FRONT", ha='center', va='bottom', color='#d62828', weight='bold', zorder=15, fontsize=12)
        else:
            if orientacja_frontu == 'L':
                ax.add_patch(patches.Rectangle((-5, 0), 5, wys, color='#d62828', zorder=5))
                ax.text(20, wys/2, "FRONT", rotation=90, color='#d62828', weight='bold', zorder=15, ha='center', va='center', fontsize=12)
            elif orientacja_frontu == 'P':
                ax.add_patch(patches.Rectangle((szer, 0), 5, wys, color='#d62828', zorder=5))
                ax.text(szer-20, wys/2, "FRONT", rotation=90, color='#d62828', weight='bold', zorder=15, ha='center', va='center', fontsize=12)
            elif orientacja_frontu == 'D': 
                ax.add_patch(patches.Rectangle((0, -5), szer, 5, color='#d62828', zorder=5))
                ax.text(szer/2, 20, "FRONT", ha='center', va='bottom', color='#d62828', weight='bold', zorder=15, fontsize=12)

    ax.text(szer/2, wys + 15, f"{szer:.0f} mm", ha='center', weight='bold', fontsize=12)
    ax.text(szer + 15, wys/2, f"{wys:.0f} mm", va='center', rotation=90, weight='bold', fontsize=12)
    
    margin_x = max(szer * 0.05, 40)
    margin_y = max(wys * 0.05, 40)
    ax.set_xlim(-margin_x, szer + margin_x)
    ax.set_ylim(-margin_y, wys + margin_y)
    plt.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.02)
    ax.set_aspect('equal')
    ax.axis('off')
    return fig

def rysuj_tabele_strona(id_elementu, nazwa, otwory):
    plt.close('all')
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis('off')
    ax.text(0.5, 0.95, f"TABELA WIERCEŃ: {id_elementu}", ha='center', fontsize=14, weight='bold')
    ax.text(0.5, 0.92, f"Element: {nazwa}", ha='center', fontsize=12, color='#555')
    
    table_data = []
    otwory_sorted = sorted(otwory, key=lambda k: (k[1], k[0]))
    for i, otw in enumerate(otwory_sorted):
        x, y = otw[0], otw[1]; kolor_kod = otw[2] if len(otw) > 2 else 'red'; nr = i + 1
        typ = "Inny"
        if kolor_kod == 'blue': typ = "Konfirmat"
        elif kolor_kod == 'red': typ = "Prowadnica"
        elif kolor_kod == 'green': typ = "Podpórka/Zawias"
        table_data.append([str(nr), f"{x:.1f}", f"{y:.1f}", typ])
    
    if table_data:
        col_labels = ["Nr", "X [mm]", "Y [mm]", "Typ Otworu"]
        col_widths = [0.1, 0.2, 0.2, 0.5]
        table = ax.table(cellText=table_data, colLabels=col_labels, loc='top', bbox=[0.05, 0.05, 0.9, 0.85], cellLoc='center', colWidths=col_widths)
        table.auto_set_font_size(False); table.set_fontsize(10)
        for (row, col), cell in table.get_celld().items():
            cell.set_height(0.04)
            if row == 0: cell.set_text_props(weight='bold', color='white'); cell.set_facecolor('#333333')
            elif row % 2 == 0: cell.set_facecolor('#f9f9f9')
    else: ax.text(0.5, 0.5, "Brak otworów.", ha='center')
    return fig

# ... (rysuj_nesting, rysuj_arkusz, rysuj_podglad_mebla, generuj_szablon_a4 bez zmian) ...
def rysuj_nesting(elementy, arkusz_w=2800, arkusz_h=2070, rzaz=4):
    elementy_sorted = sorted(elementy, key=lambda x: x['h'], reverse=True)
    sheets = []; current_sheet = {'w': arkusz_w, 'h': arkusz_h, 'placements': []}; shelf_x, shelf_y, shelf_h = 0, 0, 0
    for el in elementy_sorted:
        w, h = el['w'] + rzaz, el['h'] + rzaz
        if shelf_x + w <= arkusz_w:
            current_sheet['placements'].append((shelf_x, shelf_y, el['w'], el['h'], el['nazwa'])); shelf_x += w; shelf_h = max(shelf_h, h)
        else:
            shelf_x = 0; shelf_y += shelf_h; shelf_h = h
            if shelf_y + h <= arkusz_h: current_sheet['placements'].append((shelf_x, shelf_y, el['w'], el['h'], el['nazwa'])); shelf_x += w
            else: sheets.append(current_sheet); current_sheet = {'w': arkusz_w, 'h': arkusz_h, 'placements': []}; shelf_x, shelf_y, shelf_h = 0, 0, h; current_sheet['placements'].append((shelf_x, shelf_y, el['w'], el['h'], el['nazwa'])); shelf_x += w
    sheets.append(current_sheet); return sheets

def rysuj_arkusz(sheet_data, idx):
    fig, ax = plt.subplots(figsize=(10, 7)); ax.set_title(f"Arkusz {idx+1}", fontsize=14)
    ax.add_patch(patches.Rectangle((0, 0), 2800, 2070, facecolor='#eee', edgecolor='black'))
    for p in sheet_data['placements']: x, y, w, h, name = p; ax.add_patch(patches.Rectangle((x, y), w, h, facecolor='#d7ba9d', edgecolor='black', alpha=0.8)); ax.text(x + w/2, y + h/2, f"{name}\n{w:.0f}x{h:.0f}", ha='center', va='center', fontsize=6)
    ax.set_xlim(0, 2800); ax.set_ylim(0, 2070); ax.set_aspect('equal'); ax.axis('off'); return fig

def generuj_szablon_a4(element, rog):
    plt.close('all'); fig, ax = plt.subplots(figsize=(8.27, 11.69)); szer, wys = element['Szerokość [mm]'], element['Wysokość [mm]']; otwory = element['wiercenia']; plt.title(f"SZABLON: {element['ID']} ({rog})", fontsize=14, pad=10)
    ax.add_patch(patches.Rectangle((0, 0), szer, wys, linewidth=3, edgecolor='black', facecolor='#eee', zorder=1))
    for otw in otwory:
        x, y = otw[0], otw[1]; kolor = otw[2] if len(otw) > 2 else 'black'; ax.plot([x-10, x+10], [y, y], color=kolor, linewidth=1.5, zorder=10); ax.plot([x, x], [y-10, y+10], color=kolor, linewidth=1.5, zorder=10); ax.text(x+5, y+5, f"({x:.0f}, {y:.0f})", fontsize=9, color=kolor, zorder=20, weight='bold')
    a4_w, a4_h, m = 210, 297, 10
    if "LD" in rog: ax.set_xlim(-m, a4_w-m); ax.set_ylim(-m, a4_h-m)
    elif "LG" in rog: ax.set_xlim(-m, a4_w-m); ax.set_ylim(wys-a4_h+m, wys+m)
    elif "PD" in rog: ax.set_xlim(szer-a4_w+m, szer+m); ax.set_ylim(-m, a4_h-m)
    elif "PG" in rog: ax.set_xlim(szer-a4_w+m, szer+m); ax.set_ylim(wys-a4_h+m, wys+m)
    ax.set_aspect('equal'); ax.grid(True, linestyle=':', alpha=0.5); return fig

def rysuj_podglad_mebla(w, h, gr, n_przeg, moduly_sekcji, szer_wneki, typ_konstr):
    plt.close('all'); fig, ax = plt.subplots(figsize=(12, 8)); plt.title(f"WIZUALIZACJA: {st.session_state['kod_pro']}\n{typ_konstr}", fontsize=18, weight='bold', pad=20)
    if "Wpuszczane" in typ_konstr: ax.add_patch(patches.Rectangle((0, 0), gr, h, facecolor='#d7ba9d', edgecolor='black')); ax.add_patch(patches.Rectangle((w-gr, 0), gr, h, facecolor='#d7ba9d', edgecolor='black')); ax.add_patch(patches.Rectangle((gr, h-gr), w-2*gr, gr, facecolor='#d7ba9d', edgecolor='black')); ax.add_patch(patches.Rectangle((gr, 0), w-2*gr, gr, facecolor='#d7ba9d', edgecolor='black'))
    else: ax.add_patch(patches.Rectangle((0, 0), w, gr, facecolor='#d7ba9d', edgecolor='black')); ax.add_patch(patches.Rectangle((0, h-gr), w, gr, facecolor='#d7ba9d', edgecolor='black')); ax.add_patch(patches.Rectangle((0, gr), gr, h-2*gr, facecolor='#d7ba9d', edgecolor='black')); ax.add_patch(patches.Rectangle((w-gr, gr), gr, h-2*gr, facecolor='#d7ba9d', edgecolor='black'))
    curr_x = gr; h_wew = h - 2*gr
    for i in range(n_przeg + 1):
        if i < n_przeg: ax.add_patch(patches.Rectangle((curr_x + szer_wneki, gr), gr, h_wew, facecolor='gray', alpha=0.3))
        moduly = moduly_sekcji.get(i, [])
        if moduly:
            fixed_sum = sum(m['wys_mm'] for m in moduly if m['wys_mode'] == 'fixed'); auto_cnt = sum(1 for m in moduly if m['wys_mode'] == 'auto'); h_auto = (h_wew - fixed_sum) / auto_count if auto_count > 0 else 0; curr_y = gr
            for idx, mod in enumerate(moduly):
                if idx > 0: ax.add_patch(patches.Rectangle((curr_x, curr_y), szer_wneki, gr, facecolor='#d7ba9d', edgecolor='black')); curr_y += gr
                h_mod = mod['wys_mm'] if mod['wys_mode'] == 'fixed' else h_auto; det = mod['detale']
                if mod['typ'] == "Półki":
                    n = det.get('ilosc', 1); gap = h_mod / (n + 1)
                    for k in range(n): yp = curr_y + (k+1)*gap; ax.add_patch(patches.Rectangle((curr_x, yp), szer_wneki, gr, color='#8B4513' if not det.get('fixed') else '#d7ba9d'))
                ax.add_patch(patches.Rectangle((curr_x, curr_y), szer_wneki, h_mod, facecolor='none', edgecolor='black', linestyle=':', alpha=0.3)); curr_y += h_mod
        curr_x += szer_wneki + gr
    ax.set_xlim(-100, w + 100); ax.set_ylim(-100, h + 100); ax.set_aspect('equal'); ax.axis('off'); return fig

# ==========================================
# 6. WIDOK
# ==========================================
df = pd.DataFrame(lista_elementow)
instrukcja_tekst = generuj_instrukcje_tekst()

tabs = st.tabs(["📋 LISTA", "📐 RYSUNKI", "🛠️ INSTRUKCJA", "💰 KOSZTORYS", "🗺️ ROZKRÓJ", "👁️ WIZUALIZACJA"])

with tabs[0]: 
    csv = df.drop(columns=['wiercenia', 'orientacja']).to_csv(index=False).encode('utf-8-sig')
    st.download_button("💾 Pobierz CSV", csv, f"{KOD_PROJEKTU}.csv", "text/csv")
    st.dataframe(df)

with tabs[1]:
    if st.button("📄 PDF"):
        buf = io.BytesIO()
        with PdfPages(buf) as pdf:
            for el in lista_elementow:
                plt.clf()
                fs = (11.69, 8.27) if el['Szerokość [mm]'] > el['Wysokość [mm]'] else (8.27, 11.69)
                orient = 'landscape' if el['Szerokość [mm]'] > el['Wysokość [mm]'] else 'portrait'
                fig = rysuj_element(el['Szerokość [mm]'], el['Wysokość [mm]'], el['ID'], el['Nazwa'], el['wiercenia'], el['orientacja'], figsize=fs)
                pdf.savefig(fig, orientation=orient); plt.close(fig)
                if el['wiercenia']:
                    fig_tab = rysuj_tabele_strona(el['ID'], el['Nazwa'], el['wiercenia'])
                    pdf.savefig(fig_tab, orientation='portrait'); plt.close(fig_tab)
            
            # Dodanie instrukcji na końcu PDF
            fig_instr = rysuj_instrukcje_pdf(instrukcja_tekst)
            pdf.savefig(fig_instr, orientation='portrait'); plt.close(fig_instr)

        st.session_state['pdf_ready'] = buf
    if st.session_state['pdf_ready']: st.download_button("Pobierz", st.session_state['pdf_ready'].getvalue(), "projekt.pdf", "application/pdf")
    
    sel = st.selectbox("Element", [e['ID'] for e in lista_elementow])
    it = next(x for x in lista_elementow if x['ID'] == sel)
    st.pyplot(rysuj_element(it['Szerokość [mm]'], it['Wysokość [mm]'], it['ID'], it['Nazwa'], it['wiercenia'], it['orientacja']))

with tabs[2]:
    st.markdown("### Instrukcja Montażu")
    st.text(instrukcja_tekst)

with tabs[3]:
    st.markdown("### Szacunkowy Kosztorys")
    df_koszt = df.copy()
    df_koszt['Powierzchnia [m2]'] = (df_koszt['Szerokość [mm]'] * df_koszt['Wysokość [mm]']) / 1000000 
    
    grupy = df_koszt.groupby('Materiał')['Powierzchnia [m2]'].sum().reset_index()
    
    koszt_calkowity = 0
    st.write("#### Materiały Płytowe")
    for index, row in grupy.iterrows():
        mat = row['Materiał']
        area = row['Powierzchnia [m2]']
        cena_jedn = 0
        if "KORPUS" in mat: cena_jedn = st.session_state['cena_korpus']
        elif "FRONT" in mat: cena_jedn = st.session_state['cena_front']
        elif "HDF" in mat: cena_jedn = st.session_state['cena_hdf']
        
        koszt = area * cena_jedn
        koszt_calkowity += koszt
        st.write(f"- **{mat}**: {area:.2f} m² x {cena_jedn} zł = {koszt:.2f} zł")
        
    st.write("#### Obrzeża (Szacunek)")
    df_koszt['Obwód [m]'] = (2*df_koszt['Szerokość [mm]'] + 2*df_koszt['Wysokość [mm]']) / 1000
    mb_total = df_koszt['Obwód [m]'].sum()
    koszt_okl = mb_total * st.session_state['cena_okl']
    st.write(f"- Oklejanie: {mb_total:.1f} mb x {st.session_state['cena_okl']} zł = {koszt_okl:.2f} zł")
    koszt_calkowity += koszt_okl
    
    st.metric("RAZEM (Netto materiał)", f"{koszt_calkowity:.2f} PLN")

with tabs[4]:
    st.markdown("### Wizualizacja Rozkroju (Płyta 2800x2070)")
    el_korpus = [{"w": x['Szerokość [mm]'], "h": x['Wysokość [mm]'], "nazwa": x['ID']} for x in lista_elementow if "KORPUS" in x['Materiał']]
    
    if el_korpus:
        arkusze = rysuj_nesting(el_korpus)
        st.info(f"Potrzebujesz {len(arkusze)} płyt(y) na korpus.")
        for i, ark in enumerate(arkusze):
            st.pyplot(rysuj_arkusz(ark, i))
    else:
        st.warning("Brak elementów korpusu do rozkroju.")

with tabs[5]: st.pyplot(rysuj_podglad_mebla(W_MEBLA, H_MEBLA, GR_PLYTY, ilosc_przegrod, st.session_state['moduly_sekcji'], szer_jednej_wneki, TYP_KONSTRUKCJI))
