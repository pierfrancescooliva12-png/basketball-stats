"""Report per email: destinatari, momento dell'invio, nessun doppione, email salvata dall'utente."""

import json
from datetime import datetime, timedelta

import pytest


def test_report_non_doppio(tmp_path, monkeypatch):
    from basket import config
    from basket import invio_email as I
    monkeypatch.setattr(config, "INVII_PATH", tmp_path / "invii.json")
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setenv("ABBONATI", json.dumps([{"email": "Staff@Club.it", "squadra": "Prova"}]))
    monkeypatch.setenv("SMTP_HOST", "smtp.prova")
    monkeypatch.delenv("ARCHIVIO_URL", raising=False)
    monkeypatch.setattr(I, "open_readonly", lambda: None)
    partita = {"id": "p1"}
    monkeypatch.setattr(I, "prepare", lambda ctx, sub: [
        ("Post-partita X", "testo", [(b"%PDF", "p.pdf")], I.impronta(sub["email"], "post", partita["id"])),
        ("Scouting Y", "testo", [(b"%PDF", "s.pdf")], I.impronta(sub["email"], "scouting", partita["id"]))])
    inviati = []
    monkeypatch.setattr(I, "send", lambda msgs, fatti=None: (inviati.extend(msgs), fatti.extend(range(len(msgs)))))
    I.main([])
    I.main([])                                   # controllo successivo: niente doppioni
    assert len(inviati) == 2
    registro = (tmp_path / "invii.json").read_text()
    assert "staff@club.it" not in registro.lower()   # solo impronte
    I.main(["--forza"])
    assert len(inviati) == 4
    partita["id"] = "p2"                         # partita nuova: si invia
    I.main([])
    assert len(inviati) == 6


def test_email_valida_e_impronta():
    from basket import invio_email as I
    assert I.valida_email("  Mario.Rossi@Club.IT ") == "mario.rossi@club.it"
    for no in ("", "mario", "mario@", "@club.it", "mario@club", "a b@club.it", "x" * 130 + "@club.it"):
        assert I.valida_email(no) is None, no
    a = I.impronta("Staff@club.it", "post", "p1")
    assert a == I.impronta("staff@club.it ", "post", "p1")
    assert a != I.impronta("staff@club.it", "scouting", "p1") and a != I.impronta("staff@club.it", "post", "p2")


def test_email_salvata_dall_utente_e_destinatari(tmp_path, monkeypatch):
    from basket import invio_email as I
    from basket.note import Archivio
    a = Archivio(f"sqlite:///{tmp_path / 'n.sqlite'}")
    assert a.email_report("mario") is None                 # mai chiesto: compare al primo accesso
    a.set_email_report("mario", "Rimini", None)            # «Non ora»: non si chiede più
    assert a.email_report("mario")["email"] == "" and a.iscritti_email() == []
    a.set_email_report("mario", "Rimini", " Mario@Club.it ", post_partita=True, scouting=False)
    a.set_email_report("anna", "Rimini", "anna@club.it")
    assert a.email_report("mario") == {"email": "mario@club.it", "post_partita": True, "scouting": False,
                                       "club": "Rimini"}
    monkeypatch.setenv("ABBONATI", json.dumps([{"email": "anna@club.it", "squadra": "Rimini"},
                                              {"email": "ds@altro.it", "squadra": "Cento"}]))
    d = I.destinatari(a)
    assert sorted(x["email"] for x in d) == ["anna@club.it", "ds@altro.it", "mario@club.it"]   # anna una volta
    assert next(x for x in d if x["email"] == "mario@club.it")["scouting"] is False
    a.set_email_report("mario", "Rimini", None)            # toglie l'indirizzo
    assert [x["utente"] for x in a.iscritti_email()] == ["anna"]
    # registro degli invii nell'archivio
    r = I.Registro(a)
    assert "k1" not in r
    r.segna(["k1", "k2"])
    assert "k1" in I.Registro(a) and a.invii_fatti() == {"k1", "k2"}


