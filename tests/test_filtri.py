import pandas as pd

from basket import filtri as F


def _df():
    return pd.DataFrame({"giocatore": ["A", "B", "C", "D"], "assist_pg": [6.0, 5.5, 7.0, 2.0],
                         "perse_pg": [1.5, 2.5, 1.9, 1.0], "assist": [60, 55, 70, 20],
                         "perse": [15, 25, 19, 0], "t3_pct": [40.0, None, 35.0, 30.0]})


def test_filtri_combinati():
    f = [{"col": "assist_pg", "op": "più di", "valore": 5},
         {"col": "perse_pg", "op": "meno di", "valore": 2}]
    assert list(F.applica(_df(), f)["giocatore"]) == ["A", "C"]
    assert F.descrivi(f) == "più di 5,0 assist e meno di 2,0 palle perse"


def test_assist_per_palla_persa_e_mancanti():
    d = F.prepara(_df())
    assert d["ast_to"].iloc[0] == 4.0 and pd.isna(d["ast_to"].iloc[3])   # nessuna persa: non definito
    out = F.applica(_df(), [{"col": "ast_to", "op": "almeno", "valore": 3.5}])
    assert list(out["giocatore"]) == ["A", "C"]
    # un valore mancante non rispetta il filtro; un filtro su una colonna assente è ignorato
    assert list(F.applica(_df(), [{"col": "t3_pct", "op": "almeno", "valore": 0}])["giocatore"]) == ["A", "C", "D"]
    assert len(F.applica(_df(), [{"col": "eta", "op": "al massimo", "valore": 25}])) == 4


def test_ricerche_pronte_valide():
    for nome, filtri in F.PRONTI.items():
        assert all(f["col"] in F.CATALOGO and f["op"] in F.OPERATORI for f in filtri), nome
