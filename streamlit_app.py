"""Dashboard Streamlit: Serie A2 e Serie B Nazionale 2026/27.

Ottimizzata per iPad: filtri in alto (sempre visibili, anche in verticale),
tabelle a tutta larghezza, grafici leggibili al tocco.
"""

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from basket import analysis as A
from basket import config, db, scouting
from basket import views as V

BLU, ARANCIO, GRIGIO = "#2a78d6", "#eb6834", "#a3a29d"

st.set_page_config(page_title="LNP Stats 2026/27", page_icon="🏀", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown("""
<style>
  .block-container {padding-top: 2.6rem; padding-left: 1rem; padding-right: 1rem; max-width: 1400px;}
  div[data-baseweb="select"] > div {min-height: 46px; font-size: 1.05rem;}
  button[data-baseweb="tab"] {font-size: 1.05rem; padding: 0.6rem 0.9rem;}
  div[role="radiogroup"] label {padding: 0.25rem 0.6rem; font-size: 1rem;}
  [data-testid="stMetricValue"] {font-size: 1.7rem;}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ dati

@st.cache_data(show_spinner="Carico i dati…")
def load(db_mtime: float):
    conn = db.connect(config.DB_PATH, readonly=True)
    bs = A.load_box_squadra(conn)
    bg = A.load_box_giocatore(conn)
    partite = pd.read_sql_query(
        """SELECT p.*, sc.nome AS casa, so.nome AS ospite FROM partite p
           JOIN squadre sc ON sc.squadra_id = p.squadra_casa_id
           JOIN squadre so ON so.squadra_id = p.squadra_ospite_id""", conn)
    agg = conn.execute("SELECT MAX(scaricata_il) FROM partite").fetchone()[0]
    conn.close()
    return bs, bg, partite, agg


@st.cache_data
def report(db_mtime: float, squadra_id: int):
    conn = db.connect(config.DB_PATH, readonly=True)
    r = scouting.build_report(conn, squadra_id)
    conn.close()
    return r


def show(df: pd.DataFrame, height: int | None = None):
    """Tabella a tutta larghezza con decimali a 1 cifra."""
    df = df.copy()
    for c in df.select_dtypes("float").columns:
        df[c] = df[c].round(2 if "rate" in c.lower() else 1)
    st.dataframe(df, hide_index=True, use_container_width=True,
                 height=height or min(38 * (len(df) + 1) + 4, 640))


def chart_layout(fig, height=380, **kw):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=40, b=10),
                      legend=dict(orientation="h", y=1.12, x=0), hovermode="closest", **kw)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.18)", zeroline=False)
    return fig


if not config.DB_PATH.exists():
    st.error("Database non trovato (data/lnp.sqlite). Esegui prima il workflow di aggiornamento.")
    st.stop()

mtime = config.DB_PATH.stat().st_mtime
bs, bg, partite, aggiornato = load(mtime)
if bs.empty:
    st.warning("Nessuna partita nel database.")
    st.stop()

# ------------------------------------------------------------------ filtri

st.markdown(f"### 🏀 LNP Stats {config.STAGIONE_LABEL}")
camp_disp = [c for c in config.CAMPIONATI if c in set(bs["campionato_id"])]
f1, f2, f3 = st.columns(3)
camp = f1.selectbox("Campionato", camp_disp, format_func=lambda c: config.CAMPIONATI[c])
bs_c, bg_c = bs[bs["campionato_id"] == camp], bg[bg["campionato_id"] == camp]
squadre = bs_c.drop_duplicates("squadra_id").sort_values("squadra")
sq_opts = [None] + squadre["squadra_id"].tolist()
sq_names = dict(zip(squadre["squadra_id"], squadre["squadra"]))
sq = f2.selectbox("Squadra", sq_opts, format_func=lambda s: "Tutte" if s is None else sq_names[s])
gioc_pool = bg_c[bg_c["giocata"]]
if sq is not None:
    gioc_pool = gioc_pool[gioc_pool["squadra_id"] == sq]
gioc = gioc_pool.drop_duplicates("giocatore_id").sort_values("giocatore")
g_names = dict(zip(gioc["giocatore_id"], gioc["giocatore"] + " (" + gioc["squadra"] + ")"))
gid = f3.selectbox("Giocatore", [None] + list(g_names),
                   format_func=lambda g: "Tutti" if g is None else g_names[g])

n_partite = partite[partite["campionato_id"] == camp].shape[0]
st.caption(f"{n_partite} partite · ultima giornata {int(bs_c['giornata'].max())} · "
           f"aggiornato {str(aggiornato)[:10]} · fonte legapallacanestro.com")
n_incomplete = bs_c.loc[~bs_c["affidabile"], "partita_id"].nunique()
if n_incomplete:
    st.caption(f"ⓘ {n_incomplete} partite con box score ufficiale incompleto: valgono per "
               "risultati, punti e totali, ma sono escluse da percentuali e metriche avanzate "
               "(vedi scheda Partite).")

tab_cl, tab_sq, tab_gi, tab_g1, tab_sc, tab_pa = st.tabs(
    ["Classifica", "Squadre", "Giocatori", "Giocatore", "Scouting", "Partite"])

team_tot = A.team_summary(bs_c)

# ------------------------------------------------------------------ classifica
with tab_cl:
    show(V.select(A.standings(bs_c), V.CLASSIFICA).drop(columns="Campionato"))

# ------------------------------------------------------------------ squadre
with tab_sq:
    vista = st.radio("Vista", ["Medie", "Per 40'", "Avanzate", "Casa/Trasferta", "Ultime 5"],
                     horizontal=True, key="vista_sq")
    if vista == "Casa/Trasferta":
        t = V.casa_trasferta_squadre(bs_c if sq is None else bs_c[bs_c["squadra_id"] == sq])
    else:
        src = A.team_last_n(bs_c, 5) if vista == "Ultime 5" else team_tot
        if sq is not None:
            src = src[src["squadra_id"] == sq]
        mapping = {"Medie": V.TEAM_MEDIE, "Per 40'": V.TEAM_P40}.get(vista, V.TEAM_AVANZATE)
        t = V.select(src.sort_values("net_rtg", ascending=False), mapping)
    show(t.drop(columns="Campionato"))

    st.markdown("**Attacco e difesa** · ORtg vs DRtg (punti per 100 possessi; in alto a destra è meglio)")
    colors = [BLU if (sq is None or s == sq) else GRIGIO for s in team_tot["squadra_id"]]
    fig = go.Figure(go.Scatter(
        x=team_tot["ortg"], y=team_tot["drtg"], mode="markers+text" if sq else "markers",
        text=[n if s == sq else "" for n, s in zip(team_tot["squadra"], team_tot["squadra_id"])],
        textposition="top center",
        marker=dict(size=13, color=colors, line=dict(width=2, color="rgba(255,255,255,0.9)")),
        customdata=team_tot[["squadra", "net_rtg"]].values,
        hovertemplate="<b>%{customdata[0]}</b><br>ORtg %{x:.1f}<br>DRtg %{y:.1f}"
                      "<br>Net %{customdata[1]:+.1f}<extra></extra>"))
    fig.add_vline(x=team_tot["ortg"].mean(), line_dash="dot", line_color=GRIGIO)
    fig.add_hline(y=team_tot["drtg"].mean(), line_dash="dot", line_color=GRIGIO)
    chart_layout(fig, 440, xaxis_title="ORtg", yaxis_title="DRtg")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ giocatori
with tab_gi:
    c1, c2 = st.columns([3, 1])
    vista = c1.radio("Vista", ["Medie", "Totali", "Per 40'", "Avanzate", "Trend ult. 5",
                               "Casa/Trasferta"], horizontal=True, key="vista_gi")
    min_pg = c2.number_input("Min. partite", 0, 40, 1 if sq else 2)
    bg_f = bg_c if sq is None else bg_c[bg_c["squadra_id"] == sq]
    if vista == "Casa/Trasferta":
        t = V.casa_trasferta_giocatori(bg_f, bs)
        t = t[t["PG"] >= min_pg]
    elif vista == "Trend ult. 5":
        tr = A.player_trend(bg_f, bs)
        tr = tr[tr["partite"] >= min_pg].sort_values("valutazione_pg_delta", ascending=False)
        t = V.select(tr, V.TREND)
    else:
        p = A.player_summary(bg_f, bs, min_partite=min_pg)
        mapping = {"Medie": V.PLAYER_MEDIE, "Totali": V.PLAYER_TOTALI,
                   "Per 40'": V.PLAYER_P40}.get(vista, V.PLAYER_AVANZATE)
        if vista == "Per 40'":
            p = p[p["minuti_pg"] >= 10]
            st.caption("Per 40': solo giocatori con almeno 10 minuti di media.")
        t = V.select(p, mapping)
    if gid is not None:
        t = t[t["Giocatore"] == bg_c.loc[bg_c["giocatore_id"] == gid, "giocatore"].iloc[0]]
    show(t.drop(columns="Campionato"), height=600)

# ------------------------------------------------------------------ giocatore
with tab_g1:
    if gid is None:
        st.info("Seleziona un giocatore nel filtro in alto.")
    else:
        log = A.player_game_log(bg_c, gid)
        p = A.player_summary(bg_c[bg_c["giocatore_id"] == gid], bs).iloc[0]
        st.markdown(f"#### {p['giocatore']} · {p['squadra']}")
        m = st.columns(6)
        m[0].metric("Punti", f"{p['punti_pg']:.1f}")
        m[1].metric("Rimbalzi", f"{p['rimb_tot_pg']:.1f}")
        m[2].metric("Assist", f"{p['assist_pg']:.1f}")
        m[3].metric("Minuti", f"{p['minuti_pg']:.1f}")
        m[4].metric("TS%", f"{p['ts_pct']:.1f}")
        m[5].metric("USG%", f"{p['usg_pct']:.1f}")

        stat = st.radio("Andamento", ["punti", "valutazione", "rimb_tot", "assist", "minuti"],
                        horizontal=True, format_func=lambda s: {
                            "punti": "Punti", "valutazione": "Valutazione",
                            "rimb_tot": "Rimbalzi", "assist": "Assist", "minuti": "Minuti"}[s])
        x = [f"G{g} {a[:14]}" for g, a in zip(log["giornata"], log["avversario"])]
        fig = go.Figure()
        fig.add_bar(x=x, y=log[stat], name="Partita", marker_color=BLU, marker_cornerradius=4,
                    marker_line_width=0, hovertemplate="%{x}<br>%{y}<extra></extra>")
        roll = log[stat].rolling(5, min_periods=1).mean()
        fig.add_scatter(x=x, y=roll, name="Media mobile 5", mode="lines+markers",
                        line=dict(color=ARANCIO, width=2), marker=dict(size=8),
                        hovertemplate="Media ult. 5: %{y:.1f}<extra></extra>")
        chart_layout(fig, 360, bargap=0.35)
        st.plotly_chart(fig, use_container_width=True)

        cols = {"giornata": "G.", "data": "Data", "avversario": "Avversario", "casa": "Casa",
                "quintetto": "Q", "minuti": "Min", "punti": "Pt", "t2m": "2PM", "t2a": "2PA",
                "t3m": "3PM", "t3a": "3PA", "tlm": "TLM", "tla": "TLA", "rimb_off": "RO",
                "rimb_dif": "RD", "rimb_tot": "RT", "assist": "Ass", "perse": "Perse",
                "recuperate": "Rec", "stoppate": "Stop", "falli_commessi": "F",
                "valutazione": "Val", "efg_pct": "eFG%", "ts_pct": "TS%"}
        gl = log[list(cols)].rename(columns=cols).iloc[::-1]
        gl["Casa"] = gl["Casa"].map({1: "C", 0: "T"})
        gl["Q"] = gl["Q"].map({1: "*", 0: ""})
        show(gl)

        st.markdown("**Casa / trasferta**")
        show(V.casa_trasferta_giocatori(bg_c[bg_c["giocatore_id"] == gid], bs)
             .drop(columns=["Campionato", "Giocatore", "Squadra"]))

# ------------------------------------------------------------------ scouting
with tab_sc:
    if sq is None:
        st.info("Seleziona una squadra nel filtro in alto per il report di scouting.")
    else:
        r = report(mtime, sq)
        st.markdown(f"#### Scouting: {r.squadra}")
        st.markdown(f"{r.campionato} · record **{r.record}** · **{r.posizione}°** posto"
                    + (f"  \nProssima partita: {r.prossima}" if r.prossima else ""))
        a, b = st.columns(2)
        with a:
            st.markdown("**✅ Punti di forza**")
            for x in r.punti_forza or ["Nessuno marcato (servono più partite o più squadre)"]:
                st.markdown(f"- {x}")
        with b:
            st.markdown("**⚠️ Punti deboli**")
            for x in r.punti_deboli or ["Nessuno marcato"]:
                st.markdown(f"- {x}")

        st.markdown("**Four Factors** · squadra vs media campionato")
        ff = r.profilo[r.profilo["Metrica"].isin([
            "eFG% in attacco", "Palle perse % in attacco", "Rimbalzi offensivi %",
            "eFG% concessa", "Palle perse forzate %", "Rimbalzi difensivi %"])]
        fig = go.Figure()
        fig.add_bar(y=ff["Metrica"], x=ff["Valore"], name=r.squadra, orientation="h",
                    marker_color=BLU, marker_cornerradius=4,
                    hovertemplate="%{y}: %{x:.1f}<extra></extra>")
        fig.add_bar(y=ff["Metrica"], x=ff["Media campionato"], name="Media campionato",
                    orientation="h", marker_color=GRIGIO, marker_cornerradius=4,
                    hovertemplate="%{y}: %{x:.1f}<extra>media</extra>")
        chart_layout(fig, 380, barmode="group", bargap=0.3, bargroupgap=0.08)
        fig.update_yaxes(autorange="reversed", showgrid=False)
        fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.18)")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Profilo completo**")
        show(r.profilo)
        st.markdown("**Giocatori** (ordinati per minuti)")
        show(r.giocatori)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Ultime 5 partite**")
            show(r.ultime)
        with c2:
            st.markdown("**Casa / trasferta**")
            show(r.casa_trasferta)
            st.markdown("**Punti medi per periodo**")
            show(r.periodi)
        st.download_button("Scarica report (Markdown)", scouting.to_markdown(r),
                           file_name=f"scouting_{r.squadra}.md", mime="text/markdown")

# ------------------------------------------------------------------ partite
with tab_pa:
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
        if parz:
            st.caption("Parziali: " + ", ".join(f"{p['casa']}-{p['ospite']}" for p in parz))
        st.markdown(f"[Box score sul sito ufficiale]({row['url']})")
        if not bs.loc[bs["partita_id"] == pid, "affidabile"].all():
            st.warning("Box score ufficiale incompleto (tiri tentati, rimbalzi o perse non "
                       "registrati del tutto): partita esclusa da percentuali e metriche avanzate.")
        cols = {"numero": "#", "giocatore": "Giocatore", "quintetto": "Q", "minuti": "Min",
                "punti": "Pt", "t2m": "2PM", "t2a": "2PA", "t3m": "3PM", "t3a": "3PA",
                "tlm": "TLM", "tla": "TLA", "rimb_off": "RO", "rimb_dif": "RD",
                "rimb_tot": "RT", "assist": "Ass", "perse": "Perse", "recuperate": "Rec",
                "stoppate": "Stop", "falli_commessi": "F", "valutazione": "Val"}
        for side, team_id, name in (("casa", row["squadra_casa_id"], row["casa"]),
                                    ("ospite", row["squadra_ospite_id"], row["ospite"])):
            st.markdown(f"**{name}**")
            b = bg[(bg["partita_id"] == pid) & (bg["squadra_id"] == team_id)]
            b = b[list(cols)].rename(columns=cols)
            b["Q"] = b["Q"].map({1: "*", 0: ""})
            show(b)
        tr = A.team_ratings(bs[bs["partita_id"] == pid].copy())
        st.markdown("**Statistiche avanzate della partita**")
        show(V.select(tr, {"squadra": "Squadra", "possessi": "Possessi", "ortg": "ORtg",
                           "drtg": "DRtg", "efg_pct": "eFG%", "ts_pct": "TS%",
                           "tov_pct": "TOV%", "orb_pct": "OREB%", "ft_rate": "FT rate",
                           "ast_ratio": "AST ratio"}).drop(columns="Campionato",
                                                           errors="ignore"))
