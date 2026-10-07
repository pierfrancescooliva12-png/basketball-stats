"""Mercato e reclutamento: anagrafica, storico per stagione, ricerca, giocatori simili."""

from datetime import date

import numpy as np
import pandas as pd

from . import analysis as A
from . import approfondimenti as X
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
        pres = X.presenze(bg, bs)
        if not pres.empty:
            p = p.merge(pres[["squadra_id", "giocatore_id", "partite_periodo", "saltate",
                              "presenze_pct"]], on=["squadra_id", "giocatore_id"], how="left")
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


# ------------------------------------------------------------------ fabbisogni della squadra

# Ogni tipo di giocatore:
#   bisogno  = metriche di squadra che lo rendono necessario: (colonna, True se più alto è meglio)
#   profilo  = metriche individuali che lo descrivono: (colonna, True se più alto è meglio, peso)
#   requisiti = volume minimo per essere considerato (per 40 minuti)
ARCHETIPI = {
    "tiratore": {
        "nome": "Tiratore da 3",
        "descrizione": "allarga il campo e punisce gli aiuti: alto volume e precisione da 3",
        "bisogno": [("efg_pct", True), ("t3_pct", True)],
        "profilo": [("t3_pct", True, 0.45), ("t3a_p40", True, 0.35), ("ts_pct", True, 0.20)],
        "requisiti": {"t3a_p40": 4.0},
        "mostra": ["t3_pct", "t3a_p40", "ts_pct"],
    },
    "playmaker": {
        "nome": "Playmaker / organizzatore",
        "descrizione": "crea per i compagni e protegge la palla",
        "bisogno": [("tov_pct", False), ("ast_ratio", True)],
        "profilo": [("ast_pct", True, 0.45), ("ast_ratio", True, 0.20), ("tov_pct", False, 0.20),
                    ("usg_pct", True, 0.15)],
        "requisiti": {"assist_p40": 3.0},
        "mostra": ["ast_pct", "tov_pct", "usg_pct"],
    },
    "rimbalzista": {
        "nome": "Rimbalzista",
        "descrizione": "domina i tabelloni: seconde occasioni in attacco, possesso chiuso in difesa",
        "bisogno": [("orb_pct", True), ("drb_pct", True)],
        "profilo": [("trb_pct", True, 0.40), ("orb_pct", True, 0.25), ("drb_pct", True, 0.25),
                    ("blk_pct", True, 0.10)],
        "requisiti": {"rimb_tot_p40": 7.0},
        "mostra": ["trb_pct", "orb_pct", "drb_pct"],
    },
    "protettore": {
        "nome": "Protettore del ferro",
        "descrizione": "stoppa, intimidisce vicino a canestro senza caricarsi di falli",
        "bisogno": [("opp_efg_pct", False), ("stoppate_pg", True)],
        "profilo": [("blk_pct", True, 0.50), ("drb_pct", True, 0.30),
                    ("falli_commessi_p40", False, 0.20)],
        "requisiti": {"stoppate_p40": 0.8},
        "mostra": ["blk_pct", "drb_pct", "falli_commessi_p40"],
    },
    "difensore": {
        "nome": "Difensore perimetrale",
        "descrizione": "mani attive sulle linee di passaggio, forza palle perse",
        "bisogno": [("opp_tov_pct", True), ("recuperate_pg", True)],
        "profilo": [("stl_pct", True, 0.55), ("recuperate_p40", True, 0.25),
                    ("falli_commessi_p40", False, 0.20)],
        "requisiti": {"recuperate_p40": 1.2},
        "mostra": ["stl_pct", "recuperate_p40", "falli_commessi_p40"],
    },
    "penetratore": {
        "nome": "Attaccante del ferro",
        "descrizione": "batte l'uomo, si procura falli e va in lunetta",
        "bisogno": [("ft_rate", True)],
        "profilo": [("ft_rate", True, 0.40), ("falli_subiti_p40", True, 0.30),
                    ("t2_pct", True, 0.30)],
        "requisiti": {"tla_p40": 4.0},
        "mostra": ["ft_rate", "falli_subiti_p40", "t2_pct"],
    },
    "realizzatore": {
        "nome": "Realizzatore",
        "descrizione": "punti efficienti con volume, per alleggerire i primi due realizzatori",
        "bisogno": [("ortg", True), ("quota_top2", False)],
        "profilo": [("punti_p40", True, 0.40), ("ts_pct", True, 0.35), ("usg_pct", True, 0.25)],
        "requisiti": {"punti_p40": 14.0},
        "mostra": ["punti_p40", "ts_pct", "usg_pct"],
    },
}

