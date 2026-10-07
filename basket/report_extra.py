"""Report post-partita della propria squadra e report individuale per il giocatore.

    python -m basket.report_extra partita "Forlì"            # ultima partita giocata
    python -m basket.report_extra giocatore "Forlì" "Rossi"   # report di crescita
"""

import argparse
import io
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import analysis as A
from . import approfondimenti as X
from . import avvisi as AV
from . import config, mercato, scouting
from .contesto import Contesto, open_readonly
from .report_pdf import (ARANCIO, BLU, GRIGIO, INK, NAVY, ROSSO, _fmt, _fonts, _kpis, _styles,
                         _table, slug)

FATTORI = [("efg_pct", "eFG%", True, 1), ("tov_pct", "Palle perse %", False, 1),
           ("orb_pct", "Rimbalzi offensivi %", True, 1), ("ft_rate", "Liberi / tiri", True, 2),
           ("opp_efg_pct", "eFG% concessa", False, 1),
           ("opp_tov_pct", "Palle perse forzate %", True, 1),
           ("drb_pct", "Rimbalzi difensivi %", True, 1),
           ("opp_ft_rate", "Liberi concessi / tiri", False, 2)]


# ------------------------------------------------------------------ dati della partita

def ultima_partita(ctx: Contesto, squadra_id: int) -> str | None:
    mine = ctx.bs[ctx.bs["squadra_id"] == squadra_id].sort_values(["data", "partita_id"])
    return None if mine.empty else mine["partita_id"].iloc[-1]


def riepilogo_partita(ctx: Contesto, squadra_id: int, partita_id: str,
                      obiettivi: dict | None = None) -> dict:
    """Tutto quello che serve per raccontare una partita della propria squadra."""
    bs = ctx.bs
    riga = bs[(bs["partita_id"] == partita_id) & (bs["squadra_id"] == squadra_id)]
    if riga.empty:
        raise ValueError("Partita non trovata per questa squadra")
    riga = A.team_ratings(riga.copy()).iloc[0]
    stagione = A.team_ratings(bs[(bs["squadra_id"] == squadra_id) & bs["affidabile"]]
                              .sum(numeric_only=True).to_frame().T).iloc[0]
    obiettivi = {**AV.OBIETTIVI_DEFAULT, **(obiettivi or {})}
    affidabile = bool(riga.get("affidabile", True))

    fattori = []
    for col, lab, alto, d in FATTORI:
        v, m, o = riga.get(col), stagione.get(col), obiettivi.get(col)
        ok = None if pd.isna(v) or o is None else (v >= o if alto else v <= o)
        fattori.append({"voce": lab, "partita": v, "media": m, "obiettivo": o, "raggiunto": ok,
                        "decimali": d, "alto": alto})

    # fattore decisivo: dove la partita si discosta di più dalla media, nel verso giusto o no
    def scarto(f):
        if pd.isna(f["partita"]) or pd.isna(f["media"]) or not f["media"]:
            return 0
        s = (f["partita"] - f["media"]) / abs(f["media"])
        return s if f["alto"] else -s
    ordinati = sorted(fattori, key=scarto)
    vinta = bool(riga["vinta"])
    chiave = ordinati[-1] if vinta else ordinati[0]

    bg = ctx.bg[(ctx.bg["partita_id"] == partita_id) & (ctx.bg["squadra_id"] == squadra_id)].copy()
    bg["game_score"] = A.game_score(bg)
    medie = ctx.players[ctx.players["squadra_id"] == squadra_id].set_index("giocatore_id")
    bg["gs_medio"] = bg["giocatore_id"].map(medie["game_score_pg"])
    bg["punti_medi"] = bg["giocatore_id"].map(medie["punti_pg"])
    bg["delta_gs"] = bg["game_score"] - bg["gs_medio"]
    giocatori = bg[bg["minuti"] > 0].sort_values("minuti", ascending=False)

    partita = ctx.partite[ctx.partite["partita_id"] == partita_id].iloc[0]
    parziali = []
    try:
        parz = json.loads(ctx.conn.execute("SELECT parziali FROM partite WHERE partita_id = ?",
                                           (partita_id,)).fetchone()[0] or "[]")
        casa = int(partita["squadra_casa_id"]) == int(squadra_id)
        for p in parz:
            noi, loro = (p["casa"], p["ospite"]) if casa else (p["ospite"], p["casa"])
            parziali.append(("Q" + str(p["periodo"]) if p["periodo"] <= 4 else "OT", noi, loro))
    except (TypeError, ValueError, KeyError):
        pass

    frasi = []
    if affidabile:
        verbo = "Vinta" if vinta else "Persa"
        frasi.append(f"{verbo}: la voce che ha pesato di più è {chiave['voce']} "
                     f"({_fmt(chiave['partita'], chiave['decimali'])}, media stagionale "
                     f"{_fmt(chiave['media'], chiave['decimali'])}).")
    sopra = giocatori[giocatori["delta_gs"] >= 5].sort_values("delta_gs", ascending=False)
    sotto = giocatori[(giocatori["delta_gs"] <= -5) & (giocatori["minuti"] >= 10)]
    if not sopra.empty:
        frasi.append("Sopra la propria media: " + ", ".join(
            f"{r.giocatore} ({r.punti} punti)" for r in sopra.head(3).itertuples()) + ".")
    if not sotto.empty:
        frasi.append("Sotto la propria media: " + ", ".join(
            f"{r.giocatore}" for r in sotto.sort_values("delta_gs").head(3).itertuples()) + ".")
    if parziali:
        peggiore = min(parziali, key=lambda q: q[1] - q[2])
        migliore = max(parziali, key=lambda q: q[1] - q[2])
        if migliore[1] - migliore[2] > 0:
            frasi.append(f"Quarto migliore: {migliore[0]} ({migliore[1]}-{migliore[2]}).")
        if peggiore[1] - peggiore[2] < 0:
            frasi.append(f"Quarto peggiore: {peggiore[0]} ({peggiore[1]}-{peggiore[2]}).")

    return {"riga": riga, "stagione": stagione, "fattori": fattori, "giocatori": giocatori,
            "parziali": parziali, "frasi": frasi, "vinta": vinta, "affidabile": affidabile,
            "partita": partita, "squadra": riga["squadra"], "avversario": riga["avversario"]}


