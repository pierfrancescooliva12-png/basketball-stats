"""Live: stato della partita dalla cronaca e suggerimenti per lo staff."""

from pathlib import Path

import pandas as pd

from basket import live
from basket.scraper import parse_pbp

FIX = Path(__file__).parent / "fixtures"


def test_cronaca_reale_fermata_a_meta():
    cr = parse_pbp((FIX / "pbp_ita2_412.html").read_text())
    ev = live.da_cronaca(cr, 1, 2, "p")
    assert len(ev) > 100 and set(ev["squadra_id"]) == {1, 2}
    s = live.stato(live.fino_a(ev, 1150), 1, 0.0, cr["nomi"])
    assert s["periodo"] == 2 and s["resta"] >= 1250
    assert s["punti"][1] + s["punti"][2] > 20 and 0 < s["wp"] < 1
    assert all(0 <= v <= 2 for v in s["timeout"].values())
    tot = live.stato(ev, 1, 0.0, cr["nomi"])
    ultimo = ev.iloc[-1]
    assert (tot["punti"][1], tot["punti"][2]) == (ultimo["punti_casa"], ultimo["punti_ospite"])
    assert isinstance(live.suggerimenti(tot), list)


def _ev(righe):
    ev = pd.DataFrame(righe, columns=["n", "periodo", "secondi", "squadra_id", "giocatore_id", "tipo",
                                      "punti_casa", "punti_ospite"])
    ev["zona"] = None; ev["di_squadra"] = False
    return live.normalizza(ev, 1, 2, "p")


def test_suggerimenti_parziale_falli_finale():
    righe, pc, po, n = [], 40, 40, 0
    for k in range(5):                               # parziale 10-0 dell'avversario
        po += 2; righe.append((n, 2, 900 + 20 * k, 2, "b1", "tiro2_fatto", pc, po)); n += 1
    for k in range(4):                               # 4 falli di squadra, 3 dello stesso giocatore
        righe.append((n, 2, 1010 + k, 1, "a1" if k < 3 else "a2", "fallo", pc, po)); n += 1
    s = live.stato(_ev(righe), 1, 0.0, {"a1": "Rossi", "b1": "Bianchi"})
    sug = live.suggerimenti(s)
    testi = " ".join(x["testo"] for x in sug)
    assert sug[0]["urgenza"] == 3 and "Parziale avversario 10-0" in sug[0]["testo"]
    assert "bonus" in testi or "lunetta" in testi
    assert "Rossi ha 3 falli" in testi
    # finale: avanti di 3 a 20 secondi dalla fine
    fin = _ev([(0, 4, 2380, 1, "a1", "tiro3_fatto", 70, 67)])
    s = live.stato(fin, 1)
    assert any("niente triple" in x["testo"] for x in live.suggerimenti(s))


def test_calendario_e_finestra_della_diretta():
    import sqlite3
    c = sqlite3.connect(":memory:")
    c.executescript("""
        CREATE TABLE squadre (squadra_id INTEGER, nome TEXT);
        INSERT INTO squadre VALUES (1, 'Casa'), (2, 'Ospite');
        CREATE TABLE calendario (partita_id TEXT, gameid TEXT, campionato_id TEXT, stagione TEXT, giornata INT,
            data TEXT, ora TEXT, stato TEXT, squadra_casa_id INT, squadra_ospite_id INT, palazzetto TEXT);
        INSERT INTO calendario VALUES ('p1', 'g1', 'ita2', 's', 1, '2026-10-21', '20:30', 'ready', 1, 2, NULL),
                                      ('p2', 'g2', 'ita2', 's', 2, '2026-10-25', '18:00', 'ready', 2, 1, NULL);
    """)
    fasi = lambda t: live.calendario(c, "s", 1, da=pd.Timestamp(t))["fase"].tolist()  # noqa: E731
    assert fasi("2026-10-21 12:00") == ["oggi", "in programma"]          # mercoledì: turno infrasettimanale
    assert fasi("2026-10-21 20:15") == ["in corso", "in programma"]      # la diretta si apre 20' prima
    assert fasi("2026-10-21 23:30") == ["finita", "in programma"]
    d = live.calendario(c, "s", 1, da=pd.Timestamp("2026-10-20 09:00"))
    assert d["giorno"].iloc[0] == "mercoledì 21/10"
