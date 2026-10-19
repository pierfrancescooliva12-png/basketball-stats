from basket import accesso
from basket.note import Archivio


def test_password_hash_and_login():
    h = accesso.hash_password("segreta")
    assert accesso.verify_password("segreta", h)
    assert not accesso.verify_password("sbagliata", h)
    utenti = {"mario": {"password_hash": h, "club": "Unieuro Forlì"}}
    assert accesso.authenticate(utenti, "Mario ", "segreta")["club"] == "Unieuro Forlì"
    assert accesso.authenticate(utenti, "mario", "x") is None
    assert accesso.authenticate(utenti, "luigi", "segreta") is None


def test_archive_is_isolated_per_club(tmp_path):
    a = Archivio(f"sqlite:///{tmp_path}/n.sqlite")
    a.add_note("Forlì", "giocatore", "A1", "Mancino, attacca sempre a sinistra", "mario")
    a.add_note("Rimini", "giocatore", "A1", "nota di un altro club", "anna")
    assert list(a.notes("Forlì")["testo"]) == ["Mancino, attacca sempre a sinistra"]
    a.watch("Forlì", "Mercato estate", "A2", "Tizio", "mario")
    a.watch("Forlì", "Mercato estate", "A2", "Tizio", "mario")  # nessun duplicato
    assert len(a.watchlist("Forlì")) == 1 and a.watchlist("Rimini").empty
    a.set_goals("Forlì", {"efg_pct": 54})
    assert a.goals("Forlì") == {"efg_pct": 54.0} and a.goals("Rimini") == {}
    nid = int(a.notes("Forlì")["id"].iloc[0])
    a.delete_note("Rimini", nid)          # un altro club non può cancellare
    assert len(a.notes("Forlì")) == 1
    a.delete_note("Forlì", nid)
    assert a.notes("Forlì").empty


def test_blocco_dopo_tentativi_sbagliati():
    s = {}
    for _ in range(accesso.TENTATIVI - 1):
        s = accesso.registra(s, False, 100.0)
    assert accesso.attesa(s, 100.0) == 0                  # ancora libero
    s = accesso.registra(s, False, 100.0)
    assert accesso.attesa(s, 100.0) == accesso.BLOCCO_S   # bloccato
    assert accesso.attesa(s, 100.0 + accesso.BLOCCO_S) == 0
    for _ in range(accesso.TENTATIVI):
        s = accesso.registra(s, False, 200.0)
    assert accesso.attesa(s, 200.0) == 2 * accesso.BLOCCO_S  # il secondo blocco raddoppia
    assert accesso.registra(s, True, 210.0) == {}


def test_blocco_toml_admin_senza_club():
    import tomllib
    t = tomllib.loads(accesso.blocco_toml("Pier", "una-password-lunga", None, "admin"))
    u = t["utenti"]["pier"]
    assert "club" not in u and u["ruolo"] == "admin"
    assert "una-password-lunga" not in str(t)
    ok = accesso.authenticate(t["utenti"], "pier", "una-password-lunga")
    assert ok == {"username": "pier", "club": None, "ruolo": "admin"}
