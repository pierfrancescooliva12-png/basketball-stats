"""Programmi di allenamento: libreria esercizi, bozza delle sedute, quintetti, PDF e archivio."""

from datetime import date

import pandas as pd

from basket import allenamento as A
from basket import esercizi as E


def test_libreria_coerente():
    ids = [e["id"] for e in E.ESERCIZI]
    assert len(ids) == len(set(ids))
    for e in E.ESERCIZI:
        assert e["fase"] in E.FASI and e["intensita"] in E.INTENSITA
        assert e["aree"] and set(e["aree"]) <= set(E.AREE), e["id"]
        assert e["descrizione"] and e["punti"]
    for fase in E.FASI:
        assert any(e["fase"] == fase for e in E.ESERCIZI), fase
    for aree in list(E.AREE_SQUADRA.values()) + list(E.AREE_GIOCATORE.values()):
        assert set(aree) <= set(E.AREE)
        assert any(set(e["aree"]) & set(aree) for e in E.ESERCIZI)
    # la prima area chiesta viene prima nell'ordine
    assert "rimb_off" in E.per_aree(["rimb_off"], "tecnica")[0]["aree"]
    assert all(e["intensita"] != "alta" for e in E.per_aree(["tiro"], intensita_max="media"))


def test_bozza_seduta_somma_la_durata():
    for intensita in E.INTENSITA:
        for durata in (60, 75, 90, 120):
            b = A.bozza_seduta(durata, intensita, ["tiro", "rimb_dif"])
            assert sum(x["minuti"] for x in b) == durata
            assert b[0]["fase"] == "riscaldamento" and b[-1]["fase"] == "defaticamento"
            if intensita == "bassa":
                assert all(E.PER_ID[x["esercizio"]]["intensita"] != "alta" for x in b)
    ind = A.bozza_seduta(45, "media", ["liberi"], individuale=True)
    assert sum(x["minuti"] for x in ind) == 45 and all(x["fase"] != "collettivo" for x in ind)
    con = A.bozza_seduta(90, "media", ["sinergie"], quintetto="A · B · C · D · E")
    assert any("Quintetto: A · B" in x["note"] for x in con)


def test_microciclo_e_orari():
    gara = date(2026, 10, 31)
    assert A.microciclo(date(2026, 10, 30), gara) == ("MD-1", "bassa")
    assert A.microciclo(date(2026, 10, 29), gara) == ("MD-2", "media")
    assert A.microciclo(date(2026, 10, 27), gara)[1] == "alta"
    assert A.microciclo(date(2026, 11, 1), gara) == ("MD+1 · recupero", "bassa")
    assert A.microciclo(date(2026, 10, 27), None) == ("", "media")
    blocchi = [{"minuti": 12}, {"minuti": 20}]
    assert A.orari(blocchi, "18:00") == ["18:00–18:12", "18:12–18:32"]
    assert A.orari(blocchi) == ["0'–12'", "12'–32'"]


def test_coppie_dai_quintetti():
    lu = pd.DataFrame([
        {"squadra_id": 1, "quintetto": "a,b,c,d,e", "minuti": 20.0, "pf": 50, "ps": 40, "poss_f": 40.0, "poss_s": 40.0},
        {"squadra_id": 1, "quintetto": "a,b,f,g,h", "minuti": 10.0, "pf": 20, "ps": 25, "poss_f": 20.0, "poss_s": 20.0},
    ])
    cp = A.coppie(lu, 1).set_index(["a", "b"])
    ab = cp.loc[("a", "b")]
    assert ab["minuti"] == 30 and ab["pf"] == 70 and ab["ps"] == 65
    assert round(ab["net_rtg"], 1) == round(100 * 70 / 60 - 100 * 65 / 60, 1)
    assert cp.loc[("c", "d")]["minuti"] == 20


def test_programma_pdf_e_archivio(tmp_path, monkeypatch):
    from basket import config, db, update
    from basket.contesto import Contesto
    from basket.note import Archivio
    from basket.report_allenamento import build_programma
    from tests.test_pbp import Client
    monkeypatch.setattr(config, "CRONACA_DIR", tmp_path / "cronaca")
    conn = db.connect(tmp_path / "t.sqlite")
    update.update_league(conn, Client(), "ita2", "x2627", {2})
    ctx = Contesto(conn, "x2627")
    prog = A.nuovo_programma(ctx, 10050, "Settimana di prova", date(2026, 10, 26), [0, 2, 4], 90)
    assert len(prog["sedute"]) == 3
    assert all(sum(b["minuti"] for b in s["blocchi"]) == 90 for s in prog["sedute"])
    pdf = build_programma(ctx, 10050, prog)
    assert pdf[:4] == b"%PDF" and len(pdf) > 5_000
    gid = ctx.players[ctx.players["squadra_id"] == 10050]["giocatore_id"].iloc[0]
    ind = A.nuovo_programma(ctx, 10050, "Individuale", date(2026, 10, 26), [1], 45, tipo="individuale", giocatori=[gid])
    assert ind["includi"]["quintetti"] is False
    assert build_programma(ctx, 10050, ind)[:4] == b"%PDF"
    arch = Archivio(f"sqlite:///{tmp_path / 'n.sqlite'}")
    arch.save_program("club", prog, "staff")
    prog["nome"] = "Rinominato"
    arch.save_program("club", prog, "staff")
    salvati = arch.programs("club")
    assert len(salvati) == 1 and salvati[0]["nome"] == "Rinominato" and arch.programs("altro") == []
    arch.delete_program("club", prog["id"])
    assert arch.programs("club") == []
