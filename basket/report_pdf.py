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
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

from . import approfondimenti as X
from . import config, scouting
from .contesto import Contesto, open_readonly

FONT_DIR = config.ROOT / "assets" / "fonts"
NAVY = colors.HexColor("#0b1220")
ARANCIO = colors.HexColor("#ff7a1a")
BLU = colors.HexColor("#2a78d6")
ROSSO = colors.HexColor("#d95926")
INK = colors.HexColor("#1a2233")
GRIGIO = colors.HexColor("#6b7489")
RIGA = colors.HexColor("#f3f5f9")
BORDO = colors.HexColor("#dfe3eb")


def _fonts():
    if "Barlow" in pdfmetrics.getRegisteredFontNames():
        return
    for name, file in (("Barlow", "Barlow-Regular.ttf"), ("Barlow-Medium", "Barlow-Medium.ttf"),
                       ("Barlow-SemiBold", "Barlow-SemiBold.ttf"),
                       ("Condensed", "BarlowCondensed-Bold.ttf"),
                       ("Condensed-Semi", "BarlowCondensed-SemiBold.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))


def _styles():
    return {
        "h1": ParagraphStyle("h1", fontName="Condensed", fontSize=26, leading=28,
                             textColor=colors.white),
        "eyebrow": ParagraphStyle("eb", fontName="Barlow-SemiBold", fontSize=8, leading=10,
                                  textColor=ARANCIO),
        "meta": ParagraphStyle("meta", fontName="Barlow", fontSize=9, leading=12,
                               textColor=colors.HexColor("#c9d1e0")),
        "h2": ParagraphStyle("h2", fontName="Condensed", fontSize=14, leading=16,
                             textColor=INK, spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("body", fontName="Barlow", fontSize=8.5, leading=11,
                               textColor=INK, alignment=TA_LEFT),
        "small": ParagraphStyle("small", fontName="Barlow", fontSize=7.5, leading=9.5,
                                textColor=GRIGIO),
        "cell": ParagraphStyle("cell", fontName="Barlow", fontSize=8, leading=9.5, textColor=INK),
        "kpi_l": ParagraphStyle("kl", fontName="Barlow-SemiBold", fontSize=6.5, leading=8,
                                textColor=GRIGIO),
        "kpi_v": ParagraphStyle("kv", fontName="Condensed", fontSize=18, leading=20,
                                textColor=INK),
        "kpi_s": ParagraphStyle("ks", fontName="Barlow", fontSize=6.5, leading=8,
                                textColor=GRIGIO),
    }


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
        ("FONTNAME", (0, 0), (-1, -1), "Barlow"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("ALIGN", (align_right_from, 0), (-1, -1), "RIGHT"),
        ("LINEBELOW", (0, -1), (-1, -1), 0.4, BORDO),
    ] + [("ALIGN", (c, 0), (c, -1), "LEFT") for c in align_left]
    if header:
        style += [("FONTNAME", (0, 0), (-1, 0), "Barlow-SemiBold"),
                  ("FONTSIZE", (0, 0), (-1, 0), 7),
                  ("TEXTCOLOR", (0, 0), (-1, 0), GRIGIO),
                  ("LINEBELOW", (0, 0), (-1, 0), 0.6, INK)]
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), RIGA))
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
    t = Table([[content[0]], [content[1]], [content[2]]])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, BORDO),
                           ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafbfd")),
                           ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                           ("LEFTPADDING", (0, 0), (-1, -1), 6)]))
    return t


