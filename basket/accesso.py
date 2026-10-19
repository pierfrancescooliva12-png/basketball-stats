"""Accesso alla piattaforma: utenti per club con password cifrata.

Gli utenti si configurano nei "secrets" di Streamlit (Streamlit Cloud: App > Settings >
Secrets), mai nel repository:

    [utenti.mario]
    password_hash = "pbkdf2_sha256$200000$..."
    club = "Unieuro Forlì"          # nome della squadra (anche parziale); vuoto per admin
    ruolo = "staff"                 # staff | admin

Un admin senza club vede tutto e sceglie la squadra da seguire nella Home.

Per creare l'hash di una password:
    python -m basket.accesso nuovo mario "Unieuro Forlì"

Senza la sezione [utenti] la dashboard funziona in modalità demo (senza login).
"""

import base64
import getpass
import hashlib
import hmac
import os
import re
import secrets
import sys

ITERAZIONI = 200_000
TENTATIVI = 5              # errori consecutivi prima del blocco
BLOCCO_S = 60              # primo blocco in secondi, poi raddoppia


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


def unisci(da_secrets: dict, da_database: dict) -> dict:
    """Utenti dei Secrets (amministratori, accesso di riserva) e del database (club gestiti
    dall'Amministrazione). A parità di nome vince il Secrets."""
    out = {k.lower(): {**v, "fonte": "database"} for k, v in (da_database or {}).items()}
    out.update({k.lower(): {**dict(v), "fonte": "secrets"} for k, v in (da_secrets or {}).items()})
    return out


def authenticate(utenti: dict, username: str, password: str) -> dict | None:
    """Restituisce i dati dell'utente se le credenziali sono corrette."""
    u = utenti.get((username or "").strip().lower())
    if not u or not verify_password(password or "", u.get("password_hash", "")):
        return None
    return {"username": username.strip().lower(), "club": u.get("club"),
            "ruolo": u.get("ruolo", "staff"), "fonte": u.get("fonte", "secrets"),
            "cambio": bool(u.get("cambio_password"))}


def errore_password(nuova: str, ripeti: str, vecchia: str | None = None) -> str | None:
    """Motivo per cui la nuova password non va bene (None se va bene)."""
    if len(nuova or "") < 10:
        return "deve avere almeno 10 caratteri"
    if nuova != ripeti:
        return "le due password non coincidono"
    if vecchia is not None and nuova == vecchia:
        return "deve essere diversa da quella attuale"
    return None


# senza caratteri che si confondono (0/O, 1/l/I) per dettarla o copiarla a mano
_ALFABETO = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def genera_password(gruppi: int = 3, lunghezza: int = 4) -> str:
    """Password casuale leggibile, es. "k7Pq-Mx3a-Tn9w" (circa 70 bit)."""
    return "-".join("".join(secrets.choice(_ALFABETO) for _ in range(lunghezza))
                    for _ in range(gruppi))


def errore_nome(utente: str, esistenti) -> str | None:
    """Motivo per cui il nome utente non va bene (None se va bene)."""
    u = (utente or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,31}", u):
        return "da 3 a 32 caratteri: lettere minuscole, numeri, trattino o trattino basso"
    if u in {e.lower() for e in esistenti}:
        return "esiste già"
    return None


def blocco_toml(utente: str, password: str, club: str | None = None, ruolo: str = "staff") -> str:
    """Il blocco da incollare nei secrets di Streamlit (solo l'hash, mai la password)."""
    righe = [f"[utenti.{utente.strip().lower()}]", f'password_hash = "{hash_password(password)}"']
    if club:
        righe.append(f'club = "{club}"')
    righe.append(f'ruolo = "{ruolo}"')
    return "\n".join(righe)


def attesa(stato: dict, ora: float) -> int:
    """Secondi da aspettare prima di poter riprovare (0 se si può)."""
    return max(0, int(stato.get("fino", 0) - ora + 0.999))


def registra(stato: dict, ok: bool, ora: float) -> dict:
    """Aggiorna il conteggio degli errori: dopo TENTATIVI errori di fila blocca per BLOCCO_S
    secondi, raddoppiando a ogni blocco successivo. Un accesso riuscito azzera tutto."""
    if ok:
        return {}
    errori = stato.get("errori", 0) + 1
    blocchi = stato.get("blocchi", 0)
    out = {"errori": errori, "blocchi": blocchi, "fino": stato.get("fino", 0)}
    if errori >= TENTATIVI:
        out.update(errori=0, blocchi=blocchi + 1, fino=ora + BLOCCO_S * 2 ** blocchi)
    return out


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 3 or args[0] != "nuovo":
        print('Uso: python -m basket.accesso nuovo <utente> "<squadra>" [admin]  '
              '(squadra "" per un admin senza club)')
        return 1
    utente, club = args[1].lower(), args[2]
    ruolo = args[3] if len(args) > 3 else "staff"
    pw = getpass.getpass("Password: ")
    if pw != getpass.getpass("Ripeti la password: "):
        print("Le password non coincidono")
        return 1
    print("\nIncolla nei secrets di Streamlit:\n")
    print(blocco_toml(utente, pw, club or None, ruolo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
