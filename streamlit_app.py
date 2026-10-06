"""Dashboard Streamlit: Serie A2 e Serie B Nazionale 2026/27.

Ottimizzata per iPad: filtri in alto (sempre visibili, anche in verticale),
schede a griglia che si adattano alla larghezza, grafici leggibili al tocco.
"""

import html
import json

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from basket import analysis as A
from basket import config, db, scouting
from basket.glossario import G, voci_per_colonne
from basket import views as V

# Palette dei grafici (validata per il fondo scuro: contrasto e daltonismo)
BLU, ARANCIO, ACQUA = "#3987e5", "#d95926", "#199e70"
GRIGIO = "#5b6478"
SUPERFICIE = "#141d30"
TESTO, TESTO_2 = "#e6eaf2", "#97a1b5"
NEUTRO = "#2a3346"

st.set_page_config(page_title="LNP Stats 2026/27", page_icon="🏀", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

:root {
  --bg: #0b1220; --surface: #141d30; --surface-2: #1a2540; --line: #24304a;
  --text: #e6eaf2; --text-2: #97a1b5; --muted: #6b7489; --accent: #ff7a1a;
  --pos: #3987e5; --neg: #d95926;
}
.block-container {padding-top: 3.4rem; padding-left: 1rem; padding-right: 1rem; max-width: 1400px;}
h1, h2, h3, h4 {font-family: 'Barlow Condensed', sans-serif !important; letter-spacing: .01em;}

/* Testata */
.hero {
  position: relative; overflow: hidden; border-radius: 16px; padding: 22px 24px 18px;
  background:
    radial-gradient(120% 140% at 100% 0%, rgba(255,122,26,.20) 0%, rgba(255,122,26,0) 55%),
    linear-gradient(135deg, #111a2e 0%, #0e1628 100%);
  border: 1px solid var(--line); margin-bottom: 14px;
}
.hero svg.court {position: absolute; right: -40px; top: -30px; width: 320px; opacity: .10;}
.hero .eyebrow {font: 600 .78rem 'Inter', sans-serif; letter-spacing: .14em;
  text-transform: uppercase; color: var(--accent);}
.hero .title {font: 700 2.3rem/1.05 'Barlow Condensed', sans-serif; color: var(--text);
  margin: 4px 0 6px; text-transform: uppercase;}
.hero .meta {color: var(--text-2); font-size: .9rem;}

/* Schede numeriche */
.kpis {display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin: 4px 0 18px;}
@media (min-width: 700px) {.kpis {grid-template-columns: repeat(3, 1fr);}}
@media (min-width: 1150px) {.kpis {grid-template-columns: repeat(6, 1fr);}}
.kpi {background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
  padding: 12px 14px;}
.kpi .l {font: 600 .7rem 'Inter', sans-serif; letter-spacing: .1em; text-transform: uppercase;
  color: var(--text-2);}
.kpi .v {font: 700 2rem/1.1 'Barlow Condensed', sans-serif; color: var(--text); margin-top: 2px;}
.kpi .s {font-size: .8rem; color: var(--muted); margin-top: 2px; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis;}

/* Titoli di sezione */
.sec {display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin: 18px 0 8px;
  border-left: 3px solid var(--accent); padding-left: 10px;}
.sec .t {font: 700 1.35rem 'Barlow Condensed', sans-serif; text-transform: uppercase;
  letter-spacing: .03em; color: var(--text);}
.sec .d {color: var(--text-2); font-size: .85rem;}

/* Leader */
.leaders {display: grid; grid-template-columns: 1fr; gap: 10px;}
@media (min-width: 560px) {.leaders {grid-template-columns: repeat(3, 1fr);}}
.lcard {background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
  padding: 12px 14px 8px;}
.lcard .h {font: 600 .72rem 'Inter', sans-serif; letter-spacing: .1em; text-transform: uppercase;
  color: var(--accent); margin-bottom: 6px;}
.lrow {display: grid; grid-template-columns: 18px 1fr auto; gap: 8px; align-items: baseline;
  padding: 5px 0; border-top: 1px solid rgba(255,255,255,.05);}
.lrow:first-of-type {border-top: none;}
.lrow .r {color: var(--muted); font: 600 .85rem 'Barlow Condensed', sans-serif;}
.lrow .n {color: var(--text); font-size: .9rem; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis;}
.lrow .n small {display: block; color: var(--muted); font-size: .72rem;}
.lrow .x {font: 700 1.15rem 'Barlow Condensed', sans-serif; color: var(--text);}
.lrow:first-of-type .x {color: var(--accent);}

/* Elenchi forza / debolezza */
.pill-list {display: flex; flex-direction: column; gap: 6px;}
.pill {background: var(--surface); border: 1px solid var(--line); border-radius: 10px;
  padding: 8px 12px; font-size: .88rem; color: var(--text);}
.pill.pos {border-left: 3px solid var(--pos);} .pill.neg {border-left: 3px solid var(--neg);}

/* Controlli più grandi per il tocco */
div[data-baseweb="select"] > div {min-height: 46px; font-size: 1.02rem;}
button[data-baseweb="tab"] {font: 600 1.02rem 'Barlow Condensed', sans-serif;
  text-transform: uppercase; letter-spacing: .05em; padding: .6rem .9rem;}
div[role="radiogroup"] label {padding: .25rem .55rem;}
[data-testid="stMetricValue"] {font-family: 'Barlow Condensed', sans-serif;}
.note {color: var(--text-2); font-size: .82rem; margin: -4px 0 10px;}

/* Pulsante "?" e finestra di spiegazione (funziona al tocco, si chiude toccando fuori) */
details.tip {display: inline-block; vertical-align: middle; margin-left: 6px;}
details.tip > summary {list-style: none; cursor: pointer; display: inline-flex;
  align-items: center; justify-content: center; width: 21px; height: 21px; border-radius: 50%;
  border: 1px solid #33415f; background: var(--surface-2); color: var(--text-2);
  font: 600 12px/1 'Inter', sans-serif; text-transform: none; letter-spacing: 0;
  -webkit-tap-highlight-color: transparent;}
details.tip > summary::-webkit-details-marker {display: none;}
details.tip > summary:hover, details.tip[open] > summary {border-color: var(--accent);
  color: var(--accent);}
details.tip[open] > summary::before {content: ""; position: fixed; inset: 0; z-index: 999990;
  background: rgba(4, 8, 16, .62); cursor: default;}
details.tip .bubble {position: fixed; z-index: 999991; left: 50%; top: 50%;
  transform: translate(-50%, -50%); width: min(460px, 90vw); max-height: 78vh; overflow: auto;
  background: #18223a; border: 1px solid #2f3d5e; border-radius: 16px; padding: 18px 20px 14px;
  box-shadow: 0 24px 70px rgba(0, 0, 0, .55); text-align: left; text-transform: none;
  letter-spacing: normal; white-space: normal; color: var(--text);
  font: 400 .93rem/1.5 'Inter', sans-serif;}
.bubble .bt {font: 700 1.35rem/1.15 'Barlow Condensed', sans-serif; text-transform: uppercase;
  letter-spacing: .02em; color: var(--text); margin-bottom: 10px; padding-right: 20px;}
.bubble .bk {font: 600 .68rem 'Inter', sans-serif; letter-spacing: .12em;
  text-transform: uppercase; color: var(--accent); margin-top: 10px;}
.bubble p {margin: 2px 0 0; color: var(--text);}
.bubble .entry + .entry {border-top: 1px solid #2a3654; margin-top: 14px; padding-top: 12px;}
.bubble .bx {color: var(--muted); font-size: .75rem; margin-top: 14px; text-align: center;}
details.tip.legend {display: block; margin: 0 0 6px;}
details.tip.legend > summary {width: auto; height: auto; padding: 5px 12px; border-radius: 999px;
  font-size: .8rem; gap: 6px;}
details.tip.legend > summary b {display: inline-flex; width: 17px; height: 17px;
  border-radius: 50%; align-items: center; justify-content: center; border: 1px solid currentColor;
  font-size: 11px;}
</style>
""", unsafe_allow_html=True)

COURT_SVG = """<svg class="court" viewBox="0 0 200 200" fill="none" stroke="#ff7a1a"
stroke-width="2.5"><circle cx="100" cy="100" r="96"/><path d="M100 4v192M4 100h192"/>
<path d="M30 30c40 25 40 115 0 140M170 30c-40 25-40 115 0 140"/></svg>"""


def _template():
    t = go.layout.Template()
    axis = dict(gridcolor="rgba(255,255,255,0.06)", linecolor="rgba(255,255,255,0.12)",
                zeroline=False, tickfont=dict(color=TESTO_2), title=dict(font=dict(color=TESTO_2)),
                automargin=True)
    t.layout = go.Layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=TESTO_2, size=13),
        colorway=[BLU, ARANCIO, ACQUA], xaxis=axis, yaxis=axis,
        hoverlabel=dict(bgcolor="#1a2540", bordercolor="#24304a",
                        font=dict(color=TESTO, family="Inter, sans-serif")),
        legend=dict(orientation="h", y=1.1, x=0, font=dict(color=TESTO_2)),
        margin=dict(l=10, r=10, t=36, b=10),
    )
    return t


pio.templates["lnp"] = _template()
pio.templates.default = "lnp"


# ------------------------------------------------------------------ helper grafici e HTML

def esc(x) -> str:
    return html.escape(str(x))


# Etichette mostrate in dashboard -> voce del glossario (per il pulsante "?")
TIPS = {
    "Ritmo": "pace", "Rating offensivo": "ortg", "Miglior Net Rtg": "net_rtg",
    "Net rating": "net_rtg", "Leader": "leader", "Mappa del campionato": "mappa",
    "Da dove arrivano i punti": "distribuzione", "Differenza punti per quarto": "quarti",
    "Quarto per quarto": "quarti", "Game Score": "game_score",
    "True shooting % (≥ 6 tiri)": "ts", "True shooting": "ts", "Usage %": "usg",
    "Usage": "usg", "Valutazione": "valutazione", "Profilo": "percentili",
    "Punto a punto": "punto_a_punto", "Fortuna": "fortuna", "Punti panchina": "panchina",
    "Top 2 realizzatori": "top2", "Four Factors": "four_factors", "Possessi": "possessi",
    "ORtg": "ortg", "eFG%": "efg", "Palle perse %": "tov", "Rimb. offensivi %": "orb",
}


def _entry(v) -> str:
    return (f'<div class="entry"><div class="bt">{esc(v.titolo)}</div>'
            f'<div class="bk">Cosa misura</div><p>{esc(v.cosa)}</p>'
            f'<div class="bk">Come si calcola</div><p>{esc(v.calcolo)}</p>'
            f'<div class="bk">Come leggerlo</div><p>{esc(v.lettura)}</p></div>')


def tip(key: str | None) -> str:
    """Pulsante "?" che apre la spiegazione della statistica."""
    v = G.get(key) if key else None
    if v is None:
        return ""
    return (f'<details class="tip"><summary aria-label="Spiegazione: {esc(v.titolo)}">?</summary>'
            f'<div class="bubble">{_entry(v)}<div class="bx">Tocca fuori per chiudere</div>'
            '</div></details>')


def legend(voci) -> str:
    """Pulsante unico con la spiegazione di più statistiche (per le tabelle)."""
    if not voci:
        return ""
    body = "".join(_entry(v) for v in voci)
    return ('<details class="tip legend"><summary><b>?</b> Cosa significano le colonne</summary>'
            f'<div class="bubble">{body}<div class="bx">Tocca fuori per chiudere</div>'
            '</div></details>')


def section(title: str, desc: str = "", key: str | None = None):
    k = key or TIPS.get(title)
    st.markdown(f'<div class="sec"><span class="t">{esc(title)}</span>{tip(k)}'
                f'<span class="d">{esc(desc)}</span></div>', unsafe_allow_html=True)


def kpis(items: list[tuple[str, str, str]]):
    cards = "".join(f'<div class="kpi"><div class="l">{esc(l)}{tip(TIPS.get(l))}</div>'
                    f'<div class="v">{esc(v)}</div><div class="s">{esc(s)}</div></div>'
                    for l, v, s in items)
    st.markdown(f'<div class="kpis">{cards}</div>', unsafe_allow_html=True)


def leader_cards(cards: list[tuple[str, pd.DataFrame, str, str]]):
    """cards: (titolo, dataframe, colonna valore, formato)"""
    out = []
    for title, df, col, fmt in cards:
        rows = "".join(
            f'<div class="lrow"><span class="r">{i}</span><span class="n">{esc(r.giocatore)}'
            f'<small>{esc(r.squadra)}</small></span>'
            f'<span class="x">{getattr(r, col):{fmt}}</span></div>'
            for i, r in enumerate(df.itertuples(), start=1))
        out.append(f'<div class="lcard"><div class="h">{esc(title)}{tip(TIPS.get(title))}</div>'
                   f'{rows}</div>')
    st.markdown(f'<div class="leaders">{"".join(out)}</div>', unsafe_allow_html=True)


def pills(items: list[str], kind: str, empty: str):
    body = "".join(f'<div class="pill {kind}">{esc(x)}</div>' for x in items) or \
        f'<div class="pill">{esc(empty)}</div>'
    st.markdown(f'<div class="pill-list">{body}</div>', unsafe_allow_html=True)


def show(df: pd.DataFrame, height: int | None = None, progress: dict | None = None,
         voci: list | None = None):
    """Tabella a tutta larghezza. progress: {colonna: (min, max)} per le barre nelle celle.
    Sopra la tabella compare il pulsante "?" con la spiegazione delle colonne complesse."""
    spiegazioni = voci if voci is not None else voci_per_colonne(df.columns)
    if spiegazioni:
        st.markdown(legend(spiegazioni), unsafe_allow_html=True)
    cfg = {}
    for c in df.select_dtypes("float").columns:
        two = any(k in c for k in ("rate", "FTA/FGA", "Variabilità"))
        cfg[c] = st.column_config.NumberColumn(format="%.2f" if two else "%.1f")
    for c, (lo, hi) in (progress or {}).items():
        if c in df.columns:
            cfg[c] = st.column_config.ProgressColumn(c, min_value=lo, max_value=hi, format="%.1f")
    st.dataframe(df, hide_index=True, use_container_width=True, column_config=cfg,
                 height=height or min(36 * (len(df) + 1) + 4, 640))


def plot(fig, height=380, **layout):
    fig.update_layout(height=height, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", **layout)
    st.plotly_chart(fig, use_container_width=True, theme=None,
                    config={"displayModeBar": False})


GENERICI = {"basket", "pallacanestro", "basketball", "knights", "bees", "sharks", "academy"}


def short(name: str) -> str:
    """Nome breve per le etichette dei grafici: di solito la città (es. 'Ruvo di Puglia')."""
    words = [w for w in name.split() if not w.isdigit() and w.lower() not in GENERICI]
    if not words:
        return name
    if len(words) >= 3 and words[-2].islower():
        return " ".join(words[-3:])
    if len(words) >= 2 and words[-1][0].islower():
        return " ".join(words[-2:])
    return words[-1]


# ------------------------------------------------------------------ dati

@st.cache_data(show_spinner="Carico i dati…")
def load(db_mtime: float):
    conn = db.connect(config.DB_PATH, readonly=True)
    bs = A.load_box_squadra(conn)
    bg = A.load_box_giocatore(conn)
    quarters = A.load_quarters(conn)
    partite = pd.read_sql_query(
        """SELECT p.*, sc.nome AS casa, so.nome AS ospite FROM partite p
           JOIN squadre sc ON sc.squadra_id = p.squadra_casa_id
           JOIN squadre so ON so.squadra_id = p.squadra_ospite_id""", conn)
    agg = conn.execute("SELECT MAX(scaricata_il) FROM partite").fetchone()[0]
    conn.close()
    return bs, bg, quarters, partite, agg


@st.cache_data
def stats(db_mtime: float, camp: str):
    bs, bg, quarters, _, _ = load(db_mtime)
    bs_c, bg_c = bs[bs["campionato_id"] == camp], bg[bg["campionato_id"] == camp]
    players = A.player_summary(bg_c, bs)
    profile = A.team_profile(bs_c, bg_c, quarters[quarters["campionato_id"] == camp])
    return players, profile


@st.cache_data
def report(db_mtime: float, squadra_id: int):
    conn = db.connect(config.DB_PATH, readonly=True)
    r = scouting.build_report(conn, squadra_id)
    conn.close()
    return r


if not config.DB_PATH.exists():
    st.error("Database non trovato (data/lnp.sqlite). Esegui prima il workflow di aggiornamento.")
    st.stop()

mtime = config.DB_PATH.stat().st_mtime
bs, bg, quarters, partite, aggiornato = load(mtime)
if bs.empty:
    st.warning("Nessuna partita nel database.")
    st.stop()

# ------------------------------------------------------------------ testata e filtri

camp_disp = [c for c in config.CAMPIONATI if c in set(bs["campionato_id"])]
hero = st.empty()
f1, f2, f3 = st.columns(3)
camp = f1.selectbox("Campionato", camp_disp, format_func=lambda c: config.CAMPIONATI[c])
bs_c, bg_c = bs[bs["campionato_id"] == camp], bg[bg["campionato_id"] == camp]
players, profile = stats(mtime, camp)
squadre = profile.sort_values("squadra")
sq_names = dict(zip(squadre["squadra_id"], squadre["squadra"]))
sq = f2.selectbox("Squadra", [None] + list(sq_names),
                  format_func=lambda s: "Tutte" if s is None else sq_names[s])
pool = players if sq is None else players[players["squadra_id"] == sq]
pool = pool.sort_values("giocatore")
g_names = {(r.giocatore_id, r.squadra_id): f"{r.giocatore} ({r.squadra})"
           for r in pool.itertuples()}
gsel = f3.selectbox("Giocatore", [None] + list(g_names),
                    format_func=lambda g: "Tutti" if g is None else g_names[g])

ultima = int(bs_c["giornata"].max())
n_partite = bs_c["partita_id"].nunique()
hero.markdown(
    f'<div class="hero">{COURT_SVG}<div class="eyebrow">Stagione {config.STAGIONE_LABEL} · '
    f'{esc(config.CAMPIONATI[camp])}</div><div class="title">LNP Stats</div>'
    f'<div class="meta">{n_partite} partite · fino alla {ultima}ª giornata · aggiornato '
    f'{esc(str(aggiornato)[:10])} · fonte legapallacanestro.com</div></div>',
    unsafe_allow_html=True)
n_incomplete = bs_c.loc[~bs_c["affidabile"], "partita_id"].nunique()
if n_incomplete:
    st.markdown(f'<div class="note">{n_incomplete} partite con box score ufficiale incompleto: '
                'contano per risultati e totali, non per percentuali e metriche avanzate.'
                f'{tip("incompleto")}</div>', unsafe_allow_html=True)

tab_pan, tab_cl, tab_sq, tab_gi, tab_g1, tab_sc, tab_pa = st.tabs(
    ["Panoramica", "Classifica", "Squadre", "Giocatori", "Giocatore", "Scouting", "Partite"])

# ------------------------------------------------------------------ panoramica
with tab_pan:
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

# ------------------------------------------------------------------ classifica
with tab_cl:
    cl = A.standings(bs_c).merge(
        profile[["squadra_id", "pyth_pct", "fortuna", "record_pp", "sos"]], on="squadra_id")
    forma = (bs_c.sort_values(["data", "partita_id"]).groupby("squadra_id")["vinta"]
             .apply(lambda s: " ".join("V" if v else "P" for v in s.tail(5))))
    cl["forma"] = cl["squadra_id"].map(forma)
    cols = {"pos": "Pos", "squadra": "Squadra", "punti_classifica": "Pt", "vinte": "V",
            "perse_partite": "P", "forma": "Ultime 5", "diff": "Diff", "net_rtg": "Net Rtg",
            "pyth_pct": "V% attesa", "fortuna": "Fortuna", "record_pp": "Punto a punto",
            "sos": "Calendario", "punti": "PF", "punti_subiti": "PS", "ortg": "ORtg",
            "drtg": "DRtg", "partite": "PG"}
    show(V.select(cl, cols), height=36 * (len(cl) + 1) + 4,
         progress={"V% attesa": (0, 100)})
# ------------------------------------------------------------------ squadre
with tab_sq:
    vista = st.radio("Vista", ["Avanzate", "Profilo", "Quarti", "Medie", "Per 40'",
                               "Casa/Trasferta", "Ultime 5"], horizontal=True, key="vista_sq")
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
        show(V.select(src.sort_values("net_rtg", ascending=False), mapping)
             .drop(columns="Campionato"))

# ------------------------------------------------------------------ giocatori
with tab_gi:
    c1, c2 = st.columns([4, 1])
    vista = c1.radio("Vista", ["Medie", "Avanzate", "Ruolo", "Per 40'", "Totali", "Trend ult. 5",
                               "Casa/Trasferta"], horizontal=True, key="vista_gi")
    min_pg = c2.number_input("Min. partite", 0, 40, 1 if sq else 2)
    bg_f = bg_c if sq is None else bg_c[bg_c["squadra_id"] == sq]
    p = pool[pool["partite"] >= min_pg].sort_values("punti_pg", ascending=False)
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
        mapping = {"Medie": V.PLAYER_MEDIE, "Totali": V.PLAYER_TOTALI, "Per 40'": V.PLAYER_P40,
                   "Ruolo": V.PLAYER_RUOLO}.get(vista, V.PLAYER_AVANZATE)
        t = V.select(p, mapping)
    if gsel is not None:
        nome = players.loc[players["giocatore_id"] == gsel[0], "giocatore"].iloc[0]
        t = t[t["Giocatore"] == nome]
    show(t.drop(columns="Campionato"), height=620,
         progress={"USG%": (0, 40), "TS%": (0, 80)} if vista == "Avanzate" else None)

# ------------------------------------------------------------------ giocatore
with tab_g1:
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
            f'{int(me["quintetti"])} in quintetto · {me["minuti_pg"]:.1f} minuti di media · '
            f'massimo {int(me["max_punti"])} punti</div></div>', unsafe_allow_html=True)

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

# ------------------------------------------------------------------ scouting
with tab_sc:
    if sq is None:
        st.info("Seleziona una squadra nel filtro in alto per il report di scouting.")
    else:
        r = report(mtime, sq)
        pf = profile[profile["squadra_id"] == sq].iloc[0]
        st.markdown(
            f'<div class="hero" style="padding:16px 20px">{COURT_SVG}<div class="eyebrow">'
            f'Report di scouting · {esc(r.campionato)}</div><div class="title" '
            f'style="font-size:2rem">{esc(r.squadra)}</div><div class="meta">Record '
            f'{esc(r.record)} · {r.posizione}° posto'
            + (f' · prossima: {esc(r.prossima)}' if r.prossima else "") + '</div></div>',
            unsafe_allow_html=True)
        kpis([
            ("Net rating", f"{pf['net_rtg']:+.1f}", f"ORtg {pf['ortg']:.1f} · DRtg {pf['drtg']:.1f}"),
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
        show(r.giocatori, progress={"USG%": (0, 40)})
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
