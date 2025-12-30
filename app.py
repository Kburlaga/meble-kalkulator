import streamlit as st
import pandas as pd
import tempfile

from constants import *
from validation import validate_korpus
from model import Korpus
from drawings import rysuj_element, rysuj_podglad_mebla
from export_pdf import export_pdf
from export_cnc import export_cnc

st.set_page_config(page_title="STOLARZPRO - V18.2", page_icon="🪚", layout="wide")

# ==========================================
# 0. RESETOWANIE
# ==========================================
def resetuj_projekt():
    defaults = {
        'kod_pro': "RTV-PRO-2D",
        'h_mebla': 600,
        'w_mebla': 1800,
        'd_mebla': 600,
        'gr_plyty': 18,
        'il_przegrod': 2,
        'typ_plecow': "Nakładane",
        'sys_szuflad': "GTV Axis Pro",
        'typ_boku': "C",
        'fuga': 3.0,
        'nl': 500,
        'arkusz_w': 2800,
        'arkusz_h': 2070,
        'rzaz': 4
    }
    for k, v in defaults.items():
        st.session_state[k] = v
    st.session_state['pdf_ready'] = None

if 'kod_pro' not in st.session_state:
    resetuj_projekt()

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.title("🪚 STOLARZPRO V18.2")
    if st.button("🗑️ RESET", type="primary", use_container_width=True):
        resetuj_projekt()
        st.rerun()

    st.header("1. Gabaryty")
    KOD_PROJEKTU = st.text_input("Nazwa", key='kod_pro').upper()
    H_MEBLA = st.number_input("Wys.", key='h_mebla')
    W_MEBLA = st.number_input("Szer.", key='w_mebla')
    D_MEBLA = st.number_input("Głęb.", key='d_mebla')
    GR_PLYTY = st.number_input("Grubość", key='gr_plyty')

    st.header("2. Wnętrze")
    ilosc_przegrod = st.number_input("Przegrody", min_value=0, key='il_przegrod')
    ilosc_sekcji = ilosc_przegrod + 1
    konfiguracja = []

    for i in range(ilosc_sekcji):
        with st.expander(f"Sekcja {i+1}", expanded=True):
            typ = st.selectbox(f"Typ #{i+1}", ["Szuflady", "Półka", "Pusta"], key=f"typ_{i}")
            det = {'typ': typ, 'ilosc': 0}
            if typ == "Szuflady":
                det['ilosc'] = st.number_input(f"Ilość #{i+1}", 1, 5, 2, key=f"ile_{i}")
            elif typ == "Półka":
                det['ilosc'] = st.number_input(f"Ile półek? #{i+1}", 1, 10, 1, key=f"ile_p_{i}")
            konfiguracja.append(det)

# ==========================================
# WALIDACJA
# ==========================================
validate_korpus(W_MEBLA, H_MEBLA, D_MEBLA, GR_PLYTY, ilosc_przegrod)

# ==========================================
# BUDOWA KORPUSU
# ==========================================
korpus = Korpus(KOD_PROJEKTU, W_MEBLA, H_MEBLA, D_MEBLA, GR_PLYTY, ilosc_przegrod)
korpus.buduj_korpus()
korpus.buduj_wnetrze(konfiguracja)

# ==========================================
# OBLICZENIE SZEROKOŚCI JEDNEJ WNĘKI (zabezpieczenie dzielenia przez zero)
# ==========================================
if ilosc_sekcji > 0:
    szer_jednej_wneki = (W_MEBLA - 2*GR_PLYTY - ilosc_przegrod*GR_PLYTY)/ilosc_sekcji
else:
    szer_jednej_wneki = 0

# ==========================================
# TABS
# ==========================================
tabs = st.tabs(["📋 LISTA", "📐 RYSUNKI", "🗺️ ROZKRÓJ", "👁️ WIZUALIZACJA 2D"])

# ---- LISTA ELEMENTÓW ----
with tabs[0]:
    st.subheader("Lista elementów")
    df = pd.DataFrame([{
        "ID": e.id,
        "Nazwa": e.nazwa,
        "Szerokość [mm]": e.szer,
        "Wysokość [mm]": e.wys,
        "Grubość [mm]": e.gr,
        "Uwagi": e.uwagi
    } for e in korpus.elementy])
    st.dataframe(df, use_container_width=True)

    st.write("---")
    # PDF i CSV
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📄 Eksport PDF"):
            tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            export_pdf(korpus, tmp_pdf.name)
            st.download_button("📄 Pobierz PDF", data=open(tmp_pdf.name, "rb").read(), file_name=f"{KOD_PROJEKTU}.pdf")
    with col2:
        if st.button("💻 Eksport CNC (CSV)"):
            tmp_csv = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
            export_cnc(korpus, tmp_csv.name)
            st.download_button("💻 Pobierz CSV", data=open(tmp_csv.name, "rb").read(), file_name=f"{KOD_PROJEKTU}.csv")

# ---- RYSUNKI ----
with tabs[1]:
    st.info("Wybierz element z listy, aby zobaczyć wiercenia (dostępne dla boków/przegród).")

# ---- ROZKRÓJ ----
with tabs[2]:
    st.info("Moduł rozkroju w przygotowaniu.")

# ---- PODGLĄD 2D ----
with tabs[3]:
    st.subheader("Podgląd frontowy szafki")
    fig = rysuj_podglad_mebla(W_MEBLA, H_MEBLA, GR_PLYTY, konfiguracja, szer_jednej_wneki)
    st.pyplot(fig)
