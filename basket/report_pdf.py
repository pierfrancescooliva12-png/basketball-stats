"""Report di scouting in PDF su una squadra (pensato per la riunione tecnica).

    python -m basket.report_pdf "Forlì"                 # reports/pdf/scouting_<squadra>.pdf
    python -m basket.report_pdf --tutte --out cartella   # un PDF per ogni squadra
"""

import argparse
import io
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepInFrame, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from . import approfondimenti as X
from . import lavagna as L
from . import config, scouting
from . import pdf_stile as ST
from .contesto import Contesto, open_readonly

FONT_DIR = config.ROOT / "assets" / "fonts"
# stile editoriale, come la piattaforma: carta crema, inchiostro, arancio solo come accento
NAVY = ST.INK                       # nome storico: il colore "scuro" dei report
ARANCIO = ST.ARANCIO
BLU = ST.BLU
ROSSO = ST.ROSSO
INK = ST.INK
GRIGIO = ST.GRIGIO
RIGA = ST.CARTA
BORDO = ST.LINEA


def _fonts():
    """Instrument Sans per i testi e Newsreader per titoli e numeri grandi (licenza OFL)."""
    if "Sans" in pdfmetrics.getRegisteredFontNames():
        return
    for name, file in (("Sans", "InstrumentSans-Regular.ttf"), ("Sans-Medium", "InstrumentSans-Medium.ttf"),
                       ("Sans-Semi", "InstrumentSans-SemiBold.ttf"), ("Serif", "Newsreader-Regular.ttf"),
                       ("Serif-Medium", "Newsreader-Medium.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))
    # <b> nei paragrafi: il semibold della stessa famiglia
    pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-Semi", italic="Sans", boldItalic="Sans-Semi")
    pdfmetrics.registerFontFamily("Sans-Medium", normal="Sans-Medium", bold="Sans-Semi", italic="Sans-Medium",
                                  boldItalic="Sans-Semi")
    pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-Medium", italic="Serif",
                                  boldItalic="Serif-Medium")


def _styles():
    return {
        "h1": ParagraphStyle("h1", fontName="Serif", fontSize=26, leading=29, textColor=INK),
        "eyebrow": ParagraphStyle("eb", fontName="Sans-Semi", fontSize=7.5, leading=10, textColor=GRIGIO),
        "meta": ParagraphStyle("meta", fontName="Sans", fontSize=9, leading=12, textColor=GRIGIO),
        "h2": ParagraphStyle("h2", fontName="Serif-Medium", fontSize=14.5, leading=17,
                             textColor=INK, spaceBefore=12, spaceAfter=5),
        "h3": ParagraphStyle("h3", fontName="Sans-Semi", fontSize=9.5, leading=12,
                             textColor=INK, spaceBefore=6, spaceAfter=3),
        "body": ParagraphStyle("body", fontName="Sans", fontSize=8.5, leading=11.6,
                               textColor=INK, alignment=TA_LEFT),
        "small": ParagraphStyle("small", fontName="Sans", fontSize=7.3, leading=9.6,
                                textColor=GRIGIO),
        "cell": ParagraphStyle("cell", fontName="Sans", fontSize=7.8, leading=9.6, textColor=INK),
        "kpi_l": ParagraphStyle("kl", fontName="Sans-Semi", fontSize=6.3, leading=8,
                                textColor=GRIGIO),
        "kpi_v": ParagraphStyle("kv", fontName="Serif", fontSize=19, leading=21,
                                textColor=INK),
        "kpi_s": ParagraphStyle("ks", fontName="Sans", fontSize=6.5, leading=8,
                                textColor=GRIGIO),
    }


class Capitoli:
    """Apre i capitoli di un report numerandoli nell'ordine in cui compaiono nel sommario."""

    def __init__(self, titoli: list[str], W):
        self.titoli, self.W = titoli, W

    def __call__(self, titolo: str, descrizione: str = "") -> list:
        n = self.titoli.index(titolo) + 1 if titolo in self.titoli else len(self.titoli) + 1
        return [ST.Capitolo(self.W, n, titolo, descrizione), Spacer(1, 8)]


def _fmt(v, d=1, signed=False):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    if isinstance(v, (int,)) and not isinstance(v, bool):
        return f"{v:+d}" if signed else str(v)
    try:
        s = f"{float(v):+.{d}f}" if signed else f"{float(v):.{d}f}"
    except (TypeError, ValueError):
        return str(v)
    return s.replace(".", ",")      # decimali all'italiana


def _table(rows, widths, header=True, align_right_from=1, zebra=True, align_left=()):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Sans"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.8),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN", (align_right_from, 0), (-1, -1), "RIGHT"),
        ("LINEBELOW", (0, 1 if header else 0), (-1, -1), 0.35, BORDO),
    ] + [("ALIGN", (c, 0), (c, -1), "LEFT") for c in align_left]
    if header:
        style += [("FONTNAME", (0, 0), (-1, 0), "Sans-Medium"),
                  ("FONTSIZE", (0, 0), (-1, 0), 6.8),
                  ("TEXTCOLOR", (0, 0), (-1, 0), GRIGIO),
                  ("LINEBELOW", (0, 0), (-1, 0), 0.7, INK)]
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), ST.CARTA_CHIARA))
    t.setStyle(TableStyle(style))
    return t


def _kpis(items, S, width):
    cells = [[Paragraph(l.upper(), S["kpi_l"]), Paragraph(v, S["kpi_v"]),
              Paragraph(s, S["kpi_s"])] for l, v, s in items]
    t = Table([[_box(c) for c in cells]], colWidths=[width / len(items)] * len(items))
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 2),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 2)]))
    return t


def _box(content):
    t = Table([[content[0]], [content[1]], [content[2]]], cornerRadii=[5, 5, 5, 5])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ST.CARTA),
                           ("TOPPADDING", (0, 0), (0, 0), 6), ("TOPPADDING", (0, 1), (-1, -1), 1.5),
                           ("BOTTOMPADDING", (0, 0), (-1, -2), 1.5), ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
                           ("LEFTPADDING", (0, 0), (-1, -1), 7)]))
    return t


def _bar_rows(df, width_bar=38 * mm):
    """Tabella Four Factors con barra squadra vs media."""
    rows = [["Metrica", "Squadra", "Media", "Pos.", ""]]
    for _, r in df.iterrows():
        d = 2 if "Liberi" in r["Metrica"] else 1
        v, m = _fmt(r["Valore"], d), _fmt(r["Media campionato"], d)
        # palle perse e rimbalzi: la percentuale con il numero a partita tra parentesi
        if pd.notna(r.get("A partita")):
            v += f"% ({_fmt(r['A partita'])})"
        if pd.notna(r.get("Media a partita")):
            m += f"% ({_fmt(r['Media a partita'])})"
        rows.append([r["Metrica"], v, m, r["Posizione"], _bar(r["Valore"], r["Media campionato"], width_bar)])
    return rows


def _bar(val, media, width):
    from reportlab.graphics.shapes import Drawing, Line, Rect
    d = Drawing(width, 8)
    if pd.isna(val) or pd.isna(media) or not media:
        return d
    hi = max(val, media) * 1.15 or 1
    d.add(Rect(0, 1.5, width * val / hi, 5, fillColor=BLU, strokeColor=None))
    x = width * media / hi
    d.add(Line(x, 0, x, 8, strokeColor=INK, strokeWidth=1))
    return d


def _header(r, prossima, S, width, stagione_label=config.STAGIONE_LABEL):
    meta = f"report del {date.today().strftime('%d/%m/%Y')}"
    if prossima:
        meta = (f"{prossima['giornata']}ª giornata · {prossima['data'][8:10]}/{prossima['data'][5:7]} "
                f"{prossima['ora'] or ''} · {prossima['casa']} – {prossima['ospite']}")
        pv = prossima.get("previsione")
        if pv:
            p_team = pv["prob_casa"] if prossima["casa"] == r.squadra else 1 - pv["prob_casa"]
            meta += f" · vittoria {r.squadra.split()[-1]} {100 * p_team:.0f}%"
    return ST.Intestazione(width, 12 * mm, 12 * mm,
                           f"Scouting report · {r.campionato} {stagione_label}", r.squadra,
                           chips=[r.record, f"{r.posizione}° posto"] if r.posizione else [r.record],
                           meta=meta, marchio=config.BRAND)


