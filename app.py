import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import io  # <--- To jest ta nowa część do obsługi plików

st.set_page_config(page_title="Kalkulator Meblowy V7 PDF", page_icon="🪚", layout="wide")

# ==========================================
# 1. FUNKCJA RYSUJĄCA
# ==========================================
def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], kolor_tla='#e6ccb3'):
    fig, ax = plt.subplots(figsize=(8, 5)) # Nieco większy rozmiar dla lepszej jakości PDF
    
    # Rysowanie płyty
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla)
    ax.add_patch(rect)
    
    # Rysowanie otworów
    for otw in otwory:
        x, y = otw[0], otw[1]
        kolor = otw[2] if len(otw) > 2 else 'red'
        # Rysujemy kółko
        circle = patches.Circle((x, y), radius=4, edgecolor=kolor, facecolor='white', linewidth=1.5)
        ax.add_patch(circle)
        
        # Etykieta przy otworze
        # Żeby rysunek był czytelny, tekst jest nieco przesunięty
        label = f"{x:.1f}" # Na rysunku podajemy głównie X (ważniejszy dla ustawienia maszyny)
        ax.text(x, y + 8, label, fontsize=8, color=kolor, weight='bold', ha='center', rotation=90)

    # Legenda
    if otwory:
        ax.text(0, -wys*0.2, "🔴 Czerwone: Prowadnice/Front  🔵 Niebieskie: Konfirmaty", fontsize=10)

    # Ustawienia osi
    margines = max(szer, wys) * 0.15
    ax.set_xlim(-margines, szer + margines)
    ax.set_ylim(-margines, wys + margines)
    ax.set_aspect('equal')
    
    # Tytuł
    ax.set_title(f"ID: {id_elementu}\n{nazwa}\n{szer:.1f} x {wys:.1f} mm", fontsize=14, weight='bold', pad=20)
    ax.set_xlabel("Szerokość (mm)")
    ax.set_ylabel("Wysokość (mm)")
    ax.grid(True, linestyle='--', alpha=0.5)
    
    # Zwracamy obiekt rysunku
    return fig