ETICHETTE = {
    "efg_pct": "eFG%", "t3_pct": "% da 3", "tov_pct": "Palle perse %", "ast_ratio": "Assist ratio",
    "orb_pct": "Rimbalzi offensivi %", "drb_pct": "Rimbalzi difensivi %",
    "opp_efg_pct": "eFG% concessa", "stoppate_pg": "Stoppate a partita",
    "opp_tov_pct": "Palle perse forzate %", "recuperate_pg": "Recuperi a partita",
    "ft_rate": "Liberi / tiri", "ortg": "Rating offensivo", "quota_top2": "% punti dei primi 2",
    "t3a_p40": "3PA/40", "ts_pct": "TS%", "ast_pct": "AST%", "usg_pct": "USG%",
    "trb_pct": "REB%", "blk_pct": "BLK%", "falli_commessi_p40": "Falli/40", "stl_pct": "STL%",
    "recuperate_p40": "Rec/40", "falli_subiti_p40": "Falli sub./40", "t2_pct": "2P%",
    "punti_p40": "Punti/40",
}
SOGLIA_BISOGNO = 0.6     # quota di squadre che fanno meglio (0 = migliore, 1 = peggiore)


def team_needs(profile: pd.DataFrame, squadra_id: int) -> pd.DataFrame:
    """Carenze della squadra rispetto al campionato, ordinate per priorità.

    Per ogni tipo di giocatore: gravità = posizione media della squadra nelle metriche di
    bisogno (0 = la migliore, 1 = la peggiore) e motivazione testuale."""
    n = len(profile)
    me = profile.set_index("squadra_id").loc[squadra_id]
    rows = []
    for key, a in ARCHETIPI.items():
        gravita, motivi = [], []
        for col, alto in a["bisogno"]:
            if col not in profile.columns or pd.isna(me.get(col)):
                continue
            rank = profile[col].rank(ascending=not alto, method="min")
            r = int(rank[profile["squadra_id"] == squadra_id].iloc[0])
            gravita.append((r - 1) / max(1, n - 1))
            fmt = ".2f" if col == "ft_rate" else ".1f"
            motivi.append(f"{ETICHETTE.get(col, col)} {me[col]:{fmt}} ({r}° su {n}, media "
                          f"{profile[col].mean():{fmt}})")
        if gravita:
            g = float(np.mean(gravita))
            rows.append({"tipo": key, "nome": a["nome"], "descrizione": a["descrizione"],
                         "gravita": g, "motivi": motivi,
                         "priorita": "Alta" if g >= 0.75 else "Media" if g >= SOGLIA_BISOGNO
                         else "Bassa"})
    return pd.DataFrame(rows).sort_values("gravita", ascending=False).reset_index(drop=True)


# Percentuali stimate in modo prudente: si aggiungono K tentativi "virtuali" alla media della
# categoria, così chi ha tirato poco non sembra un 100% (colonna: (fatti, tentati, K))
PRUDENZA = {"t3_pct": ("t3m", "t3a", 15), "t2_pct": ("t2m", "t2a", 15),
            "tl_pct": ("tlm", "tla", 10)}