def _bar_rows(df, width_bar=38 * mm):
    """Tabella Four Factors con barra squadra vs media."""
    rows = [["Metrica", "Squadra", "Media", "Pos.", ""]]
    for r in df.itertuples():
        rows.append([r.Metrica, _fmt(r.Valore, 2 if "Liberi" in r.Metrica else 1),
                     _fmt(r._3, 2 if "Liberi" in r.Metrica else 1), r.Posizione,
                     _bar(r.Valore, r._3, width_bar)])
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
    righe = [[Paragraph(f"SCOUTING REPORT · {r.campionato.upper()} {stagione_label}",
                        S["eyebrow"])],
             [Paragraph(r.squadra.upper(), S["h1"])],
             [Paragraph(f"Record {r.record} · {r.posizione}° posto · report del "
                        f"{date.today().strftime('%d/%m/%Y')}", S["meta"])]]
    if prossima:
        txt = (f"Prossima partita: {prossima['giornata']}ª giornata, {prossima['data']} "
               f"{prossima['ora'] or ''} · {prossima['casa']} – {prossima['ospite']}")
        pv = prossima.get("previsione")
        if pv:
            p_team = pv["prob_casa"] if prossima["casa"] == r.squadra else 1 - pv["prob_casa"]
            txt += (f" · probabilità di vittoria {r.squadra.split()[-1]}: {100 * p_team:.0f}% "
                    f"(stima {pv['punti_casa']:.0f}-{pv['punti_ospite']:.0f})")
        righe.append([Paragraph(txt, S["meta"])])
    testo = Table(righe, colWidths=[width - 34 * mm])
    testo.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), 1),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    marchio = [Image(str(config.LOGO_DIR / "assist-mark-512.png"), 16 * mm, 16 * mm),
               Paragraph(config.BRAND, ParagraphStyle(
                   "brand", fontName="Condensed", fontSize=11, leading=13, alignment=1,
                   textColor=colors.white, spaceBefore=2))]
    t = Table([[testo, marchio]], colWidths=[width - 34 * mm, 34 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY),
                           ("LEFTPADDING", (0, 0), (0, 0), 12),
                           ("TOPPADDING", (0, 0), (-1, -1), 10),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("ALIGN", (1, 0), (1, 0), "CENTER"),
                           ("LINEBELOW", (0, -1), (-1, -1), 3, ARANCIO)]))
    return t


