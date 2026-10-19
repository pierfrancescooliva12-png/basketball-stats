"""Verifica delle chiavi della vigilia: le chiavi della partita come le avrebbe date ASSIST
prima della gara (solo con le partite giocate fino al giorno prima) a confronto con quello
che è successo davvero.

Per ogni chiave (i Four Factors in attacco e in difesa): valore atteso, obiettivo, valore
reale nella partita, se l'obiettivo è stato raggiunto e quanti punti ha spostato rispetto al
previsto (peso del fattore × scostamento dal valore atteso × possessi della partita). La
somma dei punti spostati dalle chiavi spiega quasi tutto lo scarto tra margine previsto e
reale: il resto è il caso (tiri a parità di efficienza, liberi, ecc.) che i Four Factors non
vedono. Si verifica anche il ritmo che conveniva e i giocatori chiave."""

import numpy as np
import pandas as pd

from . import analysis as A
from . import chiavi as C
from . import previsioni as F


def _partita(bs: pd.DataFrame, pid: str, sid: int) -> pd.Series | None:
    r = bs[(bs["partita_id"] == pid) & (bs["squadra_id"] == sid)]
    return r.iloc[0] if not r.empty else None


def valori_partita(bs_riga: pd.DataFrame) -> pd.Series:
    """Four Factors e possessi della sola partita, con le stesse formule della stagione."""
    t = A.team_summary(bs_riga.assign(affidabile=True))
    return t.iloc[0]


def reale(f: str, lato: str, g: pd.Series) -> float:
    """Valore reale di un fattore nella partita, dal punto di vista della squadra."""
    if lato == "In attacco":
        return float(g[C.FATTORI[f][1]])
    if f == "orb":
        return 100.0 - float(g["drb_pct"])
    return float(g[C.FATTORI[f][2]])


def _conta(f: str, valore: float, g: pd.Series, lato: str) -> float:
    """Il valore come numero nella partita (palle perse, rimbalzi offensivi, liberi segnati)."""
    p = "" if lato == "In attacco" else "opp_"
    if f == "tov":
        return float(g[f"{p}perse"])
    if f == "orb":
        return float(g[f"{p}rimb_off"])
    if f == "ftr":
        return float(g[f"{p}tlm"])
    return np.nan


def verifica(ctx, sid: int, pid: str) -> dict | None:
    """Chiavi della vigilia contro la partita giocata. None se la partita non c'è o mancano
    i dati di prima."""
    bs = ctx.bs
    noi = _partita(bs, pid, sid)
    if noi is None:
        return None
    avv, camp, data = int(noi["avversario_id"]), noi["campionato_id"], noi["data"]
    prima = bs[(bs["campionato_id"] == camp) & (bs["data"] < data)]
    if prima[prima["squadra_id"] == sid].empty or prima[prima["squadra_id"] == avv].empty:
        return None
    lega = A.team_summary(prima)
    if not {sid, avv} <= set(lega["squadra_id"]):
        return None
    forze = F.strengths(prima, ctx._prior)
    if not {sid, avv} <= set(forze["squadra_id"]):
        return None
    hca = ctx.hca(camp)
    casa = bool(noi["casa"])
    lv = C.leve(lega, forze, sid, avv, casa, hca)
    rt = C.ritmo(forze, sid, avv, casa, hca)
    m0, poss_attesi = C._margine_noi(forze, sid, avv, casa, hca)

    g = valori_partita(bs[(bs["partita_id"] == pid) & (bs["squadra_id"] == sid)])
    poss = float(g.get("pace") or g.get("possessi") or poss_attesi)
    margine = float(noi["punti"] - noi["punti_subiti"])
    righe = []
    for _, k in lv.iterrows():
        f, lato = k["chiave"], k["lato"]
        v = reale(f, lato, g)
        verso = (1 if C.PESI[f] > 0 else -1) * (1 if lato == "In attacco" else -1)
        punti = verso * abs(C.PESI[f]) * (v - k["atteso"]) * poss / 100
        raggiunto = (v - k["obiettivo"]) * verso >= 0
        meglio = (v - k["atteso"]) * verso >= 0
        righe.append({"chiave": f, "lato": lato, "fattore": k["breve"], "situazione": k["situazione"],
                      "guadagno_atteso": k["guadagno"], "atteso": k["atteso"], "obiettivo": k["obiettivo"],
                      "reale": v, "atteso_n": k["atteso_n"], "obiettivo_n": k["obiettivo_n"],
                      "reale_n": _conta(f, v, g, lato), "raggiunto": bool(raggiunto),
                      "meglio_del_previsto": bool(meglio), "punti": punti})
    k = pd.DataFrame(righe)
    lento, veloce = rt.iloc[0], rt.iloc[-1]
    conviene_lento = lento["prob"] >= veloce["prob"]
    out = {"partita_id": pid, "squadra_id": sid, "avversario_id": avv, "avversario": noi["avversario"],
           "squadra": noi["squadra"], "data": data, "giornata": noi.get("giornata"), "casa": casa,
           "punti": int(noi["punti"]), "punti_subiti": int(noi["punti_subiti"]), "vinta": bool(noi["vinta"]),
           "prob_vigilia": 100 * C._prob(m0), "margine_previsto": m0, "margine_reale": margine,
           "chiavi": k, "punti_chiavi": float(k["punti"].sum()),
           "caso": margine - m0 - float(k["punti"].sum()),
           "raggiunte": int(k["raggiunto"].sum()), "totale_chiavi": len(k),
           "ritmo": {"conveniva": "lento" if conviene_lento else "veloce",
                     "possessi_attesi": poss_attesi, "possessi_reali": poss,
                     "rispettato": (poss <= poss_attesi) if conviene_lento else (poss >= poss_attesi)}}
    out["giocatori"] = _giocatori(ctx, sid, avv, pid, data)
    return out


