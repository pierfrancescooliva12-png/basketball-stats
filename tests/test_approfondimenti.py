"""Nuove analisi: rotazioni, taglia dei quintetti, momenti, presenze, riposo e trasferte,
confronto tra categorie, frasi di sintesi, report post-partita e individuale."""

import pandas as pd
import pytest

from basket import approfondimenti as X
from basket import luoghi
from tests.test_pbp import Client


@pytest.fixture(autouse=True)
def _cronaca_tmp(tmp_path, monkeypatch):
    from basket import config
    monkeypatch.setattr(config, "CRONACA_DIR", tmp_path / "cronaca")


@pytest.fixture
def ctx(tmp_path):
    from basket import db, update
    from basket.contesto import Contesto
    conn = db.connect(tmp_path / "t.sqlite")
    update.update_league(conn, Client(), "ita2", "x2627", {2})
    return Contesto(conn, "x2627")


def _stint(squadra, partita, inizio, fine, quintetto, pf=0, ps=0):
    return {"campionato_id": "ita2", "squadra_id": squadra, "partita_id": partita,
            "inizio": inizio, "fine": fine, "quintetto": quintetto, "punti_fatti": pf,
            "punti_subiti": ps, "poss_fatti": (fine - inizio) / 30,
            "poss_subiti": (fine - inizio) / 30, "secondi": fine - inizio}


def test_rotazioni_griglia_e_titolari():
    q1, q2 = "a,b,c,d,e", "a,b,c,d,f"
    st = pd.DataFrame([_stint(1, "p1", 0, 600, q1), _stint(1, "p1", 600, 2400, q2),
                       _stint(1, "p2", 0, 2400, q1)])
    r = X.rotazioni(st)
    g = r["griglia"].set_index(["giocatore_id", "minuto"])["quota"]
    assert g[("a", 0)] == 100                       # sempre in campo
    assert g[("e", 15)] == 50                       # in campo solo nella seconda partita
    assert g[("f", 15)] == 50
    gi = r["giocatori"].set_index("giocatore_id")
    assert gi.loc["e", "quota_titolare"] == 100 and gi.loc["f", "quota_titolare"] == 0
    assert gi.loc["f", "minuto_ingresso"] == 10
    sq = r["squadre"].iloc[0]
    assert sq["quota_quintetto_base"] == 100 and sq["minuto_primo_cambio"] == 25


def test_taglia_quintetti_soglie_e_rendimento():
    alti = {g: 200 for g in "abcde"} | {g: 185 for g in "fghij"} | {g: 193 for g in "klmno"}
    st = pd.DataFrame([_stint(1, "p1", 0, 800, "a,b,c,d,e", 30, 10),
                       _stint(1, "p1", 800, 1600, "f,g,h,i,j", 10, 30),
                       _stint(1, "p1", 1600, 2400, "k,l,m,n,o", 20, 20)])
    t = X.taglia_quintetti(st, alti).set_index("taglia")
    assert t.loc["Grande", "net_rtg"] > 0 > t.loc["Piccolo", "net_rtg"]
    assert t["quota_minuti"].sum() == pytest.approx(100)


def test_luoghi_e_distanze():
    assert luoghi.citta_palazzetto("PalaDozza - Bologna") == "Bologna"
    assert luoghi.citta_palazzetto("Vitrifrigo Arena") == "Pesaro"
    assert luoghi.citta_palazzetto("Palasport") is None
    assert 60 < luoghi.distanza_km("Bologna", "Forlì") < 100
    assert luoghi.distanza_km("Bologna", "Atlantide") is None


def test_presenze_conta_le_partite_saltate():
    bs = pd.DataFrame({"squadra_id": [1] * 4, "partita_id": list("wxyz"),
                       "data": ["2026-10-01", "2026-10-08", "2026-10-15", "2026-10-22"]})
    bg = pd.DataFrame({"squadra_id": [1, 1, 1], "giocatore_id": ["g"] * 3,
                       "partita_id": ["w", "y", "z"], "minuti": [20, 0, 25]})
    p = X.presenze(bg, bs).iloc[0]
    assert p["saltate"] == 1 and p["senza_entrare"] == 1 and p["presenze_pct"] == 75


def test_fattori_categoria_e_proiezione():
    righe = []
    for i in range(15):
        base = {"giocatore_id": f"g{i}", "minuti": 600, "minuti_pg": 25, "partite": 20,
                "ts_pct": 55.0, "usg_pct": 22.0, "rimb_tot_p40": 8.0, "assist_p40": 4.0,
                "game_score_p40": 15.0}
        righe.append(base | {"stagione": "x2425", "categoria": "B Nazionale", "punti_p40": 20.0})
        righe.append(base | {"stagione": "x2526", "categoria": "A2", "punti_p40": 16.0,
                             "ts_pct": 53.0})
    lines = pd.DataFrame(righe)
    f = X.fattori_categoria(lines).set_index("statistica")
    assert f.loc["punti_p40", "valore"] == pytest.approx(0.8)
    assert f.loc["ts_pct", "valore"] == pytest.approx(-2.0)
    assert f.loc["punti_p40", "coppie"] == 15
    pr = X.proiezione_a2(lines[lines["categoria"] == "B Nazionale"], f.reset_index())
    assert pr["punti_p40_a2"].iloc[0] == pytest.approx(16.0)


def test_frase_squadra_e_posizione():
    prof = pd.DataFrame({"squadra_id": range(10), "ortg": range(100, 110),
                         "drtg": [100] * 10, "pace": [70] * 10})
    assert "attacco tra i più efficienti" in X.frase_squadra(prof, 9)
    assert "attacco poco efficiente" in X.frase_squadra(prof, 0)
    s = prof.set_index("squadra_id")["ortg"]
    assert X.posizione(s, 9) == (1, 10)
    assert X.posizione(s, 9, piu_alto_meglio=False) == (10, 10)


def test_momenti_e_calendario_su_partita_reale(ctx):
    m = ctx.momenti
    assert set(m["momento"]) == set(X.MOMENTI)
    assert (m["partite"] == 1).all()
    cal = ctx.calendario_fisico
    assert {"giorni_riposo", "km", "riposo", "viaggio"} <= set(cal.columns)
    oc = ctx.origini_concesse
    tot = ctx.origins.set_index("squadra_id")["punti_da_perse"]
    conc = oc.set_index("squadra_id")["concessi_da_perse"]
    assert conc[10050] == tot[100118] and conc[100118] == tot[10050]


def test_report_post_partita_e_giocatore(ctx):
    from basket import report_extra as R
    pid = R.ultima_partita(ctx, 10050)
    r = R.riepilogo_partita(ctx, 10050, pid)
    assert r["vinta"] and int(r["riga"]["punti"]) == 80
    assert r["frasi"] and len(r["fattori"]) == 8
    pdf = R.build_post_partita(ctx, 10050)
    assert pdf[:4] == b"%PDF" and len(pdf) > 10_000
    gid = ctx.players[ctx.players["squadra_id"] == 10050].sort_values("minuti").iloc[-1]
    pdf = R.build_giocatore(ctx, gid["giocatore_id"], 10050)
    assert pdf[:4] == b"%PDF"
