"""Intro animata prima della schermata di accesso, nello stile editoriale della pagina pubblica:
sul fondo crema compaiono, sparsi, frammenti del lavoro dello staff (una statistica, un grafico,
una lavagna con il gioco, un foglio di calcolo, la ricerca di un giocatore...), poi volano verso il
centro e si uniscono nel simbolo ASSIST; segue la scritta, con il logo del club se si entra dal
suo link, e tutto si dissolve.

Solo CSS e SVG: nessun video da scaricare, circa 4 secondi, una volta per sessione. Chi ha
impostato il sistema per ridurre le animazioni non la vede."""

import streamlit as st

from basket import config

from .ui import esc

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400&display=swap');
.intro {position: fixed; inset: 0; z-index: 1000000; background: #faf9f5; overflow: hidden; color: #141413;
  font-family: 'Instrument Sans', sans-serif; animation: intro-via .7s cubic-bezier(.6,0,.2,1) var(--fine) forwards;}
@keyframes intro-via {to {opacity: 0; transform: scale(1.03); visibility: hidden;}}
.intro .fr {position: absolute; left: 50%; top: 50%; --t: translate(calc(-50% + var(--x)), calc(-50% + var(--y))) rotate(var(--r));
  transform: var(--t); opacity: 0;
  animation: fr-in .6s cubic-bezier(.2,.8,.2,1) var(--d) forwards, fr-raduna .75s cubic-bezier(.7,0,.3,1) var(--v) forwards;}
@keyframes fr-in {from {opacity: 0; transform: var(--t) translateY(18px) scale(.92);} to {opacity: 1; transform: var(--t);}}
@keyframes fr-raduna {from {opacity: 1; transform: var(--t);} 70% {opacity: 1;}
  to {opacity: 0; transform: translate(-50%, -50%) rotate(0deg) scale(.08);}}
.intro .carta {background: #fffefb; border: 1px solid #e3e0d4; border-radius: 10px; padding: 12px 14px;
  box-shadow: 0 10px 30px rgba(20,20,19,.06);}
