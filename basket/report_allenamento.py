"""PDF del programma di allenamento, da stampare e portare in palestra.

Lo staff sceglie cosa includere (programma["includi"]): obiettivi della settimana, sedute
(una pagina ciascuna, con orari e punti chiave degli esercizi), quintetti su cui lavorare,
lavoro individuale (una scheda per giocatore, da consegnare), preparazione della partita,
gestione dei carichi, giochi della lavagna, foglio presenze e fatica.
"""

import io
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import allenamento as A
from . import config
from . import esercizi as E
from . import pdf_stile as ST
from .report_pdf import Capitoli, _carta, _esc, _fonts, _styles, _table, unisci_titoli

INTENSITA_TXT = {"bassa": "intensità bassa", "media": "intensità media", "alta": "intensità alta"}

CAPITOLI = [("obiettivi", "Obiettivi"), ("sedute", "Le sedute"), ("quintetti", "Quintetti"),
            ("individuali", "Lavoro individuale"), ("giochi", "Giochi da provare"), ("presenze", "Presenze")]


def _n(v, d=1) -> str:
    return f"{v:+.{d}f}".replace(".", ",") if v == v else "–"


def _obiettivi(ctx, sid, prog, S, W) -> list:
    inc = prog["includi"]
    el = []
    pri = A.priorita_squadra(ctx, sid)
    if pri and prog["tipo"] != "individuale":
        righe = [["Priorità", "Lato", "Ora", "Obiettivo", "Posizione", "Aree di lavoro"]]
        for p in pri:
            righe.append([Paragraph(f"<b>{_esc(p['voce'])}</b>", S["cell"]), p["lato"].replace("In ", ""), p["ora"],
                          p["obiettivo"], p["posizione"],
                          Paragraph(_esc(", ".join(E.AREE[a] for a in p["aree"])), S["cell"])])
        el += [Paragraph("Le priorità della squadra · Four Factors sotto la media del campionato", S["h2"]),
               _table(righe, [46 * mm, 18 * mm, 24 * mm, 24 * mm, 20 * mm, W - 132 * mm], align_left=(1, 5)),
               Paragraph("Obiettivo: la media del campionato. Gli esercizi delle sedute sono scelti per queste aree.",
                         S["small"])]
    aree = [E.AREE[a] for a in prog.get("aree", []) if a in E.AREE]
    if aree:
        el += [Paragraph("Le aree di lavoro della settimana", S["h2"]),
               Paragraph(" · ".join(f"<b>{i}</b>&nbsp;{_esc(a)}" for i, a in enumerate(aree, 1)), S["body"])]
    if inc.get("avversaria") and prog.get("partita"):
        el += _avversaria(ctx, sid, prog, S, W)
    if inc.get("carichi"):
        ca = A.carichi(ctx, sid)
        el.append(Paragraph("Gestione dei carichi · minuti delle ultime partite", S["h2"]))
        el += ([Paragraph(f"• <b>{_esc(c['nome'])}</b>: {_esc(c['testo'])}", S["body"]) for c in ca] or
               [Paragraph("Nessun giocatore con minuti molto sopra la sua media nelle ultime partite.", S["small"])])
    if prog.get("note"):
        el += [Paragraph("Note dello staff", S["h2"]), Paragraph(_esc(prog["note"]).replace("\n", "<br/>"), S["body"])]
    return el


def _avversaria(ctx, sid, prog, S, W) -> list:
    """Le tre cose da ricordare sulla prossima avversaria, dalla visione di squadra dello scouting."""
    p = prog["partita"]
    nomi = {v: k for k, v in ctx.nomi_squadre.items()}
    avv_nome = p["ospite"] if nomi.get(p["casa"]) == sid else p["casa"]
    avv = nomi.get(avv_nome)
    if avv is None:
        return []
    try:
        from . import scouting
        from . import sintesi as SI
        r = scouting.build_report(ctx.conn, avv, ctx.stagione)
        s = SI.squadra(ctx, avv, sid, r)
    except Exception:
        return []
    voci = (s.get("da_ricordare") or [])[:3] + (s.get("in_difesa") or [])[:1] + (s.get("in_attacco") or [])[:1]
    if not voci:
        return []
    return [Paragraph(f"Preparazione della partita · {_esc(A.giorno_it(p['data']))} contro {_esc(avv_nome)}", S["h2"])] + \
        [Paragraph(f"• {_esc(v)}", S["body"]) for v in voci]