def _giocatori(ctx, sid: int, avv: int, pid: str, data) -> list[dict]:
    """Giocatori chiave della vigilia (stagione fino al giorno prima) e cosa hanno fatto."""
    from . import validazione as V
    bt = V.carica()
    if bt.empty or "data" not in bt:
        return []
    bt = bt[(bt["stagione"] == ctx.stagione) & (bt["data"] < data)]
    bg = ctx.bg
    prima = bg[bg["data"] < data]
    out = []
    for squadra, avversario in ((avv, True), (sid, False)):
        try:
            gc = C.giocatori_chiave(prima, bt, squadra, ctx.nomi_giocatori)
        except Exception:
            continue
        if gc.empty:
            continue
        for r in gc[gc["effetto"] >= 0.5].head(3).itertuples():
            x = bg[(bg["partita_id"] == pid) & (bg["giocatore_id"] == r.giocatore_id)]
            fatto = float(x[r.colonna].iloc[0]) if not x.empty and x["minuti"].iloc[0] else None
            if avversario:
                rispettato = fatto is not None and fatto < r.soglia
                obiettivo = f"tenerlo sotto {r.soglia:.0f} {r.statistica}"
            else:
                rispettato = fatto is not None and fatto >= r.soglia
                obiettivo = f"portarlo ad almeno {r.soglia:.0f} {r.statistica}"
            out.append({"giocatore": r.giocatore, "avversario": avversario, "statistica": r.statistica,
                        "soglia": r.soglia, "fatto": fatto, "obiettivo": obiettivo,
                        "rispettato": rispettato, "effetto": r.effetto})
    return out


