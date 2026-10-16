"""Confronto tra due giocatori con metriche avanzate, pensato per il mercato.

Tre livelli, dal più immediato al più tecnico:

- verdetto(): due-tre frasi su chi è meglio in cosa e per quale ruolo;
- profilo(): sei dimensioni in percentili (0-100) rispetto ai giocatori dello stesso ruolo
  della categoria di riferimento: realizzazione, creazione, tiro da fuori, rimbalzo, difesa e
  attività, impatto;
- possesso(): cosa produce ogni 100 possessi che il giocatore usa (punti, palle perse, tiri
  sbagliati), confrontato con la mediana del ruolo.

Confronto alla pari: se i due giocano in categorie diverse, i numeri di B Nazionale sono
riportati alla scala dell'A2 con i fattori stimati sui giocatori passati tra le due categorie
(approfondimenti.fattori_categoria). Le percentuali di tiro sono stimate in modo prudente
(mercato.shrink_rates), così pochi tentativi non sembrano un 100%.
"""

import numpy as np
import pandas as pd

from . import approfondimenti as X
from . import mercato

# dimensione: [(colonna, True se più alto è meglio, peso)]
DIMENSIONI = {
    "Realizzazione": [("punti_p40", True, 0.5), ("ts_pct", True, 0.5)],
    "Creazione": [("ast_pct", True, 0.5), ("assist_p40", True, 0.2), ("tov_pct", False, 0.3)],
    "Tiro da fuori": [("t3_pct", True, 0.6), ("t3a_p40", True, 0.4)],
    "Rimbalzo": [("trb_pct", True, 0.6), ("orb_pct", True, 0.2), ("rimb_tot_p40", True, 0.2)],
    "Difesa e attività": [("stl_pct", True, 0.4), ("blk_pct", True, 0.35),
                          ("falli_commessi_p40", False, 0.25)],
    "Impatto": [("game_score_p40", True, 0.7), ("on_off", True, 0.3)],
}
# ruolo adatto quando una dimensione è il punto forte
RUOLO_DIMENSIONE = {
    "Realizzazione": "primo o secondo realizzatore", "Creazione": "organizzatore del gioco",
    "Tiro da fuori": "tiratore che allarga il campo", "Rimbalzo": "presenza sotto i tabelloni",
    "Difesa e attività": "specialista difensivo", "Impatto": "giocatore di sistema",
}
# conversione B Nazionale -> A2 per le colonne che non hanno un fattore stimato direttamente
CONVERSIONE = {"punti_p40": "punti_p40", "rimb_tot_p40": "rimb_tot_p40",
               "rimb_off_p40": "rimb_tot_p40", "rimb_dif_p40": "rimb_tot_p40",
               "assist_p40": "assist_p40", "game_score_p40": "game_score_p40",
               "recuperate_p40": "game_score_p40", "stoppate_p40": "game_score_p40",
               "t3a_p40": "punti_p40", "t3m_p40": "punti_p40",
               # le quote di squadra calano come i conteggi corrispondenti
               "ast_pct": "assist_p40", "trb_pct": "rimb_tot_p40", "orb_pct": "rimb_tot_p40",
               "drb_pct": "rimb_tot_p40", "stl_pct": "game_score_p40",
               "blk_pct": "game_score_p40"}
MINUTI_AFFIDABILI = 150      # sotto questi minuti in stagione il profilo è indicativo
MIN_POOL_RUOLO = 15


def _fattori(hist: pd.DataFrame) -> dict:
    f = X.fattori_categoria(hist)
    ok = f[f["coppie"] >= X.MIN_COPPIE] if not f.empty else f
    return {r.statistica: (r.tipo, r.valore) for r in ok.itertuples() if pd.notna(r.valore)}


def _in_a2(riga: pd.Series, fattori: dict) -> pd.Series:
    """Statistiche di un giocatore di B Nazionale riportate alla scala dell'A2."""
    r = riga.copy()
    for col, base in CONVERSIONE.items():
        if base in fattori and col in r and pd.notna(r[col]):
            r[col] = r[col] * fattori[base][1]
    for col in ("ts_pct", "usg_pct"):
        if col in fattori and pd.notna(r.get(col)):
            r[col] = r[col] + fattori[col][1]
    return r


