"""Logo ASSIST, versione editoriale: scritta in maiuscolo, geometrica e monocromatica, con le due
A senza trattino (Λ) che riprendono la A del marchio. Lettere da Instrument Sans SemiBold
(OFL), la Λ disegnata con le stesse proporzioni (altezza delle maiuscole, spessore dei tratti).

    python assets/logo/nuovo_logo.py      # SVG in assets/logo; i PNG con --png (serve Chromium)

Simbolo: la Λ chiara su quadrato scuro, con il pallone (punto arancione) accanto alla sommità.
"""

import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
FONT = HERE.parent / "fonts" / "InstrumentSans-SemiBold.ttf"
INK, CREMA, ARANCIO = "#141413", "#faf9f5", "#e8631c"
PAROLA = "ΛSSIST"
TRACKING = 70                          # unità del carattere tra una lettera e l'altra (1000 = em)
# Λ in unità del carattere (y verso l'alto): larghezza e altezza della A, tratti come la I
LAMBDA = [(28, 0), (291, 720), (442, 720), (705, 0), (562, 0), (366.5, 535), (171, 0)]
LAMBDA_W = 733


def _lambda(pen, dx):
    pts = [(x + dx, y) for x, y in LAMBDA]
    pen.moveTo(pts[0])
    for p in pts[1:]:
        pen.lineTo(p)
    pen.closePath()


def disegna(pen, parola=PAROLA, tracking=TRACKING):
    """Disegna la scritta con una penna di fontTools (unità del carattere, y verso l'alto);
    restituisce la larghezza."""
    font = TTFont(FONT)
    gs, cmap = font.getGlyphSet(), font.getBestCmap()
    x = 0.0
    for ch in parola:
        if ch == "Λ":
            _lambda(pen, x)
            w = LAMBDA_W
        else:
            g = gs[cmap[ord(ch)]]
            g.draw(TransformPen(pen, (1, 0, 0, 1, x, 0)))
            w = g.width
        x += w + tracking
    return x - tracking


def scritta_svg(colore=INK, altezza=40) -> str:
    """La scritta come SVG (tracciati): altezza delle maiuscole = altezza."""
    pen = SVGPathPen(None)
    flip = TransformPen(pen, (1, 0, 0, -1, 0, 720))
    larghezza = disegna(flip)
    w = larghezza * altezza / 720
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {larghezza:.0f} 720" width="{w:.0f}" '
            f'height="{altezza}" role="img" aria-label="ASSIST"><path fill="{colore}" d="{pen.getCommands()}"/></svg>')


def simbolo_svg(lato=128, fondo=INK, lettera=CREMA, palla=ARANCIO, angoli=0.22) -> str:
    """La Λ su quadrato, con il pallone accanto alla sommità."""
    pen = SVGPathPen(None)
    # Λ alta 52% del lato, centrata (leggermente a sinistra per far posto al pallone)
    s = lato * 0.52 / 720
    ox = (lato - LAMBDA_W * s) / 2 - lato * 0.04
    oy = lato * 0.24 + 720 * s
    _lambda(TransformPen(pen, (s, 0, 0, -s, ox, oy)), 0)
    r = lato * 0.075
    cx, cy = ox + 442 * s + r * 1.9, lato * 0.24 + r * 1.05
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lato} {lato}" width="{lato}" height="{lato}">'
            f'<rect width="{lato}" height="{lato}" rx="{lato * angoli:.1f}" fill="{fondo}"/>'
            f'<path fill="{lettera}" d="{pen.getCommands()}"/><circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{palla}"/></svg>')


def main():
    (HERE / "assist-scritta.svg").write_text(scritta_svg(INK), encoding="utf-8")
    (HERE / "assist-scritta-chiara.svg").write_text(scritta_svg(CREMA), encoding="utf-8")
    (HERE / "assist-mark.svg").write_text(simbolo_svg(), encoding="utf-8")
    if "--png" in sys.argv:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
            for lato in (32, 128, 512):
                pg = b.new_page(viewport={"width": lato, "height": lato})
                pg.set_content(f'<body style="margin:0">{simbolo_svg(lato)}</body>')
                pg.screenshot(path=str(HERE / f"assist-mark-{lato}.png"), omit_background=True)
            b.close()
    print("Logo scritto in", HERE)


if __name__ == "__main__":
    main()