def frasi(v: dict) -> list[str]:
    """Sintesi in parole: quante chiavi rispettate e quanto hanno pesato sul risultato."""
    def n(x, d=1):
        return f"{x:+.{d}f}".replace(".", ",")
    k = v["chiavi"]
    out = [f"Alla vigilia: {v['prob_vigilia']:.0f}% di vittoria, margine previsto {n(v['margine_previsto'])}. "
           f"Finita {v['punti']}-{v['punti_subiti']} ({n(v['margine_reale'], 0)})."]
    out.append(f"Chiavi raggiunte: {v['raggiunte']} su {v['totale_chiavi']}. Rispetto al previsto le chiavi "
               f"hanno spostato {n(v['punti_chiavi'])} punti; il resto ({n(v['caso'])}) è dovuto a ciò che "
               "i Four Factors non vedono (tiri presi e segnati a parità di efficienza, episodi).")
    if not k.empty:
        top = k.reindex(k["punti"].abs().sort_values(ascending=False).index).iloc[0]
        out.append(f"La chiave che ha pesato di più: {top['fattore'].lower()} ({top['lato'].lower()}), "
                   f"{n(top['punti'])} punti rispetto al previsto.")
    r = v["ritmo"]
    out.append(f"Ritmo: conveniva una partita {'lenta' if r['conveniva'] == 'lento' else 'veloce'}; possessi {r['possessi_reali']:.0f} "
               f"(attesi {r['possessi_attesi']:.0f}) · " + ("rispettato" if r["rispettato"] else "non rispettato") + ".")
    return out


def _fmt(x, d=1) -> str:
    if x is None or pd.isna(x):
        return "–"
    return f"{x:.{d}f}".replace(".", ",")


def tabella(v: dict) -> list[dict]:
    """Righe pronte per tabelle: per tiro la percentuale, per palle perse, rimbalzi e liberi
    il numero nella partita."""
    out = []
    for r in v["chiavi"].itertuples():
        conta = r.chiave in C.UNITA and pd.notna(r.atteso_n)
        fmt = (lambda x: _fmt(x, 0)) if conta else (lambda x: _fmt(x) + "%")
        out.append({"Chiave": r.fattore, "Lato": r.lato.replace("In ", ""),
                    "Previsto": fmt(r.atteso_n if conta else r.atteso),
                    "Obiettivo": fmt(r.obiettivo_n if conta else r.obiettivo),
                    "In partita": fmt(r.reale_n if conta else r.reale),
                    "Esito": "raggiunta" if r.raggiunto else "mancata", "raggiunta": r.raggiunto,
                    "Punti rispetto al previsto": f"{r.punti:+.1f}".replace(".", ",")})
    return out


def stagione(ctx, sid: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(una riga per partita, una riga per chiave): quante volte le chiavi sono state
    raggiunte e come è finita quando sì e quando no."""
    pids = ctx.bs[ctx.bs["squadra_id"] == sid].sort_values("data")["partita_id"].tolist()
    partite, chiavi = [], []
    for pid in pids:
        v = verifica(ctx, sid, pid)
        if v is None:
            continue
        partite.append({"partita_id": pid, "giornata": v["giornata"], "avversario": v["avversario"],
                        "risultato": f"{'V' if v['vinta'] else 'P'} {v['punti']}-{v['punti_subiti']}",
                        "vinta": v["vinta"], "prob_vigilia": v["prob_vigilia"],
                        "raggiunte": v["raggiunte"], "totale": v["totale_chiavi"],
                        "punti_chiavi": v["punti_chiavi"], "margine_previsto": v["margine_previsto"],
                        "margine_reale": v["margine_reale"]})
        for r in v["chiavi"].itertuples():
            chiavi.append({"chiave": r.fattore, "lato": r.lato, "raggiunta": r.raggiunto,
                           "vinta": v["vinta"], "punti": r.punti})
    p, k = pd.DataFrame(partite), pd.DataFrame(chiavi)
    if k.empty:
        return p, k
    riass = []
    for (chiave, lato), g in k.groupby(["chiave", "lato"], sort=False):
        si, no = g[g["raggiunta"]], g[~g["raggiunta"]]
        riass.append({"Chiave": chiave, "Lato": lato.replace("In ", ""), "Raggiunta": f"{len(si)} su {len(g)}",
                      "Record quando raggiunta": f"{int(si['vinta'].sum())}-{len(si) - int(si['vinta'].sum())}"
                      if len(si) else "–",
                      "Record quando mancata": f"{int(no['vinta'].sum())}-{len(no) - int(no['vinta'].sum())}"
                      if len(no) else "–",
                      "Punti medi rispetto al previsto": f"{g['punti'].mean():+.1f}".replace(".", ",")})
    return p, pd.DataFrame(riass)
