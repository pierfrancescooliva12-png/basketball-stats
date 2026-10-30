"""Guida e demo guidata: parte da sola solo per lo staff dei club, una volta per pagina."""

import re
from pathlib import Path

import pytest

HTML = Path(__file__).resolve().parent.parent / "dashboard" / "guida" / "index.html"


def test_pagine_viste_per_utente(tmp_path):
    from basket.note import Archivio
    a = Archivio(f"sqlite:///{tmp_path / 'n.sqlite'}")
    assert a.guida_viste("staff1") == []
    a.segna_guida("staff1", "home")
    a.segna_guida("staff1", "home")                 # due volte: una sola riga
    a.segna_guida("staff1", "scouting")
    assert sorted(a.guida_viste("staff1")) == ["home", "scouting"]
    assert a.guida_viste("staff2") == []
    a.azzera_guida("staff1")
    assert a.guida_viste("staff1") == []


def test_chi_vede_la_demo_da_sola():
    pytest.importorskip("streamlit")
    from dashboard import guida
    staff = {"username": "x", "club": "fortitudo", "ruolo": "staff"}
    assert guida.da_mostrare(staff, set(), "home")
    assert not guida.da_mostrare(staff, {"home"}, "home")           # già vista
    assert not guida.da_mostrare(staff, set(), "classifica")         # pagina semplice: niente demo
    assert not guida.da_mostrare({**staff, "ruolo": "admin"}, set(), "home")
    assert not guida.da_mostrare({"username": "demo", "club": None, "demo": True}, set(), "home")


def test_passi_della_demo():
    pytest.importorskip("streamlit")
    from dashboard import guida, pagine
    src = Path(pagine.__file__).read_text()
    chiavi = set(re.findall(r'P\(\w+,\s*"[^"]+",\s*"[\w-]+",\s*"(\w+)"', src))
    tipi = {"nav", "filtri", "esperto", "pagina", "tip", "sez", "btn", "tab", "exp", "sel", "frame"}
    for k, passi in guida.TOUR.items():
        assert k in chiavi and k in guida.NOMI, k
        assert 1 <= len(passi) <= 8, k
        for dove, titolo, testo in passi:
            assert dove and all(d.split(":")[0] in tipi for d in dove), (k, dove)
            assert titolo and len(titolo) <= 60 and 20 <= len(testo) <= 260, (k, titolo)
    assert {t for t, _, _ in guida.GUIDA} >= {"Primi passi", "Lavagna sul video", "Lavagna dei giochi", "Mercato"}


def test_componente_della_demo():
    s = HTML.read_text()
    # un solo valore torna alla piattaforma: il nome della pagina di cui la demo è stata vista
    assert s.count("streamlit:setComponentValue") == 1
    assert "invia({ visto: dati.chiave, t: Date.now() })" in s
    for vietato in ("fetch(", "XMLHttpRequest", "localStorage", "sendBeacon"):
        assert vietato not in s, vietato
    assert not re.findall(r"https?://", s)
