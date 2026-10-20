"""Report individuale di sviluppo, da consegnare (o inoltrare) al singolo giocatore.

Due pagine nello stile dei report:
1. chi è e i suoi numeri, il profilo rispetto ai giocatori dello stesso ruolo del campionato
   (sei barre e il valore di impatto), punti di forza, dove può crescere, le aree di
   miglioramento con l'obiettivo e la prestazione che sposta il risultato della squadra;
2. l'andamento partita per partita (grafico e tabella), il piano di lavoro e uno spazio per
   le note dello staff.

Il tono è rivolto al giocatore: niente confronti con i compagni, solo con il ruolo."""

import io
from datetime import date

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (Flowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from . import config
from . import confronto as CF
from . import figurine as FG
from . import pdf_stile as ST
from . import sviluppo as SV
from .report_pdf import _carta, _esc, _fmt, _fonts, _styles, _table

NAVY, BLU, ROSSO, ARANCIO = ST.NAVY, ST.BLU, ST.ROSSO, ST.ARANCIO
INK, GRIGIO, SEGMENTO = ST.INK, ST.GRIGIO, ST.SEGMENTO
BORDO = colors.HexColor("#dfe3eb")


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
            c.setFont("Barlow-SemiBold", 8)
            c.drawString(0, y, k.upper())
            c.setFillColor(SEGMENTO)
            c.roundRect(et, y - 0.2 * mm, bw, 2.6 * mm, 1.3 * mm, stroke=0, fill=1)
            ok = v is not None and not pd.isna(v)
            if ok:
                tinta = BLU if v >= 70 else (ROSSO if v < 35 else colors.HexColor("#9aa3b5"))
                c.setFillColor(tinta)
                c.roundRect(et, y - 0.2 * mm, max(2.6 * mm, bw * v / 100), 2.6 * mm, 1.3 * mm, stroke=0, fill=1)
            c.setFillColor(GRIGIO)                     # tacca della mediana del ruolo
            c.rect(et + bw / 2 - 0.3, y - 1 * mm, 0.6, 4.2 * mm, stroke=0, fill=1)
            c.setFillColor(INK)
            c.setFont("Condensed", 11)
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
            c.setFont("Condensed", 9)
            c.drawCentredString(x + bw / 2, base + h + 1.2 * mm, str(int(r.punti)))
            c.setFillColor(GRIGIO)
            c.setFont("Barlow", 6)
            c.drawCentredString(x + bw / 2, base - 3.4 * mm, f"G{int(r.giornata)}")
            c.drawCentredString(x + bw / 2, base - 6.2 * mm, str(r.avv_breve)[:12])
        y = base + (top - base) * media / massimo
        c.setStrokeColor(ARANCIO)
        c.setLineWidth(1)
        c.setDash(3, 2)
        c.line(0, y, self.w, y)
        c.setDash()
        c.setFillColor(ARANCIO)
        c.setFont("Barlow-SemiBold", 6.5)
        c.drawRightString(self.w, y + 1.2 * mm, f"media {_fmt(media)}")
        c.setStrokeColor(BORDO)
        c.setLineWidth(0.5)
        c.line(0, base, self.w, base)


def _breve(nome: str) -> str:
    """Città della squadra per le etichette del grafico ("Ruvo di Puglia", "Cento")."""
    parole = [p for p in str(nome).split() if not p.isdigit()]
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


def build(ctx, sid: int, gid: str, hist: pd.DataFrame | None = None, foto: bool = True) -> bytes:
    _fonts()
    S = _styles()
    g = scheda(ctx, sid, gid, foto=foto)
    if g is None:
        raise ValueError("giocatore senza minuti sufficienti per il report")
    nome = FG.maiuscole(g["nome"])
    squadra = ctx.nomi_squadre.get(sid, str(sid))
    stagione = config.STAGIONI.get(ctx.stagione, ctx.stagione)
    oggi = date.today().strftime("%d/%m/%Y")
    W = A4[0] - 24 * mm
    h2 = ParagraphStyle("rg_h2", parent=S["h2"], textColor=NAVY, spaceBefore=4, spaceAfter=3)
    voce = ParagraphStyle("rg_v", parent=S["body"], fontSize=8.5, leading=11, leftIndent=9, firstLineIndent=-9)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                            bottomMargin=14 * mm, title=f"Report individuale · {nome}", author=config.BRAND)
    el = [ST.Intestazione(W, 12 * mm, 12 * mm, f"Report individuale · stagione {stagione}", nome,
                          meta=f"{squadra} · aggiornato al {oggi}", marchio=config.BRAND)]

    # ---------------------------------------------------------------- chi è e i suoi numeri
    meta = [x for x in (g.get("ruolo"), f"{g['altezza']} cm" if g.get("altezza") else None,
                        f"{g['eta']} anni" if g.get("eta") else None, g.get("nazionalita"),
                        f"{g['partite']} partite") if x]
    numeri = Table([[Paragraph(k.upper(), S["kpi_l"]) for k, _ in g["numeri"]],
                    [Paragraph(v, S["kpi_v"]) for _, v in g["numeri"]]],
                   colWidths=[(W - 40 * mm) / max(1, len(g["numeri"]))] * len(g["numeri"]), hAlign="LEFT")
    numeri.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    an = g.get("andamento")
    righe = [Paragraph(_esc(" · ".join(map(str, meta))), S["small"]), Spacer(1, 4), numeri, Spacer(1, 3),
             Paragraph(_esc(g["tiro"]), S["small"])]
    if an:
        (pu, pm), (mi, mm_) = an["punti"], an["minuti"]
        righe.append(Paragraph(f"Ultime {an['ultime']} partite: {_fmt(pu)} punti in {_fmt(mi)} minuti "
                               f"(stagione {_fmt(pm)} in {_fmt(mm_)}) · <b>{_esc(an['tendenza'])}</b>", S["small"]))
    testa = Table([[ST.FotoMaglia(g.get("foto"), nome, g.get("maglia"), w=28 * mm, h=35 * mm), righe]],
                  colWidths=[32 * mm, W - 32 * mm - 20])
    testa.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    el += [_carta(testa, W - 4, bordo=ARANCIO, pad=9), Spacer(1, 6)]

    # ---------------------------------------------------------------- profilo rispetto al ruolo
    p = CF.scheda(hist, gid, ctx.stagione) if hist is not None else None
    if p is not None:
        barre = {etichetta: p["dimensioni"].get(chiave) for chiave, etichetta in FG.BARRE}
        imp = barre.get("Impatto")
        ruolo = FG.PLURALE_RUOLO.get(p["ruolo"], p["ruolo"].lower())
        sinistra = [Paragraph("IL TUO PROFILO RISPETTO AL RUOLO", h2),
                    Paragraph(f"Confronto con {p['pool']} {ruolo} di {p['scala']}. Il numero è la percentuale "
                              "di giocatori dello stesso ruolo che fanno meno di te; la tacca grigia è la metà "
                              "del gruppo.", S["small"]), Spacer(1, 4), Barre(W - 54 * mm, barre)]
        cifra = ParagraphStyle("rg_imp", parent=S["kpi_v"], fontSize=40, leading=40, textColor=ARANCIO,
                               alignment=1)
        destra = [Spacer(1, 10), Paragraph("–" if imp is None or pd.isna(imp) else str(int(round(imp))), cifra),
                  Paragraph("IMPATTO", ParagraphStyle("rg_il", parent=S["kpi_l"], alignment=1)),
                  Spacer(1, 4), Paragraph(FG.SIGLA_RUOLO.get(p["ruolo"], p["ruolo"]).upper(),
                                          ParagraphStyle("rg_r", parent=S["h3"], alignment=1, textColor=NAVY))]
        if p.get("pochi_dati"):
            destra.append(Paragraph("Pochi minuti giocati: valori da confermare.",
                                    ParagraphStyle("rg_pd", parent=S["small"], alignment=1)))
        t = Table([[sinistra, destra]], colWidths=[W - 50 * mm, 38 * mm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("LINEBEFORE", (1, 0), (1, 0), 0.5, BORDO)]))
        el += [_carta(t, W - 4, bordo=NAVY, pad=9), Spacer(1, 6)]

    # ---------------------------------------------------------------- forza e crescita
    cw = (W - 4 - 18) / 2
    tit = lambda t, c: Paragraph(t, ParagraphStyle("rg_t", parent=S["h3"], textColor=c, spaceBefore=0))  # noqa: E731
    bene = [tit("I TUOI PUNTI DI FORZA", BLU)] + [
        Paragraph(f'<font color="#2a78d6"><b>+</b></font>&nbsp;&nbsp;{_esc(tu(x))}', voce) for x in g["forza"]]
    if len(bene) == 1:
        bene.append(Paragraph("Servono ancora qualche partita per individuarli.", S["small"]))
    cresci = [tit("DOVE PUOI CRESCERE", ROSSO)] + [
        Paragraph(f'<font color="#d95926"><b>›</b></font>&nbsp;&nbsp;{_esc(tu(x))}', voce) for x in g["deboli"]]
    if len(cresci) == 1:
        cresci.append(Paragraph("Nessuna voce sotto il livello del campionato.", S["small"]))
    due = Table([[bene, cresci]], colWidths=[cw, cw])
    due.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 9), ("LINEBEFORE", (1, 0), (1, 0), 0.5, BORDO),
                             ("LEFTPADDING", (1, 0), (1, 0), 9)]))
    el += [_carta(due, W - 4, pad=9), Spacer(1, 6)]

    # ---------------------------------------------------------------- aree di miglioramento
    aree = [Paragraph("AREE DI MIGLIORAMENTO · OBIETTIVI", h2),
            Paragraph("Voci in cui sei tra i più bassi del ruolo. L'obiettivo è il valore normale del ruolo e, "
                      "quando si può stimare, quanti punti a partita vale raggiungerlo.", S["small"]), Spacer(1, 4)]
    if g["aree"]:
        celle = []
        for a in g["aree"]:
            punti = (f"circa <b>{_fmt(a['punti_pg'])}</b> punti a partita" if pd.notna(a["punti_pg"])
                     and a["punti_pg"] >= 0.3 else "")
            celle.append([Paragraph(f"<b>{_esc(a['voce'])}</b>", S["body"]),
                          Paragraph(f"ora {_esc(a['valore'])} › obiettivo <b>{_esc(a['obiettivo'])}</b>", S["small"]),
                          ST.Obiettivo(cw - 14, a["da"], a["a"], a["alto"]),
                          Paragraph(punti, S["small"]) if punti else Spacer(1, 1)])
        coppie = [celle[i:i + 2] + [[Spacer(1, 1)]] * (2 - len(celle[i:i + 2])) for i in range(0, len(celle), 2)]
        t = Table(coppie, colWidths=[cw, cw])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
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
        aree += [Spacer(1, 2), Paragraph("LA PRESTAZIONE CHE SPOSTA IL RISULTATO",
                                         ParagraphStyle("rg_o", parent=S["h3"], textColor=ARANCIO, spaceBefore=2)),
                 Paragraph(f"<b>{_esc(o['obiettivo'].capitalize())}</b> · {_esc(I.testo_vale(o))}", S["body"]),
                 Paragraph(_esc(tu(o["perche"][:1].upper() + o["perche"][1:])), S["small"])]
    el += [KeepTogether(_carta(aree, W - 4, bordo=ROSSO, pad=9))]

    # ---------------------------------------------------------------- pagina 2: partita per partita
    log = game_log(ctx, gid, sid)
    el += [PageBreak(), Paragraph("PARTITA PER PARTITA", h2),
           Paragraph("Punti in ogni partita: in blu quelle sopra la tua media stagionale (linea arancione).",
                     S["small"]), Spacer(1, 4)]
    if not log.empty:
        el += [_carta(Andamento(W - 22, log), W - 4, pad=9), Spacer(1, 6)]
        rows = [["G.", "Data", "Avversario", "", "Min", "Pt", "2P", "3P", "TL", "Rimb", "Ass", "Perse", "Val"]]
        for r in log.itertuples():
            data = pd.Timestamp(str(r.data)[:10]).strftime("%d/%m") if pd.notna(r.data) else "–"
            rows.append([str(int(r.giornata)), data, Paragraph(_esc(r.avversario), S["cell"]),
                         "C" if r.casa else "T", _fmt(r.minuti, 0), str(int(r.punti)),
                         f"{int(r.t2m)}/{int(r.t2a)}", f"{int(r.t3m)}/{int(r.t3a)}", f"{int(r.tlm)}/{int(r.tla)}",
                         str(int(r.rimb_tot)), str(int(r.assist)), str(int(r.perse)), str(int(r.valutazione))])
        larg = [9 * mm, 12 * mm, None, 6 * mm] + [11 * mm] * 9
        larg[2] = W - 4 - sum(x for x in larg if x)
        el += [_table(rows, larg, align_right_from=4, align_left=(2,)), Spacer(1, 8)]

    # ---------------------------------------------------------------- piano di lavoro e note
    piano = [Paragraph("IL PIANO DELLE PROSSIME SETTIMANE", h2)]
    if g["aree"]:
        for i, a in enumerate(g["aree"][:3], 1):
            piano.append(Paragraph(f"<b>{i}. {_esc(a['voce'])}</b>: da {_esc(a['valore'])} a "
                                   f"<b>{_esc(a['obiettivo'])}</b>.", voce))
        piano.append(Spacer(1, 3))
    if g["forza"]:
        piano.append(Paragraph(f"<b>Da mantenere</b>: {_esc(tu(g['forza'][0][:1].lower() + g['forza'][0][1:]))}.", voce))
    piano.append(Paragraph("I numeri si aggiornano dopo ogni partita: rivedremo insieme i progressi nel prossimo "
                           "report.", S["small"]))
    righe_note = Table([[""]] * 7, colWidths=[W - 22], rowHeights=[7.5 * mm] * 7)
    righe_note.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDO)]))
    note = [Paragraph("NOTE DELLO STAFF", ParagraphStyle("rg_n", parent=S["h3"], textColor=NAVY, spaceBefore=0)),
            righe_note]
    el += [KeepTogether(_carta(piano, W - 4, bordo=BLU, pad=9)), Spacer(1, 6),
           KeepTogether(_carta(note, W - 4, pad=9)), Spacer(1, 6),
           Paragraph("Come leggere i numeri: rimbalzi, assist, recuperi e falli sono a partita; un'azione è un tiro, "
                     "una coppia di liberi o una palla persa; i punti per tiro sono i punti segnati per ogni tiro "
                     "tentato, liberi compresi. Con poche partite giocate i valori vanno confermati.", S["small"])]

    def pagina(canvas, doc_):
        ST.sfondo(canvas, doc_)
        canvas.saveState()
        canvas.setFont("Barlow", 7)
        canvas.setFillColor(GRIGIO)
        canvas.drawString(12 * mm, 8 * mm, f"{config.BRAND} · {nome} · {squadra} · report individuale · {oggi}")
        canvas.drawRightString(A4[0] - 12 * mm, 8 * mm, f"pagina {doc_.page}")
        canvas.restoreState()
    doc.build(el, onFirstPage=pagina, onLaterPages=pagina)
    return buf.getvalue()


def nome_file(nome: str) -> str:
    from .report_pdf import slug
    return f"report_{slug(FG.maiuscole(nome))}.pdf"
