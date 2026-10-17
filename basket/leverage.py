"""Leverage: quanto ogni azione sposta la probabilità di vittoria, e a chi va il merito.

Adattamento della statistica Leverage della NBA (NBA Inside the Game) ai dati disponibili per
A2 e B Nazionale, cioè la cronaca delle partite (senza tracciamento ottico: niente difficoltà
del tiro né pressione difensiva).

- Probabilità di vittoria in partita: modello "browniano" del margine. Con m il margine della
  squadra, τ la frazione di partita che resta e μ il margine atteso prima della partita
  (forze delle squadre e fattore campo), P = Φ((m + c·possesso + μ·τ) / (σ·√τ)).
  σ è tarato sulla cronaca delle partite (vedi taratura()).
- Swing di un'azione: probabilità dopo l'azione meno probabilità dopo l'esito opposto
  (un tiro segnato contro lo stesso tiro sbagliato, un libero segnato contro uno sbagliato,
  una palla persa contro il possesso conservato, un rimbalzo contro l'esito atteso).
- Merito: lo swing va per intero alla squadra che agisce e, cambiato di segno, all'altra
  (somma zero). Nella squadra: chi fa l'azione il 70% (tiro assistito: tiratore 45%,
  assistman 25%), il resto ai compagni in campo; nella squadra che subisce: chi recupera o
  stoppa il 50%, il resto diviso tra chi è in campo.
- Scala: 1,0 = 10 punti percentuali di probabilità di vittoria, come nella NBA.
"""

import math

import numpy as np
import pandas as pd

SIGMA = 13.0                 # punti: dispersione del margine su una partita intera (taratura 2025/26)
MINIMO = 1.5                 # punti: incertezza che resta anche nei finali (falli, triple)
VALORE_POSSESSO = 1.0        # punti: avere la palla vale circa un punto
QUOTA_RIMB_DIF = 0.73        # rimbalzi difensivi sul totale (cronaca 2025/26)
DURATA = 2400                # secondi regolamentari
SUPPLEMENTARE = 300
SCALA = 10.0                 # 1,0 di Leverage = 10 punti percentuali

QUOTA_AUTORE = 0.70
QUOTA_TIRATORE_ASSISTITO, QUOTA_ASSISTMAN = 0.45, 0.25
QUOTA_DIFENSORE = 0.50       # chi recupera o stoppa, sulla parte della difesa


def _phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def restante(periodo: int, secondi: float) -> float:
    """Secondi che mancano alla fine (dei regolamentari o del supplementare in corso)."""
    if periodo is None or periodo <= 4:
        return max(0.0, DURATA - float(secondi or 0))
    fine = DURATA + SUPPLEMENTARE * (periodo - 4)
    return max(0.0, fine - float(secondi or 0))


def prob(margine: float, resta: float, possesso: int = 0, atteso: float = 0.0,
         sigma: float = SIGMA) -> float:
    """Probabilità di vittoria della squadra con questo margine. possesso: +1 palla sua,
    -1 palla avversaria, 0 non nota; atteso: margine atteso prima della partita (sua prospettiva)."""
    tau = max(resta, 0.0) / DURATA
    m = margine + VALORE_POSSESSO * possesso * min(1.0, 0.5 + tau)
    if tau <= 1e-6:                                          # partita finita
        return 1.0 if m > 0 else (0.0 if m < 0 else 0.5)
    return _phi((m + atteso * tau) / math.sqrt(sigma ** 2 * tau + MINIMO ** 2))


# ------------------------------------------------------------------ eventi

TIRI_FATTI = {"tiro2_fatto": 2, "tiro3_fatto": 3}
TIRI_SBAGLIATI = {"tiro2_sbagliato": 2, "tiro3_sbagliato": 3}


def _in_campo(stints: pd.DataFrame | None):
    """Funzione (partita, squadra, secondi) → giocatori in campo (dai quintetti ricostruiti)."""
    if stints is None or stints.empty:
        return lambda pid, sq, t: []
    per = {k: g[["inizio", "fine", "quintetto"]].to_numpy() for k, g in stints.groupby(["partita_id", "squadra_id"])}

    def f(pid, sq, t):
        arr = per.get((pid, sq))
        if arr is None:
            return []
        for ini, fin, q in arr:
            if ini <= t < fin or (t == fin and fin == arr[-1][1]):
                return str(q).split(",")
        return []
    return f


