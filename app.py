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
    typ: str = "polka"  # polka, przegroda, zawias
    strona: str = "lewa"  # lewa, prawa (dla lustrzanych odbić)

@dataclass
class Element:
    id: int
    nazwa: str
    szer: float
    wys: float
    gr: float
    uwagi: str = ""
    wiercenia: List[Wiercenie] = field(default_factory=list)
    krawedz_lewa: str = "ABS"
    krawedz_prawa: str = "ABS"
    krawedz_gorna: str = "ABS"
    krawedz_dolna: str = "ABS"
    
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
        """Dodaje wiercenia do boku pod półki (co 32mm standardowo)"""
        # Wiercenia pod półki - dwie kolumny
        odstep_od_krawedzi = 50
        odstep_pionowy = 32  # standard 32mm
        
        x_pozycje = [37, self.gleb - 37]  # dwie linie wiercen
        
        for x in x_pozycje:
            y = odstep_od_krawedzi
            while y < (self.wys - odstep_od_krawedzi):
                element.wiercenia.append(
                    Wiercenie(x, y, srednica=5, glebokos=12, typ="polka", strona=strona)
                )
                y += odstep_pionowy
    
    def dodaj_wiercenia_przegroda(self, element: Element, pozycja_w_szafce: int):
        """Dodaje wiercenia do przegrody (lustrzane dla prawej strony)"""
        odstep_od_krawedzi = 50
        odstep_pionowy = 32
        
        # Lewa strona przegrody
        x_lewe = [37, self.gleb - 37]
        for x in x_lewe:
            y = odstep_od_krawedzi
            while y < (element.wys - odstep_od_krawedzi):
                element.wiercenia.append(
                    Wiercenie(x, y, srednica=5, glebokos=12, typ="polka", strona="lewa")
                )
                y += odstep_pionowy
        
        # Prawa strona przegrody (lustrzane odbicie)
        # W rzeczywistości to ta sama współrzędna X, ale oznaczamy jako "prawa" dla rozróżnienia
        for x in x_lewe:
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
        """Prosty algorytm rozkroju - First Fit Decreasing"""
        # Sortuj elementy od największych
        elementy_sorted = sorted(elementy, 
                                key=lambda e: e.szer * e.wys, 
                                reverse=True)
        
        self.dodaj_arkusz()
        
        for elem in elementy_sorted:
            zmieszczony = False
            
            # Spróbuj dopasować do istniejących arkuszy
            for arkusz in self.arkusze:
                # Spróbuj oba kierunki
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
            
            # Jeśli nie zmieścił się, dodaj nowy arkusz
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
    
    # Wiercenia - różne kolory dla różnych typów
    kolory = {'polka': 'blue', 'przegroda': 'red', 'zawias': 'green'}
    
    for w in element.wiercenia:
        kolor = kolory.get(w.typ, 'blue')
        # Wiercenia z lewej strony - pełne kółka
        if w.strona == "lewa":
            circle = Circle((w.x, w.y), w.srednica/2, 
                          color=kolor, alpha=0.6)
            ax.add_patch(circle)
            ax.plot(w.x, w.y, 'x', color='black', markersize=4)
        # Wiercenia z prawej strony (lustrzane) - puste kółka
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
            
            kolor = kolory[i % len(kolorów)]
            
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
        if key not in
