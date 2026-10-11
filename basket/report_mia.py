"""PDF completo della propria squadra: tutte le voci di "La mia squadra" in un documento.

    python -m basket.report_mia "Forlì"        # reports/pdf/mia_squadra_<squadra>.pdf
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, Spacer

from . import avvisi as AV
from . import chiavi as C
from . import config
from . import lavagna as L
from . import miglioramento as M
from .contesto import Contesto, open_readonly
from .report_extra import _data_it, _documento, _piede, _testata
from .report_pdf import (_approfondimenti, _fmt, _fonts, _kpis, _styles, _table, slug,
                         unisci_titoli)

# stesse voci e nomi del pannello obiettivi della dashboard
OBIETTIVI = {"efg_pct": "eFG% in attacco", "tov_pct": "Palle perse %",
             "orb_pct": "Rimbalzi offensivi %", "ft_rate": "FT rate",
             "opp_efg_pct": "eFG% concessa", "opp_tov_pct": "Palle perse forzate %",
             "drb_pct": "Rimbalzi difensivi %", "opp_ft_rate": "FT rate concesso"}


def _virgola(testo: str) -> str:
    """Decimali all'italiana nelle frasi (3.5 → 3,5)."""
    return re.sub(r"(?<![\d.])(\d+)\.(\d+)(?![\d.])", r"\1,\2", testo)


def _rank(lega: pd.DataFrame, sid: int, col: str, asc: bool = False) -> str:
    v = lega.set_index("squadra_id")[col]
    if pd.isna(v.get(sid)):
        return "–"
    return f"{int(v.rank(ascending=asc, method='min')[sid])}° su {len(v)}"


def _titolo(testo: str, S) -> Paragraph:
    return Paragraph(testo.upper(), S["h2"])


def _quintetti(df: pd.DataFrame, S, W) -> list:
    rows = [["Quintetto", "Min", "PG", "+/-", "ORtg", "DRtg", "Net"]]
    for x in df.itertuples():
        rows.append([Paragraph(x.giocatori, S["cell"]), _fmt(x.minuti, 0), str(int(x.partite)),
                     _fmt(x.plus_minus, 0, True), _fmt(x.ortg), _fmt(x.drtg),
                     _fmt(x.net_rtg, signed=True)])
    return [_table(rows, [W - 84 * mm] + [14 * mm] * 6)]


