"""PDF di una pagina con il confronto tra due giocatori (per il direttore sportivo)."""

import math
from datetime import date

import pandas as pd
from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, String
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from . import confronto as CF
from .report_extra import _documento, _piede, _testata
from .report_pdf import ARANCIO, BLU, BORDO, GRIGIO, INK, _fmt, _fonts, _styles, _table


def _radar(sa: dict, sb: dict, nomi: list[str], lato: float) -> Drawing:
    dims = list(CF.DIMENSIONI)
    d = Drawing(lato, lato)
    cx, cy, r = lato / 2, lato / 2 - 4, lato / 2 - 30
    angoli = [math.pi / 2 - 2 * math.pi * i / len(dims) for i in range(len(dims))]
    for k in (25, 50, 75, 100):
        pts = []
        for a in angoli:
            pts += [cx + r * k / 100 * math.cos(a), cy + r * k / 100 * math.sin(a)]
        d.add(Polygon(pts, fillColor=None, strokeColor=BORDO, strokeWidth=0.6))
    for a, dim in zip(angoli, dims):
        d.add(Line(cx, cy, cx + r * math.cos(a), cy + r * math.sin(a), strokeColor=BORDO,
                   strokeWidth=0.5))
        x, y = cx + (r + 12) * math.cos(a), cy + (r + 10) * math.sin(a)
        anchor = "middle" if abs(math.cos(a)) < 0.3 else ("start" if math.cos(a) > 0 else "end")
        d.add(String(x, y - 3, dim, fontName="Barlow-SemiBold", fontSize=7, fillColor=INK,
                     textAnchor=anchor))
    for s, col in ((sa, BLU), (sb, ARANCIO)):
        pts = []
        for a, dim in zip(angoli, dims):
            v = s["dimensioni"].get(dim)
            v = 0 if v is None or pd.isna(v) else v
            pts += [cx + r * v / 100 * math.cos(a), cy + r * v / 100 * math.sin(a)]
        fill = colors.Color(col.red, col.green, col.blue, alpha=0.22)
        d.add(Polygon(pts, fillColor=fill, strokeColor=col, strokeWidth=1.6))
        for i in range(0, len(pts), 2):
            d.add(Circle(pts[i], pts[i + 1], 1.8, fillColor=col, strokeColor=None))
    for i, (n, col) in enumerate(((nomi[0], BLU), (nomi[1], ARANCIO))):
        x = 8 + i * lato / 2
        d.add(Line(x, 6, x + 14, 6, strokeColor=col, strokeWidth=3))
        d.add(String(x + 18, 3.5, n, fontName="Barlow-SemiBold", fontSize=7.5, fillColor=INK))
    return d


