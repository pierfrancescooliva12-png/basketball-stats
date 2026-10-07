"""Giochi disegnati sulla lavagna: disegno delle fasi per i report PDF.

Un gioco è salvato come JSON dalla lavagna della dashboard (dashboard/lavagna/lavagna.html):
    {"id", "nome", "tipo": "nostro"|"avversaria", "difesa": bool,
     "fasi": [{"giocatori": [{"id", "tipo": "o"|"x", "n", "x", "y"}],
               "linee": [{"id", "tipo": "movimento"|"passaggio"|"palleggio"|"blocco",
                          "da", "a", "punti": [[x, y], ...]}],
               "palla": id del portatore, "nota": testo}]}
Coordinate in decimetri sulla metà campo FIBA (15 × 14 m): x 0-150, y 0-140, canestro in alto.
Il disegno qui riproduce quello della lavagna, così le fasi si leggono anche su carta.
"""

import math

from reportlab.graphics.shapes import Circle, Drawing, Line, Path, PolyLine, Polygon, String
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

RIGHE = colors.HexColor("#2b3a52")
INCHIOSTRO = colors.HexColor("#1d2b44")
ATTACCO = colors.HexColor("#1f5fbf")
DIFESA = colors.HexColor("#c4501a")
PALLA = colors.HexColor("#e8701a")
FONDO = colors.HexColor("#fbfbf7")
RAGGIO = 4.2
X0, Y0, LARG, ALT = -4, -4, 158, 148      # area visibile, come il viewBox della lavagna


def _font(bold: bool = False) -> str:
    nomi = pdfmetrics.getRegisteredFontNames()
    if bold and "Condensed" in nomi:          # registrato da report_pdf._fonts()
        return "Condensed"
    if "Barlow" in nomi:
        return "Barlow"
    return "Helvetica-Bold" if bold else "Helvetica"


# ------------------------------------------------------------------ geometria

def _catmull(punti: list) -> list:
    """Segmenti di Bézier (p1, c1, c2, p2) della curva morbida per i punti, come nella
    lavagna (Catmull-Rom)."""
    seg = []
    for i in range(len(punti) - 1):
        p0 = punti[i - 1] if i > 0 else punti[i]
        p1, p2 = punti[i], punti[i + 1]
        p3 = punti[i + 2] if i + 2 < len(punti) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        seg.append((tuple(p1), c1, c2, tuple(p2)))
    return seg