.intro .beige {background: #f3f1ea;}
.intro .et {font: 500 12px 'Instrument Sans', sans-serif; color: #6f6d66;}
.intro .num {font: 400 34px/1 'Newsreader', Georgia, serif; letter-spacing: -.01em;}
.intro .chip {display: inline-flex; gap: 8px; align-items: baseline; background: #f0eee6; border: 1px solid #d6d2c4;
  border-radius: 999px; padding: 6px 14px; font: 500 14px 'Instrument Sans', sans-serif; white-space: nowrap;}
.intro .chip b {font: 400 18px 'Newsreader', Georgia, serif;}
.intro .cerca {display: flex; align-items: center; gap: 10px; background: #fffefb; border: 1px solid #d6d2c4;
  border-radius: 999px; padding: 10px 18px; font: 400 15px 'Instrument Sans', sans-serif; white-space: nowrap;
  box-shadow: 0 10px 30px rgba(20,20,19,.06);}
.intro .cerca i {font-style: normal; color: #e8631c;}
.intro table {border-collapse: collapse; font: 500 12px 'Instrument Sans', sans-serif;}
.intro td {border: 1px solid #e3e0d4; padding: 5px 10px; text-align: right; color: #3d3d3a;}
.intro td.h {color: #6f6d66; background: #f3f1ea;} .intro td.x {background: #f8dcc6; color: #141413;}
/* il simbolo che nasce dai frammenti, poi la scritta */
.intro .centro {position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); display: flex;
  flex-direction: column; align-items: center; text-align: center;}
.intro .simbolo {width: clamp(96px, 14vw, 140px); height: auto; opacity: 0; transform: scale(.4) rotate(-8deg);
  animation: simbolo .65s cubic-bezier(.2,1.5,.4,1) var(--s) forwards;}
@keyframes simbolo {to {opacity: 1; transform: none;}}
.intro .simbolo .palla {transform-box: fill-box; transform-origin: center; transform: scale(0);
  animation: palla .45s cubic-bezier(.2,1.8,.4,1) calc(var(--s) + .35s) forwards;}
@keyframes palla {to {transform: scale(1);}}
.intro .scritta {margin-top: 26px; width: clamp(200px, 32vw, 340px); height: auto; clip-path: inset(0 100% 0 0);
  animation: svela .6s cubic-bezier(.6,0,.2,1) calc(var(--s) + .55s) forwards;}
@keyframes svela {to {clip-path: inset(0 0 0 0);}}
.intro .motto {font: 400 clamp(16px, 1.9vw, 21px)/1.3 'Newsreader', Georgia, serif; color: #6f6d66; margin-top: 14px;
  opacity: 0; transform: translateY(8px); animation: entra .5s ease calc(var(--s) + .9s) forwards; padding: 0 16px;}
.intro .club {display: flex; align-items: center; gap: 14px; margin-top: 22px; opacity: 0; transform: translateY(8px);
  animation: entra .5s ease calc(var(--s) + 1.05s) forwards; font: 400 clamp(20px, 2.6vw, 28px) 'Newsreader', Georgia, serif;}
.intro .club span {font: 500 14px 'Instrument Sans', sans-serif; color: #6f6d66;}
.intro .club img {height: 52px; width: auto; max-width: 130px; object-fit: contain;}
@keyframes entra {to {opacity: 1; transform: none;}}
@media (max-width: 640px) {.intro .fr {scale: .72;}}
/* la schermata di accesso entra dopo l'intro */
.accesso-hero {animation: accesso-su .8s cubic-bezier(.2,.8,.2,1) calc(var(--fine) - .15s) both;}
.accesso-titolo, .accesso-sotto {animation: accesso-su .6s cubic-bezier(.2,.8,.2,1) calc(var(--fine) + .05s) both;}
[data-testid="stForm"] {animation: accesso-su .7s cubic-bezier(.2,.8,.2,1) calc(var(--fine) + .12s) both;}
.accesso-piede, .accesso-barra {animation: accesso-su .6s ease calc(var(--fine) + .2s) both;}
@keyframes accesso-su {from {opacity: 0; transform: translateY(16px);}}
@media (prefers-reduced-motion: reduce) {.intro {display: none;}
  .accesso-hero, .accesso-titolo, .accesso-sotto, [data-testid="stForm"], .accesso-piede, .accesso-barra {animation: none;}}
</style>
"""

# frammenti: (contenuto, x, y, rotazione, comparsa, raduno)
LAVAGNA = ('<div class="carta beige" style="padding:10px"><svg width="170" height="130" viewBox="0 0 170 130" fill="none" '
           'stroke="#141413" stroke-width="2"><path d="M6 6 H164"/><rect x="55" y="6" width="60" height="62"/>'
           '<circle cx="85" cy="68" r="20"/><path d="M14 6 V40 A72 72 0 0 0 156 40 V6"/>'
           '<g stroke-width="2.2"><path d="M40 98 l8 8 M48 98 l-8 8"/><path d="M122 92 l8 8 M130 92 l-8 8"/></g>'
           '<circle cx="85" cy="112" r="6"/><circle cx="35" cy="60" r="6"/>'
           '<path d="M85 104 Q60 86 41 66" stroke="#e8631c" stroke-dasharray="5 5"/>'
           '<path d="M126 88 Q118 60 100 46" stroke="#e8631c"/></svg></div>')
BARRE = ('<div class="carta"><div class="et">Punti per quarto</div><svg width="150" height="78" viewBox="0 0 150 78">'
         + "".join(f'<rect x="{6 + i * 24}" y="{78 - h}" width="15" height="{h}" rx="2" fill="{c}"/>'
                   for i, (h, c) in enumerate([(40, "#141413"), (58, "#141413"), (30, "#141413"), (70, "#e8631c"),
                                               (48, "#141413"), (62, "#141413")])) + '</svg></div>')
FOGLIO = ('<div class="carta" style="padding:8px"><table><tr><td class="h">Giocatore</td><td class="h">Min</td>'
          '<td class="h">Pt</td><td class="h">Ast</td></tr><tr><td class="h">#7</td><td>31,5</td><td>14,0</td>'
          '<td class="x">5,3</td></tr><tr><td class="h">#12</td><td>28,8</td><td>10,8</td><td>2,5</td></tr>'
          '<tr><td class="h">#21</td><td>24,2</td><td>7,0</td><td>1,2</td></tr></table></div>')
STAT = ('<div class="carta" style="min-width:150px"><div class="et">TS% di squadra</div><div class="num" style="margin-top:6px">'
        '58,2%</div><div style="height:5px;background:#e3e0d4;border-radius:3px;margin-top:10px"><div style="width:72%;'
        'height:5px;background:#141413;border-radius:3px"></div></div></div>')
CERCA = ('<div class="cerca"><svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#141413" stroke-width="1.8">'
         '<circle cx="7" cy="7" r="5"/><path d="M11 11 l4 4"/></svg>più di 5 assist <i>·</i> meno di 2 perse</div>')
CURVA = ('<div class="carta"><div class="et">Andamento, media su 5</div><svg width="170" height="60" viewBox="0 0 170 60" '
         'fill="none"><path d="M4 48 L30 40 L56 44 L82 28 L108 32 L134 16 L166 10" stroke="#e8631c" stroke-width="2.4" '
         'stroke-linecap="round"/><path d="M4 48 L30 40 L56 44 L82 28 L108 32 L134 16 L166 10 V60 H4 Z" fill="#f8dcc6" '
         'opacity=".5"/></svg></div>')
CHIP1 = '<div class="chip">Net rating <b>+11,4</b></div>'
CHIP2 = '<div class="chip">eFG% <b>54,1</b></div>'
PERCENTILI = ('<div class="carta" style="min-width:160px">'
              + "".join(f'<div class="et" style="display:flex;justify-content:space-between;margin-top:{m}px">{k}<span>{v}</span>'
                        f'</div><div style="height:4px;background:#e3e0d4;border-radius:2px;margin-top:3px"><div style="width:{v}%;'
                        f'height:4px;background:{c};border-radius:2px"></div></div>'
                        for k, v, c, m in [("Realizzazione", 84, "#141413", 0), ("Creazione", 61, "#141413", 8),
                                           ("Tiro da fuori", 92, "#e8631c", 8)]) + '</div>')
FRAMMENTI = [
    (LAVAGNA, "-31vw", "-21vh", "-4deg", .05, 1.55),
    (BARRE, "29vw", "-25vh", "3deg", .15, 1.6),
    (FOGLIO, "-33vw", "17vh", "2deg", .25, 1.65),
    (STAT, "32vw", "12vh", "-3deg", .1, 1.58),
    (CERCA, "-4vw", "-36vh", "0deg", .3, 1.62),
    (CURVA, "6vw", "33vh", "2deg", .2, 1.7),
    (CHIP1, "-14vw", "34vh", "-2deg", .4, 1.68),
    (CHIP2, "18vw", "-6vh", "4deg", .45, 1.52),
    (PERCENTILI, "-18vw", "-4vh", "-2deg", .35, 1.5),
]


def _simbolo() -> str:
    """Il simbolo nuovo (Λ su quadrato scuro) con il pallone che compare per ultimo."""
    s = (config.LOGO_DIR / "assist-mark.svg").read_text(encoding="utf-8")
    s = s.replace("<svg ", '<svg class="simbolo" ', 1).replace("<circle ", '<circle class="palla" ', 1)
    return s.replace(' width="128" height="128"', "", 1)


def _scritta() -> str:
    s = (config.LOGO_DIR / "assist-scritta.svg").read_text(encoding="utf-8")
    return s.replace("<svg ", '<svg class="scritta" ', 1)


def mostra(tema=None) -> None:
    """Intro animata, una volta per sessione. Con il brand del club aggiunge logo e nome."""
    gia_vista = st.session_state.get("_intro_vista", False)
    st.session_state["_intro_vista"] = True
    fine = "4.4s" if tema is not None else "4s"
    if gia_vista:                      # nelle riproposte (es. password sbagliata) niente intro
        return
    club = ""
    if tema is not None:
        logo = f'<img src="{tema.logo}" alt="">' if tema.logo else ""
        club = f'<div class="club"><span>per</span>{logo}{esc(tema.nome)}</div>'
    frammenti = "".join(
        f'<div class="fr" style="--x:{x};--y:{y};--r:{r};--d:{d}s;--v:{v}s">{html}</div>'
        for html, x, y, r, d, v in FRAMMENTI)
    st.markdown(f'<style>:root {{--fine: {fine};}}</style>' + CSS
                + f'<div class="intro" role="presentation" style="--s:2.05s">{frammenti}'
                f'<div class="centro">{_simbolo()}{_scritta()}'
                f'<div class="motto">{esc(config.BRAND_TAGLINE)}</div>{club}</div></div>',
                unsafe_allow_html=True)
