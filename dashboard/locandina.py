"""Locandina della partita, come la grafica di una diretta TV: le due metà in diagonale nei
colori delle squadre, i loghi uno di fronte all'altro, "VS" al centro e sotto giornata, data,
ora e campo. Colori e logo arrivano dal brand di ogni squadra (dal suo logo)."""

import streamlit as st

from basket import brand

from .stato import App, tema_squadra
from .ui import esc, short

# misure in cqw: la locandina si adatta alla larghezza della colonna
CSS = """
<style>
.loc {container-type: inline-size; position: relative; margin: 6px 0 16px;}
.loc .in {position: relative; overflow: hidden; border-radius: 16px; color: #fff; background: var(--c1); box-shadow: 0 16px 40px rgba(11,18,32,.22);
  animation: loc-su .55s cubic-bezier(.2,.8,.2,1) backwards;}
.loc .b2 {position: absolute; inset: 0; background: var(--c2);
  clip-path: polygon(56% 0, 100% 0, 100% 100%, 44% 100%);
  animation: loc-b2 .8s cubic-bezier(.7,0,.2,1) .05s backwards;}
.loc .st {position: absolute; inset: 0; background: var(--a1);
  clip-path: polygon(54.6% 0, 56% 0, 44% 100%, 42.6% 100%);
  animation: loc-st .8s cubic-bezier(.7,0,.2,1) .05s backwards;}
.loc .st.b {background: var(--a2); clip-path: polygon(56% 0, 57.4% 0, 45.4% 100%, 44% 100%);}
.loc .grana {position: absolute; inset: 0; pointer-events: none; opacity: .5;
  background: radial-gradient(60% 90% at 25% 50%, rgba(255,255,255,.10), transparent 70%),
              radial-gradient(60% 90% at 75% 50%, rgba(255,255,255,.08), transparent 70%);}
.loc .righe {position: relative; z-index: 2; display: grid; grid-template-columns: 1fr auto 1fr;
  align-items: center; gap: 2cqw; padding: max(44px, 5.4cqw) 4cqw max(18px, 2.4cqw);}
.loc .sq {display: flex; flex-direction: column; align-items: center; text-align: center; min-width: 0;}
.loc .sq.casa {animation: loc-sx .7s cubic-bezier(.2,.8,.2,1) .25s backwards;}
.loc .sq.osp {animation: loc-dx .7s cubic-bezier(.2,.8,.2,1) .25s backwards;}
.loc .logo {width: clamp(60px, 10cqw, 120px); aspect-ratio: 1; display: flex; align-items: center;
  justify-content: center; filter: drop-shadow(0 8px 18px rgba(0,0,0,.35));}
.loc .logo img {max-width: 100%; max-height: 100%; object-fit: contain;}
.loc .logo .ini {width: 100%; height: 100%; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; background: rgba(255,255,255,.10); border: 2px solid rgba(255,255,255,.35);
  font: italic 700 clamp(22px, 4.6cqw, 52px)/1 'Barlow Condensed', sans-serif; letter-spacing: .02em;}
.loc .nm {font: italic 700 clamp(22px, 3.8cqw, 46px)/1 'Barlow Condensed', sans-serif; letter-spacing: .03em;
  text-transform: uppercase; margin-top: 1.6cqw; max-width: 100%; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap;}
.loc .full {font: 500 clamp(11px, 1.35cqw, 15px) 'Barlow', sans-serif; color: rgba(255,255,255,.72);
  margin-top: .5cqw; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;}
.loc .ruolo {font: 600 clamp(9px, 1.05cqw, 12px) 'Barlow', sans-serif; letter-spacing: .2em; text-transform: uppercase;
  color: var(--ax); margin-top: .9cqw;}
.loc .vs {font: italic 700 clamp(28px, 5.6cqw, 64px)/1 'Barlow Condensed', sans-serif; letter-spacing: .02em;
  color: #fff; text-shadow: 0 6px 22px rgba(0,0,0,.45);
  animation: loc-vs .5s cubic-bezier(.2,1.6,.4,1) .6s backwards;}
.loc .info {position: relative; z-index: 4; display: flex; justify-content: center; flex-wrap: wrap;
  gap: 4px 1.6cqw; padding: 12px 4cqw; background: rgba(6,10,18,.72); backdrop-filter: blur(4px); font: 600 clamp(11px, 1.35cqw, 15px) 'Barlow', sans-serif;
  letter-spacing: .14em; text-transform: uppercase; color: rgba(255,255,255,.86);
  animation: loc-su .5s ease .75s backwards;}
.loc .info span + span::before {content: "·"; margin-right: 1.6cqw; color: rgba(255,255,255,.5);}
.loc .eye {position: absolute; z-index: 4; left: 50%; top: max(12px, 1.6cqw); transform: translateX(-50%);
  font: 600 clamp(10px, 1.15cqw, 13px) 'Barlow', sans-serif; letter-spacing: .24em; text-transform: uppercase;
  color: #fff; background: rgba(6,10,18,.72); padding: 5px 14px 4px; border-radius: 999px; white-space: nowrap;}
.loc .prob {position: relative; z-index: 2; display: grid; grid-template-columns: auto 1fr auto; align-items: center;
  gap: 1.4cqw; margin: -1.2cqw 8cqw 3.2cqw; font: italic 700 clamp(16px, 2.4cqw, 28px) 'Barlow Condensed', sans-serif;}
.loc .prob .bar {height: 8px; border-radius: 4px; background: var(--a2); overflow: hidden;}
.loc .prob .bar i {display: block; height: 100%; background: var(--a1); border-radius: 4px;
  animation: loc-bar 1s cubic-bezier(.2,.8,.2,1) .8s backwards; transform-origin: left;}
.loc .prob small {display: block; font: 600 clamp(9px, 1cqw, 11px) 'Barlow', sans-serif; letter-spacing: .14em;
  text-transform: uppercase; color: rgba(255,255,255,.7); font-style: normal;}
@keyframes loc-su {from {opacity: 0; transform: translateY(14px);}}
@keyframes loc-b2 {from {transform: translateX(60%);}}
@keyframes loc-st {from {transform: translateX(-60%); opacity: 0;}}
@keyframes loc-sx {from {opacity: 0; transform: translateX(-40px);}}
@keyframes loc-dx {from {opacity: 0; transform: translateX(40px);}}
@keyframes loc-vs {from {opacity: 0; transform: scale(.3) rotate(-12deg);}}
@keyframes loc-bar {from {transform: scaleX(0);}}
@media (prefers-reduced-motion: reduce) {.loc *, .loc .in {animation: none !important;}}
</style>
"""

