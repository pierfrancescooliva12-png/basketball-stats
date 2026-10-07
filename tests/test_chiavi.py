"""Chiavi per vincere: leve della partita, ritmo, quando perdono, giocatori chiave."""

import numpy as np
import pandas as pd
import pytest

from basket import chiavi as C


def _profilo():
    righe = []
    for i in range(10):
        righe.append({"squadra_id": i, "campionato_id": "ita2", "efg_pct": 50.0 + i * 0.5,
                      "opp_efg_pct": 52.0, "tov_pct": 14.0, "opp_tov_pct": 14.0,
                      "orb_pct": 28.0, "drb_pct": 72.0, "ft_rate": 0.23, "opp_ft_rate": 0.23,
                      "partite": 20})
    p = pd.DataFrame(righe)
    p.loc[p["squadra_id"] == 1, "opp_efg_pct"] = 56.0      # la nostra difesa concede molto
    return p


def _forze():
    return pd.DataFrame({"squadra_id": range(10), "forza": [0.0] * 10, "pace_stima": [70.0] * 10})


def test_leve_obiettivo_e_guadagno():
    lv = C.leve(_profilo(), _forze(), mia=1, avv=9, casa_mia=True, hca=3.0)
    assert len(lv) == 8 and (lv["guadagno"] >= 0).all()
    assert lv["guadagno"].is_monotonic_decreasing
    top = lv.iloc[0]
    # tiro concesso: loro attaccano bene (54,5) contro una difesa che concede 56 → a sfavore
    assert top["fattore"] == "Tiro concesso (eFG%)" and top["situazione"] == "a vostro sfavore"
    assert top["obiettivo"] == pytest.approx(lv["media"].iloc[0])
    assert top["prob_obiettivo"] > top["prob_ora"]
    assert "media del campionato" in C.frase_leva(top, "Avv")
    # con poche partite lo scostamento viene avvicinato alla media
    p2 = _profilo().assign(partite=2)
    lv2 = C.leve(p2, _forze(), mia=1, avv=9, casa_mia=True, hca=3.0)
    assert lv2["guadagno"].max() < lv["guadagno"].max()


def test_ritmo_favorisce_la_sfavorita_se_lento():
    f = _forze()
    f.loc[f["squadra_id"] == 9, "forza"] = 8.0
    rt = C.ritmo(f, mia=1, avv=9, casa_mia=False, hca=3.0)
    assert rt.loc[rt["variazione"] == 0, "prob"].iloc[0] < 50
    assert rt["prob"].is_monotonic_decreasing          # più possessi, meno sorprese


def test_quando_perdono():
    righe = []
    for k in range(10):
        vinta = k % 2 == 0
        righe.append({"squadra_id": 5, "vinta": int(vinta), "efg_pct": 56.0 if vinta else 46.0,
                      "opp_efg_pct": 50.0, "tov_pct": 14.0, "opp_tov_pct": 14.0, "orb_pct": 28.0,
                      "drb_pct": 72.0, "ft_rate": 0.2, "opp_ft_rate": 0.2, "pace": 70.0,
                      "t2a": 40, "t3a": 25})
    qp = C.quando_perdono(pd.DataFrame(righe), 5)
    assert qp.iloc[0]["voce"] == "Tiro (eFG%)" and qp.iloc[0]["differenza"] == pytest.approx(-10)
    assert C.quando_perdono(pd.DataFrame(righe[:4]), 5).empty


def _partite(n=16, effetto=8.0):
    """Squadra 1: quando il giocatore 'a' segna almeno 15 punti fa meglio del previsto."""
    bt, bg = [], []
    rng = np.random.default_rng(1)
    for k in range(n):
        alto = k % 2 == 0
        pid = f"p{k}"
        bt.append({"partita_id": pid, "casa_id": 1 if k % 3 else 2,
                   "ospite_id": 2 if k % 3 else 1, "margine_previsto": 0.0,
                   "margine_reale": (effetto if alto else -effetto) * (1 if k % 3 else -1)})
        data = f"2025-10-{k + 1:02d}"
        bg.append({"partita_id": pid, "squadra_id": 1, "giocatore_id": "a", "data": data,
                   "minuti": 30, "punti": 20 if alto else 8, "assist": 2, "rimb_tot": 3})
        bg.append({"partita_id": pid, "squadra_id": 1, "giocatore_id": "b", "data": data,
                   "minuti": 25, "punti": 6 if alto else 14, "assist": 1,
                   "rimb_tot": int(rng.integers(2, 5))})
    return pd.DataFrame(bt), pd.DataFrame(bg)


def test_giocatori_chiave_scarto_e_restringimento():
    bt, bg = _partite()
    gc = C.giocatori_chiave(bg, bt, 1, {"a": "Rossi", "b": "Bianchi"})
    r = gc[(gc["giocatore_id"] == "a") & (gc["colonna"] == "punti")].iloc[0]
    assert r["soglia"] == 14 and r["partite_sotto"] == 8 and r["partite_sopra"] == 8
    assert r["scarto_sopra"] == pytest.approx(8) and r["scarto_sotto"] == pytest.approx(-8)
    assert 0 < r["effetto"] < 16                          # ristretto verso zero
    assert r["compensa"] == "Bianchi" and r["compensa_punti"] == pytest.approx(8)
    pr = C.prob_giocatori(gc, 0.0, avversario=True)
    ra = pr[(pr["giocatore_id"] == "a") & (pr["colonna"] == "punti")].iloc[0]
    assert ra["prob_scenario"] > 50                        # tenerlo sotto aiuta l'avversaria
    assert "Tenere Rossi sotto 14 punti" in C.frase_giocatore(ra, True)


def test_giocatori_chiave_pochi_dati():
    bt, bg = _partite(n=6)
    assert C.giocatori_chiave(bg, bt, 1).empty


def test_pdf_con_chiavi(tmp_path, monkeypatch):
    from basket import config, db, update
    from basket.contesto import Contesto
    from basket.report_pdf import build_pdf
    from tests.test_pbp import Client
    monkeypatch.setattr(config, "CRONACA_DIR", tmp_path / "cronaca")
    conn = db.connect(tmp_path / "t.sqlite")
    update.update_league(conn, Client(), "ita2", "x2627", {2})
    pdf = build_pdf(Contesto(conn, "x2627"), 10050, 100118)
    assert pdf[:4] == b"%PDF" and len(pdf) > 10_000


def test_chiavi_tutte_insieme_e_frasi():
    lv = C.leve(_profilo(), _forze(), mia=1, avv=9, casa_mia=True, hca=3.0)
    c = C.combinata(lv, pd.DataFrame())
    assert c["chiavi"] == 3 and c["prob_tutte"] >= lv.head(3)["prob_obiettivo"].max()
    assert c["punti"] == pytest.approx(lv.head(3)["d_margine"].sum())
    assert "tutte e 3 le chiavi" in C.frase_combinata(c)
    r = lv[(lv["chiave"] == "tov") & (lv["lato"] == "In difesa")].iloc[0]
    assert "costringere Avv ad almeno" in C.frase_leva(r, "Avv")