# ------------------------------------------------------------------ PDF comuni

def _testata(eyebrow: str, titolo: str, meta: str, S, W):
    testo = Table([[Paragraph(eyebrow.upper(), S["eyebrow"])], [Paragraph(titolo, S["h1"])],
                   [Paragraph(meta, S["meta"])]], colWidths=[W - 34 * mm])
    testo.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), 1),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    marchio = [Image(str(config.LOGO_DIR / "assist-mark-512.png"), 16 * mm, 16 * mm),
               Paragraph(config.BRAND, ParagraphStyle(
                   "brand", fontName="Condensed", fontSize=11, leading=13, alignment=1,
                   textColor=colors.white, spaceBefore=2))]
    t = Table([[testo, marchio]], colWidths=[W - 34 * mm, 34 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY),
                           ("LEFTPADDING", (0, 0), (0, 0), 12),
                           ("TOPPADDING", (0, 0), (-1, -1), 10),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("ALIGN", (1, 0), (1, 0), "CENTER"),
                           ("LINEBELOW", (0, -1), (-1, -1), 3, ARANCIO)]))
    return t


def _documento(titolo: str):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=14 * mm, title=titolo,
                            author=config.BRAND)
    return buf, doc


def _piede(testo: str):
    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Barlow", 7)
        canvas.setFillColor(GRIGIO)
        canvas.drawString(12 * mm, 8 * mm, f"{config.BRAND} · {testo} · dati legapallacanestro.com"
                                           f" · {date.today().strftime('%d/%m/%Y')}")
        canvas.drawRightString(A4[0] - 12 * mm, 8 * mm, f"pagina {doc_.page}")
        canvas.restoreState()
    return footer


def _data_it(d) -> str:
    try:
        return pd.Timestamp(d).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(d)


# ------------------------------------------------------------------ PDF post-partita

