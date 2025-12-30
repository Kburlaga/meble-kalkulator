# model.py
# Model danych i logika mebla STOLARZPRO

from dataclasses import dataclass, field
from constants import (
    FUGA_FRONT,
    LUZ_FRONT,
    LUZ_POLKA,
    COF_PLECY,
)


# ======================================================
# ELEMENT
# ======================================================

@dataclass
class Element:
    id: str
    nazwa: str
    szer: float
    wys: float
    gr: float
    uwagi: str = ""
    wiercenia: list = field(default_factory=list)


# ======================================================
# KORPUS
# ======================================================

class Korpus:
    def __init__(self, kod, w, h, d, gr, przegrody):
        self.kod = kod
        self.w = w
        self.h = h
        self.d = d
        self.gr = gr
        self.przegrody = przegrody
        self.elementy: list[Element] = []

    # -------- Wymiary wewnętrzne --------

    @property
    def szer_wew(self):
        return self.w - 2 * self.gr - self.przegrody * self.gr

    @property
    def wys_wew(self):
        return self.h - 2 * self.gr

    # -------- Dodawanie elementów --------

    def _next_id(self, nazwa):
        idx = sum(1 for e in self.elementy if e.nazwa == nazwa) + 1
        return f"{self.kod}-{nazwa[:3].upper()}-{idx}"

    def dodaj(self, nazwa, szer, wys, gr, uwagi=""):
        eid = self._next_id(nazwa)
        self.elementy.append(
            Element(
                id=eid,
                nazwa=nazwa,
                szer=round(szer, 1),
                wys=round(wys, 1),
                gr=gr,
                uwagi=uwagi,
            )
        )

    # ==================================================
    # BUDOWA KORPUSU
    # ==================================================

    def buduj_korpus(self):
        # Boki
        self.dodaj("Bok Lewy", self.d, self.wys_wew, self.gr)
        self.dodaj("Bok Prawy", self.d, self.wys_wew, self.gr)

        # Przegrody
        for _ in range(self.przegrody):
            self.dodaj("Przegroda", self.d, self.wys_wew, self.gr)

        # Wieńce
        self.dodaj("Wieniec Górny", self.w, self.d, self.gr)
        self.dodaj("Wieniec Dolny", self.w, self.d, self.gr)

    # ==================================================
    # WNĘTRZE (SEKCJE)
    # ==================================================

    def buduj_wnetrze(self, konfiguracja):
        """
        konfiguracja = lista słowników, np.
        {'typ': 'Szuflady', 'ilosc': 3}
        """
        if not konfiguracja:
            return

        ilosc_sekcji = len(konfiguracja)
        szer_sekcji = self.szer_wew / ilosc_sekcji

        for idx, sekcja in enumerate(konfiguracja):
            typ = sekcja.get("typ")
            ilosc = sekcja.get("ilosc", 0)

            # -------- SZUFLADY --------
            if typ == "Szuflady" and ilosc > 0:
                h_frontu = (
                    self.wys_wew - (ilosc + 1) * FUGA_FRONT
                ) / ilosc

                for _ in range(ilosc):
                    self.dodaj(
                        "Front Szuflady",
                        szer_sekcji - LUZ_FRONT,
                        h_frontu,
                        self.gr,
                        f"Sekcja {idx + 1}",
                    )

            # -------- PÓŁKI --------
            elif typ == "Półka" and ilosc > 0:
                for _ in range(ilosc):
                    self.dodaj(
                        "Półka",
                        szer_sekcji - LUZ_POLKA,
                        self.d - COF_PLECY,
                        self.gr,
                        f"Sekcja {idx + 1}",
                    )

            # -------- PUSTA --------
            elif typ == "Pusta":
                # Nic nie dodajemy, ale sekcja istnieje
                continue
