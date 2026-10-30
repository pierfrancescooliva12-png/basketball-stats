"""Efficienza delle situazioni segnalate sul video: come finisce il possesso secondo la cronaca."""

import pandas as pd

from basket import situazioni as SI

NOI, LORO = 1, 2


def _ev(righe, pid="p1"):
    # n, periodo, secondi (dall'inizio della partita), squadra, tipo
    e = pd.DataFrame(righe, columns=["n", "periodo", "secondi", "squadra_id", "tipo"])
    e["partita_id"], e["squadra_casa_id"], e["squadra_ospite_id"] = pid, NOI, LORO
    return e


EV = _ev([
    (1, 1, 20, NOI, "tiro2_sbagliato"), (2, 1, 21, NOI, "rimb_off"), (3, 1, 24, NOI, "tiro3_fatto"),
    (4, 1, 40, LORO, "persa"), (5, 1, 41, NOI, "recupero"),
    (6, 1, 60, NOI, "tiro2_fatto"), (7, 1, 60, LORO, "fallo"), (8, 1, 60, NOI, "tl_fatto"),
    (9, 1, 80, LORO, "tiro3_sbagliato"), (10, 1, 82, NOI, "rimb_dif"),
    (11, 1, 100, LORO, "fallo"), (12, 1, 100, NOI, "tl_fatto"), (13, 1, 100, NOI, "tl_sbagliato"),
    (14, 1, 590, NOI, "tiro3_sbagliato"),
    (15, 2, 610, NOI, "tiro2_fatto")])


def test_fine_del_possesso():
    x = SI.esito(EV, 1, 18)                 # tiro sbagliato, rimbalzo offensivo, tripla: 3 punti, 2 tiri
    assert (x["squadra"], x["punti"], x["esito"], x["tiri"], x["canestri"]) == (NOI, 3, "canestro", 2, 1)
    assert SI.esito(EV, 1, 37)["esito"] == "palla persa" and SI.esito(EV, 1, 37)["squadra"] == LORO
    assert SI.esito(EV, 1, 57)["punti"] == 3                # canestro e libero aggiuntivo
    x = SI.esito(EV, 1, 78)
    assert (x["squadra"], x["esito"], x["tiri"]) == (LORO, "tiro sbagliato", 1)
    x = SI.esito(EV, 1, 98)
    assert (x["squadra"], x["punti"], x["esito"]) == (NOI, 1, "liberi")
    assert SI.esito(EV, 1, 588)["esito"] == "tiro sbagliato"   # nessun rimbalzo prima della fine del quarto
    assert SI.esito(EV, 1, 300) is None                         # niente nella cronaca entro 24 secondi
    assert SI.esito(EV, 2, 8)["punti"] == 2


def test_riepilogo_per_azione_e_schema():
    mem = {"p1": {"segnalazioni": [
        {"azione": "Pick and roll centrale", "schema": "Horns 45", "p": 1, "gs": 18},
        {"azione": "Pick and roll centrale", "schema": None, "p": 1, "gs": 57},
        {"azione": None, "schema": "Horns 45", "p": 1, "gs": 98},
        {"et": "Transizione", "p": 1, "gs": 78},                  # salvata prima dei due livelli
        {"azione": "Post basso", "schema": None, "p": None, "gs": None}]},
        "altra": {"segnalazioni": [{"azione": "Post basso", "p": 1, "gs": 18}]}}
    altra = _ev([(1, 1, 20, 7, "tiro2_fatto")], pid="altra")
    altra["squadra_casa_id"], altra["squadra_ospite_id"] = 7, 8          # partita senza la nostra squadra
    sit = SI.situazioni(mem, pd.concat([EV, altra]), NOI)
    assert len(sit) == 5 and set(sit["partita_id"]) == {"p1"}
    az = SI.riepilogo(sit, ["azione"], "noi").set_index("azione")
    assert az.loc["Pick and roll centrale", "situazioni"] == 2 and az.loc["Pick and roll centrale", "punti"] == 6
    assert az.loc["Pick and roll centrale", "punti_per_situazione"] == 3
    sc = SI.riepilogo(sit, ["schema"], "noi").set_index("schema")
    assert sc.loc["Horns 45", "situazioni"] == 2 and sc.loc["Horns 45", "punti"] == 4 and sc.loc["Horns 45", "liberi"] == 1
    insieme = SI.riepilogo(sit, ["azione", "schema"], "noi")
    assert insieme[["azione", "schema", "situazioni"]].values.tolist() == [["Pick and roll centrale", "Horns 45", 1]]
    loro = SI.riepilogo(sit, ["azione"], "loro").set_index("azione")
    assert loro.loc["Transizione", "punti"] == 0 and loro.loc["Transizione", "tiri"] == 1
    assert not sit.loc[sit["azione"] == "Post basso", "con_tempo"].any()


def test_archivio_di_tutte_le_partite(tmp_path):
    from basket.note import Archivio
    a = Archivio(f"sqlite:///{tmp_path / 'n.sqlite'}")
    a.set_video_dati("club", "partita:p1", {"segnalazioni": [1]})
    a.set_video_dati("club", "partita:p2", {"segnalazioni": [2]})
    a.set_video_dati("club", "etichette", {"azioni": []})
    a.set_video_dati("altro", "partita:p3", {"segnalazioni": [3]})
    assert a.video_dati_tutti("club", "partita:") == {"partita:p1": {"segnalazioni": [1]},
                                                     "partita:p2": {"segnalazioni": [2]}}
