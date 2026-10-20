"""Intro animata prima della schermata di accesso, in stile motion graphics: sul fondo blu
notte passa la striscia arancione, il marchio entra ruotando, la "A" si disegna, i punti del
passaggio compaiono uno dopo l'altro e il pallone arriva con un rimbalzo, poi si svela la
scritta ASSIST (con il logo del club se si entra dal suo link) e tutto si dissolve.

Solo CSS e SVG: nessun video da scaricare, circa 3,5 secondi, una volta per sessione. Chi ha
impostato il sistema per ridurre le animazioni non la vede."""

import streamlit as st

from basket import config

from .ui import esc

# punti della traiettoria del passaggio (dal marchio): x, y, raggio
PUNTI = [(21.0, 88.7, 1.90), (31.8, 78.2, 2.23), (42.4, 69.8, 2.57), (52.8, 63.3, 2.90),
         (63.1, 58.9, 3.23), (73.2, 56.5, 3.57), (83.2, 56.1, 3.90)]

CSS = """
<style>
.intro {position: fixed; inset: 0; z-index: 1000000; background: #0b1220; overflow: hidden;
  display: flex; align-items: center; justify-content: center; flex-direction: column;
  animation: intro-via .7s cubic-bezier(.6,0,.2,1) var(--fine) forwards;}
@keyframes intro-via {to {opacity: 0; transform: scale(1.04); visibility: hidden;}}
.intro .lampo {position: absolute; top: -20%; bottom: -20%; width: 9vw; min-width: 60px;
  background: #ff7a1a; transform: skewX(-24deg); left: -30%;
  animation: intro-lampo 1.1s cubic-bezier(.7,0,.25,1) .05s forwards;}
.intro .lampo.b {background: #13213b; width: 34vw; animation-delay: .18s; animation-duration: 1.25s;}
@keyframes intro-lampo {to {left: 130%;}}
.intro .fondo {position: absolute; inset: 0; opacity: 0;
  background: radial-gradient(900px 500px at 50% 45%, rgba(255,122,26,.10), transparent 70%);
  animation: intro-in .8s ease .7s forwards;}
.intro .scena {position: relative; display: flex; flex-direction: column; align-items: center;}
.intro svg {width: min(38vw, 220px); height: auto; overflow: visible;}
.intro .quadro {transform-origin: 64px 64px; transform: scale(.4) rotate(-18deg); opacity: 0;
  animation: intro-quadro .6s cubic-bezier(.2,1.4,.4,1) .45s forwards;}
@keyframes intro-quadro {to {transform: scale(1) rotate(0); opacity: 1;}}
.intro .lettera {stroke-dasharray: 1; stroke-dashoffset: 1;
  animation: intro-traccia .65s cubic-bezier(.6,0,.2,1) .85s forwards;}
@keyframes intro-traccia {to {stroke-dashoffset: 0;}}
.intro .punto {opacity: 0; transform-box: fill-box; transform-origin: center; transform: scale(0);
  animation: intro-punto .28s ease-out forwards;}
@keyframes intro-punto {to {opacity: 1; transform: scale(1);}}
.intro .palla {transform-box: fill-box; transform-origin: center; transform: scale(0); opacity: 0;
  animation: intro-palla .55s cubic-bezier(.2,1.6,.4,1) 1.85s forwards;}
@keyframes intro-palla {0% {transform: scale(0) rotate(-90deg); opacity: 0;}
  100% {transform: scale(1) rotate(0); opacity: 1;}}
.intro .nome {font: italic 700 clamp(56px, 11vw, 120px)/1 'Barlow Condensed', 'Arial Narrow', sans-serif;
  letter-spacing: .08em; color: #fff; margin-top: 18px; clip-path: inset(0 100% 0 0);
  animation: intro-svela .55s cubic-bezier(.6,0,.2,1) 2.05s forwards;}
@keyframes intro-svela {to {clip-path: inset(0 0 0 0);}}
.intro .motto {font: 600 clamp(11px, 1.6vw, 14px) 'Barlow', sans-serif; letter-spacing: .22em;
  text-transform: uppercase; color: #ff7a1a; margin-top: 10px; opacity: 0; transform: translateY(8px);
  animation: intro-in .45s ease 2.4s forwards;}
.intro .club {display: flex; align-items: center; gap: 14px; margin-top: 26px; opacity: 0;
  transform: translateY(10px); animation: intro-in .45s ease 2.55s forwards;
  font: italic 700 clamp(22px, 3vw, 30px) 'Barlow Condensed', sans-serif; letter-spacing: .04em;
  text-transform: uppercase; color: #fff;}
.intro .club span {color: #8e9ab0; font: 600 13px 'Barlow', sans-serif; letter-spacing: .2em;}
.intro .club img {height: 56px; width: auto; max-width: 140px; object-fit: contain;}
@keyframes intro-in {to {opacity: 1; transform: none;}}
/* la schermata di accesso entra dopo l'intro: testata da sinistra, modulo dal basso */
.accesso-hero {animation: accesso-sx .8s cubic-bezier(.2,.8,.2,1) calc(var(--fine) - .15s) both;}
.accesso-titolo, .accesso-sotto {animation: accesso-su .6s cubic-bezier(.2,.8,.2,1) calc(var(--fine) + .05s) both;}
[data-testid="stForm"] {animation: accesso-su .7s cubic-bezier(.2,.8,.2,1) calc(var(--fine) + .12s) both;}
.accesso-piede {animation: accesso-su .6s ease calc(var(--fine) + .25s) both;}
@keyframes accesso-sx {from {opacity: 0; transform: translateX(-28px);}}
@keyframes accesso-su {from {opacity: 0; transform: translateY(18px);}}
@media (prefers-reduced-motion: reduce) {.intro {display: none;}
  .accesso-hero, .accesso-titolo, .accesso-sotto, [data-testid="stForm"], .accesso-piede {animation: none;}}
</style>
"""


