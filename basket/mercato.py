"""Mercato e reclutamento: anagrafica, storico per stagione, ricerca, giocatori simili."""

from datetime import date

import numpy as np
import pandas as pd

from . import analysis as A
from . import config

# Caratteristiche usate per la somiglianza tra giocatori (profilo statistico)
SIMILARITY_FEATURES = ["punti_p40", "rimb_off_p40", "rimb_dif_p40", "assist_p40", "perse_p40",
                       "recuperate_p40", "stoppate_p40", "t3a_rate", "ft_rate", "ts_pct",
                       "usg_pct", "ast_pct", "trb_pct"]


def load_bio(conn) -> pd.DataFrame:
    from .pbp import _has_table
    bio = pd.read_sql_query("SELECT * FROM giocatori_info", conn) \
        if _has_table(conn, "giocatori_info") else pd.DataFrame()
    if bio.empty:
        return pd.DataFrame(columns=["giocatore_id", "eta", "nazionalita", "italiano",
                                     "altezza_cm", "peso_kg", "data_nascita"])
    oggi = date.today()
    nascita = pd.to_datetime(bio["data_nascita"], errors="coerce")
    bio["eta"] = ((pd.Timestamp(oggi) - nascita).dt.days / 365.25).round(1)
    bio["italiano"] = bio["nazionalita"].eq("ITA")
    return bio


def season_lines(conn, stagioni: list[str] | None = None) -> pd.DataFrame:
    """Riepilogo giocatori per ogni stagione in archivio (una riga per giocatore, squadra,
    stagione), con anagrafica e ruolo stimato."""
    frames = []
    for st in stagioni or list(config.STAGIONI):
        bs = A.load_box_squadra(conn, st)
        if bs.empty:
            continue
        bg = A.load_box_giocatore(conn, st)
        p = A.player_summary(bg, bs)
        p["stagione"] = st
        frames.append(p)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out = out.merge(load_bio(conn)[["giocatore_id", "eta", "nazionalita", "italiano",
                                    "altezza_cm", "peso_kg"]], on="giocatore_id", how="left")
    out["ruolo"] = estimate_role(out)
    out["stagione_label"] = out["stagione"].map(config.STAGIONI)
    out["categoria"] = np.where(out["campionato_id"] == "ita2", "A2", "B Nazionale")
    return out


def estimate_role(p: pd.DataFrame) -> pd.Series:
    """Ruolo stimato dai numeri (il sito non lo pubblica): lungo, esterno, play."""
    alt = p.get("altezza_cm", pd.Series(np.nan, index=p.index))
    lungo = (alt >= 203) | ((p["trb_pct"] >= 14) & ~(alt <= 193))
    play = ~lungo & ((p["ast_pct"] >= 22) | (alt <= 186))
    return pd.Series(np.select([lungo, play], ["Lungo", "Play / guardia"], "Esterno / ala"),
                     index=p.index)


def similar(pool: pd.DataFrame, giocatore_id: str, stagione: str, n: int = 10,
            min_minuti: float = 10.0) -> pd.DataFrame:
    """Giocatori con il profilo statistico più simile (distanza sulle caratteristiche
    standardizzate). Confronta tutte le stagioni e i campionati presenti in `pool`."""
    ref = pool[(pool["giocatore_id"] == giocatore_id) & (pool["stagione"] == stagione)]
    if ref.empty:
        return pd.DataFrame()
    ref = ref.sort_values("minuti", ascending=False).iloc[0]
    cand = pool[(pool["minuti_pg"] >= min_minuti) & (pool["partite"] >= 2)].copy()
    feats = [f for f in SIMILARITY_FEATURES if f in cand.columns]
    X = cand[feats].astype(float)
    mu, sd = X.mean(), X.std().replace(0, 1)
    Z = ((X - mu) / sd).fillna(0)
    zr = ((ref[feats].astype(float) - mu) / sd).fillna(0)
    d = np.sqrt(((Z - zr) ** 2).sum(axis=1))
    cand["distanza"] = d
    cand["somiglianza"] = (100 * np.exp(-(d ** 2) / (2 * len(feats)))).round(0)
    cand = cand[~((cand["giocatore_id"] == giocatore_id) & (cand["stagione"] == stagione))]
    return cand.sort_values("distanza").head(n)


def progression(lines: pd.DataFrame, da: str, a: str) -> pd.DataFrame:
    """Variazione tra due stagioni per i giocatori presenti in entrambe."""
    cols = ["punti_p40", "game_score_p40", "ts_pct", "usg_pct", "minuti_pg", "punti_pg"]
    x = lines[lines["stagione"] == da].sort_values("minuti").groupby("giocatore_id").tail(1)
    y = lines[lines["stagione"] == a].sort_values("minuti").groupby("giocatore_id").tail(1)
    m = y[["giocatore_id", "giocatore", "squadra", "categoria", "eta"] + cols].merge(
        x[["giocatore_id", "squadra", "categoria"] + cols], on="giocatore_id",
        suffixes=("", "_prima"))
    for c in cols:
        m[f"delta_{c}"] = m[c] - m[f"{c}_prima"]
    return m


def prospects(lines: pd.DataFrame, stagione: str, eta_max: float = 25,
              min_minuti: float = 15) -> pd.DataFrame:
    """Giocatori di B Nazionale da tenere d'occhio per l'A2: giovani, minuti importanti,
    alto rendimento per 40 minuti."""
    b = lines[(lines["stagione"] == stagione) & (lines["categoria"] == "B Nazionale")
              & (lines["minuti_pg"] >= min_minuti)].copy()
    if "eta" in b:
        b = b[b["eta"].isna() | (b["eta"] <= eta_max)]
    b["indice"] = b["game_score_p40"].rank(pct=True) * 50 + b["ts_pct"].rank(pct=True) * 25 + \
        b["usg_pct"].rank(pct=True) * 25
    return b.sort_values("indice", ascending=False)
