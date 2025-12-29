import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import io

st.set_page_config(page_title="Kalkulator Meblowy V8 (Szablony)", page_icon="🪚", layout="wide")

# ==========================================
# 1. FUNKCJA RYSUJĄCA (PODGLĄD CAŁOŚCI)
# ==========================================
def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], kolor_tla='#e6ccb3'):
    fig, ax = plt.subplots(figsize=(8, 5))
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla)
    ax.add_patch(rect)
    
    for otw in otwory:
        x, y = otw[0], otw[1]
        kolor = otw[2] if len(otw) > 2 else 'red'
        circle = patches.Circle((x, y), radius=4, edgecolor=kolor, facecolor='white', linewidth=1.5)
        ax.add_patch(circle)
        label = f"{x:.1f}"
        ax.text(x, y + 8, label, fontsize=8, color=kolor, weight='bold', ha='center', rotation=90)

    margines = max(szer, wys) * 0.15
    ax.set_xlim(-margines, szer + margines)
    ax.set_ylim(-margines, wys + margines)
    ax.set_aspect('equal')
    ax.set_title(f"ID: {id_elementu}\n{nazwa}\n{szer:.1f} x {wys:.1f} mm", fontsize=12, weight='bold', pad=15)
    ax.grid(True, linestyle='--', alpha=0.5)
    return fig

# ==========================================
# 2. FUNKCJA GENERUJĄCA SZABLON A4 (1:1)
# ==========================================
def rysuj_szablon_a4(szer_plyty, wys_plyty, id_elementu, otwory, naroznik):
    """
    Generuje szablon A4 (210x297mm) dla wybranego narożnika.
    """
    # Ustawienia A4 w calach (dla matplotlib)
    # A4 = 8.27 x 11.69 cala
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    
    # Granice A4 w mm (z małym marginesem na drukarkę)
    A4_W = 210
    A4_H = 297
    MARGINES_DRUKU = 10 # Odsuwamy krawędź płyty od krawędzi kartki, żeby drukarka nie ucięła
    
    # Transformacja współrzędnych w zależności od narożnika
    # Chcemy, żeby wybrany narożnik płyty znalazł się w punkcie (MARGINES, MARGINES) na kartce
    
    otwory_na_szablonie = []
    
    # Rysujemy "wirtualną" płytę na kartce
    plyta_rect = None
    
    if naroznik == "Lewy-Dół (0,0)":
        origin_x, origin_y = 0, 0
        # Przesuwamy otwory o margines
        for x, y, k in otwory:
            new_x = x + MARGINES_DRUKU
            new_y = y + MARGINES_DRUKU
            # Filtrujemy tylko te, które mieszczą się na kartce
            if 0 <= new_x <= A4_W and 0 <= new_y <= A4_H:
                otwory_na_szablonie.append((new_x, new_y, k, x, y)) # Zapamiętujemy też oryginał do opisu
                
        # Rysujemy krawędzie płyty (nieskończone linie)
        ax.axvline(x=MARGINES_DRUKU, color='black', linewidth=3) # Krawędź Lewa
        ax.axhline(y=MARGINES_DRUKU, color='black', linewidth=3) # Krawędź Dolna
        ax.text(MARGINES_DRUKU + 5, MARGINES_DRUKU + 5, "NAROŻNIK PŁYTY (Lewy-Dół)", fontsize=10, weight='bold')

    elif naroznik == "Lewy-Góra (0, H)":
        origin_x, origin_y = 0, wys_plyty
        # Otwór Y=564 (przy H=600) jest 36mm od góry.
        # Na kartce (od dołu) ma być na wysokości: A4_H - MARGINES - (H - y)
        # Łatwiej: Obracamy układ. Rysujemy górę kartki jako górę płyty.
        
        # Przyjmijmy system: Y na wykresie to Y na kartce.
        # Krawędź Górna Płyty to linia Y = A4_H - MARGINES
        LINIA_GORA = A4_H - MARGINES_DRUKU
        
        for x, y, k in otwory:
            dist_from_top = wys_plyty - y
            new_x = x + MARGINES_DRUKU
            new_y = LINIA_GORA - dist_from_top
            
            if 0 <= new_x <= A4_W and 0 <= new_y <= A4_H:
                otwory_na_szablonie.append((new_x, new_y, k, x, y))

        ax.axvline(x=MARGINES_DRUKU, color='black', linewidth=3) # Lewa
        ax.axhline(y=LINIA_GORA, color='black', linewidth=3) # Góra
        ax.text(MARGINES_DRUKU + 5, LINIA_GORA - 10, "NAROŻNIK PŁYTY (Lewy-Góra)", fontsize=10, weight='bold')

    # (Można dodać Prawy-Dół i Prawy-Góra analogicznie, ale L-D i L-G zazwyczaj wystarczą dla boków)

    # Rysowanie otworów na szablonie
    for ox, oy, kol, orig_x, orig_y in otwory_na_szablonie:
        # Krzyżyk (celownik) dla precyzji
        ax.plot(ox, oy, '+', markersize=15, color='black', markeredgewidth=1)
        # Kółko
        circle = patches.Circle((ox, oy), radius=2.5, edgecolor=kol, facecolor='none', linewidth=1.5)
        ax.add_patch(circle)
        # Opis
        ax.text(ox + 4, oy + 4, f"X:{orig_x:.1f}\nY:{orig_y:.1f}", fontsize=7, color=kol)

    # MIARKA KONTROLNA (Bardzo ważne!)
    ax.plot([A4_W - 60, A4_W - 10], [20, 20], color='black', linewidth=2)
    ax.plot([A4_W - 60, A4_W - 60], [18, 22], color='black', linewidth=2) # Wąs
    ax.plot([A4_W - 10, A4_W - 10], [18, 22], color='black', linewidth=2) # Wąs
    ax.text(A4_W - 35, 23, "KONTROLA: 50 mm", ha='center', fontsize=8)

    # Ustawienia osi (sztywne A4)
    ax.set_xlim(0, A4_W)
    ax.set_ylim(0, A4_H)
    ax.set_aspect('equal')
    ax.axis('off') # Wyłączamy osie z liczbami, żeby nie myliły
    
    # Ramka kartki
    rect_paper = patches.Rectangle((0,0), A4_W, A4_H, linewidth=1, edgecolor='gray', facecolor='none', linestyle='--')
    ax.add_patch(rect_paper)
    
    ax.set_title(f"SZABLON 1:1 | {id_elementu} | {naroznik}\nUWAGA: Drukuj w skali 100% (Nie 'Dopasuj do strony')", fontsize=10)
    
    return fig