def _seduta(i: int, s: dict, prog, S, W) -> list:
    inc = prog["includi"]
    testa = (f"Seduta {i} · {A.giorno_it(s['giorno'])} · {s['durata']}' · {INTENSITA_TXT.get(s['intensita'], '')}"
             + (f" · {s['etichetta']}" if s.get("etichetta") else ""))
    el = [Paragraph(_esc(testa), S["h2"]), Paragraph(_esc(s.get("obiettivo", "")), S["body"]), Spacer(1, 4)]
    orari = A.orari(s["blocchi"], s.get("inizio", ""))
    righe = [["Orario", "Fase", "Esercizio", "Min", "Gruppi e note"]]
    for o, b in zip(orari, s["blocchi"]):
        nota = " · ".join(x for x in (b.get("gruppi"), b.get("note")) if x)
        righe.append([o, E.FASI.get(b["fase"], b["fase"]), Paragraph(f"<b>{_esc(b['nome'])}</b>", S["cell"]),
                      str(b.get("minuti", "")), Paragraph(_esc(nota), S["cell"])])
    tot = sum(int(b.get("minuti") or 0) for b in s["blocchi"])
    righe.append(["", "", Paragraph("<b>Totale</b>", S["cell"]), str(tot), ""])
    el.append(_table(righe, [24 * mm, 30 * mm, 62 * mm, 11 * mm, W - 127 * mm], align_left=(1, 2, 4), align_right_from=3))
    if inc.get("esercizi", True):
        visti, schede = set(), []
        for b in s["blocchi"]:
            e = E.PER_ID.get(b["esercizio"])
            if not e or e["id"] in visti:
                continue
            visti.add(e["id"])
            punti = " · ".join(e["punti"])
            schede.append(Paragraph(f"<b>{_esc(e['nome'])}</b> — {_esc(e['descrizione'])} "
                                    f"<font color='#6f6d66'>Punti chiave: {_esc(punti)}"
                                    + (f". Misura: {_esc(e['misura'])}" if e.get("misura") else "") + "</font>",
                                    ParagraphStyle("es", parent=S["small"], textColor=ST.INK, fontSize=7.6, leading=10,
                                                   spaceAfter=3)))
        if schede:
            el += [Spacer(1, 6), Paragraph("Gli esercizi", S["h3"])] + schede
    # spazio per gli appunti a bordo campo
    linee = Table([[""]] * 4, colWidths=[W], rowHeights=[14] * 4)
    linee.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, ST.LINEA_2)]))
    el += [Spacer(1, 6), Paragraph("Appunti", S["h3"]), linee]
    return el


def _quintetti(ctx, sid, S, W) -> list:
    q = A.quintetti(ctx, sid)
    el = [Paragraph("Quintetti su cui lavorare · per migliorare le sinergie in allenamento", S["h2"])]
    if not any(q[k] for k in ("consolidare", "correggere", "coppie_si", "coppie_no")):
        return el + [Paragraph("Servono più partite con i quintetti verificati.", S["small"])]

    def tabella(titolo, voci, spiega, coppia=False):
        if not voci:
            return []
        righe = [[titolo, "Min insieme", "Net rating"]] + [
            [Paragraph(_esc(v["giocatori"]), S["cell"]), f"{v['minuti']:.0f}", _n(v["net"])] for v in voci]
        return [_table(righe, [W - 50 * mm, 25 * mm, 25 * mm], align_left=(0,)),
                Paragraph(spiega, S["small"]), Spacer(1, 6)]
    if q.get("provare"):
        p = q["provare"]
        gia = f"insieme finora {p['minuti']:.0f} minuti" if p["minuti"] >= 1 else "mai in campo insieme finora"
        el += [_carta([Paragraph("<b>Da provare</b>", S["h3"]),
                       Paragraph(f"<font size=11><b>{_esc(p['giocatori'])}</b></font>", S["body"]),
                       Paragraph(f"Tra i nove giocatori più usati, i cinque con le coppie che rendono meglio tra loro ({gia}). "
                                 "Provatelo nel 5c5 a metà campo: spaziature, chi porta palla, chi chiama i giochi.",
                                 S["small"])], W - 4, pad=9), Spacer(1, 8)]
    el += tabella("Da consolidare: funzionano", q["consolidare"],
                  "Usateli nei 5c5 per fissare i giochi e le rotazioni difensive che già funzionano.")
    el += tabella("Da correggere: in campo insieme vanno sotto", q["correggere"],
                  "Lavorate sui loro tempi: spaziature, blocchi, chi prende i rimbalzi, comunicazione in difesa.")
    el += tabella("Coppie che funzionano", q["coppie_si"],
                  "Coppie con il miglior rendimento quando sono in campo insieme: il 2c2 e il 3c3 partono da loro.")
    el += tabella("Coppie da sistemare", q["coppie_no"],
                  "Coppie che insieme subiscono più di quanto segnano: 2c2 e consegnati per costruire le letture.")
    el.append(Paragraph(f"Net rating: punti fatti meno subiti ogni 100 possessi, con il quintetto o la coppia in campo. "
                        f"Quintetti con almeno {q['soglia']:.0f} minuti insieme; i rating con pochi minuti sono "
                        "avvicinati allo zero.", S["small"]))
    return el


