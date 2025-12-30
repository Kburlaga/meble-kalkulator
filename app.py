import streamlit as st
import pandas as pd
import tempfile
from dataclasses import dataclass
from typing import List, Dict

# Sprawdzanie dostępności bibliotek
try:
    import matplotlib
    matplotlib.use('Agg')  # Backend bez GUI
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    MATPLOTLIB_OK = True
except ImportError:
    MATPLOTLIB_OK = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

# ==========================================
# KONFIGURACJA STRONY
# ==========================================
st.set_page_config(
    page_title="STOLARZPRO V18.2",
    page_icon="🪚",
    layout="wide"
)

# ==========================================
# KLASY DANYCH
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
        self.szer = round(float(self.szer), 1)
        self.wys = round(float(self.wys), 1)
        self.gr = round(float(self.gr), 1)

# ==========================================
# KLASA KORPUS
# ==========================================
class Korpus:
    def __init__(self, kod: str, szer: float, wys: float, gleb: float, gr: float, przegrody: int):
        self.kod = kod
        self.szer = float(szer)
        self.wys = float(wys)
        self.gleb = float(gleb)
        self.gr = float(gr)
        self.przegrody = int(przegrody)
        self.elementy: List[Element] = []
        self.counter = 0
        
    def dodaj_element(self, nazwa: str, szer: float, wys: float, gr: float, uwagi: str = ""):
        self.counter += 1
        kod_elementu = f"{self.kod}-{nazwa.replace(' ', '-').upper()}-{self.counter}"
        elem = Element(self.counter, kod_elementu, szer, wys, gr, uwagi)
        self.elementy.append(elem)
        return elem
        
    def buduj_korpus(self):
        """Buduje podstawowe elementy korpusu"""
        # Boki (2 sztuki)
        for i in range(2):
            strona = "Lewy" if i == 0 else "Prawy"
            self.dodaj_element(
                f"Bok {strona}",
                self.gleb,
                self.wys,
                self.gr,
                "Wiercenia pod półki"
            )
        
        # Przegrody pionowe
        if self.przegrody > 0:
            wys_przegrody = self.wys - 2 * self.gr
            for i in range(self.przegrody):
                self.dodaj_element(
                    f"Przegroda {i+1}",
                    self.gleb,
                    wys_przegrody,
                    self.gr,
                    "Wiercenia"
                )
        
        # Wieniec górny i dolny
        szer_wienca = self.szer - 2 * self.gr
        for nazwa in ["Wieniec Górny", "Wieniec Dolny"]:
            self.dodaj_element(
                nazwa,
                szer_wienca,
                self.gleb,
                self.gr,
                "Korpus"
            )
        
        # Plecy (opcjonalne)
        self.dodaj_element(
            "Plecy HDF",
            szer_wienca,
            self.wys - 2 * self.gr,
            3,
            "HDF 3mm"
        )
    
    def buduj_wnetrze(self, konfiguracja: List[Dict]):
        """Dodaje elementy wewnętrzne według konfiguracji"""
        if not konfiguracja:
            return
            
        ilosc_sekcji = len(konfiguracja)
        szer_sekcji = (self.szer - 2*self.gr - self.przegrody*self.gr) / ilosc_sekcji
        
        for i, sekcja in enumerate(konfiguracja):
            typ = sekcja.get('typ', 'Pusta')
            ilosc = sekcja.get('ilosc', 0)
            
            if typ == "Półki" and ilosc > 0:
                for j in range(ilosc):
                    self.dodaj_element(
                        f"Półka S{i+1}_{j+1}",
                        szer_sekcji - 2,
                        self.gleb - 50,
                        self.gr,
                        f"Sekcja {i+1}"
                    )
            
            elif typ == "Szuflady" and ilosc > 0:
                wys_dostepna = self.wys - 2*self.gr - 20
                wys_frontu = (wys_dostepna - (ilosc-1)*3) / ilosc
                
                for j in range(ilosc):
                    # Front szuflady
                    self.dodaj_element(
                        f"Front Szuflady S{i+1}_{j+1}",
                        szer_sekcji - 3,
                        wys_frontu,
                        self.gr,
                        f"Sekcja {i+1}"
                    )
                    
                    # Dno szuflady
                    self.dodaj_element(
                        f"Dno Szuflady S{i+1}_{j+1}",
                        szer_sekcji - 100,
                        self.gleb - 100,
                        self.gr,
                        "Dno"
                    )

