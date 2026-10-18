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
COEF_ROSA = 6.0          # punti per 100 possessi per unità dell'indice della rosa
FATTORE_B_A2 = 0.64      # Game Score per 40' di un giocatore di B quando sale in A2
MINUTI_AFFIDABILITA = 300.0


def prior_from_previous(conn, stagione: str, bg: pd.DataFrame | None = None,
                        valori: pd.DataFrame | None = None) -> dict:
    """Punto di partenza della forza di ogni squadra.

    Se si conoscono i giocatori che stanno giocando nella stagione (bg, box score
    giocatori), si usa la rosa: valore di ciascuno nella stagione precedente (Game Score per
    40' rispetto alla mediana, riportato alla categoria attuale) pesato per la sua quota di
    minuti. Altrimenti un terzo del Net rating della squadra nella stagione precedente.
    Validazione 2025/26: la rosa prevede la forza molto meglio del risultato della squadra
    (correlazione 0,51 contro 0,13) e migliora il Brier score di 0,003."""
    stagioni = sorted(config.STAGIONI)
    prev = [x for x in stagioni if x < stagione]
    if not prev:
        return {}
    bs = A.load_box_squadra(conn, prev[-1])
    if bs.empty:
        return {}
    t = A.team_summary(bs)
    prior = dict(zip(t["squadra_id"], PESO_STAGIONE_PRECEDENTE * t["net_rtg"].fillna(0)))
    if bg is not None and not bg.empty:
        if valori is None:
            valori = valori_giocatori(conn, prev[-1])
        for sid, v in indice_rosa(bg, valori).items():
            prior[sid] = COEF_ROSA * v
    return prior


def valori_giocatori(conn, stagione: str) -> pd.DataFrame:
    """Valore di ogni giocatore in una stagione: Game Score per 40' meno la mediana del
    campionato, nella scala dell'A2 e in quella della B, con la sua affidabilità."""
    bg, bs = A.load_box_giocatore(conn, stagione), A.load_box_squadra(conn, stagione)
    if bg.empty:
        return pd.DataFrame(columns=["rel_a2", "rel_b", "affidabilita"])
    p = A.player_summary(bg, bs)
    p = p[p["minuti"] >= 150].copy()
    a2 = p["campionato_id"] == "ita2"
    med = p[p["minuti_pg"] >= 15].groupby("campionato_id")["game_score_p40"].median()
    med_a2 = med.get("ita2", np.nan)
    med_b = med[[c for c in med.index if c != "ita2"]].mean()
    gs = p["game_score_p40"]
    p["rel_a2"] = np.where(a2, gs, gs * FATTORE_B_A2) - med_a2
    p["rel_b"] = np.where(a2, gs / FATTORE_B_A2, gs) - med_b
    p["affidabilita"] = p["minuti"] / (p["minuti"] + MINUTI_AFFIDABILITA)
    p = p.sort_values("minuti", ascending=False)
    return p.groupby("giocatore_id")[["rel_a2", "rel_b", "affidabilita"]].first()


def indice_rosa(bg: pd.DataFrame, valori: pd.DataFrame) -> pd.Series:
    """Somma, sui giocatori impiegati finora, di quota di minuti × valore della stagione
    precedente. Chi non ha giocato la stagione precedente in A2 o B vale come la mediana."""
    g = bg[bg["minuti"] > 0]
    if g.empty:
        return pd.Series(dtype=float)
    j = g.groupby(["squadra_id", "campionato_id", "giocatore_id"])["minuti"].sum().reset_index()
    j["quota"] = j["minuti"] / j.groupby(["squadra_id", "campionato_id"])["minuti"].transform("sum")
    j = j.join(valori, on="giocatore_id")
    rel = np.where(j["campionato_id"] == "ita2", j["rel_a2"], j["rel_b"])
    j["v"] = np.nan_to_num(rel * j["affidabilita"], nan=0.0) * j["quota"]
    return j.groupby("squadra_id")["v"].sum()


# Correzione per la fortuna nei tiri (validazione 2.215 partite: Brier da 0,2125 a 0,2110,
# errore sul margine da 9,71 a 9,62). Le percentuali da 3 e ai liberi cambiano molto da partita a
# partita per caso: nei punti fatti la percentuale da 3 della squadra conta per il 70% e quella del
# campionato per il 30%; nei punti subiti la percentuale da 3 concessa conta solo per il 20% (la
# difesa la controlla poco) e i liberi degli avversari valgono la media del campionato.
FORTUNA_ATTACCO_3, FORTUNA_DIFESA_3, FORTUNA_ATTACCO_TL = 0.7, 0.2, 0.8


