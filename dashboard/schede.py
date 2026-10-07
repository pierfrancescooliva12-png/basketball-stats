"""Schede della dashboard: Panoramica, Classifica, Squadre, Giocatori, Giocatore, Scouting,
Partite."""

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from basket import analysis as A
from basket import approfondimenti as X
from basket import scouting
from basket import views as V
from basket.glossario import G

from .stato import App, partite_df, report
from .ui import (ACQUA, ARANCIO, BLU, COURT_SVG, GRIGIO, NEUTRO, SUPERFICIE, TESTO, badge,
                 badge_pos, esc, frase, it, kpis, leader_cards, num, pills, plot, section, short,
                 show, tip)


def render_panoramica(a: App):
    bs_c = a.bs_c
    players = a.players
    profile = a.profile
    sq = a.sq
    rel = bs_c[bs_c["affidabile"]]
    sum_cols = (["minuti", "punti", "punti_subiti"] + A.COUNT_STATS[1:]
                + [c for c in rel.columns if c.startswith("opp_")])
    lg = A.team_ratings(rel[sum_cols].sum().to_frame().T).iloc[0]
    casa = bs_c[bs_c["casa"] == 1]
    best = profile.sort_values("net_rtg", ascending=False).iloc[0]
    kpis([
        ("Punti a partita", f"{bs_c['punti'].mean():.1f}", "media per squadra"),
        ("Ritmo", f"{lg['pace']:.1f}", "possessi per 40'"),
        ("Rating offensivo", f"{lg['ortg']:.1f}", "punti per 100 possessi"),
        ("% da 3", f"{lg['t3_pct']:.1f}", f"{lg['t3a'] / len(rel):.1f} tentativi a squadra"),
        ("Vittorie in casa", f"{100 * casa['vinta'].mean():.0f}%",
         f"{int(casa['vinta'].sum())} su {len(casa)}"),
        ("Miglior Net Rtg", f"{best['net_rtg']:+.1f}", best["squadra"]),
    ])

    section("Leader", "giocatori con almeno metà delle partite e 10' di media")
    q = A.qualified(players)
    tiri = q[q["fga_pg"] >= 6]
    leader_cards([
        ("Punti", q.nlargest(5, "punti_pg"), "punti_pg", ".1f"),
        ("Rimbalzi", q.nlargest(5, "rimb_tot_pg"), "rimb_tot_pg", ".1f"),
        ("Assist", q.nlargest(5, "assist_pg"), "assist_pg", ".1f"),
        ("Game Score", q.nlargest(5, "game_score_pg"), "game_score_pg", ".1f"),
        ("True shooting % (≥ 6 tiri)", tiri.nlargest(5, "ts_pct"), "ts_pct", ".1f"),
        ("Usage %", q.nlargest(5, "usg_pct"), "usg_pct", ".1f"),
        ("Recuperi", q.nlargest(5, "recuperate_pg"), "recuperate_pg", ".1f"),
        ("Stoppate", q.nlargest(5, "stoppate_pg"), "stoppate_pg", ".1f"),
        ("Valutazione", q.nlargest(5, "valutazione_pg"), "valutazione_pg", ".1f"),
    ])

    section("Mappa del campionato", "ORtg vs DRtg · in alto a destra le squadre migliori")
    pr = profile.dropna(subset=["ortg", "drtg"])
    hi = (pr["squadra_id"] == sq) if sq is not None else pd.Series(True, index=pr.index)
    top = (set(pr.nlargest(3, "net_rtg")["squadra_id"])
           | set(pr.nsmallest(3, "net_rtg")["squadra_id"]))
    label = [short(n) if (s == sq or (sq is None and s in top)) else ""
             for n, s in zip(pr["squadra"], pr["squadra_id"])]
    fig = go.Figure(go.Scatter(
        x=pr["ortg"], y=pr["drtg"], mode="markers+text", text=label,
        textposition="top center", textfont=dict(color=TESTO, size=12),
        marker=dict(size=[16 if h else 12 for h in hi], color=[BLU if h else GRIGIO for h in hi],
                    line=dict(width=2, color=SUPERFICIE)),
        customdata=pr[["squadra", "net_rtg", "vinte", "perse_partite"]].values,
        hovertemplate="<b>%{customdata[0]}</b><br>ORtg %{x:.1f} · DRtg %{y:.1f}"
                      "<br>Net %{customdata[1]:+.1f} · %{customdata[2]}-%{customdata[3]}"
                      "<extra></extra>"))
    fig.add_vline(x=pr["ortg"].mean(), line=dict(dash="dot", color=GRIGIO, width=1))
    fig.add_hline(y=pr["drtg"].mean(), line=dict(dash="dot", color=GRIGIO, width=1))
    for x, y, t, xa, ya in [(1, 1, "attacco ▲ · difesa ▲", "right", "top"),
                            (0, 1, "attacco ▼ · difesa ▲", "left", "top"),
                            (1, 0, "attacco ▲ · difesa ▼", "right", "bottom"),
                            (0, 0, "attacco ▼ · difesa ▼", "left", "bottom")]:
        fig.add_annotation(xref="paper", yref="paper", x=x, y=y, text=t, showarrow=False,
                           xanchor=xa, yanchor=ya, font=dict(size=11, color="#6b7489"))
    fig.update_yaxes(autorange="reversed", title="DRtg (subiti / 100 poss.)")
    fig.update_xaxes(title="ORtg (fatti / 100 poss.)")
    plot(fig, 460)


