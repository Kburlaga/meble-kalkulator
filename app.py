import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

st.set_page_config(page_title="Kalkulator Meblowy PRO 5.0", page_icon="🪚", layout="wide")

# ==========================================
# 1. FUNKCJA RYSUJĄCA (Z KOLORAMI)
# ==========================================
def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], kolor_tla='#e6ccb3'):
    """
    Rysuje formatkę.
    otwory: lista krotek (x, y) LUB (x, y, kolor)
    """
    fig, ax = plt.subplots(figsize=(6, 4))
    
    # Płyta
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla)
    ax.add_patch(rect)
    
    # Otwory
    for otw in otwory:
        x = otw[0]
        y = otw[1]
        # Domyślny kolor czerwony, chyba że podano trzeci parametr
        kolor = otw[2] if len(otw) > 2 else 'red'
        
        circle = patches.Circle((x, y), radius=4, edgecolor=kolor, facecolor='white', linewidth=1.5)
        ax.add_patch(circle)
        
        # Etykieta (tylko jeśli mało otworów, żeby nie zamazać)
        if len(otwory) < 20:
            label = f"({x:.1f}, {y:.1f})"
            ax.text(x + 6, y + 2, label, fontsize=7, color=kolor, weight='bold')

    # Legenda kolorów (tylko jeśli są różne)
    if otwory:
        ax.text(0, -wys*0.15, "🔴 Czerwone: Prowadnice/Front  🔵 Niebieskie: Konfirmaty (Konstrukcja)", fontsize=9)

    # Ustawienia widoku
    margines = max(szer, wys) * 0.15
    ax.set_xlim(-margines, szer + margines)
    ax.set_ylim(-margines, wys + margines)
    ax.set_aspect('equal')
    
    ax.set_title(f"ID: {id_elementu}\n{nazwa}\n{szer:.1f} x {wys:.1f} mm", fontsize=12, weight='bold', pad=15)
    ax.set_xlabel("Szerokość (mm)")
    ax.set_ylabel("Wysokość (mm)")
    ax.grid(True, linestyle='--', alpha=0.5)
    
    return fig

# ==========================================
# 2. BAZA DANYCH SYSTEMÓW
# ==========================================
BAZA_SYSTEMOW = {
    "GTV Axis Pro": {
        "opis": "Pełny wysuw, cichy domyk",
        "offset_prowadnica": 37.5,
        "offset_front_y": 47.5,
        "offset_front_x": 15.5,
        "redukcja_dna_szer": 75,
        "redukcja_dna_dl": 24,
        "redukcja_tyl_szer": 87,
        "wysokosci_tylu": {"A": 84, "B": 116, "C": 167, "D": 199}
    },
    "Blum Antaro": {
        "opis": "Standard Blum",
        "offset_prowadnica": 37.0,
        "offset_front_y": 45.5,
        "offset_front_x": 15.5,
        "redukcja_dna_szer": 75,
        "redukcja_dna_dl": 24,
        "redukcja_tyl_szer": 87,
        "wysokosci_tylu": {"M": 83, "K": 115, "C": 167, "D": 200}
    }
}

st.title("🪚 Manager Formatek (Z Wierceniami)")

# ==========================================
# 3. PANEL BOCZNY (INPUT)
# ==========================================
with st.sidebar:
    st.header("📋 Dane Projektu")
    KOD_PROJEKTU = st.text_input("Kod Projektu (Prefix)", value="RTV-01").upper()
    
    st.header("📏 Wymiary Szafki")
    H_MEBLA = st.number_input("Wysokość (mm)", value=600)
    W_MEBLA = st.number_input("Szerokość (mm)", value=1800)
    D_MEBLA = st.number_input("Głębokość (mm)", value=600)
    GR_PLYTY = st.number_input("Grubość płyty (mm)", value=18)
    
    st.header("🔨 Konstrukcja")
    ilosc_przegrod = st.number_input("Ilość przegród", value=2, min_value=0)
    typ_plecow = st.selectbox("Plecy (HDF)", ["Nakładane", "Wpuszczane", "Brak"])
    
    # Obliczenia światła
    ilosc_sekcji = ilosc_przegrod + 1
    szer_wewnetrzna_total = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)
    szer_jednej_wneki = szer_wewnetrzna_total / ilosc_sekcji
    wys_wewnetrzna = H_MEBLA - (2 * GR_PLYTY)

    st.info(f"Światło wnęki: **{szer_jednej_wneki:.1f} mm**")

    st.header("🗄️ System Szuflad")
    opcje = list(BAZA_SYSTEMOW.keys()) + ["Custom"]
    wybrany_sys = st.selectbox("Wybierz system:", opcje)
    
    if wybrany_sys == "Custom":
        params = {"offset_prowadnica": 37.5, "offset_front_y": 47.5, "offset_front_x": 15.5,
                  "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87,
                  "wysokosci_tylu": {"Custom": 167}}
        typ_boku_key = "Custom"
    else:
        params = BAZA_SYSTEMOW[wybrany_sys]
        boki = list(params["wysokosci_tylu"].keys())
        typ_boku_key = st.selectbox("Wysokość boku", boki, index=len(boki)-1)

    axis_fuga = st.number_input("Fuga (mm)", value=3.0)
    axis_ilosc = st.slider("Szuflady w sekcji", 2, 5, 2)
    axis_nl = st.selectbox("Długość (NL)", [300, 350, 400, 450, 500, 550], index=4)

