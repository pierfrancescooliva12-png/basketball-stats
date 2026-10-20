"""Componenti grafici condivisi della dashboard: stile, schede, tabelle, grafici, "?"."""

import html
import re

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from basket.glossario import G, voci_per_colonne

# Palette dei grafici: la stessa dei report PDF ("Match day"), su fondo bianco
BLU, ARANCIO, ACQUA = "#2a78d6", "#d95926", "#199e70"
GRIGIO = "#9aa3b5"
SUPERFICIE = "#ffffff"
TESTO, TESTO_2 = "#1a2233", "#4a5468"
NEUTRO = "#eef1f6"
NAVY = "#0b1220"

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@0,600;0,700;1,700&family=Barlow:wght@400;500;600;700&display=swap');

    /* ------------------------------------------------------------ token (stile "Match day" dei PDF) */
    :root {
      --bg: #f4f6fa; --surface: #ffffff; --surface-2: #ffffff; --surface-3: #eef1f6;
      --line: #e3e8f0; --line-2: #cfd6e2;
      --text: #1a2233; --text-2: #4a5468; --muted: #6b7489; --accent: #ff7a1a;
      --accent-soft: rgba(255,122,26,.12); --pos: #2a78d6; --neg: #d95926; --ok: #199e70;
      --navy: #0b1220; --navy-2: #13213b; --on-navy: #c9d1e0;
      --shadow: 0 1px 2px rgba(16,24,40,.06), 0 4px 14px rgba(16,24,40,.05);
      --r: 12px;
      --cond: 'Barlow Condensed', 'Arial Narrow', sans-serif;
    }
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMarkdownContainer"],
    button, input, textarea, select {
      font-family: 'Barlow', system-ui, -apple-system, 'Segoe UI', sans-serif;
      font-feature-settings: 'tnum'; -webkit-font-smoothing: antialiased;}
    [data-testid="stAppViewContainer"] {background: var(--bg);}
    .block-container {padding-top: 3.8rem; padding-left: 1.25rem; padding-right: 1.25rem;
      max-width: 1440px;}
    h1, h2, h3, h4 {font-family: var(--cond) !important; letter-spacing: .01em;
      font-weight: 700 !important; text-transform: uppercase; color: var(--text);}
    ::selection {background: rgba(255,122,26,.25);}

    /* ------------------------------------------------------------ navigazione: fascia scura */
    header[data-testid="stHeader"] {background: var(--navy) !important;
      border-bottom: 3px solid var(--accent);}
    header[data-testid="stHeader"] * {color: #e8ecf3;}
    header [data-testid="stTopNavLink"], header [data-testid="stTopNavSection"] {
      font: 600 .98rem 'Barlow', sans-serif !important; letter-spacing: .01em;
      text-transform: none; min-height: 40px; color: var(--on-navy) !important;
      border-radius: 8px !important;}
    header [data-testid="stTopNavLink"] *, header [data-testid="stTopNavSection"] * {
      color: inherit !important;}
    header [data-testid="stTopNavLink"]:hover, header [data-testid="stTopNavSection"]:hover {
      color: #ffffff !important; background: rgba(255,255,255,.06) !important;}
    header [data-testid="stTopNavLink"][aria-current="page"],
    header [data-testid="stTopNavLink"][data-active="true"] {color: #ffffff !important;
      background: rgba(255,255,255,.08) !important;
      box-shadow: inset 0 -2px 0 var(--accent);}
    @media (max-width: 1024px) {
      header [data-testid="stTopNavLink"], header [data-testid="stTopNavSection"] {
        font-size: .88rem !important; padding-left: .35rem !important;
        padding-right: .35rem !important;}
    }
    @media (max-width: 700px) {
      header [data-testid="stTopNavLink"], header [data-testid="stTopNavSection"] {
        font-size: .8rem !important;}
    }

    /* ------------------------------------------------------------ barra del marchio */
    .topbar {display: flex; align-items: center; gap: 12px; margin: 0 0 14px; flex-wrap: wrap; width: 100%;
      padding-bottom: 12px; border-bottom: 1px solid var(--line);}
    .topbar svg {flex: none; width: 30px; height: 30px; border-radius: 8px;}
    .topbar .nome {font: italic 700 1.45rem/1 var(--cond); letter-spacing: .06em;
      color: var(--navy);}
    .topbar .meta {color: var(--muted); font-size: .85rem; letter-spacing: .01em;}
    .pagina {font: italic 700 2.3rem/1.05 var(--cond); letter-spacing: .01em; text-transform: uppercase;
      color: var(--navy); margin: 6px 0 2px;}
    .pagina-d {color: var(--text-2); font-size: .98rem; margin-bottom: 14px;}

    /* ------------------------------------------------------------ testata: fascia scura con
       taglio diagonale e striscia arancione, come l'intestazione dei report */
    .hero {position: relative; overflow: hidden; border-radius: 14px 14px 0 0; padding: 22px 26px 38px;
      background: var(--navy); margin-bottom: 14px; color: #ffffff;
      --text: #ffffff; --text-2: var(--on-navy); --muted: #8e9ab0; --line: rgba(255,255,255,.12);
      clip-path: polygon(0 0, 100% 0, 100% calc(100% - 26px), 0 100%);}
    .hero::before, .hero::after {content: ""; position: absolute; top: -10%; bottom: -10%;
      transform: skewX(-24deg); pointer-events: none;}
    .hero::before {left: 80%; width: 16px; background: var(--accent);}
    .hero::after {left: calc(80% + 16px); right: -30%; background: var(--navy-2);}
    .hero > * {position: relative; z-index: 1;}
    .hero svg.court {display: none;}
    .hero .eyebrow {font: 600 .74rem 'Barlow', sans-serif; letter-spacing: .16em;
      text-transform: uppercase; color: var(--accent);}
    .hero .title {font: italic 700 2.6rem/1.02 var(--cond); letter-spacing: .01em;
      color: #ffffff; margin: 6px 0 8px; text-transform: uppercase; max-width: 78%;}
    .hero .meta {color: var(--on-navy); font-size: .95rem; max-width: 78%;}
    .hero .meta a {color: var(--on-navy) !important;}
    .hero .brand {display: flex; align-items: center; gap: 16px; margin-top: 8px;}
    .hero .brand svg {flex: none; border-radius: 14px; box-shadow: 0 8px 24px rgba(0,0,0,.4);}
    .hero .brand .title {font: italic 700 2.8rem/1 var(--cond); letter-spacing: .06em;}
    .hero .tagline {font: 600 .7rem 'Barlow', sans-serif; letter-spacing: .16em;
      text-transform: uppercase; color: var(--on-navy); margin-top: 4px;}
    .hero .badge {background: #ffffff; color: var(--navy); border-color: #ffffff;}
    .hero .badge.top {background: var(--pos); color: #fff; border-color: var(--pos);}
    .hero .badge.low {background: var(--neg); color: #fff; border-color: var(--neg);}
    .hero details.tip > summary {border-color: rgba(255,255,255,.4); color: var(--on-navy);}
    @media (max-width: 700px) {
      .hero {padding: 18px 18px 32px;}
      .hero .title {font-size: 2rem; max-width: 100%;}
      .hero .meta {max-width: 100%;}
      .hero::before {left: 88%;} .hero::after {left: calc(88% + 12px);}
    }

    /* ------------------------------------------------------------ titoli di sezione */
    .sec {display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin: 30px 0 12px;
      padding-bottom: 8px; border-bottom: 2px solid var(--line); position: relative;}
    .sec::before {content: ""; width: 5px; height: 1.05rem; border-radius: 1px; transform: skewX(-14deg);
      background: var(--accent); align-self: center; flex: none;}
    .sec .t {font: 700 1.4rem/1.1 var(--cond); letter-spacing: .02em; color: var(--text);
      text-transform: uppercase;}
    .sec .d {color: var(--muted); font-size: .9rem;}

    /* ------------------------------------------------------------ schede numeriche: tessere
       bianche con il bordo colorato in alto */
    .kpis {display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin: 6px 0 20px;}
    @media (min-width: 700px) {.kpis {grid-template-columns: repeat(3, 1fr);}}
    @media (min-width: 1150px) {.kpis {grid-template-columns: repeat(6, 1fr);}}
    .kpi {position: relative; background: var(--surface); overflow: hidden;
      border: 1px solid var(--line); border-radius: var(--r); padding: 16px 16px 12px;
      box-shadow: var(--shadow); transition: border-color .15s ease, transform .15s ease;}
    .kpi::before {content: ""; position: absolute; inset: 0 0 auto 0; height: 4px; background: var(--navy);}
    .kpi:hover {border-color: var(--line-2); transform: translateY(-1px);}
    .kpi .l {font: 600 .7rem 'Barlow', sans-serif; letter-spacing: .1em; text-transform: uppercase;
      color: var(--muted); display: flex; align-items: center; gap: 2px;}
    .kpi .v {font: 700 2.1rem/1.1 var(--cond); letter-spacing: .01em; color: var(--text);
      margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
    .kpi .s {font-size: .82rem; color: var(--text-2); margin-top: 4px; white-space: nowrap;
      overflow: hidden; text-overflow: ellipsis;}

    /* ------------------------------------------------------------ frase di sintesi */
    .frase {background: var(--surface);
      border: 1px solid var(--line); border-left: 4px solid var(--accent); border-radius: var(--r);
      padding: 14px 18px; margin: 8px 0 16px; color: var(--text); font-size: 1.02rem;
      line-height: 1.55; box-shadow: var(--shadow);}
    .frase b {font: 700 .9rem var(--cond); letter-spacing: .12em; color: var(--accent);
      text-transform: uppercase; display: block; margin-bottom: 4px;}
    .frase li {margin: 3px 0;} .frase li::marker {color: var(--muted);}

    /* ------------------------------------------------------------ badge */
    .badge {display: inline-block; font: 600 .74rem 'Barlow', sans-serif; padding: 2px 8px;
      border-radius: 4px; background: var(--surface-3); color: var(--text-2);
      border: 1px solid var(--line); margin-left: 6px; vertical-align: middle;
      white-space: nowrap;}
    .badge.top {color: #ffffff; background: var(--pos); border-color: var(--pos);}
    .badge.low {color: #ffffff; background: var(--neg); border-color: var(--neg);}
    .badge.warn {color: #8a5a00; background: #fff3d6; border-color: #f3d18a;}

    /* ------------------------------------------------------------ schede della Home */
    .cards {display: grid; grid-template-columns: 1fr; gap: 12px; margin: 8px 0 16px;}
    @media (min-width: 760px) {.cards {grid-template-columns: repeat(2, 1fr);}}
    @media (min-width: 1150px) {.cards.tre {grid-template-columns: repeat(3, 1fr);}}
    .card {position: relative; overflow: hidden; background: var(--surface);
      border: 1px solid var(--line); border-radius: 14px; padding: 20px 20px 18px;
      box-shadow: var(--shadow); transition: border-color .15s ease;}
    .card::before {content: ""; position: absolute; inset: 0 0 auto 0; height: 4px; background: var(--accent);}
    .card:hover {border-color: var(--line-2);}
    .card .h {font: 600 .72rem 'Barlow', sans-serif; letter-spacing: .14em; color: var(--accent);
      text-transform: uppercase; margin-bottom: 6px;}
    .card .t {font: 700 1.6rem/1.1 var(--cond); letter-spacing: .01em; color: var(--text);
      text-transform: uppercase; margin-bottom: 6px;}
    .card .m {color: var(--text-2); font-size: .94rem; line-height: 1.55;}
    .card .big {font: 700 2.6rem/1 var(--cond); letter-spacing: .01em; color: var(--text);
      margin: 6px 0;}
    .card .row {display: flex; gap: 26px; flex-wrap: wrap; margin-top: 12px;
      padding-top: 12px; border-top: 1px solid var(--line);}
    .card .row div {min-width: 90px; font: 700 1.35rem var(--cond); color: var(--text);
      letter-spacing: .01em;}
    .card .row small {display: block; color: var(--muted); font: 600 .68rem 'Barlow', sans-serif;
      letter-spacing: .12em; text-transform: uppercase; margin-bottom: 2px;}

    /* ------------------------------------------------------------ leader */
    .leaders {display: grid; grid-template-columns: 1fr; gap: 12px;}
    @media (min-width: 560px) {.leaders {grid-template-columns: repeat(3, 1fr);}}
    .lcard {background: var(--surface);
      border: 1px solid var(--line); border-top: 4px solid var(--navy); border-radius: var(--r);
      padding: 14px 16px 8px; box-shadow: var(--shadow);}
    .lcard .h {font: 700 1rem var(--cond); letter-spacing: .06em; text-transform: uppercase;
      color: var(--text); margin-bottom: 6px;}
    .lrow {display: grid; grid-template-columns: 22px 1fr auto; align-items: center; gap: 8px;
      padding: 7px 0; border-top: 1px solid var(--line);}
    .lrow .r {color: var(--muted); font: 700 .9rem var(--cond);
      font-variant-numeric: tabular-nums;}
    .lrow .n {color: var(--text); font-size: .95rem; white-space: nowrap; overflow: hidden;
      text-overflow: ellipsis;}
    .lrow .n small {display: block; color: var(--muted); font-size: .76rem;}
    .lrow .x {font: 700 1.25rem var(--cond); color: var(--text);
      font-variant-numeric: tabular-nums;}
    .lcard .lrow:nth-of-type(2) .x {color: var(--accent);}

    /* ------------------------------------------------------------ elenchi forza / debolezza */
    .pill-list {display: flex; flex-direction: column; gap: 0; background: var(--surface);
      border: 1px solid var(--line); border-radius: var(--r); overflow: hidden; box-shadow: var(--shadow);}
    .pill {background: transparent; border: none; border-top: 1px solid var(--line);
      padding: 10px 14px 10px 30px; font-size: .94rem; color: var(--text); position: relative;
      line-height: 1.45;}
    .pill:first-child {border-top: none;}
    .pill::before {content: ""; position: absolute; left: 14px; top: 1.05em; width: 7px; height: 7px;
      border-radius: 1px; background: var(--muted);}
    .pill.pos {box-shadow: inset 4px 0 0 var(--pos);} .pill.neg {box-shadow: inset 4px 0 0 var(--neg);}
    .pill.pos::before {background: var(--pos);} .pill.neg::before {background: var(--neg);}
    .fb-t {font: 700 1.2rem var(--cond); text-transform: uppercase; letter-spacing: .02em;}

    /* ------------------------------------------------------------ controlli */
    div[data-baseweb="select"] > div {min-height: 44px; font-size: 1rem;
      background: var(--surface) !important; border-color: var(--line-2) !important;
      border-radius: 10px !important;}
    div[data-baseweb="select"] > div:hover {border-color: var(--muted) !important;}
    [data-testid="stSelectbox"] [role="group"] {min-height: 44px;}
    [data-testid="stSelectbox"] input[role="combobox"] {font-size: 1rem;}
    [data-testid="stWidgetLabel"] p {font: 600 .72rem 'Barlow', sans-serif !important;
      letter-spacing: .1em; text-transform: uppercase; color: var(--muted) !important;}
    button[data-baseweb="tab"] {font: 700 1.05rem var(--cond); letter-spacing: .04em;
      text-transform: uppercase; padding: .6rem .9rem;}
    [data-testid="stBaseButton-secondary"], [data-testid="stDownloadButton"] button,
    [data-testid="stBaseButton-primary"] {border-radius: 10px !important; font-weight: 600 !important;
      min-height: 42px;}
    [data-testid="stBaseButton-secondary"] {background: var(--surface) !important;
      border: 1px solid var(--line-2) !important; color: var(--text) !important;}
    [data-testid="stBaseButton-secondary"]:hover {border-color: var(--accent) !important;
      color: var(--text) !important;}
    [data-testid="stBaseButton-primary"] {box-shadow: 0 6px 18px rgba(255,122,26,.25);}
    [data-testid="stPageLink"] a {min-height: 44px; border: 1px solid var(--line-2);
      border-radius: 10px; padding: 6px 12px; background: var(--surface);}
    [data-testid="stExpander"] details {background: var(--surface); border: 1px solid var(--line) !important;
      border-radius: var(--r) !important; box-shadow: var(--shadow);}
    [data-testid="stVerticalBlockBorderWrapper"] {background: var(--surface);}
    div[role="radiogroup"] label {padding: .25rem .55rem;}
    [data-testid="stMetricValue"] {font-family: var(--cond); font-weight: 700; letter-spacing: .01em;}
    .note {color: var(--muted); font-size: .86rem; margin: -2px 0 12px; line-height: 1.5;}

    /* tabelle e grafici in un riquadro bianco */
    [data-testid="stDataFrame"] {border: 1px solid var(--line); border-radius: var(--r);
      overflow: hidden; box-shadow: var(--shadow); background: var(--surface);}
    [data-testid="stPlotlyChart"] {background: var(--surface);
      border: 1px solid var(--line); border-radius: var(--r); padding: 6px 8px 2px;
      box-shadow: var(--shadow);}

    /* ------------------------------------------------------------ pulsante "?" */
    details.tip {display: inline-block; vertical-align: middle; margin-left: 6px;}
    details.tip > summary {list-style: none; cursor: pointer; display: inline-flex;
      align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%;
      border: 1px solid var(--line-2); background: var(--surface); color: var(--muted);
      font: 600 11px/1 'Barlow', sans-serif; text-transform: none; letter-spacing: 0;
      -webkit-tap-highlight-color: transparent; transition: all .15s ease;}
    details.tip > summary::-webkit-details-marker {display: none;}
    details.tip > summary:hover, details.tip[open] > summary {border-color: var(--accent);
      color: var(--accent); background: var(--accent-soft);}
    details.tip[open] > summary::before {content: ""; position: fixed; inset: 0; z-index: 999990;
      background: rgba(11, 18, 32, .55); backdrop-filter: blur(3px); cursor: default;}
    details.tip .bubble {position: fixed; z-index: 999991; left: 50%; top: 50%;
      transform: translate(-50%, -50%); width: min(480px, 92vw); max-height: 78vh; overflow: auto;
      background: var(--surface); border: 1px solid var(--line); border-top: 4px solid var(--accent);
      border-radius: 14px; padding: 20px 22px 16px; box-shadow: 0 30px 80px rgba(11, 18, 32, .35);
      text-align: left; text-transform: none; letter-spacing: normal; white-space: normal;
      color: var(--text); font: 400 .96rem/1.55 'Barlow', sans-serif;}
    .bubble .bt {font: 700 1.4rem/1.15 var(--cond); letter-spacing: .01em; text-transform: uppercase;
      color: var(--text); margin-bottom: 10px; padding-right: 20px;}
    .bubble .bk {font: 600 .68rem 'Barlow', sans-serif; letter-spacing: .14em;
      text-transform: uppercase; color: var(--accent); margin-top: 12px;}
    .bubble p {margin: 3px 0 0; color: var(--text-2);}
    .bubble .entry + .entry {border-top: 1px solid var(--line); margin-top: 16px; padding-top: 14px;}
    .bubble .bx {color: var(--muted); font-size: .78rem; margin-top: 14px; text-align: center;}
    details.tip.legend {display: block; margin: 0 0 8px;}
    details.tip.legend > summary {width: auto; height: auto; padding: 4px 11px; border-radius: 8px;
      font-size: .8rem; gap: 6px; color: var(--text-2);}
    details.tip.legend > summary b {display: inline-flex; width: 15px; height: 15px;
      border-radius: 50%; align-items: center; justify-content: center; border: 1px solid currentColor;
      font-size: 10px;}
    /* ------------------------------------------------------------ movimento: le tessere entrano
       in sequenza all'apertura della pagina (solo "backwards": dopo resta lo stile normale) */
    @keyframes as-su {from {opacity: 0; transform: translateY(14px);}}
    @keyframes as-sx {from {opacity: 0; transform: translateX(-22px);}}
    .hero {animation: as-sx .6s cubic-bezier(.2,.8,.2,1) backwards;}
    .kpi, .card, .lcard, .frase, .quadrante {animation: as-su .5s cubic-bezier(.2,.8,.2,1) backwards;}
    .kpis > :nth-child(2), .cards > :nth-child(2), .leaders > :nth-child(2) {animation-delay: .06s;}
    .kpis > :nth-child(3), .cards > :nth-child(3), .leaders > :nth-child(3) {animation-delay: .12s;}
    .kpis > :nth-child(4), .cards > :nth-child(4) {animation-delay: .18s;}
    .kpis > :nth-child(5), .cards > :nth-child(5) {animation-delay: .24s;}
    .kpis > :nth-child(6), .cards > :nth-child(6) {animation-delay: .30s;}
    .kpis > :nth-child(n+7), .cards > :nth-child(n+7) {animation-delay: .36s;}

    /* ------------------------------------------------------------ quadrante della probabilità */
    @property --n {syntax: '<integer>'; inherits: false; initial-value: 0;}
    .quadrante {background: var(--surface); border: 1px solid var(--line); border-radius: 14px;
      box-shadow: var(--shadow); padding: 16px 18px 14px; margin: 6px 0 14px; display: flex;
      align-items: center; gap: 22px; flex-wrap: wrap;}
    .quadrante .q {position: relative; width: 220px; max-width: 100%; flex: none;}
    .quadrante svg {display: block; width: 100%; height: auto;}
    .quadrante .tr, .quadrante .fi {fill: none; stroke-width: 18;}
    .quadrante .fi {stroke-dasharray: 100; animation: q-riempi 1.2s cubic-bezier(.2,.8,.2,1) .15s backwards;}
    @keyframes q-riempi {from {stroke-dashoffset: 100;}}
    .quadrante .qv {position: absolute; left: 0; right: 0; bottom: 2px; text-align: center;
      font: 700 2.4rem/1 var(--cond); color: var(--text); counter-reset: n var(--n);
      animation: q-conta 1.2s cubic-bezier(.2,.8,.2,1) .15s backwards;}
    .quadrante .qv::after {content: counter(n) "%";}
    @keyframes q-conta {from {--n: 0;}}
    .quadrante .qt {font: 600 .7rem 'Barlow', sans-serif; letter-spacing: .12em; text-transform: uppercase;
      color: var(--muted);}
    .quadrante .qs {display: flex; flex-direction: column; gap: 6px; min-width: 0; flex: 1; max-width: 440px;}
    .quadrante .qr {display: flex; align-items: center; gap: 8px; font-size: .95rem; color: var(--text);}
    .quadrante .qr i {width: 12px; height: 12px; border-radius: 3px; flex: none; transform: skewX(-12deg);}
    .quadrante .qr b {font: 700 1.3rem var(--cond); margin-left: auto;}
    .quadrante .qn {color: var(--text-2); font-size: .82rem;}
    .card .quadrante {box-shadow: none; border: 0; padding: 0; margin: 12px 0 0; gap: 14px;}
    .card .quadrante .q {width: 150px;} .card .quadrante .qv {font-size: 1.7rem;}

    /* ------------------------------------------------------------ caricamento: il pallone che
       rimbalza al posto della rotellina */
    [data-testid="stSpinnerIcon"], [data-testid="stStatusWidgetRunningIcon"] {
      border: 0 !important; animation: none !important; position: relative; display: inline-block;
      width: 22px !important; height: 26px !important; background: none !important;}
    [data-testid="stSpinnerIcon"]::before, [data-testid="stStatusWidgetRunningIcon"]::before {
      content: ""; position: absolute; left: 3px; top: 0; width: 16px; height: 16px; border-radius: 50%;
      background: radial-gradient(circle at 35% 30%, #ffb26b, var(--accent, #ff7a1a) 60%);
      box-shadow: inset 0 0 0 1.5px rgba(11,18,32,.55);
      animation: as-palla .7s cubic-bezier(.45,0,.55,1) infinite alternate;}
    [data-testid="stSpinnerIcon"]::after, [data-testid="stStatusWidgetRunningIcon"]::after {
      content: ""; position: absolute; left: 4px; bottom: 0; width: 14px; height: 3px; border-radius: 50%;
      background: rgba(11,18,32,.25); animation: as-ombra .7s cubic-bezier(.45,0,.55,1) infinite alternate;}
    @keyframes as-palla {from {transform: translateY(0) rotate(0);} to {transform: translateY(9px) rotate(140deg) scaleY(.9);}}
    @keyframes as-ombra {from {transform: scaleX(.55); opacity: .5;} to {transform: scaleX(1); opacity: 1;}}
    [data-testid="stStatusWidgetRunningIcon"] svg, [data-testid="stSpinnerIcon"] svg {display: none;}

    @media (prefers-reduced-motion: reduce) {
      .hero, .kpi, .card, .lcard, .frase, .quadrante, .quadrante .fi, .quadrante .qv {animation: none;}
      [data-testid="stSpinnerIcon"]::before, [data-testid="stSpinnerIcon"]::after,
      [data-testid="stStatusWidgetRunningIcon"]::before, [data-testid="stStatusWidgetRunningIcon"]::after
        {animation-duration: 1.6s;}
    }
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
    axis = dict(gridcolor="rgba(11,18,32,0.07)", linecolor="rgba(11,18,32,0.15)",
                zeroline=False, showline=False, ticks="", tickfont=dict(color="#6b7489", size=12.5),
                title=dict(font=dict(color="#6b7489", size=12.5)), automargin=True)
    t.layout = go.Layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Barlow, system-ui, sans-serif", color=TESTO_2, size=13),
        colorway=[BLU, ARANCIO, ACQUA], xaxis=axis, yaxis=axis,
        hoverlabel=dict(bgcolor=NAVY, bordercolor=NAVY,
                        font=dict(color="#ffffff", family="Barlow, sans-serif", size=13),
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
            rgb = "42,120,214" if v > 0.5 else "217,89,38"
            css.at[i, c] = f"background-color: rgba({rgb},{0.08 + 0.26 * forza:.2f})"
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
            two = any(k in str(c) for k in ("rate", "FTA/FGA", "Variabilità", "Brier", "Ass/Perse",
                                              "per palla persa"))
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


def quadrante(p: float, titolo: str, sx: str, dx: str, nota: str = "",
              colore: str = "var(--navy)", fondo: str = "var(--accent)") -> str:
    """Probabilità come quadrante semicircolare che si riempie: p (0-1) è la quota di sx."""
    v = int(round(100 * max(0.0, min(1.0, float(p)))))
    arco = "M14 100 A86 86 0 0 1 186 100"
    return (f'<div class="quadrante"><div class="q"><svg viewBox="0 0 200 108" aria-hidden="true">'
            f'<path class="tr" d="{arco}" pathLength="100" style="stroke:{fondo}"/>'
            f'<path class="fi" d="{arco}" pathLength="100" style="stroke:{colore};stroke-dashoffset:{100 - v}"/>'
            f'</svg><div class="qv" style="--n:{v}" aria-label="{v}%"></div></div>'
            f'<div class="qs"><div class="qt">{esc(titolo)}</div>'
            f'<div class="qr"><i style="background:{colore}"></i>{esc(sx)}<b>{v}%</b></div>'
            f'<div class="qr"><i style="background:{fondo}"></i>{esc(dx)}<b>{100 - v}%</b></div>'
            + (f'<div class="qn">{esc(nota)}</div>' if nota else "") + '</div></div>')


def note_html(text: str, key: str | None = None):
    st.markdown(f'<div class="note">{esc(text)}{tip(key)}</div>', unsafe_allow_html=True)


def brand_hero(eyebrow: str, meta: str = "", tema=None):
    """Testata con il marchio ASSIST, o con il logo e il nome del club se c'è il suo brand."""
    from basket import config
    if tema is not None:
        logo = (f'<img class="club-logo" src="{tema.logo}" alt="">' if tema.logo else "")
        st.markdown(
            f'<div class="hero"><div class="eyebrow">{esc(eyebrow)}</div>'
            f'<div class="brand">{logo}<div><div class="title" style="margin:0">'
            f'{esc(tema.nome)}</div><div class="tagline">con {esc(config.BRAND)} · '
            f'{esc(config.BRAND_TAGLINE)}</div></div></div>'
            f'<div class="meta" style="margin-top:10px">{meta}</div></div>',
            unsafe_allow_html=True)
        return
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