def test_quando_partono_i_report(monkeypatch):
    """Post-partita con i dati della partita; scouting quando hanno giocato tutte e due."""
    from basket import config, db
    from basket import invio_email as I
    from basket.contesto import Contesto
    if not config.DB_PATH.exists():
        pytest.skip("database non disponibile")
    ctx = Contesto(db.connect(config.DB_PATH, readonly=True), config.STAGIONE)
    monkeypatch.setattr(I, "build_pdf", lambda *a, **k: b"%PDF scouting")
    monkeypatch.setattr(I, "build_post_partita", lambda *a, **k: b"%PDF post")
    # una squadra con la prossima partita in calendario
    for sid in ctx.bs["squadra_id"].unique():
        cal = I._calendario(ctx, int(sid))
        giocate = set(ctx.bs["partita_id"])
        future = [g for g in cal if g["partita_id"] not in giocate]
        if future and any(g["partita_id"] in giocate for g in cal):
            break
    else:
        pytest.skip("stagione finita")
    sid = int(sid)
    nome = ctx.nomi_squadre[sid]
    sub = {"email": "staff@club.it", "squadra": nome, "post_partita": True, "scouting": True}
    assert I.scouting.find_team(ctx.conn, nome)[0][0] == sid
    prossima = future[0]
    ultima = ctx.bs[ctx.bs["squadra_id"] == sid].sort_values(["data", "partita_id"]).iloc[-1]
    dopo = datetime.fromisoformat(str(ultima["data"])[:10]) + timedelta(hours=30)
    avv = prossima["ospite_id"] if prossima["casa_id"] == sid else prossima["casa_id"]

    # il giorno dopo l'ultima partita giocata: il post-partita c'è, una volta per partita
    monkeypatch.setattr(I, "stato_squadra", lambda c, s, adesso=None: {"in_attesa": None, "prossima": prossima})
    pronti = I.prepare(ctx, sub, dopo)
    tipi = [o.split()[0] for o, *_ in pronti]
    assert "Post-partita" in tipi and "Scouting" in tipi
    assert pronti[0][3] == I.impronta("staff@club.it", "post", ultima["partita_id"])
    assert pronti[1][3] == I.impronta("staff@club.it", "scouting", prossima["partita_id"])
    # dopo una settimana il post-partita non parte più (chi si iscrive tardi non riceve partite vecchie)
    assert all(not o.startswith("Post-partita") for o, *_ in I.prepare(ctx, sub, dopo + timedelta(days=7)))
    # chi ha scelto solo lo scouting
    solo = I.prepare(ctx, {**sub, "post_partita": False}, dopo)
    assert [o.split()[0] for o, *_ in solo] == ["Scouting"]

    # l'avversaria deve ancora giocare un'altra partita prima: niente scouting
    altra = {**prossima, "partita_id": "altra"}
    monkeypatch.setattr(I, "stato_squadra", lambda c, s, adesso=None: {
        "in_attesa": None, "prossima": altra if s == avv else prossima})
    assert all(not o.startswith("Scouting") for o, *_ in I.prepare(ctx, sub, dopo))
    # l'avversaria ha giocato ma i dati non sono ancora arrivati: si aspetta
    monkeypatch.setattr(I, "stato_squadra", lambda c, s, adesso=None: {
        "in_attesa": prossima if s == avv else None, "prossima": prossima})
    assert all(not o.startswith("Scouting") for o, *_ in I.prepare(ctx, sub, dopo))
    # la propria squadra deve ancora giocare (o aspetta i dati): si aspetta
    monkeypatch.setattr(I, "stato_squadra", lambda c, s, adesso=None: {
        "in_attesa": prossima if s == sid else None, "prossima": prossima})
    assert all(not o.startswith("Scouting") for o, *_ in I.prepare(ctx, sub, dopo))


def test_stato_squadra_e_controllo_orario():
    from basket import config, db
    from basket import invio_email as I
    from basket.contesto import Contesto
    if not config.DB_PATH.exists():
        pytest.skip("database non disponibile")
    ctx = Contesto(db.connect(config.DB_PATH, readonly=True), config.STAGIONE)
    giocate = set(ctx.bs["partita_id"])
    for sid in ctx.bs["squadra_id"].unique():
        future = [g for g in I._calendario(ctx, int(sid)) if g["partita_id"] not in giocate]
        if future:
            break
    else:
        pytest.skip("stagione finita")
    sid, g = int(sid), future[0]
    sub = [{"email": "x@y.it", "squadra": ctx.nomi_squadre[sid]}]
    prima = g["inizio"] - timedelta(hours=2)
    assert I.stato_squadra(ctx, sid, prima) == {"in_attesa": None, "prossima": g}
    # a partita cominciata da poco non si scarica ancora; dopo un'ora e tre quarti sì
    assert I.stato_squadra(ctx, sid, g["inizio"] + timedelta(minutes=30))["in_attesa"] == g
    assert not I.serve_aggiornare(ctx, sub, g["inizio"] + timedelta(minutes=30))
    assert I.serve_aggiornare(ctx, sub, g["inizio"] + timedelta(hours=2))
    # dopo tre giorni senza dati la partita si considera rinviata: non blocca più
    assert I.stato_squadra(ctx, sid, g["inizio"] + timedelta(days=5))["in_attesa"] is None
    assert not I.serve_aggiornare(ctx, [], g["inizio"] + timedelta(hours=2))
