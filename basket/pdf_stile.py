"""Stile editoriale dei PDF, lo stesso della piattaforma: carta crema, inchiostro, titoli con
le grazie (Newsreader), testi in Instrument Sans, l'arancio solo come accento. Qui
l'intestazione con il logo ΛSSIST, i titoli di capitolo e di sezione, il piè di pagina, le
tessere della posizione in campionato, le foto con la maglia e le barre degli obiettivi."""

import io
import re
from datetime import date

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Paragraph, Table, TableStyle

INK = colors.HexColor("#141413")
ARANCIO = colors.HexColor("#e8631c")
BLU = colors.HexColor("#2a78d6")
ROSSO = colors.HexColor("#d95926")
GRIGIO = colors.HexColor("#6f6d66")
SFONDO = colors.HexColor("#faf9f5")          # la pagina
SUPERFICIE = colors.HexColor("#f3f1ea")      # i riquadri
CARTA = SUPERFICIE                           # i numeri chiave
CARTA_CHIARA = colors.HexColor("#f4f2eb")    # righe alterne delle tabelle
LINEA = colors.HexColor("#e3e0d4")
LINEA_2 = colors.HexColor("#d6d2c4")
SEGMENTO = LINEA
NAVY = INK                                   # nomi storici
NAVY2 = colors.HexColor("#2b2b29")
TINTA = {"forza": BLU, "debole": ROSSO, "media": colors.HexColor("#b9b5a8"), "neutro": INK}
TESTO_TINTA = {"forza": BLU, "debole": ROSSO, "media": GRIGIO, "neutro": INK}


def sfondo(canvas, doc):
    """Fondo crema della pagina."""
    canvas.saveState()
    canvas.setFillColor(SFONDO)
    canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], stroke=0, fill=1)
    canvas.restoreState()


def scritta(c, x_destra, y, altezza, colore=INK) -> float:
    """Il logo ΛSSIST allineato a destra in x_destra; restituisce la larghezza usata. Senza il
    disegno del logo (manca fontTools) scrive ASSIST con il carattere dei testi."""
    try:
        from .logo import disegna_pdf
        disegna_pdf(c, x_destra, y, altezza, colore)
        return altezza * 3912 / 720
    except Exception:
        c.saveState()
        c.setFillColor(colore)
        c.setFont("Sans-Semi", altezza * 1.4)
        c.drawRightString(x_destra, y, "ASSIST")
        c.restoreState()
        return stringWidth("ASSIST", "Sans-Semi", altezza * 1.4)


def piede(testo: str, margine=12 * mm):
    """Piè di pagina comune: fondo crema, filo sottile, a sinistra di cosa parla il documento e
    la data, a destra il numero di pagina e il logo."""
    def disegna(canvas, doc):
        sfondo(canvas, doc)
        w = doc.pagesize[0]
        canvas.saveState()
        canvas.setStrokeColor(LINEA)
        canvas.setLineWidth(0.5)
        canvas.line(margine, 11.5 * mm, w - margine, 11.5 * mm)
        canvas.setFont("Sans", 7)
        canvas.setFillColor(GRIGIO)
        canvas.drawString(margine, 7.5 * mm, f"{testo} · {date.today().strftime('%d/%m/%Y')}")
        lw = scritta(canvas, w - margine, 7.5 * mm, 5.2, INK)
        canvas.setFillColor(GRIGIO)
        canvas.setFont("Sans", 7)
        canvas.drawRightString(w - margine - lw - 8, 7.5 * mm, f"pagina {doc.page}")
        canvas.restoreState()
    return disegna


def _adatta(testo, font, massimo, minimo, larghezza):
    size = massimo
    while size > minimo and stringWidth(testo, font, size) > larghezza:
        size -= 1
    return size


