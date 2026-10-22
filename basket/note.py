"""Archivio dello staff: note su giocatori e squadre, liste di osservati, obiettivi.

Ogni dato appartiene a un club: un club non vede mai i dati di un altro.

Dove vengono salvati:
- se nei secrets di Streamlit c'è  [database] url = "postgresql+psycopg2://..."  (per esempio un
  database gratuito su Supabase o Neon), i dati sono permanenti e condivisi tra dispositivi;
- altrimenti in un file locale (data/note_locali.sqlite), che su Streamlit Cloud si perde
  a ogni riavvio dell'app: va bene solo per provare.
"""

import json
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine, text

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS note (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        club TEXT NOT NULL, tipo TEXT NOT NULL, riferimento TEXT NOT NULL,
        testo TEXT NOT NULL, autore TEXT, creata_il TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS osservati (
        club TEXT NOT NULL, lista TEXT NOT NULL, giocatore_id TEXT NOT NULL,
        giocatore TEXT, aggiunto_da TEXT, aggiunto_il TEXT NOT NULL,
        PRIMARY KEY (club, lista, giocatore_id))""",
    """CREATE TABLE IF NOT EXISTS obiettivi (
        club TEXT NOT NULL, metrica TEXT NOT NULL, valore REAL NOT NULL,
        PRIMARY KEY (club, metrica))""",
    """CREATE TABLE IF NOT EXISTS giochi (
        club TEXT NOT NULL, gioco_id TEXT NOT NULL, riferimento TEXT NOT NULL,
        nome TEXT, dati TEXT NOT NULL, autore TEXT, aggiornato_il TEXT NOT NULL,
        PRIMARY KEY (club, gioco_id))""",
    # programmi di allenamento (sedute, esercizi, cosa stampare): un JSON per programma
    """CREATE TABLE IF NOT EXISTS programmi (
        club TEXT NOT NULL, programma_id TEXT NOT NULL, nome TEXT, dati TEXT NOT NULL,
        autore TEXT, aggiornato_il TEXT NOT NULL,
        PRIMARY KEY (club, programma_id))""",
    """CREATE TABLE IF NOT EXISTS video_sync (
        club TEXT NOT NULL, partita_id TEXT NOT NULL, inizi TEXT NOT NULL,
        PRIMARY KEY (club, partita_id))""",
    # utenti dei club gestiti dall'Amministrazione (solo l'hash della password)
    """CREATE TABLE IF NOT EXISTS utenti (
        username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, club TEXT, ruolo TEXT NOT NULL,
        attivo INTEGER NOT NULL DEFAULT 1, cambio_password INTEGER NOT NULL DEFAULT 1,
        creato_il TEXT NOT NULL, creato_da TEXT, ultimo_accesso TEXT)""",
    # colori e logo corretti per il brand del club
    """CREATE TABLE IF NOT EXISTS brand (
        squadra_id INTEGER PRIMARY KEY, primario TEXT, secondario TEXT, logo_url TEXT,
        aggiornato_il TEXT NOT NULL, autore TEXT)""",
]


def normalizza_url(url: str) -> str:
    """Accetta la connection string così come la dà Neon o Supabase ("postgresql://..." o
    "postgres://...", anche con "psql '...'" davanti) e la adatta al driver psycopg2."""
    u = str(url).strip().strip("'\"")
    if u.startswith("psql "):
        u = u[5:].strip().strip("'\"")
    for prefisso in ("postgresql://", "postgres://"):
        if u.startswith(prefisso):
            return "postgresql+psycopg2://" + u[len(prefisso):]
    return u


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Archivio:
    def __init__(self, url: str):
        self.url = url
        self.permanente = not url.startswith("sqlite")
        self.engine = create_engine(url, pool_pre_ping=True)
        with self.engine.begin() as c:
            for stmt in SCHEMA:
                if self.permanente and "AUTOINCREMENT" in stmt:   # PostgreSQL
                    stmt = stmt.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
                c.execute(text(stmt))

    # ------------------------------------------------------------ note
    def add_note(self, club: str, tipo: str, riferimento: str, testo: str, autore: str):
        with self.engine.begin() as c:
            c.execute(text("INSERT INTO note (club, tipo, riferimento, testo, autore, creata_il) "
                           "VALUES (:c, :t, :r, :x, :a, :d)"),
                      {"c": club, "t": tipo, "r": str(riferimento), "x": testo.strip(),
                       "a": autore, "d": _now()})

    def notes(self, club: str, tipo: str | None = None, riferimento=None) -> pd.DataFrame:
        q = "SELECT id, tipo, riferimento, testo, autore, creata_il FROM note WHERE club = :c"
        p = {"c": club}
        if tipo:
            q += " AND tipo = :t"
            p["t"] = tipo
        if riferimento is not None:
            q += " AND riferimento = :r"
            p["r"] = str(riferimento)
        with self.engine.connect() as c:
            return pd.read_sql_query(text(q + " ORDER BY creata_il DESC"), c, params=p)

    def delete_note(self, club: str, note_id: int):
        with self.engine.begin() as c:
            c.execute(text("DELETE FROM note WHERE club = :c AND id = :i"),
                      {"c": club, "i": int(note_id)})

    # ------------------------------------------------------------ osservati
    def watch(self, club: str, lista: str, giocatore_id: str, giocatore: str, autore: str):
        with self.engine.begin() as c:
            c.execute(text("DELETE FROM osservati WHERE club = :c AND lista = :l "
                           "AND giocatore_id = :g"), {"c": club, "l": lista, "g": giocatore_id})
            c.execute(text("INSERT INTO osservati VALUES (:c, :l, :g, :n, :a, :d)"),
                      {"c": club, "l": lista, "g": giocatore_id, "n": giocatore, "a": autore,
                       "d": _now()})

    def unwatch(self, club: str, lista: str, giocatore_id: str):
        with self.engine.begin() as c:
            c.execute(text("DELETE FROM osservati WHERE club = :c AND lista = :l "
                           "AND giocatore_id = :g"), {"c": club, "l": lista, "g": giocatore_id})

    def watchlist(self, club: str) -> pd.DataFrame:
        with self.engine.connect() as c:
            return pd.read_sql_query(
                text("SELECT lista, giocatore_id, giocatore, aggiunto_da, aggiunto_il "
                     "FROM osservati WHERE club = :c ORDER BY lista, giocatore"), c,
                params={"c": club})

    # ------------------------------------------------------------ obiettivi
    def set_goals(self, club: str, valori: dict):
        with self.engine.begin() as c:
            for k, v in valori.items():
                c.execute(text("DELETE FROM obiettivi WHERE club = :c AND metrica = :m"),
                          {"c": club, "m": k})
                c.execute(text("INSERT INTO obiettivi VALUES (:c, :m, :v)"),
                          {"c": club, "m": k, "v": float(v)})

    def goals(self, club: str) -> dict:
        with self.engine.connect() as c:
            rows = c.execute(text("SELECT metrica, valore FROM obiettivi WHERE club = :c"),
                             {"c": club}).fetchall()
        return {m: v for m, v in rows}

    # ------------------------------------------------------------ giochi (lavagna)
    def save_play(self, club: str, riferimento, gioco: dict, autore: str):
        """Salva (o sostituisce) un gioco disegnato sulla lavagna. riferimento: la squadra a
        cui appartiene il gioco (la propria o un'avversaria)."""
        with self.engine.begin() as c:
            c.execute(text("DELETE FROM giochi WHERE club = :c AND gioco_id = :g"),
                      {"c": club, "g": str(gioco["id"])})
            c.execute(text("INSERT INTO giochi VALUES (:c, :g, :r, :n, :d, :a, :t)"),
                      {"c": club, "g": str(gioco["id"]), "r": str(riferimento),
                       "n": gioco.get("nome", ""), "d": json.dumps(gioco), "a": autore,
                       "t": _now()})

    def plays(self, club: str, riferimento) -> list[dict]:
        with self.engine.connect() as c:
            rows = c.execute(text("SELECT dati FROM giochi WHERE club = :c AND riferimento = :r "
                                  "ORDER BY nome"), {"c": club, "r": str(riferimento)}).fetchall()
        return [json.loads(r[0]) for r in rows]

    # ------------------------------------------------------------ programmi di allenamento
    def save_program(self, club: str, programma: dict, autore: str):
        """Salva (o sostituisce) un programma di allenamento."""
        with self.engine.begin() as c:
            c.execute(text("DELETE FROM programmi WHERE club = :c AND programma_id = :p"),
                      {"c": club, "p": str(programma["id"])})
            c.execute(text("INSERT INTO programmi VALUES (:c, :p, :n, :d, :a, :t)"),
                      {"c": club, "p": str(programma["id"]), "n": programma.get("nome", ""),
                       "d": json.dumps(programma), "a": autore, "t": _now()})

    def programs(self, club: str) -> list[dict]:
        """Programmi del club, il più recente prima."""
        with self.engine.connect() as c:
            rows = c.execute(text("SELECT dati FROM programmi WHERE club = :c ORDER BY aggiornato_il DESC"),
                             {"c": club}).fetchall()
        return [json.loads(r[0]) for r in rows]

    def delete_program(self, club: str, programma_id: str):
        with self.engine.begin() as c:
            c.execute(text("DELETE FROM programmi WHERE club = :c AND programma_id = :p"),
                      {"c": club, "p": str(programma_id)})

    # ------------------------------------------------------------ sincronizzazione video
    def set_video_sync(self, club: str, partita_id: str, inizi: dict):
        """Minuto del video (in secondi) in cui inizia ogni periodo: {periodo: secondi}."""
        with self.engine.begin() as c:
            c.execute(text("DELETE FROM video_sync WHERE club = :c AND partita_id = :p"),
                      {"c": club, "p": partita_id})
            c.execute(text("INSERT INTO video_sync VALUES (:c, :p, :i)"),
                      {"c": club, "p": partita_id,
                       "i": json.dumps({str(k): v for k, v in inizi.items() if v is not None})})

    def video_sync(self, club: str, partita_id: str) -> dict:
        with self.engine.connect() as c:
            r = c.execute(text("SELECT inizi FROM video_sync WHERE club = :c AND partita_id = :p"),
                          {"c": club, "p": partita_id}).fetchone()
        return {int(k): v for k, v in json.loads(r[0]).items()} if r else {}

    # ------------------------------------------------------------ utenti
    def users(self, anche_disattivi: bool = False) -> dict:
        """{username: {password_hash, club, ruolo, attivo, cambio_password, ...}}"""
        q = "SELECT * FROM utenti" + ("" if anche_disattivi else " WHERE attivo = 1")
        with self.engine.connect() as c:
            rows = c.execute(text(q)).mappings().all()
        return {r["username"]: {**dict(r), "attivo": bool(r["attivo"]),
                                "cambio_password": bool(r["cambio_password"])} for r in rows}

    def add_user(self, username: str, password_hash: str, club: str | None, ruolo: str,
                 autore: str | None = None):
        with self.engine.begin() as c:
            c.execute(text("INSERT INTO utenti (username, password_hash, club, ruolo, attivo, "
                           "cambio_password, creato_il, creato_da) "
                           "VALUES (:u, :h, :c, :r, 1, 1, :d, :a)"),
                      {"u": username.strip().lower(), "h": password_hash, "c": club, "r": ruolo,
                       "d": _now(), "a": autore})

    def set_password(self, username: str, password_hash: str, cambio: bool):
        """Nuova password; cambio=True obbliga a cambiarla al prossimo accesso."""
        with self.engine.begin() as c:
            c.execute(text("UPDATE utenti SET password_hash = :h, cambio_password = :x "
                           "WHERE username = :u"),
                      {"u": username, "h": password_hash, "x": int(cambio)})

    def set_active(self, username: str, attivo: bool):
        with self.engine.begin() as c:
            c.execute(text("UPDATE utenti SET attivo = :a WHERE username = :u"),
                      {"u": username, "a": int(attivo)})

    def touch_login(self, username: str):
        with self.engine.begin() as c:
            c.execute(text("UPDATE utenti SET ultimo_accesso = :d WHERE username = :u"),
                      {"u": username, "d": _now()})

    # ------------------------------------------------------------ brand
    def brand(self, squadra_id: int) -> dict:
        with self.engine.connect() as c:
            r = c.execute(text("SELECT primario, secondario, logo_url FROM brand "
                               "WHERE squadra_id = :s"), {"s": int(squadra_id)}).mappings().first()
        return {k: v for k, v in dict(r).items() if v} if r else {}

    def set_brand(self, squadra_id: int, valori: dict, autore: str | None = None):
        with self.engine.begin() as c:
            c.execute(text("DELETE FROM brand WHERE squadra_id = :s"), {"s": int(squadra_id)})
            c.execute(text("INSERT INTO brand VALUES (:s, :p, :x, :l, :d, :a)"),
                      {"s": int(squadra_id), "p": valori.get("primario"),
                       "x": valori.get("secondario"), "l": valori.get("logo_url"),
                       "d": _now(), "a": autore})

    def delete_play(self, club: str, gioco_id: str):
        with self.engine.begin() as c:
            c.execute(text("DELETE FROM giochi WHERE club = :c AND gioco_id = :g"),
                      {"c": club, "g": str(gioco_id)})
