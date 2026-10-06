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


def _league():
    rng = np.random.default_rng(3)
    prof = pd.DataFrame({"squadra_id": range(1, 11)})
    for col in ["efg_pct", "t3_pct", "tov_pct", "ast_ratio", "orb_pct", "drb_pct",
                "opp_efg_pct", "stoppate_pg", "opp_tov_pct", "recuperate_pg", "ft_rate", "ortg",
                "quota_top2"]:
        prof[col] = rng.normal(50, 5, 10)
    prof.loc[prof.squadra_id == 1, ["efg_pct", "t3_pct"]] = [30, 20]   # pessima al tiro
    prof.loc[prof.squadra_id == 1, ["orb_pct", "drb_pct"]] = [80, 80]   # ottima a rimbalzo
    return prof


def test_team_needs_ranks_weaknesses_first():
    needs = mercato.team_needs(_league(), 1)
    assert needs.iloc[0]["tipo"] == "tiratore" and needs.iloc[0]["priorita"] == "Alta"
    assert needs.set_index("tipo").loc["rimbalzista", "gravita"] == 0
    assert "10° su 10" in needs.iloc[0]["motivi"][0]


def test_fit_scores_shrink_small_samples():
    base = {"stagione": "x2627", "categoria": "A2", "minuti_pg": 25, "partite": 10,
            "t3a_p40": 8, "punti": 100, "t2m": 20, "t2a": 40, "tlm": 10, "tla": 12,
            "perse": 10}
    def row(gid, sid, t3m, t3a):
        return dict(base, giocatore_id=gid, squadra_id=sid, t3m=t3m, t3a=t3a,
                    punti=2 * base["t2m"] + 3 * t3m + base["tlm"])
    rows = [row("pochi", 1, 3, 3), row("tanti", 2, 45, 100)]
    rows += [row(f"x{i}", 3, 30, 100) for i in range(8)]
    fit = mercato.fit_scores(pd.DataFrame(rows), "tiratore").set_index("giocatore_id")
    # 3/3 da 3 viene stimato prudentemente: sotto chi ha fatto 45/100
    assert fit.loc["pochi", "t3_pct"] < fit.loc["tanti", "t3_pct"]
    assert fit.loc["tanti", "adattamento"] == fit["adattamento"].max()
