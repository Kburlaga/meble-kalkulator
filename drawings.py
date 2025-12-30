# drawings.py
# Funkcje rysujące (Matplotlib) dla STOLARZPRO

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from constants import KOLOR_PLYTA, KOLOR_FRONT, KOLOR_PRZEGRODA


# ======================================================
# RYSUNEK POJEDYNCZEGO ELEMENTU
# ======================================================

def rysuj_element(
    szer,
    wys,
    id_elementu,
    nazwa,
    otwory=None,
    kolor_tla=KOLOR_PLYTA,
    podtytul="",
):
    if otwory is None:
        otwory = []

    fig, ax = plt.subplots(figsize=(10, 6))

    rect = patches.Rectangle(
        (0, 0),
        szer,
        wys,
        linewidth=2,
        edgecolor="black",
        facecolor=kolor_tla,
    )
    ax.add_patch(rect)

    for otw in otwory:
        x, y = otw[0], otw[1]
        kolor = otw[2] if len(otw) > 2 else "red"

        ax.add_patch(
            patches.Circle(
                (x, y),
                radius=4,
                edgecolor=kolor,
                facecolor="white",
                linewidth=1.5,
            )
        )

        if len(otwory) < 60:
            ax.text(
                x + 10,
                y + 5,
                f"({x:.1f}, {y:.1f})",
                fontsize=6,
                color=kolor,
                weight="bold",
            )

    ax.set_aspect("equal")
    ax.set_title(f"{id_elementu} | {nazwa}\n{podtytul}", fontsize=12, weight="bold")
    ax.axis("off")

    plt.close(fig)
    return fig


# ======================================================
# PODGLĄD FRONTOWY MEBLA (2D)
# ======================================================

def rysuj_podglad_mebla(w, h, gr, konfiguracja, szer_wneki):
    fig, ax = plt.subplots(figsize=(12, 6))

    # Obrys zewnętrzny
    ax.add_patch(
        patches.Rectangle(
            (0, 0), w, h, linewidth=3, edgecolor="black", facecolor="none"
        )
    )

    # Wieniec dolny / górny
    ax.add_patch(
        patches.Rectangle((0, 0), w, gr, facecolor=KOLOR_PLYTA, edgecolor="black")
    )
    ax.add_patch(
        patches.Rectangle(
            (0, h - gr), w, gr, facecolor=KOLOR_PLYTA, edgecolor="black"
        )
    )

    # Boki
    ax.add_patch(
        patches.Rectangle(
            (0, gr), gr, h - 2 * gr, facecolor=KOLOR_PLYTA, edgecolor="black"
        )
    )
    ax.add_patch(
        patches.Rectangle(
            (w - gr, gr),
            gr,
            h - 2 * gr,
            facecolor=KOLOR_PLYTA,
            edgecolor="black",
        )
    )

    curr_x = gr
    h_wew = h - 2 * gr

    for idx, sekcja in enumerate(konfiguracja):
        # Przegroda pionowa
        if idx < len(konfiguracja) - 1:
            ax.add_patch(
                patches.Rectangle(
                    (curr_x + szer_wneki, gr),
                    gr,
                    h_wew,
                    facecolor=KOLOR_PRZEGRODA,
                    alpha=0.3,
                )
            )

        typ = sekcja.get("typ")
        ilosc = sekcja.get("ilosc", 0)

        # -------- SZUFLADY --------
        if typ == "Szuflady" and ilosc > 0:
            h_front = (h_wew - (ilosc + 1) * 3) / ilosc

            fo