def build_post_partita(ctx: Contesto, squadra_id: int, partita_id: str | None = None,
                       obiettivi: dict | None = None) -> bytes:
    _fonts()
    S = _styles()
    W = A4[0] - 24 * mm
    partita_id = partita_id or ultima_partita(ctx, squadra_id)
    if partita_id is None:
        raise ValueError("Nessuna partita giocata")
    r = riepilogo_partita(ctx, squadra_id, partita_id, obiettivi)
    riga, p = r["riga"], r["partita"]
    dove = "in casa" if int(p["squadra_casa_id"]) == int(squadra_id) else "in trasferta"
    esito = "Vittoria" if r["vinta"] else "Sconfitta"
    buf, doc = _documento(f"Post-partita {r['squadra']}")
    el = [_testata(f"Report post-partita · {p['giornata']}ª giornata · {_data_it(p['data'])}",
                   f"{r['squadra'].upper()} {int(riga['punti'])}–{int(riga['punti_subiti'])} "
                   f"{r['avversario'].upper()}",
                   f"{esito} {dove}" + (f" · {p['palazzetto']}" if p.get("palazzetto") else ""),
                   S, W), Spacer(1, 6)]
    if r["affidabile"]:
        st = r["stagione"]
        el.append(_kpis([
            ("Possessi", _fmt(riga["possessi"], 0), f"media {_fmt(st['pace'], 0)} per 40'"),
            ("Rating offensivo", _fmt(riga["ortg"]), f"media {_fmt(st['ortg'])}"),
            ("Rating difensivo", _fmt(riga["drtg"]), f"media {_fmt(st['drtg'])}"),
            ("eFG%", _fmt(riga["efg_pct"]), f"media {_fmt(st['efg_pct'])}"),
            ("Palle perse %", _fmt(riga["tov_pct"]), f"media {_fmt(st['tov_pct'])}"),
        ], S, W))
    else:
        el.append(Paragraph("Box score ufficiale incompleto: le metriche avanzate di questa "
                            "partita non sono affidabili.", S["small"]))
    el += [Paragraph("IN SINTESI", S["h2"])] + [Paragraph("• " + f, S["body"]) for f in r["frasi"]]

    if r["affidabile"]:
        rows = [["Fattore", "Partita", "Media stagione", "Obiettivo", ""]]
        for f in r["fattori"]:
            esito_f = "" if f["raggiunto"] is None else ("raggiunto" if f["raggiunto"]
                                                         else "mancato")
            rows.append([f["voce"], _fmt(f["partita"], f["decimali"]),
                         _fmt(f["media"], f["decimali"]), _fmt(f["obiettivo"], f["decimali"]),
                         esito_f])
        t = _table(rows, [60 * mm, 25 * mm, 30 * mm, 25 * mm, 25 * mm])
        stile = []
        for i, f in enumerate(r["fattori"], start=1):
            if f["raggiunto"] is not None:
                stile.append(("TEXTCOLOR", (4, i), (4, i), BLU if f["raggiunto"] else ROSSO))
        t.setStyle(TableStyle(stile))
        el += [Paragraph("FOUR FACTORS · partita, media e obiettivi dello staff", S["h2"]), t]

    if r["parziali"]:
        rows = [["Periodo"] + [q[0] for q in r["parziali"]],
                [r["squadra"][:24]] + [str(q[1]) for q in r["parziali"]],
                [r["avversario"][:24]] + [str(q[2]) for q in r["parziali"]]]
        n = len(r["parziali"])
        el += [Paragraph("QUARTO PER QUARTO", S["h2"]),
               _table(rows, [60 * mm] + [(W - 60 * mm) / n] * n)]

    g = r["giocatori"]
    rows = [["Giocatore", "Min", "Pt", "Tiri 2", "Tiri 3", "TL", "Rimb", "Ass", "Perse",
             "GmSc", "Media", "Diff"]]
    for x in g.itertuples():
        rows.append([x.giocatore, str(int(x.minuti)), str(int(x.punti)),
                     f"{int(x.t2m)}/{int(x.t2a)}", f"{int(x.t3m)}/{int(x.t3a)}",
                     f"{int(x.tlm)}/{int(x.tla)}", str(int(x.rimb_tot)), str(int(x.assist)),
                     str(int(x.perse)), _fmt(x.game_score), _fmt(x.gs_medio),
                     _fmt(x.delta_gs, signed=True)])
    t = _table(rows, [42 * mm] + [(W - 42 * mm) / 11] * 11)
    stile = []
    for i, x in enumerate(g.itertuples(), start=1):
        if pd.notna(x.delta_gs) and abs(x.delta_gs) >= 5:
            stile.append(("TEXTCOLOR", (11, i), (11, i), BLU if x.delta_gs > 0 else ROSSO))
    t.setStyle(TableStyle(stile))
    el += [Paragraph("GIOCATORI · Game Score della partita contro la media stagionale", S["h2"]),
           t, Paragraph("Game Score: sintesi del contributo statistico (punti, tiri, rimbalzi, "
                        "assist, recuperi, stoppate, perse, falli). Diff in blu/rosso quando lo "
                        "scarto dalla media è di almeno 5.", S["small"])]
    doc.build(el, onFirstPage=_piede(f"{r['squadra']} – {r['avversario']}"),
              onLaterPages=_piede(f"{r['squadra']} – {r['avversario']}"))
    return buf.getvalue()


