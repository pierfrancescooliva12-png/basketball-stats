"""Percentuali di squadra con il numero accanto: "18,3% (13,2)".

La percentuale (palle perse sulle azioni, rimbalzi presi sui tiri sbagliati) tiene conto del
numero di possessi ed è quella che si confronta tra squadre; il numero a partita è quello che
si dà in panchina. Le due cose vanno sempre insieme."""

import pandas as pd

# percentuale di squadra -> (colonna del conteggio sui totali, nome)
CONTE = {"tov_pct": ("perse", "palle perse"),
         "opp_tov_pct": ("opp_perse", "palle perse forzate"),
         "orb_pct": ("rimb_off", "rimbalzi offensivi"),
         "drb_pct": ("rimb_dif", "rimbalzi difensivi"),
         "orb_concessi": ("opp_rimb_off", "rimbalzi offensivi concessi")}


def it(x, d=1) -> str:
    if x is None or pd.isna(x):
        return "–"
    return f"{float(x):.{d}f}".replace(".", ",")


def a_partita(riga, col: str) -> float | None:
    """Numero a partita corrispondente alla percentuale col (None se non si può)."""
    if col not in CONTE:
        return None
    base = CONTE[col][0]
    if f"{base}_pg" in riga and pd.notna(riga.get(f"{base}_pg")):
        return float(riga[f"{base}_pg"])
    g = riga.get("partite")
    if base in riga and pd.notna(riga.get(base)) and g:
        return float(riga[base]) / float(g)
    return None


def con_numero(riga, col: str, valore=None, d: int = 1, numero=None) -> str:
    """"18,3% (13,2)": la percentuale col (o valore) con il numero a partita tra parentesi."""
    v = riga.get(col) if valore is None else valore
    n = a_partita(riga, col) if numero is None else numero
    testo = f"{it(v, d)}%"
    return testo + (f" ({it(n)})" if n is not None and pd.notna(n) else "")
