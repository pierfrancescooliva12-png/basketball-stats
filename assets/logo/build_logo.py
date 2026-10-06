"""Genera il logo ASSIST in SVG (testo convertito in tracciati) e le versioni PNG.

    python assets/logo/build_logo.py

Il simbolo: una "A" il cui trattino è la traiettoria punteggiata di un passaggio che
termina su un pallone. Colori della piattaforma: blu notte #0b1220, arancio #ff7a1a.
"""

from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent / "fonts"
NAVY, ARANCIO, BIANCO = "#0b1220", "#ff7a1a", "#f2f4f8"
TAGLINE = "ANALISI STATISTICA E SCOUTING INTEGRATO PER STAFF TECNICI"


def text_path(text: str, font_file: str, size: float, x: float, y: float,
              tracking: float = 0.0) -> tuple[str, float]:
    """Tracciato SVG del testo (baseline in y) e larghezza risultante."""
    font = TTFont(FONTS / font_file)
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    upm = font["head"].unitsPerEm
    scale = size / upm
    pen = SVGPathPen(gs)
    cursor = 0.0
    for ch in text:
        name = cmap.get(ord(ch))
        if name is None:
            continue
        tp = TransformPen(pen, (scale, 0, 0, -scale, x + cursor, y))
        gs[name].draw(tp)
        cursor += gs[name].width * scale + tracking
    return pen.getCommands(), cursor - tracking


def mark(x: float = 0, y: float = 0, s: float = 1.0, sfondo: bool = True) -> str:
    """Simbolo su un quadrato 128x128 (posizione x, y; scala s)."""
    parts = [f'<g transform="translate({x} {y}) scale({s})">']
    if sfondo:
        parts.append(f'<rect width="128" height="128" rx="30" fill="{NAVY}"/>')
    # gambe della A
    parts.append(f'<path d="M30 104 L60 26 Q64 18 68 26 L98 104" fill="none" '
                 f'stroke="{BIANCO}" stroke-width="15" stroke-linecap="round" '
                 f'stroke-linejoin="round"/>')
    # traiettoria del passaggio (il trattino della A): punti che crescono verso il pallone
    p0, p1, p2 = (18, 92), (56, 50), (90, 57)
    n = 7
    for i in range(n):
        t = 0.04 + 0.86 * i / (n - 1)
        bx = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        by = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        r = 1.9 + 2.0 * i / (n - 1)
        parts.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{r:.2f}" fill="{ARANCIO}"/>')
    # pallone
    cx, cy, r = 101, 55, 13
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{ARANCIO}" '
                 f'stroke="{NAVY if sfondo else "#ffffff"}" stroke-width="3"/>')
    seam = NAVY
    parts.append(f'<path d="M{cx - r} {cy} H{cx + r} M{cx} {cy - r} V{cy + r} '
                 f'M{cx - 8} {cy - 10} Q{cx - 3} {cy} {cx - 8} {cy + 10} '
                 f'M{cx + 8} {cy - 10} Q{cx + 3} {cy} {cx + 8} {cy + 10}" fill="none" '
                 f'stroke="{seam}" stroke-width="2" stroke-linecap="round"/>')
    parts.append("</g>")
    return "".join(parts)


def svg(w, h, body, bg=None):
    rect = f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" '
            f'height="{h}">{rect}{body}</svg>')


def logo(tema: str = "scuro") -> str:
    """Logo orizzontale: simbolo + ASSIST + significato dell'acronimo."""
    ink = BIANCO if tema == "scuro" else NAVY
    sub = "#97a1b5" if tema == "scuro" else "#52607a"
    word, ww = text_path("ASSIST", "BarlowCondensed-Bold.ttf", 92, 150, 86, tracking=4)
    tag, tw = text_path(TAGLINE, "Barlow-SemiBold.ttf", 11.5, 153, 112, tracking=1.6)
    w = int(max(150 + ww, 153 + tw) + 16)
    body = (mark(0, 0, 1.0) + f'<path d="{word}" fill="{ink}"/>' +
            f'<rect x="150" y="96" width="44" height="4" rx="2" fill="{ARANCIO}"/>' +
            f'<path d="{tag}" fill="{sub}"/>')
    return svg(w, 128, body)


def main():
    out = HERE
    (out / "assist-mark.svg").write_text(svg(128, 128, mark()), encoding="utf-8")
    (out / "assist-logo.svg").write_text(logo("scuro"), encoding="utf-8")
    (out / "assist-logo-chiaro.svg").write_text(logo("chiaro"), encoding="utf-8")
    print("SVG scritti in", out)


if __name__ == "__main__":
    main()
