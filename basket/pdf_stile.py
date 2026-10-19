"""Stile grafico "Match day" del report prepartita: intestazione scura con taglio diagonale e
striscia arancione, tessere bianche con il bordo colorato, barra della posizione in campionato,
foto dei giocatori con il numero di maglia."""

import io
import re

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable

NAVY = colors.HexColor("#0b1220")
NAVY2 = colors.HexColor("#13213b")
ARANCIO = colors.HexColor("#ff7a1a")
BLU = colors.HexColor("#2a78d6")
ROSSO = colors.HexColor("#d95926")
INK = colors.HexColor("#1a2233")
GRIGIO = colors.HexColor("#6b7489")
SFONDO = colors.HexColor("#f4f6fa")
SEGMENTO = colors.HexColor("#e3e8f0")
TINTA = {"forza": BLU, "debole": ROSSO, "media": colors.HexColor("#9aa3b5"), "neutro": NAVY}
TESTO_TINTA = {"forza": BLU, "debole": ROSSO, "media": GRIGIO, "neutro": NAVY}


def sfondo(canvas, doc):
    """Fondo grigio chiaro della pagina (le tessere bianche risaltano)."""
    canvas.saveState()
    canvas.setFillColor(SFONDO)
    canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], stroke=0, fill=1)
    canvas.restoreState()


def _adatta(testo, font, massimo, minimo, larghezza):
    size = massimo
    while size > minimo and stringWidth(testo, font, size) > larghezza:
        size -= 1
    return size


def _righe(testo, font, size, larghezza):
    """Spezza il titolo su più righe se non entra."""
    parole, righe, cur = testo.split(), [], ""
    for p in parole:
        prova = (cur + " " + p).strip()
        if stringWidth(prova, font, size) <= larghezza or not cur:
            cur = prova
        else:
            righe.append(cur)
            cur = p
    return righe + [cur] if cur else righe


