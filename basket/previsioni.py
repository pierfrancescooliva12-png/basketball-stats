"""Previsioni: forza delle squadre, probabilità di vittoria, simulazione della stagione.

Modello semplice e trasparente:
    margine atteso = (Net rating casa − Net rating ospite) × possessi / 100 + vantaggio campo
    probabilità di vittoria = Φ(margine atteso / σ), con σ ≈ 11 punti
La forza di ogni squadra è stimata in modo bayesiano: in partenza le squadre sono disperse
attorno a 0 con deviazione SD_FORZA (punti per 100 possessi); ogni partita aggiunge
un'osservazione rumorosa (SD_PARTITA). Ne seguono
    forza = Net rating × g / (g + K),   K = SD_PARTITA² / SD_FORZA²
e un'incertezza residua che nella simulazione viene estratta a ogni stagione simulata:
a inizio stagione le previsioni restano prudenti.
"""

import math

import numpy as np
import pandas as pd

from . import analysis as A
from . import config

SIGMA = 11.0              # deviazione standard del margine di una partita (punti)
SD_FORZA = 7.0            # dispersione della forza tra le squadre (Net rating)
SD_PARTITA = 15.0         # rumore del Net rating di una singola partita
K_RESTRINGIMENTO = SD_PARTITA ** 2 / SD_FORZA ** 2
VANTAGGIO_CAMPO_DEFAULT = 3.0


def _phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def home_advantage(conn, campionato_id: str) -> float:
    """Scarto medio a favore della squadra di casa nelle partite in archivio del campionato."""
    r = conn.execute("SELECT AVG(punti_casa - punti_ospite), COUNT(*) FROM partite "
                     "WHERE campionato_id = ?", (campionato_id,)).fetchone()
    if not r or not r[1] or r[1] < 30:
        return VANTAGGIO_CAMPO_DEFAULT
    # media con la stima di default, pesata sul numero di partite
    w = min(1.0, r[1] / 300)
    return float(w * r[0] + (1 - w) * VANTAGGIO_CAMPO_DEFAULT)


PESO_STAGIONE_PRECEDENTE = 0.5   # le rose cambiano: si conserva metà del Net rating


def prior_from_previous(conn, stagione: str) -> dict:
    """Punto di partenza della forza: metà del Net rating della stagione precedente."""
    stagioni = sorted(config.STAGIONI)
    prev = [x for x in stagioni if x < stagione]
    if not prev:
        return {}
    bs = A.load_box_squadra(conn, prev[-1])
    if bs.empty:
        return {}
    t = A.team_summary(bs)
    return dict(zip(t["squadra_id"], PESO_STAGIONE_PRECEDENTE * t["net_rtg"].fillna(0)))


def strengths(bs: pd.DataFrame, prior: dict | None = None) -> pd.DataFrame:
    """Forza per squadra: media bayesiana tra punto di partenza e Net rating attuale."""
    t = A.team_summary(bs)
    g = t["partite_avanzate"].astype(float)
    m0 = t["squadra_id"].map(prior or {}).fillna(0.0)
    t["forza"] = (m0 * K_RESTRINGIMENTO + t["net_rtg"].fillna(0) * g) / (g + K_RESTRINGIMENTO)
    t["incertezza"] = np.sqrt(1 / (1 / SD_FORZA ** 2 + g / SD_PARTITA ** 2))
    t["pace_stima"] = t["pace"].fillna(t["pace"].mean())
    return t[["campionato_id", "squadra_id", "squadra", "partite", "vinte", "perse_partite",
              "net_rtg", "forza", "incertezza", "ortg", "drtg", "pace_stima"]]


def predict(forze: pd.DataFrame, casa_id: int, ospite_id: int, hca: float,
            ortg_medio: float = 106.0) -> dict:
    f = forze.set_index("squadra_id")
    h, a = f.loc[casa_id], f.loc[ospite_id]
    poss = (h["pace_stima"] + a["pace_stima"]) / 2
    margine = (h["forza"] - a["forza"]) * poss / 100 + hca
    p = _phi(margine / SIGMA)
    base = ortg_medio * poss / 100
    return {"prob_casa": p, "margine": margine, "possessi": poss,
            "punti_casa": base + margine / 2, "punti_ospite": base - margine / 2}


