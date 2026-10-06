import numpy as np
import pandas as pd

from basket import mercato


def _pool():
    rng = np.random.default_rng(1)
    rows = []
    for i in range(30):
        rows.append({"giocatore_id": f"G{i}", "giocatore": f"G {i}", "squadra": "S",
                     "stagione": "x2627", "campionato_id": "ita2", "minuti": 300, "minuti_pg": 25,
                     "partite": 10, **{f: float(rng.normal(10, 3)) for f in
                                       mercato.SIMILARITY_FEATURES}})
    df = pd.DataFrame(rows)
    clone = df.iloc[[5]].copy()
    clone["giocatore_id"], clone["stagione"] = "CLONE", "x2526"
    return pd.concat([df, clone], ignore_index=True)


def test_similar_finds_identical_profile_first():
    sim = mercato.similar(_pool(), "G5", "x2627", n=3)
    assert sim.iloc[0]["giocatore_id"] == "CLONE"
    assert sim.iloc[0]["somiglianza"] == 100
    assert "G5" not in set(sim["giocatore_id"])


def test_role_estimate():
    p = pd.DataFrame({"altezza_cm": [208, 182, 196, None], "trb_pct": [9, 6, 15, 5],
                      "ast_pct": [5, 30, 8, 25]})
    assert list(mercato.estimate_role(p)) == ["Lungo", "Play / guardia", "Lungo", "Play / guardia"]
