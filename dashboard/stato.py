"""Stato condiviso della dashboard: dati in cache, filtri, utente, archivio note."""

from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

from basket import config, db, mercato
from basket.contesto import Contesto
from basket.note import Archivio, normalizza_url


def secrets() -> dict:
    try:
        return dict(st.secrets)
    except Exception:  # noqa: BLE001  (nessun file secrets: modalità demo)
        return {}


def brand_club(squadra_id: int) -> dict:
    """Correzioni al brand del club: Secrets ([brand.<id squadra>]) e, sopra, quelle salvate
    dall'Amministrazione nel database."""
    b = secrets().get("brand") or {}
    out = dict(b.get(str(squadra_id)) or b.get(squadra_id) or {})
    try:
        out.update(archivio(archivio_url()).brand(squadra_id))
    except Exception:
        pass
    return out


@st.cache_data(ttl=6 * 3600, show_spinner=False, max_entries=80)
def _tema(squadra_id: int, nome: str, correzioni_json: str, logo_ok: bool):
    import json
    from basket import brand
    return brand.tema(squadra_id, nome, json.loads(correzioni_json))


def tema_club(squadra_id: int, nome: str, correzioni_json: str):
    """Tema del club (logo scaricato una volta, colori dal logo o dai Secrets). Se il logo
    non era arrivato (sito lento) il tema si ricalcola appena arriva, senza aspettare ore."""
    import json
    from basket import brand
    url = json.loads(correzioni_json).get("logo_url")
    try:
        logo_ok = brand.logo(squadra_id, url) is not None
    except Exception:
        logo_ok = False
    return _tema(squadra_id, nome, correzioni_json, logo_ok)


def tema_squadra(squadra_id: int, nome: str):
    """Colori e logo di una squadra qualsiasi (con le correzioni salvate); None se non disponibili."""
    import json
    try:
        return tema_club(int(squadra_id), nome, json.dumps(brand_club(int(squadra_id)), sort_keys=True))
    except Exception:
        return None


@st.cache_resource
def _miniature() -> dict:
    return {}


def loghi_piccoli(squadre: tuple) -> dict:
    """Loghi in miniatura per le tabelle, scaricati in parallelo. Si ricordano solo quelli
    trovati: i mancanti si riprovano (il download stesso aspetta qualche minuto tra un
    tentativo e l'altro se il sito non risponde)."""
    from concurrent.futures import ThreadPoolExecutor
    from basket import brand
    memo = _miniature()
    mancanti = [s for s in squadre if s not in memo]
    if mancanti:
        url = {}
        for sid in mancanti:
            try:
                url[sid] = brand_club(int(sid)).get("logo_url")
            except Exception:
                url[sid] = None

        def uno(sid):
            try:
                return sid, brand.miniatura(brand.logo(sid, url.get(sid)))
            except Exception:
                return sid, None
        with ThreadPoolExecutor(max_workers=8) as ex:
            for sid, uri in ex.map(uno, mancanti):
                if uri:
                    memo[sid] = uri
    return {s: memo.get(s) for s in squadre}


@st.cache_resource(show_spinner="Preparo le analisi…", max_entries=2)
def contesto(db_mtime: float, stagione: str) -> Contesto:
    ctx = Contesto(db.connect(config.DB_PATH, readonly=True), stagione)
    _ = ctx.players, ctx.profile        # calcolo iniziale
    return ctx


@st.cache_resource(show_spinner="Carico l'archivio delle stagioni…", max_entries=1)
def storico(db_mtime: float) -> pd.DataFrame:
    return mercato.season_lines(db.connect(config.DB_PATH, readonly=True))


@st.cache_resource
def archivio(url: str) -> Archivio:
    return Archivio(url)


def archivio_url() -> str:
    s = secrets()
    try:
        return normalizza_url(s["database"]["url"])
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
    esperto: bool = False
    tema: object = None           # brand del club (basket.brand.Tema), se c'è

    @property
    def club(self) -> str:
        if self.utente.get("demo"):
            return "demo"
        # l'amministratore senza club ha note e liste proprie
        return self.utente.get("club") or f"admin:{self.utente.get('username')}"

    @property
    def autore(self) -> str:
        return self.utente.get("username", "demo")

    @property
    def mia_squadra(self) -> int | None:
        """Squadra del club dell'utente (se riconosciuta), altrimenti quella del filtro."""
        mid = self.utente.get("squadra_id")
        return mid if mid in set(self.profile["squadra_id"]) else self.sq


@st.cache_resource(max_entries=12)
def report(db_mtime: float, stagione: str, squadra_id: int):
    from basket import scouting
    return scouting.build_report(db.connect(config.DB_PATH, readonly=True), squadra_id, stagione)


@st.cache_data(max_entries=2)
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
