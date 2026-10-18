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
                "Rischio di errore": f"{round(100 * r.rischio)}%",
                "Affidabilità": r.affidabilita})
            righe.append(riga)
        show(pd.DataFrame(righe), progress={"Probabilità": (50, 100)}, voci=[])
    insieme(p, reg)
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
            "- **Rischio di errore**: probabilità che vinca la sfavorita.\n"
            "- **Affidabilità**: bassa a inizio stagione o con squadre cambiate molto, alta con molte partite giocate.\n"
            "- Il modello non sa delle assenze dell'ultimo momento: un infortunio del miglior giocatore cambia il "
            "pronostico di alcuni punti (simulatore \"e se\" nell'Anteprima).")


def _opzioni(r) -> dict:
    """Previsioni possibili su una partita: etichetta → (evento, serve una soglia)."""
    return {f"Vince {r.casa}": ("casa", False), f"Vince {r.ospite}": ("ospite", False),
            f"{r.casa} vince di più di": ("casa_scarto", True), f"{r.ospite} vince di più di": ("ospite_scarto", True),
            "Punti totali più di": ("over", True), "Punti totali meno di": ("under", True)}


def insieme(p: pd.DataFrame, reg: pd.DataFrame):
    """Più previsioni insieme: quante probabilmente se ne sbagliano e quale rischia di più."""
    section("Più previsioni insieme", "quante se ne sbagliano e quale rischia di più", key=None)
    etichette = {r.partita_id: f"{r.giorno} {r.ora} · {r.casa} – {r.ospite}" for r in p.itertuples()}
    primo = p[p["giorno"] == p.sort_values("inizio")["giorno"].iloc[0]]
    nette = [r.partita_id for r in primo.sort_values("rischio").itertuples() if r.rischio <= 0.3][:4]
    scelte = st.multiselect("Partite", list(etichette), default=nette, format_func=etichette.get, key="ins_partite")
    if not scelte:
        st.caption("Scegli due o più partite.")
        return
    righe = []
    for pid in scelte:
        r = next(p[p["partita_id"] == pid].itertuples())
        opz = _opzioni(r)
        fav = 0 if r.prob_casa >= 0.5 else 1
        c1, c2, c3 = st.columns([3, 3, 1.4])
        c1.markdown(f"**{esc(r.casa)} – {esc(r.ospite)}**")
        voce = c2.selectbox("Previsione", list(opz), index=fav, key=f"ins_v_{pid}", label_visibility="collapsed")
        evento, con_soglia = opz[voce]
        soglia = 0.0
        if con_soglia:
            base = r.totale if evento in ("over", "under") else max(0.5, abs(r.margine) - 3)
            soglia = c3.number_input("Soglia", value=float(round(base * 2) / 2), step=0.5, format="%.1f", key=f"ins_s_{pid}_{evento}",
                                     label_visibility="collapsed")
        q = F.probabilita_evento(r._asdict(), evento, soglia)
        righe.append({"Partita": f"{r.casa} – {r.ospite}",
                      "Previsione": voce + (f" {num(soglia, 1)}" if con_soglia else ""),
                      "Probabilità": round(100 * q), "Rischio di errore": round(100 * (1 - q)), "_q": q})
    e = F.errori([x["_q"] for x in righe])
    peggiore = max(righe, key=lambda x: x["Rischio di errore"])
    kpis([("Tutte giuste", f"{num(100 * e['tutte'], 0)}%", f"{len(righe)} previsioni"),
          ("Al massimo un errore", f"{num(100 * e['al_piu_uno'], 0)}%", "tutte giuste o una sbagliata"),
          ("Errori attesi", num(e["attesi"], 1), "in media su queste previsioni"),
          ("La più a rischio", f"{peggiore['Rischio di errore']}%", esc(peggiore["Previsione"]))])
    tab = pd.DataFrame(righe).drop(columns="_q").sort_values("Rischio di errore", ascending=False)
    show(tab, progress={"Probabilità": (0, 100)}, voci=[])
    record = ""
    if len(reg) >= 10:
        pf = reg["prob_casa"].where(reg["prob_casa"] >= 0.5, 1 - reg["prob_casa"])
        record = (f" In stagione il modello ha preso la vincente {int(reg['presa'].sum())} volte su {len(reg)} "
                  f"(previste in media il {num(100 * pf.mean(), 0)}%). Nelle stagioni passate correggere le probabilità "
                  f"sull'andamento della stagione non le ha rese più precise: a inizio stagione gli scarti sono soprattutto caso.")
    note_html("Probabilità dal modello, verificate sulle stagioni passate (gli intervalli di scarto e punti totali "
              "contengono il risultato 8 volte su 10 come previsto). Le partite sono considerate indipendenti: non "
              "si sa quale previsione sbaglierà, solo quale rischia di più." + record)