# ==========================================
# 3. BAZA DANYCH I INPUT (SKRÓCONE DLA CZYTELNOŚCI)
# ==========================================
# (Tutaj wklej tę samą bazę i input co w V7 - bez zmian w logice obliczeń)
# Aby kod był kompletny, powtarzam kluczowe fragmenty:

BAZA_SYSTEMOW = {
    "GTV Axis Pro": {
        "opis": "Pełny wysuw", "offset_prowadnica": 37.5, "offset_front_y": 47.5, "offset_front_x": 15.5,
        "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87,
        "wysokosci_tylu": {"A": 84, "B": 116, "C": 167, "D": 199}
    },
    "Blum Antaro": {
        "opis": "Standard Blum", "offset_prowadnica": 37.0, "offset_front_y": 45.5, "offset_front_x": 15.5,
        "redukcja_dna_szer": 75, "redukcja_dna_dl": 24, "redukcja_tyl_szer": 87,
        "wysokosci_tylu": {"M": 83, "K": 115, "C": 167, "D": 200}
    }
}

# --- PANEL BOCZNY (Input) ---
with st.sidebar:
    st.header("📋 Dane Projektu")
    KOD_PROJEKTU = st.text_input("Kod Projektu", value="RTV-01").upper()
    st.header("📏 Wymiary Szafki")
    H_MEBLA = st.number_input("Wysokość (mm)", value=600)
    W_MEBLA = st.number_input("Szerokość (mm)", value=600)
    D_MEBLA = st.number_input("Głębokość (mm)", value=600)
    GR_PLYTY = st.number_input("Grubość płyty (mm)", value=18)
    st.header("🎨 Styl Frontów")
    typ_frontu = st.selectbox("Typ Frontu", ["Nakładane (Na korpus)", "Wpuszczane (Wewnątrz)"])
    st.header("🔨 Konstrukcja")
    ilosc_przegrod = st.number_input("Ilość przegród", value=0, min_value=0)
    typ_plecow = st.selectbox("Plecy (HDF)", ["Nakładane", "Wpuszczane", "Brak"])
    ilosc_sekcji = ilosc_przegrod + 1
    szer_wewnetrzna_total = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)
    szer_jednej_wneki = szer_wewnetrzna_total / ilosc_sekcji
    wys_wewnetrzna = H_MEBLA - (2 * GR_PLYTY)
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

