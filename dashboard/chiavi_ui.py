"""Chiavi per vincere: leve della partita, ritmo, quando perdono, giocatori chiave."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from basket import chiavi as C
from basket import validazione as V
from basket.glossario import G

from .stato import App
from .ui import (ARANCIO, BLU, TESTO, esc, it, kpis, note_html, num, plot, section, short,
                 show)


@st.cache_data(show_spinner="Calcolo lo scarto rispetto al previsto di ogni partita…")
def _scarti_stagione(_conn, mtime: float, stagione: str) -> pd.DataFrame:
    bt = V.carica()
    if not bt.empty and stagione in set(bt["stagione"]):
        return bt[bt["stagione"] == stagione]
    return V.backtest(_conn, [stagione])


def _fmt(chiave: str, v: float) -> str:
    return num(v, 2) if chiave == "ftr" else num(v, 1)


def _avversario(a: App, avv: int) -> tuple[int | None, bool, dict]:
    """Squadra dello staff, se gioca in casa, prossima partita contro l'avversaria."""
    nomi = dict(zip(a.profile["squadra_id"], a.profile["squadra"]))
    mia = a.utente.get("squadra_id")
    if mia not in nomi or mia == avv:
        altre = [s for s in sorted(nomi, key=nomi.get) if s != avv]
        mia = st.selectbox("La vostra squadra", [None] + altre, key=f"ch_mia_{avv}",
                           format_func=lambda s: "Scegli…" if s is None else nomi[s])
        if mia is None:
            return None, True, nomi
    ng = a.ctx.next_game(mia)
    if ng and {ng["casa_id"], ng["ospite_id"]} == {mia, avv}:
        return mia, ng["casa_id"] == mia, nomi
    casa = st.toggle(f"{short(nomi[mia])} in casa", value=True, key=f"ch_casa_{mia}_{avv}")
    return mia, casa, nomi


def render(a: App, avv: int):
    section("Chiavi per vincere", "su cosa lavorare in settimana per alzare la probabilità di "
            "vittoria", key="leve")
    mia, casa_mia, nomi = _avversario(a, avv)
    if mia is None:
        note_html("Scegli la vostra squadra per vedere le chiavi della partita.")
        _giocatori(a, avv, None, nomi, avversario=True)
        return
    ctx = a.ctx
    camp = a.profile.loc[a.profile["squadra_id"] == avv, "campionato_id"].iloc[0]
    if mia not in set(a.profile.loc[a.profile["campionato_id"] == camp, "squadra_id"]):
        note_html("Le due squadre giocano in campionati diversi.")
        return
    prof = a.profile[a.profile["campionato_id"] == camp]
    forze, hca = ctx.forze(camp), ctx.hca(camp)
    lv = C.leve(prof, forze, mia, avv, casa_mia, hca)
    rt = C.ritmo(forze, mia, avv, casa_mia, hca)
    m0, _ = C._margine_noi(forze, mia, avv, casa_mia, hca)
    p0 = lv["prob_ora"].iloc[0]
    top = lv.iloc[0]
    lento, veloce = rt.iloc[0], rt.iloc[-1]
    kpis([("Probabilità ora", f"{num(p0, 0)}%",
           f"{short(nomi[mia])} {'in casa' if casa_mia else 'in trasferta'}"),
          ("Leva principale", top["breve"], f"fino a {num(top['prob_obiettivo'], 0)}% "
           "raggiungendo l'obiettivo"),
          ("Partita lenta", f"{num(lento['prob'], 0)}%", f"{num(lento['possessi'], 0)} possessi"),
          ("Partita veloce", f"{num(veloce['prob'], 0)}%",
           f"{num(veloce['possessi'], 0)} possessi")])
    bt = _scarti_stagione(ctx.conn, a.mtime, a.stagione)
    gc_avv = C.giocatori_chiave(ctx.bg, bt, avv, ctx.nomi_giocatori)
    if not gc_avv.empty:
        gc_avv = C.prob_giocatori(gc_avv[gc_avv["effetto"] >= 0.5], m0, True)
    voci = "".join(f"<li>{esc(it(v))}</li>" for v in C.sintesi(lv, gc_avv, short(nomi[avv])))
    st.markdown(f'<div class="frase"><b>Le chiavi della partita</b><ol style="margin:6px 0 0 '
                f'18px;padding:0">{voci}</ol></div>', unsafe_allow_html=True)
    g_min = int(prof.set_index("squadra_id").loc[[mia, avv], "partite"].min())
    if g_min < 8:
        note_html(f"⚠ Pochi dati: {g_min} partite giocate. I valori delle due squadre sono "
                  "avvicinati alla media del campionato; le chiavi diventano più precise con "
                  "il passare delle giornate.")
    _grafico_leve(lv)
    tab = pd.DataFrame({
        "Fattore": lv["fattore"], "Lato": lv["lato"],
        "Atteso": [_fmt(k, v) for k, v in zip(lv["chiave"], lv["atteso"])],
        "Media": [_fmt(k, v) for k, v in zip(lv["chiave"], lv["media"])],
        "Obiettivo": [_fmt(k, v) for k, v in zip(lv["chiave"], lv["obiettivo"])],
        "Situazione": lv["situazione"],
        "Probabilità con l'obiettivo": [f"{num(p, 0)}%" for p in lv["prob_obiettivo"]],
        "Guadagno": [f"{num(g, 1, signed=True)} punti" for g in lv["guadagno"]]})
    show(tab, voci=[G["leve"], G["ritmo_varianza"]])
    sfav = "più lenta" if lento["prob"] > veloce["prob"] else "più veloce"
    note_html(f"Ritmo: a {short(nomi[mia])} conviene una partita {sfav} "
              f"({num(lento['prob'], 0)}% con {num(lento['possessi'], 0)} possessi, "
              f"{num(veloce['prob'], 0)}% con {num(veloce['possessi'], 0)}). Le leve sono "
              "associazioni statistiche, non garanzie: indicano dove guardare.")

    c1, c2 = st.columns(2)
    with c1:
        _quando_perdono(a, avv, nomi)
    with c2:
        _quando_perdono(a, mia, nomi, propria=True)
    _giocatori(a, avv, m0, nomi, avversario=True)
    _giocatori(a, mia, m0, nomi, avversario=False)