NAVY, BLU = "#0b1220", "#123a72"
GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre",
        "ottobre", "novembre", "dicembre"]


def quando(data, ora=None) -> str:
    """"Martedì 21 ottobre · ore 20:30" dalla data del calendario."""
    import pandas as pd
    try:
        d = pd.Timestamp(str(data)[:10])
    except (ValueError, TypeError):
        return str(data or "")
    testo = f"{GIORNI[d.weekday()]} {d.day} {MESI[d.month - 1]}"
    return testo + (f" · ore {str(ora)[:5]}" if ora else "")


def info_partita(ng: dict) -> list[str]:
    return [f"{ng['giornata']}ª giornata", quando(ng.get("data"), ng.get("ora")), ng.get("palazzetto") or ""]


def _iniziali(nome: str) -> str:
    parole = [p for p in short(nome).split() if p[:1].isalpha()]
    if len(parole) == 1:
        return parole[0][:3].upper()          # "Cividale" → CIV
    return ("".join(p[0] for p in parole[:2]) or nome[:2]).upper()


def _colori(t1, t2) -> dict:
    """Fondo e accento delle due metà; se le squadre hanno lo stesso fondo la seconda si
    distingue con un blu (succede quando mancano i loghi)."""
    c1, a1 = (t1.fondo, t1.accento) if t1 else (NAVY, "#ff7a1a")
    c2, a2 = (t2.fondo, t2.accento) if t2 else (BLU, "#f2f4f8")
    if c1.lower() == c2.lower():
        c2 = brand.mescola(c2, "#2a78d6", 0.35) if c2.lower() != BLU else NAVY
    if a1.lower() == a2.lower():
        a2 = "#f2f4f8"
    return {"c1": c1, "a1": a1, "c2": c2, "a2": a2}


def html(casa: str, ospite: str, t1=None, t2=None, eyebrow: str = "", info: list[str] | None = None,
         prob: float | None = None) -> str:
    col = _colori(t1, t2)

    def lato(nome, t, cls, ruolo, ax):
        logo = (f'<img src="{t.logo}" alt="">' if t is not None and t.logo
                else f'<div class="ini">{esc(_iniziali(nome))}</div>')
        return (f'<div class="sq {cls}" style="--ax:{ax}"><div class="logo">{logo}</div>'
                f'<div class="nm">{esc(short(nome))}</div><div class="full">{esc(nome)}</div>'
                f'<div class="ruolo">{ruolo}</div></div>')

    righe = (lato(casa, t1, "casa", "in casa", col["a1"]) + '<div class="vs">VS</div>'
             + lato(ospite, t2, "osp", "ospite", col["a2"]))
    dettagli = "".join(f"<span>{esc(x)}</span>" for x in (info or []) if x)
    barra = ""
    if prob is not None:
        v = int(round(100 * max(0.0, min(1.0, prob))))
        barra = (f'<div class="prob"><div>{v}%<small>vittoria</small></div><div class="bar">'
                 f'<i style="width:{v}%"></i></div><div style="text-align:right">{100 - v}%'
                 f'<small>vittoria</small></div></div>')
    stile = ";".join(f"--{k}:{v}" for k, v in col.items())
    return (f'<div class="loc"><div class="in" style="{stile}"><div class="b2"></div><div class="st"></div>'
            f'<div class="st b"></div><div class="grana"></div>'
            + (f'<div class="eye">{esc(eyebrow)}</div>' if eyebrow else "")
            + f'<div class="righe">{righe}</div>{barra}'
            + (f'<div class="info">{dettagli}</div>' if dettagli else "") + '</div></div>')


def render(a: App, casa: int, ospite: int, eyebrow: str = "", info: list[str] | None = None,
           prob: float | None = None) -> None:
    nomi = a.ctx.nomi_squadre
    n1, n2 = nomi.get(casa, str(casa)), nomi.get(ospite, str(ospite))
    st.markdown(CSS + html(n1, n2, tema_squadra(casa, n1), tema_squadra(ospite, n2), eyebrow, info, prob),
                unsafe_allow_html=True)
