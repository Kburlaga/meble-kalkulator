import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages # <-- To jest nasz magik od PDF
import pandas as pd
import io

st.set_page_config(page_title="STOLARZPRO - Master V9", page_icon="🪚", layout="wide")

# ==========================================
# 1. FUNKCJA RYSUJĄCA (POPRAWIONE ETYKIETY)
# ==========================================
def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], kolor_tla='#e6ccb3'):
    """
    Rysuje formatkę z otworami. Poprawiono czytelność etykiet.
    """
    # Ustawiamy rozmiar pod A4 poziomo (mniej więcej)
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Rysujemy Płytę
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla)
    ax.add_patch(rect)
    
    # Rysujemy Otwory
    ma_konf = False
    ma_prow = False
    
    for otw in otwory:
        x, y = otw[0], otw[1]
        kolor = otw[2] if len(otw) > 2 else 'red'
        if kolor == 'blue': ma_konf = True
        if kolor == 'red': ma_prow = True
        
        # Kropka otworu (promień 4)
        circle = patches.Circle((x, y), radius=4, edgecolor=kolor, facecolor='white', linewidth=1.5)
        ax.add_patch(circle)
        
        # --- POPRAWKA ETYKIET ---
        # Zwiększamy offset, żeby tekst nie nachodził na kropkę
        # Było x+6, y+2. Dajemy x+10, y+5.
        if len(otwory) < 40:
            ax.text(x + 10, y + 5, f"({x:.1f}, {y:.1f})", fontsize=8, color=kolor, weight='bold')

    # Legenda
    legenda = []
    if ma_prow: legenda.append("🔴 Czerwone: Prowadnice/Front")
    if ma_konf: legenda.append("🔵 Niebieskie: Konfirmaty (Konstrukcja)")
    
    opis_osi = "Szerokość (mm)"
    if legenda:
        opis_osi += "\nLEGENDA: " + "  |  ".join(legenda)
        
    ax.set_xlabel(opis_osi, fontsize=9)
    ax.set_ylabel("Wysokość (mm)")

    # Marginesy i widok
    margines = max(szer, wys) * 0.1
    ax.set_xlim(-margines, szer + margines)
    ax.set_ylim(-margines, wys + margines)
    ax.set_aspect('equal')
    
    ax.set_title(f"ID: {id_elementu} | {nazwa}\nWymiar: {szer:.1f} x {wys:.1f} mm", fontsize=12, weight='bold', pad=10)
    ax.grid(True, linestyle='--', alpha=0.5)
    
    return fig

# ==========================================
# 2. ALGORYTM NESTINGU (BEZ ZMIAN)
# ==========================================
def optymalizuj_rozkroj(formatki, arkusz_w, arkusz_h, rzaz=4):
    formatki_sorted = sorted(formatki, key=lambda x: x['Szerokość [mm]'] * x['Wysokość [mm]'], reverse=True)
    arkusze = []
    aktualny_arkusz = {'elementy': [], 'zuzycie_m2': 0}
    cur_x, cur_y = 0, 0
    max_h_row = 0
    
    for f in formatki_sorted:
        w, h = f['Szerokość [mm]'], f['Wysokość [mm]']
        if cur_x + w + rzaz > arkusz_w:
            cur_x = 0
            cur_y += max_h_row + rzaz
            max_h_row = 0
        if cur_y + h + rzaz > arkusz_h:
            arkusze.append(aktualny_arkusz)
            aktualny_arkusz = {'elementy': [], 'zuzycie_m2': 0}
            cur_x, cur_y = 0, 0
            max_h_row = 0
        aktualny_arkusz['elementy'].append({'x': cur_x, 'y': cur_y, 'w': w, 'h': h, 'id': f['ID']})
        aktualny_arkusz['zuzycie_m2'] += (w * h) / 1000000
        cur_x += w + rzaz
        if h > max_h_row: max_h_row = h
    if aktualny_arkusz['elementy']:
        arkusze.append(aktualny_arkusz)
    return arkusze

# ==========================================
# 3. BAZA SYSTEMÓW (BEZ ZMIAN)
# ==========================================
BAZA_SYSTEMOW = {
    "GTV Axis Pro": {
        "opis": "Pełny wysuw, cichy domyk",
        "offset_prowadnica": 37.5, "offset_front_y": 47.5, "offset_front_x": 15.5,
        "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87,
        "wysokosci_tylu": {"A": 84, "B": 116, "C": 167, "D": 199}
    },
    "Blum Antaro": {
        "opis": "Standard Blum",
        "offset_prowadnica": 37.0, "offset_front_y": 45.5, "offset_front_x": 15.5,
        "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87,
        "wysokosci_tylu": {"M": 83, "K": 115, "C": 167, "D": 200}
    },
    "GTV Modern Box": {
        "opis": "Szary klasyk",
        "offset_prowadnica": 37.0, "offset_front_y": 45.0, "offset_front_x": 15.5,
        "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87,
        "wysokosci_tylu": {"A": 84, "B": 135, "C": 199, "D": 224}
    }
}