# ==========================================
# FUNKCJE WALIDACJI
# ==========================================
def waliduj_wymiary(szer: float, wys: float, gleb: float, gr: float, przegrody: int) -> bool:
    """Waliduje wymiary korpusu"""
    bledy = []
    
    if szer < 200 or szer > 3000:
        bledy.append("Szerokość: 200-3000 mm")
    if wys < 200 or wys > 2500:
        bledy.append("Wysokość: 200-2500 mm")
    if gleb < 200 or gleb > 800:
        bledy.append("Głębokość: 200-800 mm")
    if gr not in [16, 18, 25]:
        bledy.append("Grubość: 16, 18 lub 25 mm")
    if przegrody < 0 or przegrody > 10:
        bledy.append("Przegrody: 0-10")
    
    # Sprawdź czy jest miejsce
    min_szer_sekcji = 200
    wymagana_szer = (przegrody + 1) * min_szer_sekcji + przegrody * gr + 2 * gr
    if szer < wymagana_szer:
        bledy.append(f"Za mała szerokość na {przegrody} przegród (min: {wymagana_szer} mm)")
    
    if bledy:
        for blad in bledy:
            st.error(f"⚠️ {blad}")
        return False
    return True

# ==========================================
# FUNKCJE EKSPORTU
# ==========================================
def eksport_pdf(korpus: Korpus, plik: str) -> bool:
    """Eksportuje listę do PDF"""
    if not REPORTLAB_OK:
        st.error("Brak biblioteki reportlab")
        return False
    
    try:
        c = canvas.Canvas(plik, pagesize=A4)
        w, h = A4
        
        # Nagłówek
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, h-50, f"STOLARZPRO - {korpus.kod}")
        
        c.setFont("Helvetica", 10)
        c.drawString(50, h-70, f"Wymiary: {korpus.szer}x{korpus.wys}x{korpus.gleb} mm")
        
        # Tabela
        y = h - 110
        c.setFont("Helvetica-Bold", 9)
        c.drawString(50, y, "LP")
        c.drawString(80, y, "Nazwa")
        c.drawString(280, y, "Szer")
        c.drawString(340, y, "Wys")
        c.drawString(400, y, "Grub")
        
        y -= 20
        c.setFont("Helvetica", 8)
        
        for elem in korpus.elementy:
            if y < 50:
                c.showPage()
                y = h - 50
                c.setFont("Helvetica", 8)
            
            c.drawString(50, y, str(elem.id))
            c.drawString(80, y, elem.nazwa[:35])
            c.drawString(280, y, f"{elem.szer:.1f}")
            c.drawString(340, y, f"{elem.wys:.1f}")
            c.drawString(400, y, f"{elem.gr:.1f}")
            y -= 15
        
        c.save()
        return True
    except Exception as e:
        st.error(f"Błąd PDF: {e}")
        return False

def eksport_csv(korpus: Korpus, plik: str) -> bool:
    """Eksportuje do CSV dla CNC"""
    try:
        df = pd.DataFrame([{
            "LP": e.id,
            "Nazwa": e.nazwa,
            "Dlugosc": e.szer,
            "Szerokosc": e.wys,
            "Grubosc": e.gr,
            "Ilosc": 1,
            "Material": "Płyta",
            "Uwagi": e.uwagi
        } for e in korpus.elementy])
        
        df.to_csv(plik, index=False, encoding='utf-8-sig', sep=';')
        return True
    except Exception as e:
        st.error(f"Błąd CSV: {e}")
        return False

