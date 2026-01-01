import streamlit as st
import pandas as pd
import io

# Konfiguracja strony
st.set_page_config(page_title="STOLARZPRO - V20.3", page_icon="🪚", layout="wide")

# Próba importu grafiki z bezpiecznym backendem
try:
    import matplotlib
    matplotlib.use('Agg') # Kluczowe dla stabilności na serwerze
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
    
    # Tło (zorder=1 - najniższa warstwa)
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla, zorder=1)
    ax.add_patch(rect)
    
    # Otwory (zorder=10 - wyższa warstwa, zawsze na wierzchu)
    if otwory:
        for otw in otwory:
            x, y = otw[0], otw[1]
            kolor = otw[2] if len(otw) > 2 else 'red'
            
            if kolor == 'blue': 
                ax.add_patch(patches.Circle((x, y), radius=6, edgecolor='blue', facecolor='none', linestyle='--', zorder=10))
                ax.add_patch(patches.Circle((x, y), radius=1, color='blue', zorder=10))
            elif kolor == 'red': 
                ax.add_patch(patches.Circle((x, y), radius=3, color='red', zorder=10)) 
            elif kolor == 'green': 
                if "Front" in nazwa:
                    ax.add_patch(patches.Circle((x, y), radius=17.5, edgecolor='green', facecolor='#ccffcc', linewidth=1.5, zorder=10))
                else:
                    ax.add_patch(patches.Circle((x, y), radius=4, edgecolor='green', facecolor='white', zorder=10))
            
            if len(otwory) < 60:
                ax.text(x+8, y+2, f"({x:.0f},{y:.0f})", fontsize=7, alpha=0.7, zorder=20)

    # Orientacja
    if orientacja_frontu == 'L':
        ax.add_patch(patches.Rectangle((-3, 0), 3, wys, color='#d62828', zorder=5))
        ax.text(5, wys/2, "FRONT", rotation=90, color='#d62828', fontsize=9, weight='bold', zorder=20)
    elif orientacja_frontu == 'D': 
        ax.add_patch(patches.Rectangle((0, -3), szer, 3, color='#d62828', zorder=5))
        ax.text(szer/2, 5, "FRONT", ha='center', color='#d62828', fontsize=9, weight='bold', zorder=20)
    elif orientacja_frontu == 'P':
        ax.add_patch(patches.Rectangle((szer, 0), 3, wys, color='#d62828', zorder=5))
        ax.text(szer-15, wys/2, "FRONT", rotation=90, color='#d62828', fontsize=9, weight='bold', zorder=20)

    ax.text(szer/2, -15, f"{szer} mm", ha='center', weight='bold')
    ax.text(-15, wys/2, f"{wys} mm", va='center', rotation=90, weight='bold')
    
    # === FIX: SZTYWNE GRANICE (Naprawia błąd Image size too large) ===
    ax.set_xlim(-50, szer + 50)
    ax.set_ylim(-50, wys + 50)
    # =================================================================

    ax.set_aspect('equal')
    ax.axis('off')
    return fig

