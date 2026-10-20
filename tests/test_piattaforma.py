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
    assert ok == {"username": "pier", "club": None, "ruolo": "admin", "fonte": "secrets", "cambio": False}


def test_password_generata_e_nomi_utente():
    pw = accesso.genera_password()
    assert len(pw) == 14 and pw.count("-") == 2 and not set(pw) & set("0O1lI")
    assert accesso.genera_password() != pw
    assert accesso.errore_nome("forli-staff", ["pier"]) is None
    assert accesso.errore_nome("Pier", ["pier"]) == "esiste già"
    assert accesso.errore_nome("forli.staff", []) is not None     # il punto rompe i Secrets
    assert accesso.errore_nome("ab", []) is not None


def test_utenti_secrets_e_database():
    from basket.note import Archivio
    arch = Archivio("sqlite://")
    arch.add_user("Luiss-Staff", accesso.hash_password("provvisoria-1"), "Luiss Roma", "staff", "pier")
    db = arch.users()
    assert db["luiss-staff"]["cambio_password"] and db["luiss-staff"]["attivo"]
    sec = {"pier": {"password_hash": accesso.hash_password("riserva-12345"), "ruolo": "admin"},
           "luiss-staff": {"password_hash": accesso.hash_password("dai-secrets-1"), "club": "Luiss Roma"}}
    tutti = accesso.unisci(sec, db)
    assert tutti["pier"]["fonte"] == "secrets"
    assert tutti["luiss-staff"]["fonte"] == "secrets"          # a parità di nome vince il Secrets
    ok = accesso.authenticate(accesso.unisci({}, db), "luiss-staff", "provvisoria-1")
    assert ok["fonte"] == "database" and ok["cambio"] is True
    arch.set_password("luiss-staff", accesso.hash_password("la-mia-password"), cambio=False)
    assert accesso.authenticate(accesso.unisci({}, arch.users()), "luiss-staff", "provvisoria-1") is None
    assert accesso.authenticate(accesso.unisci({}, arch.users()), "luiss-staff", "la-mia-password")["cambio"] is False
    arch.set_active("luiss-staff", False)
    assert "luiss-staff" not in arch.users() and "luiss-staff" in arch.users(anche_disattivi=True)


def test_regole_nuova_password_e_brand():
    assert accesso.errore_password("corta", "corta") is not None
    assert accesso.errore_password("abbastanza-lunga", "diversa-lunga") is not None
    assert accesso.errore_password("stessa-password", "stessa-password", "stessa-password") is not None
    assert accesso.errore_password("nuova-password", "nuova-password", "vecchia-password") is None
    from basket.note import Archivio
    arch = Archivio("sqlite://")
    arch.set_brand(9583, {"primario": "#0b2a5b", "secondario": None})
    assert arch.brand(9583) == {"primario": "#0b2a5b"} and arch.brand(1) == {}


def test_connection_string_incollata_com_e():
    from basket.note import normalizza_url
    neon = "postgresql://u:p@ep-x.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    assert normalizza_url(neon) == neon.replace("postgresql://", "postgresql+psycopg2://")
    assert normalizza_url(" postgres://u:p@h/db ") == "postgresql+psycopg2://u:p@h/db"
    assert normalizza_url("psql 'postgresql://u:p@h/db'") == "postgresql+psycopg2://u:p@h/db"
    assert normalizza_url("postgresql+psycopg2://u:p@h/db") == "postgresql+psycopg2://u:p@h/db"
