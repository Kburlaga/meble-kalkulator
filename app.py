import streamlit as st
import pandas as pd
import tempfile
import io
from dataclasses import dataclass
from typing import List, Dict
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

# ==========================================
# CONSTANTS
# ==========================================
SYSTEMY_SZUFLAD = ["GTV Axis Pro", "Blum Tandembox", "Hettich ArciTech"]
TYPY_PLECOW = ["Nakładane", "Wpuszczane", "Brak"]
TYPY_BOKU = ["A", "B", "C"]

# ==========================================
# DATA CLASSES
# ==========================================
@dataclass
class Element:
    id: int
    nazwa: str
    szer: float
    wys: float
    gr: float
    uwagi: str = ""
    
    def __post_init__(self):
        self.szer = round(self.szer, 1)
        self.wys = round(self.wys, 1)
        self.gr = round(self.gr, 1)

# ==========================================
# KORPUS CLASS
# ==========================================
class Korpus:
    def __init__(self, kod: str, szer: float, wys: float, gleb: float, gr: float, przegrody: int):
        self.kod = kod
        self.szer = szer
        self.wys = wys
        self.gleb = gleb
        self.gr = gr
        self.przegrody = przegrody
        self.elementy: List[Element] = []
        self.counter = 1
        
    def dodaj_element(self, nazwa: str, szer: float, wys: float, gr: float, uwagi: str = ""):
        elem = Element(self.counter, nazwa, szer, wys, gr, uwagi)
        self.elementy.append(elem)
        self.counter += 1
        return elem
        
    def buduj_korpus(self):
        """Tworzy podstawowe elementy korpusu"""
        # Boki (2 szt)
        bok_wys = self.wys
        bok_gleb = self.gleb
        for i in range(2):
            self.dodaj_element(
                f"Bok {i+1}",
                bok_gleb,
                bok_wys,
                self.gr,
                "Wiercenia pod półki/przegrody"
            )
        
        # Górna i dolna płyta
        plyty_szer = self.szer - 2 * self.gr
        for nazwa in ["Górna płyta", "Dolna płyta"]:
            self.dodaj_element(
                nazwa,
                plyty_szer,
                self.gleb,
                self.gr,
                "Korpus"
            )
        
        # Przegrody pionowe
        przegroda_wys = self.wys - 2 * self.gr
        for i in range(self.przegrody):
            self.dodaj_element(
                f"Przegroda {i+1}",
                self.gleb,
                przegroda_wys,
                self.gr,
                "Wiercenia pod półki"
            )
        
        # Plecy (opcjonalne)
        plecy_szer = self.szer - 2 * self.gr
        plecy_wys = self.wys - 2 * self.gr
        self.dodaj_element(
            "Plecy HDF",
            plecy_szer,
            plecy_wys,
            3,
            "HDF 3mm"
        )
    
    def buduj_wnetrze(self, konfiguracja: List[Dict]):
        """Dodaje wewnętrzne elementy według konfiguracji"""
        ilosc_sekcji = len(konfiguracja)
        if ilosc_sekcji == 0:
            return
            
        # Szerokość jednej sekcji
        szer_sekcji = (self.szer - 2*self.gr - self.przegrody*self.gr) / ilosc_sekcji
        
        for i, sekcja in enumerate(konfiguracja):
            typ = sekcja['typ']
            ilosc = sekcja.get('ilosc', 0)
            
            if typ == "Półka" and ilosc > 0:
                for j in range(ilosc):
                    self.dodaj_element(
                        f"Półka S{i+1}_{j+1}",
                        szer_sekcji - 1,  # luz 1mm
                        self.gleb - 50,   # cofnięta o 50mm
                        self.gr,
                        f"Sekcja {i+1}"
                    )
            
            elif typ == "Szuflady" and ilosc > 0:
                wys_dostepna = self.wys - 2*self.gr - 20  # odstęp
                wys_frontu = (wys_dostepna - (ilosc-1)*3) / ilosc  # 3mm fuga
                
                for j in range(ilosc):
                    # Front szuflady
                    self.dodaj_element(
                        f"Front szuflady S{i+1}_{j+1}",
                        szer_sekcji - 3,
                        wys_frontu,
                        self.gr,
                        f"Szuflada {j+1} w sekcji {i+1}"
                    )
                    
                    # Dno szuflady
                    self.dodaj_element(
                        f"Dno szuflady S{i+1}_{j+1}",
                        szer_sekcji - 100,  # prowadnice
                        self.gleb - 100,
                        self.gr,
                        "Dno"
                    )