def classifica(a: App) -> pd.DataFrame:
    bs_c = a.bs_c
    cl = A.standings(bs_c).merge(
        a.profile[["squadra_id", "pyth_pct", "fortuna", "record_pp", "sos"]], on="squadra_id")
    forma = (bs_c.sort_values(["data", "partita_id"]).groupby("squadra_id")["vinta"]
             .apply(lambda s: " ".join("V" if v else "P" for v in s.tail(5))))
    cl["forma"] = cl["squadra_id"].map(forma)
    return cl


def render_classifica(a: App):
    cl = classifica(a)
    cols = {"pos": "Pos", "squadra": "Squadra", "punti_classifica": "Pt", "vinte": "V",
            "perse_partite": "P", "forma": "Ultime 5", "diff": "Diff", "net_rtg": "Net Rtg",
            "pyth_pct": "V% attesa", "fortuna": "Fortuna", "record_pp": "Punto a punto",
            "sos": "Calendario", "punti": "PF", "punti_subiti": "PS", "ortg": "ORtg",
            "drtg": "DRtg", "partite": "PG"}
    show(V.select(cl, cols), height=36 * (len(cl) + 1) + 4,
         progress={"V% attesa": (0, 100)})


def render_squadre(a: App):
    bs_c = a.bs_c
    profile = a.profile
    sq = a.sq
    viste = ["Avanzate", "Profilo", "Quarti", "Medie", "Per 40'", "Casa/Trasferta",
             "Ultime 5"] if a.esperto else ["Essenziale", "Quarti", "Casa/Trasferta", "Ultime 5"]
    vista = st.radio("Vista", viste, horizontal=True, key="vista_sq")
    sel = profile if sq is None else profile[profile["squadra_id"] == sq]
    if vista == "Profilo":
        show(V.select(sel.sort_values("net_rtg", ascending=False), V.TEAM_PROFILO)
             .drop(columns=["Campionato", "Diff Q1", "Diff Q2", "Diff Q3", "Diff Q4"],
                   errors="ignore"),
             progress={"% punti panchina": (0, 60), "% punti top 2": (0, 70)})
        section("Da dove arrivano i punti", "quota dei punti da 2, da 3 e dai liberi")
        d = profile.sort_values("quota_punti_3")
        fig = go.Figure()
        for col, name, color in [("quota_punti_2", "Da 2", BLU), ("quota_punti_3", "Da 3", ARANCIO),
                                 ("quota_punti_tl", "Liberi", ACQUA)]:
            fig.add_bar(y=[short(n) for n in d["squadra"]], x=d[col], name=name, orientation="h",
                        marker=dict(color=color, line=dict(color=SUPERFICIE, width=2)),
                        customdata=d["squadra"],
                        hovertemplate="%{customdata}<br>" + name + ": %{x:.1f}%<extra></extra>")
        fig.update_xaxes(range=[0, 100], ticksuffix="%")
        fig.update_yaxes(showgrid=False)
        plot(fig, max(360, 26 * len(d) + 80), barmode="stack", bargap=0.25)
    elif vista == "Quarti":
        section("Differenza punti per quarto",
                "media a partita · blu = quarto vinto, arancio = quarto perso")
        d = profile.sort_values("net_rtg", ascending=False)
        qcols = [c for c in ["diff_q1", "diff_q2", "diff_q3", "diff_q4"] if c in d.columns]
        z = d[qcols].values
        lim = max(1.0, float(d[qcols].abs().max().max()))
        fig = go.Figure(go.Heatmap(
            z=z, x=[c[-2:].upper() for c in qcols], y=[short(n) for n in d["squadra"]],
            zmin=-lim, zmax=lim, colorscale=[[0, ARANCIO], [0.5, NEUTRO], [1, BLU]],
            text=[[f"{v:+.1f}" if pd.notna(v) else "" for v in row] for row in z],
            texttemplate="%{text}", textfont=dict(color=TESTO, size=12),
            xgap=2, ygap=2, showscale=False,
            customdata=[[n] * len(qcols) for n in d["squadra"]],
            hovertemplate="%{customdata} · %{x}: %{z:+.1f}<extra></extra>"))
        fig.update_yaxes(autorange="reversed", showgrid=False)
        fig.update_xaxes(side="top", showgrid=False)
        plot(fig, max(360, 26 * len(d) + 60))
    elif vista == "Casa/Trasferta":
        show(V.casa_trasferta_squadre(bs_c if sq is None else bs_c[bs_c["squadra_id"] == sq])
             .drop(columns="Campionato"))
    else:
        src = A.team_last_n(bs_c, 5) if vista == "Ultime 5" else sel
        if sq is not None:
            src = src[src["squadra_id"] == sq]
        mapping = {"Medie": V.TEAM_MEDIE, "Per 40'": V.TEAM_P40}.get(vista, V.TEAM_AVANZATE)
        if not a.esperto:
            mapping = V.TEAM_ESSENZIALE
        show(V.select(src.sort_values("net_rtg", ascending=False), mapping)
             .drop(columns="Campionato", errors="ignore"),
             colori={"Net rating": True, "Net Rtg": True, "Attacco (ORtg)": True,
                     "ORtg": True, "Difesa (DRtg)": False, "DRtg": False})


