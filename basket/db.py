"""Database SQLite: schema e scrittura dei dati estratti."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS campionati (
    campionato_id TEXT NOT NULL,          -- codice lega sul sito (ita2, ita3_a, ...)
    stagione      TEXT NOT NULL,          -- codice stagione sul sito (x2627)
    nome          TEXT NOT NULL,
    PRIMARY KEY (campionato_id, stagione)
);

CREATE TABLE IF NOT EXISTS squadre (
    squadra_id    INTEGER PRIMARY KEY,    -- id squadra del sito (stabile tra stagioni)
    nome          TEXT NOT NULL,          -- denominazione più recente
    campionato_id TEXT,
    stagione      TEXT
);

CREATE TABLE IF NOT EXISTS giocatori (
    giocatore_id  TEXT PRIMARY KEY,       -- codice giocatore del sito (es. A94671)
    nome          TEXT NOT NULL
);

-- Calendario completo, anche partite non ancora giocate
CREATE TABLE IF NOT EXISTS calendario (
    partita_id        TEXT PRIMARY KEY,   -- {stagione}_{gameid}
    gameid            TEXT NOT NULL,
    campionato_id     TEXT NOT NULL,
    stagione          TEXT NOT NULL,
    giornata          INTEGER NOT NULL,
    data              TEXT,
    ora               TEXT,
    squadra_casa_id   INTEGER NOT NULL,
    squadra_ospite_id INTEGER NOT NULL,
    punti_casa        INTEGER,
    punti_ospite      INTEGER,
    palazzetto        TEXT,
    stato             TEXT
);

-- Partite giocate con box score scaricato
CREATE TABLE IF NOT EXISTS partite (
    partita_id        TEXT PRIMARY KEY,
    gameid            TEXT NOT NULL,
    campionato_id     TEXT NOT NULL,
    stagione          TEXT NOT NULL,
    giornata          INTEGER NOT NULL,
    data              TEXT,
    ora               TEXT,
    squadra_casa_id   INTEGER NOT NULL REFERENCES squadre(squadra_id),
    squadra_ospite_id INTEGER NOT NULL REFERENCES squadre(squadra_id),
    punti_casa        INTEGER NOT NULL,
    punti_ospite      INTEGER NOT NULL,
    palazzetto        TEXT,
    parziali          TEXT,               -- JSON [{periodo, casa, ospite}]
    url               TEXT,
    scaricata_il      TEXT
);

CREATE TABLE IF NOT EXISTS box_giocatore (
    partita_id      TEXT NOT NULL REFERENCES partite(partita_id),
    giocatore_id    TEXT NOT NULL REFERENCES giocatori(giocatore_id),
    squadra_id      INTEGER NOT NULL REFERENCES squadre(squadra_id),
    numero          TEXT,
    quintetto       INTEGER,
    minuti          REAL,
    punti           INTEGER,
    t2m INTEGER, t2a INTEGER,
    t3m INTEGER, t3a INTEGER,
    tlm INTEGER, tla INTEGER,
    rimb_off INTEGER, rimb_dif INTEGER, rimb_tot INTEGER,
    assist INTEGER, perse INTEGER, recuperate INTEGER,
    stoppate INTEGER, stoppate_subite INTEGER,
    falli_commessi INTEGER, falli_subiti INTEGER,
    valutazione INTEGER,
    oer REAL,
    PRIMARY KEY (partita_id, giocatore_id)
);

-- Totali di squadra (comprendono la riga "Squadra": rimbalzi e perse di squadra)
CREATE TABLE IF NOT EXISTS box_squadra (
    partita_id      TEXT NOT NULL REFERENCES partite(partita_id),
    squadra_id      INTEGER NOT NULL REFERENCES squadre(squadra_id),
    avversario_id   INTEGER NOT NULL REFERENCES squadre(squadra_id),
    casa            INTEGER NOT NULL,     -- 1 = in casa, 0 = in trasferta
    minuti          REAL,
    punti           INTEGER,
    punti_subiti    INTEGER,
    t2m INTEGER, t2a INTEGER,
    t3m INTEGER, t3a INTEGER,
    tlm INTEGER, tla INTEGER,
    rimb_off INTEGER, rimb_dif INTEGER, rimb_tot INTEGER,
    assist INTEGER, perse INTEGER, recuperate INTEGER,
    stoppate INTEGER, stoppate_subite INTEGER,
    falli_commessi INTEGER, falli_subiti INTEGER,
    valutazione INTEGER,
    rimb_off_squadra INTEGER, rimb_dif_squadra INTEGER, perse_squadra INTEGER,
    PRIMARY KEY (partita_id, squadra_id)
);

CREATE INDEX IF NOT EXISTS idx_box_giocatore_giocatore ON box_giocatore(giocatore_id);
CREATE INDEX IF NOT EXISTS idx_box_giocatore_squadra ON box_giocatore(squadra_id);
CREATE INDEX IF NOT EXISTS idx_partite_campionato ON partite(campionato_id, stagione);
"""