# ------------------------------------------------------------------ PDF giocatore

def build_giocatore(ctx: Contesto, giocatore_id: str, squadra_id: int,
                    storico: pd.DataFrame | None = None) -> bytes:
    _fonts()
    S = _styles()
    W = A4[0] - 24 * mm
    pl = ctx.players
    me = pl[(pl["giocatore_id"] == giocatore_id) & (pl["squadra_id"] == squadra_id)]
    if me.empty:
        raise ValueError("Giocatore non trovato")
    me = me.iloc[0]
    hist = storico if storico is not None else mercato.season_lines(ctx.conn)
    mine = hist[hist["giocatore_id"] == giocatore_id]
    bio = mine[mine["stagione"] == ctx.stagione].head(1)
    bio = bio.iloc[0] if not bio.empty else None
    meta = [me["squadra"], f"{int(me['partite'])} partite", f"{me['minuti_pg']:.1f} minuti di media"]
    if bio is not None:
        if pd.notna(bio.get("eta")):
            meta.append(f"{int(bio['eta'])} anni")
        if pd.notna(bio.get("altezza_cm")):
            meta.append(f"{int(bio['altezza_cm'])} cm")
        if bio.get("ruolo"):
            meta.append(str(bio["ruolo"]).lower())
    buf, doc = _documento(f"Report {me['giocatore']}")
    el = [_testata(f"Report individuale · {config.STAGIONI.get(ctx.stagione, ctx.stagione)}",
                   me["giocatore"].upper(), " · ".join(meta), S, W), Spacer(1, 6)]
    el.append(_kpis([
        ("Punti", _fmt(me["punti_pg"]), f"{_fmt(me['punti_p40'])} per 40'"),
        ("Rimbalzi", _fmt(me["rimb_tot_pg"]), f"REB% {_fmt(me['trb_pct'])}"),
        ("Assist", _fmt(me["assist_pg"]), f"AST% {_fmt(me['ast_pct'])}"),
        ("True shooting", _fmt(me["ts_pct"]) + "%", f"eFG% {_fmt(me['efg_pct'])}"),
        ("Usage", _fmt(me["usg_pct"]) + "%", f"palle perse {_fmt(me['tov_pct'])}%"),
        ("Game Score", _fmt(me["game_score_pg"]), "a partita"),
    ], S, W))
    frasi = X.frase_giocatore(pl[pl["campionato_id"] == me["campionato_id"]], giocatore_id,
                              squadra_id)
    if frasi:
        el += [Paragraph("IN UNA FRASE", S["h2"]),
               Paragraph(frasi[0][0].upper() + frasi[0][1:] + (
                   ", " + ", ".join(frasi[1:]) if len(frasi) > 1 else "") + ".", S["body"])]

    pc = A.percentiles(pl, giocatore_id, squadra_id)
    if not pc.empty:
        rows = [["Metrica", "Valore", "Percentile", ""]]
        for x in pc.itertuples():
            rows.append([x.Metrica, _fmt(x.Valore), f"{int(x.Percentile)}°",
                         _barra(x.Percentile, 60 * mm)])
        el += [Paragraph("PROFILO · percentile nel campionato (giocatori con almeno 10' di media)",
                         S["h2"]), _table(rows, [60 * mm, 22 * mm, 22 * mm, 66 * mm])]

    log = A.player_game_log(ctx.bg[ctx.bg["squadra_id"] == squadra_id], giocatore_id)
    if not log.empty:
        log["game_score"] = A.game_score(log)
        rows = [["G.", "Data", "Avversario", "Min", "Pt", "Tiri", "Rimb", "Ass", "Perse", "GmSc"]]
        for x in log.tail(10).iloc[::-1].itertuples():
            rows.append([str(x.giornata), _data_it(x.data), str(x.avversario)[:26],
                         str(int(x.minuti)), str(int(x.punti)),
                         f"{int(x.t2m + x.t3m)}/{int(x.t2a + x.t3a)}", str(int(x.rimb_tot)),
                         str(int(x.assist)), str(int(x.perse)), _fmt(x.game_score)])
        el += [Paragraph("ULTIME PARTITE", S["h2"]),
               _table(rows, [10 * mm, 20 * mm, 50 * mm] + [(W - 80 * mm) / 7] * 7,
                      align_left=(2,))]

    if len(mine) > 1:
        rows = [["Stagione", "Squadra", "Cat.", "PG", "Min", "Pt", "Rimb", "Ass", "TS%", "USG%"]]
        for x in mine.sort_values("stagione", ascending=False).itertuples():
            rows.append([x.stagione_label, str(x.squadra)[:28], x.categoria, str(int(x.partite)),
                         _fmt(x.minuti_pg), _fmt(x.punti_pg), _fmt(x.rimb_tot_pg),
                         _fmt(x.assist_pg), _fmt(x.ts_pct), _fmt(x.usg_pct)])
        el += [Paragraph("CARRIERA IN ARCHIVIO", S["h2"]),
               _table(rows, [18 * mm, 50 * mm, 22 * mm] + [(W - 90 * mm) / 7] * 7,
                      align_left=(1, 2))]

    el += [Paragraph("OBIETTIVI CONCORDATI CON LO STAFF", S["h2"])]
    linee = Table([[""] for _ in range(6)], colWidths=[W], rowHeights=[9 * mm] * 6)
    linee.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9cfdb"))]))
    el.append(linee)
    doc.build(el, onFirstPage=_piede(me["giocatore"]), onLaterPages=_piede(me["giocatore"]))
    return buf.getvalue()


