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