# ==========================================
# 4. INTERFEJS I LOGIKA (BEZ ZMIAN)
# ==========================================
with st.sidebar:
    st.title("🪚 STOLARZPRO")
    st.markdown("---")
    st.header("1. Projekt")
    KOD_PROJEKTU = st.text_input("Kod Projektu", value="RTV-SALON").upper()
    st.header("2. Wymiary Szafki")
    H_MEBLA = st.number_input("Wysokość (mm)", value=600)
    W_MEBLA = st.number_input("Szerokość (mm)", value=1800)
    D_MEBLA = st.number_input("Głębokość (mm)", value=600)
    GR_PLYTY = st.number_input("Grubość płyty (mm)", value=18)
    st.header("3. Konstrukcja")
    ilosc_przegrod = st.number_input("Ilość przegród", value=2, min_value=0)
    typ_plecow = st.selectbox("Plecy (HDF)", ["Nakładane", "Wpuszczane", "Brak"])
    st.header("4. System Szuflad")
    opcje_sys = list(BAZA_SYSTEMOW.keys()) + ["Custom"]
    wybrany_sys = st.selectbox("Model:", opcje_sys)
    if wybrany_sys == "Custom":
        params = {"offset_prowadnica": 37.5, "offset_front_y": 47.5, "offset_front_x": 15.5, "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87, "wysokosci_tylu": {"Custom": 167}}
        typ_boku_key = "Custom"
    else:
        params = BAZA_SYSTEMOW[wybrany_sys]
        boki_list = list(params["wysokosci_tylu"].keys())
        typ_boku_key = st.selectbox("Wysokość boku", boki_list, index=len(boki_list)-1)
    axis_fuga = st.number_input("Fuga frontów (mm)", value=3.0)
    axis_ilosc = st.slider("Szuflady w sekcji", 1, 5, 2)
    axis_nl = st.selectbox("Długość (NL)", [300, 350, 400, 450, 500, 550], index=4)
    st.markdown("---")
    st.header("5. Parametry Rozkroju")
    ARKUSZ_W = st.number_input("Szer. arkusza", value=2800)
    ARKUSZ_H = st.number_input("Wys. arkusza", value=2070)
    RZAZ = st.number_input("Rzaz piły", value=4)

# --- OBLICZENIA ---
ilosc_sekcji = ilosc_przegrod + 1
szer_wew_total = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)
szer_jednej_wneki = szer_wew_total / ilosc_sekcji
wys_wewnetrzna = H_MEBLA - (2 * GR_PLYTY)
st.info(f"📏 Światło wnęki na szuflady: **{szer_jednej_wneki:.1f} mm**")

lista_elementow = []

def dodaj_element(nazwa, szer, wys, gr, material, uwagi="", wiercenia=[]):
    count = sum(1 for x in lista_elementow if x['typ'] == nazwa) + 1
    skroty = {"Bok Lewy": "BOK-L", "Bok Prawy": "BOK-P", "Wieniec Górny": "WIEN-G", "Wieniec Dolny": "WIEN-D", "Przegroda": "PRZEG", "Plecy HDF": "HDF", "Front Szuflady": "FR", "Dno Szuflady": "DNO", "Tył Szuflady": "TYL"}
    kod = skroty.get(nazwa, "EL")
    ident = f"{KOD_PROJEKTU}-{kod}" if nazwa in ["Bok Lewy", "Bok Prawy", "Wieniec Górny", "Wieniec Dolny"] else f"{KOD_PROJEKTU}-{kod}-{count}"
    lista_elementow.append({"ID": ident, "Nazwa": nazwa, "typ": nazwa, "Szerokość [mm]": round(szer, 1), "Wysokość [mm]": round(wys, 1), "Grubość [mm]": gr, "Materiał": material, "Uwagi": uwagi, "wiercenia": wiercenia})

