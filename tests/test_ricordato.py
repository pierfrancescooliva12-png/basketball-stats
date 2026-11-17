from basket import accesso
from basket.note import Archivio


def test_accesso_ricordato(tmp_path):
    a = Archivio(f"sqlite:///{tmp_path / 'n.sqlite'}")
    h = accesso.hash_password("Vecchia-1234")
    a.add_user("pistoiastaff", h, "Lumos Pistoia Basket", "staff", "admin")
    codice = accesso.nuovo_codice()
    a.crea_sessione(accesso.impronta(codice), "pistoiastaff", accesso.impronta(h)[:24], 30)
    utenti = accesso.unisci({}, a.users())
    u = accesso.utente_ricordato(utenti, a.sessione(accesso.impronta(codice)))
    assert u["username"] == "pistoiastaff" and u["club"] == "Lumos Pistoia Basket"
    # codice sbagliato: niente accesso
    assert a.sessione(accesso.impronta("altro")) is None
    # password cambiata (anche dall'amministratore): il vecchio codice non vale più
    a.set_password("pistoiastaff", accesso.hash_password("Nuova-5678"), cambio=False)
    utenti = accesso.unisci({}, a.users())
    assert accesso.utente_ricordato(utenti, a.sessione(accesso.impronta(codice))) is None
    # utente disattivato: non è più tra gli utenti
    assert accesso.utente_ricordato({}, {"utente": "pistoiastaff", "password": "x"}) is None
    # «Esci» chiude la sessione
    a.chiudi_sessione(accesso.impronta(codice))
    assert a.sessione(accesso.impronta(codice)) is None


def test_sessione_scaduta(tmp_path):
    a = Archivio(f"sqlite:///{tmp_path / 'n.sqlite'}")
    a.crea_sessione("k", "u", "p", -1)
    assert a.sessione("k") is None
