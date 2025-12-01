import streamlit as st

st.set_page_config(page_title="Kalkulator Meblowy 2.0", page_icon="🪚")

# ==========================================
# 📚 BAZA DANYCH SYSTEMÓW (TU DODAJESZ NOWE)
# ==========================================
# Aby dodać nowy system, skopiuj klamry {} i wklej po przecinku.
BAZA_SYSTEMOW = {
    "GTV Axis Pro": {
        "opis": "Prowadnica z dociągiem, pełny wysuw",
        "offset_prowadnica": 37.5,      # Oś otworów w korpusie (standard)
        "offset_front_y": 47.5,         # Pierwszy otwór we froncie od dołu
        "offset_front_x": 15.5,         # Oś otworów od boku korpusu
        "redukcja_dna_szer": 75,        # LW - 75
        "redukcja_dna_dl": 24,          # NL - 24
        "redukcja_tyl_szer": 87,        # LW - 87
        # Wysokości tyłów dla wariantów A, B, C, D
        "wysokosci_tylu": {"A": 84, "B": 116, "C": 167, "D": 199}
    },
    "GTV Modern Box (Starszy)": {
        "opis": "Popularny szary system",
        "offset_prowadnica": 37.0,      # Inny standard!
        "offset_front_y": 45.0,
        "offset_front_x": 15.5,
        "redukcja_dna_szer": 75,
        "redukcja_dna_dl": 24,
        "redukcja_tyl_szer": 87,
        "wysokosci_tylu": {"A": 84, "B": 135, "C": 199, "D": 224}
    },
    "Blum Antaro (Przykładowy)": {
        "opis": "Standard Blum",
        "offset_prowadnica": 37.0,
        "offset_front_y": 45.5,         # Mocowanie na wkręty
        "offset_front_x": 15.5,
        "redukcja_dna_szer": 75,
        "redukcja_dna_dl": 24,
        "redukcja_tyl_szer": 87,
        "wysokosci_tylu": {"A": 83, "B": 115, "C": 167, "D": 200}
    }
}

st.title("🪚 Twój Projekt RTV 2.0")

# --- PANEL BOCZNY (USTAWIENIA) ---
with st.sidebar:
    st.header("1. Wymiary Szafki")
    H_MEBLA = st.number_input("Wysokość całkowita (mm)", value=600)
    W_MEBLA = st.number_input("Szerokość całkowita (mm)", value=1800)
    D_MEBLA = st.number_input("Głębokość całkowita (mm)", value=600)
    GR_PLYTY = st.number_input("Grubość płyty (mm)", value=18)
    
    st.header("2. Konstrukcja")
    ilosc_przegrod = st.number_input("Ilość przegród pionowych", value=2, min_value=0)
    
    # Obliczanie światła
    ilosc_sekcji = ilosc_przegrod + 1
    szer_wewnetrzna_total = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)
    szer_jednej_wneki = szer_wewnetrzna_total / ilosc_sekcji
    wys_wewnetrzna = H_MEBLA - (2 * GR_PLYTY)

    st.info(f"Światło wnęki: **{szer_jednej_wneki:.1f} mm**")

    st.divider()
    st.header("3. System Szuflad")
    
    # Wybór systemu z listy
    opcje_systemow = list(BAZA_SYSTEMOW.keys()) + ["🛠️ Własny / Testowy"]
    wybrany_nazwa = st.selectbox("Wybierz system szuflad:", opcje_systemow)
    
    # Logika ładowania danych
    params = {}
    
    if wybrany_nazwa == "🛠️ Własny / Testowy":
        st.warning("Tryb ręczny - wpisz dane z karty technicznej")
        params["offset_prowadnica"] = st.number_input("Oś prowadnicy w korpusie (mm)", value=37.5)
        params["offset_front_y"] = st.number_input("Oś frontu od dołu (mm)", value=47.5)
        params["offset_front_x"] = st.number_input("Oś frontu od boku (mm)", value=15.5)
        params["redukcja_dna_szer"] = st.number_input("Redukcja dna szerokość (LW minus ?)", value=75)
        params["redukcja_dna_dl"] = st.number_input("Redukcja dna długość (NL minus ?)", value=24)
        params["redukcja_tyl_szer"] = st.number_input("Redukcja tyłu szerokość (LW minus ?)", value=87)
        # Dla trybu własnego upraszczamy wysokość tyłu do jednego pola
        tyl_custom = st.number_input("Wysokość ścianki tylnej (mm)", value=167)
        params["wysokosci_tylu"] = {"Custom": tyl_custom}
        typ_boku_key = "Custom" # Klucz do mapy
        
    else:
        # Ładujemy z bazy
        params = BAZA_SYSTEMOW[wybrany_nazwa]
        st.caption(f"ℹ️ {params['opis']}")
        # Wybór wysokości boku dostępnej w danym systemie
        dostepne_boki = list(params["wysokosci_tylu"].keys())
        typ_boku_key = st.selectbox("Wysokość boku", dostepne_boki, index=len(dostepne_boki)-1)

    # Wspólne ustawienia dla wszystkich
    st.subheader("Konfiguracja")
    axis_fuga = st.number_input("Fuga między frontami (mm)", value=3.0, step=0.5)
    axis_ilosc = st.slider("Ile szuflad w sekcji?", 2, 5, 2)
    axis_nl = st.selectbox("Długość prowadnicy (NL)", [300, 350, 400, 450, 500, 550], index=4)