def shrink_rates(pool: pd.DataFrame) -> pd.DataFrame:
    """Sostituisce le percentuali di tiro, il TS% e le palle perse % con stime prudenti."""
    pool = pool.copy()
    grp = pool.groupby(["stagione", "categoria"])
    for col, (m, a, k) in PRUDENZA.items():
        media = grp[m].transform("sum") / grp[a].transform("sum").replace(0, np.nan)
        pool[col] = 100 * (pool[m] + k * media) / (pool[a] + k)
    tiri = pool["t2a"] + pool["t3a"] + 0.44 * pool["tla"]
    ts_media = grp["punti"].transform("sum") / (2 * (grp["t2a"].transform("sum") + grp["t3a"]
                                                     .transform("sum") + 0.44 * grp["tla"]
                                                     .transform("sum")))
    pool["ts_pct"] = 100 * (pool["punti"] + 2 * 20 * ts_media) / (2 * (tiri + 20))
    usati = tiri + pool["perse"]
    tov_media = grp["perse"].transform("sum") / (grp["t2a"].transform("sum") + grp["t3a"]
                                                .transform("sum") + 0.44 * grp["tla"]
                                                .transform("sum") + grp["perse"].transform("sum"))
    pool["tov_pct"] = 100 * (pool["perse"] + 20 * tov_media) / (usati + 20)
    return pool


def fit_scores(lines: pd.DataFrame, tipo: str, min_minuti: float = 10.0) -> pd.DataFrame:
    """Adattamento (0-100) di ogni giocatore a un tipo, con i percentili calcolati all'interno
    della propria categoria (A2 o B Nazionale) e della stagione."""
    a = ARCHETIPI[tipo]
    max_g = lines.groupby(["stagione", "categoria"])["partite"].transform("max")
    pool = lines[(lines["minuti_pg"] >= min_minuti)
                 & (lines["partite"] >= np.maximum(2, np.ceil(0.4 * max_g)))].copy()
    for col, soglia in a["requisiti"].items():
        if col in pool.columns:
            pool = pool[pool[col] >= soglia]
    if pool.empty:
        return pool.assign(adattamento=pd.Series(dtype=float))
    pool = shrink_rates(pool)
    score = pd.Series(0.0, index=pool.index)
    for col, alto, peso in a["profilo"]:
        pct = pool.groupby(["stagione", "categoria"])[col].rank(pct=True, ascending=alto)
        score += peso * pct.fillna(0.5)
    pool["adattamento"] = (100 * score).round(0)
    return pool.sort_values("adattamento", ascending=False)


def suggestions(lines: pd.DataFrame, profile: pd.DataFrame, squadra_id: int, stagione: str,
                categorie=("A2", "B Nazionale"), eta_max: float | None = None,
                solo_ita: bool = False, n: int = 6, max_bisogni: int = 4) -> list[dict]:
    """Per le principali carenze della squadra: tipo di giocatore, motivazione, migliore in rosa
    per quel profilo e candidati di altre squadre con l'adattamento più alto."""
    needs = team_needs(profile, squadra_id)
    top = needs[needs["gravita"] >= SOGLIA_BISOGNO].head(max_bisogni)
    if top.empty:
        top = needs.head(2)
    season = lines[lines["stagione"] == stagione]
    out = []
    for need in top.to_dict("records"):
        fit = fit_scores(season, need["tipo"])
        # adattamento dei giocatori in rosa misurato sullo stesso campione del campionato
        interni = fit[fit["squadra_id"] == squadra_id]
        best_in = interni.iloc[0] if not interni.empty else None
        cand = fit[fit["squadra_id"] != squadra_id]
        cand = cand[cand["categoria"].isin(categorie)]
        if eta_max:
            cand = cand[cand["eta"].isna() | (cand["eta"] <= eta_max)]
        if solo_ita:
            cand = cand[cand["italiano"].fillna(False)]
        if best_in is not None:
            cand = cand[cand["adattamento"] > best_in["adattamento"]]
        out.append({**need, "migliore_in_rosa": best_in, "candidati": cand.head(n),
                    "mostra": ARCHETIPI[need["tipo"]]["mostra"]})
    return out
