import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

st.set_page_config(page_title="Kalkulator Meblowy PRO ID 2025", page_icon="🪚", layout="wide")

# ==========================================
# 1. FUNKCJA RYSUJĄCA
# ==========================================
def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], kolor_tla='#e6ccb3'):
    """
    Rysuje formatkę z unikalnym ID i wymiarami.
    """
    fig, ax = plt.subplots(figsize=(6, 4))
    
    # Płyta
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla)
    ax.add_patch(rect)
    
    # Otwory
    for x, y in otwory:
        circle = patches.Circle((x, y), radius=4, edgecolor='red', facecolor='white', linewidth=1.5)
        ax.add_patch(circle)
        label = f"({x:.1f}, {y:.1f})"
        ax.text(x + 6, y + 2, label, fontsize=8, color='darkred', weight='bold')

    # Ustawienia widoku
    margines = max(szer, wys) * 0.15
    ax.set_xlim(-margines, szer + margines)
    ax.set_ylim(-margines, wys + margines)
    ax.set_aspect('equal')
    
    # Tytuł z ID
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

st.title("🪚 Manager Formatek z ID")

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
    
    # Ładowanie parametrów
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
# 4. LOGIKA GENEROWANIA LISTY FORMATEK
# ==========================================
lista_elementow = []

def dodaj_element(nazwa_czesci, szer, wys, gr, material, uwagi="", wiercenia=[]):
    """Pomocnicza funkcja do tworzenia obiektów"""
    # Generowanie unikalnego ID
    # Licznik sprawdzający ile już jest takich elementów, żeby dodać numer (np. FR-1, FR-2)
    count = sum(1 for x in lista_elementow if x['typ'] == nazwa_czesci) + 1
    
    # Skróty do ID
    skroty = {
        "Bok Lewy": "BOK-L", "Bok Prawy": "BOK-P", "Wieniec Górny": "WIEN-G", 
        "Wieniec Dolny": "WIEN-D", "Przegroda": "PRZEG", "Plecy HDF": "HDF",
        "Front Szuflady": "FR", "Dno Szuflady": "DNO", "Tył Szuflady": "TYL"
    }
    kod_czesci = skroty.get(nazwa_czesci, "EL")
    
    # Dla boków L/P i wieńców nie numerujemy jeśli jest 1 sztuka danego typu
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
        "typ": nazwa_czesci, # do filtrowania
        "wiercenia": wiercenia # lista krotek (x,y)
    })

# --- A. KORPUS ---
# 1. Boki
# Obliczanie wierceń w bokach (pod prowadnice)
wiercenia_prowadnice = []
akt_h = 0
h_frontu = (wys_wewnetrzna - ((axis_ilosc + 1) * axis_fuga)) / axis_ilosc

for i in range(axis_ilosc):
    pos = akt_h + axis_fuga + params["offset_prowadnica"]
    wiercenia_prowadnice.append(pos)
    akt_h += axis_fuga + h_frontu

# Przygotowanie współrzędnych otworów dla rysunku boku (X=37mm od przodu)
otwory_bok_rys = []
for y in wiercenia_prowadnice:
    otwory_bok_rys.append((37.0, y))
    otwory_bok_rys.append((37.0 + 224, y)) # Drugi otwór stabilizacyjny

