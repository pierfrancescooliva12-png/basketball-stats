"""Report individuale di sviluppo, da consegnare (o inoltrare) al singolo giocatore.

Una pagina A4 nello stile dei report: chi è e i suoi numeri, il profilo rispetto ai giocatori
dello stesso ruolo del campionato (sei barre e il valore di impatto), punti di forza, dove può
crescere, le aree di miglioramento con l'obiettivo, la prestazione che sposta il risultato,
l'andamento partita per partita, il piano delle prossime settimane e lo spazio per le note.

Il tono è rivolto al giocatore: niente confronti con i compagni, solo con il ruolo."""

import io
from datetime import date

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (Flowable, KeepInFrame, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from . import config
from . import confronto as CF
from . import figurine as FG
from . import pdf_stile as ST
from . import sviluppo as SV
from .report_pdf import _carta, _esc, _fmt, _fonts, _styles, _table

NAVY, BLU, ROSSO, ARANCIO = ST.NAVY, ST.BLU, ST.ROSSO, ST.ARANCIO
INK, GRIGIO, SEGMENTO = ST.INK, ST.GRIGIO, ST.SEGMENTO
BORDO = colors.HexColor("#e3e0d4")


class Barre(Flowable):
    """Profilo rispetto al ruolo: una barra per dimensione (percentile 0-100)."""

    def __init__(self, larghezza, barre: dict, riga=7.2 * mm):
        super().__init__()
        self.w, self.barre, self.riga = larghezza, barre, riga
        self.h = riga * len(barre)

    def wrap(self, aw, ah):
        return self.w, self.h

    def draw(self):
        c, et = self.canv, 34 * mm
        bw = self.w - et - 12 * mm
        for i, (k, v) in enumerate(self.barre.items()):
            y = self.h - (i + 1) * self.riga + 2.2 * mm
            c.setFillColor(INK)
            c.setFont("Sans-Semi", 8)
            c.drawString(0, y, k.upper())
            c.setFillColor(SEGMENTO)
            c.roundRect(et, y - 0.2 * mm, bw, 2.6 * mm, 1.3 * mm, stroke=0, fill=1)
            ok = v is not None and not pd.isna(v)
            if ok:
                tinta = BLU if v >= 70 else (ROSSO if v < 35 else colors.HexColor("#b9b5a8"))
                c.setFillColor(tinta)
                c.roundRect(et, y - 0.2 * mm, max(2.6 * mm, bw * v / 100), 2.6 * mm, 1.3 * mm, stroke=0, fill=1)
            c.setFillColor(GRIGIO)                     # tacca della mediana del ruolo
            c.rect(et + bw / 2 - 0.3, y - 1 * mm, 0.6, 4.2 * mm, stroke=0, fill=1)
            c.setFillColor(INK)
            c.setFont("Serif", 11)
            c.drawRightString(self.w, y - 0.3 * mm, str(int(round(v))) if ok else "–")


class Andamento(Flowable):
    """Punti partita per partita (barre) con la media stagionale (linea tratteggiata)."""

    def __init__(self, larghezza, log: pd.DataFrame, altezza=42 * mm):
        super().__init__()
        self.w, self.h, self.log = larghezza, altezza, log

    def wrap(self, aw, ah):
        return self.w, self.h

    def draw(self):
        c, log = self.canv, self.log
        n = len(log)
        if not n:
            return
        base, top = 9 * mm, self.h - 5 * mm
        massimo = max(10.0, float(log["punti"].max()) * 1.15)
        passo = self.w / n
        bw = min(12 * mm, passo * 0.6)
        media = float(log["punti"].mean())
        for i, r in enumerate(log.itertuples()):
            x = i * passo + (passo - bw) / 2
            h = (top - base) * float(r.punti) / massimo
            c.setFillColor(BLU if r.punti >= media else colors.HexColor("#9fb6d8"))
            c.roundRect(x, base, bw, max(0.6, h), 1, stroke=0, fill=1)
            c.setFillColor(INK)
            c.setFont("Serif", 9)
            c.drawCentredString(x + bw / 2, base + h + 1.2 * mm, str(int(r.punti)))
            c.setFillColor(GRIGIO)
            c.setFont("Sans", 6)
            c.drawCentredString(x + bw / 2, base - 3.4 * mm, f"G{int(r.giornata)}")
            etichetta = str(r.avv_breve)
            while len(etichetta) > 3 and stringWidth(etichetta, "Sans", 6) > passo - 2:
                etichetta = etichetta[:-1]
            c.drawCentredString(x + bw / 2, base - 6.2 * mm, etichetta)
        y = base + (top - base) * media / massimo
        c.setStrokeColor(ARANCIO)
        c.setLineWidth(1)
        c.setDash(3, 2)
        c.line(0, y, self.w, y)
        c.setDash()
        c.setFillColor(ARANCIO)
        c.setFont("Sans-Semi", 6.5)
        c.drawString(0, top + 1.5 * mm, f"- - media {_fmt(media)} punti")
        c.setStrokeColor(BORDO)
        c.setLineWidth(0.5)
        c.line(0, base, self.w, base)


def _breve(nome: str) -> str:
    """Città della squadra per le etichette del grafico ("Ruvo di Puglia", "Cento")."""
    generici = {"basket", "pallacanestro", "basketball", "academy"}
    parole = [p for p in str(nome).split() if not p.isdigit() and p.lower() not in generici]
    if len(parole) >= 3 and parole[-2].islower():
        return " ".join(parole[-3:])
    return parole[-1] if parole else str(nome)


# i testi delle schede sono scritti per lo staff ("con lui in campo"): nel report al giocatore
# si passa al "tu"
TU = [("Con lui in campo", "Con te in campo"), ("con lui in campo", "con te in campo"),
      ("senza di lui", "senza di te"), ("Senza di lui", "Senza di te"), ("le sue partite", "le tue partite"),
      ("Le sue partite", "Le tue partite"), ("la sua squadra", "la squadra"), ("La sua squadra", "La squadra"),
      ("la sua media", "la tua media"), ("sua media", "tua media"), ("quando è fuori", "quando sei fuori"),
      ("quando è in campo", "quando sei in campo")]


def tu(testo) -> str:
    s = str(testo)
    for a, b in TU:
        s = s.replace(a, b)
    return s


def game_log(ctx, gid: str, sid: int) -> pd.DataFrame:
    bg = ctx.bg
    log = bg[(bg["giocatore_id"] == gid) & (bg["squadra_id"] == sid)].sort_values(["data", "giornata"]).copy()
    log["avv_breve"] = log["avversario"].map(_breve)
    return log


def scheda(ctx, sid: int, gid: str, foto: bool = True) -> dict | None:
    """La scheda di sviluppo del giocatore (come nella pagina Sviluppo)."""
    for g in SV.squadra(ctx, sid, foto=foto):
        if g["giocatore_id"] == gid:
            return g
    return None


def build(ctx, sid: int, gid: str, hist: pd.DataFrame | None = None, foto: bool = True,
          g: dict | None = None) -> bytes:
    """Report individuale su una pagina A4 (g: la scheda di sviluppo, se già calcolata)."""
    _fonts()
    S = _styles()
    g = g if g is not None else scheda(ctx, sid, gid, foto=foto)
    if g is None:
        raise ValueError("giocatore senza minuti sufficienti per il report")
    nome = FG.maiuscole(g["nome"])
    squadra = ctx.nomi_squadre.get(sid, str(sid))
    stagione = config.STAGIONI.get(ctx.stagione, ctx.stagione)
    oggi = date.today().strftime("%d/%m/%Y")
    W = A4[0] - 24 * mm
    HW = W / 2 - 3                      # mezza colonna (le carte affiancate)
    tit = lambda t, c=NAVY: Paragraph(t, ParagraphStyle(  # noqa: E731
        "rg_t", parent=S["h3"], fontSize=10, leading=12, textColor=c, spaceBefore=0, spaceAfter=3))
    voce = ParagraphStyle("rg_v", parent=S["body"], fontSize=8, leading=10, leftIndent=8, firstLineIndent=-8)
    piccolo = ParagraphStyle("rg_s", parent=S["small"], fontSize=7, leading=8.8)

    def affianca(sx, dx, sp=6):
        t = Table([[sx, dx]], colWidths=[W / 2, W / 2])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (0, 0), 3), ("LEFTPADDING", (1, 0), (1, 0), 3),
                               ("RIGHTPADDING", (1, 0), (1, 0), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), sp)]))
        return t

    testata = ST.Intestazione(W, 12 * mm, 12 * mm, f"Report individuale · stagione {stagione}", nome,
                              meta=f"{squadra} · aggiornato al {oggi}", marchio=config.BRAND, grande=False)
    el = []

    # ---------------------------------------------------------------- chi è | profilo rispetto al ruolo
    meta = [x for x in (g.get("ruolo"), f"{g['altezza']} cm" if g.get("altezza") else None,
                        f"{g['eta']} anni" if g.get("eta") else None, g.get("nazionalita"),
                        f"{g['partite']} partite") if x]
    kv = ParagraphStyle("rg_kv", parent=S["kpi_v"], fontSize=14, leading=15)
    lw = HW - 18 - 25 * mm
    numeri = Table([[Paragraph(k.upper(), S["kpi_l"]) for k, _ in g["numeri"]],
                    [Paragraph(v, kv) for _, v in g["numeri"]]],
                   colWidths=[lw / max(1, len(g["numeri"]))] * len(g["numeri"]), hAlign="LEFT")
    numeri.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    an = g.get("andamento")
    righe = [Paragraph(_esc(" · ".join(map(str, meta))), piccolo), Spacer(1, 3), numeri, Spacer(1, 3),
             Paragraph(_esc(g["tiro"]), piccolo)]
    if an:
        (pu, pm), (mi, mm_) = an["punti"], an["minuti"]
        righe.append(Paragraph(f"Ultime {an['ultime']}: {_fmt(pu)} punti in {_fmt(mi)}' (stagione {_fmt(pm)} in "
                               f"{_fmt(mm_)}') · <b>{_esc(an['tendenza'])}</b>", piccolo))
    testa = Table([[ST.FotoMaglia(g.get("foto"), nome, g.get("maglia"), w=22 * mm, h=28 * mm), righe]],
                  colWidths=[25 * mm, lw])
    testa.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0)]))
    chi = _carta([tit("Chi sei in campo"), testa], HW, bordo=ARANCIO, pad=8)

    p = CF.scheda(hist, gid, ctx.stagione) if hist is not None else None
    if p is not None:
        barre = {etichetta: p["dimensioni"].get(chiave) for chiave, etichetta in FG.BARRE}
        imp = barre.get("Impatto")
        ruolo = FG.PLURALE_RUOLO.get(p["ruolo"], p["ruolo"].lower())
        imp_txt = "–" if imp is None or pd.isna(imp) else str(int(round(imp)))
        profilo = [tit(f'IL TUO PROFILO · <font color="#ff7a1a">IMPATTO {imp_txt}</font>'),
                   Paragraph(f"Confronto con {p['pool']} {ruolo} di {p['scala']}: percentuale di giocatori del "
                             "ruolo che fanno meno di te (tacca = metà del gruppo)."
                             + (" Pochi minuti: valori da confermare." if p.get("pochi_dati") else ""), piccolo),
                   Spacer(1, 3), Barre(HW - 18, barre, riga=5.4 * mm)]
    else:
        profilo = [tit("Il tuo profilo"), Paragraph("Confronto con il ruolo non disponibile.", piccolo)]
    el.append(affianca(chi, _carta(profilo, HW, bordo=NAVY, pad=8)))

    # ---------------------------------------------------------------- forza | crescita
    bene = [tit("I tuoi punti di forza", BLU)] + [
        Paragraph(f'<font color="#2a78d6"><b>+</b></font>&nbsp;&nbsp;{_esc(tu(x))}', voce) for x in g["forza"][:4]]
    if len(bene) == 1:
        bene.append(Paragraph("Servono ancora qualche partita per individuarli.", piccolo))
    cresci = [tit("Dove puoi crescere", ROSSO)] + [
        Paragraph(f'<font color="#d95926"><b>›</b></font>&nbsp;&nbsp;{_esc(tu(x))}', voce) for x in g["deboli"][:4]]
    if len(cresci) == 1:
        cresci.append(Paragraph("Nessuna voce sotto il livello del campionato.", piccolo))
    el.append(affianca(_carta(bene, HW, pad=8), _carta(cresci, HW, pad=8)))

    # ---------------------------------------------------------------- aree di miglioramento (tutta riga)
    cw = (W - 4 - 16) / 2
    aree = [tit("Aree di miglioramento · obiettivi", ROSSO),
            Paragraph("Dove sei tra i più bassi del ruolo. Obiettivo = il valore normale del ruolo e, quando si può "
                      "stimare, quanti punti a partita vale raggiungerlo.", piccolo), Spacer(1, 3)]
    if g["aree"]:
        celle = []
        for a in g["aree"][:4]:
            punti = (f" · circa <b>{_fmt(a['punti_pg'])}</b> punti a partita" if pd.notna(a["punti_pg"])
                     and a["punti_pg"] >= 0.3 else "")
            celle.append([Paragraph(f"<b>{_esc(a['voce'])}</b>", ParagraphStyle("rg_av", parent=S["body"],
                                                                              fontSize=8, leading=10)),
                          Paragraph(f"ora {_esc(a['valore'])} › obiettivo <b>{_esc(a['obiettivo'])}</b>{punti}",
                                    piccolo),
                          ST.Obiettivo(cw - 12, a["da"], a["a"], a["alto"])])
        coppie = [celle[i:i + 2] + [[Spacer(1, 1)]] * (2 - len(celle[i:i + 2])) for i in range(0, len(celle), 2)]
        t = Table(coppie, colWidths=[cw, cw])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        aree.append(t)
    else:
        aree.append(Paragraph("Nessuna voce sotto il livello del ruolo: l'obiettivo è confermare questi numeri.",
                              S["body"]))
    try:
        from . import impatto as I
        ob = [o for o in I.obiettivi(ctx, sid, n=40, avversaria=False) if o["giocatore_id"] == gid]
    except Exception:
        ob = []
    if ob:
        o = ob[0]
        aree += [Paragraph(f'<font color="#ff7a1a"><b>LA PRESTAZIONE CHE SPOSTA IL RISULTATO</b></font> · '
                           f"<b>{_esc(o['obiettivo'])}</b> ({_esc(I.testo_vale(o))})",
                           ParagraphStyle("rg_ob", parent=S["body"], fontSize=8, leading=10)),
                 Paragraph(_esc(tu(o["perche"][:1].upper() + o["perche"][1:])), piccolo)]
    el += [_carta(aree, W - 4, bordo=ROSSO, pad=8), Spacer(1, 6)]

    # ---------------------------------------------------------------- andamento | piano e note
    log = game_log(ctx, gid, sid)
    anda = [tit("Partita per partita" if len(log) <= 12 else "Le ultime 12 partite"),
            Paragraph("Punti in ogni partita; in blu sopra la tua media (linea arancione).", piccolo), Spacer(1, 2)]
    if not log.empty:
        anda.append(Andamento(HW - 16, log.tail(12), altezza=38 * mm))
    piano = [tit("Il piano delle prossime settimane", BLU)]
    for i, a in enumerate(g["aree"][:3], 1):
        piano.append(Paragraph(f"<b>{i}. {_esc(a['voce'])}</b>: da {_esc(a['valore'])} a "
                               f"<b>{_esc(a['obiettivo'])}</b>", voce))
    if g["forza"]:
        piano.append(Paragraph(f"<b>Da mantenere</b>: {_esc(tu(g['forza'][0][:1].lower() + g['forza'][0][1:]))}",
                               voce))
    righe_note = Table([[""]] * 3, colWidths=[HW - 16], rowHeights=[6.5 * mm] * 3)
    righe_note.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDO)]))
    piano += [Spacer(1, 4), Paragraph("<b>Note dello staff</b>", piccolo), righe_note]
    el.append(affianca(_carta(anda, HW, pad=8), _carta(piano, HW, bordo=BLU, pad=8)))
    if not log.empty:
        ultime = log.tail(6).iloc[::-1]
        rows = [["G.", "Data", "Avversario", "", "Min", "Pt", "2P", "3P", "TL", "Rimb", "Ass", "Perse", "Val"]]
        for r in ultime.itertuples():
            data = pd.Timestamp(str(r.data)[:10]).strftime("%d/%m") if pd.notna(r.data) else "–"
            rows.append([str(int(r.giornata)), data, Paragraph(_esc(r.avversario), S["cell"]),
                         "C" if r.casa else "T", _fmt(r.minuti, 0), str(int(r.punti)),
                         f"{int(r.t2m)}/{int(r.t2a)}", f"{int(r.t3m)}/{int(r.t3a)}", f"{int(r.tlm)}/{int(r.tla)}",
                         str(int(r.rimb_tot)), str(int(r.assist)), str(int(r.perse)), str(int(r.valutazione))])
        larg = [8 * mm, 11 * mm, 0, 6 * mm] + [10.5 * mm] * 9
        larg[2] = W - 20 - sum(larg)
        ult = [tit(f"Le ultime {len(ultime)} partite"), _table(rows, larg, align_right_from=4, align_left=(2,))]
        el += [_carta(ult, W - 4, pad=8), Spacer(1, 4)]
    el.append(Paragraph("Rimbalzi, assist, recuperi e falli sono a partita; un'azione è un tiro, una coppia di liberi o "
                        "una palla persa; punti per tiro = punti per ogni tiro tentato, liberi compresi. I numeri si "
                        "aggiornano dopo ogni partita: rivedremo insieme i progressi nel prossimo report.", piccolo))

    # tutto su una pagina: se il contenuto è più lungo si riduce, non va a capo
    _, h_testa = testata.wrap(W, A4[1])
    spazio = A4[1] - 12 * mm - 14 * mm - 12 - h_testa
    corpo = KeepInFrame(W, spazio, el, mode="shrink")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                            bottomMargin=14 * mm, title=f"Report individuale · {nome}", author=config.BRAND)

    pagina = ST.piede(f"Report individuale · {nome} · {squadra}")
    doc.build([testata, corpo], onFirstPage=pagina, onLaterPages=pagina)
    return buf.getvalue()


def nome_file(nome: str) -> str:
    from .report_pdf import slug
    return f"report_{slug(FG.maiuscole(nome))}.pdf"