COLORI_GIOCATORI = {"Punti": True, "Rimbalzi": True, "Assist": True, "Palle perse": False,
                    "% da 3": True, "Valutazione": True, "Tiro (TS%)": True, "Game Score": True,
                    "TS%": True, "Val": True}


def pochi_dati(df: pd.DataFrame, minuti: float = 60) -> pd.Series:
    """Segnala i campioni troppo piccoli rispetto agli altri: meno della metà delle partite
    giocate dai più presenti, o meno di 60 minuti in totale."""
    soglia = max(1, df["partite"].max() / 2) if not df.empty else 1
    return ((df["partite"] < soglia) | (df["minuti"] < minuti)).map(
        {True: "⚠ pochi dati", False: ""})


def avviso_inizio_stagione(a: App):
    g = int(a.bs_c["giornata"].max()) if not a.bs_c.empty else 0
    if g < 5:
        st.markdown(f'<div class="note">{badge("Inizio stagione", "warn")} con {g} giornate '
                    'giocate medie e percentuali cambiano molto da una partita all\'altra: '
                    'per il mercato confronta anche la stagione precedente.</div>',
                    unsafe_allow_html=True)


def render_giocatori(a: App):
    bs = a.ctx.bs
    bg_c = a.bg_c
    players = a.players
    sq = a.sq
    gsel = a.gsel
    pool = players if sq is None else players[players["squadra_id"] == sq]
    c1, c2 = st.columns([4, 1])
    viste = ["Medie", "Avanzate", "Ruolo", "Per 40'", "Totali", "Trend ult. 5",
             "Casa/Trasferta"] if a.esperto else ["Medie", "Avanzate", "Trend ult. 5",
                                                  "Casa/Trasferta"]
    vista = c1.radio("Vista", viste, horizontal=True, key="vista_gi")
    min_pg = c2.number_input("Min. partite", 0, 40, 1 if sq else 2)
    bg_f = bg_c if sq is None else bg_c[bg_c["squadra_id"] == sq]
    p = pool[pool["partite"] >= min_pg].sort_values("punti_pg", ascending=False)
    p = p.assign(dati=pochi_dati(p))
    if vista == "Casa/Trasferta":
        t = V.casa_trasferta_giocatori(bg_f, bs)
        t = t[t["PG"] >= min_pg]
    elif vista == "Trend ult. 5":
        tr = A.player_trend(bg_f, bs)
        tr = tr[tr["partite"] >= min_pg].sort_values("valutazione_pg_delta", ascending=False)
        t = V.select(tr, V.TREND)
    else:
        if vista == "Per 40'":
            p = p[p["minuti_pg"] >= 10]
            st.markdown('<div class="note">Per 40\': solo giocatori con almeno 10\' di media.'
                        f'{tip("per40")}</div>', unsafe_allow_html=True)
        if a.esperto:
            mapping = {"Medie": V.PLAYER_MEDIE, "Totali": V.PLAYER_TOTALI,
                       "Per 40'": V.PLAYER_P40, "Ruolo": V.PLAYER_RUOLO}.get(
                           vista, V.PLAYER_AVANZATE)
        else:
            mapping = V.PLAYER_ESSENZIALE if vista == "Medie" else V.PLAYER_AVANZATE_ESS
        mapping = {**{k: v for k, v in mapping.items() if k in ("campionato", "giocatore",
                                                                "squadra")},
                   "dati": "Dati", **mapping}
        t = V.select(p, mapping)
    if gsel is not None:
        nome = players.loc[players["giocatore_id"] == gsel[0], "giocatore"].iloc[0]
        t = t[t["Giocatore"] == nome]
    avviso_inizio_stagione(a)
    if not a.esperto:
        st.markdown('<div class="note">Vista essenziale: attiva <b>Esperto</b> in alto per tutte '
                    'le colonne e le viste.</div>', unsafe_allow_html=True)
    show(t.drop(columns="Campionato", errors="ignore"), height=620,
         progress={"USG%": (0, 40), "TS%": (0, 80)} if vista == "Avanzate" and a.esperto
         else None, colori=COLORI_GIOCATORI)