def _barra(pct, width):
    from reportlab.graphics.shapes import Drawing, Line, Rect
    d = Drawing(width, 8)
    d.add(Rect(0, 1.5, width, 5, fillColor=colors.HexColor("#eef1f6"), strokeColor=None))
    d.add(Rect(0, 1.5, width * max(0, min(100, pct)) / 100, 5,
               fillColor=BLU if pct >= 50 else ARANCIO, strokeColor=None))
    d.add(Line(width / 2, 0, width / 2, 8, strokeColor=INK, strokeWidth=0.6))
    return d


# ------------------------------------------------------------------ riga di comando

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Report post-partita e report individuale")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("partita")
    a.add_argument("squadra")
    b = sub.add_parser("giocatore")
    b.add_argument("squadra")
    b.add_argument("giocatore")
    ap.add_argument("--out", default=str(config.REPORTS_DIR / "pdf"))
    args = ap.parse_args(argv)
    ctx = open_readonly()
    teams = scouting.find_team(ctx.conn, args.squadra)
    if len(teams) != 1:
        print("Squadre trovate:", ", ".join(n for _, n in teams) or "nessuna")
        return 1
    sid, nome = teams[0]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.cmd == "partita":
        path = out / f"post_partita_{slug(nome)}.pdf"
        path.write_bytes(build_post_partita(ctx, int(sid)))
    else:
        p = ctx.players[(ctx.players["squadra_id"] == sid) &
                        ctx.players["giocatore"].str.contains(args.giocatore, case=False)]
        if len(p) != 1:
            print("Giocatori trovati:", ", ".join(p["giocatore"]) or "nessuno")
            return 1
        path = out / f"giocatore_{slug(p.iloc[0]['giocatore'])}.pdf"
        path.write_bytes(build_giocatore(ctx, p.iloc[0]["giocatore_id"], int(sid)))
    print("Scritto", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