def build_pdf(ctx: Contesto, squadra_id: int, mia: int | None = None,
              giochi: list[dict] | None = None, note: list[dict] | None = None,
              foto: bool = True, situazioni: list[list[str]] | None = None) -> bytes:
    """Report prepartita su squadra_id. Si apre con la visione di squadra (una pagina da
    spogliatoio) e lo scouting breve dei giocatori di rotazione (con le foto del sito se foto è
    True), poi il piano partita: con mia (la squadra dello staff) probabilità, chiavi per
    vincere e consigli; senza, i consigli ricavati dai dati. Seguono tutte le sezioni della
    pagina Scouting. Con giochi (disegnati sulla lavagna) aggiunge i suoi giochi fase per fase;
    con note quelle dello staff; con situazioni (righe di situazioni.righe_report) le situazioni del loro
    attacco segnalate dallo staff sul video."""
    from . import scheda_giocatori as SG
    from . import sintesi as SI
    _fonts()
    S = _styles()
    r = scouting.build_report(ctx.conn, squadra_id, ctx.stagione)
    prof = ctx.profile.set_index("squadra_id")
    pf = prof.loc[squadra_id]
    camp = pf["campionato_id"]
    lega = ctx.profile[ctx.profile["campionato_id"] == camp]
    buf = io.BytesIO()
    W = A4[0] - 24 * mm
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=14 * mm,
                            title=f"Scouting {r.squadra}", author=config.BRAND)
    prossima = ctx.next_game(squadra_id)
    giocatori = SG.schede(ctx, squadra_id, foto=foto)
    # i capitoli del report, nell'ordine: la prima pagina li elenca
    capitoli = (["La squadra"] + (["I giocatori"] if giocatori else []) + ["Il piano partita", "I numeri"]
                + (["I giochi"] if giochi else []))
    cap = Capitoli(capitoli, W)
    el = [_header(r, prossima, S, W, config.STAGIONI.get(ctx.stagione, ctx.stagione)),
          ST.Sommario(W, capitoli), Spacer(1, 8)]

    # ---- 1. la squadra: la visione di squadra sta sempre in una pagina (si riduce se i testi sono lunghi)
    libera = A4[1] - 26 * mm - sum(x.wrap(W, A4[1])[1] for x in el) - 2
    el.append(KeepInFrame(W, libera, _sintesi(SI.squadra(ctx, squadra_id, mia, r), r, S, W), mode="shrink"))
    # ---- 2. i giocatori
    from . import impatto as I
    try:
        obiettivi = I.obiettivi(ctx, squadra_id)
    except Exception:
        obiettivi = []
    if giocatori:
        el += [PageBreak()] + cap("I giocatori", "Giocatori di rotazione (almeno 10 minuti a partita), in ordine di "
                                  "minuti, con gli obiettivi per limitarne l'impatto.") \
            + _schede(giocatori, r.squadra, S, W, obiettivi)
    # ---- 3. il piano partita
    el += [PageBreak()] + cap("Il piano partita", "I numeri chiave, come affrontarli in difesa e in attacco, "
                              "le chiavi per vincere.")

    el.append(_kpis([
        ("Net rating", _fmt(pf["net_rtg"], signed=True), f"ORtg {_fmt(pf['ortg'])} · "
                                                         f"DRtg {_fmt(pf['drtg'])}"),
        ("Ritmo", _fmt(pf["pace"]), "possessi per 40'"),
        ("Punto a punto", str(pf["record_pp"]), "margine fino a 5"),
        ("Fortuna", _fmt(pf["fortuna"], signed=True), f"vittorie attese {_fmt(pf['vinte_attese'])}"),
        ("Panchina", f"{_fmt(pf['quota_punti_panchina'], 0)}%", "dei punti"),
        ("Top 2", f"{_fmt(pf['quota_top2'], 0)}%", "dei punti"),
    ], S, W))

    frasi = X.frase_squadra(lega, squadra_id)
    if frasi:
        testo = frasi[0] if len(frasi) == 1 else ", ".join(frasi[:-1]) + " e " + frasi[-1]
        el.append(Paragraph(f"<b>In una frase</b> · {testo[0].upper() + testo[1:]}.", S["body"]))

    piano, dettaglio = _piano(ctx, squadra_id, mia, S, W)
    el += piano
    if dettaglio:
        el += [PageBreak()] + dettaglio

    # ---- 4. i numeri: le tabelle per approfondire
    el += [PageBreak()] + cap("I numeri", "Punti di forza e deboli, Four Factors, giocatori, tiro, finali, "
                              "quintetti, origine dei punti, risultati e profilo completo.")

    def lista(items, colore):
        if not items:
            return [Paragraph("Nessuno marcato (servono più partite).", S["small"])]
        return [Paragraph(f'<font color="{colore}"><b>•</b></font>&nbsp;&nbsp;{x}', S["body"]) for x in items]
    fd = Table([[Paragraph("Punti di forza", S["h2"]), Paragraph("Punti deboli", S["h2"])],
                [lista(r.punti_forza, "#2a78d6"), lista(r.punti_deboli, "#d95926")]],
               colWidths=[W / 2, W / 2])
    fd.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
    el += [fd]

    ff = r.profilo[r.profilo["Metrica"].isin([
        "eFG% in attacco", "Palle perse % in attacco", "Rimbalzi offensivi %",
        "Liberi segnati / tiri dal campo", "eFG% concessa", "Palle perse forzate %",
        "Rimbalzi difensivi %", "Liberi concessi / tiri avversari"])]
    q = r.periodi
    qrows = [["Periodo", "Fatti", "Subiti", "Diff"]] + [
        [x.Periodo, _fmt(x.Fatti), _fmt(x.Subiti), _fmt(x.Diff, signed=True)]
        for x in q.itertuples()]
    blocco = Table([[
        [Paragraph("Four Factors", S["h2"]),
         _table(_bar_rows(ff, 22 * mm), [46 * mm, 24 * mm, 24 * mm, 12 * mm, 22 * mm])],
        [Paragraph("Quarto per quarto", S["h2"]),
         _table(qrows, [16 * mm, 14 * mm, 14 * mm, 14 * mm]),
         Spacer(1, 4),
         Paragraph("Barra blu = squadra, linea = media del campionato. Diff = punti medi "
                   "fatti − subiti nel periodo.", S["small"])]]],
        colWidths=[W * 0.66, W * 0.34])
    blocco.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
    el.append(blocco)

    # Giocatori
    pl = ctx.players[ctx.players["squadra_id"] == squadra_id].sort_values(
        "minuti", ascending=False).head(12)
    has_pm = "plus_minus" in pl.columns and pl["plus_minus"].notna().any()
    head = ["Giocatore", "PG", "Min", "Pt", "Rimb", "Ass", "Perse", "3PM-A", "TL%", "TS%",
            "USG%", "GmSc"] + (["+/-", "On-Off"] if has_pm else [])
    rows = [head]
    for p in pl.itertuples():
        row = [p.giocatore, str(p.partite), _fmt(p.minuti_pg), _fmt(p.punti_pg),
               _fmt(p.rimb_tot_pg), _fmt(p.assist_pg), _fmt(p.perse_pg),
               f"{_fmt(p.t3m_pg)}-{_fmt(p.t3a_pg)}", _fmt(p.tl_pct, 0), _fmt(p.ts_pct),
               _fmt(p.usg_pct), _fmt(p.game_score_pg)]
        if has_pm:
            row += [_fmt(p.plus_minus, 0, signed=True), _fmt(p.on_off, signed=True)]
        rows.append(row)
    widths = [38 * mm] + [((W - 38 * mm) / (len(head) - 1))] * (len(head) - 1)
    el += [Paragraph("Giocatori", S["h2"]), _table(rows, widths)]
    if has_pm:
        el.append(Paragraph("+/- e On-Off (Net rating con il giocatore in campo meno fuori) "
                            "calcolati dalle partite con quintetti verificati.", S["small"]))

    sh = ctx.shots
    if sh is not None and not sh.empty and squadra_id in set(sh["squadra_id"]):
        s = sh[sh["squadra_id"] == squadra_id].sort_values("tiri", ascending=False).head(10)
        zone = s["tiri2_zona"].sum() > 0
        head = ["Giocatore", "Tiri", "Da 3", "3P%"] + (
            ["In area", "Area %", "Media dist.", "Media %"] if zone else []) + ["Schiacciate"]
        rows = [head]
        for x in s.itertuples():
            row = [x.giocatore, str(int(x.tiri)), str(int(x.tre_t)), _fmt(x.tre_pct, 0)]
            if zone:
                row += [str(int(x.area_t)), _fmt(x.area_pct, 0), str(int(x.media_t)),
                        _fmt(x.media_pct, 0)]
            rows.append(row + [str(int(x.schiacciate_r))])
        el += [Paragraph("Profilo di tiro", S["h2"]),
               _table(rows, [44 * mm] + [(W - 44 * mm) / (len(head) - 1)] * (len(head) - 1))]

    f = ctx.fouls
    if f is not None and not f.empty:
        mine = f[(f["squadra_id"] == squadra_id) & (f["partite_problemi"] > 0)].sort_values(
            "partite_problemi", ascending=False).head(6)
        if not mine.empty:
            rows = [["Giocatore", "Partite con problemi", "Uscito per 5 falli", "Falli totali"]]
            rows += [[x.giocatore, str(int(x.partite_problemi)), str(int(x.uscite_5_falli)),
                      str(int(x.falli))] for x in mine.itertuples()]
            el += [Paragraph("Problemi di falli · 2+ nel 1° quarto o 3+ all'intervallo", S["h2"]),
                   _table(rows, [60 * mm] + [(W - 60 * mm) / 3] * 3)]

    # ---- 3. come gioca: finali, quintetti, punti
    el.append(Paragraph("Finali punto a punto · ultimi 5' con scarto entro 5", S["h2"]))
    ct = ctx.clutch_teams
    cp = ctx.clutch_players
    if ct is not None and not ct.empty and squadra_id in set(ct["squadra_id"]):
        c = ct.set_index("squadra_id").loc[squadra_id]
        el.append(Paragraph(f"Partite con finale punto a punto: {int(c['partite_clutch'])} · "
                            f"record {c['record_clutch']} · punti nei finali "
                            f"{int(c['punti_fatti'])}-{int(c['punti_subiti'])}", S["body"]))
        mine = cp[cp["squadra_id"] == squadra_id].head(6)
        if not mine.empty:
            rows = [["Giocatore", "Punti", "Tiri", "% campo", "TL", "Perse", "Quota tiri"]]
            for x in mine.itertuples():
                rows.append([x.giocatore, str(int(x.punti)), f"{int(x.fgm)}/{int(x.fga)}",
                             _fmt(x.fg_pct, 0), f"{int(x.ftm)}/{int(x.fta)}", str(int(x.perse)),
                             f"{_fmt(x.quota_tiri, 0)}%"])
            el.append(_table(rows, [50 * mm] + [(W - 50 * mm) / 6] * 6))
    else:
        el.append(Paragraph("Nessun finale punto a punto finora (o cronaca non disponibile).",
                            S["small"]))

    left, right = [], []
    a = ctx.assists
    if a is not None and not a.empty:
        mine = a[a["squadra_id"] == squadra_id].head(8)
        rows = [["Passa", "Segna", "Canestri", "Punti"]] + [
            [x.da, x.a, str(int(x.canestri)), str(int(x.punti))] for x in mine.itertuples()]
        left = [Paragraph("Chi serve chi", S["h2"]),
                _table(rows, [30 * mm, 30 * mm, 14 * mm, 12 * mm])]
    lu = ctx.lineups
    if lu is not None and not lu.empty:
        mine = lu[lu["squadra_id"] == squadra_id].head(6)
        rows = [["Quintetto", "Min", "+/-", "Net"]] + [
            [Paragraph(x.giocatori, S["cell"]), _fmt(x.minuti), _fmt(x.plus_minus, 0, True),
             _fmt(x.net_rtg, signed=True)] for x in mine.itertuples()]
        right = [Paragraph("Quintetti più usati", S["h2"]),
                 _table(rows, [60 * mm, 12 * mm, 10 * mm, 12 * mm])]
    if left or right:
        t = Table([[left or "", right or ""]], colWidths=[W * 0.47, W * 0.53])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
        el.append(t)

    from . import miglioramento as M
    migliori, peggiori, soglia = M.quintetti_estremi(ctx.lineups, squadra_id)
    if not migliori.empty or not peggiori.empty:
        el.append(Paragraph(f"Quintetti migliori e peggiori · almeno {_fmt(soglia, 0)} minuti "
                            "insieme", S["h2"]))
        for df, testo in ((migliori, "Migliori: da limitare con i cambi"),
                          (peggiori, "Peggiori: da cercare in partita")):
            if df.empty:
                continue
            rows = [[testo, "Min", "+/-", "ORtg", "DRtg", "Net"]] + [
                [Paragraph(x.giocatori, S["cell"]), _fmt(x.minuti, 0), _fmt(x.plus_minus, 0, True),
                 _fmt(x.ortg), _fmt(x.drtg), _fmt(x.net_rtg, signed=True)]
                for x in df.itertuples()]
            el.append(_table(rows, [W - 70 * mm] + [14 * mm] * 5))

    oc = ctx.origini_concesse
    if oc is not None and not oc.empty and squadra_id in set(oc["squadra_id"]) and \
            "punti_da_perse_pg" in prof.columns:
        o = oc.set_index("squadra_id").loc[squadra_id]
        lega_oc = oc[oc["campionato_id"] == camp]
        rows = [["Origine", "Fatti", "Media", "Concessi", "Media"]]
        for lab, fc, cc in (("Da palle perse", "punti_da_perse_pg", "concessi_da_perse_pg"),
                            ("Seconde occasioni", "punti_seconda_occasione_pg",
                             "concessi_seconda_occasione_pg"),
                            ("Contropiede (stima)", "punti_contropiede_pg",
                             "concessi_contropiede_pg")):
            rows.append([lab, _fmt(pf[fc]), _fmt(lega[fc].mean()), _fmt(o[cc]),
                         _fmt(lega_oc[cc].mean())])
        el += [Paragraph("Origine dei punti fatti e concessi · a partita", S["h2"]),
               _table(rows, [60 * mm] + [(W - 60 * mm) / 4] * 4)]

    righe = [["Voce", "Squadra", "Media campionato"]]

    def voce(label, col, d=1, suffix=""):
        if col in prof.columns and pd.notna(pf.get(col)):
            righe.append([label, _fmt(pf[col], d) + suffix, _fmt(lega[col].mean(), d) + suffix])

    voce("Break da 8-0 piazzati (a partita)", "break_fatti_pg", 2)
    voce("Break da 8-0 subiti (a partita)", "break_subiti_pg", 2)
    voce("Periodi in cui va in bonus falli (%)", "quota_periodi_bonus", 0, "%")
    voce("Minuto medio del 5° fallo di squadra", "minuto_medio_bonus")
    voce("Differenza punti nei 2' prima di un proprio timeout", "diff_prima")
    voce("Differenza punti nei 2' dopo un proprio timeout", "diff_dopo")
    voce("% canestri assistiti", "ast_su_canestri", 0, "%")
    voce("% punti da 2", "quota_punti_2", 0, "%")
    voce("% punti da 3", "quota_punti_3", 0, "%")
    voce("% punti dai liberi", "quota_punti_tl", 0, "%")
    voce("% punti dalla panchina", "quota_punti_panchina", 0, "%")
    if len(righe) > 1:
        el += [Paragraph("Come fa punti · parziali, falli e timeout", S["h2"]),
               _table(righe, [100 * mm, 30 * mm, 40 * mm])]

    el += _approfondimenti(ctx, squadra_id, prossima, S, W)

    # ---- 4. risultati e profilo completo
    ct_ = r.casa_trasferta
    if ct_ is not None and not ct_.empty:
        el += [Paragraph("Casa e trasferta", S["h2"]),
               _table([list(ct_.columns)] + [[_fmt(v, 1) if isinstance(v, float) else str(v)
                                              for v in row] for row in ct_.values],
                      [W / len(ct_.columns)] * len(ct_.columns))]
    el += [Paragraph("Ultime partite", S["h2"]),
           _table([list(r.ultime.columns)] + [[_fmt(v, 1) if isinstance(v, float) else str(v)
                                               for v in row] for row in r.ultime.values],
                  [18 * mm, 10 * mm, 50 * mm, 18 * mm, 22 * mm, 14 * mm, 14 * mm, 14 * mm,
                   26 * mm], align_left=(2, 3, 8))]
    prof_c = scouting.profilo_leggibile(r.profilo)
    rows = [["Metrica", "Valore", "Media campionato", "Posizione"]] + prof_c.values.tolist()
    el += [Paragraph("Profilo completo · posizione nel campionato", S["h2"]),
           _table(rows, [80 * mm] + [(W - 80 * mm) / 3] * 3)]

    al = ctx.alerts
    if al is not None and not al.empty:
        mine = al[al["squadra_id"] == squadra_id]
        if not mine.empty:
            el.append(Paragraph("Avvisi", S["h2"]))
            for x in mine.itertuples():
                chi = f"<b>{x.giocatore}</b>: " if isinstance(x.giocatore, str) else ""
                el.append(Paragraph(f"• {chi}{x.testo}", S["body"]))
    if situazioni:
        media = pf.get("ortg")
        el += [Paragraph("Situazioni segnalate sul video", S["h2"]),
               Paragraph("Il loro attacco nelle situazioni segnate dallo staff nella lavagna sul video: come è finito "
                         "il possesso secondo la cronaca. Punti ogni 100 situazioni, da confrontare con il loro rating "
                         f"offensivo ({_fmt(media, 1)}). Con meno di 5 situazioni il dato è indicativo.", S["body"]),
               _table([["", "Situazione", "Situazioni", "Punti ogni 100", "Canestri / tiri", "Palle perse"]]
                      + situazioni, [18 * mm, W - 18 * mm - 4 * 26 * mm] + [26 * mm] * 4, align_left=(0, 1))]
    if note:
        el.append(Paragraph("Note dello staff", S["h2"]))
        for n in note:
            el.append(Paragraph(f"• {_esc(n.get('testo', ''))} "
                                f"<font color='#6f6d66'>({_esc(n.get('autore', ''))}, "
                                f"{str(n.get('creata_il', ''))[:10]})</font>", S["body"]))

    if giochi:
        el += [PageBreak()] + cap("I giochi", "Disegnati dallo staff sulla lavagna, fase per fase.") \
            + L.flowables(giochi, S, W, f"Giochi di {r.squadra} · disegnati dallo staff, fase per fase")[1:]

    footer = ST.piede(f"Scouting · {r.squadra}")
    doc.build(unisci_titoli(el, W), onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


VERDE_FORTE = colors.HexColor("#2a78d6")      # punto di forza (stesso blu dei punti di forza)
DEBOLE = colors.HexColor("#d95926")


def _semaforo(profilo: pd.DataFrame, S, W, riga=None):
    """Otto voci chiave con la posizione in campionato: tessere con barra della posizione."""
    from . import sintesi as SI
    w = W / 4 - 4
    celle = [ST.Tessera(w, v, _fmt(v["valore"])) for v in SI.semaforo(profilo, riga)]
    if not celle:
        return Spacer(1, 1)
    righe = [celle[i:i + 4] + [""] * (4 - len(celle[i:i + 4])) for i in range(0, len(celle), 4)]
    g = Table(righe, colWidths=[W / 4] * 4)
    g.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return g


def _carta(contenuto, w, bordo=None, sfondo=None, pad=8):
    """Riquadro arrotondato: carta chiara o, se sfondo è l'inchiostro, scura. bordo resta per
    compatibilità: nello stile editoriale i riquadri non hanno filetti colorati."""
    sfondo = ST.SUPERFICIE if sfondo is None or sfondo == colors.white else sfondo
    t = Table([[contenuto]], colWidths=[w], cornerRadii=[6, 6, 6, 6])
    stile = [("BACKGROUND", (0, 0), (-1, -1), sfondo), ("LEFTPADDING", (0, 0), (-1, -1), pad),
             ("RIGHTPADDING", (0, 0), (-1, -1), pad), ("TOPPADDING", (0, 0), (-1, -1), pad - 1),
             ("BOTTOMPADDING", (0, 0), (-1, -1), pad - 1), ("VALIGN", (0, 0), (-1, -1), "TOP")]
    t.setStyle(TableStyle(stile))
    return t


def _sintesi(s: dict, r, S, W) -> list:
    """Prima pagina, visione di squadra: in 30 secondi, come stanno in campionato, come
    difendere e attaccare, ritmo e momenti, le tre cose da ricordare."""
    titolo = ParagraphStyle("tmd", parent=S["h2"], fontSize=13, leading=15, textColor=ARANCIO,
                            spaceBefore=0, spaceAfter=2)
    sez = ParagraphStyle("smd", parent=S["h2"], fontSize=13, leading=15, textColor=NAVY,
                         spaceBefore=8, spaceAfter=4)
    grande = ParagraphStyle("grande", parent=S["body"], fontSize=10.5, leading=14)
    voce = ParagraphStyle("voce", parent=S["body"], fontSize=8.6, leading=11.2, spaceAfter=4)
    el = [_carta([Paragraph("La squadra in 30 secondi", titolo), Paragraph(_esc(s.get("sintesi", "")), grande)],
                 W - 4, pad=10),
          Paragraph("Come stanno in campionato", sez), _semaforo(r.profilo, S, W, s.get("riga"))]

    def colonna(titolo_c, voci, colore, w):
        st_t = ParagraphStyle("ct", parent=S["h3"], fontSize=11, leading=13, textColor=colore,
                              spaceBefore=0, spaceAfter=4)
        corpo = [Paragraph(titolo_c, st_t)]
        corpo += [Paragraph(_esc(v), voce) for v in voci] or [Paragraph("Nessuna indicazione marcata.", S["small"])]
        return _carta(corpo, w, pad=9)
    w3 = W / 3 - 4
    tre = Table([[colonna("In difesa · contro il loro attacco", s.get("in_difesa", []), BLU, w3),
                  colonna("In attacco · contro la loro difesa", s.get("in_attacco", []), ARANCIO, w3),
                  colonna("Ritmo, momenti e finali", s.get("ritmo", []), NAVY, w3)]],
                colWidths=[W / 3] * 3)
    tre.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 2)]))
    el += [Spacer(1, 6), tre]
    if s.get("da_ricordare"):
        num = ParagraphStyle("num", parent=S["h1"], fontSize=24, leading=26, textColor=ARANCIO)
        testo = ParagraphStyle("ric", parent=S["body"], fontName="Sans-Semi", fontSize=10,
                               leading=13, textColor=colors.white)
        voci = s["da_ricordare"][:3]
        celle = [_carta([Paragraph(f"<i>{i}</i>", num), Paragraph(_esc(x), testo)], W / 3 - 4,
                        sfondo=NAVY, pad=10) for i, x in enumerate(voci, start=1)]
        celle += [""] * (3 - len(celle))
        box = Table([celle], colWidths=[W / 3] * 3)
        box.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 2)]))
        el += [Paragraph("Da ricordare", sez), box]
    if s.get("attenzione"):
        el += [Spacer(1, 4), Paragraph(f"<b>Attenzione</b> · {_esc(s['attenzione'])}", S["small"])]
    return el


