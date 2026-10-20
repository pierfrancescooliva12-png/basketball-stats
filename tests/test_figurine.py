"""Figurine dei giocatori: dati della carta e HTML."""

from types import SimpleNamespace as NS

import pandas as pd
import pytest

from basket import confronto as CF
from basket import figurine as FG
from basket import scheda_giocatori as SG


def _scheda(gid, stagione):
    if gid == 2:
        return None
    riga = pd.Series({"punti_pg": 14.25, "rimb_tot_pg": 8.0, "assist_pg": 1.5, "ts_pct": 61.2,
                      "t3_pct": 20.0, "partite": 7, "minuti_pg": 27.4})
    dims = {"Realizzazione": 82.0, "Creazione": 30.0, "Tiro da fuori": float("nan"), "Rimbalzo": 95.0,
            "Difesa e attività": 60.0, "Impatto": 77.0}
    return {"riga": riga, "ruolo": "Lungo", "dimensioni": dims, "pool": 41, "scala": "A2",
            "pochi_dati": False}


def test_carte(monkeypatch):
    monkeypatch.setattr(SG, "schede", lambda ctx, sid, **k: [
        {"giocatore_id": 1, "nome": "Mario De Rossi", "maglia": "12", "ruolo": "Centro", "foto": None},
        {"giocatore_id": 2, "nome": "Senza Dati", "maglia": None, "ruolo": None, "foto": None}])
    monkeypatch.setattr(SG, "meta", lambda s: "#12 · Centro")
    monkeypatch.setattr(CF, "scheda", lambda hist, gid, stagione: _scheda(gid, stagione))
    carte = FG.carte(NS(stagione="2025-26"), pd.DataFrame(), 10)
    assert len(carte) == 1
    c = carte[0]
    assert (c["nome"], c["cognome"], c["sigla"], c["impatto"]) == ("Mario", "De Rossi", "LUNGO", 77.0)
    assert c["barre"]["Difesa"] == 60.0 and list(c["barre"])[0] == "Realizzazione"
    assert c["numeri"] == [("PT", "14,2"), ("RIM", "8,0"), ("AST", "1,5"), ("TS%", "61,2")]
    assert c["piede"] == "Confronto con 41 lunghi di A2 · 7 partite, 27,4 minuti"


def test_carta_html():
    pytest.importorskip("streamlit")
    from dashboard import figurine_ui as FU
    c = {"nome": "Mario", "cognome": "Rossi<", "maglia": "12", "sigla": "PLAY", "meta": "x", "foto": None,
         "impatto": 77.4, "barre": {"Realizzazione": 82.0, "Tiro da fuori": float("nan")},
         "numeri": [("PT", "14,2")], "piede": "p", "pochi_dati": True}
    h = FU.carta(c, "Luiss", 2)
    assert "<b>77</b>" in h and "Rossi&lt;" in h and "pochi dati" in h and "width:0%" in h
    assert 'class="sil"' in h and "animation-delay:0.12s" in h


def test_dividi_nome():
    assert FG.dividi_nome("Andrea De Nicolao") == ("Andrea", "De Nicolao")
    assert FG.dividi_nome("Niccolo De Vico") == ("Niccolo", "De Vico")
    assert FG.dividi_nome("Regimantas Miniotas") == ("Regimantas", "Miniotas")
    assert FG.dividi_nome("Nene") == ("", "Nene")


def test_locandina():
    pytest.importorskip("streamlit")
    from basket.brand import Tema
    from dashboard import locandina as LO
    assert LO.quando("2026-10-21", "20:30:00") == "Mercoledì 21 ottobre · ore 20:30"
    t = Tema(1, "A", "#101820", "#202830", "#ff7a1a", "#ffffff", "#f4f6fa", "data:image/png;base64,xx", True)
    h = LO.html("CMT Orange Tools Pesaro", "UEB Gesteco Cividale", t, None, "Prossima partita",
                ["5ª giornata", "", "PalaX"], prob=0.76)
    assert 'src="data:image/png;base64,xx"' in h and '<div class="ini">CIV</div>' in h
    assert "<span>PalaX</span>" in h and "<span></span>" not in h and "76%" in h and "24%" in h
    # stesso fondo per le due squadre (loghi mancanti): la seconda metà cambia colore
    col = LO._colori(None, None)
    assert col["c1"] != col["c2"]


def test_maiuscole():
    assert FG.maiuscole("Andrea De nicolao") == "Andrea De Nicolao"
    assert FG.maiuscole("Cheick yaya Sissoko") == "Cheick Yaya Sissoko"
    assert FG.maiuscole("Luca di Prima") == "Luca di Prima"
