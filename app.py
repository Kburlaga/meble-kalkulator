import streamlit as st
import pandas as pd
import io
import copy
import json
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
        'kod_pro': "SZAFKA_CARGO", # Zmieniona nazwa domyślna dla testu
        'h_mebla': 720, 'w_mebla': 200, 'd_mebla': 500, 'gr_plyty': 18, # Domyślne wymiary Cargo
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

# ==========================================
# 3. RYSOWANIE (STRONA A)
# ==========================================
def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], orientacja_frontu="L", kolor_tla='#e6ccb3', figsize=(10, 7)):
    plt.close('all')
    fig, ax = plt.subplots(figsize=figsize)
    
    if "HDF" in nazwa: kolor_tla = '#d9d9d9'
    
    ax.set_title(f"{id_elementu}\n[{nazwa}]", fontsize=16, weight='bold', pad=20, color='#333333')

    # Rysunek płyty
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla, zorder=1)
    ax.add_patch(rect)
    
    if otwory:
        unique_x = sorted(list(set([o[0] for o in otwory])))
        unique_y = sorted(list(set([o[1] for o in otwory])))
        
        # Linie Traserskie
        for y_line in unique_y:
            ax.plot([-500, szer+500], [y_line, y_line], color='#666666', linestyle='--', linewidth=0.5, alpha=0.5, zorder=2)
            ax.text(5, y_line+2, f"Y:{y_line:.0f}", ha='left', va='bottom', fontsize=6, color='#444')
            ax.text(szer-5, y_line+2, f"{y_line:.0f}", ha='right', va='bottom', fontsize=6, color='#444')

        for x_line in unique_x:
            ax.plot([x_line, x_line], [-500, wys+500], color='#666666', linestyle='--', linewidth=0.5, alpha=0.5, zorder=2)
            ax.text(x_line+2, 5, f"{x_line:.0f}", ha='left', va='bottom', fontsize=6, color='#444', rotation=90)

        # Otwory (tylko numery)
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

    # 2. ORIENTACJA FRONTU (POPRAWIONA DLA CARGO)
    is_poziomy = "WIENIEC" in nazwa.upper() or "PÓŁKA" in nazwa.upper()
    
    if "Plecy" not in nazwa:
        if is_poziomy:
            # Dla wieńców/półek front jest ZAWSZE wzdłuż wymiaru 'szer' (który odpowiada szerokości szafki)
            # Niezależnie czy to krótki czy długi bok.
            ax.add_patch(patches.Rectangle((0, -5), szer, 5, color='#d62828', zorder=5))
            ax.text(szer/2, 20, "FRONT", ha='center', va='bottom', color='#d62828', weight='bold', zorder=15, fontsize=12)
        else:
            # Boki / Fronty (Pionowe)
            if orientacja_frontu == 'L':
                ax.add_patch(patches.Rectangle((-5, 0), 5, wys, color='#d62828', zorder=5))
                ax.text(20, wys/2, "FRONT", rotation=90, color='#d62828', weight='bold', zorder=15, ha='center', va='center', fontsize=12)
            elif orientacja_frontu == 'P':
                ax.add_patch(patches.Rectangle((szer, 0), 5, wys, color='#d62828', zorder=5))
                ax.text(szer-20, wys/2, "FRONT", rotation=90, color='#d62828', weight='bold', zorder=15, ha='center', va='center', fontsize=12)
            elif orientacja_frontu == 'D': 
                ax.add_patch(patches.Rectangle((0, -5), szer, 5, color='#d62828', zorder=5))
                ax.text(szer/2, 20, "FRONT", ha='center', va='bottom', color='#d62828', weight='bold', zorder=15, fontsize=12)

    # Wymiary
    ax.text(szer/2, wys + 15, f"{szer:.0f} mm", ha='center', weight='bold', fontsize=12)
    ax.text(szer + 15, wys/2, f"{wys:.0f} mm", va='center', rotation=90, weight='bold', fontsize=12)
    
    # 3. ZOOM
    margin_x = max(szer * 0.05, 40)
    margin_y = max(wys * 0.05, 40)
    ax.set_xlim(-margin_x, szer + margin_x)
    ax.set_ylim(-margin_y, wys + margin_y)
    plt.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.02)
    ax.set_aspect('equal')
    ax.axis('off')
    return fig