# ==========================================
# 4. LOGIKA GENEROWANIA LISTY
# ==========================================
lista_elementow = []

def dodaj_element(nazwa_czesci, szer, wys, gr, material, uwagi="", wiercenia=[]):
    count = sum(1 for x in lista_elementow if x['typ'] == nazwa_czesci) + 1
    skroty = {
        "Bok Lewy": "BOK-L", "Bok Prawy": "BOK-P", "Wieniec Górny": "WIEN-G", 
        "Wieniec Dolny": "WIEN-D", "Przegroda": "PRZEG", "Plecy HDF": "HDF",
        "Front Szuflady": "FR", "Dno Szuflady": "DNO", "Tył Szuflady": "TYL"
    }
    kod_czesci = skroty.get(nazwa_czesci, "EL")
    
    if nazwa_czesci in ["Bok Lewy", "Bok Prawy", "Wieniec Górny", "Wieniec Dolny"]:
        identyfikator = f"{KOD_PROJEKTU}-{kod_czesci}"
    else:
        identyfikator = f"{KOD_PROJEKTU}-{kod_czesci}-{count}"

    lista_elementow.append({
        "ID": identyfikator,
        "Nazwa": nazwa_czesci,
        "Szerokość [mm]": round(szer, 1),
        "Wysokość [mm]": round(wys, 1),
        "Grubość [mm]": gr,
        "Materiał": material,
        "Uwagi": uwagi,
        "typ": nazwa_czesci,
        "wiercenia": wiercenia
    })

# --- A. KORPUS ---
# 1. Boki (Tylko prowadnice - czerwone)
wiercenia_prowadnice = []
akt_h = 0
h_frontu = (wys_wewnetrzna - ((axis_ilosc + 1) * axis_fuga)) / axis_ilosc

for i in range(axis_ilosc):
    pos = akt_h + axis_fuga + params["offset_prowadnica"]
    wiercenia_prowadnice.append(pos)
    akt_h += axis_fuga + h_frontu

otwory_bok_rys = []
for y in wiercenia_prowadnice:
    # (x, y, kolor) -> 'red' domyślnie
    otwory_bok_rys.append((37.0, y, 'red')) 
    otwory_bok_rys.append((37.0 + 224, y, 'red'))