def _campiona(punti: list, passo: float) -> list:
    """Punti lungo la curva a distanza circa costante."""
    if len(punti) < 2:
        return [tuple(p) for p in punti]
    fitti = []
    for p1, c1, c2, p2 in _catmull(punti):
        for k in range(20):
            t = k / 20
            u = 1 - t
            fitti.append((u ** 3 * p1[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * p2[0],
                          u ** 3 * p1[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * p2[1]))
    fitti.append(tuple(punti[-1]))
    out, resto = [fitti[0]], 0.0
    for a, b in zip(fitti, fitti[1:]):
        d = math.dist(a, b)
        resto += d
        if resto >= passo:
            out.append(b)
            resto = 0.0
    if out[-1] != fitti[-1]:
        out.append(fitti[-1])
    return out


def _accorcia(punti: list, quanto: float) -> list:
    p = [tuple(x) for x in punti]
    if len(p) < 2:
        return p
    a, b = p[-2], p[-1]
    d = math.dist(a, b) or 1
    k = min(quanto, d * 0.8) / d
    p[-1] = (b[0] - (b[0] - a[0]) * k, b[1] - (b[1] - a[1]) * k)
    return p


# ------------------------------------------------------------------ disegno

class _Tela:
    """Converte le coordinate della lavagna (y in basso) in quelle del PDF (y in alto)."""

    def __init__(self, larghezza: float):
        self.s = larghezza / LARG
        self.d = Drawing(larghezza, ALT * self.s)

    def p(self, x, y):
        return ((x - X0) * self.s, (ALT - (y - Y0)) * self.s)

    def w(self, v):
        return v * self.s

    def linea(self, a, b, colore=RIGHE, spessore=0.6, tratteggio=None):
        (x1, y1), (x2, y2) = self.p(*a), self.p(*b)
        self.d.add(Line(x1, y1, x2, y2, strokeColor=colore, strokeWidth=self.w(spessore),
                        strokeDashArray=tratteggio, strokeLineCap=1))

    def spezzata(self, punti, colore=RIGHE, spessore=0.6, tratteggio=None):
        flat = [c for q in punti for c in self.p(*q)]
        self.d.add(PolyLine(flat, strokeColor=colore, strokeWidth=self.w(spessore),
                            strokeDashArray=tratteggio, strokeLineJoin=1, strokeLineCap=1))

    def arco(self, cx, cy, r, da, a, tratteggio=None):
        pts = [(cx + r * math.cos(math.radians(t)), cy + r * math.sin(math.radians(t)))
               for t in [da + (a - da) * k / 48 for k in range(49)]]
        self.spezzata(pts, tratteggio=tratteggio)

    def curva(self, punti, colore, spessore, tratteggio=None):
        if len(punti) < 3:
            self.spezzata(punti, colore, spessore, tratteggio)
            return
        path = Path(strokeColor=colore, strokeWidth=self.w(spessore), fillColor=None,
                    strokeDashArray=tratteggio, strokeLineCap=1)
        path.moveTo(*self.p(*punti[0]))
        for _, c1, c2, p2 in _catmull(punti):
            path.curveTo(*self.p(*c1), *self.p(*c2), *self.p(*p2))
        self.d.add(path)


def _campo(t: _Tela):
    t.d.add(Polygon([*t.p(-4, -4), *t.p(154, -4), *t.p(154, 144), *t.p(-4, 144)],
                    fillColor=FONDO, strokeColor=None))
    for a, b in (((0, 0), (150, 0)), ((150, 0), (150, 140)), ((150, 140), (0, 140)),
                 ((0, 140), (0, 0)), ((50.5, 0), (50.5, 58)), ((99.5, 0), (99.5, 58)),
                 ((50.5, 58), (99.5, 58)), ((9, 0), (9, 29.9)), ((141, 0), (141, 29.9))):
        t.linea(a, b)
    t.linea((66, 12), (84, 12), spessore=1)                       # tabellone
    t.arco(75, 15.75, 2.25, 0, 360)                                # ferro
    t.arco(75, 58, 18, 0, 180)                                     # lunetta (verso il centro)
    t.arco(75, 58, 18, 180, 360, tratteggio=[t.w(2), t.w(2)])
    a = math.degrees(math.atan2(29.9 - 15.75, 66))
    t.arco(75, 15.75, 67.5, a, 180 - a)                            # tre punti
    t.arco(75, 15.75, 12.5, 0, 180)                                # no-sfondamento
    t.arco(75, 140, 18, 180, 360)                                  # cerchio centrale
    for y in (17.5, 26, 34.5, 43):
        t.linea((49.5, y), (50.5, y))
        t.linea((99.5, y), (100.5, y))


def _punta(t: _Tela, fine, prima, colore):
    ang = math.atan2(fine[1] - prima[1], fine[0] - prima[0])
    a, b = 3.2, 1.7
    p1 = (fine[0] - a * math.cos(ang) + b * math.sin(ang), fine[1] - a * math.sin(ang) - b * math.cos(ang))
    p2 = (fine[0] - a * math.cos(ang) - b * math.sin(ang), fine[1] - a * math.sin(ang) + b * math.cos(ang))
    t.d.add(Polygon([*t.p(*fine), *t.p(*p1), *t.p(*p2)], fillColor=colore, strokeColor=None))


def _linea(t: _Tela, l: dict):
    pts = [tuple(p) for p in l.get("punti", [])]
    if len(pts) < 2:
        return
    if l.get("tipo") == "passaggio" and l.get("a"):
        pts = _accorcia(pts, RAGGIO + 1)
    tipo = l.get("tipo")
    if tipo == "palleggio":
        c = _campiona(pts, 1.6)
        zig = []
        for i, p in enumerate(c):
            if i == 0 or i >= len(c) - 3:
                zig.append(p)
                continue
            q = c[i + 1]
            dx, dy = q[0] - p[0], q[1] - p[1]
            d = math.hypot(dx, dy) or 1
            s = 1.6 if i % 2 else -1.6
            zig.append((p[0] - dy / d * s, p[1] + dx / d * s))
        t.spezzata(zig, INCHIOSTRO, 0.9)
    else:
        tr = [t.w(2.4), t.w(1.8)] if tipo == "passaggio" else None
        t.curva(pts, INCHIOSTRO, 0.9, tr)
    fine = pts[-1]
    prima = _campiona(pts, 1.0)[-3] if len(pts) > 2 else pts[-2]
    if tipo == "blocco":
        ang = math.atan2(fine[1] - prima[1], fine[0] - prima[0]) + math.pi / 2
        dx, dy = math.cos(ang) * 3.4, math.sin(ang) * 3.4
        t.linea((fine[0] - dx, fine[1] - dy), (fine[0] + dx, fine[1] + dy), INCHIOSTRO, 1.4)
    else:
        _punta(t, fine, prima, INCHIOSTRO)


def _giocatore(t: _Tela, p: dict, palla: bool):
    x, y = t.p(p["x"], p["y"])
    if p.get("tipo") == "x":
        for a, b in (((-3, -3), (3, 3)), ((3, -3), (-3, 3))):
            t.linea((p["x"] + a[0], p["y"] + a[1]), (p["x"] + b[0], p["y"] + b[1]), DIFESA, 1.3)
        t.d.add(String(*t.p(p["x"] + 3.6, p["y"] + 4.6), str(p.get("n", "")),
                       fontName=_font(True), fontSize=t.w(3.4), fillColor=DIFESA))
        return
    t.d.add(Circle(x, y, t.w(RAGGIO), fillColor=FONDO, strokeColor=ATTACCO,
                   strokeWidth=t.w(0.9)))
    fs = t.w(5.6)
    t.d.add(String(x, y - fs * 0.35, str(p.get("n", "")), fontName=_font(True), fontSize=fs,
                   fillColor=ATTACCO, textAnchor="middle"))
    if palla:
        bx, by = t.p(p["x"] + 3.6, p["y"] - 3.6)
        t.d.add(Circle(bx, by, t.w(1.9), fillColor=PALLA, strokeColor=INCHIOSTRO,
                       strokeWidth=t.w(0.35)))


def disegno_fase(fase: dict, difesa: bool, larghezza: float) -> Drawing:
    t = _Tela(larghezza)
    _campo(t)
    for l in fase.get("linee", []):
        _linea(t, l)
    for p in fase.get("giocatori", []):
        if p.get("tipo") == "x" and not difesa:
            continue
        _giocatore(t, p, p.get("id") == fase.get("palla"))
    return t.d


# ------------------------------------------------------------------ flowable per i PDF

def flowables(giochi: list[dict], S: dict, W: float, titolo: str, colonne: int = 2) -> list:
    """Sezione del PDF con i giochi: per ognuno nome e tutte le fasi affiancate con le note.
    S: stili del report (h2, body, small)."""
    if not giochi:
        return []
    el = [Paragraph(titolo, S["h2"])]
    larg = (W - (colonne - 1) * 3 * mm) / colonne
    for g in giochi:
        celle = []
        for i, f in enumerate(g.get("fasi", []), start=1):
            nota = (f.get("nota") or "").strip()
            celle.append([disegno_fase(f, bool(g.get("difesa")), larg),
                          Paragraph(f"<b>Fase {i}</b>" + (f" · {_esc(nota)}" if nota else ""),
                                    S["small"])])
        righe = [celle[i:i + colonne] for i in range(0, len(celle), colonne)]
        for r in righe:
            r += [""] * (colonne - len(r))
        tab = Table(righe, colWidths=[larg] * colonne)
        tab.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        nome = _esc(g.get("nome") or "Gioco senza nome")
        el.append(KeepTogether([Paragraph(f"<b>{nome}</b> · {len(celle)} fasi", S["body"]),
                                Spacer(1, 2), tab, Spacer(1, 6)]))
    return el


def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