# --- GENEROWANIE ELEMENTÓW ---
wiercenia_prow = []
akt_h = 0
h_frontu = (wys_wewnetrzna - ((axis_ilosc + 1) * axis_fuga)) / axis_ilosc
for i in range(axis_ilosc):
    pos = akt_h + axis_fuga + params["offset_prowadnica"]
    wiercenia_prow.append(pos)
    akt_h += axis_fuga + h_frontu
otwory_bok = []
for y in wiercenia_prow:
    otwory_bok.append((37.0, y, 'red'))
    otwory_bok.append((261.0, y, 'red'))
dodaj_element("Bok Lewy", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "Płyta 18mm", "Okleina G/D/P", otwory_bok)
dodaj_element("Bok Prawy", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "Płyta 18mm", "Okleina G/D/P", otwory_bok)
otwory_wien = []
y_k1, y_k2 = 50, D_MEBLA - 50
otwory_wien.extend([(GR_PLYTY/2, y_k1, 'blue'), (GR_PLYTY/2, y_k2, 'blue')])
otwory_wien.extend([(W_MEBLA-GR_PLYTY/2, y_k1, 'blue'), (W_MEBLA-GR_PLYTY/2, y_k2, 'blue')])
cx = GR_PLYTY
for i in range(ilosc_przegrod):
    cx += szer_jednej_wneki
    otwory_wien.extend([(cx+GR_PLYTY/2, y_k1, 'blue'), (cx+GR_PLYTY/2, y_k2, 'blue')])
    cx += GR_PLYTY
dodaj_element("Wieniec Górny", W_MEBLA, D_MEBLA, GR_PLYTY, "Płyta 18mm", "Okleina dookoła", otwory_wien)
dodaj_element("Wieniec Dolny", W_MEBLA, D_MEBLA, GR_PLYTY, "Płyta 18mm", "Okleina dookoła", otwory_wien)
dodaj_element("Przegroda", D_MEBLA, wys_wewnetrzna, GR_PLYTY, "Płyta 18mm", "Wiercenia 2-stronne", otwory_bok)
hdf_h = H_MEBLA - 4 if typ_plecow == "Nakładane" else H_MEBLA - 20
hdf_w = W_MEBLA - 4 if typ_plecow == "Nakładane" else W_MEBLA - 20
if typ_plecow != "Brak": dodaj_element("Plecy HDF", hdf_w, hdf_h, 3, "HDF 3mm", typ_plecow)
czy_wszystkie = st.sidebar.checkbox("Wypełnij szufladami WSZYSTKIE wnęki", value=True)
sekcje_do_wypelnienia = ilosc_sekcji if czy_wszystkie else 1
w_fr = szer_jednej_wneki - (2 * axis_fuga)
dno_w, dno_l = szer_jednej_wneki - params["redukcja_dna_szer"], axis_nl - params["redukcja_dna_dl"]
tyl_w, tyl_h = szer_jednej_wneki - params["redukcja_tyl_szer"], params["wysokosci_tylu"][typ_boku_key]
wx, wy = params["offset_front_x"] - axis_fuga, params["offset_front_y"]
otw_front = [(wx, wy, 'red'), (wx, wy+32, 'red'), (w_fr-wx, wy, 'red'), (w_fr-wx, wy+32, 'red')]
for s in range(sekcje_do_wypelnienia):
    for sz in range(axis_ilosc):
        dodaj_element("Front Szuflady", w_fr, h_frontu, 18, "Płyta 18mm", f"Sekcja {s+1}", otw_front)
        dodaj_element("Dno Szuflady", dno_l, dno_w, 16, "Płyta 16mm", "Biała/Szara")
        dodaj_element("Tył Szuflady", tyl_w, tyl_h, 16, "Płyta 16mm", "Biała/Szara")

# ==========================================
# 5. PREZENTACJA WYNIKÓW (NOWY PDF)
# ==========================================
df = pd.DataFrame(lista_elementow)
df_view = df.drop(columns=['typ', 'wiercenia'])

t1, t2, t3 = st.tabs(["📋 LISTA MATERIAŁOWA", "📐 RYSUNKI I PDF", "🗺️ ROZKRÓJ (NESTING)"])

with t1:
    st.subheader(f"Zestawienie: {KOD_PROJEKTU}")
    csv = df_view.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Pobierz CSV (Excel)", csv, f'{KOD_PROJEKTU}.csv', 'text/csv')
    st.dataframe(df_view, hide_index=True, use_container_width=True)
    st.divider()
    m18 = df[df["Materiał"] == "Płyta 18mm"]
    m16 = df[df["Materiał"] == "Płyta 16mm"]
    c1, c2 = st.columns(2)
    c1.metric("Płyta 18mm", f"{len(m18)} szt.")
    c2.metric("Płyta 16mm", f"{len(m16)} szt.")