# --- LOGIKA OBLICZEŃ (Skrócona - to samo co w V7) ---
lista_elementow = []
def dodaj_element(nazwa, szer, wys, gr, mat, uwagi="", wiercenia=[]):
    count = sum(1 for x in lista_elementow if x['typ'] == nazwa) + 1
    skroty = {"Bok Lewy": "BOK-L", "Bok Prawy": "BOK-P", "Wieniec Górny": "WIEN-G", 
              "Wieniec Dolny": "WIEN-D", "Przegroda": "PRZEG", "Plecy HDF": "HDF",
              "Front Szuflady": "FR", "Dno Szuflady": "DNO", "Tył Szuflady": "TYL"}
    kod = skroty.get(nazwa, "EL")
    identyfikator = f"{KOD_PROJEKTU}-{kod}" if nazwa in ["Bok Lewy", "Bok Prawy", "Wieniec Górny", "Wieniec Dolny"] else f"{KOD_PROJEKTU}-{kod}-{count}"
    lista_elementow.append({"ID": identyfikator, "Nazwa": nazwa, "Szerokość [mm]": round(szer, 1), 
                            "Wysokość [mm]": round(wys, 1), "Grubość [mm]": gr, "Materiał": mat, 
                            "Uwagi": uwagi, "typ": nazwa, "wiercenia": wiercenia})

# Obliczenia Frontów
if typ_frontu == "Nakładane (Na korpus)":
    total_h_frontow = H_MEBLA - 4; total_w_frontow = W_MEBLA - 4
    h_frontu = (total_h_frontow - ((axis_ilosc - 1) * axis_fuga)) / axis_ilosc
    w_frontu = (total_w_frontow - ((ilosc_sekcji - 1) * axis_fuga)) / ilosc_sekcji
    x_prowadnicy = params["offset_prowadnica"]
else:
    h_frontu = (wys_wewnetrzna - ((axis_ilosc + 1) * axis_fuga)) / axis_ilosc
    w_frontu = szer_jednej_wneki - (2 * axis_fuga)
    x_prowadnicy = params["offset_prowadnica"] + GR_PLYTY + 1

# Wiercenia w boku
wiercenia_prowadnice = []
akt_h = 0 
for i in range(axis_ilosc):
    if typ_frontu == "Nakładane (Na korpus)": start_y = 2 + params["offset_prowadnica"] + akt_h
    else: start_y = GR_PLYTY + axis_fuga + params["offset_prowadnica"] + akt_h
    wiercenia_prowadnice.append(start_y)
    akt_h += h_frontu + axis_fuga

otwory_bok = []
for y in wiercenia_prowadnice:
    otwory_bok.append((x_prowadnicy, y, 'red'))
    otwory_bok.append((x_prowadnicy + 224, y, 'red'))