def render_giocatore(a: App):
    bs = a.ctx.bs
    bg_c = a.bg_c
    players = a.players
    gsel = a.gsel
    if gsel is None:
        st.info("Seleziona un giocatore nel filtro in alto.")
    else:
        gid, gsq = gsel
        me = players[(players["giocatore_id"] == gid) & (players["squadra_id"] == gsq)].iloc[0]
        log = A.player_game_log(bg_c[bg_c["squadra_id"] == gsq], gid)
        log["game_score"] = A.game_score(log)
        st.markdown(
            f'<div class="hero" style="padding:16px 20px">{COURT_SVG}<div class="eyebrow">'
            f'{esc(me["squadra"])}</div><div class="title" style="font-size:2rem">'
            f'{esc(me["giocatore"])}</div><div class="meta">{int(me["partite"])} partite · '
            f'{int(me["quintetti"])} in quintetto · {num(me["minuti_pg"])} minuti di media · '
            f'massimo {int(me["max_punti"])} punti</div></div>', unsafe_allow_html=True)

        frase("In una frase", X.frase_giocatore(players, gid, gsq))
        if me["partite"] < 3 or me["minuti"] < 60:
            st.markdown('<div class="note">' + badge("⚠ pochi dati", "warn") +
                        ' con meno di 3 partite o 60 minuti i numeri possono cambiare molto.'
                        '</div>', unsafe_allow_html=True)

        def f1_(v, suffix=""):
            return "–" if pd.isna(v) else f"{v:.1f}{suffix}"

        kpis([
            ("Punti", f1_(me["punti_pg"]), f"{f1_(me['punti_p40'])} per 40'"),
            ("Rimbalzi", f1_(me["rimb_tot_pg"]), f"REB% {f1_(me['trb_pct'])}"),
            ("Assist", f1_(me["assist_pg"]), f"AST% {f1_(me['ast_pct'])}"),
            ("True shooting", f1_(me["ts_pct"], "%"), f"eFG% {f1_(me['efg_pct'])}"),
            ("Usage", f1_(me["usg_pct"], "%"), f"TOV% {f1_(me['tov_pct'])}"),
            ("Game Score", f1_(me["game_score_pg"]), f"valutazione {f1_(me['valutazione_pg'])}"),
        ])
        from .nuove import scheda_giocatore
        scheda_giocatore(a)

        c1, c2 = st.columns(2)
        with c1:
            section("Profilo", "percentile nel campionato (min. 10')")
            pc = A.percentiles(players, gid, gsq).iloc[::-1]
            fig = go.Figure(go.Bar(
                y=pc["Metrica"], x=pc["Percentile"], orientation="h",
                marker=dict(color=[BLU if v >= 50 else ARANCIO for v in pc["Percentile"]],
                            cornerradius=4),
                text=[f"{v}" for v in pc["Percentile"]], textposition="outside",
                textfont=dict(color=TESTO, size=12), customdata=pc["Valore"],
                hovertemplate="%{y}: %{x}° percentile<br>valore %{customdata:.1f}<extra></extra>"))
            fig.add_vline(x=50, line=dict(color=GRIGIO, dash="dot", width=1))
            fig.update_xaxes(range=[0, 112], showgrid=False, showticklabels=False)
            fig.update_yaxes(showgrid=False)
            plot(fig, 440, bargap=0.35)
        with c2:
            section("Andamento", "partita per partita e media mobile su 5")
            stat = st.radio("Statistica", ["punti", "game_score", "valutazione", "rimb_tot",
                                           "assist", "minuti"], horizontal=True,
                            label_visibility="collapsed",
                            format_func=lambda s: {"punti": "Punti", "game_score": "GmSc",
                                                   "valutazione": "Val", "rimb_tot": "Rimb",
                                                   "assist": "Ass", "minuti": "Min"}[s])
            x = [f"G{g}" for g in log["giornata"]]
            fig = go.Figure()
            fig.add_bar(x=x, y=log[stat], name="Partita", marker=dict(color=BLU, cornerradius=4),
                        customdata=log[["avversario"]].values,
                        hovertemplate="%{x} vs %{customdata[0]}<br>%{y:.1f}<extra></extra>")
            fig.add_scatter(x=x, y=log[stat].rolling(5, min_periods=1).mean(),
                            name="Media mobile 5", mode="lines+markers",
                            line=dict(color=ARANCIO, width=2),
                            marker=dict(size=8, line=dict(color=SUPERFICIE, width=2)),
                            hovertemplate="Media ult. 5: %{y:.1f}<extra></extra>")
            plot(fig, 390, bargap=0.4 if len(log) > 3 else 0.7)

        section("Game log")
        cols = {"giornata": "G.", "data": "Data", "avversario": "Avversario", "casa": "Casa",
                "quintetto": "Q", "minuti": "Min", "punti": "Pt", "t2m": "2PM", "t2a": "2PA",
                "t3m": "3PM", "t3a": "3PA", "tlm": "TLM", "tla": "TLA", "rimb_off": "RO",
                "rimb_dif": "RD", "rimb_tot": "RT", "assist": "Ass", "perse": "Perse",
                "recuperate": "Rec", "stoppate": "Stop", "falli_commessi": "F",
                "valutazione": "Val", "game_score": "GmSc", "ts_pct": "TS%"}
        gl = log[list(cols)].rename(columns=cols).iloc[::-1]
        gl["Casa"] = gl["Casa"].map({1: "C", 0: "T"})
        gl["Q"] = gl["Q"].map({1: "★", 0: ""})
        show(gl)
        section("Casa / trasferta")
        show(V.casa_trasferta_giocatori(bg_c[(bg_c["giocatore_id"] == gid)
                                             & (bg_c["squadra_id"] == gsq)], bs)
             .drop(columns=["Campionato", "Giocatore", "Squadra"]))