def _foto(dati: bytes | None, nome: str, w, h):
    """Foto del giocatore o, se manca, un riquadro con le iniziali."""
    if dati:
        try:
            from reportlab.lib.utils import ImageReader
            ImageReader(io.BytesIO(dati)).getSize()
            img = Image(io.BytesIO(dati), w, h, kind="proportional")
            return img
        except Exception:
            pass
    from reportlab.graphics.shapes import Drawing, Rect, String
    iniziali = "".join(x[0] for x in nome.split()[:2]).upper()
    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, fillColor=colors.HexColor("#f0eee6"), strokeColor=None))
    d.add(String(w / 2, h / 2 - 6, iniziali, fontName="Serif", fontSize=18, fillColor=GRIGIO,
                 textAnchor="middle"))
    return d


def _scheda(g: dict, S, w):
    """Scheda di un giocatore: foto con maglia, anagrafica, numeri, cosa fa meglio e peggio."""
    nome = ParagraphStyle("gn", parent=S["h3"], fontSize=12.5, leading=14, spaceBefore=0, spaceAfter=0,
                          textColor=NAVY)
    voce = ParagraphStyle("gv", parent=S["body"], fontSize=8, leading=10.3, leftIndent=8, firstLineIndent=-8)
    meta = [x for x in (g.get("ruolo"), f"{g['altezza']} cm" if g.get("altezza") else None,
                        f"{g['eta']} anni" if g.get("eta") else None, g.get("nazionalita")) if x]
    wd = w - 27 * mm - 16
    numeri = Table([[Paragraph(k, S["kpi_l"]) for k, _ in g["numeri"]],
                    [Paragraph(v, ParagraphStyle("nv", parent=S["kpi_v"], fontSize=14, leading=15, textColor=NAVY))
                     for _, v in g["numeri"]]], colWidths=[wd / len(g["numeri"])] * len(g["numeri"]))
    numeri.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    destra = [Paragraph(_esc(g["nome"]), nome), Paragraph(_esc(" · ".join(map(str, meta))) or "&nbsp;", S["small"]),
              Spacer(1, 3), numeri, Paragraph(_esc(g["tiro"]), S["small"]), Spacer(1, 3)]
    destra += [Paragraph(f'<font color="#2a78d6"><b>+</b></font>&nbsp;&nbsp;{_esc(c)}', voce) for c in g["forza"]]
    destra += [Paragraph(f'<font color="#d95926"><b>−</b></font>&nbsp;&nbsp;{_esc(c)}', voce) for c in g["deboli"]]
    if g.get("obiettivo"):
        destra.append(Paragraph(f'<font color="#141413"><b>Obiettivo</b></font> · {_esc(g["obiettivo"]["obiettivo"])}',
                                voce))
    interno = Table([[ST.FotoMaglia(g.get("foto"), g["nome"], g.get("maglia")), destra]],
                    colWidths=[27 * mm, wd])
    interno.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return _carta(interno, w, pad=8)