class Intestazione(Flowable):
    """Fascia a tutta larghezza in cima alla pagina, con taglio diagonale in basso."""

    def __init__(self, larghezza, margine_sx, margine_top, eyebrow, titolo, chips=(), meta="",
                 marchio="ASSIST", altezza=44 * mm, grande=True):
        super().__init__()
        self.w, self.ms, self.mt = larghezza, margine_sx, margine_top
        self.eyebrow, self.titolo, self.chips, self.marchio = eyebrow, titolo.upper(), chips, marchio
        # più righe di sotto-titolo separate da <br/>; niente altri tag
        self.meta = [re.sub(r"<[^>]+>", "", x).strip() for x in re.split(r"<br\s*/?>", meta or "") if x.strip()]
        self.grande = grande
        self.size = _adatta(self.titolo, "Condensed", 40 if grande else 26, 22 if grande else 18, larghezza * 0.74)
        self.linee = _righe(self.titolo, "Condensed", self.size, larghezza * 0.74)[:2]
        # altezza dal contenuto: margine, occhiello, titolo, chip, spazio per il taglio diagonale
        righe_meta = (16 if chips else 0) + 11 * len(self.meta)
        self.h = margine_top + (5 * mm if grande else 2 * mm) + 8 + self.size * 0.95 * len(self.linee) \
            + righe_meta + (7 * mm if grande else 4 * mm) + 9 * mm

    GAP = 4 * mm

    def wrap(self, aw, ah):
        return self.w, self.h - self.mt + self.GAP

    def draw(self):
        c = self.canv
        pw = self.w + 2 * self.ms
        top = self.h + self.GAP                   # bordo superiore della pagina
        base = self.GAP                           # punto più basso della fascia (a sinistra)
        c.saveState()
        c.translate(-self.ms, 0)
        # fascia con taglio diagonale: più bassa a sinistra
        p = c.beginPath()
        p.moveTo(0, top + 1)
        p.lineTo(pw, top + 1)
        p.lineTo(pw, base + 9 * mm)
        p.lineTo(0, base)
        p.close()
        c.setFillColor(NAVY)
        c.drawPath(p, stroke=0, fill=1)
        c.clipPath(p, stroke=0, fill=0)
        # striscia arancione e parte destra più chiara
        x0 = pw * 0.80
        for col, a, b in ((ARANCIO, x0, x0 + 6 * mm), (NAVY2, x0 + 6 * mm, pw + 40 * mm)):
            s = c.beginPath()
            s.moveTo(a + 22 * mm, top + 1)
            s.lineTo(b + 22 * mm, top + 1)
            s.lineTo(b - 22 * mm, base)
            s.lineTo(a - 22 * mm, base)
            s.close()
            c.setFillColor(col)
            c.drawPath(s, stroke=0, fill=1)
        c.restoreState()

        c.saveState()
        y = top - self.mt - (5 * mm if self.grande else 2 * mm)
        c.setFillColor(ARANCIO)
        c.setFont("Barlow-SemiBold", 7.5)
        c.drawString(0, y - 6, self.eyebrow.upper())
        c.setFillColor(colors.white)
        c.setFont("Condensed", 15 if self.grande else 12)
        c.saveState()
        c.translate(self.w, y - (12 if self.grande else 10))
        c.skew(0, 10)
        c.drawRightString(0, 0, self.marchio)
        c.restoreState()
        y -= 8 + self.size * 0.95
        for linea in self.linee:
            c.saveState()
            c.translate(0, y)
            c.skew(0, 10)                          # corsivo "da locandina"
            c.setFont("Condensed", self.size)
            c.drawString(0, 0, linea)
            c.restoreState()
            y -= self.size * 0.95
        if self.chips or self.meta:
            y -= 4
            x = 0
            for chip in self.chips:
                w = stringWidth(chip, "Barlow-SemiBold", 8) + 9
                c.saveState()
                c.translate(x, y - 3)
                c.skew(0, 10)
                c.setFillColor(colors.white)
                c.roundRect(0, 0, w, 12, 2, stroke=0, fill=1)
                c.restoreState()
                c.setFillColor(NAVY)
                c.setFont("Barlow-SemiBold", 8)
                c.drawString(x + 5, y + 0.5, chip)
                x += w + 5
            for i, meta in enumerate(self.meta):
                if self.chips or i:
                    y -= 13 if i == 0 else 11
                while stringWidth(meta, "Barlow", 8) > self.w * 0.76 and " " in meta:
                    meta = meta.rsplit(" ", 1)[0]
                c.setFillColor(colors.HexColor("#c9d1e0"))
                c.setFont("Barlow", 8)
                c.drawString(0, y + 0.5, meta)
        c.restoreState()


class Tessera(Flowable):
    """Voce del "come stanno in campionato": bordo colorato in alto, valore, giudizio,
    barra con una casella per squadra (quella colorata è la loro posizione)."""

    def __init__(self, larghezza, voce, valore_txt, altezza=24 * mm):
        super().__init__()
        self.w, self.h, self.v, self.txt = larghezza, altezza, voce, valore_txt

    def wrap(self, aw, ah):
        return self.w, self.h

    def draw(self):
        c, v, w, h = self.canv, self.v, self.w, self.h
        tinta = TINTA[v["tipo"]]
        c.saveState()
        c.setFillColor(colors.HexColor("#e6eaf1"))
        c.roundRect(0.4, -0.6, w, h, 3 * mm, stroke=0, fill=1)    # ombra leggera
        c.setFillColor(colors.white)
        c.roundRect(0, 0, w, h, 3 * mm, stroke=0, fill=1)
        p = c.beginPath()
        p.roundRect(0, 0, w, h, 3 * mm)
        c.clipPath(p, stroke=0, fill=0)
        c.setFillColor(tinta)
        c.rect(0, h - 1.4 * mm, w, 1.4 * mm, stroke=0, fill=1)
        c.restoreState()
        x = 3.2 * mm
        c.setFillColor(GRIGIO)
        c.setFont("Barlow-SemiBold", 6.5)
        c.drawString(x, h - 5.2 * mm, v["etichetta"].upper())
        c.setFillColor(INK)
        c.setFont("Condensed", 17)
        c.drawString(x, h - 11 * mm, self.txt)
        c.setFillColor(TESTO_TINTA[v["tipo"]])
        c.setFont("Barlow-SemiBold", 7)
        c.drawString(x, h - 14.2 * mm, f"{v['giudizio']} · {v['posizione']}° su {v['squadre']}")
        n = max(v["squadre"], 1)
        seg_w = (w - 2 * x) / n
        for i in range(n):
            c.setFillColor(tinta if i + 1 == v["posizione"] else SEGMENTO)
            c.roundRect(x + i * seg_w + 0.3, h - 18.2 * mm, seg_w - 0.8, 1.6 * mm, 0.4, stroke=0, fill=1)
        c.setFillColor(GRIGIO)
        c.setFont("Barlow", 6.3)
        c.drawString(x, 2.4 * mm, v["spiega"])