def simulate(conn, campionato_id: str, stagione: str = config.STAGIONE, n: int = 5000,
             seed: int = 7) -> pd.DataFrame:
    """Simula il resto del calendario: vittorie finali attese e probabilità per ogni zona
    della classifica."""
    bs = A.load_box_squadra(conn, stagione)
    bs = bs[bs["campionato_id"] == campionato_id]
    if bs.empty:
        return pd.DataFrame()
    forze = strengths(bs, prior_from_previous(conn, stagione))
    hca = home_advantage(conn, campionato_id)
    rest = pd.read_sql_query(
        "SELECT squadra_casa_id, squadra_ospite_id FROM calendario WHERE campionato_id = ? "
        "AND stagione = ? AND stato != 'finished'", conn, params=(campionato_id, stagione))
    teams = forze["squadra_id"].tolist()
    # squadre presenti solo nel calendario (nessuna partita giocata)
    extra = set(rest["squadra_casa_id"]) | set(rest["squadra_ospite_id"])
    for sid in extra - set(teams):
        forze = pd.concat([forze, pd.DataFrame([{"squadra_id": sid, "forza": 0.0, "vinte": 0,
                                                 "incertezza": SD_FORZA,
                                                 "pace_stima": forze["pace_stima"].mean()}])])
        teams.append(sid)
    idx = {s: i for i, s in enumerate(teams)}
    wins0 = np.array([forze.set_index("squadra_id").loc[s, "vinte"] for s in teams], float)
    diff0 = bs.groupby("squadra_id").apply(lambda x: (x["punti"] - x["punti_subiti"]).sum(),
                                           include_groups=False).reindex(teams).fillna(0).values
    rng = np.random.default_rng(seed)
    wins = np.tile(wins0, (n, 1))
    if len(rest):
        f = forze.set_index("squadra_id").loc[teams]
        # forza estratta per ogni stagione simulata (incertezza della stima)
        forza_sim = f["forza"].values[None, :] + rng.normal(size=(n, len(teams))) * \
            f["incertezza"].values[None, :]
        pace = f["pace_stima"].values
        hi = rest["squadra_casa_id"].map(idx).values
        ai = rest["squadra_ospite_id"].map(idx).values
        poss = (pace[hi] + pace[ai]) / 2
        margine = (forza_sim[:, hi] - forza_sim[:, ai]) * poss[None, :] / 100 + hca
        esiti = rng.normal(size=margine.shape) * SIGMA < margine
        for j in range(len(rest)):
            wins[:, hi[j]] += esiti[:, j]
            wins[:, ai[j]] += ~esiti[:, j]
    # posizione finale: vittorie, poi differenza punti attuale, poi sorteggio
    key = wins * 1e6 + diff0[None, :] + rng.random((n, len(teams)))
    pos = (-key).argsort(axis=1).argsort(axis=1) + 1
    out = pd.DataFrame({"squadra_id": teams, "vinte_ora": wins0,
                        "vinte_finali": wins.mean(axis=0),
                        "posizione_media": pos.mean(axis=0)})
    for label, (lo, hi_) in config.ZONE_CLASSIFICA.get(campionato_id, {}).items():
        out[label] = 100 * ((pos >= lo) & (pos <= hi_)).mean(axis=0)
    out["partite_rimanenti"] = [int(((rest.squadra_casa_id == s) | (rest.squadra_ospite_id == s))
                                    .sum()) for s in teams]
    nomi = dict(conn.execute("SELECT squadra_id, nome FROM squadre").fetchall())
    out["squadra"] = out["squadra_id"].map(nomi)
    return out.sort_values("posizione_media")


def head_to_head(conn, a: int, b: int) -> pd.DataFrame:
    """Precedenti tra due squadre in archivio (tutte le stagioni)."""
    df = pd.read_sql_query(
        """SELECT p.stagione, p.giornata, p.data, sc.nome AS casa, p.punti_casa, p.punti_ospite,
                  so.nome AS ospite, p.squadra_casa_id
           FROM partite p JOIN squadre sc ON sc.squadra_id = p.squadra_casa_id
           JOIN squadre so ON so.squadra_id = p.squadra_ospite_id
           WHERE (p.squadra_casa_id = :a AND p.squadra_ospite_id = :b)
              OR (p.squadra_casa_id = :b AND p.squadra_ospite_id = :a)
           ORDER BY p.data DESC""", conn, params={"a": a, "b": b})
    df["stagione"] = df["stagione"].map(config.STAGIONI).fillna(df["stagione"])
    vince_a = np.where(df["squadra_casa_id"] == a, df["punti_casa"] > df["punti_ospite"],
                       df["punti_ospite"] > df["punti_casa"])
    df["vincente"] = np.where(vince_a, "A", "B")
    return df.drop(columns="squadra_casa_id")