def _linee(hist: pd.DataFrame, stagione: str) -> pd.DataFrame:
    """Linee di una stagione con percentuali prudenti, una per giocatore e squadra."""
    s = hist[hist["stagione"] == stagione]
    return mercato.shrink_rates(s) if not s.empty else s


def _pool(linee: pd.DataFrame, categoria: str, ruolo: str) -> pd.DataFrame:
    max_g = linee.groupby("categoria")["partite"].transform("max")
    p = linee[(linee["categoria"] == categoria) & (linee["minuti_pg"] >= 10)
              & (linee["partite"] >= np.maximum(2, np.ceil(0.4 * max_g)))]
    stesso = p[p["ruolo"] == ruolo]
    return stesso if len(stesso) >= MIN_POOL_RUOLO else p


def _percentile(serie: pd.Series, v, alto: bool) -> float:
    s = serie.dropna().astype(float)
    if s.empty or pd.isna(v):
        return np.nan
    p = 100 * ((s < v).mean() + 0.5 * (s == v).mean())
    return p if alto else 100 - p


def _possesso(r: pd.Series) -> dict:
    usati = float(r["fga"]) + 0.44 * float(r["tla"]) + float(r["perse"])
    if usati <= 0:
        return {"usati_p40": np.nan, "punti_100": np.nan, "perse_100": np.nan,
                "sbagliati_100": np.nan}
    return {"usati_p40": 40 * usati / max(1.0, float(r["minuti"])),
            "punti_100": 100 * float(r["punti"]) / usati,
            "perse_100": 100 * float(r["perse"]) / usati,
            "sbagliati_100": 100 * (float(r["fga"]) - float(r["fgm"])) / usati}


def scheda(hist: pd.DataFrame, giocatore_id: str, stagione: str, scala: str | None = None,
           on_off: pd.DataFrame | None = None, fattori: dict | None = None) -> dict | None:
    """Profilo di un giocatore in una stagione. scala: "A2" per riportare un giocatore di B
    alla scala dell'A2 (percentili calcolati tra i giocatori di A2), None per la sua categoria.
    on_off: tabella giocatore_id -> on_off (dalla cronaca, stagione in corso)."""
    if on_off is not None and on_off.attrs.get("stagione") not in (None, stagione):
        on_off = None            # l'On-Off c'è solo per la stagione della cronaca caricata
    linee = _linee(hist, stagione)
    mie = linee[linee["giocatore_id"] == giocatore_id]
    if mie.empty:
        return None
    r = mie.sort_values("minuti", ascending=False).iloc[0].copy()
    if on_off is not None and not on_off.empty and giocatore_id in set(on_off["giocatore_id"]):
        r["on_off"] = on_off.set_index("giocatore_id")["on_off"].get(giocatore_id)
    else:
        r["on_off"] = np.nan
    categoria = r["categoria"]
    convertito = scala == "A2" and categoria == "B Nazionale"
    poss = _possesso(r)
    if convertito:
        fattori = fattori if fattori is not None else _fattori(hist)
        ts0 = r["ts_pct"]
        r = _in_a2(r, fattori)
        if pd.notna(ts0) and ts0:
            poss["punti_100"] *= r["ts_pct"] / ts0
        categoria = "A2"
    pool = _pool(linee, categoria, r["ruolo"])
    if on_off is not None and not on_off.empty:
        pool = pool.merge(on_off[["giocatore_id", "on_off"]], on="giocatore_id", how="left") \
            if "on_off" not in pool else pool
    dims, dettagli = {}, {}
    for dim, voci in DIMENSIONI.items():
        tot, pesi = 0.0, 0.0
        for col, alto, peso in voci:
            if col not in pool or pd.isna(r.get(col)) or pool[col].notna().sum() < 5:
                continue
            p = _percentile(pool[col], r[col], alto)
            dettagli[col] = p
            tot += peso * p
            pesi += peso
        dims[dim] = tot / pesi if pesi else np.nan
    pool_poss = pd.DataFrame([_possesso(x) for _, x in pool.iterrows()]) if len(pool) else \
        pd.DataFrame()
    return {"riga": r, "categoria_originale": mie.iloc[0]["categoria"], "scala": categoria,
            "convertito": convertito, "dimensioni": dims, "percentili": dettagli,
            "possesso": poss, "possesso_ruolo": pool_poss.median().to_dict()
            if not pool_poss.empty else {},
            "pool": len(pool), "ruolo": r["ruolo"],
            "pochi_dati": float(r["minuti"]) < MINUTI_AFFIDABILI}