def swing(ev: pd.DataFrame, attese: dict | None = None, sigma: float = SIGMA) -> pd.DataFrame:
    """Swing di probabilità di ogni azione per la squadra che la compie (colonna 'swing',
    in punti di probabilità 0-1) e probabilità di vittoria della casa dopo l'azione ('wp_casa').
    attese: {partita_id: margine atteso per la casa}."""
    attese = attese or {}
    righe = []
    for pid, g in ev.sort_values(["partita_id", "n"]).groupby("partita_id", sort=False):
        mu = float(attese.get(pid, 0.0))
        pos = 0                                                     # +1 casa, -1 ospite, 0 non noto
        pc0 = po0 = 0
        for r in g.itertuples(index=False):
            casa = bool(r.casa); s = 1 if casa else -1
            resta = restante(r.periodo, r.secondi)
            m = (pc0 - po0) * s                                     # margine prima, per chi agisce
            mu_s = mu * s
            v = lambda marg, p: prob(marg, resta, p, mu_s, sigma)  # noqa: E731
            sw = 0.0
            t = r.tipo
            if t in TIRI_FATTI:
                p = TIRI_FATTI[t]
                atteso_errore = QUOTA_RIMB_DIF * v(m, -1) + (1 - QUOTA_RIMB_DIF) * v(m, 1)
                sw = v(m + p, -1) - atteso_errore
                pos = -s
            elif t in TIRI_SBAGLIATI:
                p = TIRI_SBAGLIATI[t]
                atteso_errore = QUOTA_RIMB_DIF * v(m, -1) + (1 - QUOTA_RIMB_DIF) * v(m, 1)
                sw = atteso_errore - v(m + p, -1)
                pos = 0
            elif t == "tl_fatto":
                sw = v(m + 1, 0) - v(m, 0)
            elif t == "tl_sbagliato":
                sw = v(m, 0) - v(m + 1, 0)
            elif t in ("rimb_dif", "rimb_off"):
                q = QUOTA_RIMB_DIF if t == "rimb_off" else 1 - QUOTA_RIMB_DIF   # quanto era inatteso
                sw = q * (v(m, 1) - v(m, -1))
                pos = s
            elif t == "persa":
                sw = v(m, -1) - v(m, 1)
                pos = -s
            pc0 = r.punti_casa if pd.notna(r.punti_casa) else pc0
            po0 = r.punti_ospite if pd.notna(r.punti_ospite) else po0
            wp = prob(pc0 - po0, resta, pos, mu, sigma)
            righe.append((pid, r.n, sw, wp))
    out = pd.DataFrame(righe, columns=["partita_id", "n", "swing", "wp_casa"])
    return ev.merge(out, on=["partita_id", "n"], how="left")


def crediti(ev_sw: pd.DataFrame, stints: pd.DataFrame | None = None) -> pd.DataFrame:
    """Merito per giocatore di ogni azione (somma zero tra le due squadre).
    Colonne: partita_id, n, giocatore_id, squadra_id, leverage, categoria."""
    in_campo = _in_campo(stints)
    ev = ev_sw.sort_values(["partita_id", "n"])
    righe = []
    for pid, g in ev.groupby("partita_id", sort=False):
        rr = g.to_dict("records")
        for i, r in enumerate(rr):
            sw = r.get("swing")
            if sw is None or pd.isna(sw) or sw == 0:
                continue
            L = sw * SCALA
            sq, avv, t = r["squadra_id"], r["avversario_id"], r["tipo"]
            autore = r["giocatore_id"] if isinstance(r["giocatore_id"], str) and not r["di_squadra"] else None
            cat = ("tiro" if t in TIRI_FATTI or t in TIRI_SBAGLIATI else "liberi" if t.startswith("tl_")
                   else "rimbalzo" if t.startswith("rimb") else "palla persa")
            # assist e azione difensiva collegati (eventi vicini con lo stesso tempo)
            vicini = [x for x in rr[max(0, i - 3):i + 4] if x["secondi"] == r["secondi"] and x is not r]
            assist = next((x["giocatore_id"] for x in vicini if x["tipo"] == "assist" and x["squadra_id"] == sq), None) \
                if t in TIRI_FATTI else None
            difensore = next((x["giocatore_id"] for x in vicini if x["squadra_id"] == avv and
                              x["tipo"] in ("recupero", "stoppata")), None) if t in ("persa",) or t in TIRI_SBAGLIATI else None
            # attacco: +L
            quote = {}
            if autore:
                if assist:
                    quote[autore] = QUOTA_TIRATORE_ASSISTITO; quote[assist] = QUOTA_ASSISTMAN
                else:
                    quote[autore] = QUOTA_AUTORE
            compagni = [p for p in in_campo(pid, sq, r["secondi"]) if p not in quote]
            resto = 1 - sum(quote.values())
            if compagni:
                for p in compagni: quote[p] = quote.get(p, 0) + resto / len(compagni)
            elif autore:
                quote[autore] += resto
            if not quote:
                quote[None] = 1.0                                   # in campo non noto: alla squadra
            for p, q in quote.items():
                righe.append((pid, r["n"], p, sq, L * q, cat))
            # difesa: -L
            quote_d = {}
            if difensore:
                quote_d[difensore] = QUOTA_DIFENSORE
            altri = [p for p in in_campo(pid, avv, r["secondi"]) if p not in quote_d]
            resto = 1 - sum(quote_d.values())
            if altri:
                for p in altri: quote_d[p] = quote_d.get(p, 0) + resto / len(altri)
            elif difensore:
                quote_d[difensore] += resto
            if not quote_d:
                quote_d[None] = 1.0
            cat_d = "difesa" if cat in ("tiro", "palla persa", "liberi") else "rimbalzo"
            for p, q in quote_d.items():
                righe.append((pid, r["n"], p, avv, -L * q, cat_d))
    return pd.DataFrame(righe, columns=["partita_id", "n", "giocatore_id", "squadra_id", "leverage", "categoria"])


