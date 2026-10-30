"""Efficienza delle situazioni segnalate dallo staff sul video.

Ogni segnalazione della lavagna sul video ha un tipo di azione (pick and roll centrale, transizione…), uno
schema con il nome scelto dal club (Horns 45…) o entrambi, e il tempo di gioco (quarto e secondi) letto dal
cronometro. Dalla cronaca della partita si ricava come è finito quel possesso: canestro da 2 o da 3, liberi,
tiro sbagliato con rimbalzo difensivo, palla persa. Sommando le situazioni si vede quanto rende ogni tipo di
azione e ogni schema, quando attaccate voi e quando attaccano gli avversari.
"""

import pandas as pd

from .tiri import durata_periodo, inizio_periodo

CANESTRI = {"tiro2_fatto": 2, "tiro3_fatto": 3}
SBAGLIATI = {"tiro2_sbagliato", "tiro3_sbagliato"}
PRIMA, FINESTRA = 3, 24        # secondi di gioco: la segnalazione arriva durante l'azione, il tiro entro 24"


def esito(ev: pd.DataFrame, periodo: int, gs: float) -> dict | None:
    """Fine del possesso in corso al secondo di gioco gs del periodo (cronaca di una sola partita, con le
    colonne periodo, secondi dall'inizio della partita, squadra_id, tipo). {squadra: chi attaccava,
    punti, esito: "canestro" | "liberi" | "tiro sbagliato" | "palla persa", tiri, canestri}; None se nella
    cronaca non c'è una fine del possesso vicina."""
    if ev.empty:
        return None
    squadre = [int(x) for x in pd.unique(ev[["squadra_casa_id", "squadra_ospite_id"]].values.ravel())] \
        if "squadra_casa_id" in ev else [int(x) for x in ev["squadra_id"].dropna().unique()]
    altra = lambda s: next((x for x in squadre if x != s), None)  # noqa: E731
    t0 = inizio_periodo(periodo) + gs
    fine = min(t0 + FINESTRA, inizio_periodo(periodo) + durata_periodo(periodo))
    q = ev[(ev["periodo"] == periodo) & (ev["secondi"] >= t0 - PRIMA) & (ev["secondi"] <= fine)].sort_values("n")
    tiri = {}                   # tiri sbagliati nel possesso, per squadra (si continua dopo un rimbalzo offensivo)
    for r in q.itertuples():
        tipo, sq = r.tipo, (int(r.squadra_id) if pd.notna(r.squadra_id) else None)
        if sq is None:
            continue
        if tipo in CANESTRI:
            # libero aggiuntivo dopo il canestro con fallo (stesso secondo, stessa squadra)
            extra = int(((q["secondi"] == r.secondi) & (q["squadra_id"] == sq) & (q["tipo"] == "tl_fatto")).sum())
            return {"squadra": sq, "punti": CANESTRI[tipo] + extra, "esito": "canestro",
                    "tiri": tiri.get(sq, 0) + 1, "canestri": 1, "tre": tipo == "tiro3_fatto"}
        if tipo in SBAGLIATI:
            tiri[sq] = tiri.get(sq, 0) + 1
        elif tipo == "rimb_dif":
            att = altra(sq)
            return {"squadra": att, "punti": 0, "esito": "tiro sbagliato" if tiri.get(att) else "palla persa",
                    "tiri": tiri.get(att, 0), "canestri": 0, "tre": False}
        elif tipo == "persa":
            return {"squadra": sq, "punti": 0, "esito": "palla persa", "tiri": tiri.get(sq, 0), "canestri": 0,
                    "tre": False}
        elif tipo in ("tl_fatto", "tl_sbagliato"):
            stessi = q[(q["secondi"] == r.secondi) & (q["squadra_id"] == sq) & q["tipo"].isin(["tl_fatto", "tl_sbagliato"])]
            return {"squadra": sq, "punti": int((stessi["tipo"] == "tl_fatto").sum()), "esito": "liberi",
                    "tiri": tiri.get(sq, 0), "canestri": 0, "tre": False}
    if tiri:                    # tiro sbagliato senza rimbalzo scritto (fine del periodo): possesso finito
        att = max(tiri, key=tiri.get)
        return {"squadra": att, "punti": 0, "esito": "tiro sbagliato", "tiri": tiri[att], "canestri": 0, "tre": False}
    return None


def situazioni(memorie: dict, ev: pd.DataFrame, mia: int) -> pd.DataFrame:
    """Una riga per segnalazione con tempo di gioco, nelle partite della squadra mia.
    memorie: {partita_id: dati salvati dalla lavagna sul video}."""
    righe = []
    for pid, m in memorie.items():
        e = ev[ev["partita_id"] == pid]
        if e.empty or mia not in (int(e["squadra_casa_id"].iloc[0]), int(e["squadra_ospite_id"].iloc[0])):
            continue
        for s in (m or {}).get("segnalazioni", []) or []:
            azione, schema = s.get("azione") or s.get("et"), s.get("schema")
            if not (azione or schema):
                continue
            p, gs = s.get("p"), s.get("gs")
            x = esito(e, int(p), float(gs)) if p is not None and gs is not None else None
            righe.append({"partita_id": pid, "azione": azione, "schema": schema, "con_tempo": p is not None,
                          "attacco": None if x is None else ("noi" if x["squadra"] == mia else "loro"),
                          "esito": None if x is None else x["esito"], "punti": 0 if x is None else x["punti"],
                          "tiri": 0 if x is None else x["tiri"], "canestri": 0 if x is None else x["canestri"]})
    return pd.DataFrame(righe, columns=["partita_id", "azione", "schema", "con_tempo", "attacco", "esito", "punti",
                                        "tiri", "canestri"])


def riepilogo(sit: pd.DataFrame, per: list[str], attacco: str) -> pd.DataFrame:
    """Efficienza per tipo di azione, per schema o per entrambi (per = ["azione"], ["schema"] o tutti e due),
    solo per le situazioni con un esito e chi attaccava ("noi" o "loro")."""
    d = sit[(sit["attacco"] == attacco)].dropna(subset=per)
    cols = per + ["situazioni", "punti", "punti_per_situazione", "canestri", "tiri", "perc_tiro", "perse", "liberi",
                  "partite"]
    if d.empty:
        return pd.DataFrame(columns=cols)
    g = d.groupby(per, dropna=True)
    out = pd.DataFrame({
        "situazioni": g.size(), "punti": g["punti"].sum(), "canestri": g["canestri"].sum(), "tiri": g["tiri"].sum(),
        "perse": g["esito"].apply(lambda x: int((x == "palla persa").sum())),
        "liberi": g["esito"].apply(lambda x: int((x == "liberi").sum())),
        "partite": g["partita_id"].nunique()}).reset_index()
    out["punti_per_situazione"] = out["punti"] / out["situazioni"]
    out["perc_tiro"] = (100 * out["canestri"] / out["tiri"].where(out["tiri"] > 0)).round(1)
    return out.sort_values(["situazioni", "punti_per_situazione"], ascending=False)[cols]