def _svg() -> str:
    punti = "".join(f'<circle class="punto" cx="{x}" cy="{y}" r="{r}" fill="#ff7a1a" '
                    f'style="animation-delay:{1.45 + i * 0.06:.2f}s"/>'
                    for i, (x, y, r) in enumerate(PUNTI))
    return ('<svg viewBox="0 0 128 128" aria-hidden="true">'
            '<g class="quadro"><rect width="128" height="128" rx="30" fill="#13213b"/>'
            '<path class="lettera" pathLength="1" d="M30 104 L60 26 Q64 18 68 26 L98 104" fill="none" '
            'stroke="#f2f4f8" stroke-width="15" stroke-linecap="round" stroke-linejoin="round"/>'
            f'{punti}'
            '<g class="palla"><circle cx="101" cy="55" r="13" fill="#ff7a1a" stroke="#13213b" stroke-width="3"/>'
            '<path d="M88 55 H114 M101 42 V68 M93 45 Q98 55 93 65 M109 45 Q104 55 109 65" fill="none" '
            'stroke="#13213b" stroke-width="2" stroke-linecap="round"/></g></g></svg>')


def mostra(tema=None) -> None:
    """Intro animata, una volta per sessione. Con il brand del club aggiunge logo e nome."""
    gia_vista = st.session_state.get("_intro_vista", False)
    st.session_state["_intro_vista"] = True
    fine = "3.9s" if tema is not None else "3.5s"
    if gia_vista:                      # nelle riproposte (es. password sbagliata) niente intro
        return
    club = ""
    if tema is not None:
        logo = f'<img src="{tema.logo}" alt="">' if tema.logo else ""
        club = f'<div class="club"><span>per</span>{logo}{esc(tema.nome)}</div>'
    st.markdown(f'<style>:root {{--fine: {fine};}}</style>' + CSS
                + f'<div class="intro" role="presentation"><div class="lampo b"></div><div class="lampo"></div>'
                f'<div class="fondo"></div><div class="scena">{_svg()}'
                f'<div class="nome">{esc(config.BRAND)}</div>'
                f'<div class="motto">{esc(config.BRAND_TAGLINE)}</div>{club}</div></div>',
                unsafe_allow_html=True)
