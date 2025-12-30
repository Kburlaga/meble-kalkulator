# validation.py
# Walidacja danych wejściowych użytkownika

import streamlit as st


def validate_korpus(w, h, d, gr, przegrody):
    """
    Sprawdza poprawność podstawowych wymiarów mebla.
    Jeśli coś jest niepoprawne – pokazuje błąd i zatrzymuje aplikację.
    """

    if w <= 2 * gr:
        st.error("❌ Szerokość mebla jest za mała względem grubości płyt.")
        st.stop()

    if h <= 2 * gr:
        st.error("❌ Wysokość mebla jest za mała względem grubości płyt.")
        st.stop()

    if d <= gr:
        st.error("❌ Głębokość mebla jest za mała.")
        st.stop()

    if przegrody < 0:
        st.error("❌ Liczba przegród nie może być ujemna.")
        st.stop()
