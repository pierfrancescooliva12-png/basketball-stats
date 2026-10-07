"""Validazione retrospettiva, previsione spiegata e simulatore "e se"."""

import pandas as pd
import pytest

from basket import previsioni as F
from basket import validazione as V


def _bt(prob, vince, margine_prev=None, margine_reale=None):
    n = len(prob)
    return pd.DataFrame({
        "partita_id": [f"p{i}" for i in range(n)], "stagione": "x2526",
        "campionato_id": "ita2", "giornata": range(1, n + 1),
        "data": [f"2025-10-{i + 1:02d}" for i in range(n)],
        "casa_id": [1, 2] * (n // 2) + [1] * (n % 2), "ospite_id": [2, 1] * (n // 2) + [2] * (n % 2),
        "prob_casa": prob, "vince_casa": vince,
        "margine_previsto": margine_prev or [0.0] * n,
        "margine_reale": margine_reale or [0.0] * n})


def test_metriche_e_calibrazione():
    bt = _bt([0.9, 0.9, 0.2, 0.55], [True, True, False, False],
             margine_prev=[10, 10, -5, 2], margine_reale=[12, 6, -5, -4])
    m = V.metriche(bt)
    assert m["partite"] == 4 and m["accuratezza"] == pytest.approx(75)
    assert m["brier"] == pytest.approx((0.01 + 0.01 + 0.04 + 0.3025) / 4)
    assert m["errore_margine"] == pytest.approx(3.0)
    assert m["rif_sempre_casa"] == pytest.approx(50)
    c = V.calibrazione(bt).set_index("fascia")
    assert c.loc["90–100%", "partite"] == 2 and c.loc["80–90%", "reale"] == 100
    assert c.loc["50–60%", "reale"] == 0           # favorita al 55% che ha perso
    assert V.metriche(bt.iloc[:0]) == {}


def test_fasi_e_gruppi():
    bt = _bt([0.6] * 20, [True] * 20)
    fasi = V.per_gruppo(bt.assign(fase=V.fase_stagione(bt)), "fase")
    assert list(fasi["fase"]) == ["Giornate 1-5", "Giornate 6-15", "Dalla 16ª"]
    assert list(fasi["partite"]) == [5, 10, 5]


def _forze():
    return pd.DataFrame({
        "squadra_id": [1, 2], "forza": [4.0, -2.0], "pace_stima": [72.0, 68.0],
        "parte_precedente": [1.0, 0.5], "parte_attacco": [2.0, -1.5],
        "parte_difesa": [1.0, -1.0]})


def test_spiega_somma_e_segni():
    sp = F.spiega(_forze(), 1, 2, hca=3.0).set_index("fattore")
    assert sp["punti"].sum() == pytest.approx(F.predict(_forze(), 1, 2, 3.0)["margine"])
    assert (sp["probabilita"] > 0).all()
    assert sp.index[0] in ("Attacco", "Fattore campo")
    sp = F.spiega(_forze(), 1, 2, hca=3.0, extra={"Assenze": -4.0}).set_index("fattore")
    assert sp.loc["Assenze", "probabilita"] < 0


def test_scenario_assenze_e_campo_neutro():
    players = pd.DataFrame({
        "giocatore_id": ["a", "b", "c"], "squadra_id": [1, 1, 2],
        "campionato_id": "ita2", "minuti_pg": [32.0, 20.0, 30.0],
        "game_score_p40": [25.0, 12.0, 15.0], "on_off": [10.0, None, 3.0],
        "minuti_campo": [800.0, None, 600.0]})
    imp = F.impatto_giocatori(players).set_index("giocatore_id")
    assert imp.loc["a", "impatto"] == pytest.approx(5.0)          # 10 · 800/(800+800)
    assert imp.loc["b", "fonte_impatto"] == "Box score"
    r = F.scenario(_forze(), players, 1, 2, 3.0, assenti_casa=["a"])
    assert r["delta_casa"] == pytest.approx(-5.0 * 0.8)
    assert r["scenario"]["prob_casa"] < r["base"]["prob_casa"]
    assert "Assenze" in set(r["spiegazione"]["fattore"])
    n = F.scenario(_forze(), players, 1, 2, 3.0, campo_neutro=True)
    assert n["scenario"]["margine"] == pytest.approx(n["base"]["margine"] - 3.0)
    s = F.scenario(_forze(), players, 1, 2, 3.0, correzione_ospite=6.0)
    assert s["scenario"]["prob_casa"] < s["base"]["prob_casa"]


def test_backtest_e_registro(tmp_path):
    from basket import db, update
    from tests.test_pbp import Client
    conn = db.connect(tmp_path / "t.sqlite")
    update.update_league(conn, Client(), "ita2", "x2627", {2})
    bt = V.backtest(conn)
    assert len(bt) == 1 and 0 < bt["prob_casa"].iloc[0] < 1
    assert bt["partite_note"].iloc[0] == 0      # nessuna partita precedente
    V.registra(conn, "x2627")
    assert "prob_casa" in V.registro(conn).columns
