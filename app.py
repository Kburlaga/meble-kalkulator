import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
from fpdf import FPDF
import io

st.set_page_config(page_title="STOLARZPRO - Kalkulator Meblowy", page_icon="🪚", layout="wide")

# ==========================================
# 1. FUNKCJA GENEROWANIA PDF
# ==========================================
def generuj_pdf(df, kod_projektu, wymiary_info):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    
    # Nagłówek
    pdf.cell(190, 10, f"STOLARZPRO - LISTA ROZKROJU", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(190, 10, f"Projekt: {kod_projektu}", ln=True, align='C')
    pdf.ln(5)
    
    # Dane projektu
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(190, 7, "Parametry szafki:", ln=True)
    pdf.set_font("Arial", '', 10)
    for k, v in wymiary_info.items():
        pdf.cell(190, 6, f"- {k}: {v}", ln=True)
    pdf.ln(10)
    
    # Tabela rozkroju
    pdf.set_font("Arial", 'B', 10)
    # Nagłówki tabeli
    cols = ["ID", "Nazwa", "Szer [mm]", "Wys [mm]", "Szt"]
    widths = [40, 60, 30, 30, 20]
    
    for i in range(len(cols)):
        pdf.cell(widths[i], 8, cols[i], border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', 9)
    # Grupowanie takich samych elementów
    df_sum = df.groupby(['Nazwa', 'Szerokość [mm]', 'Wysokość [mm]', 'Materiał']).size().reset_index(name='Szt')
    
    for _, row in df_sum.iterrows():
        pdf.cell(widths[0], 7, "EL", border=1) # Uproszczone ID
        pdf.cell(widths[1], 7, str(row['Nazwa']), border=1)
        pdf.cell(widths[2], 7, str(row['Szerokość [mm]']), border=1, align='C')
        pdf.cell(widths[3], 7, str(row['Wysokość [mm]']), border=1, align='C')
        pdf.cell(widths[4], 7, str(row['Szt']), border=1, align='C')
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1', 'replace')

# ==========================================
# 2. FUNKCJA RYSUJĄCA
# ==========================================
def rysuj_element(szer, wys, id_elementu, nazwa, otwory=[], kolor_tla='#e6ccb3'):
    fig, ax = plt.subplots(figsize=(6, 4))
    rect = patches.Rectangle((0, 0), szer, wys, linewidth=2, edgecolor='black', facecolor=kolor_tla)
    ax.add_patch(rect)
    
    for otw in otwory:
        x, y = otw[0], otw[1]
        kolor = otw[2] if len(otw) > 2 else 'red'
        circle = patches.Circle((x, y), radius=4, edgecolor=kolor, facecolor='white', linewidth=1.5)
        ax.add_patch(circle)
        if len(otwory) < 25:
            ax.text(x + 6, y + 2, f"({x:.1f}, {y:.1f})", fontsize=7, color=kolor, weight='bold')

    ax.set_xlim(-max(szer, wys)*0.1, szer + max(szer, wys)*0.1)
    ax.set_ylim(-max(szer, wys)*0.1, wys + max(szer, wys)*0.1)
    ax.set_aspect('equal')
    ax.set_title(f"{id_elementu} | {nazwa}", fontsize=12, weight='bold')
    ax.grid(True, linestyle='--', alpha=0.3)
    return fig

# ==========================================
# 3. INTERFEJS I LOGIKA
# ==========================================
with st.sidebar:
    st.title("🪚 STOLARZPRO")
    st.subheader("Twój Manager Rozkroju")
    st.divider()
    
    KOD_PROJEKTU = st.text_input("Nazwa Projektu", value="RTV-SALON").upper()
    
    with st.expander("📏 Wymiary Korpusu", expanded=True):
        H_MEBLA = st.number_input("Wysokość (mm)", value=600)
        W_MEBLA = st.number_input("Szerokość (mm)", value=1800)
        D_MEBLA = st.number_input("Głębokość (mm)", value=600)
        GR_PLYTY = st.number_input("Grubość płyty (mm)", value=18)

    with st.expander("🔨 Konstrukcja", expanded=True):
        typ_frontu = st.selectbox("Typ frontu", ["Nakładany", "Wpuszczany (Inset)"])
        ilosc_przegrod = st.number_input("Ilość przegród", value=2, min_value=0)
        typ_plecow = st.selectbox("Plecy (HDF)", ["Nakładane", "Wpuszczane", "Brak"])
        korekta_odbojnik = st.number_input("Miejsce na odbojnik (mm)", value=1.0, step=0.5)

    with st.expander("🗄️ Szuflady (GTV Axis Pro)", expanded=False):
        axis_fuga = st.number_input("Fuga (mm)", value=3.0)
        axis_ilosc = st.slider("Szuflady w sekcji", 1, 5, 2)
        axis_nl = st.selectbox("Długość (NL)", [450, 500, 550], index=1)

# --- Obliczenia ---
ilosc_sekcji = ilosc_przegrod + 1
szer_wew_total = W_MEBLA - (2 * GR_PLYTY) - (ilosc_przegrod * GR_PLYTY)
szer_wneki = szer_wew_total / ilosc_sekcji
wys_wew = H_MEBLA - (2 * GR_PLYTY)

# Offset prowadnicy X (Baza 37 + front jeśli wpuszczany + odbojnik)
base_x = 37.0
if typ_frontu == "Wpuszczany (Inset)":
    offset_x = base_x + GR_PLYTY + korekta_odbojnik
else:
    offset_x = base_x + korekta_odbojnik

# ==========================================
# 4. LISTA FORMATEK
# ==========================================
lista = []

def add_el(nazwa, w, h, gr, mat, wierc=[]):
    lista.append({"ID": f"{KOD_PROJEKTU}-{nazwa[:3].upper()}", "Nazwa": nazwa, "Szerokość [mm]": round(w, 1), "Wysokość [mm]": round(h, 1), "Grubość [mm]": gr, "Materiał": mat, "wiercenia": wierc})

# Wiercenia boku
h_frontu = (wys_wew - ((axis_ilosc + 1) * axis_fuga)) / axis_ilosc
otwory_bok = []
for i in range(axis_ilosc):
    y = (i * (h_frontu + axis_fuga)) + axis_fuga + 37.0
    otwory_bok.append((offset_x, y, 'red'))
    otwory_bok.append((offset_x + 224, y, 'red'))

# Elementy
add_el("Bok Lewy", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", otwory_bok)
add_el("Bok Prawy", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", otwory_bok)
add_el("Wieniec Górny", W_MEBLA, D_MEBLA, GR_PLYTY, "Płyta 18mm")
add_el("Wieniec Dolny", W_MEBLA, D_MEBLA, GR_PLYTY, "Płyta 18mm")

for _ in range(ilosc_przegrod):
    add_el("Przegroda", D_MEBLA, H_MEBLA - 2*GR_PLYTY, GR_PLYTY, "Płyta 18mm", otwory_bok)

for _ in range(ilosc_sekcji * axis_ilosc):
    add_el("Front Szuflady", szer_wneki - 2*axis_fuga, h_frontu, 18, "Front 18mm")

df = pd.DataFrame(lista)

# ==========================================
# 5. WIDOK GŁÓWNY
# ==========================================
st.header(f"Projekt: {KOD_PROJEKTU}")

c1, c2, c3 = st.columns(3)
c1.download_button("📥 Pobierz PDF do druku", data=generuj_pdf(df, KOD_PROJEKTU, {"Szerokość": W_MEBLA, "Wysokość": H_MEBLA, "Typ": typ_frontu}), file_name=f"{KOD_PROJEKTU}.pdf")
c2.download_button("📊 Eksportuj CSV (Excel)", data=df.drop(columns=['wiercenia']).to_csv(index=False), file_name=f"{KOD_PROJEKTU}.csv")
c3.button("🔄 Odśwież widok")

t1, t2 = st.tabs(["📋 Lista Formatek", "📐 Podgląd Wierceń"])

with t1:
    st.dataframe(df.drop(columns=['wiercenia']), use_container_width=True, hide_index=True)

with t2:
    wybor = st.selectbox("Wybierz element do podglądu:", [e['Nazwa'] for e in lista if e['wiercenia']])
    item = next(e for e in lista if e['Nazwa'] == wybor)
    st.pyplot(rysuj_element(item['Szerokość [mm]'], item['Wysokość [mm]'], item['ID'], item['Nazwa'], item['wiercenia']))
