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
]


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

    def delete_play(self, club: str, gioco_id: str):
        with self.engine.begin() as c:
            c.execute(text("DELETE FROM giochi WHERE club = :c AND gioco_id = :g"),
                      {"c": club, "g": str(gioco_id)})
