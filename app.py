import streamlit as st
import pandas as pd
import tempfile
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import math

# Sprawdzanie dostępności bibliotek
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import Circle
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
# SYSTEMY SZUFLAD - DANE TECHNICZNE
# ==========================================
SYSTEMY_SZUFLAD = {
    "GTV Axis Pro": {
        "min_bok_do_bok": 466,
        "luz_szer": 26,
        "wys_boczka": 54,
        "gleb_montaz": 450,
        "luz_tyl": 8
    },
    "Blum Tandembox": {
        "min_bok_do_bok": 468,
        "luz_szer": 32,
        "wys_boczka": 65,
        "gleb_montaz": 450,
        "luz_tyl": 10
    },
    "Hettich ArciTech": {
        "min_bok_do_bok": 470,
        "luz_szer": 30,
        "wys_boczka": 70,
        "gleb_montaz": 450,
        "luz_tyl": 9
    }
}

# ==========================================
# KLASY DANYCH
# ==========================================
@dataclass
class Wiercenie:
    x: float
    y: float
    srednica: float = 5
    glebokos: float = 12
    typ: str = "polka"
    strona: str = "lewa"

@dataclass
class Element:
    id: int
    nazwa: str
    szer: float
    wys: float
    gr: float
    uwagi: str = ""
    wiercenia: List[Wiercenie] = field(default_factory=list)
    
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
    
    def dodaj_wiercenia_bok(self, element: Element, strona: str = "lewy"):
        """Dodaje wiercenia do boku pod półki (co 32mm)"""
        odstep_od_krawedzi = 50
        odstep_pionowy = 32
        
        x_pozycje = [37, self.gleb - 37]
        
        for x in x_pozycje:
            y = odstep_od_krawedzi
            while y < (self.wys - odstep_od_krawedzi):
                element.wiercenia.append(
                    Wiercenie(x, y, srednica=5, glebokos=12, typ="polka", strona=strona)
                )
                y += odstep_pionowy
    
    def dodaj_wiercenia_przegroda(self, element: Element, pozycja: int):
        """Dodaje wiercenia do przegrody (obustronne z lustrzanym odbiciem)"""
        odstep_od_krawedzi = 50
        odstep_pionowy = 32
        
        x_pozycje = [37, self.gleb - 37]
        
        # Lewa strona przegrody
        for x in x_pozycje:
            y = odstep_od_krawedzi
            while y < (element.wys - odstep_od_krawedzi):
                element.wiercenia.append(
                    Wiercenie(x, y, srednica=5, glebokos=12, typ="polka", strona="lewa")
                )
                y += odstep_pionowy
        
        # Prawa strona przegrody (lustrzane)
        for x in x_pozycje:
            y = odstep_od_krawedzi
            while y < (element.wys - odstep_od_krawedzi):
                element.wiercenia.append(
                    Wiercenie(x, y, srednica=5, glebokos=12, typ="polka", strona="prawa")
                )
                y += odstep_pionowy
        
    def buduj_korpus(self):
        """Buduje podstawowe elementy korpusu z wierceniami"""
        # Bok lewy
        bok_lewy = self.dodaj_element("Bok Lewy", self.gleb, self.wys, self.gr, "Wiercenia pod półki")
        self.dodaj_wiercenia_bok(bok_lewy, "lewy")
        
        # Bok prawy
        bok_prawy = self.dodaj_element("Bok Prawy", self.gleb, self.wys, self.gr, "Wiercenia pod półki")
        self.dodaj_wiercenia_bok(bok_prawy, "prawy")
        
        # Przegrody pionowe
        if self.przegrody > 0:
            wys_przegrody = self.wys - 2 * self.gr
            for i in range(self.przegrody):
                przegroda = self.dodaj_element(
                    f"Przegroda {i+1}",
                    self.gleb,
                    wys_przegrody,
                    self.gr,
                    "Wiercenia obustronne"
                )
                self.dodaj_wiercenia_przegroda(przegroda, i)
        
        # Wieniec górny i dolny
        szer_wienca = self.szer - 2 * self.gr
        self.dodaj_element("Wieniec Górny", szer_wienca, self.gleb, self.gr, "Korpus")
        self.dodaj_element("Wieniec Dolny", szer_wienca, self.gleb, self.gr, "Korpus")
        
        # Plecy
        self.dodaj_element("Plecy HDF", szer_wienca, self.wys - 2*self.gr, 3, "HDF 3mm")
    
    def buduj_wnetrze(self, konfiguracja: List[Dict], system_szuflad: str):
        """Dodaje elementy wewnętrzne według konfiguracji"""
        if not konfiguracja:
            return
            
        ilosc_sekcji = len(konfiguracja)
        szer_sekcji = (self.szer - 2*self.gr - self.przegrody*self.gr) / ilosc_sekcji
        
        params_sys = SYSTEMY_SZUFLAD.get(system_szuflad, SYSTEMY_SZUFLAD["GTV Axis Pro"])
        
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
                        f"Sekcja {i+1}, {system_szuflad}"
                    )
                    
                    # Dno szuflady
                    gleb_dna = params_sys['gleb_montaz'] - params_sys['luz_tyl']
                    szer_dna = szer_sekcji - params_sys['luz_szer']
                    self.dodaj_element(
                        f"Dno Szuflady S{i+1}_{j+1}",
                        szer_dna,
                        gleb_dna,
                        self.gr,
                        f"Dno, {system_szuflad}"
                    )