class FotoMaglia(Flowable):
    """Foto del giocatore in un riquadro scuro arrotondato, con il numero di maglia in un
    cerchio arancione; senza foto le iniziali."""

    def __init__(self, dati, nome, maglia=None, w=24 * mm, h=30 * mm):
        super().__init__()
        self.dati, self.nome, self.maglia, self.w, self.h = dati, nome, maglia, w, h

    def wrap(self, aw, ah):
        return self.w, self.h

    def draw(self):
        c, w, h = self.canv, self.w, self.h
        c.saveState()
        p = c.beginPath()
        p.roundRect(0, 0, w, h, 2.5 * mm)
        c.setFillColor(NAVY)
        c.drawPath(p, stroke=0, fill=1)
        c.clipPath(p, stroke=0, fill=0)
        disegnata = False
        if self.dati:
            try:
                from reportlab.lib.utils import ImageReader
                img = ImageReader(io.BytesIO(self.dati))
                iw, ih = img.getSize()
                scala = max(w / iw, h / ih)            # riempie il riquadro, centrata in alto
                dw, dh = iw * scala, ih * scala
                c.drawImage(img, (w - dw) / 2, h - dh, dw, dh, mask="auto")
                disegnata = True
            except Exception:
                disegnata = False
        if not disegnata:
            c.setFillColor(colors.HexColor("#5f7397"))
            c.setFont("Condensed", 20)
            c.drawCentredString(w / 2, h / 2 - 7, "".join(x[0] for x in self.nome.split()[:2]).upper())
        c.restoreState()
        if self.maglia:
            c.setFillColor(ARANCIO)
            c.circle(4.2 * mm, h - 4.2 * mm, 3.4 * mm, stroke=0, fill=1)
            c.setFillColor(colors.white)
            c.setFont("Condensed", 10 if len(str(self.maglia)) < 3 else 8)
            c.drawCentredString(4.2 * mm, h - 5.6 * mm, str(self.maglia))


class Obiettivo(Flowable):
    """Barra "da → obiettivo": quanto manca al valore normale del ruolo."""

    def __init__(self, larghezza, da, a, alto=True, altezza=2.2 * mm):
        super().__init__()
        self.w, self.h, self.da, self.a, self.alto = larghezza, altezza, da, a, alto

    def wrap(self, aw, ah):
        return self.w, self.h + 1

    def draw(self):
        c, w, h = self.canv, self.w, self.h
        quota = (self.da / self.a if self.a else 0) if self.alto else (self.a / self.da if self.da else 0)
        quota = max(0.04, min(1.0, quota))
        c.setFillColor(SEGMENTO)
        c.roundRect(0, 0, w, h, h / 2, stroke=0, fill=1)
        c.setFillColor(ROSSO)
        c.roundRect(0, 0, w * quota, h, h / 2, stroke=0, fill=1)
        c.setFillColor(BLU)
        c.rect(w - 1.2, -0.8, 1.2, h + 1.6, stroke=0, fill=1)
