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
    assert abs((p["margine_a"] - p["margine_da"]) - 2 * F.Z80 * F.SIGMA) < 1e-9
    assert 140 < p["totale"] < 175 and p["da"] < p["totale"] < p["a"]
    assert abs(p["punti_casa"] - p["punti_ospite"] - p["margine"]) < 1e-9
    assert p["affidabilita"] == "alta" and p["scarto_10_casa"] > p["scarto_10_ospite"]
    pari = F.pronostico(forze, 3, 3, 0.0)
    assert abs(pari["prob_casa"] - 0.5) < 1e-9