def _righe(testo, font, size, larghezza):
    """Spezza il testo su più righe se non entra."""
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
    """Testata del documento: in alto l'occhiello e il logo, un filo d'inchiostro, poi il
    titolo con le grazie, le etichette (record, posizione) e le righe di dettaglio."""

    def __init__(self, larghezza, margine_sx=0, margine_top=0, eyebrow="", titolo="", chips=(), meta="",
                 marchio="ASSIST", altezza=None, grande=True):
        super().__init__()
        self.w, self.eyebrow, self.titolo, self.chips, self.marchio = larghezza, eyebrow, titolo, chips, marchio
        # più righe di sotto-titolo separate da <br/>; niente altri tag
        self.meta = [re.sub(r"<[^>]+>", "", x).strip() for x in re.split(r"<br\s*/?>", meta or "") if x.strip()]
        self.grande = grande
        massimo, minimo = (30, 21) if grande else (21, 16)
        self.size = _adatta(self.titolo, "Serif", massimo, minimo, larghezza)
        self.linee = _righe(self.titolo, "Serif", self.size, larghezza)[:2]
        self.h = (10 + 6 + (12 if grande else 9) + self.size * 1.08 * len(self.linee)
                  + (19 if chips else 0) + (4 + 11 * len(self.meta) if self.meta else 0) + (10 if grande else 7))

    def wrap(self, aw, ah):
        return self.w, self.h

    def draw(self):
        c, w = self.canv, self.w
        y = self.h - 8
        c.saveState()
        # occhiello con il punto arancio, logo a destra
        c.setFillColor(ARANCIO)
        c.circle(2, y + 2.4, 2, stroke=0, fill=1)
        c.setFillColor(GRIGIO)
        c.setFont("Sans-Semi", 7.2)
        eb = self.eyebrow.upper()
        while stringWidth(eb, "Sans-Semi", 7.2) > w - 60 and " " in eb:
            eb = eb.rsplit(" ", 1)[0]
        c.drawString(8, y, eb)
        if str(self.marchio).upper() == "ASSIST":
            scritta(c, w, y, 7.5 if self.grande else 6.5, INK)
        else:
            c.setFillColor(INK)
            c.setFont("Sans-Semi", 9)
            c.drawRightString(w, y, self.marchio)
        y -= 6
        c.setStrokeColor(INK)
        c.setLineWidth(0.8)
        c.line(0, y, w, y)
        y -= (12 if self.grande else 9)
        c.setFillColor(INK)
        c.setFont("Serif", self.size)
        for linea in self.linee:
            y -= self.size * 0.86
            c.drawString(0, y, linea)
            y -= self.size * 0.22
        if self.chips:
            y -= 16
            x = 0
            for chip in self.chips:
                cw = stringWidth(chip, "Sans-Medium", 7.8) + 14
                c.setStrokeColor(LINEA_2)
                c.setFillColor(SUPERFICIE)
                c.setLineWidth(0.6)
                c.roundRect(x, y - 4, cw, 14, 7, stroke=1, fill=1)
                c.setFillColor(INK)
                c.setFont("Sans-Medium", 7.8)
                c.drawString(x + 7, y + 0.6, chip)
                x += cw + 5
            y -= 3
        if self.meta:
            y -= 4
            c.setFillColor(GRIGIO)
            c.setFont("Sans", 8.2)
            for meta in self.meta:
                y -= 11
                while stringWidth(meta, "Sans", 8.2) > w and " " in meta:
                    meta = meta.rsplit(" ", 1)[0]
                c.drawString(0, y + 2, meta)
        c.restoreState()


def sezione(testo: str, stile, larghezza) -> Table:
    """Titolo di sezione: filo d'inchiostro sopra, titolo con le grazie e, dopo il primo " · ",
    la spiegazione in piccolo e in grigio sulla stessa riga."""
    titolo, _, resto = testo.partition(" · ")
    if resto:
        titolo += (f'<font name="Sans" size="7.6" color="#6f6d66">&nbsp;&nbsp;&nbsp;'
                   f'{resto.replace(" · ", ", ")}</font>')
    p = Paragraph(titolo, stile.clone("sez", spaceBefore=0, spaceAfter=0))
    t = Table([[p]], colWidths=[larghezza])
    t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.8, INK), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    t.spaceBefore, t.spaceAfter = stile.spaceBefore + 2, 2
    return t


class Capitolo(Flowable):
    """Apertura di un capitolo del report: numero arancio, titolo grande, cosa contiene."""

    def __init__(self, larghezza, numero: int, titolo: str, descrizione: str = ""):
        super().__init__()
        self.w, self.n, self.titolo, self.descr = larghezza, numero, titolo, descrizione
        self.righe = _righe(descrizione, "Sans", 8.4, larghezza * 0.8) if descrizione else []
        self.h = 12 + 26 + 4 + 12 * len(self.righe) + 12

    def wrap(self, aw, ah):
        return self.w, self.h

    def draw(self):
        c, w = self.canv, self.w
        y = self.h - 9
        c.saveState()
        c.setFillColor(ARANCIO)
        c.setFont("Sans-Semi", 7.5)
        c.drawString(0, y, f"{self.n:02d}")
        c.setFillColor(GRIGIO)
        c.setFont("Sans-Semi", 7.2)
        c.drawString(16, y, "CAPITOLO")
        y -= 25
        c.setFillColor(INK)
        c.setFont("Serif", 23)
        c.drawString(0, y, self.titolo)
        c.setFillColor(GRIGIO)
        c.setFont("Sans", 8.4)
        y -= 4
        for r in self.righe:
            y -= 12
            c.drawString(0, y, r)
        c.setStrokeColor(INK)
        c.setLineWidth(0.8)
        c.line(0, 2, w, 2)
        c.restoreState()