def render_scouting(a: App):
    profile = a.profile
    sq = a.sq
    mtime = a.mtime
    if sq is None:
        st.info("Seleziona una squadra nel filtro in alto per il report di scouting.")
    else:
        r = report(mtime, a.stagione, sq)
        pf = profile[profile["squadra_id"] == sq].iloc[0]
        st.markdown(
            f'<div class="hero" style="padding:16px 20px">{COURT_SVG}<div class="eyebrow">'
            f'Report di scouting · {esc(r.campionato)}</div><div class="title" '
            f'style="font-size:2rem">{esc(r.squadra)}</div><div class="meta">Record '
            f'{esc(r.record)} · {r.posizione}° posto'
            + (f' · prossima: {esc(it(r.prossima))}' if r.prossima else "") + '</div></div>',
            unsafe_allow_html=True)
        frase("In una frase", X.frase_squadra(profile, sq))
        from .nuove import _pdf
        from basket.report_pdf import slug
        st.download_button("⬇ Report PDF per la riunione tecnica",
                           _pdf(a.ctx, a.mtime, a.stagione, sq, a.utente.get("squadra_id")),
                           file_name=f"scouting_{slug(r.squadra)}.pdf", mime="application/pdf",
                           type="primary")
        pr = profile.set_index("squadra_id")
        kpis([
            ("Net rating", f"{pf['net_rtg']:+.1f}", badge_pos(X.posizione(pr["net_rtg"], sq))),
            ("Rating offensivo", f"{pf['ortg']:.1f}", badge_pos(X.posizione(pr["ortg"], sq))),
            ("Rating difensivo", f"{pf['drtg']:.1f}",
             badge_pos(X.posizione(pr["drtg"], sq, piu_alto_meglio=False))),
            ("Ritmo", f"{pf['pace']:.1f}", "possessi per 40'"),
            ("Punto a punto", pf["record_pp"], f"partite con margine ≤ {A.CLOSE_MARGIN}"),
            ("Fortuna", f"{pf['fortuna']:+.1f}", f"vittorie attese {pf['vinte_attese']:.1f}"),
            ("Punti panchina", f"{pf['quota_punti_panchina']:.0f}%", "sul totale di squadra"),
            ("Top 2 realizzatori", f"{pf['quota_top2']:.0f}%", "dei punti di squadra"),
        ])
        a, b = st.columns(2)
        with a:
            section("Punti di forza")
            pills(r.punti_forza, "pos", "Nessuno marcato (servono più partite)")
        with b:
            section("Punti deboli")
            pills(r.punti_deboli, "neg", "Nessuno marcato")

        c1, c2 = st.columns(2)
        with c1:
            section("Four Factors", "squadra vs media campionato")
            ff = r.profilo[r.profilo["Metrica"].isin([
                "eFG% in attacco", "Palle perse % in attacco", "Rimbalzi offensivi %",
                "eFG% concessa", "Palle perse forzate %", "Rimbalzi difensivi %"])]
            fig = go.Figure()
            fig.add_bar(y=ff["Metrica"], x=ff["Valore"], name=short(r.squadra), orientation="h",
                        marker=dict(color=BLU, cornerradius=4),
                        hovertemplate="%{y}: %{x:.1f}<extra></extra>")
            fig.add_bar(y=ff["Metrica"], x=ff["Media campionato"], name="Media", orientation="h",
                        marker=dict(color=GRIGIO, cornerradius=4),
                        hovertemplate="%{y}: %{x:.1f}<extra>media</extra>")
            fig.update_yaxes(autorange="reversed", showgrid=False)
            plot(fig, 400, barmode="group", bargap=0.3, bargroupgap=0.08)
        with c2:
            section("Quarto per quarto", "punti medi fatti − subiti")
            per = r.periodi
            fig = go.Figure(go.Bar(
                x=per["Periodo"], y=per["Diff"],
                marker=dict(color=[BLU if v >= 0 else ARANCIO for v in per["Diff"]],
                            cornerradius=4),
                text=[f"{v:+.1f}" for v in per["Diff"]], textposition="outside",
                textfont=dict(color=TESTO), customdata=per[["Fatti", "Subiti"]].values,
                hovertemplate="%{x}: %{customdata[0]:.1f} fatti, %{customdata[1]:.1f} subiti"
                              "<extra></extra>"))
            fig.add_hline(y=0, line=dict(color=GRIGIO, width=1))
            lim = max(3.0, float(per["Diff"].abs().max()) * 1.35) if len(per) else 3.0
            fig.update_yaxes(range=[-lim, lim])
            plot(fig, 400, bargap=0.45)

        section("Giocatori chiave", "ordinati per minuti")
        show(r.giocatori, progress={"USG%": (0, 40)},
             colori={"Punti": True, "TS%": True, "Val": True})
        c1, c2 = st.columns(2)
        with c1:
            section("Ultime 5 partite")
            show(r.ultime)
        with c2:
            section("Casa / trasferta")
            show(r.casa_trasferta)
        section("Profilo completo", "posizione nel campionato per ogni metrica")
        show(r.profilo, voci=[G[k] for k in ("ortg", "drtg", "net_rtg", "pace", "four_factors",
                                             "efg", "tov", "orb", "drb", "ft_rate", "ast_ratio")])
        st.download_button("⬇ Scarica report (Markdown)", scouting.to_markdown(r),
                           file_name=f"scouting_{r.squadra}.md", mime="text/markdown")