def build_confronto(sa: dict, sb: dict, aa: dict, ab: dict, fit: pd.DataFrame, chiavi: list,
                    nomi: list[str], squadra: str | None = None) -> bytes:
    _fonts()
    S = _styles()
    W = 186 * mm
    na, nb = nomi
    ra, rb = sa["riga"], sb["riga"]
    buf, doc = _documento(f"Confronto {na} – {nb}")
    meta = (f"{ra['giocatore']} ({ra['squadra']}, {ra['categoria']}, {ra['stagione_label']}) · "
            f"{rb['giocatore']} ({rb['squadra']}, {rb['categoria']}, {rb['stagione_label']}) · "
            f"{date.today().strftime('%d/%m/%Y')}")
    el = [_testata("Confronto giocatori · mercato", f"{na.upper()} – {nb.upper()}", meta, S, W),
          Spacer(1, 6)]
    frasi = CF.verdetto(sa, sb) + CF.frasi_affidabilita(aa, ab, na, nb)
    fr = CF.frase_adattamento(fit, chiavi, nomi) if fit is not None and not fit.empty else None
    if fr:
        frasi.append(fr)
    el.append(Paragraph("IN SINTESI", S["h2"]))
    el += [Paragraph(f"• {f}", S["body"]) for f in frasi]
    avvisi = []
    for s, n in ((sa, na), (sb, nb)):
        if s["convertito"]:
            avvisi.append(f"numeri di {n} (B Nazionale) riportati alla scala dell'A2")
        if s["pochi_dati"]:
            avvisi.append(f"{n}: solo {_fmt(s['riga']['minuti'], 0)} minuti, profilo indicativo")
    if sa["ruolo"] != sb["ruolo"]:
        avvisi.append("ruoli diversi: ognuno è misurato rispetto al proprio ruolo")
    if avvisi:
        el.append(Paragraph("<b>Da sapere:</b> " + "; ".join(avvisi) + ".", S["small"]))

    # radar + dimensioni
    rows = [["Dimensione", na, nb, "Diff."]]
    for d in CF.DIMENSIONI:
        va, vb = sa["dimensioni"].get(d), sb["dimensioni"].get(d)
        rows.append([d, _fmt(va, 0), _fmt(vb, 0),
                     _fmt(va - vb, 0, True) if pd.notna(va) and pd.notna(vb) else "–"])
    pa, pb = sa["possesso"], sb["possesso"]
    prow = [["Ogni 100 possessi usati", na, nb, "Mediana ruolo"],
            ["Possessi usati / 40'", _fmt(pa["usati_p40"]), _fmt(pb["usati_p40"]),
             _fmt(sa["possesso_ruolo"].get("usati_p40"))],
            ["Punti prodotti", _fmt(pa["punti_100"], 0), _fmt(pb["punti_100"], 0),
             _fmt(sa["possesso_ruolo"].get("punti_100"), 0)],
            ["Palle perse", _fmt(pa["perse_100"], 0), _fmt(pb["perse_100"], 0),
             _fmt(sa["possesso_ruolo"].get("perse_100"), 0)],
            ["Tiri sbagliati", _fmt(pa["sbagliati_100"], 0), _fmt(pb["sbagliati_100"], 0),
             _fmt(sa["possesso_ruolo"].get("sbagliati_100"), 0)]]
    destra = [Paragraph("PROFILO · percentili nel ruolo", S["h3"]),
              _table(rows, [40 * mm, 20 * mm, 20 * mm, 16 * mm]), Spacer(1, 6),
              Paragraph("COSA PRODUCE OGNI POSSESSO", S["h3"]),
              _table(prow, [40 * mm, 18 * mm, 18 * mm, 20 * mm])]
    t = Table([[_radar(sa, sb, nomi, 82 * mm), destra]], colWidths=[86 * mm, W - 86 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    el.append(t)

    # affidabilità e numeri affiancati
    arow = [["Affidabilità (GS/40)", na, nb]]
    for lab, k, d, suf in (("Partite", "partite", 0, ""), ("Game Score / 40'", "gs_p40", 1, ""),
                           ("Partite storte", "partite_storte", 0, "%"),
                           ("Contro le forti", "forti_p40", 1, ""),
                           ("Contro le deboli", "deboli_p40", 1, ""),
                           ("Ultime 5", "ultime5_p40", 1, "")):
        arow.append([lab, _fmt(aa.get(k), d) + (suf if pd.notna(aa.get(k)) else ""),
                     _fmt(ab.get(k), d) + (suf if pd.notna(ab.get(k)) else "")])
    nrow = [["Per 40 minuti", na, nb]]
    for lab, col, d in (("Minuti a partita", "minuti_pg", 1), ("Punti", "punti_p40", 1),
                        ("TS%", "ts_pct", 1), ("Usage %", "usg_pct", 1),
                        ("Assist", "assist_p40", 1), ("Rimbalzi", "rimb_tot_p40", 1),
                        ("% da 3 (prudente)", "t3_pct", 1), ("Età", "eta", 0),
                        ("Altezza", "altezza_cm", 0)):
        nrow.append([lab, _fmt(ra.get(col), d), _fmt(rb.get(col), d)])
    t = Table([[_table(arow, [44 * mm, 24 * mm, 24 * mm]),
                _table(nrow, [40 * mm, 24 * mm, 24 * mm])]], colWidths=[W / 2, W / 2])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    el += [Spacer(1, 6), t]

    if fit is not None and not fit.empty:
        frow = [["Bisogno di " + (squadra or "squadra"), "Priorità", na, nb]]
        for _, r in fit.iterrows():
            frow.append([r["bisogno"], r["priorita"],
                         _fmt(r[chiavi[0]], 0) if pd.notna(r[chiavi[0]]) else "fuori profilo",
                         _fmt(r[chiavi[1]], 0) if pd.notna(r[chiavi[1]]) else "fuori profilo"])
        el += [Spacer(1, 6), _table(frow, [70 * mm, 24 * mm, 30 * mm, 30 * mm])]
    el.append(Paragraph("Percentili tra i giocatori dello stesso ruolo con almeno 10' di media. "
                        "Percentuali di tiro prudenti. Possessi usati = tiri + 0,44 × liberi + palle "
                        "perse. Partite storte: Game Score sotto metà della propria media.",
                        S["small"]))
    piede = _piede(f"confronto {na} – {nb}")
    doc.build(el, onFirstPage=piede, onLaterPages=piede)
    return buf.getvalue()
