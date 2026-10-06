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
