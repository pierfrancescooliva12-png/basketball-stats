import ast
from pathlib import Path

from basket import views as V
from basket.glossario import COLONNE, G, voci_per_colonne


def test_ogni_colonna_ha_una_voce():
    assert set(COLONNE.values()) <= set(G)
    for v in G.values():
        assert v.titolo and v.cosa and v.calcolo and v.lettura


def test_colonne_avanzate_delle_tabelle_sono_spiegate():
    for mapping in (V.TEAM_AVANZATE, V.TEAM_PROFILO, V.PLAYER_AVANZATE, V.PLAYER_RUOLO):
        etichette = set(mapping.values())
        for col in ("ORtg", "DRtg", "Net Rtg", "eFG%", "TS%", "USG%", "AST%", "REB%",
                    "Fortuna", "V% attesa", "Game Score"):
            if col in etichette:
                assert col in COLONNE, col
    voci = voci_per_colonne(["eFG%", "eFG% avv.", "Squadra"])
    assert [v.titolo for v in voci] == [G["efg"].titolo]


def test_tips_della_dashboard_esistono():
    src = Path(__file__).parent.parent / "dashboard" / "ui.py"
    tree = ast.parse(src.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "TIPS" for t in node.targets):
            tips = ast.literal_eval(node.value)
            assert set(tips.values()) <= set(G)
            return
    raise AssertionError("TIPS non trovato")


def test_dashboard_modules_import():
    """I moduli della dashboard si importano senza errori (nessun codice eseguito).
    Nel workflow di aggiornamento dati le librerie della dashboard non sono installate:
    lì il test viene saltato."""
    import importlib

    import pytest
    pytest.importorskip("plotly")
    pytest.importorskip("streamlit")
    for mod in ("dashboard.ui", "dashboard.stato", "dashboard.schede", "dashboard.nuove",
                "dashboard.analisi", "dashboard.pagine"):
        importlib.import_module(mod)