# ==========================================
# 3b. TABELA (STRONA B)
# ==========================================
def rysuj_tabele_strona(id_elementu, nazwa, otwory):
    plt.close('all')
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis('off')
    
    ax.text(0.5, 0.95, f"TABELA WIERCEŃ: {id_elementu}", ha='center', fontsize=14, weight='bold')
    ax.text(0.5, 0.92, f"Element: {nazwa}", ha='center', fontsize=12, color='#555')
    
    table_data = []
    otwory_sorted = sorted(otwory, key=lambda k: (k[1], k[0]))
    
    for i, otw in enumerate(otwory_sorted):
        x, y = otw[0], otw[1]
        kolor_kod = otw[2] if len(otw) > 2 else 'red'
        nr = i + 1
        
        typ = "Inny"
        if kolor_kod == 'blue': typ = "Konfirmat"
        elif kolor_kod == 'red': typ = "Prowadnica"
        elif kolor_kod == 'green': typ = "Podpórka/Zawias"
        
        table_data.append([str(nr), f"{x:.1f}", f"{y:.1f}", typ])
    
    if table_data:
        col_labels = ["Nr", "X [mm]", "Y [mm]", "Typ Otworu"]
        col_widths = [0.1, 0.2, 0.2, 0.5]
        
        # Tabela na całą szerokość
        table = ax.table(cellText=table_data, colLabels=col_labels, loc='top', bbox=[0.05, 0.05, 0.9, 0.85], cellLoc='center', colWidths=col_widths)
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        
        for (row, col), cell in table.get_celld().items():
            cell.set_height(0.04)
            if row == 0:
                cell.set_text_props(weight='bold', color='white')
                cell.set_facecolor('#333333')
            elif row % 2 == 0:
                cell.set_facecolor('#f9f9f9')
    else:
        ax.text(0.5, 0.5, "Brak otworów.", ha='center')
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
# 4. INTERFEJS GŁÓWNY
# ==========================================
with st.sidebar:
    st.title("🪚 STOLARZPRO V20.3")
    st.markdown("### 💾 Projekt"); c1, c2 = st.columns(2)
    c1.download_button("Pobierz .JSON", export_project_to_json(), f"projekt.json", "application/json")
    uploaded = c2.file_uploader("Wczytaj", type=['json'], label_visibility="collapsed")
    if uploaded: load_project_from_json(uploaded)
    if st.button("🗑️ NOWY PROJEKT", type="primary"): st.session_state.clear(); st.rerun()
    st.markdown("---"); st.text_input("Nazwa", key="kod_pro")
    st.selectbox("Typ", ["Wieńce Nakładane", "Wieńce Wpuszczane"], key="typ_konstrukcji")
    st.selectbox("Plecy", ["HDF 3mm (Nakładane)", "Płyta 18mm (Wpuszczana)", "Płyta 16mm (Wpuszczana)", "Brak"], key="typ_plecow")
    c1, c2 = st.columns(2); c1.number_input("Wysokość", key="h_mebla"); c2.number_input("Szerokość", key="w_mebla")
    c1.number_input("Głębokość", key="d_mebla"); c2.number_input("Grubość", key="gr_plyty"); st.number_input("Przegrody", key="il_przegrod")
    
    st.markdown("### 2. Moduły")
    tabs = st.tabs([f"Sekcja {i+1}" for i in range(st.session_state['il_przegrod']+1)])
    for i, tab in enumerate(tabs):
        with tab:
            ms = st.session_state['moduly_sekcji'].get(i, [])
            if ms: 
                for idx, m in enumerate(ms): 
                    c1, c2 = st.columns([1, 4]); 
                    if c1.button("X", key=f"d{i}{idx}"): usun_modul(i, idx); st.rerun()
                    c2.write(f"{m['typ']}")
            with st.form(f"f{i}"):
                t = st.selectbox("Typ", ["Półki", "Szuflady", "Drążek", "Pusta"])
                if st.form_submit_button("Dodaj"): dodaj_modul_akcja(i, t, "AUTO", 0, 1, False, False); st.rerun()
    
    st.markdown("---"); st.selectbox("Prowadnice", list(BAZA_SYSTEMOW.keys())); st.selectbox("Zawiasy", list(BAZA_ZAWIASOW.keys()))

# ==========================================
# 5. SILNIK OBLICZENIOWY
# ==========================================
H_MEBLA = st.session_state['h_mebla']; W_MEBLA = st.session_state['w_mebla']; D_MEBLA = st.session_state['d_mebla']; GR_PLYTY = st.session_state['gr_plyty']
TYP_KONSTRUKCJI = st.session_state.get('typ_konstrukcji', "Wieńce Nakładane"); TYP_PLECOW = st.session_state.get('typ_plecow', "HDF 3mm (Nakładane)")
ilosc_przegrod = st.session_state['il_przegrod']; n_sekcji_val = ilosc_przegrod + 1
KOD_PROJEKTU = st.session_state['kod_pro'].upper().replace(" ", "_")

