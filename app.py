import streamlit as st

st.set_page_config(page_title="Kalkulator Meblowy", page_icon="🪚")

st.title("🪚 Twój Projekt RTV")

# --- PANEL BOCZNY (USTAWIENIA GŁÓWNE) ---
with st.sidebar:
    st.header("1. Wymiary Szafki (Zewnętrzne)")
    H_MEBLA = st.number_input("Wysokość całkowita (mm)", value=600)
    W_MEBLA = st.number_input("Szerokość całkowita (mm)", value=1800)
    D_MEBLA = st.number_input("Głębokość całkowita (mm)", value=600)
    GR_PLYTY = st.number_input("Grubość płyty (mm)", value=18)
    
    st.header("2. Konstrukcja")
    typ_plecow = st.selectbox("Plecy (HDF 3mm)", ["Wpuszczane (Nut)", "Nakładane (HDF przybijany)", "Brak / Płyta 18mm"])
    ilosc_przegrod = st.number_input("Ilość przegród pionowych", value=2, min_value=0)
    
    # Obliczanie światła dla szuflad
    # Zakładamy równe sekcje
    ilosc_sekcji = ilosc_przegrod + 1
    szer_wewnetrzna_total = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)
    szer_jednej_wneki = szer_wewnetrzna_total / ilosc_sekcji
    wys_wewnetrzna = H_MEBLA - (2 * GR_PLYTY)

    st.info(f"📏 Wychodzi {ilosc_sekcji} sekcje po ok. **{szer_jednej_wneki:.1f} mm** szerokości wewnątrz.")

    st.header("3. Konfiguracja Szuflad (Axis)")
    # Te dane idą do drugiej zakładki
    axis_fuga = st.number_input("Fuga frontów (mm)", value=3.0, step=0.5)
    axis_ilosc = st.slider("Ile szuflad w JEDNEJ sekcji?", 2, 5, 2)
    axis_bok = st.selectbox("Wysokość boku Axis", ["A (Niski)", "B (Średni)", "C (Wysoki)", "D (b. Wysoki)"], index=2)
    axis_nl = st.selectbox("Długość prowadnicy", [300, 350, 400, 450, 500, 550], index=4)


# --- ZAKŁADKI GŁÓWNE ---
tab_korpus, tab_szuflady = st.tabs(["📦 KORPUS (Formatki)", "🗄️ SZUFLADY (Axis Pro)"])

# === ZAKŁADKA 1: KORPUS ===
with tab_korpus:
    st.subheader("Rozkrój Płyty na Szafkę")
    
    # Logika Korpusu (Wieńce nakładane na boki - standard RTV)
    wieniec_dl = W_MEBLA
    wieniec_szer = D_MEBLA
    
    bok_wys = H_MEBLA - (2 * GR_PLYTY)
    bok_szer = D_MEBLA # Domyślnie
    
    przegroda_wys = bok_wys
    przegroda_szer = D_MEBLA # Domyślnie
    
    # Korekta na plecy
    komentarz_plecy = ""
    hdf_wys = H_MEBLA - 4 # Minus po 2mm na stronę
    hdf_szer = W_MEBLA - 4
    
    if typ_plecow == "Wpuszczane (Nut)":
        # Jeśli nutowanie, to przegrody i półki są często cofnięte, 
        # ale boki zostają głębokie. Tu zależy od szkoły.
        # Przyjmijmy wersję prostą: boki pełne, HDF w rowku.
        komentarz_plecy = "Pamiętaj o nucie (rowku) na HDF w wieńcach i bokach! (zazwyczaj 10-12mm od tyłu)"
        hdf_wys = H_MEBLA - 20 # Wchodzi w rowek, ale mniejszy niż gabaryt
        hdf_szer = W_MEBLA - 20
        
    elif typ_plecow == "Nakładane (HDF przybijany)":
        # Wtedy środek często cofa się o grubość HDF (3mm) żeby nie wystawało, 
        # albo HDF przybija się na płasko.
        # Przyjmijmy standard: korpus ma głębokość X, HDF dochodzi z tyłu.
        pass

    # Tabela Formatek Korpusu
    st.markdown("### 🪵 Płyta Meblowa 18mm")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**1. Wieńce (Góra/Dół)**")
        st.write(f"Ilość: 2 szt.")
        st.code(f"{wieniec_dl} x {wieniec_szer} mm")

        st.write(f"**2. Boki (Zewnętrzne)**")
        st.write(f"Ilość: 2 szt.")
        st.code(f"{bok_wys} x {bok_szer} mm")
        
    with col2:
        if ilosc_przegrod > 0:
            st.write(f"**3. Przegrody Pionowe**")
            st.write(f"Ilość: {ilosc_przegrod} szt.")
            st.code(f"{przegroda_wys} x {przegroda_szer} mm")
        else:
            st.write("Brak przegród")

    st.markdown("### 🔨 Plecy (HDF 3mm)")
    st.write(f"Wymiar orientacyjny: **{hdf_wys} x {hdf_szer} mm**")
    if komentarz_plecy:
        st.caption(f"ℹ️ {komentarz_plecy}")