class Sommario(Flowable):
    """Riga "In questo report": i capitoli numerati, per orientarsi prima di leggere."""

    def __init__(self, larghezza, capitoli: list[str]):
        super().__init__()
        self.w, self.capitoli = larghezza, capitoli
        self.h = 22

    def wrap(self, aw, ah):
        return self.w, self.h

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(SUPERFICIE)
        c.roundRect(0, 0, self.w, self.h, 11, stroke=0, fill=1)
        x, y = 10, 7.6
        c.setFillColor(GRIGIO)
        c.setFont("Sans-Semi", 6.8)
        c.drawString(x, y, "IN QUESTO REPORT")
        x += stringWidth("IN QUESTO REPORT", "Sans-Semi", 6.8) + 12
        for i, t in enumerate(self.capitoli, start=1):
            c.setFillColor(ARANCIO)
            c.setFont("Sans-Semi", 7.6)
            c.drawString(x, y, f"{i:02d}")
            x += stringWidth(f"{i:02d}", "Sans-Semi", 7.6) + 4
            c.setFillColor(INK)
            c.setFont("Sans-Medium", 7.8)
            c.drawString(x, y, t)
            x += stringWidth(t, "Sans-Medium", 7.8) + 14
        c.restoreState()


class Tessera(Flowable):
    """Voce del "come stanno in campionato": valore, giudizio, barra con una casella per
    squadra (quella colorata è la loro posizione)."""

    def __init__(self, larghezza, voce, valore_txt, altezza=24 * mm):
        super().__init__()
        self.w, self.h, self.v, self.txt = larghezza, altezza, voce, valore_txt

    def wrap(self, aw, ah):
        return self.w, self.h

    def draw(self):
        c, v, w, h = self.canv, self.v, self.w, self.h
        tinta = TINTA[v["tipo"]]
        c.saveState()
        c.setFillColor(SUPERFICIE)
        c.roundRect(0, 0, w, h, 2.2 * mm, stroke=0, fill=1)
        c.restoreState()
        x = 3.2 * mm
        c.setFillColor(GRIGIO)
        c.setFont("Sans-Semi", 6.2)
        c.drawString(x, h - 5.2 * mm, v["etichetta"].upper())
        c.setFillColor(INK)
        c.setFont("Serif", 18)
        c.drawString(x, h - 11.4 * mm, self.txt)
        c.setFillColor(TESTO_TINTA[v["tipo"]])
        c.setFont("Sans-Semi", 6.8)
        c.drawString(x, h - 14.6 * mm, f"{v['giudizio']} · {v['posizione']}° su {v['squadre']}")
        n = max(v["squadre"], 1)
        seg_w = (w - 2 * x) / n
        for i in range(n):
            c.setFillColor(tinta if i + 1 == v["posizione"] else LINEA_2)
            c.roundRect(x + i * seg_w + 0.3, h - 18.4 * mm, seg_w - 0.8, 1.4 * mm, 0.4, stroke=0, fill=1)
        c.setFillColor(GRIGIO)
        c.setFont("Sans", 6.1)
        c.drawString(x, 2.4 * mm, v["spiega"])


class FotoMaglia(Flowable):
    """Foto del giocatore in un riquadro arrotondato, con il numero di maglia in un cerchio
    arancio; senza foto le iniziali."""

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
        c.setFillColor(colors.HexColor("#e6e2d6"))
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
            c.setFillColor(colors.HexColor("#8f8b7f"))
            c.setFont("Serif", 21)
            c.drawCentredString(w / 2, h / 2 - 7, "".join(x[0] for x in self.nome.split()[:2]).upper())
        c.restoreState()
        if self.maglia:
            c.setFillColor(ARANCIO)
            c.circle(4.2 * mm, h - 4.2 * mm, 3.4 * mm, stroke=0, fill=1)
            c.setFillColor(SFONDO)
            c.setFont("Sans-Semi", 8.5 if len(str(self.maglia)) < 3 else 7)
            c.drawCentredString(4.2 * mm, h - 5.3 * mm, str(self.maglia))


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
        c.setFillColor(LINEA)
        c.roundRect(0, 0, w, h, h / 2, stroke=0, fill=1)
        c.setFillColor(ARANCIO)
        c.roundRect(0, 0, w * quota, h, h / 2, stroke=0, fill=1)
        c.setFillColor(INK)
        c.rect(w - 1.2, -0.8, 1.2, h + 1.6, stroke=0, fill=1)