def _grafico_leve(lv: pd.DataFrame):
    d = lv.iloc[::-1]
    etich = list(d["fattore"])
    fig = go.Figure(go.Bar(
        y=etich, x=d["guadagno"], orientation="h",
        marker=dict(color=[ARANCIO if s == "a vostro sfavore" else BLU for s in d["situazione"]],
                    cornerradius=4),
        text=[f"+{num(v, 0)}%" for v in d["guadagno"]], textposition="outside",
        textfont=dict(color=TESTO),
        hovertemplate="%{y}: +%{x:.1f} punti di probabilità<extra></extra>"))
    fig.update_xaxes(range=[0, max(5.0, float(d["guadagno"].max()) * 1.25)], ticksuffix="%",
                     title="punti di probabilità guadagnati raggiungendo l'obiettivo")
    fig.update_yaxes(showgrid=False)
    plot(fig, 70 + 40 * len(d), bargap=0.35)
    note_html("Arancio: fattore oggi a vostro sfavore (obiettivo: riportarlo alla media del "
              "campionato). Blu: già a vostro favore (obiettivo: allungare il vantaggio).")


def _quando_perdono(a: App, sid: int, nomi: dict, propria: bool = False):
    qp = C.quando_perdono(a.ctx.bs, sid)
    titolo = f"Quando {short(nomi[sid])} perde" if not propria else \
        f"Quando perdete voi ({short(nomi[sid])})"
    section(titolo, "vittorie contro sconfitte", key="quando_perdono")
    if qp.empty:
        note_html("Servono almeno 3 vittorie e 3 sconfitte.")
        return
    qp = qp.head(5)
    fmt2 = qp["colonna"].isin(["ft_rate", "opp_ft_rate"])
    show(pd.DataFrame({
        "Voce": qp["voce"],
        "Nelle vittorie": [num(v, 2 if f else 1) for v, f in zip(qp["vittorie"], fmt2)],
        "Nelle sconfitte": [num(v, 2 if f else 1) for v, f in zip(qp["sconfitte"], fmt2)]}),
        voci=[G["quando_perdono"]])
    note_html(f"{int(qp['vinte'].iloc[0])} vittorie e {int(qp['perse'].iloc[0])} sconfitte.")