# === ZAKŁADKA 2: SZUFLADY ===
with tab_szuflady:
    st.subheader(f"Szuflady dla wnęki: {szer_jednej_wneki:.1f} mm")
    
    # Stałe Axis Pro
    AXIS_OFFSET_PROWADNICA = 37.5
    AXIS_OFFSET_FRONT_Y = 47.5
    AXIS_OFFSET_FRONT_X_BASE = 15.5
    REDUKCJA_DNA_SZER = 75
    REDUKCJA_DNA_DL = 24
    REDUKCJA_TYL_SZER = 87
    mapa_tyl = {"A": 84, "B": 116, "C": 167, "D": 199}
    
    # Obliczenia
    h_frontu = (wys_wewnetrzna - ((axis_ilosc + 1) * axis_fuga)) / axis_ilosc
    w_frontu = szer_jednej_wneki - (2 * axis_fuga)
    
    # Formatki szuflady
    dno_szer = szer_jednej_wneki - REDUKCJA_DNA_SZER
    dno_dl = axis_nl - REDUKCJA_DNA_DL
    tyl_szer = szer_jednej_wneki - REDUKCJA_TYL_SZER
    tyl_wys = mapa_tyl.get(axis_bok[0], 167)

    # Wiercenie
    wiercenia = []
    akt_wys = 0
    for i in range(axis_ilosc):
        pos = akt_wys + axis_fuga + AXIS_OFFSET_PROWADNICA
        wiercenia.append(pos)
        akt_wys += axis_fuga + h_frontu
    
    wiercenie_front_y = AXIS_OFFSET_FRONT_Y
    wiercenie_front_x = AXIS_OFFSET_FRONT_X_BASE - axis_fuga

    # Wyświetlanie
    c1, c2 = st.columns(2)
    with c1:
        st.success("**Fronty (Płyta 18mm)**")
        st.write(f"Wymiar: **{h_frontu:.1f} x {w_frontu:.1f}** mm")
        st.write(f"Ilość (na 1 sekcję): {axis_ilosc} szt.")
        
    with c2:
        st.warning("**Dno i Tył (Płyta 16mm)**")
        st.write(f"Dno: **{dno_dl} x {dno_szer:.1f}** mm")
        st.write(f"Tył: **{tyl_wys} x {tyl_szer:.1f}** mm")
        
    st.divider()
    st.markdown("**📍 Wiercenie Korpus (od dołu wnęki):**")
    for idx, w in enumerate(wiercenia):
        st.write(f"- Szuflada {idx+1}: oś otworu na **{w:.1f} mm**")
        
    st.markdown("**📍 Wiercenie Front:**")
    st.write(f"- Od dołu: **{wiercenie_front_y} mm**")
    st.write(f"- Od boku: **{wiercenie_front_x:.1f} mm**")
