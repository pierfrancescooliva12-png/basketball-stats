import pandas as pd
import pytest

from basket import previsioni as F


def test_predict_symmetry_and_home_advantage():
    forze = pd.DataFrame({"squadra_id": [1, 2], "forza": [5.0, 5.0], "pace_stima": [70, 70]})
    p = F.predict(forze, 1, 2, hca=3.0)
    assert p["prob_casa"] > 0.5 and p["margine"] == pytest.approx(3.0)
    p0 = F.predict(forze, 1, 2, hca=0.0)
    assert p0["prob_casa"] == pytest.approx(0.5)
    forte = pd.DataFrame({"squadra_id": [1, 2], "forza": [15.0, -15.0], "pace_stima": [70, 70]})
    assert F.predict(forte, 1, 2, 0)["prob_casa"] > 0.95


def test_pronostico_totali_e_intervalli():
    import pandas as pd
    from basket import previsioni as F
    forze = pd.DataFrame({"squadra_id": [1, 2, 3], "forza": [6.0, -6.0, 0.0], "pace_stima": [74.0, 70.0, 72.0],
                          "ortg": [112.0, 100.0, 106.0], "drtg": [102.0, 110.0, 106.0], "partite": [20, 20, 20],
                          "incertezza": [2.5, 2.5, 2.5]})
    p = F.pronostico(forze, 1, 2, 3.0)
    assert p["prob_casa"] > 0.8 and p["margine_da"] < p["margine"] < p["margine_a"]
    assert abs((p["margine_a"] - p["margine_da"]) - 2 * F.Z80 * F.sigma_margine(20)) < 1e-9   # da metà stagione più stretti
    assert p["margine_da"] < p["margine_da50"] < p["margine_a50"] < p["margine_a"]
    inizio = F.pronostico(forze.assign(partite=2), 1, 2, 3.0)
    assert inizio["margine_a"] - inizio["margine_da"] > p["margine_a"] - p["margine_da"]
    assert 140 < p["totale"] < 175 and p["da"] < p["totale"] < p["a"]
    assert abs(p["punti_casa"] - p["punti_ospite"] - p["margine"]) < 1e-9
    assert p["affidabilita"] == "alta" and p["scarto_10_casa"] > p["scarto_10_ospite"]
    pari = F.pronostico(forze, 3, 3, 0.0)
    assert abs(pari["prob_casa"] - 0.5) < 1e-9


def test_correzione_fortuna():
    import pandas as pd
    from basket import previsioni as F
    # stessa squadra, due partite: una con il 60% da 3, una con il 20%; la correzione avvicina i punti
    b = pd.DataFrame({"squadra_id": [1, 1], "punti": [100, 70], "punti_subiti": [80, 80], "opp_punti": [80, 80],
                      "t3m": [12, 4], "t3a": [20, 20], "tlm": [10, 10], "tla": [14, 14],
                      "opp_t3m": [7, 7], "opp_t3a": [20, 20], "opp_tlm": [10, 10], "opp_tla": [14, 14]})
    c = F.correggi_fortuna(b)
    assert (c["punti"].iloc[0] - c["punti"].iloc[1]) < (b["punti"].iloc[0] - b["punti"].iloc[1])
    assert abs(c["punti"].sum() - b["punti"].sum()) < 1e-9      # con la sola squadra in archivio il totale resta uguale


def test_piu_previsioni_insieme():
    forze = pd.DataFrame({"squadra_id": [1, 2], "forza": [6.0, -6.0], "pace_stima": [72.0, 72.0],
                          "ortg": [110.0, 102.0], "drtg": [102.0, 110.0], "partite": [10, 10], "incertezza": [3.0, 3.0]})
    p = F.pronostico(forze, 1, 2, 3.0, "ita2")
    assert F.probabilita_evento(p, "casa") == pytest.approx(p["prob_casa"])
    assert p["rischio"] == pytest.approx(1 - p["prob_casa"])
    assert F.probabilita_evento(p, "casa_scarto", 0) == pytest.approx(0.5 + 0.5 * (2 * p["prob_casa"] - 1), abs=0.05)
    assert F.probabilita_evento(p, "over", p["totale"]) == pytest.approx(0.5)
    assert F.probabilita_evento(p, "over", 150) + F.probabilita_evento(p, "under", 150) == pytest.approx(1)
    assert F.probabilita_evento(p, "casa_scarto", 5) > F.probabilita_evento(p, "casa_scarto", 10)
    e = F.errori([0.8, 0.7, 0.6])
    assert e["tutte"] == pytest.approx(0.8 * 0.7 * 0.6)
    assert e["attesi"] == pytest.approx(0.9) and e["distribuzione"].sum() == pytest.approx(1)
    assert e["al_piu_uno"] == pytest.approx(0.336 + 0.8 * 0.7 * 0.4 + 0.8 * 0.3 * 0.6 + 0.2 * 0.7 * 0.6)
