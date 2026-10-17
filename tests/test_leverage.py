"""Leverage: probabilità di vittoria in partita, swing delle azioni e merito a somma zero."""

import pandas as pd

from basket import leverage as L


def test_probabilita():
    assert abs(L.prob(0, 2400) - 0.5) < 1e-9
    assert L.prob(10, 60) > L.prob(10, 1200) > 0.5            # lo stesso vantaggio vale di più alla fine
    assert L.prob(1, 0) == 1.0 and L.prob(-1, 0) == 0.0
    assert L.prob(0, 1200, atteso=6) > 0.5                     # la squadra più forte parte avanti
    assert L.prob(0, 30, possesso=1) > L.prob(0, 30, possesso=-1)
    assert L.restante(5, 2500) == 200


def _partita():
    righe = [  # n, periodo, secondi, squadra, giocatore, tipo, casa, punti dopo
        (0, 1, 30, 1, "a1", "tiro2_fatto", True, 2, 0),
        (1, 1, 30, 1, "a2", "assist", True, 2, 0),
        (2, 4, 2380, 2, "b1", "tiro3_fatto", False, 2, 3),
        (3, 4, 2395, 1, "a1", "persa", True, 2, 3),
        (4, 4, 2395, 2, "b2", "recupero", False, 2, 3),
    ]
    ev = pd.DataFrame(righe, columns=["n", "periodo", "secondi", "squadra_id", "giocatore_id", "tipo", "casa",
                                      "punti_casa", "punti_ospite"])
    ev["partita_id"] = "p1"; ev["di_squadra"] = False
    ev["avversario_id"] = ev["squadra_id"].map({1: 2, 2: 1})
    return ev


def test_swing_e_crediti():
    sw = L.swing(_partita())
    s = sw.set_index("n")["swing"]
    assert s[2] > 5 * abs(s[0])                 # la tripla del sorpasso nel finale pesa molto più del primo canestro
    assert s[3] < 0                             # palla persa: toglie probabilità
    st = pd.DataFrame({"partita_id": "p1", "squadra_id": [1, 2], "inizio": 0, "fine": 2400,
                       "quintetto": ["a1,a2,a3,a4,a5", "b1,b2,b3,b4,b5"]})
    cr = L.crediti(sw, st)
    assert abs(cr["leverage"].sum()) < 1e-9     # somma zero
    tripla = cr[cr["n"] == 2].set_index("giocatore_id")["leverage"]
    assert tripla["b1"] > tripla["b2"] > 0 > tripla["a1"]
    canestro = cr[cr["n"] == 0].set_index("giocatore_id")["leverage"]
    assert canestro["a1"] > canestro["a2"] > canestro["a3"] > 0    # tiratore, assistman, compagni
    persa = cr[cr["n"] == 3].set_index("giocatore_id")["leverage"]
    assert persa["b2"] > persa["b1"] > 0                            # chi recupera prende di più
    t = L.per_giocatore(cr)
    assert {"leverage", "tiro", "difesa"} <= set(t.columns)
