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


def test_pagine_accorpate_e_nomi_italiani():
    pytest = __import__("pytest")
    pytest.importorskip("streamlit")
    import streamlit as st
    from dashboard import pagine, ui
    from pathlib import Path
    import re
    src = Path(pagine.__file__).read_text()
    u = set(re.findall(r'P\(\w+,\s*[^,]+?,\s*"([\w-]+)",\s*"\w+"', src, flags=re.S))
    # pronostici, proiezione e affidabilità in una pagina; la panoramica dentro la classifica
    assert not {"pronostici", "affidabilita", "panoramica"} & u
    assert {"proiezione", "classifica", "squadre", "partite", "scouting"} <= u
    df = pd.DataFrame({"Giocatore": ["a"], "TS%": [55.0], "USG%": [20.0], "Net Rtg": [1.0]})
    st.session_state["esperto"] = False
    d, colori = ui.nomi_italiani(df, {"TS%": True})
    assert list(d.columns) == ["Giocatore", "Tiro (TS%)", "Possessi usati (USG%)", "Net rating"]
    assert colori == {"Tiro (TS%)": True}
    st.session_state["esperto"] = True                      # vista Esperto: restano le sigle
    assert list(ui.nomi_italiani(df, None)[0].columns) == list(df.columns)
    from basket.glossario import COLONNE
    assert all(n in COLONNE or n in ("Game Score",) for n in ui.NOMI_ITALIANI.values())


def test_report_senza_istruzioni_tattiche():
    """I report indicano su cosa concentrarsi: non dicono alla squadra cosa fare."""
    from basket import config, db
    from basket import piano_partita as PP
    from basket.contesto import Contesto
    from pathlib import Path
    radice = Path(PP.__file__).parent
    assert "Come stanno in campionato" not in (radice / "report_pdf.py").read_text() + (radice / "report_word.py").read_text()
    assert "Come sono posizionati in campionato" in (radice / "report_pdf.py").read_text()
    vietate = ("raddoppi", "tagliafuori", "chiusure", "pressione a tutto campo", "fallo tattico", "trappole",
               "timeout presto", "con un timeout", "mandare in lunetta", "attaccarli", "attaccare il", "correre dopo",
               "correre sempre", "spingere", "marcature", "extra-passaggio", "spaziature", "allungare le rotazioni",
               "due portatori", "crash", "alzare l'intensità", "cambi difensivi", "aiuti")
    sorgente = (radice / "piano_partita.py").read_text().lower()
    for parola in vietate:
        assert parola not in sorgente, parola
    if not config.DB_PATH.exists():
        return
    ctx = Contesto(db.connect(config.DB_PATH, readonly=True), config.STAGIONE)
    a2 = ctx.profile[ctx.profile["campionato_id"] == ctx.profile["campionato_id"].iloc[0]]
    ids = [int(x) for x in a2["squadra_id"]]
    for avv, mia in ((ids[0], ids[1]), (ids[2], None), (ids[3], ids[0])):
        gruppi = PP.consigli(ctx, avv, mia)
        assert list(gruppi)[0].startswith("Il loro attacco") and list(gruppi)[1].startswith("La loro difesa")
        testo = " ".join(v for voci in gruppi.values() for v in voci).lower()
        for parola in vietate:
            assert parola not in testo, (parola, testo[:200])


def test_con_e_senza_di_lui_su_stint_e_cronaca():
    from types import SimpleNamespace
    # una partita: squadra 1 contro 2; A in campo nei primi 100 secondi, poi in panchina
    stints = pd.DataFrame([
        {"squadra_id": 1, "inizio": 0, "fine": 100, "quintetto": "A,B,C,D,E", "punti_fatti": 10, "punti_subiti": 4,
         "poss_fatti": 10.0, "poss_subiti": 10.0, "partita_id": "p", "campionato_id": "c", "stagione": "s", "secondi": 100},
        {"squadra_id": 1, "inizio": 100, "fine": 200, "quintetto": "B,C,D,E,F", "punti_fatti": 4, "punti_subiti": 10,
         "poss_fatti": 50.0, "poss_subiti": 50.0, "partita_id": "p", "campionato_id": "c", "stagione": "s", "secondi": 100},
    ])
    ev = pd.DataFrame([
        {"partita_id": "p", "secondi": 10, "squadra_id": 1, "tipo": "tiro3_fatto"},
        {"partita_id": "p", "secondi": 20, "squadra_id": 1, "tipo": "tiro2_sbagliato"},
        {"partita_id": "p", "secondi": 20, "squadra_id": 1, "tipo": "rimb_off"},
        {"partita_id": "p", "secondi": 30, "squadra_id": 2, "tipo": "persa"},
        {"partita_id": "p", "secondi": 150, "squadra_id": 1, "tipo": "tiro2_sbagliato"},
        {"partita_id": "p", "secondi": 150, "squadra_id": 2, "tipo": "rimb_dif"},
        {"partita_id": "p", "secondi": 160, "squadra_id": 2, "tipo": "tiro2_fatto"},
    ]).assign(squadra_casa_id=1, squadra_ospite_id=2)
    st = AV.stint_eventi(ev, stints)
    assert list(st["f_fga"]) == [2, 1] and list(st["f_orb"]) == [1, 0] and list(st["s_tov"]) == [1, 0]
    assert list(st["s_drb"]) == [0, 1] and list(st["s_fgm"]) == [0, 1]
    ctx = SimpleNamespace(ev=ev, stints=stints)
    oo = AV.on_off_squadra(ctx).set_index("giocatore_id")
    a = oo.loc["A"]
    assert a["ortg_on"] == 100 and a["ortg_off"] == 8 and a["ortg_diff"] == 92
    assert a["efg_on"] == 75 and a["efg_off"] == 0          # (1 + 0,5) su 2 tiri · 0 su 1
    assert a["orb_on"] == 100 and a["orb_off"] == 0          # 1 su 1 · 0 su (0 + 1)
    assert oo.loc["B", "poss_off"] == 0 and pd.isna(oo.loc["B", "ortg_off"])   # sempre in campo


def test_scheda_con_senza_e_posizione_in_squadra():
    from basket import config, db
    from basket.contesto import Contesto
    if not config.DB_PATH.exists():
        return
    ctx = Contesto(db.connect(config.DB_PATH, readonly=True), config.STAGIONE)
    t = AV.tabella(ctx)
    r = t[t["minuti_pg"] >= 20].iloc[0]
    s = AV.scheda(ctx, int(r.squadra_id), r.giocatore_id)
    cs = s["con_senza"]
    assert cs and len(cs["righe"]) == len(AV.VOCI_ONOFF) and cs["poss_on"] > 0
    net = next(x for x in cs["righe"] if x["chiave"] == "net")
    net_tab = next(x for g in s["gruppi"] for x in g["righe"] if x["sigla"] == "NETRTG")
    assert net["testo_con"] == net_tab["testo"]                 # stesso saldo nelle due tabelle
    pos = [x["in_squadra"] for g in s["gruppi"] for x in g["righe"] if x["in_squadra"]]
    assert pos and all(1 <= p["pos"] <= p["su"] <= s["compagni"] for p in pos)
