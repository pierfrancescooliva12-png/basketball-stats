import pandas as pd

from basket import numeri as N


def test_percentuale_con_numero():
    riga = pd.Series({"tov_pct": 18.27, "perse": 132, "partite": 10, "efg_pct": 52.0})
    assert N.con_numero(riga, "tov_pct") == "18,3% (13,2)"
    assert N.con_numero(riga, "efg_pct") == "52,0%"            # nessun conteggio: solo la percentuale
    assert N.con_numero(riga, "tov_pct", numero=15.0) == "18,3% (15,0)"
    assert N.a_partita(pd.Series({"rimb_off_pg": 11.5}), "orb_pct") == 11.5
