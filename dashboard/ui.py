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
SUPERFICIE = "#141d30"
TESTO, TESTO_2 = "#e6eaf2", "#97a1b5"
NEUTRO = "#2a3346"

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

    :root {
      --bg: #0b1220; --surface: #141d30; --surface-2: #1a2540; --line: #24304a;
      --text: #e6eaf2; --text-2: #97a1b5; --muted: #6b7489; --accent: #ff7a1a;
      --pos: #3987e5; --neg: #d95926;
    }
    .block-container {padding-top: 3.6rem; padding-left: 1rem; padding-right: 1rem; max-width: 1400px;}

    /* Barra del marchio compatta (tutte le pagine tranne la Home) */
    .topbar {display: flex; align-items: center; gap: 12px; margin: 0 0 8px; flex-wrap: wrap;}
    .topbar svg {flex: none; width: 34px; height: 34px; border-radius: 9px;}
    .topbar .nome {font: 700 1.45rem/1 'Barlow Condensed', sans-serif; letter-spacing: .04em;
      color: var(--text);}
    .topbar .meta {color: var(--text-2); font-size: .82rem;}
    .pagina {font: 700 1.9rem/1.05 'Barlow Condensed', sans-serif; text-transform: uppercase;
      letter-spacing: .02em; color: var(--text); margin: 4px 0 2px;}
    .pagina-d {color: var(--text-2); font-size: .9rem; margin-bottom: 10px;}

    /* Frase di sintesi */
    .frase {background: linear-gradient(90deg, rgba(255,122,26,.12), rgba(255,122,26,0) 70%);
      border-left: 3px solid var(--accent); border-radius: 10px; padding: 12px 16px;
      margin: 6px 0 14px; color: var(--text); font-size: 1rem; line-height: 1.45;}
    .frase b {font: 700 .72rem 'Inter', sans-serif; letter-spacing: .12em; color: var(--accent);
      text-transform: uppercase; display: block; margin-bottom: 4px;}

    /* Badge (posizione, campione ridotto) */
    .badge {display: inline-block; font: 600 .72rem 'Inter', sans-serif; padding: 2px 8px;
      border-radius: 999px; background: var(--surface-2); color: var(--text-2);
      border: 1px solid var(--line); margin-left: 6px; vertical-align: middle;}
    .badge.top {color: #9cc3f5; border-color: rgba(57,135,229,.5);}
    .badge.low {color: #f0a07e; border-color: rgba(217,89,38,.5);}
    .badge.warn {color: #f3c77a; border-color: rgba(243,199,122,.45);}

    /* Schede della Home */
    .cards {display: grid; grid-template-columns: 1fr; gap: 12px; margin: 6px 0 14px;}
    @media (min-width: 760px) {.cards {grid-template-columns: repeat(2, 1fr);}}
    @media (min-width: 1150px) {.cards.tre {grid-template-columns: repeat(3, 1fr);}}
    .card {background: var(--surface); border: 1px solid var(--line); border-radius: 14px;
      padding: 16px 18px;}
    .card .h {font: 600 .72rem 'Inter', sans-serif; letter-spacing: .12em; color: var(--accent);
      text-transform: uppercase;}
    .card .t {font: 700 1.6rem/1.1 'Barlow Condensed', sans-serif; color: var(--text);
      margin: 6px 0 4px; text-transform: uppercase;}
    .card .m {color: var(--text-2); font-size: .88rem; line-height: 1.5;}
    .card .big {font: 700 2.4rem/1 'Barlow Condensed', sans-serif; color: var(--text);}
    .card .row {display: flex; gap: 22px; flex-wrap: wrap; margin-top: 10px;}
    .card .row div {min-width: 90px;}
    .card .row small {display: block; color: var(--muted); font-size: .72rem; text-transform: uppercase;
      letter-spacing: .08em;}
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
    .hero .brand {display: flex; align-items: center; gap: 14px; margin-top: 6px;}
    .hero .brand svg {flex: none; border-radius: 14px; box-shadow: 0 6px 18px rgba(0,0,0,.35);}
    .hero .tagline {font: 600 .68rem 'Inter', sans-serif; letter-spacing: .14em;
      text-transform: uppercase; color: var(--text-2); margin-top: 2px;}

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
    .fb-t {font: 700 1.25rem 'Barlow Condensed', sans-serif; text-transform: uppercase;
      letter-spacing: .02em;}
    .pill.pos {border-left: 3px solid var(--pos);} .pill.neg {border-left: 3px solid var(--neg);}

    /* Controlli più grandi per il tocco */
    div[data-baseweb="select"] > div {min-height: 46px; font-size: 1.02rem;}
    [data-testid="stSelectbox"] [role="group"] {min-height: 46px;}
    [data-testid="stSelectbox"] input[role="combobox"] {font-size: 1.02rem;}
    button[data-baseweb="tab"] {font: 600 1.02rem 'Barlow Condensed', sans-serif;
      text-transform: uppercase; letter-spacing: .05em; padding: .6rem .9rem;}
    /* Navigazione in alto: voci più grandi al tocco */
    header [data-testid="stTopNavLink"], header [data-testid="stTopNavSection"] {
      font: 600 1.05rem 'Barlow Condensed', sans-serif !important; letter-spacing: .04em;
      text-transform: uppercase; min-height: 44px;}
    /* iPad in verticale e schermi stretti: tutte le aree restano visibili nel menu */
    @media (max-width: 1024px) {
      header [data-testid="stTopNavLink"], header [data-testid="stTopNavSection"] {
        font-size: .9rem !important; letter-spacing: 0; padding-left: .35rem !important;
        padding-right: .35rem !important;}
    }
    @media (max-width: 700px) {
      header [data-testid="stTopNavLink"], header [data-testid="stTopNavSection"] {
        font-size: .8rem !important;}
    }
    [data-testid="stPageLink"] a {min-height: 44px; border: 1px solid var(--line);
      border-radius: 10px; padding: 6px 12px; background: var(--surface-2);}
    div[role="radiogroup"] label {padding: .25rem .55rem;}
    [data-testid="stMetricValue"] {font-family: 'Barlow Condensed', sans-serif;}
    .note {color: var(--text-2); font-size: .82rem; margin: -4px 0 10px;}

    /* Pulsante "?" e finestra di spiegazione (funziona al tocco, si chiude toccando fuori) */
    details.tip {display: inline-block; vertical-align: middle; margin-left: 6px;}
    details.tip > summary {list-style: none; cursor: pointer; display: inline-flex;
      align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: 50%;
      border: 1px solid #33415f; background: var(--surface-2); color: var(--text-2);
      font: 600 13px/1 'Inter', sans-serif; text-transform: none; letter-spacing: 0;
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
