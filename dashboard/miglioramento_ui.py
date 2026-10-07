"""La mia squadra: aree da migliorare e dettagli su cui concentrarsi."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from basket import chiavi as C
from basket import miglioramento as M
from basket.glossario import G

from .stato import App
from .ui import ARANCIO, BLU, TESTO, esc, it, note_html, num, plot, section, show


def render(a: App, sid: int):
    ctx = a.ctx
    camp = a.profile.loc[a.profile["squadra_id"] == sid, "campionato_id"].iloc[0]
    prof = a.profile[a.profile["campionato_id"] == camp]
    pri = M.priorita(prof, sid)
    oc = ctx.origini_concesse
    oc = oc[oc["campionato_id"] == camp] if oc is not None and not oc.empty else oc
    rg = M.punti_regalati(prof, oc, sid)
    pl = a.players[a.players["campionato_id"] == camp]
    dett = M.dettagli_giocatori(pl, sid)

    section("Aree da migliorare", "dove lavorare in allenamento e quanto vale",
            key="aree_migliorare")
    g = int(prof.set_index("squadra_id").loc[sid, "partite"])
    if g < 8:
        note_html(f"⚠ Pochi dati: {g} partite giocate. Le differenze dal campionato sono ancora "
                  "instabili; diventano affidabili dopo 8-10 giornate.")
    voci = "".join(f"<li>{esc(it(v))}</li>" for v in M.sintesi(pri, rg, dett))
    me = prof.set_index("squadra_id").loc[sid]
    tutte = M.tutte_insieme(pri, float(me["net_rtg"]), float(me["pace"]))
    extra = ""
    if tutte["voci"]:
        extra = (f'<div style="margin-top:8px"><b>Tutte insieme</b> portando alla media le '
                 f'{tutte["voci"]} voci sotto la media: circa {num(tutte["vittorie"], 1, signed=True)} '
                 f'vittorie su {M.PARTITE_STAGIONE} partite ({num(tutte["guadagno_net"], 1, signed=True)} '
                 'punti ogni 100 possessi). Scenario migliore, da usare come obiettivo.</div>')
    if voci:
        st.markdown(f'<div class="frase"><b>Su cosa concentrarsi</b><ol style="margin:6px 0 0 '
                    f'18px;padding:0">{voci}</ol>{extra}</div>', unsafe_allow_html=True)

    section("Priorità di lavoro", "Four Factors rispetto al campionato e vittorie in più "
            f"raggiungendo l'obiettivo, su {M.PARTITE_STAGIONE} partite", key="aree_migliorare")
    d = pri.iloc[::-1]
    fig = go.Figure(go.Bar(
        y=[f"{v} · {l.lower()}" for v, l in zip(d["voce"], d["lato"])], x=d["vittorie"],
        orientation="h",
        marker=dict(color=[ARANCIO if s else BLU for s in d["sotto_media"]], cornerradius=4),
        text=[f"+{num(v, 1)}" for v in d["vittorie"]], textposition="outside",
        textfont=dict(color=TESTO),
        hovertemplate="%{y}: +%{x:.1f} vittorie su 30 partite<extra></extra>"))
    fig.update_xaxes(range=[0, max(1.0, float(d["vittorie"].max()) * 1.3)],
                     title=f"vittorie in più su {M.PARTITE_STAGIONE} partite")
    fig.update_yaxes(showgrid=False)
    plot(fig, 70 + 40 * len(d), bargap=0.35)
    fmt = lambda c, v: num(v, 2) if "ft" in c else num(v, 1)
    show(pd.DataFrame({
        "Voce": pri["voce"], "Lato": pri["lato"],
        "Voi": [fmt(c, v) for c, v in zip(pri["colonna"], pri["valore"])],
        "Media": [fmt(c, v) for c, v in zip(pri["colonna"], pri["media"])],
        "Migliori": [fmt(c, v) for c, v in zip(pri["colonna"], pri["migliori"])],
        "Posizione": [f"{p}° su {n}" for p, n in zip(pri["posizione"], pri["squadre"])],
        "Obiettivo": [fmt(c, v) for c, v in zip(pri["colonna"], pri["obiettivo"])],
        "Vittorie in più": [f"+{num(v, 1)}" for v in pri["vittorie"]]}),
        voci=[G["aree_migliorare"]])
    note_html("Arancio: sotto la media del campionato (obiettivo: la media). Blu: già sopra "
              "(obiettivo: il livello del miglior quarto delle squadre). Le vittorie sono una "
              "stima contro un avversario medio.")

    c1, c2 = st.columns(2)
    with c1:
        section("Punti regalati", "a partita, rispetto al campionato", key="origini")
        if rg.empty:
            note_html("Dati non disponibili.")
        else:
            show(pd.DataFrame({"Voce": rg["voce"], "Voi": [num(v, 1) for v in rg["valore"]],
                               "Media": [num(v, 1) for v in rg["media"]],
                               "Posizione": [f"{p}° su {n}" for p, n in
                                             zip(rg["posizione"], rg["squadre"])]}), voci=[])
            note_html("Posizione: 1° = chi ne concede di meno.")
    with c2:
        section("Quando perdete terreno", "momenti della partita, punti a partita",
                key="momenti")
        m = M.momenti_critici(ctx.momenti, sid)
        if m.empty:
            note_html("Servono le cronache delle partite.")
        else:
            show(pd.DataFrame({"Momento": m["etichetta"],
                               "Fatti": [num(v, 1) for v in m["fatti_pg"]],
                               "Subiti": [num(v, 1) for v in m["subiti_pg"]],
                               "Differenza": [num(v, 1, signed=True) for v in m["diff_pg"]],
                               "Posizione": [f"{p}° su {n}" for p, n in
                                             zip(m["posizione"], m["squadre"])]}), voci=[])

    section("Dettagli individuali", "abitudini che costano punti, con la stima dei punti a "
            "partita in gioco rispetto alla media del campionato", key="dettagli_individuali")
    if dett.empty:
        note_html("Nessun dettaglio individuale marcato.")
    else:
        show(pd.DataFrame({"Giocatore": dett["giocatore"], "Area": dett["area"],
                           "Dettaglio": dett["dettaglio"].map(it),
                           "Punti a partita in gioco": [num(v, 1) if pd.notna(v) else "–"
                                                         for v in dett["punti_pg"]]}),
             voci=[G["dettagli_individuali"]])

    peggiori, migliori = M.quintetti_da_rivedere(ctx.lineups, sid)
    if not peggiori.empty or not migliori.empty:
        c1, c2 = st.columns(2)
        for col, df, titolo in ((c1, peggiori, "Quintetti da rivedere"),
                                (c2, migliori, "Quintetti che funzionano")):
            with col:
                section(titolo, "almeno 20 minuti insieme", key="quintetti")
                if df.empty:
                    note_html("Nessuno.")
                else:
                    show(pd.DataFrame({"Quintetto": df["giocatori"],
                                       "Minuti": [num(v, 0) for v in df["minuti"]],
                                       "+/-": [num(v, 0, signed=True) for v in df["plus_minus"]],
                                       "Net Rtg": [num(v, 1, signed=True) for v in df["net_rtg"]]}),
                         voci=[])

    qp = C.quando_perdono(ctx.bs, sid)
    section("Cosa cambia quando perdete", "vittorie contro sconfitte", key="quando_perdono")
    if qp.empty:
        note_html("Servono almeno 3 vittorie e 3 sconfitte.")
    else:
        qp = qp.head(5)
        f2 = qp["colonna"].isin(["ft_rate", "opp_ft_rate"])
        show(pd.DataFrame({
            "Voce": qp["voce"],
            "Nelle vittorie": [num(v, 2 if f else 1) for v, f in zip(qp["vittorie"], f2)],
            "Nelle sconfitte": [num(v, 2 if f else 1) for v, f in zip(qp["sconfitte"], f2)]}),
            voci=[G["quando_perdono"]])
