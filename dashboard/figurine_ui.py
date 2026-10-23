"""Figurine dei giocatori nel sito: una griglia di carte nei colori della squadra (per lo
Scouting quelli dell'avversaria, per lo Sviluppo quelli del proprio club)."""

import base64

import pandas as pd
import streamlit as st

from basket import figurine as FG

from .stato import App, storico
from .ui import esc, note_html, section, short

# la carta è disegnata su 380 px di larghezza: tutte le misure in cqw (1cqw = 3,8 px)
CSS = """
<style>
.figurine {display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 22px; margin: 6px 0 22px;}
.fig {container-type: inline-size; position: relative; aspect-ratio: 380 / 590; border-radius: 6% / 3.9%;
  overflow: hidden; color: #fff; background: linear-gradient(160deg, var(--f2) 0%, var(--f1) 58%);
  box-shadow: 0 16px 40px rgba(11,18,32,.28), inset 0 0 0 1px rgba(255,255,255,.08);
  transition: transform .25s ease, box-shadow .25s ease;
  animation: fig-entra .6s cubic-bezier(.2,.8,.2,1) both;}
.fig:hover {transform: translateY(-4px) rotate(-.6deg); box-shadow: 0 24px 54px rgba(11,18,32,.36);}
@keyframes fig-entra {from {opacity: 0; transform: translateY(16px);}}
@media (prefers-reduced-motion: reduce) {.fig {animation: none; transition: none;}}
.fig::after {content: ""; position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(115deg, transparent 30%, rgba(255,255,255,.10) 45%, transparent 60%);}
.fig .diag {position: absolute; top: -10.5cqw; right: -15.8cqw; width: 39.5cqw; height: 87cqw;
  transform: skewX(-22deg); background: var(--ac); opacity: .95;}
.fig .ovr {position: absolute; left: 6.3cqw; top: 5.8cqw; z-index: 3;}
.fig .ovr b {display: block; font: italic 700 19.5cqw/.9 'Barlow Condensed', sans-serif; color: var(--ac);}
.fig .ovr span {font: 600 2.9cqw 'Barlow', sans-serif; letter-spacing: .2em; text-transform: uppercase; color: var(--tn);}
.fig .pos {display: inline-block; margin-top: 2.6cqw; font: italic 700 4.7cqw 'Barlow Condensed', sans-serif;
  letter-spacing: .08em; background: var(--ac); color: var(--ta); padding: .8cqw 2.6cqw .5cqw; border-radius: 1cqw;
  transform: skewX(-10deg);}
.fig .squadra {position: absolute; right: 6.3cqw; top: 55.8cqw; z-index: 3; font: italic 700 3.9cqw 'Barlow Condensed', sans-serif;
  letter-spacing: .08em; color: var(--tn); writing-mode: vertical-rl; transform: rotate(180deg); text-transform: uppercase;
  max-height: 60cqw; overflow: hidden; white-space: nowrap;}
.fig .foto {position: absolute; left: 0; right: 0; top: 14.7cqw; height: 65.8cqw; z-index: 1;}
.fig .foto img {position: absolute; left: 50%; bottom: 0; transform: translateX(-50%); height: 100%; width: auto;
  max-width: 82%; object-fit: cover; object-position: top;
  -webkit-mask-image: linear-gradient(180deg, #000 70%, transparent); mask-image: linear-gradient(180deg, #000 70%, transparent);}
.fig .sil {position: absolute; left: 50%; transform: translateX(-50%); bottom: 0; width: 60cqw;}
.fig .numero {position: absolute; right: 15cqw; top: -1.6cqw; font: italic 700 55cqw/1 'Barlow Condensed', sans-serif;
  color: rgba(255,255,255,.07);}
.fig .nome {position: absolute; left: 6.3cqw; right: 6.3cqw; top: 79cqw; z-index: 2;
  font: italic 700 12.1cqw/.95 'Barlow Condensed', sans-serif; text-transform: uppercase; letter-spacing: .02em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.fig .nome small {display: block; font: 600 3.7cqw 'Barlow', sans-serif; letter-spacing: .18em; color: var(--ac);}
.fig .meta {position: absolute; left: 6.3cqw; right: 6.3cqw; top: 96.3cqw; font-size: 3.4cqw; color: var(--tn);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.fig .attrs {position: absolute; left: 6.3cqw; right: 6.3cqw; top: 102cqw; display: grid;
  grid-template-columns: 1fr 1fr; gap: 1.8cqw 4.7cqw;}
.fig .attr .r {display: flex; justify-content: space-between; align-items: baseline; font: 600 3cqw 'Barlow', sans-serif;
  letter-spacing: .06em; text-transform: uppercase; color: #d5dbe6;}
.fig .attr .r b {font: italic 700 4.5cqw/1.1 'Barlow Condensed', sans-serif; color: #fff;}
.fig .attr .b {height: 1.3cqw; border-radius: 1cqw; background: rgba(255,255,255,.12); margin-top: .8cqw; overflow: hidden;}
.fig .attr .b i {display: block; height: 100%; border-radius: 1cqw; background: var(--ac);
  animation: fig-barra 1s cubic-bezier(.2,.8,.2,1) .3s both; transform-origin: left;}
@keyframes fig-barra {from {transform: scaleX(0);}}
.fig .attr.medio .b i {opacity: .6;} .fig .attr.basso .b i {opacity: .3;}
.fig .stats {position: absolute; left: 6.3cqw; right: 6.3cqw; bottom: 8.6cqw; display: grid; grid-template-columns: repeat(4, 1fr);
  border-top: 1px solid rgba(255,255,255,.14); padding-top: 2.6cqw;}
.fig .stats div {text-align: center;}
.fig .stats b {display: block; font: italic 700 6.8cqw/1 'Barlow Condensed', sans-serif;}
.fig .stats span {font: 600 2.8cqw 'Barlow', sans-serif; letter-spacing: .16em; color: var(--tn);}
.fig .piede {position: absolute; left: 6.3cqw; right: 6.3cqw; bottom: 2.8cqw; font-size: 2.7cqw; color: var(--tn);
  text-align: center; line-height: 1.3;}
.fig .pdf {position: absolute; right: 6.3cqw; top: 6.3cqw; z-index: 3; font: 700 3cqw 'Barlow', sans-serif;
  letter-spacing: .08em; text-transform: uppercase; background: var(--ac); color: var(--ta); padding: 1.2cqw 2.4cqw;
  border-radius: 1.4cqw; box-shadow: 0 1.5cqw 4cqw rgba(0,0,0,.3); transition: transform .2s ease;}
.fig .pdf + .avviso {top: 15cqw;}
/* figurina cliccabile: il pulsante di download copre tutta la carta (trasparente) */
[class*="st-key-figpdf_"] {position: relative;}
[class*="st-key-figpdf_"] [data-testid="stElementContainer"]:has([data-testid="stDownloadButton"]) {
  position: absolute; inset: 0; z-index: 5; margin: 0; width: auto !important;}
[class*="st-key-figpdf_"] [data-testid="stDownloadButton"], [class*="st-key-figpdf_"] [data-testid="stDownloadButton"] > *,
[class*="st-key-figpdf_"] [data-testid="stDownloadButton"] button {width: 100% !important; height: 100%; max-width: none;}
[class*="st-key-figpdf_"] [data-testid="stDownloadButton"] button {opacity: 0; cursor: pointer;
  -webkit-tap-highlight-color: transparent; touch-action: manipulation;}
[class*="st-key-figpdf_"]:hover .fig {transform: translateY(-4px) rotate(-.6deg); box-shadow: 0 24px 54px rgba(11,18,32,.36);}
[class*="st-key-figpdf_"]:hover .fig .pdf {transform: scale(1.08);}
[class*="st-key-figpdf_"]:has(button:focus-visible) .fig {outline: 3px solid var(--ac); outline-offset: 3px;}
.figurine.uno {grid-template-columns: 1fr; margin: 0 0 6px;}
.fig .avviso {position: absolute; right: 6.3cqw; top: 6.3cqw; z-index: 3; font: 600 2.7cqw 'Barlow', sans-serif;
  letter-spacing: .1em; text-transform: uppercase; background: rgba(0,0,0,.45); color: #f3c77a; padding: 1cqw 2cqw;
  border-radius: 1cqw;}
</style>
"""