def _obiettivi_singoli(obiettivi: list[dict], S, W, titolo="Obiettivi sui singoli · per limitarne l'impatto") -> list:
    """Tabella degli obiettivi sui giocatori, con quanto valgono e perché."""
    from . import impatto as I
    if not obiettivi:
        return []
    rows = [["Giocatore", "Obiettivo", "Vale", "Perché"]]
    for o in obiettivi:
        rows.append([Paragraph(f"<b>{_esc(o['giocatore'])}</b>", S["cell"]), Paragraph(_esc(o["obiettivo"]), S["cell"]),
                     Paragraph(_esc(I.testo_vale(o)), S["cell"]), Paragraph(_esc(o["perche"]), S["cell"])])
    t = _table(rows, [32 * mm, 36 * mm, 28 * mm, W - 4 - 16 - 96 * mm], align_left=(1, 2, 3))
    return [_carta([Paragraph(titolo, ParagraphStyle("ost", parent=S["h3"], textColor=NAVY, spaceBefore=0)), t,
                    Paragraph("Margine: punti di differenza nel risultato. Dai dati delle sue partite (questa stagione e "
                              "la precedente) rispetto a quanto la sua squadra rende di solito; con poche partite si usa la "
                              "stima generale del campionato.", S["small"])], W - 4, bordo=NAVY, pad=8), Spacer(1, 6)]