# ==========================================
# VALIDATION
# ==========================================
def validate_korpus(szer: float, wys: float, gleb: float, gr: float, przegrody: int):
    """Walidacja wymiarów korpusu"""
    errors = []
    
    if szer < 200 or szer > 3000:
        errors.append("Szerokość musi być między 200-3000mm")
    if wys < 200 or wys > 2500:
        errors.append("Wysokość musi być między 200-2500mm")
    if gleb < 200 or gleb > 800:
        errors.append("Głębokość musi być między 200-800mm")
    if gr not in [16, 18, 25]:
        errors.append("Grubość musi wynosić 16, 18 lub 25mm")
    if przegrody < 0 or przegrody > 10:
        errors.append("Liczba przegród: 0-10")
    
    # Sprawdź czy jest miejsce na przegrody
    min_szer_sekcji = 200
    wymagana_szer = (przegrody + 1) * min_szer_sekcji + przegrody * gr + 2 * gr
    if szer < wymagana_szer:
        errors.append(f"Za wąska szafka na {przegrody} przegród. Min. szerokość: {wymagana_szer}mm")
    
    if errors:
        for err in errors:
            st.error(err)
        return False
    return True

# ==========================================
# EXPORT PDF
# ==========================================
def export_pdf(korpus: Korpus, filename: str):
    """Eksportuje listę elementów do PDF"""
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    
    # Nagłówek
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, f"STOLARZPRO - Projekt: {korpus.kod}")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Wymiary: {korpus.szer} x {korpus.wys} x {korpus.gleb} mm")
    
    # Tabela
    y = height - 120
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y, "ID")
    c.drawString(80, y, "Nazwa")
    c.drawString(250, y, "Szerokość")
    c.drawString(330, y, "Wysokość")
    c.drawString(410, y, "Grubość")
    
    y -= 20
    c.setFont("Helvetica", 8)
    
    for elem in korpus.elementy:
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 8)
        
        c.drawString(50, y, str(elem.id))
        c.drawString(80, y, elem.nazwa[:30])
        c.drawString(250, y, f"{elem.szer:.1f} mm")
        c.drawString(330, y, f"{elem.wys:.1f} mm")
        c.drawString(410, y, f"{elem.gr:.1f} mm")
        y -= 15
    
    c.save()

# ==========================================
# EXPORT CNC
# ==========================================
def export_cnc(korpus: Korpus, filename: str):
    """Eksportuje do formatu CSV dla CNC"""
    df = pd.DataFrame([{
        "ID": e.id,
        "Nazwa": e.nazwa,
        "Dlugosc": e.szer,
        "Szerokosc": e.wys,
        "Grubosc": e.gr,
        "Ilosc": 1,
        "Material": "Płyta",
        "Uwagi": e.uwagi
    } for e in korpus.elementy])
    
    df.to_csv(filename, index=False, encoding='utf-8-sig', sep=';')

# ==========================================
# RYSUNKI
# ==========================================
def rysuj_podglad_mebla(szer: float, wys: float, gr: float, konfiguracja: List[Dict], szer_sekcji: float):
    """Rysuje prosty podgląd frontowy szafki"""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Skala
    scale = min(10/szer, 8/wys) * 800
    
    # Korpus
    korpus_rect = patches.Rectangle(
        (0, 0), szer, wys,
        linewidth=2, edgecolor='black', facecolor='wheat', alpha=0.3
    )
    ax.add_patch(korpus_rect)
    
    # Boki
    for x in [0, szer-gr]:
        bok = patches.Rectangle(
            (x, 0), gr, wys,
            linewidth=1, edgecolor='black', facecolor='saddlebrown', alpha=0.6
        )
        ax.add_patch(bok)
    
    # Górna i dolna płyta
    for y in [0, wys-gr]:
        plyta = patches.Rectangle(
            (gr, y), szer-2*gr, gr,
            linewidth=1, edgecolor='black', facecolor='saddlebrown', alpha=0.6
        )
        ax.add_patch(plyta)
    
    # Przegrody
    ilosc_sekcji = len(konfiguracja)
    if ilosc_sekcji > 1:
        for i in range(1, ilosc_sekcji):
            x = gr + i * (szer_sekcji + gr)
            przegroda = patches.Rectangle(
                (x, gr), gr, wys-2*gr,
                linewidth=1, edgecolor='black', facecolor='saddlebrown', alpha=0.6
            )
            ax.add_patch(przegroda)
    
    # Szuflady i półki
    for i, sekcja in enumerate(konfiguracja):
        x_start = gr + i * (szer_sekcji + gr)
        typ = sekcja['typ']
        ilosc = sekcja.get('ilosc', 0)
        
        if typ == "Szuflady" and ilosc > 0:
            wys_dostepna = wys - 2*gr - 20
            wys_frontu = (wys_dostepna - (ilosc-1)*3) / ilosc
            
            for j in range(ilosc):
                y = gr + 10 + j * (wys_frontu + 3)
                szuflada = patches.Rectangle(
                    (x_start + 1.5, y), szer_sekcji - 3, wys_frontu,
                    linewidth=1.5, edgecolor='darkblue', facecolor='lightblue', alpha=0.5
                )
                ax.add_patch(szuflada)
                
                # Uchwyt
                uch_y = y + wys_frontu/2
                ax.plot([x_start + szer_sekcji/2 - 30, x_start + szer_sekcji/2 + 30],
                       [uch_y, uch_y], 'k-', linewidth=3)
        
        elif typ == "Półka" and ilosc > 0:
            wys_dostepna = wys - 2*gr
            odstep = wys_dostepna / (ilosc + 1)
            
            for j in range(ilosc):
                y = gr + (j+1) * odstep
                ax.plot([x_start + 5, x_start + szer_sekcji - 5],
                       [y, y], 'brown', linewidth=2, linestyle='--')
    
    ax.set_xlim(-50, szer + 50)
    ax.set_ylim(-50, wys + 50)
    ax.set_aspect('equal')
    ax.set_xlabel('Szerokość [mm]')
    ax.set_ylabel('Wysokość [mm]')
    ax.set_title('Podgląd frontowy szafki')
    ax.grid(True, alpha=0.3)
    
    return fig

