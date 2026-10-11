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
    show(pd.DataFrame({
        "Voce": pri["voce"], "Lato": pri["lato"],
        "Voi (a partita)": [M.leggibile(r, "valore") for _, r in pri.iterrows()],
        "Media": [M.leggibile(r, "media") for _, r in pri.iterrows()],
        "Migliori": [M.leggibile(r, "migliori") for _, r in pri.iterrows()],
        "Posizione": [f"{p}° su {n}" for p, n in zip(pri["posizione"], pri["squadre"])],
        "Obiettivo": [M.leggibile(r, "obiettivo") for _, r in pri.iterrows()],
        "Vittorie in più": [f"+{num(v, 1)}" for v in pri["vittorie"]]}),
        voci=[G["aree_migliorare"]])
    note_html("Palle perse e rimbalzi: numero a partita con la percentuale tra parentesi "
              "(la percentuale non dipende dal ritmo, il numero è quello da dare in panchina); "
              "tiri liberi: liberi segnati a partita.")
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

    render_quintetti(ctx, sid, noi=True)

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


def render_quintetti(ctx, sid: int, noi: bool = False):
    """Quintetti migliori e peggiori della squadra (Net rating prudente sui minuti insieme)."""
    migliori, peggiori, soglia = M.quintetti_estremi(ctx.lineups, sid)
    section("Quintetti migliori e peggiori", f"almeno {num(soglia, 0)} minuti insieme, "
            "ordinati per Net rating pesato sui minuti", key="quintetti_estremi")
    if migliori.empty and peggiori.empty:
        note_html("Servono più partite con quintetti verificati.", "quintetti")
        return
    pr = ctx.profile.set_index("squadra_id")
    if sid in pr.index and int(pr.loc[sid, "partite"]) < 8:
        note_html("⚠ Inizio stagione: pochi minuti insieme per ogni quintetto, indicazioni da "
                  "confermare nelle prossime giornate.")

    def tabella(df):
        return pd.DataFrame({"Quintetto": df["giocatori"],
                             "Min": [num(v, 0) for v in df["minuti"]],
                             "PG": df["partite"].astype(int),
                             "+/-": [num(v, 0, signed=True) for v in df["plus_minus"]],
                             "ORtg": [num(v, 1) for v in df["ortg"]],
                             "DRtg": [num(v, 1) for v in df["drtg"]],
                             "Net Rtg": [num(v, 1, signed=True) for v in df["net_rtg"]]})
    for df, titolo, vuoto in (
            (migliori, "✅ " + ("Quelli che funzionano: da usare di più" if noi else
                                "Migliori: quelli da limitare"), "Nessuno con saldo positivo."),
            (peggiori, "⚠ " + ("Quelli da rivedere" if noi else
                               "Peggiori: quelli da cercare in partita"),
             "Nessuno con saldo negativo.")):
        st.markdown(f"**{titolo}**")
        if df.empty:
            note_html(vuoto)
        else:
            show(tabella(df), voci=[])