def _giocatori(a: App, sid: int, m0: float | None, nomi: dict, avversario: bool):
    bt = _scarti_stagione(a.ctx.conn, a.mtime, a.stagione)
    gc = C.giocatori_chiave(a.ctx.bg, bt, sid, a.ctx.nomi_giocatori)
    if avversario:
        section(f"Giocatori chiave di {short(nomi[sid])}", "come rendono rispetto al previsto "
                "quando il giocatore resta sotto la sua soglia", key="giocatori_chiave")
    else:
        section(f"I vostri giocatori chiave ({short(nomi[sid])})", "quando vanno sopra la loro "
                "soglia", key="giocatori_chiave")
    if gc.empty:
        note_html("Servono più partite: almeno 4 sotto e 4 sopra la soglia per ogni giocatore.")
        return
    gc = gc[gc["effetto"] >= 0.5]
    if m0 is not None:
        gc = C.prob_giocatori(gc, m0, avversario)
    gc = gc.head(6)
    if gc.empty:
        note_html("Nessun giocatore con un effetto marcato: il rendimento della squadra non "
                  "dipende da una sola persona.")
        return
    prob_col = "Probabilità se resta sotto" if avversario else "Probabilità se va sopra"
    df = pd.DataFrame({
        "Giocatore": gc["giocatore"],
        "Soglia": [f"{'meno di ' if avversario else 'almeno '}{num(s, 0)} {st_}"
                   for s, st_ in zip(gc["soglia"], gc["statistica"])],
        "Partite sotto/sopra": [f"{int(x)}/{int(y)}" for x, y in
                                zip(gc["partite_sotto"], gc["partite_sopra"])],
        "Scarto sotto": [num(v, 1, signed=True) for v in gc["scarto_sotto"]],
        "Scarto sopra": [num(v, 1, signed=True) for v in gc["scarto_sopra"]]})
    if m0 is not None:
        df[prob_col] = [f"{num(p, 0)}% ({num(g, 0, signed=True)})"
                        for p, g in zip(gc["prob_scenario"], gc["guadagno"])]
    df["Chi compensa"] = [f"{c} (+{num(p, 1)} punti)" if c else "–"
                          for c, p in zip(gc["compensa"], gc["compensa_punti"])]
    df["Senza di lui"] = [f"{num(s, 1, signed=True)} ({int(n)} partite)" if pd.notna(s) else "–"
                          for s, n in zip(gc["scarto_assente"], gc["partite_assente"])]
    if avversario:
        df = df.drop(columns=["Chi compensa"]) if df["Chi compensa"].eq("–").all() else df
    else:
        df = df.drop(columns=["Chi compensa"])
    show(df, voci=[G["giocatori_chiave"]])
    note_html("Scarto: punti in più (+) o in meno (−) rispetto al margine previsto prima della "
              "partita. Associazioni osservate in stagione, non garanzie.")


def anteprima(a: App, casa: int, ospite: int, nomi: dict):
    """Le tre chiavi nella pagina Anteprima, quando la partita è della squadra dello staff."""
    mia = a.utente.get("squadra_id")
    if mia not in (casa, ospite):
        return
    avv = ospite if mia == casa else casa
    camp = a.camp
    prof = a.profile[a.profile["campionato_id"] == camp]
    if not {mia, avv} <= set(prof["squadra_id"]):
        return
    forze, hca = a.ctx.forze(camp), a.ctx.hca(camp)
    lv = C.leve(prof, forze, mia, avv, mia == casa, hca)
    section("Chiavi per vincere", "le leve principali; il dettaglio è nella pagina Scouting "
            "dell'avversaria", key="leve")
    voci = "".join(f"<li>{esc(it(v))}</li>" for v in C.sintesi(lv, pd.DataFrame(), short(nomi[avv])))
    st.markdown(f'<div class="frase"><ol style="margin:0 0 0 18px;padding:0">{voci}</ol></div>',
                unsafe_allow_html=True)