# ==========================================
# STREAMLIT APP
# ==========================================
st.set_page_config(page_title="STOLARZPRO - V18.2", page_icon="🪚", layout="wide")

def resetuj_projekt():
    """Resetuje wszystkie wartości do domyślnych"""
    defaults = {
        'kod_pro': "RTV-PRO-2D",
        'h_mebla': 600,
        'w_mebla': 1800,
        'd_mebla': 600,
        'gr_plyty': 18,
        'il_przegrod': 2,
    }
    for k, v in defaults.items():
        st.session_state[k] = v

# Inicjalizacja
if 'kod_pro' not in st.session_state:
    resetuj_projekt()

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.title("🪚 STOLARZPRO V18.2")
    st.caption("Profesjonalny system projektowania mebli")
    
    if st.button("🗑️ RESET PROJEKTU", type="primary", use_container_width=True):
        resetuj_projekt()
        st.rerun()
    
    st.divider()
    
    st.header("1. 📏 Gabaryty korpusu")
    KOD_PROJEKTU = st.text_input("Kod projektu", key='kod_pro').upper()
    
    col1, col2 = st.columns(2)
    with col1:
        W_MEBLA = st.number_input("Szerokość [mm]", min_value=200, max_value=3000, key='w_mebla', step=10)
        H_MEBLA = st.number_input("Wysokość [mm]", min_value=200, max_value=2500, key='h_mebla', step=10)
    with col2:
        D_MEBLA = st.number_input("Głębokość [mm]", min_value=200, max_value=800, key='d_mebla', step=10)
        GR_PLYTY = st.selectbox("Grubość [mm]", [16, 18, 25], index=1, key='gr_plyty')
    
    st.divider()
    
    st.header("2. 🗂️ Podział wnętrza")
    ilosc_przegrod = st.number_input(
        "Liczba przegród pionowych",
        min_value=0,
        max_value=10,
        key='il_przegrod',
        help="Przegrody dzielą szafkę na sekcje"
    )
    
    ilosc_sekcji = ilosc_przegrod + 1
    st.info(f"Szafka będzie miała **{ilosc_sekcji}** sekcji(-e)")
    
    # Konfiguracja sekcji
    konfiguracja = []
    st.subheader("Konfiguracja sekcji")
    
    for i in range(ilosc_sekcji):
        with st.expander(f"⚙️ Sekcja {i+1}", expanded=True):
            typ = st.selectbox(
                "Typ zabudowy",
                ["Pusta", "Półki", "Szuflady"],
                key=f"typ_{i}",
                index=0
            )
            
            det = {'typ': typ, 'ilosc': 0}
            
            if typ == "Szuflady":
                det['ilosc'] = st.number_input(
                    "Liczba szuflad",
                    min_value=1,
                    max_value=5,
                    value=2,
                    key=f"ile_{i}"
                )
            elif typ == "Półki":
                det['ilosc'] = st.number_input(
                    "Liczba półek",
                    min_value=1,
                    max_value=10,
                    value=2,
                    key=f"ile_p_{i}"
                )
            
            konfiguracja.append(det)

# ==========================================
# MAIN CONTENT
# ==========================================

st.title("🪚 STOLARZPRO V18.2")
st.caption("System wspomagania projektowania mebli z automatycznym obliczaniem wymiarów")

# Walidacja
if not validate_korpus(W_MEBLA, H_MEBLA, D_MEBLA, GR_PLYTY, ilosc_przegrod):
    st.stop()