def _individuale(g: dict, prog, S, W) -> list:
    sedute = prog.get("sedute", [])
    corpo = [Paragraph(f"<b>{_esc(g['nome'])}</b>" + (f"  <font color='#6f6d66'>#{g['maglia']}</font>" if g.get("maglia") else ""),
                       ParagraphStyle("gn", parent=S["h3"], fontSize=12, leading=14, spaceBefore=0))]
    if g["aree"]:
        for a in g["aree"][:3]:
            corpo.append(Paragraph(f"<b>{_esc(a['voce'])}</b>: {_esc(a['valore'])} → obiettivo <b>{_esc(a['obiettivo'])}</b>",
                                   S["body"]))
    else:
        corpo.append(Paragraph("Nessuna area sotto il livello del ruolo: lavoro di mantenimento sul tiro.", S["small"]))
    if g.get("forza"):
        corpo.append(Paragraph("Punti di forza: " + _esc("; ".join(g["forza"])), S["small"]))
    es = [E.PER_ID[x] for x in g["esercizi"] if x in E.PER_ID]
    if es:
        corpo += [Spacer(1, 3), Paragraph("Esercizi", S["h3"])]
        corpo += [Paragraph(f"• <b>{_esc(e['nome'])}</b> ({e['durata']}') — {_esc(e['descrizione'])}"
                            + (f" <font color='#6f6d66'>Misura: {_esc(e['misura'])}.</font>" if e.get("misura") else ""),
                            S["cell"]) for e in es]
    if sedute:
        righe = [["Seduta"] + [A.giorno_it(s["giorno"]).split()[0][:3] + " " + A.giorno_it(s["giorno"]).split()[-1]
                               for s in sedute], ["Fatto / misura"] + [""] * len(sedute)]
        t = Table(righe, colWidths=[28 * mm] + [(W - 50 * mm) / len(sedute)] * len(sedute), rowHeights=[12, 18])
        t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "Sans"), ("FONTSIZE", (0, 0), (-1, -1), 7),
                               ("TEXTCOLOR", (0, 0), (-1, 0), ST.GRIGIO), ("GRID", (1, 1), (-1, 1), 0.4, ST.LINEA_2),
                               ("LINEBELOW", (0, 0), (-1, 0), 0.4, ST.LINEA_2)]))
        corpo += [Spacer(1, 4), t]
    return [KeepTogether(_carta(corpo, W - 4, pad=9)), Spacer(1, 7)]


def _presenze(ctx, sid, prog, S, W) -> list:
    sedute = prog.get("sedute", [])
    pl = ctx.players[ctx.players["squadra_id"] == sid].sort_values("minuti", ascending=False)
    if prog.get("tipo") == "individuale" and prog.get("giocatori"):
        pl = pl[pl["giocatore_id"].isin(prog["giocatori"])]
    nomi = [A._cognome(n) for n in pl["giocatore"].head(16)] + [""] * 2
    if not sedute:
        return []
    testa = ["Giocatore"] + [f"{A.giorno_it(s['giorno'])}" for s in sedute]
    sotto = [""] + ["Presente · RPE 1-10"] * len(sedute)
    righe = [testa, sotto] + [[n] + [""] * len(sedute) for n in nomi]
    t = Table(righe, colWidths=[40 * mm] + [(W - 40 * mm) / len(sedute)] * len(sedute),
              rowHeights=[14, 11] + [17] * len(nomi), repeatRows=2)
    t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "Sans"), ("FONTSIZE", (0, 0), (-1, 0), 7.5),
                           ("FONTSIZE", (0, 1), (-1, -1), 7.8), ("FONTSIZE", (1, 1), (-1, 1), 6.2),
                           ("TEXTCOLOR", (0, 0), (-1, 1), ST.GRIGIO), ("FONTNAME", (0, 0), (-1, 0), "Sans-Medium"),
                           ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("LINEBELOW", (0, 1), (-1, 1), 0.7, ST.INK), ("GRID", (1, 2), (-1, -1), 0.4, ST.LINEA_2),
                           ("LINEBELOW", (0, 2), (0, -1), 0.4, ST.LINEA_2)]))
    return [Paragraph("Presenze e fatica · da compilare a fine seduta", S["h2"]), t,
            Paragraph("RPE: fatica percepita da 1 (molto leggera) a 10 (massima), chiesta a ogni giocatore 20-30 minuti "
                      "dopo la seduta. RPE × minuti della seduta = carico: tenerlo sotto controllo prima della partita.",
                      S["small"])]


