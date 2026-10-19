"""Filtri sulle statistiche dei giocatori: condizioni combinabili del tipo "più di 5 assist a
partita" e "meno di 2 palle perse", applicate tutte insieme (e logico).

Un filtro è un dizionario {"col": colonna, "op": operatore, "valore": numero}; gli operatori
sono quelli di OPERATORI ("più di", "almeno", "meno di", "al massimo")."""

import operator

import pandas as pd

# colonna -> (nome per lo staff, unità nella frase, decimali, passo del campo numerico)
CATALOGO = {
    "punti_pg": ("Punti a partita", "punti", 1, 1.0),
    "rimb_tot_pg": ("Rimbalzi a partita", "rimbalzi", 1, 1.0),
    "rimb_off_pg": ("Rimbalzi offensivi a partita", "rimbalzi offensivi", 1, 0.5),
    "rimb_dif_pg": ("Rimbalzi difensivi a partita", "rimbalzi difensivi", 1, 0.5),
    "assist_pg": ("Assist a partita", "assist", 1, 0.5),
    "perse_pg": ("Palle perse a partita", "palle perse", 1, 0.5),
    "ast_to": ("Assist per palla persa", "assist per palla persa", 2, 0.25),
    "recuperate_pg": ("Recuperi a partita", "recuperi", 1, 0.5),
    "stoppate_pg": ("Stoppate a partita", "stoppate", 1, 0.5),
    "t3m_pg": ("Triple segnate a partita", "triple segnate", 1, 0.5),
    "t3a_pg": ("Triple tentate a partita", "triple tentate", 1, 0.5),
    "t3_pct": ("% da 3", "% da 3", 1, 1.0),
    "t2_pct": ("% da 2", "% da 2", 1, 1.0),
    "tl_pct": ("% ai liberi", "% ai liberi", 1, 1.0),
    "tla_pg": ("Liberi tentati a partita", "liberi tentati", 1, 0.5),
    "falli_subiti_pg": ("Falli subiti a partita", "falli subiti", 1, 0.5),
    "falli_commessi_pg": ("Falli commessi a partita", "falli commessi", 1, 0.5),
    "minuti_pg": ("Minuti a partita", "minuti", 1, 1.0),
    "partite": ("Partite giocate", "partite", 0, 1.0),
    "valutazione_pg": ("Valutazione a partita", "di valutazione", 1, 1.0),
    "ts_pct": ("Tiro (TS%)", "di TS%", 1, 1.0),
    "efg_pct": ("eFG%", "di eFG%", 1, 1.0),
    "usg_pct": ("Possessi usati (USG%)", "di USG%", 1, 1.0),
    "ast_pct": ("Assist % (AST%)", "di AST%", 1, 1.0),
    "trb_pct": ("Rimbalzi % (REB%)", "di REB%", 1, 1.0),
    "game_score_pg": ("Game Score a partita", "di Game Score", 1, 1.0),
    "punti_p40": ("Punti per 40'", "punti per 40'", 1, 1.0),
    "eta": ("Età", "anni", 0, 1.0),
    "altezza_cm": ("Altezza (cm)", "cm", 0, 1.0),
}

OPERATORI = {"più di": operator.gt, "almeno": operator.ge, "meno di": operator.lt,
             "al massimo": operator.le}

# ricerche pronte (si possono poi modificare)
PRONTI = {
    "Registi che curano la palla": [{"col": "assist_pg", "op": "più di", "valore": 5.0},
                                    {"col": "perse_pg", "op": "meno di", "valore": 2.0}],
    "Tiratori da 3": [{"col": "t3a_pg", "op": "almeno", "valore": 4.0},
                      {"col": "t3_pct", "op": "almeno", "valore": 38.0}],
    "Rimbalzisti": [{"col": "rimb_tot_pg", "op": "almeno", "valore": 8.0}],
    "Realizzatori efficienti": [{"col": "punti_pg", "op": "almeno", "valore": 15.0},
                                {"col": "ts_pct", "op": "almeno", "valore": 58.0}],
    "Mani rapide in difesa": [{"col": "recuperate_pg", "op": "almeno", "valore": 1.5}],
    "Attaccano il ferro": [{"col": "tla_pg", "op": "almeno", "valore": 4.0},
                           {"col": "falli_subiti_pg", "op": "almeno", "valore": 4.0}],
}


def disponibili(df: pd.DataFrame) -> dict:
    """Le voci del catalogo presenti (o calcolabili) nella tabella."""
    cols = set(df.columns)
    out = {}
    for c, v in CATALOGO.items():
        if c in cols or (c == "ast_to" and {"assist", "perse"} <= cols):
            if c in cols and df[c].isna().all():
                continue                       # es. età non ancora disponibile
            out[c] = v
    return out


def prepara(df: pd.DataFrame) -> pd.DataFrame:
    """Aggiunge le colonne calcolabili che mancano (assist per palla persa)."""
    if "ast_to" not in df.columns and {"assist", "perse"} <= set(df.columns):
        df = df.assign(ast_to=df["assist"] / df["perse"].where(df["perse"] > 0))
    return df


def validi(filtri: list[dict], df: pd.DataFrame) -> list[dict]:
    voci = disponibili(df)
    return [f for f in filtri if f.get("col") in voci and f.get("op") in OPERATORI
            and f.get("valore") is not None and not pd.isna(f["valore"])]


def applica(df: pd.DataFrame, filtri: list[dict]) -> pd.DataFrame:
    """Le righe che rispettano tutti i filtri. Un valore mancante non rispetta il filtro."""
    df = prepara(df)
    mask = pd.Series(True, index=df.index)
    for f in validi(filtri, df):
        v = pd.to_numeric(df[f["col"]], errors="coerce")
        mask &= v.notna() & OPERATORI[f["op"]](v, float(f["valore"]))
    return df[mask]


def _numero(x: float, d: int) -> str:
    return f"{x:.{d}f}".replace(".", ",") if d else f"{x:.0f}"


def descrivi(filtri: list[dict]) -> str:
    """"più di 5 assist e meno di 2 palle perse"."""
    parti = []
    for f in filtri:
        if f.get("col") not in CATALOGO:
            continue
        _, unita, d, _ = CATALOGO[f["col"]]
        valore = _numero(float(f["valore"]), d)
        parti.append(f"{f['op']} {valore}{'' if unita.startswith('%') else ' '}{unita}")
    if not parti:
        return ""
    return parti[0] if len(parti) == 1 else ", ".join(parti[:-1]) + " e " + parti[-1]