with t2:
    # --- SEKCJA PDF (NOWOŚĆ) ---
    st.subheader("🖨️ Książka Wierceń (PDF)")
    st.caption("Wygeneruj plik ze wszystkimi rysunkami technicznymi do druku.")
    
    col_pdf1, col_pdf2 = st.columns([1, 2])
    with col_pdf1:
        if st.button("🚀 GENERUJ PLIK PDF", type="primary", use_container_width=True):
            with st.spinner("Rysuję i składam PDF..."):
                # Tu dzieje się magia tworzenia PDF w pamięci
                pdf_buffer = io.BytesIO()
                with PdfPages(pdf_buffer) as pdf:
                    # Iterujemy tylko po elementach, które mają wiercenia lub są frontami
                    elements_to_print = [el for el in lista_elementow if el['wiercenia'] or el['Nazwa'] == 'Front Szuflady']
                    
                    if not elements_to_print:
                        st.warning("Brak elementów z wierceniami do wydruku.")
                    else:
                        for el in elements_to_print:
                            # Rysujemy każdy element
                            fig = rysuj_element(
                                el['Szerokość [mm]'], el['Wysokość [mm]'], 
                                el['ID'], el['Nazwa'], el['wiercenia'], 
                                '#e6ccb3' if '18mm' in el['Materiał'] else '#f0f2f6'
                            )
                            # Zapisujemy stronę do PDF
                            pdf.savefig(fig)
                            # Zamykamy figurę, żeby zwolnić pamięć
                            plt.close(fig)
                        
                        # Przygotowanie do pobrania
                        pdf_buffer.seek(0)
                        st.session_state['pdf_ready'] = pdf_buffer

    with col_pdf2:
        if 'pdf_ready' in st.session_state:
            st.success("PDF gotowy do pobrania!")
            st.download_button(
                label="📥 POBIERZ PDF (Gotowy)",
                data=st.session_state['pdf_ready'],
                file_name=f"{KOD_PROJEKTU}_Rysunki_Techniczne.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.info("Kliknij przycisk po lewej, aby rozpocząć generowanie.")

    st.divider()
    
    # --- SEKCJA POJEDYNCZEGO PODGLĄDU (BEZ ZMIAN) ---
    st.subheader("👁️ Pojedynczy Podgląd")
    ids = [r['ID'] for r in lista_elementow if r['wiercenia'] or r['Nazwa']=='Front Szuflady']
    if ids:
        wybor = st.selectbox("Wybierz element:", ids)
        item = next(x for x in lista_elementow if x['ID'] == wybor)
        st.pyplot(rysuj_element(item['Szerokość [mm]'], item['Wysokość [mm]'], item['ID'], item['Nazwa'], item['wiercenia'], '#e6ccb3' if '18mm' in item['Materiał'] else '#f0f2f6'))
    else:
        st.info("Brak elementów z wierceniami.")

with t3:
    st.subheader(f"Symulacja Rozkroju (Płyta 18mm)")
    st.caption(f"Arkusz: {ARKUSZ_W}x{ARKUSZ_H} mm | Rzaz: {RZAZ} mm")
    if st.button("Uruchom Optymalizację"):
        p18 = [x for x in lista_elementow if x['Materiał'] == "Płyta 18mm"]
        wyniki = optymalizuj_rozkroj(p18, ARKUSZ_W, ARKUSZ_H, RZAZ)
        st.success(f"Potrzebna ilość arkuszy: {len(wyniki)}")
        for i, ark in enumerate(wyniki):
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.add_patch(patches.Rectangle((0,0), ARKUSZ_W, ARKUSZ_H, facecolor='#f0f0f0', edgecolor='black'))
            for el in ark['elementy']:
                ax.add_patch(patches.Rectangle((el['x'], el['y']), el['w'], el['h'], facecolor='#e6ccb3', edgecolor='brown'))
                if el['w'] > 150: ax.text(el['x']+el['w']/2, el['y']+el['h']/2, el['id'], ha='center', va='center', fontsize=7)
            ax.set_xlim(-100, ARKUSZ_W+100); ax.set_ylim(-100, ARKUSZ_H+100); ax.set_aspect('equal')
            ax.set_title(f"Arkusz #{i+1} (Zużycie: {ark['zuzycie_m2'] / ((ARKUSZ_W*ARKUSZ_H)/1000000) * 100:.1f}%)")
            st.pyplot(fig)