def correggi_fortuna(bs: pd.DataFrame) -> pd.DataFrame:
    """Punti fatti e subiti di ogni partita come se le percentuali da 3 e ai liberi fossero quelle
    attese (della squadra, riportate verso la media del campionato), non quelle della serata."""
    b = bs.copy()
    if b.empty or not {"t3a", "opp_t3a", "tla", "opp_tla"} <= set(b.columns):
        return b
    l3 = b["t3m"].sum() / max(1, b["t3a"].sum())
    lf = b["tlm"].sum() / max(1, b["tla"].sum())
    g = b.groupby("squadra_id")
    quota = lambda m, a: g[m].transform("sum") / g[a].transform("sum").clip(lower=1)  # noqa: E731
    e3o = FORTUNA_ATTACCO_3 * quota("t3m", "t3a") + (1 - FORTUNA_ATTACCO_3) * l3
    e3d = FORTUNA_DIFESA_3 * quota("opp_t3m", "opp_t3a") + (1 - FORTUNA_DIFESA_3) * l3
    efo = FORTUNA_ATTACCO_TL * quota("tlm", "tla") + (1 - FORTUNA_ATTACCO_TL) * lf
    d_att = 3 * (b["t3m"] - b["t3a"] * e3o) + (b["tlm"] - b["tla"] * efo)
    d_dif = 3 * (b["opp_t3m"] - b["opp_t3a"] * e3d) + (b["opp_tlm"] - b["opp_tla"] * lf)
    b["punti"] = b["punti"] - d_att.fillna(0)
    b["punti_subiti"] = b["punti_subiti"] - d_dif.fillna(0)
    if "opp_punti" in b:
        b["opp_punti"] = b["opp_punti"] - d_dif.fillna(0)
    return b


def strengths(bs: pd.DataFrame, prior: dict | None = None) -> pd.DataFrame:
    """Forza per squadra: media bayesiana tra punto di partenza e Net rating attuale, corretto
    per la fortuna nei tiri. Net rating, ORtg e DRtg restano quelli reali (per la lettura)."""
    reale = A.team_summary(bs)
    t = A.team_summary(correggi_fortuna(bs))
    t = t.merge(reale[["squadra_id", "net_rtg", "ortg", "drtg"]].rename(
        columns={"net_rtg": "net_reale", "ortg": "ortg_reale", "drtg": "drtg_reale"}), on="squadra_id", how="left")
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
    t["ortg_corr"], t["drtg_corr"] = t["ortg"], t["drtg"]
    t["net_rtg"], t["ortg"], t["drtg"] = t["net_reale"], t["ortg_reale"], t["drtg_reale"]
    return t[["campionato_id", "squadra_id", "squadra", "partite", "vinte", "perse_partite",
              "net_rtg", "forza", "incertezza", "ortg", "drtg", "pace_stima",
              "parte_precedente", "parte_attacco", "parte_difesa", "ortg_corr", "drtg_corr"]]


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
        "Rosa e stagione precedente": (h["parte_precedente"] - a["parte_precedente"]) * poss / 100,
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
    forze = strengths(bs, prior_from_previous(conn, stagione, A.load_box_giocatore(conn, stagione)))
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


# ------------------------------------------------------------------ punti totali e intervalli
# Validazione retrospettiva 2024/25–2026/27 (2.002 partite, solo dati precedenti a ogni partita):
# errore medio sui punti totali 12,5 (efficienze corrette per la fortuna) contro 13,1 della media; il modello
# sottostimava di 1,5 punti (correzione). Dispersione dei totali 16 punti, del margine 12,5.
RESTRINGI_TOTALI = 6.0       # partite di "media di campionato" aggiunte a ogni squadra
CORREZIONE_TOTALI = 1.5
SIGMA_TOTALI = 16.0
Z80 = 1.2816                 # intervallo che contiene 8 risultati su 10
Z50 = 0.6745                 # intervallo che contiene 1 risultato su 2
# Scarto reale tra margine previsto e reale (validazione 2.215 partite, con la correzione per la
# fortuna): più largo nelle prime giornate, quando le forze sono ancora poco note. Con questi valori
# gli intervalli contengono il risultato l'80,7% e il 51,6% delle volte.
SIGMA_MARGINE_FASI = ((3, 13.1), (7, 12.3), (999, 11.85))      # (partite giocate fino a, dispersione)
SIGMA_TOTALI_CAMPIONATO = {"ita2": 15.0, "ita3_a": 16.7, "ita3_b": 15.9}


def sigma_margine(partite_giocate: float) -> float:
    for fino, s in SIGMA_MARGINE_FASI:
        if partite_giocate <= fino:
            return s
    return SIGMA_MARGINE_FASI[-1][1]