SAGOMA = ('<svg class="sil" viewBox="0 0 200 220" aria-hidden="true"><defs><linearGradient id="fg-sil" x1="0" y1="0" '
          'x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".30"/><stop offset="1" stop-color="#fff" '
          'stop-opacity=".05"/></linearGradient></defs><circle cx="100" cy="72" r="40" fill="url(#fg-sil)"/>'
          '<path d="M28 220 C30 150 62 126 100 126 C138 126 170 150 172 220 Z" fill="url(#fg-sil)"/></svg>')


def _colori(tema) -> str:
    if tema is None:
        return "--f1:#0b1220;--f2:#13213b;--ac:#ff7a1a;--ta:#0b1220;--tn:#8e9ab0"
    return (f"--f1:{tema.fondo};--f2:{tema.fondo_2};--ac:{tema.accento};"
            f"--ta:{tema.testo_accento if tema.testo_accento != '#ffffff' else tema.fondo};--tn:#a3acbd")


def _livello(v) -> str:
    return "basso" if v is None or pd.isna(v) or v < 50 else ("medio" if v < 80 else "alto")


def carta(c: dict, squadra: str, i: int = 0, pdf: bool = False) -> str:
    if c.get("foto"):
        foto = f'<img src="data:image/jpeg;base64,{base64.b64encode(c["foto"]).decode()}" alt="">'
    else:
        foto = SAGOMA
    numero = f'<div class="numero">{esc(c["maglia"])}</div>' if c.get("maglia") else ""
    barre = "".join(
        f'<div class="attr {_livello(v)}"><div class="r"><span>{esc(k)}</span><b>{"–" if v is None or pd.isna(v) else int(round(v))}</b></div>'
        f'<div class="b"><i style="width:{0 if v is None or pd.isna(v) else max(3, min(100, v)):.0f}%"></i></div></div>'
        for k, v in c["barre"].items())
    stats = "".join(f'<div><b>{esc(v)}</b><span>{esc(k)}</span></div>' for k, v in c["numeri"])
    imp = c.get("impatto")
    avviso = '<div class="avviso">pochi dati</div>' if c.get("pochi_dati") else ""
    if pdf:
        avviso = '<div class="pdf">⬇ Report PDF</div>' + avviso
    return (f'<div class="fig" style="animation-delay:{0.06 * i:.2f}s"><div class="diag"></div>{avviso}'
            f'<div class="ovr"><b>{"–" if imp is None or pd.isna(imp) else int(round(imp))}</b><span>impatto</span>'
            f'<div><span class="pos">{esc(c["sigla"])}</span></div></div>'
            f'<div class="squadra">{esc(squadra)}</div>'
            f'<div class="foto">{numero}{foto}</div>'
            f'<div class="nome"><small>{esc(c["nome"])}</small>{esc(c["cognome"])}</div>'
            f'<div class="meta">{esc(c["meta"])}</div><div class="attrs">{barre}</div>'
            f'<div class="stats">{stats}</div><div class="piede">{esc(c["piede"])}</div></div>')