def generuj_szablon_a4(element, rog):
    if not GRAFIKA_DOSTEPNA: return None
    plt.close('all')
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    
    szer, wys = element['Szerokość [mm]'], element['Wysokość [mm]']
    otwory = element['wiercenia']
    
    # Tło szablonu (zorder=1)
    ax.add_patch(patches.Rectangle((0, 0), szer, wys, linewidth=3, edgecolor='black', facecolor='#eee', zorder=1))
    
    for otw in otwory:
        x, y = otw[0], otw[1]
        kolor = otw[2] if len(otw) > 2 else 'black'
        # Krzyżyki nawiertów (zorder=10)
        ax.plot([x-5, x+5], [y, y], color=kolor, linewidth=1, zorder=10)
        ax.plot([x, x], [y-5, y+5], color=kolor, linewidth=1, zorder=10)
        ax.text(x+2, y+2, f"({x:.1f}, {y:.1f})", fontsize=8, color=kolor, zorder=20)

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

    # Obrys mebla (zorder=5)
    ax.add_patch(patches.Rectangle((0, 0), w, h, linewidth=3, edgecolor='black', facecolor='none', zorder=5))
    ax.add_patch(patches.Rectangle((0, 0), w, gr, facecolor='#d7ba9d', edgecolor='black', zorder=5))
    ax.add_patch(patches.Rectangle((0, h-gr), w, gr, facecolor='#d7ba9d', edgecolor='black', zorder=5))
    ax.add_patch(patches.Rectangle((0, gr), gr, h-2*gr, facecolor='#d7ba9d', edgecolor='black', zorder=5))
    ax.add_patch(patches.Rectangle((w-gr, gr), gr, h-2*gr, facecolor='#d7ba9d', edgecolor='black', zorder=5))
    
    curr_x = gr
    h_wew = h - 2*gr
    
    for i in range(n_przeg + 1):
        if i < n_przeg:
            # Przegroda pionowa
            ax.add_patch(patches.Rectangle((curr_x + szer_wneki, gr), gr, h_wew, facecolor='gray', alpha=0.3, zorder=1))
        
        moduly = moduly_sekcji.get(i, [])
        if moduly:
            fixed_h_sum = sum(m['wys_mm'] for m in moduly if m['wys_mode'] == 'fixed')
            auto_count = sum(1 for m in moduly if m['wys_mode'] == 'auto')
            auto_h = (h_wew - fixed_h_sum) / auto_count if auto_count > 0 else 0
            
            curr_y = gr 
            
            for mod in moduly:
                h_mod = mod['wys_mm'] if mod['wys_mode'] == 'fixed' else auto_h
                
                # Obrys modułu
                ax.add_patch(patches.Rectangle((curr_x, curr_y), szer_wneki, h_mod, facecolor='none', edgecolor='black', linestyle=':', alpha=0.3, zorder=1))
                
                det = mod['detale']
                if mod['typ'] == "Szuflady":
                    n = det.get('ilosc', 2)
                    if n > 0:
                        h_f = (h_mod - ((n-1)*3)) / n
                        for k in range(n):
                            yf = curr_y + k*(h_f+3)
                            # Fronty szuflad (zorder=10)
                            ax.add_patch(patches.Rectangle((curr_x+2, yf), szer_wneki-4, h_f, facecolor='#f4e1d2', edgecolor='#669bbc', zorder=10))
                            ax.text(curr_x + szer_wneki/2, yf + h_f/2, "SZUFLADA", ha='center', va='center', fontsize=7, color='#004488', zorder=11, fontweight='bold')

                elif mod['typ'] == "Półki":
                    n = det.get('ilosc', 1)
                    if n > 0:
                        gap = h_mod / (n + 1)
                        for k in range(n):
                            yp = curr_y + (k+1)*gap
                            # Półka (zorder=10)
                            ax.add_patch(patches.Rectangle((curr_x, yp), szer_wneki, gr, color='#bc6c25', zorder=10))

                elif mod['typ'] == "Drążek":
                    ax.add_patch(patches.Rectangle((curr_x+5, curr_y + h_mod - 60), szer_wneki-10, 15, facecolor='silver', edgecolor='black', zorder=10))
                    ax.text(curr_x + szer_wneki/2, curr_y + h_mod/2, "DRĄŻEK", ha='center', alpha=0.5, rotation=45, zorder=10)

                if det.get('drzwi'):
                     ax.add_patch(patches.Rectangle((curr_x+1, curr_y+1), szer_wneki-2, h_mod-2, 
                                                  facecolor='green', alpha=0.1, edgecolor='green', linestyle='--', zorder=15))
                     ax.text(curr_x + szer_wneki/2, curr_y + h_mod/2, "DRZWI", ha='center', color='green', fontweight='bold', alpha=0.8, zorder=16)

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
    D_MEBLA, GR_PLYTY = c1.number_input
