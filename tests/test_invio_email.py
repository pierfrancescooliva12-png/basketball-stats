"""Report agli abbonati: lo stesso report sulla stessa partita parte una sola volta."""

import json


def test_report_non_doppio(tmp_path, monkeypatch):
    from basket import config
    from basket import invio_email as I
    monkeypatch.setattr(config, "INVII_PATH", tmp_path / "invii.json")
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setenv("ABBONATI", json.dumps([{"email": "Staff@Club.it", "squadra": "Prova"}]))
    monkeypatch.setenv("SMTP_HOST", "smtp.prova")
    monkeypatch.setattr(I, "open_readonly", lambda: None)
    partita = {"data": "2026-11-01", "casa_id": 1, "ospite_id": 2}
    monkeypatch.setattr(I, "prepare", lambda ctx, sub: (
        "Scouting X", "testo", [(b"%PDF", "s.pdf")], I.impronta(sub["email"], partita)))
    inviati = []
    monkeypatch.setattr(I, "send", lambda msgs, fatti=None: (inviati.extend(msgs), fatti.extend(range(len(msgs)))))
    I.main([])
    I.main([])                                   # secondo aggiornamento: niente doppione
    assert len(inviati) == 1
    registro = (tmp_path / "invii.json").read_text()
    assert "staff@club.it" not in registro.lower()   # solo impronte
    I.main(["--forza"])
    assert len(inviati) == 2
    partita["data"] = "2026-11-08"               # partita nuova: si invia
    I.main([])
    assert len(inviati) == 3