if "Wpuszczane" in TYP_KONSTRUKCJI: wys_boku = H_MEBLA; szer_wienca = W_MEBLA - (2*GR_PLYTY); szer_wew_total = szer_wienca
else: wys_boku = H_MEBLA - (2*GR_PLYTY); szer_wienca = W_MEBLA; szer_wew_total = W_MEBLA - (2*GR_PLYTY)
szer_jednej_wneki = szer_wew_total; wys_wewnetrzna = H_MEBLA - (2*GR_PLYTY)
gr_plecow = 18 if "18mm" in TYP_PLECOW else (16 if "16mm" in TYP_PLECOW else 0); glebokosc_wewnetrzna = D_MEBLA - gr_plecow

lista_elementow = []; counts_dict = {}
def get_unique_id(nazwa_baza):
    k = nazwa_baza.upper().replace(" ", "_"); c = counts_dict.get(k, 0) + 1; counts_dict[k] = c
    return f"{KOD_PROJEKTU}_{k}_{c}"

# FIX: POPRAWIONA LOGIKA OKLEJANIA DLA CARGO
def opisz_oklejanie(nazwa, szer_el, wys_el):
    n = nazwa.upper()
    if "FRONT" in n or "DRZWI" in n: return "4 krawędzie (2mm)"
    elif "WIENIEC" in n or "PÓŁKA" in n or "PRZEGRODA" in n:
        # Porównujemy wymiary formatki, żeby określić czy front jest długi czy krótki
        if szer_el >= wys_el: return "1 Długa (Przód)"
        else: return "1 Krótka (Przód)"
    elif "BOK" in n: return "1 Długa + 2 Krótkie (Przód+Góra+Dół)"
    return "Brak" if "DNO" in n or "TYŁ" in n or "PLECY" in n else "Wg uznania"

def dodaj_el(nazwa, szer, wys, gr, mat, wiercenia, ori):
    ident = get_unique_id(nazwa)
    # Przekazujemy wymiary do funkcji opisującej
    oklejanie = opisz_oklejanie(nazwa, szer, wys)
    lista_elementow.append({"ID": ident, "Nazwa": nazwa, "Szerokość [mm]": int(szer), "Wysokość [mm]": int(wys), "Grubość [mm]": gr, "Materiał": mat, "Oklejanie": oklejanie, "wiercenia": wiercenia, "orientacja": ori})

def gen_wiercenia_boku(moduly, is_mirror=False):
    otwory = []; xf = 37.0 if not is_mirror else D_MEBLA-37.0; xb = 37.0+224.0 if not is_mirror else D_MEBLA-(37.0+224.0)
    if "Wpuszczane" in TYP_KONSTRUKCJI: xw = 50.0 if is_mirror else D_MEBLA-50.0; otwory += [(xf, GR_PLYTY/2, 'blue'), (xw, GR_PLYTY/2, 'blue'), (xf, H_MEBLA-GR_PLYTY/2, 'blue'), (xw, H_MEBLA-GR_PLYTY/2, 'blue')]
    curr_y = GR_PLYTY; ha = (wys_wewnetrzna)/max(1, len(moduly)) 
    for m in moduly:
        if m['typ'] == "Półki": 
            for _ in range(m['detale']['ilosc']): yp = curr_y + ha/2; xb_p = 50.0 if is_mirror else D_MEBLA-50.0; otwory += [(xf, yp, 'green'), (xb_p, yp, 'green')]
        curr_y += ha
    return otwory

gen_konstrukcja()

# ==========================================
# 6. WIDOK
# ==========================================
df = pd.DataFrame(lista_elementow)
tabs = st.tabs(["📋 LISTA", "📐 RYSUNKI", "💰 KOSZTORYS", "🗺️ ROZKRÓJ", "👁️ WIZUALIZACJA"])

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
        st.session_state['pdf_ready'] = buf
    if st.session_state['pdf_ready']: st.download_button("Pobierz", st.session_state['pdf_ready'].getvalue(), "projekt.pdf", "application/pdf")
    
    sel = st.selectbox("Element", [e['ID'] for e in lista_elementow])
    it = next(x for x in lista_elementow if x['ID'] == sel)
    st.pyplot(rysuj_element(it['Szerokość [mm]'], it['Wysokość [mm]'], it['ID'], it['Nazwa'], it['wiercenia'], it['orientacja']))

with tabs[4]: st.pyplot(rysuj_podglad_mebla(W_MEBLA, H_MEBLA, GR_PLYTY, ilosc_przegrod, st.session_state['moduly_sekcji'], szer_jednej_wneki, TYP_KONSTRUKCJI))