def build_programma(ctx, sid: int, prog: dict, giochi: list[dict] | None = None) -> bytes:
    """PDF del programma: copertina con i capitoli scelti, poi un capitolo per ogni parte inclusa."""
    _fonts()
    S = _styles()
    W = A4[0] - 24 * mm
    inc = prog.get("includi", {})
    nome_sq = ctx.nomi_squadre.get(sid, str(sid))
    individuale = prog.get("tipo") == "individuale"
    giochi = [g for g in (giochi or []) if g.get("id") in set(prog.get("giochi", []))] if inc.get("giochi") else []
    ind = A.individuali(ctx, sid, prog.get("giocatori") or None) if inc.get("individuali") else []
    presenti = {"obiettivi": inc.get("obiettivi"), "sedute": inc.get("sedute") and prog.get("sedute"),
                "quintetti": inc.get("quintetti") and not individuale, "individuali": bool(ind),
                "giochi": bool(giochi), "presenze": inc.get("presenze") and prog.get("sedute")}
    if individuale:            # nel programma individuale le schede dei giocatori vengono prima
        ordine = ["individuali", "obiettivi", "sedute", "giochi", "presenze"]
    else:
        ordine = [k for k, _ in CAPITOLI]
    titoli = dict(CAPITOLI)
    capitoli = [titoli[k] for k in ordine if presenti.get(k)]
    cap = Capitoli(capitoli, W)
    sedute = prog.get("sedute", [])
    durata = sum(s.get("durata", 0) for s in sedute)
    meta = (f"{len(sedute)} sedute · {durata} minuti in tutto · dal {A.giorno_it(prog.get('dal', ''))}"
            + (f"<br/>Prossima partita: {A.giorno_it(prog['partita']['data'])}, {prog['partita']['casa']} – "
               f"{prog['partita']['ospite']}" if prog.get("partita") else ""))
    eyebrow = ("Programma individuale" if individuale else "Programma di allenamento") + f" · {nome_sq}"
    el = [ST.Intestazione(W, eyebrow=eyebrow, titolo=prog.get("nome") or "Programma della settimana", meta=meta,
                          marchio=config.BRAND)]
    if capitoli:
        el += [ST.Sommario(W, capitoli), Spacer(1, 8)]
    primo = True
    for k in ordine:
        if not presenti.get(k):
            continue
        if not primo:
            el.append(PageBreak())
        if k == "obiettivi":
            el += cap(titoli[k], "Su cosa lavora la settimana e perché, dai numeri della squadra.") + \
                _obiettivi(ctx, sid, prog, S, W)
        elif k == "sedute":
            el += cap(titoli[k], "Una pagina per seduta: orari, esercizi, punti chiave e spazio per gli appunti.")
            rep = A.reparti(ind or A.individuali(ctx, sid, prog.get("giocatori") or None))
            if rep and not individuale:
                el += [Paragraph("Gruppi per reparto · per la tecnica individuale e i lavori a stazioni", S["h3"])] + \
                    [Paragraph(f"<b>{_esc(k)}</b>: {_esc(', '.join(v))}", S["body"]) for k, v in rep.items()] + \
                    [Spacer(1, 8)]
            for i, s in enumerate(sedute, 1):
                if i > 1:
                    el.append(PageBreak())
                el += _seduta(i, s, prog, S, W)
        elif k == "quintetti":
            el += cap(titoli[k], "I quintetti e le coppie su cui costruire le sinergie nei 5c5 e nelle situazioni.") + \
                _quintetti(ctx, sid, S, W)
        elif k == "individuali":
            el += cap(titoli[k], "Una scheda per giocatore, da consegnare: aree, obiettivi, esercizi e cosa misurare.")
            for g in ind:
                el += _individuale(g, prog, S, W)
        elif k == "giochi":
            from . import lavagna as L
            el += cap(titoli[k], "I giochi della lavagna da provare nelle sedute, fase per fase.") + \
                L.flowables(giochi, S, W, "Giochi · disegnati dallo staff")[1:]
        elif k == "presenze":
            el += cap(titoli[k], "Da stampare e compilare a bordo campo.") + _presenze(ctx, sid, prog, S, W)
        primo = False
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                            bottomMargin=14 * mm, title=f"Programma di allenamento · {nome_sq}", author=config.BRAND)
    piede = ST.piede(f"{'Programma individuale' if individuale else 'Programma di allenamento'} · {nome_sq}")
    doc.build(unisci_titoli(el, W), onFirstPage=piede, onLaterPages=piede)
    return buf.getvalue()


def nome_file(prog: dict) -> str:
    from .report_pdf import slug
    return f"allenamento_{slug(prog.get('nome') or 'programma')}_{prog.get('dal', date.today().isoformat())}.pdf"