# ==========================================
# ROZKRÓJ NA ARKUSZE
# ==========================================
class Rozkroj:
    def __init__(self, szer_arkusza: float, wys_arkusza: float, szerokosc_pilarki: float = 4):
        self.szer_ark = szer_arkusza
        self.wys_ark = wys_arkusza
        self.rzaz = szerokosc_pilarki
        self.arkusze = []
        self.niezmieszczone = []
    
    def dodaj_arkusz(self):
        """Dodaje nowy pusty arkusz"""
        self.arkusze.append({
            'elementy': [],
            'pozostale_x': self.szer_ark,
            'pozostale_y': self.wys_ark
        })
    
    def czy_zmiesci_sie(self, arkusz, elem_szer, elem_wys):
        """Sprawdza czy element zmieści się na arkuszu"""
        return (elem_szer + self.rzaz <= arkusz['pozostale_x'] and 
                elem_wys + self.rzaz <= arkusz['pozostale_y'])
    
    def rozkroj_elementy(self, elementy: List[Element]):
        """Prosty algorytm rozkroju"""
        elementy_sorted = sorted(elementy, 
                                key=lambda e: e.szer * e.wys, 
                                reverse=True)
        
        self.dodaj_arkusz()
        
        for elem in elementy_sorted:
            zmieszczony = False
            
            for arkusz in self.arkusze:
                if self.czy_zmiesci_sie(arkusz, elem.szer, elem.wys):
                    arkusz['elementy'].append({
                        'elem': elem,
                        'rotacja': False,
                        'x': self.szer_ark - arkusz['pozostale_x'],
                        'y': self.wys_ark - arkusz['pozostale_y']
                    })
                    arkusz['pozostale_x'] -= (elem.szer + self.rzaz)
                    zmieszczony = True
                    break
                elif self.czy_zmiesci_sie(arkusz, elem.wys, elem.szer):
                    arkusz['elementy'].append({
                        'elem': elem,
                        'rotacja': True,
                        'x': self.szer_ark - arkusz['pozostale_x'],
                        'y': self.wys_ark - arkusz['pozostale_y']
                    })
                    arkusz['pozostale_x'] -= (elem.wys + self.rzaz)
                    zmieszczony = True
                    break
            
            if not zmieszczony:
                self.dodaj_arkusz()
                arkusz = self.arkusze[-1]
                
                if self.czy_zmiesci_sie(arkusz, elem.szer, elem.wys):
                    arkusz['elementy'].append({
                        'elem': elem,
                        'rotacja': False,
                        'x': 0,
                        'y': 0
                    })
                    arkusz['pozostale_x'] -= (elem.szer + self.rzaz)
                elif self.czy_zmiesci_sie(arkusz, elem.wys, elem.szer):
                    arkusz['elementy'].append({
                        'elem': elem,
                        'rotacja': True,
                        'x': 0,
                        'y': 0
                    })
                    arkusz['pozostale_x'] -= (elem.wys + self.rzaz)
                else:
                    self.niezmieszczone.append(elem)

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
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, h-50, f"STOLARZPRO - {korpus.kod}")
        
        c.setFont("Helvetica", 10)
        c.drawString(50, h-70, f"Wymiary: {korpus.szer}x{korpus.wys}x{korpus.gleb} mm")
        
        y = h - 110
        c.setFont("Helvetica-Bold", 9)
        c.drawString(50, y, "LP")
        c.drawString(80, y, "Nazwa")
        c.drawString(280, y, "Szer")
        c.drawString(340, y, "Wys")
        c.drawString(400, y, "Grub")
        c.drawString(450, y, "Wiercenia")
        
        y -= 20
        c.setFont("Helvetica", 8)
        
        for elem in korpus.elementy:
            if y < 50:
                c.showPage()
                y = h - 50
                c.setFont("Helvetica", 8)
            
            c.drawString(50, y, str(elem.id))
            c.drawString(80, y, elem.nazwa[:25])
            c.drawString(280, y, f"{elem.szer:.1f}")
            c.drawString(340, y, f"{elem.wys:.1f}")
            c.drawString(400, y, f"{elem.gr:.1f}")
            c.drawString(450, y, str(len(elem.wiercenia)))
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
            "Wiercenia": len(e.wiercenia),
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
def rysuj_element_z_wierceniami(element: Element):
    """Rysuje formatke z zaznaczonymi wierceniami"""
    if not MATPLOTLIB_OK:
        return None
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Formatka
    formatka = patches.Rectangle((0, 0), element.szer, element.wys,
                                linewidth=2, edgecolor='black',
                                facecolor='wheat', alpha=0.3)
    ax.add_patch(formatka)
    
    # Wiercenia
    kolory = {'polka': 'blue', 'przegroda': 'red', 'zawias': 'green'}
    
    for w in element.wiercenia:
        kolor = kolory.get(w.typ, 'blue')
        if w.strona == "lewa":
            circle = Circle((w.x, w.y), w.srednica/2, 
                          color=kolor, alpha=0.6)
            ax.add_patch(circle)
            ax.plot(w.x, w.y, 'x', color='black', markersize=4)
        else:
            circle = Circle((w.x, w.y), w.srednica/2, 
                          fill=False, edgecolor=kolor, linewidth=2, alpha=0.8)
            ax.add_patch(circle)
            ax.plot(w.x, w.y, 'o', color=kolor, markersize=3, fillstyle='none')
    
    # Wymiary
    ax.text(element.szer/2, -20, f'{element.szer:.1f} mm', 
           ha='center', fontsize=10, fontweight='bold')
    ax.text(-20, element.wys/2, f'{element.wys:.1f} mm', 
           ha='center', va='center', rotation=90, fontsize=10, fontweight='bold')
    
    # Legenda
    if element.wiercenia:
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', 
                  markersize=10, label='Półka (lewa)'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='none', 
                  markeredgecolor='blue', markersize=10, label='Półka (prawa)', 
                  markeredgewidth=2)
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=8)
    
    ax.set_xlim(-50, element.szer + 50)
    ax.set_ylim(-50, element.wys + 50)
    ax.set_aspect('equal')
    ax.set_title(f'{element.nazwa}\nWiercenia: {len(element.wiercenia)} szt.', 
                fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlabel('Szerokość [mm]')
    ax.set_ylabel('Wysokość [mm]')
    
    return fig

def rysuj_widok_frontowy(szer, wys, gr, konfiguracja, szer_sekcji):
    """Rysuje widok frontowy szafki"""
    if not MATPLOTLIB_OK:
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

def rysuj_rozkroj(rozkroj: Rozkroj):
    """Rysuje rozkrój elementów na arkuszach"""
    if not MATPLOTLIB_OK:
        return []
    
    figs = []
    
    for idx, arkusz in enumerate(rozkroj.arkusze):
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Arkusz
        ark_rect = patches.Rectangle((0, 0), rozkroj.szer_ark, rozkroj.wys_ark,
                                    linewidth=3, edgecolor='red',
                                    facecolor='lightgray', alpha=0.2)
        ax.add_patch(ark_rect)
        
        # Elementy
        kolory = ['lightblue', 'lightgreen', 'lightyellow', 'lightcoral', 'plum']
        
        for i, item in enumerate(arkusz['elementy']):
            elem = item['elem']
            rotacja = item['rotacja']
            x, y = item['x'], item['y']
            
            if rotacja:
                w, h = elem.wys, elem.szer
                tekst_rot = " (ROT)"
            else:
                w, h = elem.szer, elem.wys
                tekst_rot = ""
            
            kolor = kolory[i % len(kolory)]
            
            rect = patches.Rectangle((x, y), w, h,
                                    linewidth=1, edgecolor='black',
                                    facecolor=kolor, alpha=0.6)
            ax.add_patch(rect)
            
            # Opis elementu
            ax.text(x + w/2, y + h/2, 
                   f"#{elem.id}{tekst_rot}\n{w:.0f}x{h:.0f}",
                   ha='center', va='center', fontsize=8,
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
        
        ax.set_xlim(-100, rozkroj.szer_ark + 100)
        ax.set_ylim(-100, rozkroj.wys_ark + 100)
        ax.set_aspect('equal')
        ax.set_title(f'Arkusz #{idx+1} ({len(arkusz["elementy"])} elementów)', 
                    fontsize=12, fontweight='bold')
        ax.set_xlabel('Szerokość [mm]')
        ax.set_ylabel('Wysokość [mm]')
        ax.grid(True, alpha=0.3)
        
        figs.append(fig)
    
    return figs

# ==========================================
# INICJALIZACJA SESSION STATE
# ==========================================
def init_session_state():
    defaults = {
        'kod_pro': "RTV-PRO-2D",
        'w_mebla': 1800,
        'h_mebla': 600,
        'd_mebla': 600,
        'gr_plyty': 18,
        'il_przegrod': 2,
        'system_szuflad': "GTV Axis Pro",
        'arkusz_szer': 2800,
        'arkusz_wys': 2070,
        'piła_szer': 4
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def resetuj():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session_state()

# ==========================================
# APLIKACJA GŁÓWNA
# ==========================================
def main():
    init_session_state()
    
    # SIDEBAR
    with st.sidebar:
        st.title("🪚 STOLARZPRO V18.2")
        st.caption("System projektowania mebli")
        
        if st.button("🗑️ RESET", type="primary", use_container_width=True):
            resetuj()
            st.rerun()
        
        st.divider()
        
        # GABARYTY
        st.header("1. 📏 Gabaryty")
        kod = st.text_input("Nazwa projektu", key='kod_pro').upper()
        
        col1, col2 = st.columns(2)
        with col1:
            szer = st.number_input("Szer [mm]", 200, 3000, key='w_mebla', step=10)
            wys = st.number_input("Wys [mm]", 200, 2500, key='h_mebla', step=10)
        with col2:
            gleb = st.number_input("Głęb [mm]", 200, 800, key='d_mebla', step=10)
            gr = st.selectbox("Grub [mm]", [16, 18, 25], index=1, key='gr_plyty')
        
        st.divider()
        
        # SYSTEM SZUFLAD
        st.header("2. 🔧 System szuflad")
        system = st.selectbox("Wybierz system", 
                             list(SYSTEMY_SZUFLAD.keys()),
                             key='system_szuflad')
        
        with st.expander("📋 Parametry systemu", expanded=False):
            params = SYSTEMY_SZUFLAD[system]
            st.write(f"**Min. odstęp bok-bok:** {params['min_bok_do_bok']} mm")
            st.write(f"**Luz szerokości:** {params['luz_szer']} mm")
            st.write(f"**Wys. boczka:** {params['wys_boczka']} mm")
            st.write(f"**Głęb. montażu:** {params['gleb_montaz']} mm")
            st.write(f"**Luz od tyłu:** {params['luz_tyl']} mm")
        
        st.divider()
        
        # PODZIAŁ
        st.header("3. 🗂️ Podział")
        przegrody = st.number_input("Liczba przegród", 0, 10, key='il_przegrod')
        sekcje = przegrody + 1
        st.info(f"Liczba sekcji: **{sekcje}**")
        
        # KONFIGURACJA SEKCJI
        konfiguracja = []
        for i in range(sekcje):
            with st.expander(f"⚙️ Sekcja {i+1}", expanded=True):
                typ = st.selectbox("Typ zabudowy", 
                                  ["Pusta", "Półki", "Szuflady"], 
                                  key=f"typ_{i}", index=0)
                
                det = {'typ': typ, 'ilosc': 0}
                
                if typ == "Szuflady":
                    det['ilosc'] = st.number_input("Liczba szuflad", 1, 5, 2, key=f"sz_{i}")
                elif typ == "Półki":
                    det['ilosc'] = st.number_input("Liczba półek", 1, 10, 2, key=f"po_{i}")
                
                konfiguracja.append(det)
        
        st.divider()
        
        # ROZKRÓJ
        st.header("4. 📐 Rozkrój")
        st.write("Wymiary arkusza płyty:")
        ark_szer = st.number_input("Szer. arkusza [mm]", 1000, 3000, key='arkusz_szer', step=10)
        ark_wys = st.number_input("Wys. arkusza [mm]", 1000, 3000, key='arkusz_wys', step=10)
        pila_szer = st.number_input("Szerokość rzazu [mm]", 3, 6, key='piła_szer')
    
    # MAIN CONTENT
    st.title("🪚 STOLARZPRO V18.2")
    st.caption("Profesjonalny system projektowania mebli")
    
    # Walidacja
    if not waliduj_wymiary(szer, wys, gleb, gr, przegrody):
        st.stop()
    
    # Budowa korpusu
    korpus = Korpus(kod, szer, wys, gleb, gr, przegrody)
    korpus.buduj_korpus()
    korpus.buduj_wnetrze(konfiguracja, st.session_state.system_szuflad)
    
    szer_sekcji = (szer - 2*gr - przegrody*gr) / sekcje if sekcje > 0 else 0
    
    # Rozkrój
    rozkroj = Rozkroj(st.session_state.arkusz_szer, 
                      st.session_state.arkusz_wys, 
                      st.session_state.piła_szer)
    elementy_do_rozkroju = [e for e in korpus.elementy if e.gr == gr]
    rozkroj.rozkroj_elementy(elementy_do_rozkroju)
    
    # TABS
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 Lista", 
        "📐 Podsumowanie", 
        "🔍 Wiercenia 2D",
        "🗺️ Rozkrój", 
        "👁️ Wizualizacja", 
        "💾 Eksport"
    ])
    
    # TAB 1: LISTA
    with tab1:
        st.subheader("📋 Kompletna lista elementów")
        
        df = pd.DataFrame([{
            "LP": e.id,
            "Nazwa": e.nazwa,
            "Szer [mm]": e.szer,
            "Wys [mm]": e.wys,
            "Grub [mm]": e.gr,
            "Wiercenia": len(e.wiercenia),
            "Uwagi": e.uwagi
        } for e in korpus.elementy])
        
        st.dataframe(df, use_container_width=True, height=400)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Liczba elementów", len(korpus.elementy))
        with col2:
            pow = sum(e.szer * e.wys / 1_000_000 for e in korpus.elementy if e.gr == gr)
            st.metric("Powierzchnia płyty", f"{pow:.2f} m²")
        with col3:
            st.metric("Liczba arkuszy", len(rozkroj.arkusze))
    
    # TAB 2: PODSUMOWANIE
    with tab2:
        st.subheader("📐 Szczegóły projektu")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📏 Wymiary korpusu")
            st.write(f"**Kod projektu:** {kod}")
            st.write(f"**Szerokość:** {szer} mm")
            st.write(f"**Wysokość:** {wys} mm")
            st.write(f"**Głębokość:** {gleb} mm")
            st.write(f"**Grubość płyty:** {gr} mm")
            st.write(f"**Liczba przegród:** {przegrody}")
            st.write(f"**Szerokość sekcji:** {szer_sekcji:.1f} mm")
        
        with col2:
            st.markdown("### 🔧 System i konfiguracja")
            st.write(f"**System szuflad:** {st.session_state.system_szuflad}")
            
            params = SYSTEMY_SZUFLAD[st.session_state.system_szuflad]
            st.write(f"**Parametry systemu:**")
            st.write(f"- Luz szerokości: {params['luz_szer']} mm")
            st.write(f"- Głębokość montażu: {params['gleb_montaz']} mm")
            
            st.markdown("### 📦 Sekcje")
            for i, sek in enumerate(konfiguracja):
                if sek['typ'] != "Pusta":
                    st.write(f"**Sekcja {i+1}:** {sek['typ']} ({sek['ilosc']} szt.)")
    
    # TAB 3: WIERCENIA 2D
    with tab3:
        st.subheader("🔍 Widok 2D elementów z wierceniami")
        st.info("💡 **Legenda:** Pełne kółka = wiercenia po lewej stronie | Puste kółka = wiercenia po prawej stronie (lustrzane odbicie)")
        
        elementy_z_wierceniami = [e for e in korpus.elementy if e.wiercenia]
        
        if elementy_z_wierceniami:
            nazwy = [f"#{e.id} - {e.nazwa} ({len(e.wiercenia)} wierceń)" 
                    for e in elementy_z_wierceniami]
            
            wybrany_idx = st.selectbox("Wybierz element do podglądu", 
                                      range(len(nazwy)), 
                                      format_func=lambda x: nazwy[x])
            
            wybrany_element = elementy_z_wierceniami[wybrany_idx]
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = rysuj_element_z_wierceniami(wybrany_element)
                if fig:
                    st.pyplot(fig)
                    plt.close(fig)
            
            with col2:
                st.markdown("### 📊 Szczegóły wiercenia")
                st.write(f"**Element:** {wybrany_element.nazwa}")
                st.write(f"**Wymiary:** {wybrany_element.szer} x {wybrany_element.wys} mm")
                st.write(f"**Liczba wierceń:** {len(wybrany_element.wiercenia)}")
                
                if wybrany_element.wiercenia:
                    st.markdown("#### Lista wierceń:")
                    df_wiercenia = pd.DataFrame([{
                        "X [mm]": w.x,
                        "Y [mm]": w.y,
                        "Ø [mm]": w.srednica,
                        "Głęb [mm]": w.glebokos,
                        "Strona": w.strona
                    } for w in wybrany_element.wiercenia[:20]])
                    st.dataframe(df_wiercenia, height=300)
                    
                    if len(wybrany_element.wiercenia) > 20:
                        st.caption(f"...i {len(wybrany_element.wiercenia)-20} więcej")
        else:
            st.warning("Brak elementów z wierceniami w tym projekcie")
    
    # TAB 4: ROZKRÓJ
    with tab4:
        st.subheader("🗺️ Rozkrój na arkusze")
        
        st.info(f"📐 Arkusz: {st.session_state.arkusz_szer} x {st.session_state.arkusz_wys} mm | Rzaz: {st.session_state.piła_szer} mm")
        
        if rozkroj.niezmieszczone:
            st.error(f"⚠️ Uwaga! {len(rozkroj.niezmieszczone)} elementów nie zmieściło się na arkuszach!")
            for elem in rozkroj.niezmieszczone:
                st.write(f"- {elem.nazwa}: {elem.szer} x {elem.wys} mm")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Liczba arkuszy", len(rozkroj.arkusze))
        with col2:
            pow = sum(e.szer * e.wys / 1_000_000 for e in korpus.elementy if e.gr == gr)
            wykorzystanie = (pow / (len(rozkroj.arkusze) * st.session_state.arkusz_szer * st.session_state.arkusz_wys / 1_000_000)) * 100 if len(rozkroj.arkusze) > 0 else 0
            st.metric("Wykorzystanie", f"{wykorzystanie:.1f}%")
        with col3:
            st.metric("Elementów do rozkroju", len(elementy_do_rozkroju))
        
        # Rysunki rozkroju
        figs = rysuj_rozkroj(rozkroj)
        for idx, fig in enumerate(figs):
            st.pyplot(fig)
            plt.close(fig)
            
            # Szczegóły arkusza
            with st.expander(f"📋 Szczegóły arkusza #{idx+1}"):
                arkusz = rozkroj.arkusze[idx]
                df_ark = pd.DataFrame([{
                    "LP": item['elem'].id,
                    "Nazwa": item['elem'].nazwa,
                    "Szer": item['elem'].wys if item['rotacja'] else item['elem'].szer,
                    "Wys": item['elem'].szer if item['rotacja'] else item['elem'].wys,
                    "Rotacja": "TAK" if item['rotacja'] else "NIE",
                    "X": item['x'],
                    "Y": item['y']
                } for item in arkusz['elementy']])
                st.dataframe(df_ark, use_container_width=True)
    
    # TAB 5: WIZUALIZACJA
    with tab5:
        st.subheader("👁️ Wizualizacja 3D - Widok frontowy")
        fig = rysuj_widok_frontowy(szer, wys, gr, konfiguracja, szer_sekcji)
        if fig:
            st.pyplot(fig)
            plt.close(fig)
    
    # TAB 6: EKSPORT
    with tab6:
        st.subheader("💾 Eksport danych projektu")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📄 Eksport PDF")
            st.write("Lista wszystkich elementów wraz z liczbą wierceń")
            if st.button("Generuj PDF", use_container_width=True, disabled=not REPORTLAB_OK):
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                if eksport_pdf(korpus, tmp.name):
                    with open(tmp.name, "rb") as f:
                        st.download_button("📥 Pobierz PDF", f.read(),
                                         f"{kod}_lista.pdf", "application/pdf",
                                         use_container_width=True)
                    st.success("✅ PDF wygenerowany!")
        
        with col2:
            st.markdown("### 💻 Eksport CNC (CSV)")
            st.write("Plik CSV gotowy do importu w oprogramowaniu CNC")
            if st.button("Generuj CSV", use_container_width=True):
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
                if eksport_csv(korpus, tmp.name):
                    with open(tmp.name, "rb") as f:
                        st.download_button("📥 Pobierz CSV", f.read(),
                                         f"{kod}_cnc.csv", "text/csv",
                                         use_container_width=True)
                    st.success("✅ CSV wygenerowany!")
    
    # Footer
    st.divider()
    st.caption("STOLARZPRO V18.2 © 2024 | Wszystkie funkcje aktywne")

if __name__ == "__main__":
    main()