def _schede(giocatori: list[dict], squadra: str, S, W, obiettivi: list[dict] | None = None) -> list:
    el = [Paragraph("<font color='#2a78d6'><b>+</b></font> cosa fa meglio, "
                    "<font color='#d95926'><b>−</b></font> cosa fa peggio in modo evidente, sempre "
                    "rispetto ai giocatori di rotazione del campionato.", S["small"]), Spacer(1, 5)]
    el += _obiettivi_singoli(obiettivi or [], S, W)
    per_g = {o["giocatore_id"]: o for o in obiettivi or []}
    giocatori = [dict(g, obiettivo=per_g.get(g["giocatore_id"])) for g in giocatori]
    w = W / 2 - 4
    for i in range(0, len(giocatori), 2):
        coppia = [_scheda(g, S, w) for g in giocatori[i:i + 2]] + [""] * (2 - len(giocatori[i:i + 2]))
        t = Table([coppia], colWidths=[W / 2, W / 2])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        el.append(t)
    return el


def build_sviluppo(ctx: Contesto, squadra_id: int, foto: bool = True) -> bytes:
    """Report sullo sviluppo dei giocatori della propria squadra: priorità di lavoro, poi per
    ogni giocatore cosa fa bene, cosa fa male e le aree di miglioramento con l'obiettivo."""
    from . import sviluppo as SV
    _fonts()
    S = _styles()
    nome = ctx.nomi_squadre.get(squadra_id, str(squadra_id))
    giocatori = SV.squadra(ctx, squadra_id, foto=foto)
    buf = io.BytesIO()
    W = A4[0] - 24 * mm
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                            bottomMargin=14 * mm, title=f"Sviluppo dei giocatori · {nome}", author=config.BRAND)
    el = [ST.Intestazione(W, 12 * mm, 12 * mm,
                          f"Sviluppo dei giocatori · {config.STAGIONI.get(ctx.stagione, ctx.stagione)}", nome,
                          meta=f"report del {date.today().strftime('%d/%m/%Y')}", marchio=config.BRAND),
          Paragraph("Ogni giocatore è confrontato con i giocatori di rotazione del campionato dello stesso "
                    "ruolo (esterni, ali, lunghi). <b>Area di miglioramento</b>: una voce in cui è tra i "
                    "più bassi del ruolo; l'<b>obiettivo</b> è il valore normale del ruolo (la mediana) e, "
                    "quando si può stimare, quanti punti a partita vale raggiungerlo. Rimbalzi, assist, recuperi e falli "
                    "sono a partita con i minuti del giocatore; <b>azione</b> = un tiro, una coppia di liberi o una "
                    "palla persa; <b>punti per tiro</b> = punti segnati per ogni tiro tentato, liberi compresi.", S["small"])]
    from . import impatto as I
    try:
        prest = I.obiettivi(ctx, squadra_id, n=6, avversaria=False)
    except Exception:
        prest = []
    el += sviluppo_flowables(giocatori, S, W, prestazioni=prest)

    pagina = ST.piede(f"Sviluppo dei giocatori · {nome}")
    doc.build(unisci_titoli(el, W), onFirstPage=pagina, onLaterPages=pagina)
    return buf.getvalue()


