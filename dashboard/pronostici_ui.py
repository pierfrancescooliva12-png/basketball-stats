"""Pronostici della giornata: tutte le partite in programma con probabilità, margine e punti
totali attesi (con intervalli), affidabilità e storico del modello. Strumento di analisi."""

import pandas as pd
import streamlit as st

from basket import live
from basket import previsioni as F
from basket import validazione as V

from .stato import App
from .ui import esc, kpis, note_html, num, section, show

CAMPIONATI = {"ita2": "Serie A2", "ita3_a": "B Nazionale · girone A", "ita3_b": "B Nazionale · girone B"}


def _registro_stagione(a: App) -> pd.DataFrame:
    r = V.registro(a.ctx.conn)
    if r.empty:
        return r
    r = r[(r["stagione"] == a.stagione) & r["punti_casa"].notna()].copy()
    r["vince_casa"] = r["punti_casa"] > r["punti_ospite"]
    r["presa"] = (r["prob_casa"] >= 0.5) == r["vince_casa"]
    return r


def pronostici(a: App, giorni: int = 10) -> pd.DataFrame:
    cal = live.calendario(a.ctx.conn, a.stagione, giorni=giorni)
    cal = cal[cal["fase"].isin(["oggi", "in programma", "in corso"])]
    righe = []
    for camp, g in cal.groupby("campionato_id"):
        try:
            forze, hca = a.ctx.forze(camp), a.ctx.hca(camp)
        except Exception:
            continue
        for r in g.itertuples():
            try:
                p = F.pronostico(forze, r.squadra_casa_id, r.squadra_ospite_id, hca, camp)
            except KeyError:
                continue
            righe.append({"partita_id": r.partita_id, "campionato_id": camp, "giornata": r.giornata, "inizio": r.inizio,
                          "giorno": r.giorno, "ora": r.ora, "casa": r.casa, "ospite": r.ospite, "fase": r.fase, **p})
    return pd.DataFrame(righe).sort_values("inizio") if righe else pd.DataFrame()


def _s(x) -> str:
    v = int(round(x))
    return f"{v:+d}" if v else "0"


def _fav(r) -> tuple[str, float]:
    return (r.casa, r.prob_casa) if r.prob_casa >= 0.5 else (r.ospite, 1 - r.prob_casa)


def render(a: App):
    note_html("Probabilità calcolate con le sole informazioni disponibili prima della partita, dallo stesso modello "
              "validato su oltre 2.000 partite. Il basket ha molta casualità: anche una favorita al 75% perde una "
              "partita su quattro. Analisi statistica, non consigli di scommessa.")
    p = pronostici(a)
    if p.empty:
        st.info("Nessuna partita in programma nei prossimi giorni.")
        return
    c1, c2 = st.columns([2, 1])
    scelti = c1.multiselect("Campionati", list(CAMPIONATI), default=[a.camp] if a.camp in CAMPIONATI else list(CAMPIONATI),
                            format_func=CAMPIONATI.get, key="pron_camp")
    giorni = sorted(p["giorno"].unique(), key=lambda g: p.loc[p["giorno"] == g, "inizio"].min())
    giorno = c2.selectbox("Giorno", ["Tutti i prossimi giorni"] + giorni, key="pron_giorno")
    p = p[p["campionato_id"].isin(scelti)]
    if giorno != "Tutti i prossimi giorni":
        p = p[p["giorno"] == giorno]
    if p.empty:
        st.info("Nessuna partita per la scelta fatta.")
        return
    # storico della stagione
    reg = _registro_stagione(a)
    reg = reg[reg["campionato_id"].isin(scelti)] if not reg.empty else reg
    netti = p[(p["prob_casa"] >= 0.7) | (p["prob_casa"] <= 0.3)]
    equil = p[(p["prob_casa"] - 0.5).abs() < 0.08]
    kpis([("Partite", str(len(p)), f"{p['giorno'].nunique()} giorni"),
          ("Favorite nette", str(len(netti)), "probabilità di almeno il 70%"),
          ("Partite equilibrate", str(len(equil)), "tra il 42% e il 58%"),
          ("Il modello in stagione", f"{num(100 * reg['presa'].mean(), 0)}%" if len(reg) >= 10 else "–",
           f"favorita vincente in {int(reg['presa'].sum())} partite su {len(reg)}" if len(reg) else "registro ancora vuoto")])
    for g in [x for x in giorni if x in set(p["giorno"])]:
        q = p[p["giorno"] == g]
        section(g.capitalize(), f"{len(q)} partit{'a' if len(q) == 1 else 'e'}", key=None)
        righe = []
        for r in q.itertuples():
            fav, pf = _fav(r)
            riga = {"Ora": r.ora}
            if len(scelti) > 1:
                riga["Campionato"] = CAMPIONATI.get(r.campionato_id, r.campionato_id)
            riga.update({
                "Partita": f"{r.casa} – {r.ospite}", "Favorita": fav, "Probabilità": round(100 * pf),
                "Scarto atteso": f"+{num(abs(r.margine), 1)}",
                "Margine casa · 1 su 2": f"{_s(r.margine_da50)} / {_s(r.margine_a50)}",
                "8 su 10": f"{_s(r.margine_da)} / {_s(r.margine_a)}",
                "Punti totali · 1 su 2": f"{round(r.totale)} ({num(r.da50, 0)}–{num(r.a50, 0)})",
                "Totali 8 su 10": f"{num(r.da, 0)}–{num(r.a, 0)}",
                "Affidabilità": r.affidabilita})
            righe.append(riga)
        show(pd.DataFrame(righe), progress={"Probabilità": (50, 100)}, voci=[])
    with st.expander("Come leggere i pronostici"):
        st.markdown(
            "- **Probabilità**: quante volte su 100 vince la favorita in partite come questa. È calibrata: quando il "
            "modello dice 70-80%, la favorita ha vinto il 75% delle volte.\n"
            "- **Scarto atteso** (punti di vantaggio della favorita) e **punti totali**: il risultato medio atteso.\n"
            "- **1 su 2**: la fascia in cui cade il risultato in metà delle partite, cioè il risultato più probabile. "
            "**8 su 10**: la fascia che lo contiene 8 volte su 10. Sono larghe perché il basket lo è (un margine si "
            "sposta in media di quasi 10 punti rispetto al previsto, i totali di 12-13), più strette da metà stagione, "
            "quando le squadre sono note; verificate sulle partite passate (contengono il risultato il 52% e l'81% "
            "delle volte).\n"
            "- **Margine (8 su 10)**: dal punto di vista della squadra di casa (positivo = vince la casa).\n"
            "- **Affidabilità**: bassa a inizio stagione o con squadre cambiate molto, alta con molte partite giocate.\n"
            "- Il modello non sa delle assenze dell'ultimo momento: un infortunio del miglior giocatore cambia il "
            "pronostico di alcuni punti (simulatore \"e se\" nell'Anteprima).")
