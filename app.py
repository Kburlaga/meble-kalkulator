import streamlit as st

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Kalkulator Axis Pro", page_icon="🪚")

st.title("🪚 Kalkulator Meblarski")
st.header("System GTV Axis Pro (Podniesiony)")

# --- 1. PANEL BOCZNY (USTAWIENIA) ---
with st.sidebar:
    st.subheader("Wymiary Wnęki (mm)")
    h_wneki = st.number_input("Wysokość wnęki (bez wieńców)", value=564, step=1)
    w_wneki = st.number_input("Szerokość wnęki (wewnątrz)", value=564, step=1)
    
    st.subheader("Konfiguracja")
    ilosc_szuflad = st.slider("Liczba szuflad", min_value=2, max_value=5, value=2)
    fuga = st.number_input("Fuga (szczelina)", value=3.0, step=0.5)
    
    st.subheader("Szuflada")
    typ_boku = st.selectbox("Wysokość boku", ["A (Niski)", "B (Średni)", "C (Wysoki)", "D (b. Wysoki)"], index=2)
    dl_prowadnicy = st.selectbox("Długość prowadnicy", [300, 350, 400, 450, 500, 550], index=4)

# --- 2. LOGIKA (Twoja funkcja) ---
# Mapowanie literek z selectboxa na kod
typ_boku_kod = typ_boku[0] # Bierze pierwszą literę np. "C"

# Stałe systemowe
AXIS_OFFSET_PROWADNICA = 37.5
AXIS_OFFSET_FRONT_Y = 47.5
AXIS_OFFSET_FRONT_X_BASE = 15.5
REDUKCJA_DNA_SZER = 75
REDUKCJA_DNA_DL = 24
REDUKCJA_TYL_SZER = 87
wysokosci_tylu = {"A": 84, "B": 116, "C": 167, "D": 199}
h_tylu = wysokosci_tylu.get(typ_boku_kod, 167)

# Obliczenia
suma_fug = (ilosc_szuflad + 1) * fuga
h_frontu = (h_wneki - suma_fug) / ilosc_szuflad
w_frontu = w_wneki - (2 * fuga)

# Prowadnice
pozycje_prowadnic = []
aktualna_wysokosc = 0
for i in range(ilosc_szuflad):
    pos = aktualna_wysokosc + fuga + AXIS_OFFSET_PROWADNICA
    pozycje_prowadnic.append(round(pos, 1))
    aktualna_wysokosc += fuga + h_frontu

# Mocowania frontu
mocowanie_front_y = AXIS_OFFSET_FRONT_Y
mocowanie_front_x = AXIS_OFFSET_FRONT_X_BASE - fuga

# Formatki
dno_szer = w_wneki - REDUKCJA_DNA_SZER
dno_dl = dl_prowadnicy - REDUKCJA_DNA_DL
tyl_szer = w_wneki - REDUKCJA_TYL_SZER

# --- 3. WYNIKI NA EKRANIE ---
st.success(f"Gotowe! Fronty: {h_frontu:.1f} x {w_frontu:.1f} mm")

tab1, tab2, tab3 = st.tabs(["📏 Formatki", "🔨 Wiercenie Korpus", "🎯 Wiercenie Front"])

with tab1:
    st.subheader("Formatki do zamówienia")
    col1, col2 = st.columns(2)
    with col1:
        st.info("**Fronty (18mm)**")
        st.write(f"Ilość: {ilosc_szuflad} szt.")
        st.write(f"Wymiar: **{h_frontu:.1f} x {w_frontu:.1f}** mm")
    with col2:
        st.warning("**Dno i Tył (16mm)**")
        st.write(f"Dno: **{dno_dl} x {dno_szer}** mm")
        st.write(f"Tył: **{h_tylu} x {tyl_szer}** mm")

with tab2:
    st.subheader("Wiercenie w boku szafki")
    st.caption("Mierzone od wewnętrznego dna szafki w górę")
    for idx, pos in enumerate(pozycje_prowadnic):
        st.write(f"📍 **Szuflada {idx+1}:** oś na wysokości **{pos} mm**")

with tab3:
    st.subheader("Wiercenie we froncie")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Od dołu frontu", f"{mocowanie_front_y} mm")
    with col2:
        st.metric("Od boku frontu", f"{mocowanie_front_x} mm")
    st.image("https://www.gtv.com.pl/images/produkty/akcesoria/szuflady/axis-pro/axis-pro-rys-tech-1.jpg", caption="Schemat poglądowy")