def sviluppo_flowables(giocatori: list[dict], S, W, titolo: bool = False, sfondo=colors.white,
                       prestazioni: list[dict] | None = None) -> list:
    """Tabella delle priorità di lavoro e schede di sviluppo (tre per pagina)."""
    sez = ParagraphStyle("svs2", parent=S["h2"], fontSize=13, leading=15, textColor=NAVY, spaceBefore=6,
                         spaceAfter=4)
    el = []
    if titolo:
        el += [Paragraph("Sviluppo dei giocatori", sez),
               Paragraph("Ogni giocatore è confrontato con i giocatori di rotazione del campionato dello stesso "
                         "ruolo (esterni, ali, lunghi); l'obiettivo è il valore normale del ruolo. Rimbalzi, "
                         "assist, recuperi e falli sono a partita con i minuti del giocatore; azione = un tiro, "
                         "una coppia di liberi o una palla persa.", S["small"])]
    if not giocatori:
        return el + [Paragraph("Nessun giocatore con almeno 5 minuti a partita.", S["body"])]
    righe = [["Giocatore", "Min", "Priorità di lavoro", "Ora › obiettivo", "Punti in gioco"]]
    for g in giocatori:
        a = g["aree"][0] if g["aree"] else None
        righe.append([g["nome"], g["numeri"][0][1], Paragraph(_esc(a["voce"]) if a else "–", S["cell"]),
                      Paragraph(_esc(f"{a['valore']} › {a['obiettivo']}") if a else "–", S["cell"]),
                      _fmt(a["punti_pg"]) if a and pd.notna(a["punti_pg"]) else "–"])
    el += [Paragraph("Priorità di lavoro · la voce su cui lavorare per prima, per ogni giocatore", S["h2"]),
           _table(righe, [42 * mm, 12 * mm, W - 42 * mm - 12 * mm - 52 * mm - 20 * mm, 52 * mm, 20 * mm],
                  align_left=(2, 3)), Spacer(1, 6)]
    el += _obiettivi_singoli(prestazioni or [], S, W, "Le prestazioni che spostano il risultato")
    # le schede scorrono una dopo l'altra (ognuna intera sulla sua pagina), senza pagine mezze vuote
    el.append(Paragraph("Giocatori · cosa fa bene, cosa fa male, dove crescere", S["h2"]))
    for g in giocatori:
        el += [_scheda_sviluppo(g, S, W, sfondo), Spacer(1, 6)]
    return el


def _scheda_sviluppo(g: dict, S, W, sfondo=colors.white):
    """Scheda di sviluppo: foto e numeri, poi cosa fa bene, cosa fa male, aree di miglioramento."""
    nome = ParagraphStyle("sn", parent=S["h3"], fontSize=13, leading=15, spaceBefore=0, spaceAfter=0, textColor=NAVY)
    voce = ParagraphStyle("sv", parent=S["body"], fontSize=8, leading=10.3, leftIndent=8, firstLineIndent=-8)
    tit = lambda t, c: Paragraph(t, ParagraphStyle("st", parent=S["h3"], fontSize=9.5, leading=11, textColor=c,
                                                   spaceBefore=0, spaceAfter=3))  # noqa: E731
    meta = [x for x in (g.get("ruolo"), f"{g['altezza']} cm" if g.get("altezza") else None,
                        f"{g['eta']} anni" if g.get("eta") else None, g.get("nazionalita"),
                        f"{g['partite']} partite") if x]
    wd = W - 27 * mm - 16
    numeri = Table([[Paragraph(k, S["kpi_l"]) for k, _ in g["numeri"]],
                    [Paragraph(v, ParagraphStyle("nv2", parent=S["kpi_v"], fontSize=14, leading=15, textColor=NAVY))
                     for _, v in g["numeri"]]], colWidths=[min(22 * mm, wd / len(g["numeri"]))] * len(g["numeri"]),
                   hAlign="LEFT")
    numeri.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    an = g.get("andamento")
    trend = ""
    if an:
        (pu, pm), (mi, mm_) = an["punti"], an["minuti"]
        trend = (f"Ultime {an['ultime']} partite: {_fmt(pu)} punti in {_fmt(mi)} minuti (stagione {_fmt(pm)} in "
                 f"{_fmt(mm_)}) · <b>{an['tendenza']}</b>")
    testa = [Paragraph(_esc(g["nome"]), nome), Paragraph(_esc(" · ".join(map(str, meta))), S["small"]), Spacer(1, 3),
             numeri, Paragraph(_esc(g["tiro"]), S["small"])] + ([Paragraph(trend, S["small"])] if trend else [])
    cw = (W - 16) / 3
    bene = [tit("Cosa fa bene", BLU)] + [Paragraph(f'<font color="#2a78d6"><b>+</b></font>&nbsp;&nbsp;{_esc(x)}', voce)
                                        for x in g["forza"]]
    male = [tit("Cosa fa male", ROSSO)] + ([Paragraph(f'<font color="#d95926"><b>−</b></font>&nbsp;&nbsp;{_esc(x)}', voce)
                                           for x in g["deboli"]] or
                                          [Paragraph("Nessun difetto evidente rispetto al campionato.", S["small"])])
    aree = [tit("Aree di miglioramento", NAVY)]
    for a in g["aree"]:
        punti = f" · circa {_fmt(a['punti_pg'])} punti a partita" if pd.notna(a["punti_pg"]) and a["punti_pg"] >= 0.3 \
            else ""
        aree += [Paragraph(f"<b>{_esc(a['voce'])}</b>", voce),
                 Paragraph(f"{a['valore']} › obiettivo <b>{a['obiettivo']}</b>{punti}", S["small"]),
                 ST.Obiettivo(cw - 16, a["da"], a["a"], a["alto"]), Spacer(1, 3)]
    if len(aree) == 1:
        aree.append(Paragraph("Nessuna voce sotto il livello del ruolo.", S["small"]))
    tre = Table([[bene, male, aree]], colWidths=[cw] * 3)
    tre.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (0, -1), 0),
                             ("LEFTPADDING", (1, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                             ("LINEBEFORE", (1, 0), (-1, 0), 0.5, ST.LINEA_2)]))
    alto_ = Table([[ST.FotoMaglia(g.get("foto"), g["nome"], g.get("maglia")), testa]], colWidths=[27 * mm, wd])
    alto_.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return KeepTogether(_carta([alto_, tre], W - 4, sfondo=sfondo, pad=9))


def unisci_titoli(el: list, W: float = A4[0] - 24 * mm) -> list:
    """Titoli di sezione con il filo d'inchiostro sopra (pdf_stile.sezione); ogni titolo resta
    sulla stessa pagina del blocco che lo segue."""
    out, i = [], 0
    while i < len(el):
        x = el[i]
        titolo = isinstance(x, Paragraph) and x.style.name in ("h2", "h3")
        if isinstance(x, Paragraph) and x.style.name == "h2":
            x = ST.sezione(x.text, x.style, W)
        if titolo and i + 1 < len(el) and not isinstance(el[i + 1], PageBreak):
            dopo = el[i + 1]
            # un KeepTogether dentro l'altro manda tutto alla pagina dopo: si uniscono i contenuti
            out.append(KeepTogether([x] + (list(dopo._content) if isinstance(dopo, KeepTogether) else [dopo])))
            i += 2
        else:
            out.append(x)
            i += 1
    return out


