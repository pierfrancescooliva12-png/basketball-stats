"""Stato condiviso della dashboard: dati in cache, filtri, utente, archivio note."""

from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

from basket import config, db, mercato
from basket.contesto import Contesto
from basket.note import Archivio


def secrets() -> dict:
    try:
        return dict(st.secrets)
    except Exception:  # noqa: BLE001  (nessun file secrets: modalità demo)
        return {}


@st.cache_resource(show_spinner="Preparo le analisi…")
def contesto(db_mtime: float, stagione: str) -> Contesto:
    ctx = Contesto(db.connect(config.DB_PATH, readonly=True), stagione)
    _ = ctx.players, ctx.profile        # calcolo iniziale
    return ctx


@st.cache_resource(show_spinner="Carico l'archivio delle stagioni…")
def storico(db_mtime: float) -> pd.DataFrame:
    return mercato.season_lines(db.connect(config.DB_PATH, readonly=True))


@st.cache_resource
def archivio(url: str) -> Archivio:
    return Archivio(url)


def archivio_url() -> str:
    s = secrets()
    try:
        return s["database"]["url"]
    except (KeyError, TypeError):
        return f"sqlite:///{config.ROOT / 'data' / 'note_locali.sqlite'}"


def stagioni_disponibili() -> list[str]:
    conn = db.connect(config.DB_PATH, readonly=True)
    have = {r[0] for r in conn.execute("SELECT DISTINCT stagione FROM partite")}
    return [s for s in config.STAGIONI if s in have] or [config.STAGIONE]


@dataclass
class App:
    ctx: Contesto
    mtime: float
    stagione: str
    camp: str
    sq: int | None
    gsel: tuple | None
    utente: dict
    archivio: Archivio
    players: pd.DataFrame = field(default=None)
    profile: pd.DataFrame = field(default=None)
    bs_c: pd.DataFrame = field(default=None)
    bg_c: pd.DataFrame = field(default=None)

    @property
    def club(self) -> str:
        return self.utente.get("club") or "demo"

    @property
    def autore(self) -> str:
        return self.utente.get("username", "demo")

    @property
    def mia_squadra(self) -> int | None:
        """Squadra del club dell'utente (se riconosciuta), altrimenti quella del filtro."""
        mid = self.utente.get("squadra_id")
        return mid if mid in set(self.profile["squadra_id"]) else self.sq


@st.cache_resource
def report(db_mtime: float, stagione: str, squadra_id: int):
    from basket import scouting
    return scouting.build_report(db.connect(config.DB_PATH, readonly=True), squadra_id, stagione)


@st.cache_data
def partite_df(db_mtime: float, stagione: str) -> pd.DataFrame:
    conn = db.connect(config.DB_PATH, readonly=True)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(calendario)")}
    stream = "c.stream_url" if "stream_url" in cols else "NULL AS stream_url"
    return pd.read_sql_query(
        f"""SELECT p.*, sc.nome AS casa, so.nome AS ospite, {stream}
            FROM partite p
            JOIN squadre sc ON sc.squadra_id = p.squadra_casa_id
            JOIN squadre so ON so.squadra_id = p.squadra_ospite_id
            LEFT JOIN calendario c USING (partita_id)
            WHERE p.stagione = ?""", conn, params=(stagione,))