# Budowa korpusu
try:
    korpus = Korpus(KOD_PROJEKTU, W_MEBLA, H_MEBLA, D_MEBLA, GR_PLYTY, ilosc_przegrod)
    korpus.buduj_korpus()
    korpus.buduj_wnetrze(konfiguracja)
    
    # Obliczenie szerokości sekcji
    szer_jednej_wneki = (W_MEBLA - 2*GR_PLYTY - ilosc_przegrod*GR_PLYTY) / ilosc_sekcji if ilosc_sekcji > 0 else 0
    
except Exception as e:
    st.error(f"Błąd podczas budowy korpusu: {str(e)}")
    st.stop()

# ==========================================
# TABS
# ==========================================
tabs = st.tabs(["📋 Lista elementów", "📐 Podsumowanie", "👁️ Wizualizacja 2D", "💾 Eksport"])

# ---- TAB 1: LISTA ELEMENTÓW ----
with tabs[0]:
    st.subheader("📋 Kompletna lista elementów do produkcji")
    
    if korpus.elementy:
        df = pd.DataFrame([{
            "ID": e.id,
            "Nazwa elementu": e.nazwa,
            "Szerokość [mm]": e.szer,
            "Wysokość [mm]": e.wys,
            "Grubość [mm]": e.gr,
            "Uwagi": e.uwagi
        } for e in korpus.elementy])
        
        st.dataframe(df, use_container_width=True, height=500)
        
        # Statystyki
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Liczba elementów", len(korpus.elementy))
        with col2:
            powierzchnia = sum(e.szer * e.wys / 1_000_000 for e in korpus.elementy)
            st.metric("Powierzchnia", f"{powierzchnia:.2f} m²")
        with col3:
            arkusze = powierzchnia / (2.8 * 2.07)
            st.metric("Szacowana liczba arkuszy", f"{arkusze:.1f}")
    else:
        st.warning("Brak elementów do wyświetlenia")

# ---- TAB 2: PODSUMOWANIE ----
with tabs[1]:
    st.subheader("📐 Podsumowanie projektu")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Wymiary korpusu")
        st.write(f"**Kod projektu:** {KOD_PROJEKTU}")
        st.write(f"**Szerokość:** {W_MEBLA} mm")
        st.write(f"**Wysokość:** {H_MEBLA} mm")
        st.write(f"**Głębokość:** {D_MEBLA} mm")
        st.write(f"**Grubość płyty:** {GR_PLYTY} mm")
        st.write(f"**Liczba przegród:** {ilosc_przegrod}")
    
    with col2:
        st.markdown("### Konfiguracja sekcji")
        for i, sek in enumerate(konfiguracja):
            if sek['typ'] != "Pusta":
                st.write(f"**Sekcja {i+1}:** {sek['typ']} ({sek['ilosc']} szt.)")
        
        st.write(f"**Szerokość sekcji:** {szer_jednej_wneki:.1f} mm")

# ---- TAB 3: WIZUALIZACJA ----
with tabs[2]:
    st.subheader("👁️ Wizualizacja 2D - widok frontowy")
    
    try:
        fig = rysuj_podglad_mebla(W_MEBLA, H_MEBLA, GR_PLYTY, konfiguracja, szer_jednej_wneki)
        st.pyplot(fig)
        plt.close()
    except Exception as e:
        st.error(f"Błąd podczas rysowania: {str(e)}")

# ---- TAB 4: EKSPORT ----
with tabs[3]:
    st.subheader("💾 Eksport danych projektu")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📄 Eksport do PDF")
        st.write("Lista wszystkich elementów w formacie PDF do wydruku")
        
        if st.button("🔄 Generuj PDF", use_container_width=True):
            try:
                tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                export_pdf(korpus, tmp_pdf.name)
                
                with open(tmp_pdf.name, "rb") as f:
                    st.download_button(
                        "📥 Pobierz PDF",
                        data=f.read(),
                        file_name=f"{KOD_PROJEKTU}_lista.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                st.success("✅ PDF wygenerowany pomyślnie!")
            except Exception as e:
                st.error(f"Błąd podczas generowania PDF: {str(e)}")
    
    with col2:
        st.markdown("### 💻 Eksport dla CNC")
        st.write("Plik CSV z wymiarami do importu w oprogramowaniu CNC")
        
        if st.button("🔄 Generuj CSV", use_container_width=True):
            try:
                tmp_csv = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='w')
                export_cnc(korpus, tmp_csv.name)
                
                with open(tmp_csv.name, "rb") as f:
                    st.download_button(
                        "📥 Pobierz CSV",
                        data=f.read(),
                        file_name=f"{KOD_PROJEKTU}_cnc.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                st.success("✅ CSV wygenerowany pomyślnie!")
            except Exception as e:
                st.error(f"Błąd podczas generowania CSV: {str(e)}")

# ==========================================
# FOOTER
# ==========================================
st.divider()
st.caption("STOLARZPRO V18.2 | System wspomagania projektowania mebli | © 2024")