# ==========================================
# FUNKCJE RYSOWANIA
# ==========================================
def rysuj_widok_frontowy(szer, wys, gr, konfiguracja, szer_sekcji):
    """Rysuje widok frontowy szafki"""
    if not MATPLOTLIB_OK:
        st.warning("Zainstaluj matplotlib: pip install matplotlib")
        return None
    
    try:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Tło korpusu
        tlo = patches.Rectangle((0, 0), szer, wys, 
                                linewidth=2, edgecolor='black', 
                                facecolor='wheat', alpha=0.3)
        ax.add_patch(tlo)
        
        # Boki
        for x in [0, szer-gr]:
            bok = patches.Rectangle((x, 0), gr, wys,
                                   linewidth=1, edgecolor='black',
                                   facecolor='saddlebrown', alpha=0.6)
            ax.add_patch(bok)
        
        # Wieńce
        for y in [0, wys-gr]:
            wieniec = patches.Rectangle((gr, y), szer-2*gr, gr,
                                       linewidth=1, edgecolor='black',
                                       facecolor='saddlebrown', alpha=0.6)
            ax.add_patch(wieniec)
        
        # Przegrody
        ilosc_sekcji = len(konfiguracja)
        if ilosc_sekcji > 1:
            for i in range(1, ilosc_sekcji):
                x_przegroda = gr + i * (szer_sekcji + gr)
                przegroda = patches.Rectangle((x_przegroda, gr), gr, wys-2*gr,
                                             linewidth=1, edgecolor='black',
                                             facecolor='saddlebrown', alpha=0.6)
                ax.add_patch(przegroda)
        
        # Elementy wewnętrzne
        for i, sekcja in enumerate(konfiguracja):
            x_start = gr + i * (szer_sekcji + gr)
            typ = sekcja.get('typ', 'Pusta')
            ilosc = sekcja.get('ilosc', 0)
            
            if typ == "Szuflady" and ilosc > 0:
                wys_dost = wys - 2*gr - 20
                wys_front = (wys_dost - (ilosc-1)*3) / ilosc
                
                for j in range(ilosc):
                    y_szuflada = gr + 10 + j * (wys_front + 3)
                    szuflada = patches.Rectangle((x_start+2, y_szuflada), 
                                                szer_sekcji-4, wys_front,
                                                linewidth=1.5, edgecolor='darkblue',
                                                facecolor='lightblue', alpha=0.5)
                    ax.add_patch(szuflada)
                    
                    # Uchwyt
                    y_uch = y_szuflada + wys_front/2
                    x_uch = x_start + szer_sekcji/2
                    ax.plot([x_uch-30, x_uch+30], [y_uch, y_uch], 
                           'k-', linewidth=3)
            
            elif typ == "Półki" and ilosc > 0:
                wys_dost = wys - 2*gr
                odstep = wys_dost / (ilosc + 1)
                
                for j in range(ilosc):
                    y_polka = gr + (j+1) * odstep
                    ax.plot([x_start+5, x_start+szer_sekcji-5],
                           [y_polka, y_polka], 
                           color='brown', linewidth=2, linestyle='--')
        
        ax.set_xlim(-50, szer+50)
        ax.set_ylim(-50, wys+50)
        ax.set_aspect('equal')
        ax.set_xlabel('Szerokość [mm]', fontsize=10)
        ax.set_ylabel('Wysokość [mm]', fontsize=10)
        ax.set_title('Widok frontowy', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        return fig
    except Exception as e:
        st.error(f"Błąd rysowania: {e}")
        return None

# ==========================================
# INICJALIZACJA SESSION STATE
# ==========================================
def init_session_state():
    """Inicjalizuje domyślne wartości"""
    defaults = {
        'kod_pro': "RTV-PRO-2D",
        'w_mebla': 1800,
        'h_mebla': 600,
        'd_mebla': 600,
        'gr_plyty': 18,
        'il_przegrod': 2,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def resetuj():
    """Resetuje projekt"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session_state()

# ==========================================
# APLIKACJA GŁÓWNA
# ==========================================
def main():
    # Inicjalizacja
    init_session_state()
    
    # SIDEBAR
    with st.sidebar:
        st.title("🪚 STOLARZPRO V18.2")
        st.caption("System projektowania")
        
        if st.button("🗑️ RESET", type="primary", use_container_width=True):
            resetuj()
            st.rerun()
        
        st.divider()
        
        # GABARYTY
        st.header("1. 📏 Gabaryty")
        kod = st.text_input("Nazwa", key='kod_pro').upper()
        
        col1, col2 = st.columns(2)
        with col1:
            szer = st.number_input("Szer [mm]", 200, 3000, key='w_mebla', step=10)
            wys = st.number_input("Wys [mm]", 200, 2500, key='h_mebla', step=10)
        with col2:
            gleb = st.number_input("Głęb [mm]", 200, 800, key='d_mebla', step=10)
            gr = st.selectbox("Grub [mm]", [16, 18, 25], index=1, key='gr_plyty')
        
        st.divider()
        
        # PODZIAŁ
        st.header("2. 🗂️ Podział")
        przegrody = st.number_input("Przegrody", 0, 10, key='il_przegrod')
        sekcje = przegrody + 1
        st.info(f"Sekcji: **{sekcje}**")
        
        # KONFIGURACJA SEKCJI
        konfiguracja = []
        for i in range(sekcje):
            with st.expander(f"Sekcja {i+1}", expanded=True):
                typ = st.selectbox("Typ", ["Pusta", "Półki", "Szuflady"], 
                                  key=f"typ_{i}", index=0)
                
                det = {'typ': typ, 'ilosc': 0}
                
                if typ == "Szuflady":
                    det['ilosc'] = st.number_input("Ile", 1, 5, 2, key=f"sz_{i}")
                elif typ == "Półki":
                    det['ilosc'] = st.number_input("Ile", 1, 10, 2, key=f"po_{i}")
                
                konfiguracja.append(det)
    
    # MAIN CONTENT
    st.title("🪚 STOLARZPRO V18.2")
    st.caption("Profesjonalny system projektowania mebli")
    
    # Walidacja
    if not waliduj_wymiary(szer, wys, gleb, gr, przegrody):
        st.stop()
    
    # Budowa korpusu
    korpus = Korpus(kod, szer, wys, gleb, gr, przegrody)
    korpus.buduj_korpus()
    korpus.buduj_wnetrze(konfiguracja)
    
    szer_sekcji = (szer - 2*gr - przegrody*gr) / sekcje if sekcje > 0 else 0
    
    # TABS
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Lista", "📐 Info", "👁️ Wizualizacja", "💾 Eksport"])
    
    # TAB 1: LISTA
    with tab1:
        st.subheader("Lista elementów")
        
        df = pd.DataFrame([{
            "LP": e.id,
            "Nazwa": e.nazwa,
            "Szer [mm]": e.szer,
            "Wys [mm]": e.wys,
            "Grub [mm]": e.gr,
            "Uwagi": e.uwagi
        } for e in korpus.elementy])
        
        st.dataframe(df, use_container_width=True, height=400)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Elementów", len(korpus.elementy))
        with col2:
            pow = sum(e.szer * e.wys / 1_000_000 for e in korpus.elementy)
            st.metric("Powierzchnia", f"{pow:.2f} m²")
        with col3:
            ark = pow / (2.8 * 2.07)
            st.metric("Arkuszy", f"{ark:.1f}")
    
    # TAB 2: INFO
    with tab2:
        st.subheader("Podsumowanie projektu")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Wymiary")
            st.write(f"**Kod:** {kod}")
            st.write(f"**Szerokość:** {szer} mm")
            st.write(f"**Wysokość:** {wys} mm")
            st.write(f"**Głębokość:** {gleb} mm")
            st.write(f"**Grubość:** {gr} mm")
        
        with col2:
            st.markdown("### Sekcje")
            st.write(f"**Przegrody:** {przegrody}")
            for i, sek in enumerate(konfiguracja):
                if sek['typ'] != "Pusta":
                    st.write(f"**S{i+1}:** {sek['typ']} ({sek['ilosc']})")
            st.write(f"**Szerokość sekcji:** {szer_sekcji:.1f} mm")
    
    # TAB 3: WIZUALIZACJA
    with tab3:
        st.subheader("Widok frontowy")
        fig = rysuj_widok_frontowy(szer, wys, gr, konfiguracja, szer_sekcji)
        if fig:
            st.pyplot(fig)
            plt.close(fig)
    
    # TAB 4: EKSPORT
    with tab4:
        st.subheader("Eksport danych")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📄 PDF")
            if st.button("Eksport PDF", use_container_width=True, disabled=not REPORTLAB_OK):
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                if eksport_pdf(korpus, tmp.name):
                    with open(tmp.name, "rb") as f:
                        st.download_button("📥 Pobierz PDF", f.read(),
                                         f"{kod}.pdf", "application/pdf",
                                         use_container_width=True)
        
        with col2:
            st.markdown("### 💻 CNC (CSV)")
            if st.button("Eksport CNC (CSV)", use_container_width=True):
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
                if eksport_csv(korpus, tmp.name):
                    with open(tmp.name, "rb") as f:
                        st.download_button("📥 Pobierz CSV", f.read(),
                                         f"{kod}.csv", "text/csv",
                                         use_container_width=True)
    
    # Footer
    st.divider()
    st.caption("STOLARZPRO V18.2 © 2024")

if __name__ == "__main__":
    main()