# --- ZAKŁADKI GŁÓWNE ---
tab_korpus, tab_szuflady = st.tabs(["📦 KORPUS", "🗄️ SZUFLADY"])

# === ZAKŁADKA 1: KORPUS ===
with tab_korpus:
    st.subheader("Rozkrój Płyty na Szafkę")
    wieniec_dl = W_MEBLA
    wieniec_szer = D_MEBLA
    bok_wys = H_MEBLA - (2 * GR_PLYTY)
    bok_szer = D_MEBLA
    
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**Wieńce (Góra/Dół)**: 2 szt.")
        st.code(f"{wieniec_dl} x {wieniec_szer} mm")
        st.write(f"**Boki (Zewn)**: 2 szt.")
        st.code(f"{bok_wys} x {bok_szer} mm")
    with c2:
        if ilosc_przegrod > 0:
            st.write(f"**Przegrody**: {ilosc_przegrod} szt.")
            st.code(f"{bok_wys} x {bok_szer} mm")
    
    st.caption("Pamiętaj o plecach (HDF) - wymiar zależy od sposobu montażu (nut vs gwoździe).")

# === ZAKŁADKA 2: SZUFLADY ===
with tab_szuflady:
    st.subheader(f"System: {wybrany_nazwa}")
    st.write(f"Dla wnęki szerokości: **{szer_jednej_wneki:.1f} mm**")
    
    # 1. Obliczenia Frontów
    h_frontu = (wys_wewnetrzna - ((axis_ilosc + 1) * axis_fuga)) / axis_ilosc
    w_frontu = szer_jednej_wneki - (2 * axis_fuga)
    
    # 2. Obliczenia Formatek Wnętrza (Dynamiczne!)
    dno_szer = szer_jednej_wneki - params["redukcja_dna_szer"]
    dno_dl = axis_nl - params["redukcja_dna_dl"]
    tyl_szer = szer_jednej_wneki - params["redukcja_tyl_szer"]
    tyl_wys = params["wysokosci_tylu"][typ_boku_key]

    # 3. Obliczenia Wierceń
    wiercenia_korpus = []
    akt_wys = 0
    for i in range(axis_ilosc):
        # Tutaj kluczowa zmiana: pobieramy offset z params!
        pos = akt_wys + axis_fuga + params["offset_prowadnica"]
        wiercenia_korpus.append(pos)
        akt_wys += axis_fuga + h_frontu
    
    wiercenie_front_y = params["offset_front_y"]
    wiercenie_front_x = params["offset_front_x"] - axis_fuga

    # --- WYNIKI ---
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.success("**FRONTY (18mm)**")
        st.write(f"Wymiar: **{h_frontu:.1f} x {w_frontu:.1f}** mm")
        st.write(f"Ilość: {axis_ilosc} szt.")
        st.markdown("---")
        st.info("**WIERCENIE FRONTU**")
        st.write(f"Od dołu: **{wiercenie_front_y} mm**")
        st.write(f"Od boku: **{wiercenie_front_x:.1f} mm**")
        
    with c2:
        st.warning("**DNO I TYŁ (16mm)**")
        st.write(f"Dno: **{dno_dl} x {dno_szer:.1f}** mm")
        st.write(f"Tył: **{tyl_wys} x {tyl_szer:.1f}** mm")
        st.markdown("---")
        st.error("**PROWADNICE (W KORPUSIE)**")
        st.caption("Mierzone od dna wnęki w górę")
        for idx, w in enumerate(wiercenia_korpus):
            st.write(f"Szuflada {idx+1}: **{w:.1f} mm**")