def _esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_giochi(giochi: list[dict], squadra: str) -> bytes:
    """PDF con i giochi disegnati sulla lavagna (il playbook della squadra), fase per fase."""
    _fonts()
    S = _styles()
    buf = io.BytesIO()
    W = A4[0] - 24 * mm
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=14 * mm,
                            title=f"Giochi {squadra}", author=config.BRAND)
    el = [ST.Intestazione(W, eyebrow="Giochi disegnati dallo staff", titolo=squadra,
                          meta=f"{len(giochi)} giochi · report del {date.today().strftime('%d/%m/%Y')}",
                          marchio=config.BRAND, grande=False),
          Paragraph("Taglio: freccia piena · passaggio: tratteggio · palleggio: zig-zag · blocco: barra finale.",
                    S["small"]), Spacer(1, 4)]
    el += L.flowables(giochi, S, W, "")[1:]

    footer = ST.piede(f"Giochi · {squadra}")
    doc.build(unisci_titoli(el, W), onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


def _consigli(ctx: Contesto, avv: int, mia: int | None, rt, S, W) -> list:
    """Consigli su come affrontare la partita, in quattro gruppi."""
    from . import piano_partita as PP
    gruppi = PP.consigli(ctx, avv, mia, rt)
    el = []
    celle = []
    for g, voci in gruppi.items():
        corpo = [Paragraph(g, S["h3"])]
        corpo += [Paragraph(f'<font color="#ff7a1a">•</font> {v}', S["body"]) for v in voci] \
            or [Paragraph("Nessuna indicazione marcata.", S["small"])]
        celle.append(corpo)
    for k in range(0, len(celle), 2):
        riga = celle[k:k + 2] + [""] * (2 - len(celle[k:k + 2]))
        tab = Table([riga], colWidths=[W / 2, W / 2])
        tab.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 3),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        el.append(tab)
    return el


def _piano(ctx: Contesto, avv: int, mia: int | None, S, W) -> tuple[list, list]:
    """(piano partita, dettaglio delle chiavi). Senza la propria squadra (o in un altro
    campionato) il piano contiene solo i consigli ricavati dai dati dell'avversaria."""
    from . import chiavi as C
    from . import validazione as V
    prof = ctx.profile
    camp = prof.set_index("squadra_id").loc[avv, "campionato_id"]
    lega = prof[prof["campionato_id"] == camp]
    nome_avv = ctx.nomi_squadre.get(avv, str(avv))
    g_avv = int(lega.set_index("squadra_id").loc[avv, "partite"])
    if mia is None or mia == avv or mia not in set(lega["squadra_id"]):
        el = [Paragraph(f"Come affrontare {nome_avv}", S["h2"]),
              Paragraph("Indicazioni ricavate dai dati della squadra rispetto al campionato. "
                        "Con la propria squadra impostata il report aggiunge le probabilità di "
                        "vittoria e le chiavi della partita.", S["small"])]
        return el + _consigli(ctx, avv, None, None, S, W), []
    nome_mia = ctx.nomi_squadre.get(mia, str(mia))
    ng = ctx.next_game(mia)
    casa_mia = ng["casa_id"] == mia if ng and {ng["casa_id"], ng["ospite_id"]} == {mia, avv} \
        else True
    forze, hca = ctx.forze(camp), ctx.hca(camp)
    lv = C.leve(lega, forze, mia, avv, casa_mia, hca)
    rt = C.ritmo(forze, mia, avv, casa_mia, hca)
    m0, _ = C._margine_noi(forze, mia, avv, casa_mia, hca)
    bt = V.carica()
    bt = bt[bt["stagione"] == ctx.stagione] if not bt.empty else bt

    def chiave_giocatori(sid, avversario):
        if bt.empty:
            return pd.DataFrame()
        gc = C.giocatori_chiave(ctx.bg, bt, sid, ctx.nomi_giocatori)
        return C.prob_giocatori(gc[gc["effetto"] >= 0.5], m0, avversario) if not gc.empty \
            else gc
    gc = chiave_giocatori(avv, True)
    comb = C.combinata(lv, gc)
    p0 = lv["prob_ora"].iloc[0]
    top = lv.iloc[0]
    lento, veloce = rt.iloc[0], rt.iloc[-1]
    lento_meglio = lento["prob"] >= veloce["prob"]
    rit = lento if lento_meglio else veloce

    el = [Paragraph(f"Piano partita · {nome_mia} contro {nome_avv}", S["h2"]),
          _kpis([("Probabilità ora", f"{_fmt(p0, 0)}%",
                  f"{nome_mia.split()[-1]} {'in casa' if casa_mia else 'in trasferta'}"),
                 ("Con tutte le chiavi", f"{_fmt(comb['prob_tutte'], 0)}%",
                  f"scenario migliore · {_fmt(comb['prob_tutte'] - p0, 0, signed=True)} punti"),
                 ("Leva principale", top["breve"],
                  f"da sola fino a {_fmt(top['prob_obiettivo'], 0)}%"),
                 ("Ritmo che conviene", "lento" if lento_meglio else "veloce",
                  f"{_fmt(rit['prob'], 0)}% con {_fmt(rit['possessi'], 0)} possessi")], S, W),
          Spacer(1, 4),
          Paragraph("Le chiavi della partita", S["h3"])]
    for i, frase in enumerate(C.sintesi(lv, gc, nome_avv.split()[-1]), start=1):
        el.append(Paragraph(f"<b>{i}.</b> {_virgole(frase)}".replace(" → ", " · "), S["body"]))
    el.append(Paragraph(f"<b>Tutte insieme:</b> {_virgole(C.frase_combinata(comb))}.",
                        S["body"]))
    if min(g_avv, int(lega.set_index("squadra_id").loc[mia, "partite"])) < 8:
        el.append(Paragraph("<b>Attenzione</b> · Inizio stagione: con meno di 8 partite i valori sono avvicinati "
                            "alla media del campionato e i consigli vanno confermati.",
                            S["small"]))
    el.append(Spacer(1, 4))
    el += _consigli(ctx, avv, mia, rt, S, W)
    el.append(Paragraph(f"Consigli dal confronto tra i dati di {nome_mia} e di {nome_avv} "
                        "(voci lontane dalla media del campionato). <b>Sfida chiave</b>: un loro "
                        "punto forte contro un vostro punto debole. <b>Occasione</b>: un vostro "
                        "punto forte contro un loro punto debole. <b>Forza contro forza</b>: i "
                        "due punti forti si incontrano. <b>Neutralizzata</b>: un loro punto "
                        "forte dove siete forti anche voi. <b>Da curare</b>: un vostro punto "
                        "debole. Probabilità dal modello di previsione; sono associazioni "
                        "statistiche, non garanzie.", S["small"]))

    # ---- dettaglio
    det = [Paragraph("Le chiavi in dettaglio · Four Factors della partita", S["h2"])]
    rows = [["Fattore", "Lato", "Atteso", "Media", "Obiettivo", "Situazione", "Prob.",
             "Guadagno"]]
    for _, x in lv.iterrows():
        rows.append([x["fattore"], x["lato"], C.leggibile(x, "atteso"), C.leggibile(x, "media"),
                     C.leggibile(x, "obiettivo"), x["situazione"],
                     f"{_fmt(x['prob_obiettivo'], 0)}%", f"{_fmt(x['guadagno'], 1, signed=True)}"])
    det.append(_table(rows, [42 * mm, 16 * mm] + [21 * mm] * 3 + [25 * mm] + [(W - 146 * mm) / 2]
                      * 2, align_left=(1, 5)))
    det.append(Paragraph("Palle perse, rimbalzi offensivi e liberi: numero a partita sui possessi "
                         "e sui tiri attesi nella partita. Il tiro è la percentuale dal campo con "
                         "le triple che valgono 1,5.", S["small"]))
    for _, x in lv.iterrows():
        det.append(Paragraph(f"• {_virgole(C.frase_leva(x, nome_avv.split()[-1]))}", S["small"]))
    det.append(Paragraph(f"Ritmo: con {_fmt(lento['possessi'], 0)} possessi "
                         f"{_fmt(lento['prob'], 0)}%, con {_fmt(veloce['possessi'], 0)} possessi "
                         f"{_fmt(veloce['prob'], 0)}%.", S["small"]))

    blocchi = []
    for sid, titolo in ((avv, f"Quando {nome_avv.split()[-1]} perde"),
                        (mia, f"Quando perdete voi ({nome_mia.split()[-1]})")):
        qp = C.quando_perdono(ctx.bs, sid)
        corpo = [Paragraph(titolo, S["h3"])]
        if qp.empty:
            corpo.append(Paragraph("Servono almeno 3 vittorie e 3 sconfitte.", S["small"]))
        else:
            rr = [["Voce", "Vittorie", "Sconfitte"]]
            for x in qp.head(5).itertuples():
                d = 2 if x.colonna in ("ft_rate", "opp_ft_rate") else 1
                rr.append([x.voce, _fmt(x.vittorie, d), _fmt(x.sconfitte, d)])
            corpo.append(_table(rr, [W / 2 - 40 * mm, 17 * mm, 17 * mm]))
        blocchi.append(corpo)
    tq = Table([blocchi], colWidths=[W / 2, W / 2])
    tq.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
    det.append(tq)

    for sid, avversario in ((avv, True), (mia, False)):
        g = gc if avversario else chiave_giocatori(mia, False)
        nome = nome_avv if avversario else nome_mia
        det.append(Paragraph(
            f"Giocatori chiave di {nome} · " + (
                "quando restano sotto la soglia" if avversario else "quando vanno sopra la "
                                                                   "soglia"), S["h3"]))
        if g.empty:
            det.append(Paragraph("Nessun giocatore con un effetto marcato (servono almeno 4 "
                                 "partite sotto e 4 sopra la soglia).", S["small"]))
            continue
        rows = [["Giocatore", "Soglia", "Sotto/sopra", "Scarto sotto", "Scarto sopra",
                 "Probabilità", "Senza di lui"]]
        for x in g.head(5).itertuples():
            senza = f"{_fmt(x.scarto_assente, 1, signed=True)} ({int(x.partite_assente)})" \
                if pd.notna(x.scarto_assente) else "–"
            rows.append([x.giocatore, f"{'meno di ' if avversario else 'almeno '}"
                                      f"{_fmt(x.soglia, 0)} {x.statistica}",
                         f"{x.partite_sotto}/{x.partite_sopra}",
                         _fmt(x.scarto_sotto, 1, signed=True), _fmt(x.scarto_sopra, 1, signed=True),
                         f"{_fmt(x.prob_scenario, 0)}%", senza])
        det.append(_table(rows, [42 * mm, 34 * mm] + [(W - 76 * mm) / 5] * 5, align_left=(1,)))
    det.append(Paragraph("Scarto: punti in più o in meno rispetto al margine previsto prima della "
                         "partita. Senza di lui: scarto medio nelle partite in cui non ha giocato "
                         "(tra parentesi quante).", S["small"]))
    return el, det


