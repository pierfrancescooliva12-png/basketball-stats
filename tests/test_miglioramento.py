"""Aree da migliorare della propria squadra."""

import pandas as pd
import pytest

from basket import miglioramento as M


def _profilo():
    righe = []
    for i in range(8):
        righe.append({"squadra_id": i, "efg_pct": 52.0 + 0.2 * i, "tov_pct": 14.0, "orb_pct": 28.0,
                      "ft_rate": 0.23, "opp_efg_pct": 51.0, "opp_tov_pct": 14.0,
                      "drb_pct": 72.0, "opp_ft_rate": 0.23, "pace": 70.0, "net_rtg": 0.0,
                      "partite": 20, "tla": 400, "tlm": 300, "perse": 240,
                      "falli_commessi": 400})
    p = pd.DataFrame(righe)
    p.loc[0, "opp_efg_pct"] = 55.0          # la difesa della squadra 0 concede molto
    p.loc[0, "tlm"] = 240
    return p


def test_priorita_ordine_e_vittorie():
    pri = M.priorita(_profilo(), 0)
    top = pri.iloc[0]
    assert top["voce"] == "Tiro concesso (eFG%)" and top["sotto_media"]
    assert top["obiettivo"] == pytest.approx(51.5) and top["vittorie"] > 0
    assert pri.loc[pri["voce"] == "Tiro (eFG%)", "posizione"].iloc[0] == 8
    sopra = M.priorita(_profilo(), 7)
    r = sopra[sopra["voce"] == "Tiro (eFG%)"].iloc[0]
    assert not r["sotto_media"] and r["obiettivo"] == r["migliori"]


def test_punti_regalati():
    conc = pd.DataFrame({"squadra_id": range(8), "concessi_da_perse_pg": [15.0] + [10.0] * 7})
    rg = M.punti_regalati(_profilo(), conc, 0)
    assert rg.iloc[0]["voce"] == "Punti concessi dalle vostre palle perse"
    tl = rg[rg["voce"] == "Tiri liberi sbagliati a partita"].iloc[0]
    assert tl["valore"] == pytest.approx(8.0) and tl["posizione"] == 8


def test_dettagli_giocatori():
    base = {"squadra_id": 1, "minuti_pg": 25.0, "tla": 80, "tlm": 60, "t3a": 100, "t3m": 35,
            "tla_pg": 1.0, "tl_pct": 75.0, "t3a_pg": 2.0, "t3_pct": 35.0, "perse_pg": 1.0,
            "fga_pg": 10.0, "tov_pct": 12.0, "ts_pct": 55.0, "usg_pct": 18.0,
            "falli_commessi_p40": 3.0}
    righe = [base | {"giocatore_id": f"g{i}", "giocatore": f"G{i}", "squadra_id": 2}
             for i in range(6)]
    righe.append(base | {"giocatore_id": "x", "giocatore": "Rossi", "tla_pg": 4.0,
                         "tl_pct": 50.0, "usg_pct": 28.0, "ts_pct": 45.0,
                         "falli_commessi_p40": 6.0})
    d = M.dettagli_giocatori(pd.DataFrame(righe), 1)
    assert set(d["area"]) == {"Tiri liberi", "Scelta di tiro", "Falli"}
    tl = d[d["area"] == "Tiri liberi"].iloc[0]
    assert tl["punti_pg"] == pytest.approx((0.75 - 0.5) * 4)
    assert any("Rossi" in x for x in M.sintesi(M.priorita(_profilo(), 0), pd.DataFrame(), d))