def render_partite(a: App):
    bs = a.ctx.bs
    bg = a.ctx.bg
    sq = a.sq
    camp = a.camp
    mtime = a.mtime
    partite = partite_df(mtime, a.stagione)
    pc = partite[partite["campionato_id"] == camp].sort_values(["giornata", "data"],
                                                                ascending=False)
    if sq is not None:
        pc = pc[(pc["squadra_casa_id"] == sq) | (pc["squadra_ospite_id"] == sq)]
    labels = {r.partita_id: f"G{r.giornata} · {r.data} · {r.casa} {r.punti_casa}-"
                            f"{r.punti_ospite} {r.ospite}" for r in pc.itertuples()}
    pid = st.selectbox("Partita", list(labels), format_func=labels.get)
    if pid:
        row = pc[pc["partita_id"] == pid].iloc[0]
        parz = json.loads(row["parziali"] or "[]")
        tr = A.team_ratings(bs[bs["partita_id"] == pid].copy()).set_index("squadra_id")
        quarti = " · ".join((f"Q{p['periodo']}" if p["periodo"] <= 4 else "OT")
                            + f" {p['casa']}-{p['ospite']}" for p in parz)
        st.markdown(
            f'<div class="hero" style="padding:16px 20px">{COURT_SVG}<div class="eyebrow">'
            f'{row["giornata"]}ª giornata · {esc(row["data"])} · {esc(row["palazzetto"] or "")}'
            f'</div><div class="title" style="font-size:1.9rem">{esc(row["casa"])} '
            f'<span style="color:var(--accent)">{row["punti_casa"]}–{row["punti_ospite"]}</span> '
            f'{esc(row["ospite"])}</div><div class="meta">{esc(quarti)} · '
            f'<a href="{esc(row["url"])}" style="color:var(--text-2)">box score ufficiale</a>'
            '</div></div>', unsafe_allow_html=True)
        if not tr["affidabile"].all():
            st.warning("Box score ufficiale incompleto (tiri tentati, rimbalzi o perse non "
                       "registrati del tutto): partita esclusa da percentuali e metriche avanzate.")
        else:
            h, o = tr.loc[row["squadra_casa_id"]], tr.loc[row["squadra_ospite_id"]]
            kpis([
                ("Possessi", f"{h['possessi']:.0f}", "stima per squadra"),
                ("ORtg", f"{h['ortg']:.0f} / {o['ortg']:.0f}", "casa / ospite"),
                ("eFG%", f"{h['efg_pct']:.0f} / {o['efg_pct']:.0f}", "casa / ospite"),
                ("Palle perse %", f"{h['tov_pct']:.0f} / {o['tov_pct']:.0f}", "casa / ospite"),
                ("Rimb. offensivi %", f"{h['orb_pct']:.0f} / {o['orb_pct']:.0f}", "casa / ospite"),
            ])
        cols = {"numero": "#", "giocatore": "Giocatore", "quintetto": "Q", "minuti": "Min",
                "punti": "Pt", "t2m": "2PM", "t2a": "2PA", "t3m": "3PM", "t3a": "3PA",
                "tlm": "TLM", "tla": "TLA", "rimb_off": "RO", "rimb_dif": "RD",
                "rimb_tot": "RT", "assist": "Ass", "perse": "Perse", "recuperate": "Rec",
                "stoppate": "Stop", "falli_commessi": "F", "valutazione": "Val",
                "game_score": "GmSc"}
        for team_id, name in ((row["squadra_casa_id"], row["casa"]),
                              (row["squadra_ospite_id"], row["ospite"])):
            section(name)
            b = bg[(bg["partita_id"] == pid) & (bg["squadra_id"] == team_id)].copy()
            b["game_score"] = A.game_score(b)
            b = b[list(cols)].rename(columns=cols)
            b["Q"] = b["Q"].map({1: "★", 0: ""})
            show(b)
    return pid