def _virgole(testo: str) -> str:
    return re.sub(r"(?<![\d.])(\d+)\.(\d+)(?![\d.])", r"\1,\2", str(testo))


def _approfondimenti(ctx: Contesto, sid: int, prossima, S, W) -> list:
    """Rotazioni, quintetti per taglia, momenti della partita, riposo e trasferta."""
    el = []
    nomi = ctx.nomi_giocatori
    rot = ctx.rotazioni
    sq = rot["squadre"]
    if not sq.empty and sid in set(sq["squadra_id"]):
        s = sq.set_index("squadra_id").loc[sid]
        gi = rot["giocatori"]
        gi = gi[gi["squadra_id"] == sid].sort_values("secondi", ascending=False).head(10)
        rows = [["Giocatore", "Minuti", "% da titolare", "Entra al minuto", "% negli ultimi 5'"]]
        for x in gi.itertuples():
            rows.append([nomi.get(x.giocatore_id, x.giocatore_id), _fmt(x.minuti_pg),
                         f"{_fmt(x.quota_titolare, 0)}%", _fmt(x.minuto_ingresso),
                         f"{_fmt(x.quota_finale, 0)}%"])
        base = ", ".join(nomi.get(g, g) for g in str(s["quintetto"]).split(","))
        el += [Paragraph("Rotazioni", S["h2"]),
               Paragraph(f"Primo cambio al minuto {_fmt(s['minuto_primo_cambio'])} (mediana) · "
                         f"{_fmt(s['giocatori_rotazione'])} giocatori con almeno 5' · quintetto "
                         f"base ({_fmt(s['quota_quintetto_base'], 0)}% delle partite): {base}.",
                         S["body"]),
               _table(rows, [60 * mm] + [(W - 60 * mm) / 4] * 4)]
    tg = ctx.taglie
    if tg is not None and not tg.empty and sid in set(tg["squadra_id"]):
        t = tg[tg["squadra_id"] == sid]
        rows = [["Quintetto", "% minuti", "Altezza media", "ORtg", "DRtg", "Net rating"]]
        for x in t.itertuples():
            rows.append([str(x.taglia), f"{_fmt(x.quota_minuti, 0)}%", f"{_fmt(x.altezza, 0)} cm",
                         _fmt(x.ortg), _fmt(x.drtg), _fmt(x.net_rtg, signed=True)])
        el += [Paragraph("Quintetti alti e bassi", S["h2"]),
               _table(rows, [40 * mm] + [(W - 40 * mm) / 5] * 5)]
    m = ctx.momenti
    if m is not None and not m.empty and sid in set(m["squadra_id"]):
        rows = [["Momento", "Fatti", "Subiti", "Differenza", "Posizione"]]
        for x in m[m["squadra_id"] == sid].itertuples():
            rows.append([x.etichetta, _fmt(x.fatti_pg), _fmt(x.subiti_pg),
                         _fmt(x.diff_pg, signed=True), f"{x.posizione}° su {x.squadre}"])
        el += [Paragraph("Momenti della partita · punti a partita", S["h2"]),
               _table(rows, [60 * mm] + [(W - 60 * mm) / 4] * 4)]
    if prossima:
        cal = ctx.calendario_fisico
        if cal is not None and not cal.empty:
            casa = cal[cal["casa"] == 1].groupby("squadra_id")["citta_squadra"].agg(
                lambda v: v.value_counts().index[0] if v.notna().any() else None)
            righe = []
            for tid in (prossima["casa_id"], prossima["ospite_id"]):
                info = X.prossima_trasferta(cal[cal["squadra_id"] == tid]["data"].max(),
                                            prossima["data"], casa.get(prossima["casa_id"]),
                                            casa.get(tid), tid == prossima["casa_id"])
                nome = ctx.nomi_squadre.get(tid, str(tid))
                riposo = info["giorni_riposo"]
                righe.append(f"{nome}: {riposo if riposo is not None else '–'} giorni di riposo"
                             + ("" if tid == prossima["casa_id"] else
                                f", trasferta di circa {_fmt(info['km'], 0)} km"))
            el += [Paragraph("Riposo e trasferta per la prossima partita", S["h2"]),
                   Paragraph(" · ".join(righe) + ".", S["body"])]
    return el


def slug(nome: str) -> str:
    import unicodedata
    ascii_ = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_.lower()).strip("_")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Report di scouting in PDF")
    ap.add_argument("squadra", nargs="?", help="nome (anche parziale) della squadra")
    ap.add_argument("--tutte", action="store_true", help="un PDF per ogni squadra")
    ap.add_argument("--out", default=str(config.REPORTS_DIR / "pdf"))
    args = ap.parse_args(argv)
    ctx = open_readonly()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.tutte:
        teams = ctx.bs[["squadra_id", "squadra"]].drop_duplicates().values.tolist()
    else:
        teams = scouting.find_team(ctx.conn, args.squadra or "")
        if len(teams) != 1:
            print("Squadre trovate:", ", ".join(n for _, n in teams) or "nessuna")
            return 1
    for sid, nome in teams:
        path = out / f"scouting_{slug(nome)}.pdf"
        path.write_bytes(build_pdf(ctx, int(sid)))
        print("Scritto", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