# ==========================================
# 2. BAZA DANYCH
# ==========================================
BAZA_SYSTEMOW = {
    "GTV Axis Pro": {
        "opis": "Pełny wysuw",
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

st.title("🪚 Manager Formatek (Eksport PDF)")

# ==========================================
# 3. PANEL BOCZNY
# ==========================================
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
# 4. LOGIKA OBLICZEŃ
# ==========================================
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

# --- OBLICZENIA ---
if typ_frontu == "Nakładane (Na korpus)":
    total_h_frontow = H_MEBLA - 4
    total_w_frontow = W_MEBLA - 4
    h_frontu = (total_h_frontow - ((axis_ilosc - 1) * axis_fuga)) / axis_ilosc
    w_frontu = (total_w_frontow - ((ilosc_sekcji - 1) * axis_fuga)) / ilosc_sekcji
    x_prowadnicy = params["offset_prowadnica"]
else:
    h_frontu = (wys_wewnetrzna - ((axis_ilosc + 1) * axis_fuga)) / axis_ilosc
    w_frontu = szer_jednej_wneki - (2 * axis_fuga)
    x_prowadnicy = params["offset_prowadnica"] + GR_PLYTY + 1

wiercenia_prowadnice = []
akt_h = 0 
for i in range(axis_ilosc):
    if typ_frontu == "Nakładane (Na korpus)":
        start_y = 2 + params["offset_prowadnica"] + akt_h
    else:
        start_y = GR_PLYTY + axis_fuga + params["offset_prowadnica"] + akt_h
    wiercenia_prowadnice.append(start_y)
    akt_h += h_frontu + axis_fuga

# --- GENEROWANIE ELEMENTÓW ---
otwory_bok = []
for y in wiercenia_prowadnice:
    otwory_bok.append((x_prowadnicy, y, 'red'))
    otwory_bok.append((x_prowadnicy + 224, y, 'red'))

dodaj_element("Bok Lewy", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", f"Sys: {typ_frontu}", otwory_bok)
dodaj_element("Bok Prawy", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", f"Sys: {typ_frontu}", otwory_bok)

otwory_wieniec = []
y_k1, y_k2 = 50, D_MEBLA - 50
otwory_wieniec.append((GR_PLYTY/2, y_k1, 'blue'))
otwory_wieniec.append((GR_PLYTY/2, y_k2, 'blue'))
otwory_wieniec.append((W_MEBLA - GR_PLYTY/2, y_k1, 'blue'))
otwory_wieniec.append((W_MEBLA - GR_PLYTY/2, y_k2, 'blue'))
curr_x = GR_PLYTY
for i in range(ilosc_przegrod):
    curr_x += szer_jednej_wneki
    otwory_wieniec.append((curr_x + GR_PLYTY/2, y_k1, 'blue'))
    otwory_wieniec.append((curr_x + GR_PLYTY/2, y_k2, 'blue'))
    curr_x += GR_PLYTY

dodaj_element("Wieniec Górny", W_MEBLA, D_MEBLA, GR_PLYTY, "Płyta 18mm", "Okleina dookoła", otwory_wieniec)
dodaj_element("Wieniec Dolny", W_MEBLA, D_MEBLA, GR_PLYTY, "Płyta 18mm", "Okleina dookoła", otwory_wieniec)

if ilosc_przegrod > 0:
    dodaj_element("Przegroda", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", "Wiercenia OBUSTRONNE", otwory_bok)

czy_wszystkie = st.sidebar.checkbox("Szuflady we wszystkich sekcjach", value=True)
sekcje_do_gen = ilosc_sekcji if czy_wszystkie else 1
dno_szer = szer_jednej_wneki - params["redukcja_dna_szer"]
dno_dl = axis_nl - params["redukcja_dna_dl"]
tyl_szer = szer_jednej_wneki - params["redukcja_tyl_szer"]
tyl_wys = params["wysokosci_tylu"][typ_boku_key]
wf_y = params["offset_front_y"]
wf_x = params["offset_front_x"] if typ_frontu == "Nakładane (Na korpus)" else params["offset_front_x"] - axis_fuga
otwory_front = [(wf_x, wf_y, 'red'), (wf_x, wf_y+32, 'red'), (w_frontu-wf_x, wf_y, 'red'), (w_frontu-wf_x, wf_y+32, 'red')]

for s in range(sekcje_do_gen):
    for sz in range(axis_ilosc):
        dodaj_element("Front Szuflady", w_frontu, h_frontu, 18, "Płyta 18mm", f"Sekcja {s+1}", otwory_front)
        dodaj_element("Dno Szuflady", dno_dl, dno_szer, 16, "Płyta 16mm", "Biała")
        dodaj_element("Tył Szuflady", tyl_szer, tyl_wys, 16, "Płyta 16mm", "Biała")
        
if typ_plecow != "Brak":
    hdf_h = H_MEBLA - 4 if typ_plecow == "Nakładane" else H_MEBLA - 20
    hdf_w = W_MEBLA - 4 if typ_plecow == "Nakładane" else W_MEBLA - 20
    dodaj_element("Plecy HDF", hdf_w, hdf_h, 3, "HDF 3mm", typ_plecow)

# --- WYŚWIETLANIE ---
df = pd.DataFrame(lista_elementow)
tab_lista, tab_rysunki = st.tabs(["📋 LISTA ROZKROJU", "📐 RYSUNKI / EKSPORT PDF"])

with tab_lista:
    st.subheader(f"Projekt: {KOD_PROJEKTU} [{typ_frontu}]")
    st.dataframe(df.drop(columns=['typ', 'wiercenia']), use_container_width=True, hide_index=True)
    st.download_button("📥 Pobierz CSV", df.drop(columns=['typ', 'wiercenia']).to_csv(index=False).encode('utf-8'), "rozkroj.csv", "text/csv")

with tab_rysunki:
    ids = [x['ID'] for x in lista_elementow if x['wiercenia']]
    if ids:
        sel = st.selectbox("Wybierz element do wygenerowania:", ids)
        it = next(x for x in lista_elementow if x['ID'] == sel)
        
        # Generujemy rysunek
        fig = rysuj_element(it['Szerokość [mm]'], it['Wysokość [mm]'], it['ID'], it['Nazwa'], it['wiercenia'], '#e6ccb3' if "18mm" in it['Materiał'] else '#f0f2f6')
        
        # Wyświetlamy na ekranie
        st.pyplot(fig)
        
        # --- SEKCJA POBIERANIA ---
        col_pdf, col_png = st.columns(2)
        
        # 1. Eksport PDF
        pdf_buffer = io.BytesIO()
        fig.savefig(pdf_buffer, format='pdf')
        pdf_buffer.seek(0)
        
        col_pdf.download_button(
            label="📥 Pobierz PDF (Druk)",
            data=pdf_buffer,
            file_name=f"{it['ID']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
        # 2. Eksport PNG
        png_buffer = io.BytesIO()
        fig.savefig(png_buffer, format='png', dpi=150) # dpi=150 dla lepszej jakości obrazka
        png_buffer.seek(0)
        
        col_png.download_button(
            label="🖼️ Pobierz PNG (Foto)",
            data=png_buffer,
            file_name=f"{it['ID']}.png",
            mime="image/png",
            use_container_width=True
        )
        
        st.markdown("---")
        st.write(f"**Szczegóły Wierceń (Tekstowo):**")
        for w in it['wiercenia']:
            st.code(f"X: {w[0]:.1f} | Y: {w[1]:.1f}  [{'Konfirmat' if w[2]=='blue' else 'Prowadnica'}]")