def build_pdf(ctx: Contesto, squadra_id: int, mia: int | None = None) -> bytes:
    """Report di scouting su squadra_id. Con mia (la squadra dello staff) aggiunge le chiavi
    per vincere la partita contro di lei."""
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
    el = [_header(r, prossima, S, W, config.STAGIONI.get(ctx.stagione, ctx.stagione)),
          Spacer(1, 6)]

    el.append(_kpis([
        ("Net rating", _fmt(pf["net_rtg"], signed=True), f"ORtg {_fmt(pf['ortg'])} · "
                                                         f"DRtg {_fmt(pf['drtg'])}"),
        ("Ritmo", _fmt(pf["pace"]), "possessi per 40'"),
        ("Punto a punto", str(pf["record_pp"]), "margine ≤ 5"),
        ("Fortuna", _fmt(pf["fortuna"], signed=True), f"vittorie attese {_fmt(pf['vinte_attese'])}"),
        ("Panchina", f"{_fmt(pf['quota_punti_panchina'], 0)}%", "dei punti"),
        ("Top 2", f"{_fmt(pf['quota_top2'], 0)}%", "dei punti"),
    ], S, W))

    frasi = X.frase_squadra(lega, squadra_id)
    if frasi:
        testo = frasi[0] if len(frasi) == 1 else ", ".join(frasi[:-1]) + " e " + frasi[-1]
        el.append(Paragraph(f"<b>IN UNA FRASE</b> · {testo[0].upper() + testo[1:]}.", S["body"]))

    # Forza / debolezza
    def lista(items, colore):
        if not items:
            return [Paragraph("Nessuno marcato (servono più partite).", S["small"])]
        return [Paragraph(f'<font color="{colore}">■</font> {x}', S["body"]) for x in items]
    fd = Table([[Paragraph("PUNTI DI FORZA", S["h2"]), Paragraph("PUNTI DEBOLI", S["h2"])],
                [lista(r.punti_forza, "#2a78d6"), lista(r.punti_deboli, "#d95926")]],
               colWidths=[W / 2, W / 2])
    fd.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
    el += [fd]
    if mia is not None and mia != squadra_id:
        el += _chiavi(ctx, squadra_id, mia, S, W)

    ff = r.profilo[r.profilo["Metrica"].isin([
        "eFG% in attacco", "Palle perse % in attacco", "Rimbalzi offensivi %",
        "Liberi segnati / tiri dal campo", "eFG% concessa", "Palle perse forzate %",
        "Rimbalzi difensivi %", "Liberi concessi / tiri avversari"])]
    q = r.periodi
    qrows = [["Periodo", "Fatti", "Subiti", "Diff"]] + [
        [x.Periodo, _fmt(x.Fatti), _fmt(x.Subiti), _fmt(x.Diff, signed=True)]
        for x in q.itertuples()]
    blocco = Table([[
        [Paragraph("FOUR FACTORS", S["h2"]),
         _table(_bar_rows(ff), [46 * mm, 16 * mm, 14 * mm, 12 * mm, 40 * mm])],
        [Paragraph("QUARTO PER QUARTO", S["h2"]),
         _table(qrows, [16 * mm, 14 * mm, 14 * mm, 14 * mm]),
         Spacer(1, 4),
         Paragraph("Barra blu = squadra, linea = media del campionato. Diff = punti medi "
                   "fatti − subiti nel periodo.", S["small"])]]],
        colWidths=[W * 0.66, W * 0.34])
    blocco.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
    el.append(blocco)

    # Giocatori chiave
    pl = ctx.players[ctx.players["squadra_id"] == squadra_id].sort_values(
        "minuti", ascending=False).head(11)
    has_pm = "plus_minus" in pl.columns and pl["plus_minus"].notna().any()
    head = ["Giocatore", "PG", "Min", "Pt", "Rimb", "Ass", "Perse", "3PM-A", "TS%", "USG%",
            "GmSc"] + (["+/-", "On-Off"] if has_pm else [])
    rows = [head]
    for p in pl.itertuples():
        row = [p.giocatore, str(p.partite), _fmt(p.minuti_pg), _fmt(p.punti_pg),
               _fmt(p.rimb_tot_pg), _fmt(p.assist_pg), _fmt(p.perse_pg),
               f"{_fmt(p.t3m_pg)}-{_fmt(p.t3a_pg)}", _fmt(p.ts_pct), _fmt(p.usg_pct),
               _fmt(p.game_score_pg)]
        if has_pm:
            row += [_fmt(p.plus_minus, 0, signed=True), _fmt(p.on_off, signed=True)]
        rows.append(row)
    widths = [40 * mm] + [((W - 40 * mm) / (len(head) - 1))] * (len(head) - 1)
    el += [Paragraph("GIOCATORI CHIAVE", S["h2"]), _table(rows, widths)]
    if has_pm:
        el.append(Paragraph("+/- e On-Off (Net rating con il giocatore in campo meno fuori) "
                            "calcolati dalle partite con quintetti verificati.", S["small"]))

    el.append(PageBreak())
    # Finali punto a punto
    el.append(Paragraph("FINALI PUNTO A PUNTO · ultimi 5' con scarto ≤ 5", S["h2"]))
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

    # Rete degli assist + quintetti
    left, right = [], []
    a = ctx.assists
    if a is not None and not a.empty:
        mine = a[a["squadra_id"] == squadra_id].head(8)
        rows = [["Passa", "Segna", "Canestri", "Punti"]] + [
            [x.da, x.a, str(int(x.canestri)), str(int(x.punti))] for x in mine.itertuples()]
        left = [Paragraph("CHI SERVE CHI", S["h2"]),
                _table(rows, [30 * mm, 30 * mm, 14 * mm, 12 * mm])]
    lu = ctx.lineups
    if lu is not None and not lu.empty:
        mine = lu[lu["squadra_id"] == squadra_id].head(5)
        rows = [["Quintetto", "Min", "+/-", "Net"]] + [
            [Paragraph(x.giocatori, S["cell"]), _fmt(x.minuti), _fmt(x.plus_minus, 0, True),
             _fmt(x.net_rtg, signed=True)] for x in mine.itertuples()]
        right = [Paragraph("QUINTETTI PIÙ USATI", S["h2"]),
                 _table(rows, [60 * mm, 12 * mm, 10 * mm, 12 * mm])]
    if left or right:
        t = Table([[left or "", right or ""]], colWidths=[W * 0.47, W * 0.53])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
        el.append(t)

    # Origine dei punti, parziali, falli, timeout
    righe = [["Voce", "Squadra", "Media campionato"]]

    def voce(label, col, d=1, suffix=""):
        if col in prof.columns and pd.notna(pf.get(col)):
            righe.append([label, _fmt(pf[col], d) + suffix, _fmt(lega[col].mean(), d) + suffix])

    voce("Punti da palle perse avversarie (a partita)", "punti_da_perse_pg")
    voce("Punti da seconde occasioni (a partita)", "punti_seconda_occasione_pg")
    voce("Punti in contropiede (a partita, stima)", "punti_contropiede_pg")
    voce("Break da 8-0 piazzati (a partita)", "break_fatti_pg", 2)
    voce("Break da 8-0 subiti (a partita)", "break_subiti_pg", 2)
    voce("Periodi in cui va in bonus falli (%)", "quota_periodi_bonus", 0, "%")
    voce("Minuto medio del 5° fallo di squadra", "minuto_medio_bonus")
    voce("Differenza punti nei 2' dopo un proprio timeout", "diff_dopo")
    voce("% canestri assistiti", "ast_su_canestri", 0, "%")
    voce("% punti da 3", "quota_punti_3", 0, "%")
    if len(righe) > 1:
        el += [Paragraph("COME FA PUNTI · RITMO PARTITA · FALLI", S["h2"]),
               _table(righe, [100 * mm, 30 * mm, 40 * mm])]

    f = ctx.fouls
    if f is not None and not f.empty:
        mine = f[(f["squadra_id"] == squadra_id) & (f["partite_problemi"] > 0)].sort_values(
            "partite_problemi", ascending=False).head(5)
        if not mine.empty:
            el.append(Paragraph("Problemi di falli (2+ nel 1° quarto o 3+ all'intervallo): " +
                                ", ".join(f"{x.giocatore} {int(x.partite_problemi)} volte"
                                          for x in mine.itertuples()), S["body"]))

    el += _approfondimenti(ctx, squadra_id, prossima, S, W)

    el += [Paragraph("ULTIME PARTITE", S["h2"]),
           _table([list(r.ultime.columns)] + [[_fmt(v, 1) if isinstance(v, float) else str(v)
                                               for v in row] for row in r.ultime.values],
                  [18 * mm, 10 * mm, 50 * mm, 18 * mm, 22 * mm, 14 * mm, 14 * mm, 14 * mm,
                   26 * mm], align_left=(2, 3, 8))]
    al = ctx.alerts
    if al is not None and not al.empty:
        mine = al[al["squadra_id"] == squadra_id]
        if not mine.empty:
            el.append(Paragraph("AVVISI", S["h2"]))
            for x in mine.itertuples():
                chi = f"<b>{x.giocatore}</b>: " if isinstance(x.giocatore, str) else ""
                el.append(Paragraph(f"• {chi}{x.testo}", S["body"]))

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Barlow", 7)
        canvas.setFillColor(GRIGIO)
        canvas.drawString(12 * mm, 8 * mm, f"{config.BRAND} · {r.squadra} · dati legapallacanestro.com"
                                           f" · {date.today().strftime('%d/%m/%Y')}")
        canvas.drawRightString(A4[0] - 12 * mm, 8 * mm, f"pagina {doc_.page}")
        canvas.restoreState()

    doc.build(el, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


def _chiavi(ctx: Contesto, avv: int, mia: int, S, W) -> list:
    """Chiavi per vincere: leve della partita, ritmo, giocatori chiave dell'avversaria."""
    from . import chiavi as C
    from . import validazione as V
    prof = ctx.profile
    camp = prof.set_index("squadra_id").loc[avv, "campionato_id"]
    lega = prof[prof["campionato_id"] == camp]
    if mia not in set(lega["squadra_id"]):
        return []
    ng = ctx.next_game(mia)
    casa_mia = ng["casa_id"] == mia if ng and {ng["casa_id"], ng["ospite_id"]} == {mia, avv} \
        else True
    forze, hca = ctx.forze(camp), ctx.hca(camp)
    lv = C.leve(lega, forze, mia, avv, casa_mia, hca)
    rt = C.ritmo(forze, mia, avv, casa_mia, hca)
    m0, _ = C._margine_noi(forze, mia, avv, casa_mia, hca)
    bt = V.carica()
    bt = bt[bt["stagione"] == ctx.stagione] if not bt.empty else bt
    gc = C.giocatori_chiave(ctx.bg, bt, avv, ctx.nomi_giocatori) if not bt.empty else \
        pd.DataFrame()
    if not gc.empty:
        gc = C.prob_giocatori(gc[gc["effetto"] >= 0.5], m0, True)
    nome_avv = ctx.nomi_squadre.get(avv, str(avv))
    nome_mia = ctx.nomi_squadre.get(mia, str(mia))
    el = [Paragraph(f"CHIAVI PER VINCERE · {nome_mia} contro {nome_avv}", S["h2"]),
          Paragraph(f"Probabilità di vittoria di {nome_mia} secondo il modello: "
                    f"<b>{lv['prob_ora'].iloc[0]:.0f}%</b> "
                    f"({'in casa' if casa_mia else 'in trasferta'}). Le chiavi sono "
                    "associazioni statistiche, non garanzie.", S["body"])]
    for i, t in enumerate(C.sintesi(lv, gc, nome_avv), start=1):
        el.append(Paragraph(f"{i}. {t}".replace(" → ", " · "), S["body"]))
    el.append(Paragraph(f"<b>{C.frase_combinata(C.combinata(lv, gc))}.</b>", S["body"]))
    rows = [["Fattore", "Lato", "Atteso", "Media", "Obiettivo", "Probabilità", "Guadagno"]]
    for x in lv.itertuples():
        f = (lambda v: _fmt(v, 2)) if x.chiave == "ftr" else (lambda v: _fmt(v, 1))
        rows.append([x.fattore, x.lato, f(x.atteso), f(x.media), f(x.obiettivo),
                     f"{_fmt(x.prob_obiettivo, 0)}%", f"{_fmt(x.guadagno, 1, signed=True)}"])
    el.append(_table(rows, [58 * mm, 22 * mm] + [(W - 80 * mm) / 5] * 5, align_left=(1,)))
    lento, veloce = rt.iloc[0], rt.iloc[-1]
    el.append(Paragraph(f"Ritmo: con {_fmt(lento['possessi'], 0)} possessi "
                        f"{_fmt(lento['prob'], 0)}%, con {_fmt(veloce['possessi'], 0)} possessi "
                        f"{_fmt(veloce['prob'], 0)}%.", S["small"]))
    if not gc.empty:
        rows = [["Giocatore", "Soglia", "Partite sotto/sopra", "Scarto sotto", "Scarto sopra",
                 "Probabilità se resta sotto"]]
        for x in gc.head(5).itertuples():
            rows.append([x.giocatore, f"meno di {_fmt(x.soglia, 0)} {x.statistica}",
                         f"{x.partite_sotto}/{x.partite_sopra}",
                         _fmt(x.scarto_sotto, 1, signed=True), _fmt(x.scarto_sopra, 1, signed=True),
                         f"{_fmt(x.prob_scenario, 0)}%"])
        el += [Paragraph(f"GIOCATORI CHIAVE DI {nome_avv.upper()} · scarto rispetto al margine "
                         "previsto", S["h2"]),
               _table(rows, [50 * mm, 34 * mm] + [(W - 84 * mm) / 4] * 4, align_left=(1,))]
    return el


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
        el += [Paragraph("ROTAZIONI", S["h2"]),
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
        el += [Paragraph("QUINTETTI ALTI E BASSI", S["h2"]),
               _table(rows, [40 * mm] + [(W - 40 * mm) / 5] * 5)]
    m = ctx.momenti
    if m is not None and not m.empty and sid in set(m["squadra_id"]):
        rows = [["Momento", "Fatti", "Subiti", "Differenza", "Posizione"]]
        for x in m[m["squadra_id"] == sid].itertuples():
            rows.append([x.etichetta, _fmt(x.fatti_pg), _fmt(x.subiti_pg),
                         _fmt(x.diff_pg, signed=True), f"{x.posizione}° su {x.squadre}"])
        el += [Paragraph("MOMENTI DELLA PARTITA · punti a partita", S["h2"]),
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
            el += [Paragraph("RIPOSO E TRASFERTA PER LA PROSSIMA PARTITA", S["h2"]),
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