dodaj_element("Bok Lewy", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", "Okleina: przód/dół/góra", otwory_bok_rys)
dodaj_element("Bok Prawy", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", "Okleina: przód/dół/góra", otwory_bok_rys)

# 2. Wieńce (Konfirmaty - NIEBIESKIE)
# Musimy obliczyć gdzie wiercić w wieńcu, żeby trafić w boki i przegrody
otwory_wieniec = []
y_konf_przod = 50 # 5cm od krawędzi przedniej
y_konf_tyl = D_MEBLA - 50 # 5cm od krawędzi tylnej

# A. Łączenie z Bokiem Lewym (środek płyty bocznej to 9mm od krawędzi wieńca)
center_bok_lewy = GR_PLYTY / 2
otwory_wieniec.append((center_bok_lewy, y_konf_przod, 'blue'))
otwory_wieniec.append((center_bok_lewy, y_konf_tyl, 'blue'))

# B. Łączenie z Bokiem Prawym
center_bok_prawy = W_MEBLA - (GR_PLYTY / 2)
otwory_wieniec.append((center_bok_prawy, y_konf_przod, 'blue'))
otwory_wieniec.append((center_bok_prawy, y_konf_tyl, 'blue'))

# C. Łączenie z Przegrodami
current_x = GR_PLYTY # Startujemy za bokiem lewym
for i in range(ilosc_przegrod):
    current_x += szer_jednej_wneki
    center_przegroda = current_x + (GR_PLYTY / 2)
    otwory_wieniec.append((center_przegroda, y_konf_przod, 'blue'))
    otwory_wieniec.append((center_przegroda, y_konf_tyl, 'blue'))
    current_x += GR_PLYTY

dodaj_element("Wieniec Górny", W_MEBLA, D_MEBLA, GR_PLYTY, "Płyta 18mm", "Okleina dookoła", otwory_wieniec)
dodaj_element("Wieniec Dolny", W_MEBLA, D_MEBLA, GR_PLYTY, "Płyta 18mm", "Okleina dookoła", otwory_wieniec)

# 3. Przegrody (Prowadnice z OBU stron)
# Uwaga: Na rysunku 2D pokażemy wiercenia jak dla boku, stolarz musi wiedzieć że to "przelotowe" lub dwustronne
dodaj_element("Przegroda", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", "Wiercenia OBUSTRONNE!", otwory_bok_rys)

# 4. Plecy
hdf_h = H_MEBLA - 4 if typ_plecow == "Nakładane" else H_MEBLA - 20
hdf_w = W_MEBLA - 4 if typ_plecow == "Nakładane" else W_MEBLA - 20
if typ_plecow != "Brak":
    dodaj_element("Plecy HDF", hdf_w, hdf_h, 3, "HDF 3mm", typ_plecow)

# --- B. SZUFLADY ---
st.sidebar.markdown("---")
czy_wszystkie = st.sidebar.checkbox("Szuflady we wszystkich wnękach", value=True)
sekcje_do_wypelnienia = ilosc_sekcji if czy_wszystkie else 1

w_frontu = szer_jednej_wneki - (2 * axis_fuga)
dno_szer = szer_jednej_wneki - params["redukcja_dna_szer"]
dno_dl = axis_nl - params["redukcja_dna_dl"]
tyl_szer = szer_jednej_wneki - params["redukcja_tyl_szer"]
tyl_wys = params["wysokosci_tylu"][typ_boku_key]

wierc_front_y = params["offset_front_y"]
wierc_front_x = params["offset_front_x"] - axis_fuga
otwory_front_rys = [
    (wierc_front_x, wierc_front_y, 'red'), 
    (wierc_front_x, wierc_front_y+32, 'red'),
    (w_frontu - wierc_front_x, wierc_front_y, 'red'),
    (w_frontu - wierc_front_x, wierc_front_y+32, 'red')
]

for s in range(sekcje_do_wypelnienia):
    for sz in range(axis_ilosc):
        dodaj_element("Front Szuflady", w_frontu, h_frontu, 18, "Płyta 18mm", f"Sekcja {s+1}, Szuflada {sz+1}", otwory_front_rys)
        dodaj_element("Dno Szuflady", dno_dl, dno_szer, 16, "Płyta 16mm", "Biała/Szara")
        dodaj_element("Tył Szuflady", tyl_szer, tyl_wys, 16, "Płyta 16mm", "Biała/Szara")

# ==========================================
# 5. WYŚWIETLANIE
# ==========================================
df = pd.DataFrame(lista_elementow)
df_view = df.drop(columns=['typ', 'wiercenia'])

tab_lista, tab_rysunki = st.tabs(["📋 LISTA ROZKROJU", "📐 RYSUNKI TECHNICZNE"])

with tab_lista:
    st.subheader(f"Lista Formatek: {KOD_PROJEKTU}")
    
    # Przycisk pobierania CSV
    csv = df_view.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Pobierz Listę (CSV)",
        data=csv,
        file_name=f'{KOD_PROJEKTU}_rozpiska.csv',
        mime='text/csv',
    )
    
    st.dataframe(
        df_view,
        column_config={
            "Szerokość [mm]": st.column_config.NumberColumn(format="%.1f"),
            "Wysokość [mm]": st.column_config.NumberColumn(format="%.1f"),
        },
        use_container_width=True,
        hide_index=True
    )
    
    st.divider()
    m18 = df[df["Materiał"] == "Płyta 18mm"]
    m16 = df[df["Materiał"] == "Płyta 16mm"]
    c1, c2 = st.columns(2)
    c1.metric("Płyta 18mm", f"{len(m18)} szt.")
    c2.metric("Płyta 16mm", f"{len(m16)} szt.")

with tab_rysunki:
    st.subheader("Generator Rysunków")
    elementy_z_rys = [row['ID'] for row in lista_elementow if row['wiercenia']]
    
    if not elementy_z_rys:
        st.info("Brak elementów z wierceniami.")
    else:
        wybrane_id = st.selectbox("Wybierz element:", elementy_z_rys)
        item = next(x for x in lista_elementow if x['ID'] == wybrane_id)
        
        c_rys1, c_rys2 = st.columns([2, 1])
        with c_rys1:
            fig = rysuj_element(
                item['Szerokość [mm]'], 
                item['Wysokość [mm]'], 
                item['ID'], 
                item['Nazwa'], 
                item['wiercenia'],
                '#e6ccb3' if item['Materiał'] == "Płyta 18mm" else '#f0f2f6'
            )
            st.pyplot(fig)
        with c_rys2:
            st.info("Legenda Wierceń")
            # Filtrujemy kolory do wyświetlenia opisu
            coords = item['wiercenia']
            st.write(f"Ilość otworów: {len(coords)}")
            st.markdown("---")
            for w in coords:
                typ = "Konfirmat" if len(w) > 2 and w[2] == 'blue' else "Prowadnica/Front"
                st.code(f"X: {w[0]:.1f} | Y: {w[1]:.1f} [{typ}]")
