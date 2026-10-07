"""Lavagna: archivio dei giochi e disegno delle fasi nei PDF."""

from pathlib import Path

from basket import lavagna as L
from basket.note import Archivio


def gioco_esempio(gid="g1", nome="Pick and roll centrale"):
    o = [{"id": f"o{i}", "tipo": "o", "n": i, "x": x, "y": y}
         for i, (x, y) in enumerate([(75, 100), (126, 80), (24, 80), (138, 24), (60, 40)], 1)]
    x = [{"id": f"x{p['n']}", "tipo": "x", "n": p["n"], "x": p["x"], "y": p["y"] - 9} for p in o]
    f1 = {"giocatori": o + x, "palla": "o1", "nota": "5 blocca per 1",
          "linee": [{"id": "l1", "tipo": "blocco", "da": "o5", "punti": [[60, 40], [66, 62], [72, 88]]},
                    {"id": "l2", "tipo": "palleggio", "da": "o1", "punti": [[75, 100], [92, 94], [104, 82]]},
                    {"id": "l3", "tipo": "movimento", "da": "o4", "punti": [[138, 24], [140, 40], [134, 52]]}]}
    f2 = {"giocatori": o + x, "palla": "o1", "nota": "",
          "linee": [{"id": "l4", "tipo": "passaggio", "da": "o1", "a": "o5", "punti": [[104, 82], [84, 36]]}]}
    return {"id": gid, "nome": nome, "tipo": "nostro", "difesa": True, "fasi": [f1, f2]}


def test_archivio_giochi(tmp_path):
    a = Archivio(f"sqlite:///{tmp_path / 'n.sqlite'}")
    a.save_play("club", 10050, gioco_esempio(), "coach")
    a.save_play("club", 10050, gioco_esempio(nome="Pick and roll · v2"), "coach")   # sostituisce
    a.save_play("club", 13051, gioco_esempio("g2", "Horns"), "coach")
    a.save_play("altro", 10050, gioco_esempio("g3"), "x")
    giochi = a.plays("club", 10050)
    assert [g["nome"] for g in giochi] == ["Pick and roll · v2"]
    assert len(giochi[0]["fasi"]) == 2
    a.delete_play("club", "g2")
    assert a.plays("club", 13051) == []


def test_disegno_fase_e_pdf():
    g = gioco_esempio()
    d = L.disegno_fase(g["fasi"][0], True, 200)
    assert d.width == 200 and len(d.contents) > 30
    zig = L._campiona([[0, 0], [10, 0], [20, 5]], 1.6)
    assert 10 < len(zig) < 20
    from basket.report_pdf import build_giochi
    pdf = build_giochi([g, gioco_esempio("g2", "Horns")], "Unieuro Forlì")
    assert pdf[:4] == b"%PDF" and len(pdf) > 5_000


def test_componente_aggiornato():
    """Il componente della dashboard è generato dalla lavagna: devono restare allineati."""
    import pytest
    pytest.importorskip("streamlit")
    from dashboard import lavagna_ui
    base = Path(__file__).resolve().parent.parent / "dashboard" / "lavagna"
    assert (base / "componente" / "index.html").read_text() == lavagna_ui.pagina_componente()
