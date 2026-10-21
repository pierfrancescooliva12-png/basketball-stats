"""Foto e loghi: cosa si riprova e quando (sito lento, immagine che non c'è ancora)."""

import os
import time

from basket import brand
from basket import scheda_giocatori as SG


def test_foto_riprovate(monkeypatch, tmp_path):
    monkeypatch.setattr(SG, "CACHE_FOTO", tmp_path)
    chiamate = []

    def rete_giu(url, timeout):
        chiamate.append(url)
        raise OSError("timeout")
    monkeypatch.setattr(SG, "_scarica", rete_giu)
    SG._FALLITE.clear()
    assert SG.scarica_foto("G1", "u") is None and SG.scarica_foto("G1", "u") is None
    assert len(chiamate) == 1                       # dopo un errore di rete si aspetta
    SG._FALLITE["G1"] = time.time() - SG.RIPROVA_RETE - 1
    monkeypatch.setattr(SG, "_scarica", lambda url, timeout: b"\xff\xd8\xffdati")
    assert SG.scarica_foto("G1", "u") == b"\xff\xd8\xffdati"
    # "nessuna foto": file vuoto, si richiede solo dopo qualche giorno
    (tmp_path / "G2.jpg").write_bytes(b"")
    assert SG.scarica_foto("G2", "u") is None
    vecchio = time.time() - SG.RIPROVA_VUOTE - 10
    os.utime(tmp_path / "G2.jpg", (vecchio, vecchio))
    assert SG.scarica_foto("G2", "u") == b"\xff\xd8\xffdati"
    s = [{"giocatore_id": "G3", "foto_url": "u", "foto": None}, {"giocatore_id": "G4", "foto": b"x"}]
    assert SG.completa_foto(s)[0]["foto"] == b"\xff\xd8\xffdati" and s[1]["foto"] == b"x"


def test_logo_con_indirizzo_alternativo(monkeypatch, tmp_path):
    monkeypatch.setattr(brand, "CACHE_LOGHI", tmp_path)
    monkeypatch.setattr(brand, "_scarica", lambda url, timeout: b"" if "static" in url else b"\x89PNG\r\n\x1a\nok")
    brand._FALLITI.clear()
    assert brand.logo(7) is None                     # il sito della Lega non ce l'ha
    assert brand.logo(7, "https://club.example/logo.png").startswith(b"\x89PNG")