BOX_FIELDS = [
    "minuti", "punti", "t2m", "t2a", "t3m", "t3a", "tlm", "tla",
    "rimb_off", "rimb_dif", "rimb_tot", "assist", "perse", "recuperate",
    "stoppate", "stoppate_subite", "falli_commessi", "falli_subiti", "valutazione",
]


def connect(path: Path | str = config.DB_PATH, readonly: bool = False) -> sqlite3.Connection:
    path = Path(path)
    if readonly:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.executescript(SCHEMA)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def partita_id(season: str, gameid: str) -> str:
    return f"{season}_{gameid}"


def upsert_campionato(conn, campionato_id: str, stagione: str, nome: str):
    conn.execute(
        "INSERT INTO campionati VALUES (?, ?, ?) "
        "ON CONFLICT(campionato_id, stagione) DO UPDATE SET nome = excluded.nome",
        (campionato_id, stagione, nome),
    )


def upsert_squadra(conn, squadra_id: int, nome: str, campionato_id: str, stagione: str):
    conn.execute(
        "INSERT INTO squadre VALUES (?, ?, ?, ?) ON CONFLICT(squadra_id) DO UPDATE SET "
        "nome = excluded.nome, campionato_id = excluded.campionato_id, stagione = excluded.stagione",
        (squadra_id, nome, campionato_id, stagione),
    )


def save_calendario(conn, games: list[dict]):
    for g in games:
        upsert_squadra(conn, g["squadra_casa_id"], g["squadra_casa"], g["campionato"], g["stagione"])
        upsert_squadra(conn, g["squadra_ospite_id"], g["squadra_ospite"], g["campionato"], g["stagione"])
        conn.execute(
            "INSERT OR REPLACE INTO calendario VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (partita_id(g["stagione"], g["gameid"]), g["gameid"], g["campionato"], g["stagione"],
             g["giornata"], g["data"], g["ora"], g["squadra_casa_id"], g["squadra_ospite_id"],
             g["punti_casa"], g["punti_ospite"], g["palazzetto"], g["stato"]),
        )


def downloaded_ids(conn) -> set[str]:
    return {r[0] for r in conn.execute("SELECT partita_id FROM partite")}


def save_partita(conn, game: dict, box: dict, url: str):
    """Salva una partita e i suoi box score in un'unica transazione."""
    pid = partita_id(game["stagione"], game["gameid"])
    ids = {"casa": game["squadra_casa_id"], "ospite": game["squadra_ospite_id"]}
    for side in ("casa", "ospite"):
        if box[side]["id"] is not None and box[side]["id"] != ids[side]:
            raise ValueError(
                f"{pid}: squadra {side} nel box score ({box[side]['id']}) "
                f"diversa dal calendario ({ids[side]})")
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO partite VALUES (" + ",".join("?" * 15) + ")",
            (pid, game["gameid"], game["campionato"], game["stagione"], game["giornata"],
             game["data"], game["ora"], ids["casa"], ids["ospite"],
             box["casa"]["totali"]["punti"], box["ospite"]["totali"]["punti"],
             game["palazzetto"], json.dumps(box["parziali"]), url,
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        conn.execute("DELETE FROM box_giocatore WHERE partita_id = ?", (pid,))
        conn.execute("DELETE FROM box_squadra WHERE partita_id = ?", (pid,))
        for side, other in (("casa", "ospite"), ("ospite", "casa")):
            team = box[side]
            for p in team["giocatori"]:
                conn.execute(
                    "INSERT INTO giocatori VALUES (?, ?) "
                    "ON CONFLICT(giocatore_id) DO UPDATE SET nome = excluded.nome",
                    (p["giocatore_id"], p["nome"]),
                )
                _insert(
                    conn, "box_giocatore",
                    (pid, p["giocatore_id"], ids[side], p["numero"], int(p["quintetto"]),
                     *[p[f] for f in BOX_FIELDS], p["oer"]),
                )
            tot, sq = team["totali"], team["riga_squadra"] or {}
            _insert(
                conn, "box_squadra",
                (pid, ids[side], ids[other], int(side == "casa"), tot["minuti"], tot["punti"],
                 box[other]["totali"]["punti"],
                 *[tot[f] for f in BOX_FIELDS[2:]],
                 sq.get("rimb_off") or 0, sq.get("rimb_dif") or 0, sq.get("perse") or 0),
            )


def _insert(conn, table: str, values: tuple):
    conn.execute(f"INSERT INTO {table} VALUES ({','.join('?' * len(values))})", values)