def confronta(hist: pd.DataFrame, a: tuple[str, str], b: tuple[str, str],
              on_off: pd.DataFrame | None = None) -> tuple[dict, dict]:
    """Schede dei due giocatori ((giocatore_id, stagione) ciascuno). Se uno dei due gioca in
    B Nazionale e l'altro in A2, entrambi sono portati alla scala dell'A2."""
    cat = {g: hist.loc[(hist["giocatore_id"] == g) & (hist["stagione"] == s), "categoria"]
           for g, s in (a, b)}
    cats = {c.iloc[0] for c in cat.values() if not c.empty}
    scala = "A2" if len(cats) > 1 else None
    fattori = _fattori(hist) if scala else None
    return (scheda(hist, *a, scala=scala, on_off=on_off, fattori=fattori),
            scheda(hist, *b, scala=scala, on_off=on_off, fattori=fattori))


def _cognome(nome: str) -> str:
    if not isinstance(nome, str) or " " not in nome:
        return str(nome)
    parti = [p for p in nome.split() if p.lower().strip(".") not in ("jr", "sr", "ii", "iii", "iv")]
    return parti[-1] if parti else nome


def _n(v, d=0) -> str:
    return "–" if v is None or pd.isna(v) else f"{v:.{d}f}".replace(".", ",")


def verdetto(sa: dict, sb: dict) -> list[str]:
    """Le differenze che contano, in parole: dove ognuno è superiore, l'efficienza con cui usa
    i possessi e il ruolo per cui è più adatto."""
    na, nb = _cognome(sa["riga"]["giocatore"]), _cognome(sb["riga"]["giocatore"])
    da, db = sa["dimensioni"], sb["dimensioni"]
    diff = {k: da[k] - db[k] for k in da if pd.notna(da.get(k)) and pd.notna(db.get(k))}
    meglio_a = [k for k, v in sorted(diff.items(), key=lambda x: -x[1]) if v >= 12][:2]
    meglio_b = [k for k, v in sorted(diff.items(), key=lambda x: x[1]) if v <= -12][:2]
    out = []

    def lista(dims, s):
        return " e ".join(f"{d.lower()} ({_n(s['dimensioni'][d])})" for d in dims)
    if meglio_a and meglio_b:
        out.append(f"{na} è superiore in {lista(meglio_a, sa)}; {nb} in {lista(meglio_b, sb)}.")
    elif meglio_a or meglio_b:
        chi, dims, s, altro = (na, meglio_a, sa, nb) if meglio_a else (nb, meglio_b, sb, na)
        out.append(f"{chi} è superiore in {lista(dims, s)}; nelle altre voci i due si "
                   f"equivalgono, nessun punto in cui {altro} sia nettamente meglio.")
    else:
        out.append(f"Profili simili: nessuna dimensione con più di 12 punti di percentile di "
                   f"differenza tra {na} e {nb}.")
    pa, pb = sa["possesso"], sb["possesso"]
    if pd.notna(pa["punti_100"]) and pd.notna(pb["punti_100"]):
        vol = (f"{na} usa {_n(pa['usati_p40'], 1)} possessi ogni 40', {nb} "
               f"{_n(pb['usati_p40'], 1)}")
        eff = pa["punti_100"] - pb["punti_100"]
        if abs(eff) >= 5:
            piu, meno = (na, nb) if eff > 0 else (nb, na)
            out.append(f"{vol}; {piu} li trasforma meglio: {_n(max(pa['punti_100'], pb['punti_100']))} "
                       f"punti ogni 100 possessi usati contro {_n(min(pa['punti_100'], pb['punti_100']))}"
                       f" di {meno}.")
        else:
            out.append(f"{vol}, con un'efficienza simile ({_n(pa['punti_100'])} e "
                       f"{_n(pb['punti_100'])} punti ogni 100 possessi usati).")
    ruoli = []
    for nome, s in ((na, sa), (nb, sb)):
        dd = {k: v for k, v in s["dimensioni"].items() if pd.notna(v) and k != "Impatto"}
        if dd:
            top = max(dd, key=dd.get)
            if dd[top] >= 60:
                ruoli.append(f"{nome} come {RUOLO_DIMENSIONE[top]}")
    if ruoli:
        out.append("Più adatti: " + "; ".join(ruoli) + ".")
    return out