def totale(forze: pd.DataFrame, casa_id: int, ospite_id: int, partite: dict | None = None) -> dict:
    """Punti totali attesi: possessi (ritmo delle due squadre) × efficienza dell'attacco contro la
    difesa avversaria, ognuna ristretta verso la media con poche partite giocate."""
    f = forze.set_index("squadra_id")
    o, d = ("ortg_corr", "drtg_corr") if "ortg_corr" in f else ("ortg", "drtg")   # corretti per la fortuna
    lega_o, lega_p = f[o].mean(), f["pace_stima"].mean()
    partite = partite or {}

    def sh(sid, col, media):
        g = partite.get(sid, f.loc[sid, "partite"] if "partite" in f else 0) or 0
        v = f.loc[sid, col]
        v = media if pd.isna(v) else v
        return (v * g + media * RESTRINGI_TOTALI) / (g + RESTRINGI_TOTALI)
    poss = sh(casa_id, "pace_stima", lega_p) + sh(ospite_id, "pace_stima", lega_p) - lega_p
    eff_c = sh(casa_id, o, lega_o) + sh(ospite_id, d, lega_o) - lega_o
    eff_o = sh(ospite_id, o, lega_o) + sh(casa_id, d, lega_o) - lega_o
    tot = poss * (eff_c + eff_o) / 100 + CORREZIONE_TOTALI
    return {"totale": tot, "possessi": poss, "da": tot - Z80 * SIGMA_TOTALI, "a": tot + Z80 * SIGMA_TOTALI}


def pronostico(forze: pd.DataFrame, casa_id: int, ospite_id: int, hca: float,
               campionato: str | None = None) -> dict:
    """Pronostico completo di una partita: vincente, margine con intervallo all'80%, punti
    totali con intervallo, punteggio indicativo, probabilità di uno scarto ampio."""
    p = predict(forze, casa_id, ospite_id, hca)
    t = totale(forze, casa_id, ospite_id)
    m = p["margine"]
    out = {**p, **{k: v for k, v in t.items() if k != "possessi"}}
    f0 = forze.set_index("squadra_id")
    giocate = min(f0.loc[casa_id].get("partite", 99), f0.loc[ospite_id].get("partite", 99))
    sm, stt = sigma_margine(giocate), SIGMA_TOTALI_CAMPIONATO.get(campionato, SIGMA_TOTALI)
    out["margine_da"], out["margine_a"] = m - Z80 * sm, m + Z80 * sm
    out["margine_da50"], out["margine_a50"] = m - Z50 * sm, m + Z50 * sm
    out["da"], out["a"] = t["totale"] - Z80 * stt, t["totale"] + Z80 * stt
    out["da50"], out["a50"] = t["totale"] - Z50 * stt, t["totale"] + Z50 * stt
    out["punti_casa"], out["punti_ospite"] = (t["totale"] + m) / 2, (t["totale"] - m) / 2
    out["scarto_10_casa"] = 1 - _phi((10 - m) / SIGMA)       # casa vince di più di 10
    out["scarto_10_ospite"] = _phi((-10 - m) / SIGMA)
    f = forze.set_index("squadra_id")
    inc = math.sqrt(f.loc[casa_id, "incertezza"] ** 2 + f.loc[ospite_id, "incertezza"] ** 2)
    out["incertezza"] = inc
    out["affidabilita"] = "alta" if inc < 4.5 else ("media" if inc < 6.5 else "bassa")
    out["sigma_margine"], out["sigma_totali"] = sm, stt
    out["rischio"] = min(out["prob_casa"], 1 - out["prob_casa"])     # probabilità che la favorita perda
    return out


# ------------------------------------------------------------------ più previsioni insieme
# Correggere le probabilità con l'andamento della stagione in corso (fattore campo, fiducia, totali
# per campionato) è stato provato giorno per giorno sulle stagioni 2024/25–2026/27: nessun
# miglioramento (Brier 0,2110 contro 0,2109-0,2115). Le deviazioni di inizio stagione sono in gran
# parte caso e rientrano: si usano le probabilità del modello, calibrate sullo storico.


def probabilita_evento(p: dict, evento: str, soglia: float = 0.0) -> float:
    """Probabilità di un esito della partita dal pronostico: "casa", "ospite" (vincente),
    "casa_scarto"/"ospite_scarto" (vince di più di soglia), "over"/"under" (punti totali)."""
    m, sm, st = p["margine"], p.get("sigma_margine", SIGMA), p.get("sigma_totali", SIGMA_TOTALI)
    if evento == "casa":
        return p["prob_casa"]
    if evento == "ospite":
        return 1 - p["prob_casa"]
    if evento == "casa_scarto":
        return 1 - _phi((soglia - m) / sm)
    if evento == "ospite_scarto":
        return _phi((-soglia - m) / sm)
    if evento == "over":
        return 1 - _phi((soglia - p["totale"]) / st)
    if evento == "under":
        return _phi((soglia - p["totale"]) / st)
    raise ValueError(evento)


def errori(probabilita: list[float]) -> dict:
    """Su più previsioni indipendenti: probabilità di prenderle tutte, al più 1 errore, errori attesi."""
    dist = np.array([1.0])                       # dist[j] = probabilità di j errori
    for q in probabilita:
        dist = np.convolve(dist, [q, 1 - q])
    return {"tutte": float(dist[0]), "al_piu_uno": float(dist[:2].sum()),
            "attesi": float(sum(1 - q for q in probabilita)), "distribuzione": dist}