dodaj_element("Bok Lewy", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", "Okleina: przód/dół/góra", otwory_bok_rys)
dodaj_element("Bok Prawy", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", "Okleina: przód/dół/góra", otwory_bok_rys)

# 2. Wieńce
dodaj_element("Wieniec Górny", W_MEBLA, D_MEBLA, GR_PLYTY, "Płyta 18mm", "Okleina dookoła")
dodaj_element("Wieniec Dolny", W_MEBLA, D_MEBLA, GR_PLYTY, "Płyta 18mm", "Okleina dookoła")

# 3. Przegrody
for i in range(ilosc_przegrod):
    # Przegroda ma wiercenia z obu stron (teoretycznie), tutaj upraszczamy do jednej listy
    dodaj_element("Przegroda", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", "Wiercenia z obu stron!", otwory_bok_rys)

# 4. Plecy
hdf_h = H_MEBLA - 4 if typ_plecow == "Nakładane" else H_MEBLA - 20
hdf_w = W_MEBLA - 4 if typ_plecow == "Nakładane" else W_MEBLA - 20
if typ_plecow != "Brak":
    dodaj_element("Plecy HDF", hdf_w, hdf_h, 3, "HDF 3mm", typ_plecow)

# --- B. SZUFLADY ---
# Generujemy formatki dla WSZYSTKICH sekcji (na razie założenie: szuflady są tylko w pierwszej sekcji lub w każdej)
# Przyjmijmy dla uproszczenia widoku, że szuflady są w 1 sekcji (żeby nie robić 50 formatek)
# Lub zróbmy pętlę po sekcjach jeśli chcesz:
st.sidebar.markdown("---")
czy_wszystkie_sekcje = st.sidebar.checkbox("Wypełnij szufladami WSZYSTKIE wnęki", value=True)
sekcje_do_wypelnienia = ilosc_sekcji if czy_wszystkie_sekcje else 1

w_frontu = szer_jednej_wneki - (2 * axis_fuga)
dno_szer = szer_jednej_wneki - params["redukcja_dna_szer"]
dno_dl = axis_nl - params["redukcja_dna_dl"]
tyl_szer = szer_jednej_wneki - params["redukcja_tyl_szer"]
tyl_wys = params["wysokosci_tylu"][typ_boku_key]

# Obliczanie wierceń frontu
wierc_front_y = params["offset_front_y"]
wierc_front_x = params["offset_front_x"] - axis_fuga
otwory_front_rys = [
    (wierc_front_x, wierc_front_y), 
    (wierc_front_x, wierc_front_y+32),
    (w_frontu - wierc_front_x, wierc_front_y),
    (w_frontu - wierc_front_x, wierc_front_y+32)
]

for s in range(sekcje_do_wypelnienia):
    for sz in range(axis_ilosc):
        # Front
        dodaj_element("Front Szuflady", w_frontu, h_frontu, 18, "Płyta 18mm", f"Sekcja {s+1}, Szuflada {sz+1}", otwory_front_rys)
        # Wnętrze
        dodaj_element("Dno Szuflady", dno_dl, dno_szer, 16, "Płyta 16mm", "Biała/Szara")
        dodaj_element("Tył Szuflady", tyl_szer, tyl_wys, 16, "Płyta 16mm", "Biała/Szara")

# ==========================================
# 5. WYŚWIETLANIE (TABELA I RYSUNKI)
# ==========================================
# Tworzenie DataFrame
df = pd.DataFrame(lista_elementow)
# Ukrywamy kolumny techniczne w tabeli
df_view = df.drop(columns=['typ', 'wiercenia'])

tab_lista, tab_rysunki = st.tabs(["📋 LISTA ROZKROJU", "📐 RYSUNKI TECHNICZNE"])

with tab_lista:
    st.subheader(f"Lista Formatek: {KOD_PROJEKTU}")
    st.caption("Możesz powiększyć tabelę ikoną w rogu.")
    st.dataframe(
        df_view,
        column_config={
            "Szerokość [mm]": st.column_config.NumberColumn(format="%.1f"),
            "Wysokość [mm]": st.column_config.NumberColumn(format="%.1f"),
        },
        use_container_width=True,
        hide_index=True
    )
    
    # Podsumowanie materiałowe
    st.divider()
    m18 = df[df["Materiał"] == "Płyta 18mm"]
    m16 = df[df["Materiał"] == "Płyta 16mm"]
    mhdf = df[df["Materiał"] == "HDF 3mm"]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Płyta 18mm (Front/Korpus)", f"{len(m18)} szt.")
    c2.metric("Płyta 16mm (Szuflady)", f"{len(m16)} szt.")
    c3.metric("HDF 3mm (Plecy)", f"{len(mhdf)} szt.")

with tab_rysunki:
    st.subheader("Generator Rysunków")
    
    # Lista rozwijana z ID elementów, które mają wiercenia lub są istotne
    # Filtrujemy tylko te, które mają sensowne wiercenia lub są duże
    elementy_z_rys = [row['ID'] for row in lista_elementow if row['wiercenia']]
    
    if not elementy_z_rys:
        st.info("Brak elementów zdefiniowanych jako wymagające wiercenia (Fronty/Boki).")
    else:
        wybrane_id = st.selectbox("Wybierz element do podglądu:", elementy_z_rys)
        
        # Pobieramy dane wybranego elementu
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
            st.info("**Szczegóły elementu**")
            st.write(f"**Nazwa:** {item['Nazwa']}")
            st.write(f"**Wymiar:** {item['Szerokość [mm]']} x {item['Wysokość [mm]']}")
            st.write(f"**Materiał:** {item['Materiał']}")
            if item['Uwagi']:
                st.warning(f"⚠️ {item['Uwagi']}")
            
            st.markdown("---")
            st.write("**Lista współrzędnych wierceń (X, Y):**")
            for w in item['wiercenia']:
                st.code(f"X: {w[0]:.1f} | Y: {w[1]:.1f}")
