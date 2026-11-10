"""Statistiche avanzate del giocatore: PIE, voci, posizione nel campionato, pagina del report."""

import pandas as pd

from basket import avanzate as AV


def _riga(**k):
    base = dict(punti=0, t2m=0, t2a=0, t3m=0, t3a=0, tlm=0, tla=0, rimb_dif=0, rimb_off=0, assist=0,
                recuperate=0, stoppate=0, falli_commessi=0, perse=0)
    base.update(k)
    return base


def test_pie_e_la_parte_del_giocatore_sul_totale_della_partita():
    # squadra 1: 20 punti (10 canestri da 2 su 20), avversari: 10 punti (5 su 20)
    sq = _riga(punti=20, t2m=10, t2a=20)
    opp = {f"opp_{k}": v for k, v in _riga(punti=10, t2m=5, t2a=20).items()}
    bs = pd.DataFrame([{**sq, **opp, "partita_id": "p", "squadra_id": 1, "affidabile": True}])
    bg = pd.DataFrame([{**_riga(punti=10, t2m=5, t2a=8), "partita_id": "p", "squadra_id": 1,
                        "giocatore_id": "a", "giocata": True, "affidabile": True}])
    # numeratori: giocatore 10+5-8 = 7; partita (20+10-20) + (10+5-20) = 5
    assert abs(AV.pie(bg, bs)["pie"].iloc[0] - 100 * 7 / 5) < 1e-9


def test_quindici_voci_in_cinque_famiglie():
    assert len(AV.GRUPPI) == 5 and all(len(v) == 3 for _, _, v in AV.GRUPPI)
    sigle = {v.sigla for v in AV.VOCI}
    assert {"OFFRTG", "DEFRTG", "NETRTG", "AST%", "AST/TO", "AST RATIO", "OREB%", "DREB%", "REB%", "EFG%",
            "TS%", "TO RATIO", "USG%", "PIE", "PACE"} == sigle
    assert AV._livello(90, 1) == "tra i migliori" and AV._livello(10, 1) == "tra i più deboli"
    assert AV._livello(90, 0) == "alto"                    # utilizzo e ritmo descrivono, non giudicano


def test_scheda_e_pagina_del_report_sui_dati_veri():
    from basket import config, db
    from basket.contesto import Contesto
    if not config.DB_PATH.exists():
        return
    ctx = Contesto(db.connect(config.DB_PATH, readonly=True), config.STAGIONE)
    t = AV.tabella(ctx)
    r = t[t["minuti_pg"] >= 20].sort_values("pie", ascending=False).iloc[0]
    s = AV.scheda(ctx, int(r.squadra_id), r.giocatore_id)
    righe = [x for g in s["gruppi"] for x in g["righe"]]
    assert len(righe) == 15 and all(0 <= x["pct"] <= 100 for x in righe if x["pct"] is not None)
    pie = next(x for x in righe if x["sigla"] == "PIE")
    assert pie["pct"] >= 90 and pie["livello"] == "tra i migliori"
    # difesa e palle perse: più basso è meglio
    peggiore = t[t["minuti_pg"] >= 15].sort_values("to_ratio", ascending=False).iloc[0]
    s2 = AV.scheda(ctx, int(peggiore.squadra_id), peggiore.giocatore_id)
    assert next(x for g in s2["gruppi"] for x in g["righe"] if x["sigla"] == "TO RATIO")["pct"] < 20
    assert AV.scheda(ctx, -1, "nessuno") is None
    assert not AV.tabella_squadra(ctx, int(r.squadra_id)).empty
    from basket import report_giocatore as RG
    pdf = RG.build(ctx, int(r.squadra_id), r.giocatore_id, None, foto=False)
    assert pdf[:4] == b"%PDF" and pdf.count(b"/Type /Page\n") + pdf.count(b"/Type /Page ") >= 0