@st.cache_data(show_spinner="Preparo le figurine…", ttl=6 * 3600, max_entries=10)
def _carte(_ctx, mtime: float, stagione: str, sid: int) -> list[dict]:
    return FG.carte(_ctx, storico(mtime), sid)


def render(a: App, sid: int, titolo: str, descrizione: str, tema=None, pdf=None, per_riga: int = 4):
    """Griglia di figurine dei giocatori di rotazione della squadra sid. Con pdf (funzione
    giocatore_id → (funzione che crea il PDF, nome del file)) ogni figurina è cliccabile e
    scarica il report individuale del giocatore."""
    from basket import scheda_giocatori as SG
    carte = SG.completa_foto(_carte(a.ctx, a.mtime, a.stagione, int(sid)))
    if not carte:
        return
    nome = a.ctx.nomi_squadre.get(sid, "")
    section(titolo, descrizione, key=None)
    breve = short(nome)
    colori = _colori(tema)
    if pdf is None:
        st.markdown(CSS + f'<div class="figurine" style="{colori}">'
                    + "".join(carta(c, breve, i) for i, c in enumerate(carte)) + "</div>", unsafe_allow_html=True)
    else:
        st.markdown(CSS, unsafe_allow_html=True)
        for r in range(0, len(carte), per_riga):
            cols = st.columns(per_riga, gap="medium")
            for j, c in enumerate(carte[r:r + per_riga]):
                crea, file = pdf(c["giocatore_id"])
                with cols[j], st.container(key=f"figpdf_{c['giocatore_id']}"):
                    st.markdown(f'<div class="figurine uno" style="{colori}">{carta(c, breve, r + j, pdf=True)}'
                                '</div>', unsafe_allow_html=True)
                    st.download_button(f"Scarica il report PDF di {c['nome']} {c['cognome']}".replace("  ", " "),
                                       crea, file_name=file, mime="application/pdf", on_click="ignore",
                                       key=f"figdl_{c['giocatore_id']}")
    note_html("Il numero grande è l'impatto: in percentuale, quanti giocatori dello stesso ruolo e campionato "
              "fanno meno. Le barre confrontano ogni voce con lo stesso gruppo: piena e accesa è un punto di "
              "forza. Con «pochi dati» (meno di 150 minuti giocati) i valori vanno confermati."
              + (" Clic su una figurina: scarica il report PDF di quel giocatore, da consegnare o inoltrare."
                 if pdf is not None else ""))