def build_mia_squadra(ctx: Contesto, sid: int, obiettivi: dict | None = None,
                      giochi: list[dict] | None = None) -> bytes:
    """Tutte le voci della propria squadra: sintesi, aree da migliorare, quintetti, obiettivi,
    andamento, giocatori, rotazioni e momenti, avvisi; con giochi aggiunge il playbook."""
    _fonts()
    S = _styles()
    W = 186 * mm
    prof = ctx.profile
    camp = prof.set_index("squadra_id").loc[sid, "campionato_id"]
    lega = prof[prof["campionato_id"] == camp]
    me = lega.set_index("squadra_id").loc[sid]
    nome = me["squadra"]
    stag = config.STAGIONI.get(ctx.stagione, ctx.stagione)
    camp_nome = config.CAMPIONATI.get(camp, camp)
    pos = _rank(lega.assign(_v=lega["vinte"] - lega["perse_partite"]), sid, "_v")
    buf, doc = _documento(f"La mia squadra · {nome}")

    meta = (f"Record {int(me['vinte'])}-{int(me['perse_partite'])} · {pos.split(' ')[0]} "
            f"posto per saldo vittorie · report del {date.today().strftime('%d/%m/%Y')}")
    ng = ctx.next_game(sid)
    if ng:
        avv = ng["ospite"] if ng["casa_id"] == sid else ng["casa"]
        meta += (f"<br/>Prossima partita: {ng['giornata']}ª giornata, {_data_it(ng['data'])} "
                 f"contro {avv} ({'in casa' if ng['casa_id'] == sid else 'in trasferta'})")
    el = [_testata(f"La mia squadra · {camp_nome} {stag}", nome.upper(), meta, S, W),
          Spacer(1, 6)]
    el.append(_kpis([
        ("Net rating", _fmt(me["net_rtg"], signed=True), _rank(lega, sid, "net_rtg")),
        ("Rating offensivo", _fmt(me["ortg"]), _rank(lega, sid, "ortg")),
        ("Rating difensivo", _fmt(me["drtg"]), _rank(lega, sid, "drtg", True)),
        ("Ritmo", _fmt(me["pace"]), _rank(lega, sid, "pace")),
        ("Punto a punto", str(me["record_pp"]), "margine ≤ 5"),
        ("Fortuna", _fmt(me["fortuna"], signed=True), "vittorie reali − attese"),
    ], S, W))

    # ---- aree da migliorare
    pri = M.priorita(lega, sid)
    oc = ctx.origini_concesse
    oc = oc[oc["campionato_id"] == camp] if oc is not None and not oc.empty else oc
    rg = M.punti_regalati(lega, oc, sid)
    pl = ctx.players[ctx.players["campionato_id"] == camp]
    dett = M.dettagli_giocatori(pl, sid)
    el.append(_titolo("Su cosa concentrarsi", S))
    if int(me["partite"]) < 8:
        el.append(Paragraph(f"⚠ Pochi dati: {int(me['partite'])} partite giocate. Le differenze "
                            "dal campionato diventano affidabili dopo 8-10 giornate.", S["small"]))
    for i, v in enumerate(M.sintesi(pri, rg, dett), start=1):
        el.append(Paragraph(f"{i}. {_virgola(v)}", S["body"]))
    tutte = M.tutte_insieme(pri, float(me["net_rtg"]), float(me["pace"]))
    if tutte["voci"]:
        el.append(Paragraph(
            f"<b>Tutte insieme</b> portando alla media le {tutte['voci']} voci sotto la media: "
            f"circa {_fmt(tutte['vittorie'], 1, True)} vittorie su {M.PARTITE_STAGIONE} partite "
            f"({_fmt(tutte['guadagno_net'], 1, True)} punti ogni 100 possessi). Scenario "
            "migliore, da usare come obiettivo.", S["body"]))

    fmt = lambda c, v: _fmt(v, 2) if "ft" in c else _fmt(v, 1)
    rows = [["Voce", "Lato", "Voi", "Media", "Migliori", "Posizione", "Obiettivo", "Vittorie +"]]
    for x in pri.itertuples():
        rows.append([x.voce, x.lato, fmt(x.colonna, x.valore), fmt(x.colonna, x.media),
                     fmt(x.colonna, x.migliori), f"{x.posizione}° su {x.squadre}",
                     fmt(x.colonna, x.obiettivo), f"+{_fmt(x.vittorie, 1)}"])
    el += [_titolo("Priorità di lavoro · Four Factors", S),
           _table(rows, [44 * mm, 18 * mm] + [(W - 62 * mm) / 6] * 6, align_left=(1,)),
           Paragraph("Vittorie in più su 30 partite raggiungendo l'obiettivo: la media del "
                     "campionato per le voci sotto la media, il livello del miglior quarto per "
                     "le altre. Stima contro un avversario medio.", S["small"])]

    if not rg.empty:
        rows = [["Voce", "Voi", "Media", "Posizione"]] + [
            [x.voce, _fmt(x.valore), _fmt(x.media), f"{x.posizione}° su {x.squadre}"]
            for x in rg.itertuples()]
        el += [_titolo("Punti regalati · a partita", S),
               _table(rows, [80 * mm] + [(W - 80 * mm) / 3] * 3),
               Paragraph("Posizione: 1° = chi ne concede di meno.", S["small"])]
    if not dett.empty:
        rows = [["Giocatore", "Area", "Dettaglio", "Punti/partita"]] + [
            [x.giocatore, x.area, Paragraph(x.dettaglio, S["cell"]),
             _fmt(x.punti_pg, 1) if pd.notna(x.punti_pg) else "–"] for x in dett.itertuples()]
        el += [_titolo("Dettagli individuali · abitudini che costano punti", S),
               _table(rows, [38 * mm, 26 * mm, W - 88 * mm, 24 * mm], align_left=(1, 2))]

    # ---- quintetti
    migliori, peggiori, soglia = M.quintetti_estremi(ctx.lineups, sid)
    el.append(_titolo(f"Quintetti migliori e peggiori · almeno {_fmt(soglia, 0)} minuti insieme",
                      S))
    if migliori.empty and peggiori.empty:
        el.append(Paragraph("Servono più partite con quintetti verificati.", S["small"]))
    else:
        if int(me["partite"]) < 8:
            el.append(Paragraph("⚠ Inizio stagione: pochi minuti insieme per ogni quintetto, "
                                "indicazioni da confermare.", S["small"]))
        for df, testo in ((migliori, "Quelli che funzionano: da usare di più"),
                          (peggiori, "Quelli da rivedere")):
            el.append(Paragraph(f"<b>{testo}</b>", S["body"]))
            el += _quintetti(df, S, W) if not df.empty else [
                Paragraph("Nessuno.", S["small"])]
        el.append(Paragraph("Ordine per Net rating pesato sui minuti (Net × minuti / (minuti + "
                            "30)): pochi minuti fortunati non superano molti minuti solidi.",
                            S["small"]))
    lu = ctx.lineups
    if lu is not None and not lu.empty:
        usati = lu[lu["squadra_id"] == sid].head(8)
        if not usati.empty:
            el += [_titolo("Quintetti più usati", S)] + _quintetti(usati, S, W)

    qp = C.quando_perdono(ctx.bs, sid)
    if not qp.empty:
        qp = qp.head(6)
        rows = [["Voce", "Nelle vittorie", "Nelle sconfitte"]]
        for x in qp.itertuples():
            d = 2 if x.colonna in ("ft_rate", "opp_ft_rate") else 1
            rows.append([x.voce, _fmt(x.vittorie, d), _fmt(x.sconfitte, d)])
        el += [_titolo("Cosa cambia quando perdete", S),
               _table(rows, [90 * mm] + [(W - 90 * mm) / 2] * 2)]

    # ---- obiettivi, andamento, avversarie
    el.append(PageBreak())
    goals = {**AV.OBIETTIVI_DEFAULT, **(obiettivi or {})}
    form = AV.rolling_form(ctx.bs, sid)
    rows = [["Voce", "Obiettivo", "Stagione", "Ultime 5", "Raggiunto"]]
    for k, lab in OBIETTIVI.items():
        val = me.get(k)
        ult = form[k].tail(5).mean() if not form.empty and k in form else None
        alto = AV.OBIETTIVO_MEGLIO_ALTO[k]
        ok = pd.notna(val) and (val >= goals[k] if alto else val <= goals[k])
        d = 2 if "ft" in k else 1
        rows.append([lab, _fmt(goals[k], d), _fmt(val, d), _fmt(ult, d), "sì" if ok else "no"])
    el += [_titolo("Obiettivi Four Factors · impostati dallo staff", S),
           _table(rows, [70 * mm] + [(W - 70 * mm) / 4] * 4)]

    if not form.empty:
        rows = [["Giornata", "Data", "Avversaria", "Risultato", "ORtg", "DRtg", "Net",
                 "Net (media 5)"]]
        for x in form.itertuples():
            ris = f"{'V' if x.vinta else 'P'} {int(x.punti)}-{int(x.punti_subiti)}"
            rows.append([str(x.giornata), _data_it(x.data), x.avversario, ris, _fmt(x.ortg),
                         _fmt(x.drtg), _fmt(x.net_rtg, signed=True),
                         _fmt(x.net_rtg_mm, signed=True)])
        el += [_titolo("Andamento partita per partita", S),
               _table(rows, [16 * mm, 20 * mm, 56 * mm, 22 * mm] + [(W - 114 * mm) / 4] * 4,
                      align_left=(2, 3))]

    sp = AV.split_by_opponent(ctx.bs, sid)
    if not sp.empty:
        rows = [["Avversarie", "PG", "V", "P", "Punti", "Subiti", "ORtg", "DRtg", "Net"]]
        for x in sp.itertuples():
            rows.append([x.avversari, str(int(x.partite)), str(int(x.vinte)),
                         str(int(x.perse_partite)), _fmt(x.punti_pg), _fmt(x.punti_subiti_pg),
                         _fmt(x.ortg), _fmt(x.drtg), _fmt(x.net_rtg, signed=True)])
        el += [_titolo("Contro le forti e contro le deboli · divise per Net rating", S),
               _table(rows, [36 * mm] + [(W - 36 * mm) / 8] * 8)]

    # ---- giocatori
    gi = pl[pl["squadra_id"] == sid].sort_values("minuti", ascending=False)
    if not gi.empty:
        has_pm = "on_off" in gi.columns and gi["on_off"].notna().any()
        head = ["Giocatore", "PG", "Min", "Pt", "Rimb", "Ass", "Perse", "3PM-A", "TL%", "TS%",
                "USG%", "GmSc"] + (["+/-", "On-Off"] if has_pm else [])
        rows = [head]
        for p in gi.itertuples():
            row = [p.giocatore, str(p.partite), _fmt(p.minuti_pg), _fmt(p.punti_pg),
                   _fmt(p.rimb_tot_pg), _fmt(p.assist_pg), _fmt(p.perse_pg),
                   f"{_fmt(p.t3m_pg)}-{_fmt(p.t3a_pg)}", _fmt(p.tl_pct, 0),
                   _fmt(getattr(p, "ts_pct", None)), _fmt(getattr(p, "usg_pct", None)),
                   _fmt(p.game_score_pg)]
            if has_pm:
                row += [_fmt(p.plus_minus, 0, signed=True), _fmt(p.on_off, signed=True)]
            rows.append(row)
        el += [_titolo("Giocatori · medie a partita", S),
               _table(rows, [40 * mm] + [(W - 40 * mm) / (len(head) - 1)] * (len(head) - 1))]

    ct = ctx.clutch_teams
    if ct is not None and not ct.empty and sid in set(ct["squadra_id"]):
        c = ct.set_index("squadra_id").loc[sid]
        el += [_titolo("Finali punto a punto · ultimi 5' con scarto ≤ 5", S),
               Paragraph(f"Partite con finale punto a punto: {int(c['partite_clutch'])} · record "
                         f"{c['record_clutch']} · punti nei finali {int(c['punti_fatti'])}-"
                         f"{int(c['punti_subiti'])}", S["body"])]

    el += _approfondimenti(ctx, sid, ng, S, W)

    al = ctx.alerts
    if al is not None and not al.empty:
        mine = al[al["squadra_id"] == sid]
        if not mine.empty:
            el.append(_titolo("Avvisi", S))
            for x in mine.itertuples():
                chi = f"<b>{x.giocatore}</b>: " if isinstance(x.giocatore, str) else ""
                el.append(Paragraph(f"• {chi}{x.testo}", S["body"]))

    if giochi:
        el += [PageBreak()] + L.flowables(giochi, S, W, f"GIOCHI DI {nome.upper()} · "
                                                        "disegnati dallo staff, fase per fase")

    piede = _piede(f"{nome} · la mia squadra")
    doc.build(unisci_titoli(el), onFirstPage=piede, onLaterPages=piede)
    return buf.getvalue()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="PDF completo della propria squadra")
    ap.add_argument("squadra", help="nome (anche parziale) della squadra")
    ap.add_argument("--out", default=str(config.ROOT / "reports" / "pdf"))
    args = ap.parse_args(argv)
    ctx = open_readonly()
    p = ctx.profile
    trovate = p[p["squadra"].str.contains(args.squadra, case=False)]
    if trovate.empty:
        print(f"Squadra non trovata: {args.squadra}", file=sys.stderr)
        return 1
    r = trovate.iloc[0]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"mia_squadra_{slug(r['squadra'])}.pdf"
    f.write_bytes(build_mia_squadra(ctx, int(r["squadra_id"])))
    print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
