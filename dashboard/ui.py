"""Componenti grafici condivisi della dashboard: stile, schede, tabelle, grafici, "?"."""

import html
import re

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from basket.glossario import G, voci_per_colonne

# Palette dei grafici (validata per il fondo scuro: contrasto e daltonismo)
BLU, ARANCIO, ACQUA = "#3987e5", "#d95926", "#199e70"
GRIGIO = "#5b6478"
SUPERFICIE = "#111722"
TESTO, TESTO_2 = "#e8ecf3", "#a3acbd"
NEUTRO = "#2a3346"

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Inter:wght@400;500;600;700&display=swap');

    /* ------------------------------------------------------------ token */
    :root {
      --bg: #0a0e15; --surface: #111722; --surface-2: #161d2b; --surface-3: #1c2434;
      --line: rgba(255,255,255,.075); --line-2: rgba(255,255,255,.14);
      --text: #e8ecf3; --text-2: #a3acbd; --muted: #6f7a8e; --accent: #ff7a1a;
      --accent-soft: rgba(255,122,26,.12); --pos: #3987e5; --neg: #d95926; --ok: #199e70;
      --shadow: 0 1px 0 rgba(255,255,255,.035) inset, 0 8px 24px rgba(0,0,0,.28);
      --r: 12px;
    }
    html, body, [data-testid="stAppViewContainer"] {
      font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
      font-feature-settings: 'cv11', 'ss01', 'tnum'; -webkit-font-smoothing: antialiased;}
    [data-testid="stAppViewContainer"] {
      background:
        radial-gradient(900px 420px at 85% -120px, rgba(57,135,229,.10), transparent 70%),
        radial-gradient(700px 360px at -10% -80px, rgba(255,122,26,.07), transparent 70%),
        var(--bg);}
    .block-container {padding-top: 3.8rem; padding-left: 1.25rem; padding-right: 1.25rem;
      max-width: 1440px;}
    h1, h2, h3, h4 {font-family: 'Inter', sans-serif !important; letter-spacing: -.015em;
      font-weight: 650 !important;}
    ::selection {background: rgba(57,135,229,.35);}

    /* ------------------------------------------------------------ navigazione */
    header[data-testid="stHeader"] {background: rgba(10,14,21,.78) !important;
      backdrop-filter: saturate(160%) blur(14px); -webkit-backdrop-filter: saturate(160%) blur(14px);
      border-bottom: 1px solid var(--line);}
    header [data-testid="stTopNavLink"], header [data-testid="stTopNavSection"] {
      font: 500 .92rem 'Inter', sans-serif !important; letter-spacing: -.005em;
      text-transform: none; min-height: 40px; color: var(--text-2) !important;
      border-radius: 8px !important;}
    header [data-testid="stTopNavLink"]:hover, header [data-testid="stTopNavSection"]:hover {
      color: var(--text) !important; background: rgba(255,255,255,.04) !important;}
    header [data-testid="stTopNavLink"][aria-current="page"],
    header [data-testid="stTopNavLink"][data-active="true"] {color: var(--text) !important;
      background: rgba(255,255,255,.06) !important;
      box-shadow: inset 0 -2px 0 var(--accent);}
    @media (max-width: 1024px) {
      header [data-testid="stTopNavLink"], header [data-testid="stTopNavSection"] {
        font-size: .84rem !important; padding-left: .35rem !important;
        padding-right: .35rem !important;}
    }
    @media (max-width: 700px) {
      header [data-testid="stTopNavLink"], header [data-testid="stTopNavSection"] {
        font-size: .78rem !important;}
    }

    /* ------------------------------------------------------------ barra del marchio */
    .topbar {display: flex; align-items: center; gap: 12px; margin: 0 0 14px; flex-wrap: wrap; width: 100%;
      padding-bottom: 12px; border-bottom: 1px solid var(--line);}
    .topbar svg {flex: none; width: 30px; height: 30px; border-radius: 8px;}
    .topbar .nome {font: 700 1.3rem/1 'Barlow Condensed', sans-serif; letter-spacing: .08em;
      color: var(--text);}
    .topbar .meta {color: var(--muted); font-size: .8rem; letter-spacing: .01em;}
    .pagina {font: 650 1.75rem/1.15 'Inter', sans-serif; letter-spacing: -.025em;
      color: var(--text); margin: 6px 0 2px;}
    .pagina-d {color: var(--text-2); font-size: .92rem; margin-bottom: 14px;}

    /* ------------------------------------------------------------ testata */
    .hero {position: relative; overflow: hidden; border-radius: 16px; padding: 24px 26px 20px;
      background:
        linear-gradient(180deg, rgba(255,255,255,.025), rgba(255,255,255,0) 40%),
        radial-gradient(120% 160% at 100% 0%, rgba(57,135,229,.16) 0%, rgba(57,135,229,0) 52%),
        var(--surface);
      border: 1px solid var(--line); margin-bottom: 16px; box-shadow: var(--shadow);}
    .hero::before {content: ""; position: absolute; inset: 0 0 auto 0; height: 2px;
      background: linear-gradient(90deg, var(--accent), rgba(255,122,26,0) 60%);}
    .hero svg.court {position: absolute; right: 0; top: 0; height: 100%; width: auto;
      opacity: .55; pointer-events: none;}
    .hero .eyebrow {font: 600 .7rem 'Inter', sans-serif; letter-spacing: .16em;
      text-transform: uppercase; color: var(--accent);}
    .hero .title {font: 700 2.05rem/1.1 'Inter', sans-serif; letter-spacing: -.03em;
      color: var(--text); margin: 6px 0 6px; text-transform: none;}
    .hero .meta {color: var(--text-2); font-size: .9rem;}
    .hero .brand {display: flex; align-items: center; gap: 16px; margin-top: 8px;}
    .hero .brand svg {flex: none; border-radius: 14px; box-shadow: 0 8px 24px rgba(0,0,0,.4);}
    .hero .brand .title {font: 700 2.3rem/1 'Barlow Condensed', sans-serif; letter-spacing: .06em;}
    .hero .tagline {font: 600 .66rem 'Inter', sans-serif; letter-spacing: .16em;
      text-transform: uppercase; color: var(--muted); margin-top: 4px;}

    /* ------------------------------------------------------------ titoli di sezione */
    .sec {display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin: 30px 0 12px;
      padding-bottom: 10px; border-bottom: 1px solid var(--line); position: relative;}
    .sec::before {content: ""; width: 6px; height: 6px; border-radius: 2px;
      background: var(--accent); align-self: center; flex: none;}
    .sec .t {font: 650 1.08rem 'Inter', sans-serif; letter-spacing: -.01em; color: var(--text);
      text-transform: none;}
    .sec .d {color: var(--muted); font-size: .84rem;}

    /* ------------------------------------------------------------ schede numeriche */
    .kpis {display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin: 6px 0 20px;}
    @media (min-width: 700px) {.kpis {grid-template-columns: repeat(3, 1fr);}}
    @media (min-width: 1150px) {.kpis {grid-template-columns: repeat(6, 1fr);}}
    .kpi {position: relative; background: linear-gradient(180deg, var(--surface-2), var(--surface));
      border: 1px solid var(--line); border-radius: var(--r); padding: 14px 16px 12px;
      box-shadow: var(--shadow); transition: border-color .15s ease, transform .15s ease;}
    .kpi:hover {border-color: var(--line-2); transform: translateY(-1px);}
    .kpi .l {font: 600 .66rem 'Inter', sans-serif; letter-spacing: .1em; text-transform: uppercase;
      color: var(--muted); display: flex; align-items: center; gap: 2px;}
    .kpi .v {font: 650 1.85rem/1.15 'Inter', sans-serif; letter-spacing: -.03em; color: var(--text);
      margin-top: 6px; font-variant-numeric: tabular-nums;}
    .kpi .s {font-size: .78rem; color: var(--text-2); margin-top: 4px; white-space: nowrap;
      overflow: hidden; text-overflow: ellipsis;}

    /* ------------------------------------------------------------ frase di sintesi */
    .frase {background: linear-gradient(180deg, var(--surface-2), var(--surface));
      border: 1px solid var(--line); border-left: 2px solid var(--accent); border-radius: var(--r);
      padding: 14px 18px; margin: 8px 0 16px; color: var(--text); font-size: .98rem;
      line-height: 1.55; box-shadow: var(--shadow);}
    .frase b {font: 600 .66rem 'Inter', sans-serif; letter-spacing: .16em; color: var(--accent);
      text-transform: uppercase; display: block; margin-bottom: 6px;}
    .frase li {margin: 3px 0;} .frase li::marker {color: var(--muted);}

    /* ------------------------------------------------------------ badge */
    .badge {display: inline-block; font: 600 .7rem 'Inter', sans-serif; padding: 2px 8px;
      border-radius: 6px; background: rgba(255,255,255,.04); color: var(--text-2);
      border: 1px solid var(--line); margin-left: 6px; vertical-align: middle;
      font-variant-numeric: tabular-nums;}
    .badge.top {color: #8fbcf3; background: rgba(57,135,229,.10); border-color: rgba(57,135,229,.32);}
    .badge.low {color: #f09a78; background: rgba(217,89,38,.10); border-color: rgba(217,89,38,.32);}
    .badge.warn {color: #f3c77a; background: rgba(243,199,122,.08); border-color: rgba(243,199,122,.3);}

    /* ------------------------------------------------------------ schede della Home */
    .cards {display: grid; grid-template-columns: 1fr; gap: 12px; margin: 8px 0 16px;}
    @media (min-width: 760px) {.cards {grid-template-columns: repeat(2, 1fr);}}
    @media (min-width: 1150px) {.cards.tre {grid-template-columns: repeat(3, 1fr);}}
    .card {background: linear-gradient(180deg, var(--surface-2), var(--surface));
      border: 1px solid var(--line); border-radius: 14px; padding: 18px 20px;
      box-shadow: var(--shadow); transition: border-color .15s ease;}
    .card:hover {border-color: var(--line-2);}
    .card .h {font: 600 .66rem 'Inter', sans-serif; letter-spacing: .14em; color: var(--accent);
      text-transform: uppercase;}
    .card .t {font: 650 1.3rem/1.25 'Inter', sans-serif; letter-spacing: -.02em; color: var(--text);
      margin: 8px 0 4px; text-transform: none;}
    .card .m {color: var(--text-2); font-size: .88rem; line-height: 1.55;}
    .card .big {font: 650 2.2rem/1 'Inter', sans-serif; letter-spacing: -.03em; color: var(--text);
      font-variant-numeric: tabular-nums;}
    .card .row {display: flex; gap: 26px; flex-wrap: wrap; margin-top: 12px;
      padding-top: 12px; border-top: 1px solid var(--line);}
    .card .row div {min-width: 90px; font: 600 1.15rem 'Inter', sans-serif; color: var(--text);
      font-variant-numeric: tabular-nums;}
    .card .row small {display: block; color: var(--muted); font: 600 .64rem 'Inter', sans-serif;
      text-transform: uppercase; letter-spacing: .1em; margin-bottom: 3px;}

    /* ------------------------------------------------------------ leader */
    .leaders {display: grid; grid-template-columns: 1fr; gap: 12px;}
    @media (min-width: 560px) {.leaders {grid-template-columns: repeat(3, 1fr);}}
    .lcard {background: linear-gradient(180deg, var(--surface-2), var(--surface));
      border: 1px solid var(--line); border-radius: var(--r); padding: 14px 16px 8px;
      box-shadow: var(--shadow);}
    .lcard .h {font: 600 .66rem 'Inter', sans-serif; letter-spacing: .12em; text-transform: uppercase;
      color: var(--muted); margin-bottom: 6px;}
    .lrow {display: grid; grid-template-columns: 20px 1fr auto; gap: 10px; align-items: baseline;
      padding: 7px 0; border-top: 1px solid var(--line);}
    .lrow:first-of-type {border-top: none;}
    .lrow .r {color: var(--muted); font: 600 .78rem 'Inter', sans-serif;
      font-variant-numeric: tabular-nums;}
    .lrow .n {color: var(--text); font-size: .9rem; white-space: nowrap; overflow: hidden;
      text-overflow: ellipsis;}
    .lrow .n small {display: block; color: var(--muted); font-size: .72rem;}
    .lrow .x {font: 650 1.02rem 'Inter', sans-serif; color: var(--text);
      font-variant-numeric: tabular-nums;}
    .lrow:first-of-type .x {color: var(--accent);}

    /* ------------------------------------------------------------ elenchi forza / debolezza */
    .pill-list {display: flex; flex-direction: column; gap: 0; background: var(--surface);
      border: 1px solid var(--line); border-radius: var(--r); overflow: hidden;}
    .pill {background: transparent; border: none; border-top: 1px solid var(--line);
      padding: 10px 14px 10px 30px; font-size: .88rem; color: var(--text); position: relative;
      line-height: 1.45;}
    .pill:first-child {border-top: none;}
    .pill::before {content: ""; position: absolute; left: 14px; top: 1.05em; width: 6px; height: 6px;
      border-radius: 50%; background: var(--muted);}
    .pill.pos::before {background: var(--pos);} .pill.neg::before {background: var(--neg);}
    .fb-t {font: 650 1.05rem 'Inter', sans-serif;}

    /* ------------------------------------------------------------ controlli */
    div[data-baseweb="select"] > div {min-height: 44px; font-size: .98rem;
      background: var(--surface) !important; border-color: var(--line-2) !important;
      border-radius: 10px !important;}
    div[data-baseweb="select"] > div:hover {border-color: rgba(255,255,255,.24) !important;}
    [data-testid="stSelectbox"] [role="group"] {min-height: 44px;}
    [data-testid="stSelectbox"] input[role="combobox"] {font-size: .98rem;}
    [data-testid="stWidgetLabel"] p {font: 600 .7rem 'Inter', sans-serif !important;
      letter-spacing: .1em; text-transform: uppercase; color: var(--muted) !important;}
    button[data-baseweb="tab"] {font: 600 .92rem 'Inter', sans-serif; letter-spacing: -.005em;
      padding: .6rem .9rem;}
    [data-testid="stBaseButton-secondary"], [data-testid="stDownloadButton"] button,
    [data-testid="stBaseButton-primary"] {border-radius: 10px !important; font-weight: 600 !important;
      min-height: 42px;}
    [data-testid="stBaseButton-secondary"] {background: var(--surface-2) !important;
      border: 1px solid var(--line-2) !important;}
    [data-testid="stBaseButton-secondary"]:hover {border-color: var(--accent) !important;
      color: var(--text) !important;}
    [data-testid="stBaseButton-primary"] {box-shadow: 0 6px 18px rgba(255,122,26,.22);}
    [data-testid="stPageLink"] a {min-height: 44px; border: 1px solid var(--line-2);
      border-radius: 10px; padding: 6px 12px; background: var(--surface-2);}
    [data-testid="stExpander"] details {background: var(--surface); border: 1px solid var(--line) !important;
      border-radius: var(--r) !important;}
    div[role="radiogroup"] label {padding: .25rem .55rem;}
    [data-testid="stMetricValue"] {font-family: 'Inter', sans-serif; letter-spacing: -.03em;}
    .note {color: var(--muted); font-size: .8rem; margin: -2px 0 12px; line-height: 1.5;}

    /* tabelle e grafici in un riquadro */
    [data-testid="stDataFrame"] {border: 1px solid var(--line); border-radius: var(--r);
      overflow: hidden; box-shadow: var(--shadow);}
    [data-testid="stPlotlyChart"] {background: linear-gradient(180deg, var(--surface-2), var(--surface));
      border: 1px solid var(--line); border-radius: var(--r); padding: 6px 8px 2px;
      box-shadow: var(--shadow);}

    /* ------------------------------------------------------------ pulsante "?" */
    details.tip {display: inline-block; vertical-align: middle; margin-left: 6px;}
    details.tip > summary {list-style: none; cursor: pointer; display: inline-flex;
      align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%;
      border: 1px solid var(--line-2); background: transparent; color: var(--muted);
      font: 600 11px/1 'Inter', sans-serif; text-transform: none; letter-spacing: 0;
      -webkit-tap-highlight-color: transparent; transition: all .15s ease;}
    details.tip > summary::-webkit-details-marker {display: none;}
    details.tip > summary:hover, details.tip[open] > summary {border-color: var(--accent);
      color: var(--accent); background: var(--accent-soft);}
    details.tip[open] > summary::before {content: ""; position: fixed; inset: 0; z-index: 999990;
      background: rgba(4, 7, 12, .66); backdrop-filter: blur(3px); cursor: default;}
    details.tip .bubble {position: fixed; z-index: 999991; left: 50%; top: 50%;
      transform: translate(-50%, -50%); width: min(480px, 92vw); max-height: 78vh; overflow: auto;
      background: var(--surface-2); border: 1px solid var(--line-2); border-radius: 16px;
      padding: 20px 22px 16px; box-shadow: 0 30px 80px rgba(0, 0, 0, .6); text-align: left;
      text-transform: none; letter-spacing: normal; white-space: normal; color: var(--text);
      font: 400 .92rem/1.55 'Inter', sans-serif;}
    .bubble .bt {font: 650 1.15rem/1.25 'Inter', sans-serif; letter-spacing: -.015em;
      color: var(--text); margin-bottom: 10px; padding-right: 20px;}
    .bubble .bk {font: 600 .64rem 'Inter', sans-serif; letter-spacing: .14em;
      text-transform: uppercase; color: var(--accent); margin-top: 12px;}
    .bubble p {margin: 3px 0 0; color: var(--text-2);}
    .bubble .entry + .entry {border-top: 1px solid var(--line); margin-top: 16px; padding-top: 14px;}
    .bubble .bx {color: var(--muted); font-size: .74rem; margin-top: 14px; text-align: center;}
    details.tip.legend {display: block; margin: 0 0 8px;}
    details.tip.legend > summary {width: auto; height: auto; padding: 4px 11px; border-radius: 8px;
      font-size: .76rem; gap: 6px; color: var(--text-2);}
    details.tip.legend > summary b {display: inline-flex; width: 15px; height: 15px;
      border-radius: 50%; align-items: center; justify-content: center; border: 1px solid currentColor;
      font-size: 10px;}
    </style>
    """, unsafe_allow_html=True)


COURT_SVG = """<svg class="court" viewBox="0 0 320 160" preserveAspectRatio="xMaxYMid slice"
fill="none"><defs><pattern id="pt" width="16" height="16" patternUnits="userSpaceOnUse">
<circle cx="1" cy="1" r="1" fill="rgba(255,255,255,.10)"/></pattern>
<linearGradient id="fd" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>
<stop offset="1" stop-color="#fff" stop-opacity="1"/></linearGradient>
<mask id="mk"><rect width="320" height="160" fill="url(#fd)"/></mask></defs>
<g mask="url(#mk)"><rect width="320" height="160" fill="url(#pt)"/>
<path d="M60 120 L110 96 L150 104 L190 70 L230 78 L270 40 L310 30" stroke="rgba(57,135,229,.55)"
stroke-width="1.6"/><path d="M60 120 L110 96 L150 104 L190 70 L230 78 L270 40 L310 30 L310 160 L60 160Z"
fill="rgba(57,135,229,.06)"/></g></svg>"""


def _template():
    t = go.layout.Template()
    axis = dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.10)",
                zeroline=False, showline=False, ticks="", tickfont=dict(color="#7d889c", size=12),
                title=dict(font=dict(color="#7d889c", size=12)), automargin=True)
    t.layout = go.Layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=TESTO_2, size=12.5),
        colorway=[BLU, ARANCIO, ACQUA], xaxis=axis, yaxis=axis,
        hoverlabel=dict(bgcolor="#1c2434", bordercolor="rgba(255,255,255,0.14)",
                        font=dict(color=TESTO, family="Inter, sans-serif", size=12.5),
                        align="left"),
        hovermode="closest",
        legend=dict(orientation="h", y=1.08, x=0, font=dict(color=TESTO_2, size=12),
                    itemsizing="constant", bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=8, r=8, t=34, b=8), bargap=0.32,
    )
    # segni sottili: barre con l'estremità arrotondata, linee da 2px, punti con anello
    t.data.bar = [go.Bar(marker=dict(cornerradius=4, line=dict(width=0)))]
    t.data.scatter = [go.Scatter(line=dict(width=2),
                                 marker=dict(size=8, line=dict(width=2, color=SUPERFICIE)))]
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
    "+/-": "plus_minus", "On-Off": "on_off", "Quintetti più usati": "quintetti",
    "Finali punto a punto": "clutch", "Chi serve chi": "assist_rete",
    "Come nascono i punti": "origini", "Break": "break", "Bonus falli": "bonus",
    "Timeout": "timeout_eff", "Probabilità di vittoria": "prob_vittoria",
    "Proiezione della classifica": "simulazione", "Giocatori simili": "somiglianza",
    "Talenti di B Nazionale": "talenti", "Ruolo stimato": "ruolo", "Profilo di tiro": "t3a_rate",
    "Andamento della partita": "break", "Clutch": "clutch", "Fabbisogni": "fabbisogni",
    "Riposo": "riposo", "Trasferte": "riposo", "Presenze": "presenze",
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


_DEC = re.compile(r"(?<![\d.])(\d+)\.(\d+)(?![\d.])")


_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def it(testo) -> str:
    """Testi all'italiana: decimali con la virgola ("75.8" -> "75,8") e date gg/mm/aaaa."""
    return _DEC.sub(r"\1,\2", _ISO.sub(r"\3/\2/\1", str(testo)))


def num(v, d: int = 1, signed: bool = False, suffix: str = "") -> str:
    """Numero formattato all'italiana; "–" se mancante."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    try:
        s = f"{float(v):+.{d}f}" if signed else f"{float(v):.{d}f}"
    except (TypeError, ValueError):
        return str(v)
    return s.replace(".", ",") + suffix


def kpis(items: list[tuple[str, str, str]]):
    """Schede numeriche: (etichetta, valore, sottotitolo). Il sottotitolo accetta HTML
    già sicuro (es. un badge di posizione)."""
    cards = "".join(f'<div class="kpi"><div class="l">{esc(l)}{tip(TIPS.get(l))}</div>'
                    f'<div class="v">{esc(it(v))}</div><div class="s">'
                    f'{s if str(s).startswith("<") else esc(it(s))}</div></div>'
                    for l, v, s in items)
    st.markdown(f'<div class="kpis">{cards}</div>', unsafe_allow_html=True)


def leader_cards(cards: list[tuple[str, pd.DataFrame, str, str]]):
    """cards: (titolo, dataframe, colonna valore, formato)"""
    out = []
    for title, df, col, fmt in cards:
        rows = "".join(
            f'<div class="lrow"><span class="r">{i}</span><span class="n">{esc(r.giocatore)}'
            f'<small>{esc(r.squadra)}</small></span>'
            f'<span class="x">{it(format(getattr(r, col), fmt))}</span></div>'
            for i, r in enumerate(df.itertuples(), start=1))
        out.append(f'<div class="lcard"><div class="h">{esc(title)}{tip(TIPS.get(title))}</div>'
                   f'{rows}</div>')
    st.markdown(f'<div class="leaders">{"".join(out)}</div>', unsafe_allow_html=True)


def pills(items: list[str], kind: str, empty: str):
    body = "".join(f'<div class="pill {kind}">{esc(it(x))}</div>' for x in items) or \
        f'<div class="pill">{esc(empty)}</div>'
    st.markdown(f'<div class="pill-list">{body}</div>', unsafe_allow_html=True)


CHIAVI_NOME = ("Giocatore", "Squadra", "Quintetto", "Voce", "Metrica", "Fattore")


def _colori(df: pd.DataFrame, colori: dict) -> pd.DataFrame:
    """CSS di sfondo: blu per i valori migliori, arancio per i peggiori (tenue)."""
    css = pd.DataFrame("", index=df.index, columns=df.columns)
    for c, alto in colori.items():
        if c not in df.columns or not pd.api.types.is_numeric_dtype(df[c]):
            continue
        r = df[c].rank(pct=True)
        if not alto:
            r = 1 - r
        for i, v in r.items():
            if pd.isna(v) or df[c].notna().sum() < 4:
                continue
            forza = abs(v - 0.5) * 2
            if forza < 0.35:
                continue
            rgb = "57,135,229" if v > 0.5 else "217,89,38"
            css.at[i, c] = f"background-color: rgba({rgb},{0.10 + 0.32 * forza:.2f})"
    return css


def show(df: pd.DataFrame, height: int | None = None, progress: dict | None = None,
         voci: list | None = None, colori: dict | None = None):
    """Tabella a tutta larghezza. progress: {colonna: (min, max)} per le barre nelle celle;
    colori: {colonna: True se più alto è meglio} per evidenziare migliori e peggiori.
    Sopra la tabella compare il pulsante "?" con la spiegazione delle colonne complesse.
    I numeri seguono il formato del dispositivo (virgola per i decimali in italiano);
    i valori mancanti sono mostrati come "–"."""
    spiegazioni = voci if voci is not None else voci_per_colonne(df.columns)
    if spiegazioni:
        st.markdown(legend(spiegazioni), unsafe_allow_html=True)
    df = df.reset_index(drop=True).copy()
    css = _colori(df, colori) if colori else None
    cfg = {}
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            two = any(k in str(c) for k in ("rate", "FTA/FGA", "Variabilità", "Brier"))
            d = 2 if two else 1
            if df[c].isna().any() and c not in (progress or {}):
                # colonne con valori mancanti: testo formattato, "–" al posto del vuoto
                df[c] = df[c].map(lambda v, d=d: num(v, d))
            else:
                df[c] = df[c].round(d)
                cfg[c] = st.column_config.NumberColumn(format="localized")
        elif not pd.api.types.is_numeric_dtype(df[c]):
            if str(c).startswith("Data"):
                df[c] = df[c].map(lambda v: it(v) if isinstance(v, str) else v)
            if df[c].isna().any():
                df[c] = df[c].astype(object).where(df[c].notna(), "–")
    for c, (lo, hi) in (progress or {}).items():
        if c in df.columns:
            cfg[c] = st.column_config.ProgressColumn(c, min_value=lo, max_value=hi,
                                                     format="localized")
    if len(df.columns) > 6:
        for c in df.columns[:2]:
            if c in CHIAVI_NOME:
                cfg[c] = st.column_config.TextColumn(c, pinned=True, width="medium")
                break
    data = df.style.apply(lambda _: css, axis=None) if css is not None else df
    st.dataframe(data, hide_index=True, width="stretch", column_config=cfg,
                 height=height or min(36 * (len(df) + 1) + 4, 640))


def plot(fig, height=380, **layout):
    fig.update_layout(height=height, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", separators=",.", **layout)
    st.plotly_chart(fig, width="stretch", theme=None,
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




def hero(eyebrow: str, title: str, meta: str = "", small: bool = False):
    size = ' style="font-size:2rem"' if small else ""
    pad = ' style="padding:16px 20px"' if small else ""
    st.markdown(f'<div class="hero"{pad}>{COURT_SVG}<div class="eyebrow">{esc(eyebrow)}</div>'
                f'<div class="title"{size}>{esc(title)}</div><div class="meta">{meta}</div></div>',
                unsafe_allow_html=True)


def note_html(text: str, key: str | None = None):
    st.markdown(f'<div class="note">{esc(text)}{tip(key)}</div>', unsafe_allow_html=True)


def brand_hero(eyebrow: str, meta: str = ""):
    """Testata con il marchio ASSIST."""
    from basket import config
    mark = (config.LOGO_DIR / "assist-mark.svg").read_text(encoding="utf-8")
    mark = mark.replace('width="128" height="128"', 'width="64" height="64"', 1)
    st.markdown(
        f'<div class="hero">{COURT_SVG}<div class="eyebrow">{esc(eyebrow)}</div>'
        f'<div class="brand">{mark}<div><div class="title" style="margin:0">'
        f'{esc(config.BRAND)}</div><div class="tagline">{esc(config.BRAND_TAGLINE)}</div>'
        f'</div></div><div class="meta" style="margin-top:10px">{meta}</div></div>',
        unsafe_allow_html=True)


def topbar(meta: str = ""):
    """Barra compatta con il marchio (al posto della testata grande)."""
    from basket import config
    mark = (config.LOGO_DIR / "assist-mark.svg").read_text(encoding="utf-8")
    st.markdown(f'<div class="topbar">{mark}<span class="nome">{esc(config.BRAND)}</span>'
                f'<span class="meta">{meta}</span></div>', unsafe_allow_html=True)


def titolo_pagina(titolo: str, desc: str = ""):
    st.markdown(f'<div class="pagina">{esc(titolo)}</div>'
                + (f'<div class="pagina-d">{esc(desc)}</div>' if desc else ""),
                unsafe_allow_html=True)


def frase(titolo: str, voci: list[str]):
    """Riquadro "in una frase" con le caratteristiche più marcate."""
    if not voci:
        return
    testo = voci[0] if len(voci) == 1 else ", ".join(voci[:-1]) + " e " + voci[-1]
    testo = testo[0].upper() + testo[1:]
    st.markdown(f'<div class="frase"><b>{esc(titolo)}</b>{esc(testo)}.</div>',
                unsafe_allow_html=True)


def badge_pos(pos: tuple[int, int] | None) -> str:
    """Badge "3° su 20": blu nel primo quarto, arancio nell'ultimo."""
    if not pos:
        return ""
    r, n = pos
    cls = "top" if r <= max(1, round(n / 4)) else ("low" if r > n - max(1, round(n / 4)) else "")
    return f'<span class="badge {cls}">{r}° su {n}</span>'


def badge(testo: str, cls: str = "") -> str:
    return f'<span class="badge {cls}">{esc(testo)}</span>'
