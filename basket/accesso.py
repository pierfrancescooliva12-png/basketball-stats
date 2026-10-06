"""Accesso alla piattaforma: utenti per club con password cifrata.

Gli utenti si configurano nei "secrets" di Streamlit (Streamlit Cloud: App > Settings >
Secrets), mai nel repository:

    [utenti.mario]
    password_hash = "pbkdf2_sha256$200000$..."
    club = "Unieuro Forlì"          # nome della squadra (anche parziale)
    ruolo = "staff"                 # staff | admin

Per creare l'hash di una password:
    python -m basket.accesso nuovo mario "Unieuro Forlì"

Senza la sezione [utenti] la dashboard funziona in modalità demo (senza login).
"""

import base64
import getpass
import hashlib
import hmac
import os
import sys

ITERAZIONI = 200_000


def hash_password(password: str, iterazioni: int = ITERAZIONI) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterazioni)
    return "pbkdf2_sha256${}${}${}".format(iterazioni, base64.b64encode(salt).decode(),
                                           base64.b64encode(dk).decode())


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, it, salt_b64, hash_b64 = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64),
                                 int(it))
        return hmac.compare_digest(dk, base64.b64decode(hash_b64))
    except (ValueError, TypeError):
        return False


def authenticate(utenti: dict, username: str, password: str) -> dict | None:
    """Restituisce i dati dell'utente se le credenziali sono corrette."""
    u = utenti.get((username or "").strip().lower())
    if not u or not verify_password(password or "", u.get("password_hash", "")):
        return None
    return {"username": username.strip().lower(), "club": u.get("club"),
            "ruolo": u.get("ruolo", "staff")}


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 3 or args[0] != "nuovo":
        print('Uso: python -m basket.accesso nuovo <utente> "<squadra>" [admin]')
        return 1
    utente, club = args[1].lower(), args[2]
    ruolo = args[3] if len(args) > 3 else "staff"
    pw = getpass.getpass("Password: ")
    if pw != getpass.getpass("Ripeti la password: "):
        print("Le password non coincidono")
        return 1
    print("\nIncolla nei secrets di Streamlit:\n")
    print(f"[utenti.{utente}]\npassword_hash = \"{hash_password(pw)}\"\n"
          f"club = \"{club}\"\nruolo = \"{ruolo}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
