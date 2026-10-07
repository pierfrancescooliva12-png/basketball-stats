"""Previsioni: forza delle squadre, probabilità di vittoria, simulazione della stagione.

Modello semplice e trasparente:
    margine atteso = (Net rating casa − Net rating ospite) × possessi / 100 + vantaggio campo
    probabilità di vittoria = Φ(margine atteso / σ), con σ = 12,5 punti
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

# Parametri tarati sulla validazione retrospettiva delle stagioni 2024/25 e 2025/26
# (python -m basket.validazione): migliore Brier score e calibrazione.
SIGMA = 12.5              # deviazione standard del margine di una partita (punti)
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


PESO_STAGIONE_PRECEDENTE = 0.35  # le rose cambiano: si conserva un terzo del Net rating


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
    # scomposizione della forza: stagione precedente + attacco + difesa di quest'anno
    w = g / (g + K_RESTRINGIMENTO)
    lega = t["ortg"].mean()
    t["parte_precedente"] = m0 * K_RESTRINGIMENTO / (g + K_RESTRINGIMENTO)
    t["parte_attacco"] = ((t["ortg"] - lega) * w).fillna(0)
    t["parte_difesa"] = ((lega - t["drtg"]) * w).fillna(0)
    return t[["campionato_id", "squadra_id", "squadra", "partite", "vinte", "perse_partite",
              "net_rtg", "forza", "incertezza", "ortg", "drtg", "pace_stima",
              "parte_precedente", "parte_attacco", "parte_difesa"]]


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


def spiega(forze: pd.DataFrame, casa_id: int, ospite_id: int, hca: float,
           extra: dict | None = None) -> pd.DataFrame:
    """Da cosa dipende la previsione: contributo di ogni fattore al margine atteso (punti a
    favore della squadra di casa) e alla probabilità di vittoria.

    Il contributo in probabilità di un fattore è quanto cambierebbe la probabilità della
    squadra di casa togliendo solo quel fattore. extra: altri fattori già in punti
    (es. {"Assenze": -2.1})."""
    f = forze.set_index("squadra_id")
    h, a = f.loc[casa_id], f.loc[ospite_id]
    poss = (h["pace_stima"] + a["pace_stima"]) / 2
    fattori = {
        "Fattore campo": hca,
        "Attacco": (h["parte_attacco"] - a["parte_attacco"]) * poss / 100,
        "Difesa": (h["parte_difesa"] - a["parte_difesa"]) * poss / 100,
        "Stagione precedente": (h["parte_precedente"] - a["parte_precedente"]) * poss / 100,
    }
    fattori.update(extra or {})
    margine = sum(fattori.values())
    p = _phi(margine / SIGMA)
    righe = [{"fattore": k, "punti": v, "probabilita": 100 * (p - _phi((margine - v) / SIGMA))}
             for k, v in fattori.items()]
    return pd.DataFrame(righe).sort_values("probabilita", key=abs, ascending=False)


# Simulatore "e se": impatto di un'assenza
IMPATTO_MAX = 8.0           # punti per 100 possessi, limite per giocatore
MINUTI_RIFERIMENTO = 800.0  # restringimento dell'On-Off verso 0 con pochi minuti


def impatto_giocatori(players: pd.DataFrame) -> pd.DataFrame:
    """Impatto stimato di ogni giocatore sulla forza della squadra (punti per 100 possessi
    quando è in campo rispetto a chi lo sostituisce).

    Fonte principale: On-Off dalla cronaca, ristretto verso 0 con pochi minuti. Senza
    cronaca: stima dal Game Score per 40 minuti rispetto alla mediana del campionato."""
    p = players.copy()
    gs_med = p[p["minuti_pg"] >= 15].groupby("campionato_id")["game_score_p40"].median()
    box = 0.5 * (p["game_score_p40"] - p["campionato_id"].map(gs_med))
    if "on_off" in p and "minuti_campo" in p:
        mc = p["minuti_campo"].fillna(0)
        oo = p["on_off"] * mc / (mc + MINUTI_RIFERIMENTO)
        p["impatto"] = oo.where(p["on_off"].notna(), box)
        p["fonte_impatto"] = np.where(p["on_off"].notna(), "On-Off (cronaca)", "Box score")
    else:
        p["impatto"] = box
        p["fonte_impatto"] = "Box score"
    p["impatto"] = p["impatto"].fillna(0).clip(-IMPATTO_MAX, IMPATTO_MAX)
    p["quota_minuti"] = (p["minuti_pg"] / 40).clip(0, 1)
    return p


def scenario(forze: pd.DataFrame, players: pd.DataFrame, casa_id: int, ospite_id: int,
             hca: float, assenti_casa=(), assenti_ospite=(), campo_neutro: bool = False,
             correzione_casa: float = 0.0, correzione_ospite: float = 0.0) -> dict:
    """Previsione in uno scenario diverso: giocatori assenti, campo neutro, correzione della
    forza decisa dallo staff (punti per 100 possessi). Restituisce previsione di base,
    previsione nello scenario e scomposizione."""
    base = predict(forze, casa_id, ospite_id, hca)
    imp = impatto_giocatori(players).set_index("giocatore_id")

    def delta(assenti, sid):
        tot = 0.0
        for g in assenti:
            if g in imp.index:
                r = imp.loc[g]
                r = r[r["squadra_id"] == sid].iloc[0] if isinstance(r, pd.DataFrame) else r
                tot -= float(r["impatto"]) * float(r["quota_minuti"])
        return max(tot, -2 * IMPATTO_MAX)

    dc, do = delta(assenti_casa, casa_id), delta(assenti_ospite, ospite_id)
    f = forze.copy()
    f.loc[f["squadra_id"] == casa_id, "forza"] += dc + correzione_casa
    f.loc[f["squadra_id"] == ospite_id, "forza"] += do + correzione_ospite
    h = 0.0 if campo_neutro else hca
    nuovo = predict(f, casa_id, ospite_id, h)
    poss = nuovo["possessi"]
    extra = {}
    if assenti_casa or assenti_ospite:
        extra["Assenze"] = (dc - do) * poss / 100
    if correzione_casa or correzione_ospite:
        extra["Correzione dello staff"] = (correzione_casa - correzione_ospite) * poss / 100
    sp = spiega(forze, casa_id, ospite_id, h, extra)
    return {"base": base, "scenario": nuovo, "spiegazione": sp,
            "delta_casa": dc, "delta_ospite": do}


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