# ------------------------------------------------------------------ riepiloghi

def per_giocatore(cr: pd.DataFrame, minuti: pd.DataFrame | None = None) -> pd.DataFrame:
    """Leverage della stagione per giocatore, totale e per categoria; per 40' se ci sono i minuti
    (giocatore_id, squadra_id, minuti)."""
    if cr.empty:
        return pd.DataFrame()
    t = cr.pivot_table(index=["giocatore_id", "squadra_id"], columns="categoria", values="leverage",
                       aggfunc="sum", fill_value=0.0)
    t["leverage"] = t.sum(axis=1)
    t["partite"] = cr.groupby(["giocatore_id", "squadra_id"])["partita_id"].nunique()
    t = t.reset_index()
    if minuti is not None and not minuti.empty:
        t = t.merge(minuti, on=["giocatore_id", "squadra_id"], how="left")
        t["leverage_p40"] = np.where(t["minuti"] > 0, t["leverage"] / t["minuti"] * 40, np.nan)
    return t.sort_values("leverage", ascending=False)


def per_partita(cr: pd.DataFrame) -> pd.DataFrame:
    return (cr.groupby(["partita_id", "giocatore_id", "squadra_id"])["leverage"].sum()
            .reset_index().sort_values("leverage", ascending=False))


DESCR = {"tiro2_fatto": "canestro da 2", "tiro3_fatto": "tripla", "tiro2_sbagliato": "errore da 2",
         "tiro3_sbagliato": "errore da 3", "tl_fatto": "libero segnato", "tl_sbagliato": "libero sbagliato",
         "rimb_off": "rimbalzo offensivo", "rimb_dif": "rimbalzo difensivo", "persa": "palla persa"}


def momenti_decisivi(ev_sw: pd.DataFrame, partita_id: str, n: int = 5) -> pd.DataFrame:
    """Le azioni che hanno spostato di più la partita."""
    g = ev_sw[(ev_sw["partita_id"] == partita_id) & ev_sw["swing"].notna() & (ev_sw["swing"] != 0)].copy()
    if g.empty:
        return g
    g["peso"] = g["swing"].abs()
    g = g.nlargest(n, "peso").sort_values("n")
    g["azione"] = g["tipo"].map(DESCR).fillna(g["tipo"])
    g["leverage"] = g["swing"] * SCALA
    return g


def taratura(ev: pd.DataFrame, attese: dict, sigme=(9, 10, 11, 12, 13, 14, 16)) -> dict:
    """Sigma con la migliore log-loss sulle situazioni di partita (un campione ogni ~30 s)."""
    fin = ev.groupby("partita_id").agg(pc=("punti_casa", "max"), po=("punti_ospite", "max"))
    vince = (fin["pc"] > fin["po"]).astype(float)
    c = ev[ev["secondi"] % 30 < 3].drop_duplicates(["partita_id", "secondi"])
    c = c[c["partita_id"].isin(vince.index)]
    out = {}
    for s in sigme:
        ll = []
        for r in c.itertuples(index=False):
            p = prob((r.punti_casa or 0) - (r.punti_ospite or 0), restante(r.periodo, r.secondi), 0,
                     attese.get(r.partita_id, 0.0), s)
            p = min(max(p, 1e-4), 1 - 1e-4); y = vince[r.partita_id]
            ll.append(-(y * math.log(p) + (1 - y) * math.log(1 - p)))
        out[s] = float(np.mean(ll))
    return out
