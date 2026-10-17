"""Leverage nella dashboard: probabilità di vittoria minuto per minuto, momenti decisivi e
chi ha spostato le partite (per partita e nella stagione)."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from basket import leverage as L
from basket.glossario import G

from .stato import App
from .ui import ARANCIO, BLU, GRIGIO, TESTO, note_html, num, plot, section, show


def _nomi(a: App) -> dict:
    bg = a.ctx.bg
    return bg.drop_duplicates("giocatore_id").set_index("giocatore_id")["giocatore"].to_dict() if not bg.empty else {}


def grafico_probabilita(e: pd.DataFrame, casa: str, ospite: str, momenti: pd.DataFrame | None = None,
                        altezza: int = 300):
    """Probabilità di vittoria della casa durante la partita (0-100%)."""
    e = e.dropna(subset=["wp_casa"]).groupby("secondi", as_index=False).last()
    x, y = e["secondi"] / 60, e["wp_casa"] * 100
    fig = go.Figure()
    meta = [50] * len(x)
    for parte, colore in ((y.clip(lower=50), "rgba(57,135,229,0.30)"), (y.clip(upper=50), "rgba(217,89,38,0.30)")):
        fig.add_scatter(x=x, y=meta, mode="lines", line=dict(width=0, shape="hv"), hoverinfo="skip", showlegend=False)
        fig.add_scatter(x=x, y=parte, mode="lines", line=dict(width=0, shape="hv"), fill="tonexty",
                        fillcolor=colore, hoverinfo="skip", showlegend=False)
    fig.add_scatter(x=x, y=y, mode="lines", line=dict(color=TESTO, width=1.6, shape="hv"),
                    customdata=e[["punti_casa", "punti_ospite"]].values, showlegend=False,
                    hovertemplate="%{x:.1f}' · %{customdata[0]}-%{customdata[1]} · casa %{y:.0f}%<extra></extra>")
    if momenti is not None and not momenti.empty:
        fig.add_scatter(x=momenti["secondi"] / 60, y=momenti["wp_casa"] * 100, mode="markers",
                        marker=dict(size=9, color=TESTO, line=dict(color="#0a0e15", width=2)),
                        text=momenti["etichetta"], hovertemplate="%{text}<extra></extra>", showlegend=False)
    fine = int(e["periodo"].max()) if not e.empty else 4
    for q in range(1, fine):
        fig.add_vline(x=10 * q if q <= 4 else 40 + 5 * (q - 4), line=dict(color=GRIGIO, dash="dot", width=1))
    fig.add_hline(y=50, line=dict(color=GRIGIO, width=1))
    fig.update_yaxes(title=f"vince {casa} (%)", range=[0, 100], ticksuffix="%")
    fig.update_xaxes(title="minuto", showgrid=False)
    plot(fig, altezza)


def partita(a: App, pid: str, casa: str, ospite: str):
    sw = a.ctx.leverage_eventi
    if sw.empty or pid not in set(sw["partita_id"]):
        return
    nomi = _nomi(a)
    e = sw[sw["partita_id"] == pid]
    m = L.momenti_decisivi(sw, pid, 5)
    sq = {e["squadra_casa_id"].iloc[0]: casa, e["squadra_ospite_id"].iloc[0]: ospite}
    if not m.empty:
        m["etichetta"] = [f"{r.secondi // 60}' · {nomi.get(r.giocatore_id, sq.get(r.squadra_id, ''))}: {r.azione} "
                          f"({num(r.leverage, 2, True)})" for r in m.itertuples()]
    section("Probabilità di vittoria e momenti decisivi",
            "come cambiava la probabilità di vincere azione dopo azione; i punti sono le 5 azioni che "
            "l'hanno spostata di più", key="leverage")
    grafico_probabilita(e, casa, ospite, m)
    cr = a.ctx.leverage
    g = L.per_partita(cr[cr["partita_id"] == pid])
    g = g[g["giocatore_id"].notna()]
    if not g.empty:
        g["Giocatore"] = g["giocatore_id"].map(nomi); g["Squadra"] = g["squadra_id"].map(sq)
        alto = pd.concat([g.head(5), g.tail(3)]).drop_duplicates("giocatore_id")
        show(alto[["Giocatore", "Squadra", "leverage"]].rename(columns={"leverage": "Leverage"}),
             colori={"Leverage": True}, voci=[G["leverage"]])
    if not m.empty:
        show(pd.DataFrame({"Minuto": [f"{r.secondi // 60}'{r.secondi % 60:02d}" for r in m.itertuples()],
                           "Squadra": m["squadra_id"].map(sq), "Giocatore": m["giocatore_id"].map(nomi).fillna("squadra"),
                           "Azione": m["azione"], "Punteggio": [f"{int(x)}-{int(y)}" for x, y in m[["punti_casa", "punti_ospite"]].values],
                           "Leverage": m["leverage"]}), voci=[])


def classifica(a: App):
    cr = a.ctx.leverage
    if cr.empty:
        return
    section("Leverage", "chi sposta la probabilità di vittoria: tiri, liberi, rimbalzi, palle perse e "
            "difesa, pesati per quanto contava il momento", key="leverage")
    bg = a.bg_c
    mi = bg.groupby(["giocatore_id", "squadra_id"])["minuti"].sum().reset_index()
    t = L.per_giocatore(cr[cr["squadra_id"].isin(set(bg["squadra_id"]))], mi)
    if t.empty:
        return
    if a.sq is not None:
        t = t[t["squadra_id"] == a.sq]
    c1, c2 = st.columns([3, 1])
    ordine = c1.radio("Ordina per", ["Per 40'", "Totale"], horizontal=True, key="lev_ordine")
    base = int(min(150, round(0.3 * float(t["minuti"].max() or 0) / 10) * 10))   # a inizio stagione meno minuti
    soglia = c2.number_input("Min. minuti", 0, 2000, base, step=10, key=f"lev_min_{a.stagione}")
    t = t[t["minuti"].fillna(0) >= soglia]
    t = t.sort_values("leverage_p40" if ordine == "Per 40'" else "leverage", ascending=False)
    nomi = _nomi(a); sqn = a.profile.set_index("squadra_id")["squadra"].to_dict()
    for c in ("tiro", "liberi", "rimbalzo", "palla persa", "difesa"):
        if c not in t: t[c] = 0.0
    out = pd.DataFrame({"Giocatore": t["giocatore_id"].map(nomi), "Squadra": t["squadra_id"].map(sqn),
                        "Partite": t["partite"], "Min": t["minuti"], "Leverage": t["leverage"],
                        "Per 40'": t["leverage_p40"], "Tiro": t["tiro"], "Liberi": t["liberi"],
                        "Rimbalzi": t["rimbalzo"], "Palle perse": t["palla persa"], "Difesa": t["difesa"]})
    show(out.head(40), colori={"Per 40'": True, "Leverage": True}, voci=[G["leverage"]])
    note_html("Adattamento della statistica Leverage della NBA alla cronaca di A2 e B: 1,0 = 10 punti "
              "percentuali di probabilità di vittoria. Senza tracciamento ottico la difficoltà del tiro e la "
              "pressione difensiva non si misurano: la parte di squadra va a chi era in campo.")