dodaj_element("Bok Lewy", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", f"Sys: {typ_frontu}", otwory_bok)
dodaj_element("Bok Prawy", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", f"Sys: {typ_frontu}", otwory_bok)

otwory_wieniec = []
y_k1, y_k2 = 50, D_MEBLA - 50
otwory_wieniec.append((GR_PLYTY/2, y_k1, 'blue')); otwory_wieniec.append((GR_PLYTY/2, y_k2, 'blue'))
otwory_wieniec.append((W_MEBLA - GR_PLYTY/2, y_k1, 'blue')); otwory_wieniec.append((W_MEBLA - GR_PLYTY/2, y_k2, 'blue'))
curr_x = GR_PLYTY
for i in range(ilosc_przegrod):
    curr_x += szer_jednej_wneki
    otwory_wieniec.append((curr_x + GR_PLYTY/2, y_k1, 'blue')); otwory_wieniec.append((curr_x + GR_PLYTY/2, y_k2, 'blue'))
    curr_x += GR_PLYTY

dodaj_element("Wieniec Górny", W_MEBLA, D_MEBLA, GR_PLYTY, "Płyta 18mm", "Okleina dookoła", otwory_wieniec)
dodaj_element("Wieniec Dolny", W_MEBLA, D_MEBLA, GR_PLYTY, "Płyta 18mm", "Okleina dookoła", otwory_wieniec)

if ilosc_przegrod > 0: dodaj_element("Przegroda", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", "Wiercenia OBUSTRONNE", otwory_bok)

czy_wszystkie = st.sidebar.checkbox("Szuflady we wszystkich sekcjach", value=True)
sekcje_do_gen = ilosc_sekcji if czy_wszystkie else 1
dno_szer = szer_jednej_wneki - params["redukcja_dna_szer"]; dno_dl = axis_nl - params["redukcja_dna_dl"]
tyl_szer = szer_jednej_wneki - params["redukcja_tyl_szer"]; tyl_wys = params["wysokosci_tylu"][typ_boku_key]
wf_y = params["offset_front_y"]
wf_x = params["offset_front_x"] if typ_frontu == "Nakładane (Na korpus)" else params["offset_front_x"] - axis_fuga
otwory_front = [(wf_x, wf_y, 'red'), (wf_x, wf_y+32, 'red'), (w_frontu-wf_x, wf_y, 'red'), (w_frontu-wf_x, wf_y+32, 'red')]

for s in range(sekcje_do_gen):
    for sz in range(axis_ilosc):
        dodaj_element("Front Szuflady", w_frontu, h_frontu, 18, "Płyta 18mm", f"Sekcja {s+1}", otwory_front)
        dodaj_element("Dno Szuflady", dno_dl, dno_szer, 16, "Płyta 16mm", "Biała"); dodaj_element("Tył Szuflady", tyl_szer, tyl_wys, 16, "Płyta 16mm", "Biała")
        
if typ_plecow != "Brak":
    hdf_h = H_MEBLA - 4 if typ_plecow == "Nakładane" else H_MEBLA - 20
    hdf_w = W_MEBLA - 4 if typ_plecow == "Nakładane" else W_MEBLA - 20
    dodaj_element("Plecy HDF", hdf_w, hdf_h, 3, "HDF 3mm", typ_plecow)

# ==========================================
# 4. WYŚWIETLANIE
# ==========================================
df = pd.DataFrame(lista_elementow)
tab_lista, tab_rysunki, tab_szablon = st.tabs(["📋 LISTA ROZKROJU", "📐 PODGLĄD CAŁOŚCI", "🖨️ SZABLONY 1:1"])

with tab_lista:
    st.subheader(f"Projekt: {KOD_PROJEKTU} [{typ_frontu}]")
    st.dataframe(df.drop(columns=['typ', 'wiercenia']), use_container_width=True, hide_index=True)
    st.download_button("📥 Pobierz CSV", df.drop(columns=['typ', 'wiercenia']).to_csv(index=False).encode('utf-8'), "rozkroj.csv", "text/csv")

with tab_rysunki:
    ids = [x['ID'] for x in lista_elementow if x['wiercenia']]
    if ids:
        sel = st.selectbox("Wybierz element (Podgląd):", ids)
        it = next(x for x in lista_elementow if x['ID'] == sel)
        st.pyplot(rysuj_element(it['Szerokość [mm]'], it['Wysokość [mm]'], it['ID'], it['Nazwa'], it['wiercenia'], '#e6ccb3' if "18mm" in it['Materiał'] else '#f0f2f6'))

with tab_szablon:
    st.subheader("Generator Szablonów Wierceń (A4)")
    st.info("Pobierz PDF, wydrukuj w skali 100% i przyłóż do rogu płyty.")
    
    ids_szablon = [x['ID'] for x in lista_elementow if x['wiercenia']]
    if ids_szablon:
        sel_szablon = st.selectbox("Element do wiercenia:", ids_szablon, key="szablon_sel")
        it_s = next(x for x in lista_elementow if x['ID'] == sel_szablon)
        
        # Wybór narożnika
        naroznik = st.radio("Wybierz narożnik do szablonu:", ["Lewy-Dół (0,0)", "Lewy-Góra (0, H)"], horizontal=True)
        
        # Generowanie
        fig_a4 = rysuj_szablon_a4(it_s['Szerokość [mm]'], it_s['Wysokość [mm]'], it_s['ID'], it_s['wiercenia'], naroznik)
        st.pyplot(fig_a4)
        
        # Pobieranie
        pdf_buf = io.BytesIO()
        fig_a4.savefig(pdf_buf, format='pdf')
        pdf_buf.seek(0)
        
        st.download_button(
            label=f"📥 Pobierz SZABLON PDF ({naroznik})",
            data=pdf_buf,
            file_name=f"SZABLON_{it_s['ID']}_{naroznik}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
