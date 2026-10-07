"""Analisi della cronaca (play-by-play).

1. Ricostruzione dei quintetti in campo. La cronaca registra solo chi ENTRA ("Cambio"),
   non chi esce: chi esce si deduce dai vincoli (un giocatore uscito non può comparire in
   azioni successive finché non rientra) e, tra i possibili, si sceglie chi ha già giocato
   la quota maggiore dei suoi minuti ufficiali. Ogni partita viene poi verificata
   confrontando i minuti ricostruiti con quelli del box score: le statistiche sui quintetti
   (+/-, on/off, quintetti) usano solo le partite verificate.
2. Statistiche ricavate dagli eventi: finali punto a punto, rete degli assist, origine dei
   punti (da palla persa, seconde occasioni, contropiede), parziali, falli, timeout,
   profilo di tiro.
"""

import sqlite3
from collections import defaultdict

import numpy as np
import pandas as pd

FT = 0.44
CLUTCH_DA = 35 * 60          # ultimi 5 minuti del 4° quarto (e supplementari)
CLUTCH_MARGINE = 5
CONTROPIEDE_S = 8            # secondi dall'inizio del possesso
TOLLERANZA_MIN = 3.0         # scarto massimo sui minuti (quelli del box score sono arrotondati)
PUNTI = {"tiro2_fatto": 2, "tiro3_fatto": 3, "tl_fatto": 1}
TIRI = {"tiro2_fatto", "tiro2_sbagliato", "tiro3_fatto", "tiro3_sbagliato"}
ALTRO_LATO = {"casa": "ospite", "ospite": "casa"}


# ------------------------------------------------------------------ quintetti

def game_end(eventi: list[dict]) -> int:
    periodi = max((e["periodo"] or 4) for e in eventi)
    return 2400 + 300 * max(0, periodi - 4)


def reconstruct(eventi: list[dict], quintetti_base: dict, minuti_box: dict,
                obiettivo: dict | None = None) -> tuple[list, dict]:
    """Ricostruisce le frazioni con gli stessi 5 in campo.

    quintetti_base: {'casa': set(id), 'ospite': set(id)}; minuti_box: {id: minuti}.
    Restituisce (stint, qualità). Ogni stint: lato, inizio, fine, quintetto, punti_fatti,
    punti_subiti, poss_fatti, poss_subiti."""
    n = len(eventi)
    attivita = defaultdict(list)   # giocatore -> indici di azioni (non cambi)
    entrate = defaultdict(list)    # giocatore -> indici dei suoi ingressi
    for i, e in enumerate(eventi):
        gid = e["giocatore_id"]
        if not gid:
            continue
        (entrate if e["tipo"] == "cambio" else attivita)[gid].append(i)

    def next_after(lst, i, t):
        for j in lst:
            if j > i and (eventi[j]["secondi"] or 0) > t:
                return j
        return None

    def next_in(lst, i):
        for j in lst:
            if j > i:
                return j
        return None

    in_campo = {lato: set(q) for lato, q in quintetti_base.items()}
    giocati = defaultdict(float)       # secondi giocati finora
    entrato_a = {g: 0 for q in in_campo.values() for g in q}
    errori = 0
    confini = {"casa": [(0, 0, frozenset(in_campo["casa"]))],
               "ospite": [(0, 0, frozenset(in_campo["ospite"]))]}  # (indice, secondi, quintetto)

    for i, e in enumerate(eventi):
        lato, gid, t = e["lato"], e["giocatore_id"], e["secondi"] or 0
        if e["tipo"] != "cambio" or not gid or gid in in_campo[lato]:
            continue
        cand = []
        for p in in_campo[lato]:
            na, ni = next_after(attivita[p], i, t), next_in(entrate[p], i)
            valido = na is None or (ni is not None and ni < na)
            target = (obiettivo or minuti_box).get(p, 40)
            quota = (giocati[p] + t - entrato_a.get(p, t)) / max(60.0, 60 * target)
            cand.append((valido, quota, na if na is not None else n + 1, p))
        validi = [c for c in cand if c[0]]
        if validi:
            esce = max(validi, key=lambda c: (c[1], c[2]))[3]
        else:
            errori += 1
            esce = max(cand, key=lambda c: c[2])[3]
        giocati[esce] += t - entrato_a.get(esce, t)
        in_campo[lato].discard(esce)
        in_campo[lato].add(gid)
        entrato_a[gid] = t
        confini[lato].append((i, t, frozenset(in_campo[lato])))

    fine = game_end(eventi)
    for lato in in_campo:
        for p in in_campo[lato]:
            giocati[p] += fine - entrato_a.get(p, fine)

    # Punteggio dopo ogni evento e possessi per lato
    punti = np.array([[e["punti_casa"] or 0, e["punti_ospite"] or 0] for e in eventi])
    poss = np.zeros((n, 2))
    for i, e in enumerate(eventi):
        k = 0 if e["lato"] == "casa" else 1
        if e["tipo"] in TIRI or e["tipo"] == "persa":
            poss[i, k] += 1
        elif e["tipo"] in ("tl_fatto", "tl_sbagliato"):
            poss[i, k] += FT
        elif e["tipo"] == "rimb_off":
            poss[i, k] -= 1
    poss_cum = poss.cumsum(axis=0)

    def score_before(idx):
        return punti[idx - 1] if idx > 0 else np.array([0, 0])

    def poss_before(idx):
        return poss_cum[idx - 1] if idx > 0 else np.array([0.0, 0.0])

    stints = []
    for lato, k in (("casa", 0), ("ospite", 1)):
        b = confini[lato] + [(n, fine, None)]
        for (i0, t0, q), (i1, t1, _) in zip(b, b[1:]):
            if t1 <= t0 and i1 <= i0:
                continue
            ds = score_before(i1) - score_before(i0)
            dp = poss_before(i1) - poss_before(i0)
            stints.append({
                "lato": lato, "inizio": t0, "fine": t1,
                "quintetto": ",".join(sorted(q)),
                "punti_fatti": int(ds[k]), "punti_subiti": int(ds[1 - k]),
                "poss_fatti": float(dp[k]), "poss_subiti": float(dp[1 - k]),
            })

    err_min = max((abs(giocati.get(g, 0) / 60 - m) for g, m in minuti_box.items()), default=99)
    qualita = {"errori_coerenza": errori, "errore_minuti": round(float(err_min), 2),
               "quintetti_ok": bool(err_min <= TOLLERANZA_MIN and errori <= 2),
               "minuti": {g: giocati.get(g, 0) / 60 for g in minuti_box}}
    return stints, qualita


def reconstruct_best(eventi: list[dict], quintetti_base: dict, minuti_box: dict,
                     iterazioni: int = 6) -> tuple[list, dict]:
    """Ricostruzione con affinamento: dopo ogni tentativo gli obiettivi di minutaggio usati
    per scegliere chi esce vengono corretti dello scarto rispetto ai minuti ufficiali; si
    tiene il tentativo con lo scarto massimo più basso."""
    obiettivo = dict(minuti_box)
    best = None
    for _ in range(iterazioni):
        stints, q = reconstruct(eventi, quintetti_base, minuti_box, obiettivo)
        if best is None or (q["errore_minuti"], q["errori_coerenza"]) < \
                (best[1]["errore_minuti"], best[1]["errori_coerenza"]):
            best = (stints, q)
        if q["quintetti_ok"] and q["errore_minuti"] <= 1.0:
            break
        obiettivo = {g: max(0.5, obiettivo[g] - 0.7 * (q["minuti"][g] - m))
                     for g, m in minuti_box.items()}
    stints, q = best
    q = {k: v for k, v in q.items() if k != "minuti"}
    return stints, q


def quality(eventi: list[dict], punti_box: tuple[int, int]) -> dict:
    last = eventi[-1]
    return {
        "n_eventi": len(eventi),
        "punteggio_ok": (last["punti_casa"], last["punti_ospite"]) == tuple(punti_box),
        "zone_affidabili": any(e["tipo"] == "tiro2_fatto" and e["zona"] == "area" for e in eventi),
    }


# ------------------------------------------------------------------ caricamento

def _has_table(conn, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                        (name,)).fetchone() is not None


def _games(conn, stagione):
    if not _has_table(conn, "pbp_qualita"):
        return []
    return conn.execute(
        """SELECT p.partita_id, p.gameid, p.stagione, p.campionato_id, p.squadra_casa_id,
                  p.squadra_ospite_id, p.data, p.giornata, q.quintetti_ok
           FROM partite p JOIN pbp_qualita q USING (partita_id)
           WHERE (:s IS NULL OR p.stagione = :s) ORDER BY p.partita_id""",
        {"s": stagione}).fetchall()


def load_events(conn: sqlite3.Connection, stagione: str | None = None,
                base=None) -> pd.DataFrame:
    from . import db
    frames = []
    for pid, gameid, stag, camp, home, away, data, giornata, _ in _games(conn, stagione):
        d = db.load_pbp_file(stag, gameid, base)
        if not d:
            continue
        f = pd.DataFrame(d["eventi"]["righe"], columns=d["eventi"]["campi"])
        f["partita_id"], f["campionato_id"], f["stagione"] = pid, camp, stag
        f["squadra_casa_id"], f["squadra_ospite_id"] = home, away
        f["data"], f["giornata"] = data, giornata
        frames.append(f)
    if not frames:
        return pd.DataFrame()
    ev = pd.concat(frames, ignore_index=True)
    ev["casa"] = ev["squadra_id"] == ev["squadra_casa_id"]
    ev["avversario_id"] = np.where(ev["casa"], ev["squadra_ospite_id"], ev["squadra_casa_id"])
    ev["punti"] = ev["tipo"].map(PUNTI).fillna(0).astype(int)
    # Margine (dal punto di vista della squadra dell'evento) PRIMA dell'evento
    prev_c = ev.groupby("partita_id")["punti_casa"].shift(fill_value=0)
    prev_o = ev.groupby("partita_id")["punti_ospite"].shift(fill_value=0)
    ev["margine_prima"] = np.where(ev["casa"], prev_c - prev_o, prev_o - prev_c)
    ev["clutch"] = (ev["secondi"] >= CLUTCH_DA) & (ev["margine_prima"].abs() <= CLUTCH_MARGINE)
    return ev


def load_stints(conn: sqlite3.Connection, stagione: str | None = None,
                solo_affidabili: bool = True, base=None) -> pd.DataFrame:
    from . import db
    frames = []
    for pid, gameid, stag, camp, *_, ok in _games(conn, stagione):
        if solo_affidabili and not ok:
            continue
        d = db.load_pbp_file(stag, gameid, base)
        if not d or not d["stint"]["righe"]:
            continue
        f = pd.DataFrame(d["stint"]["righe"], columns=d["stint"]["campi"])
        f["partita_id"], f["campionato_id"], f["stagione"] = pid, camp, stag
        frames.append(f)
    if not frames:
        return pd.DataFrame(columns=["partita_id", "campionato_id", "stagione", "squadra_id",
                                     "inizio", "fine", "quintetto", "punti_fatti",
                                     "punti_subiti", "poss_fatti", "poss_subiti", "secondi"])
    st = pd.concat(frames, ignore_index=True)
    st["secondi"] = st["fine"] - st["inizio"]
    return st


def coverage(conn: sqlite3.Connection, stagione: str | None = None) -> pd.DataFrame:
    if not _has_table(conn, "pbp_qualita"):
        return pd.DataFrame(columns=["campionato_id", "partite", "con_cronaca", "quintetti_ok",
                                     "zone_ok"])
    q = """SELECT p.campionato_id, COUNT(*) AS partite, COUNT(q.partita_id) AS con_cronaca,
                  SUM(q.quintetti_ok) AS quintetti_ok, SUM(q.zone_affidabili) AS zone_ok
           FROM partite p LEFT JOIN pbp_qualita q USING (partita_id)"""
    params = ()
    if stagione:
        q += " WHERE p.stagione = ?"
        params = (stagione,)
    return pd.read_sql_query(q + " GROUP BY p.campionato_id", conn, params=params)


# ------------------------------------------------------------------ +/- e quintetti

def _explode(st: pd.DataFrame) -> pd.DataFrame:
    x = st.assign(giocatore_id=st["quintetto"].str.split(",")).explode("giocatore_id")
    return x


def on_off(st: pd.DataFrame) -> pd.DataFrame:
    """+/-, rating con il giocatore in campo e fuori, per giocatore e squadra."""
    if st.empty:
        return pd.DataFrame()
    x = _explode(st)
    on = x.groupby(["campionato_id", "squadra_id", "giocatore_id"]).agg(
        sec=("secondi", "sum"), pf=("punti_fatti", "sum"), ps=("punti_subiti", "sum"),
        poss_f=("poss_fatti", "sum"), poss_s=("poss_subiti", "sum"),
        partite=("partita_id", "nunique")).reset_index()
    team = st.groupby(["squadra_id"]).agg(t_pf=("punti_fatti", "sum"),
                                         t_ps=("punti_subiti", "sum"),
                                         t_pof=("poss_fatti", "sum"),
                                         t_pos=("poss_subiti", "sum")).reset_index()
    on = on.merge(team, on="squadra_id")
    poss_on = (on["poss_f"] + on["poss_s"]) / 2
    poss_off = ((on["t_pof"] - on["poss_f"]) + (on["t_pos"] - on["poss_s"])) / 2
    on["minuti_campo"] = on["sec"] / 60
    on["plus_minus"] = on["pf"] - on["ps"]
    on["plus_minus_40"] = 40 * on["plus_minus"] / on["minuti_campo"].where(on["minuti_campo"] > 0)
    on["net_on"] = 100 * (on["pf"] - on["ps"]) / poss_on.where(poss_on > 0)
    on["net_off"] = 100 * ((on["t_pf"] - on["pf"]) - (on["t_ps"] - on["ps"])) / \
        poss_off.where(poss_off > 5)
    on["on_off"] = on["net_on"] - on["net_off"]
    on["ortg_on"] = 100 * on["pf"] / on["poss_f"].where(on["poss_f"] > 0)
    on["drtg_on"] = 100 * on["ps"] / on["poss_s"].where(on["poss_s"] > 0)
    return on.drop(columns=["t_pf", "t_ps", "t_pof", "t_pos", "sec"])


def lineups(st: pd.DataFrame, min_minuti: float = 5.0) -> pd.DataFrame:
    """Quintetti: minuti, +/-, rating."""
    if st.empty:
        return pd.DataFrame()
    g = st.groupby(["campionato_id", "squadra_id", "quintetto"]).agg(
        sec=("secondi", "sum"), pf=("punti_fatti", "sum"), ps=("punti_subiti", "sum"),
        poss_f=("poss_fatti", "sum"), poss_s=("poss_subiti", "sum"),
        partite=("partita_id", "nunique")).reset_index()
    g["minuti"] = g["sec"] / 60
    g = g[g["minuti"] >= min_minuti].copy()
    poss = (g["poss_f"] + g["poss_s"]) / 2
    g["plus_minus"] = g["pf"] - g["ps"]
    g["ortg"] = 100 * g["pf"] / g["poss_f"].where(g["poss_f"] > 0)
    g["drtg"] = 100 * g["ps"] / g["poss_s"].where(g["poss_s"] > 0)
    g["net_rtg"] = 100 * (g["pf"] - g["ps"]) / poss.where(poss > 0)
    return g.drop(columns="sec").sort_values("minuti", ascending=False)


def name_lineup(quintetto: str, nomi: dict) -> str:
    """'A1,A2,...' -> 'Cognome, Cognome, ...'"""
    out = []
    for g in quintetto.split(","):
        nome = nomi.get(g, g)
        out.append(nome.split()[-1] if " " in nome else nome)
    return " · ".join(out)


# ------------------------------------------------------------------ eventi

def clutch_players(ev: pd.DataFrame) -> pd.DataFrame:
    """Finali punto a punto (ultimi 5' con scarto ≤ 5): statistiche individuali."""
    c = ev[ev["clutch"] & ev["giocatore_id"].notna()]
    if c.empty:
        return pd.DataFrame()
    t = c.assign(
        fgm=c["tipo"].isin(["tiro2_fatto", "tiro3_fatto"]), fga=c["tipo"].isin(TIRI),
        t3m=c["tipo"] == "tiro3_fatto", t3a=c["tipo"].isin(["tiro3_fatto", "tiro3_sbagliato"]),
        ftm=c["tipo"] == "tl_fatto", fta=c["tipo"].isin(["tl_fatto", "tl_sbagliato"]),
        tov=c["tipo"] == "persa", ast=c["tipo"] == "assist")
    g = t.groupby(["campionato_id", "squadra_id", "giocatore_id"]).agg(
        punti=("punti", "sum"), fgm=("fgm", "sum"), fga=("fga", "sum"), t3m=("t3m", "sum"),
        t3a=("t3a", "sum"), ftm=("ftm", "sum"), fta=("fta", "sum"), perse=("tov", "sum"),
        assist=("ast", "sum"), partite=("partita_id", "nunique")).reset_index()
    g["fg_pct"] = 100 * g["fgm"] / g["fga"].where(g["fga"] > 0)
    g["tl_pct"] = 100 * g["ftm"] / g["fta"].where(g["fta"] > 0)
    g["ts_pct"] = 100 * g["punti"] / (2 * (g["fga"] + FT * g["fta"])).where(
        (g["fga"] + g["fta"]) > 0)
    # Quota dei tiri della squadra nei finali presi dal giocatore
    tot = g.groupby("squadra_id")[["fga", "fta"]].transform("sum")
    g["quota_tiri"] = 100 * (g["fga"] + FT * g["fta"]) / (tot["fga"] + FT * tot["fta"]).where(
        (tot["fga"] + tot["fta"]) > 0)
    return g.sort_values(["squadra_id", "punti"], ascending=[True, False])


def clutch_teams(ev: pd.DataFrame, bs: pd.DataFrame) -> pd.DataFrame:
    """Per squadra: partite con finale punto a punto, record, punti fatti/subiti nei finali."""
    c = ev[ev["clutch"]]
    if c.empty:
        return pd.DataFrame()
    pf = c.groupby(["partita_id", "squadra_id"])["punti"].sum().rename("pf").reset_index()
    giochi = c[["partita_id", "squadra_casa_id", "squadra_ospite_id"]].drop_duplicates()
    rows = []
    for r in giochi.itertuples():
        for sid, oid in ((r.squadra_casa_id, r.squadra_ospite_id),
                         (r.squadra_ospite_id, r.squadra_casa_id)):
            f = pf[(pf.partita_id == r.partita_id) & (pf.squadra_id == sid)]["pf"].sum()
            s = pf[(pf.partita_id == r.partita_id) & (pf.squadra_id == oid)]["pf"].sum()
            rows.append((r.partita_id, sid, f, s))
    d = pd.DataFrame(rows, columns=["partita_id", "squadra_id", "pf", "ps"])
    d = d.merge(bs[["partita_id", "squadra_id", "vinta", "campionato_id"]],
                on=["partita_id", "squadra_id"], how="left")
    out = d.groupby(["campionato_id", "squadra_id"]).agg(
        partite_clutch=("partita_id", "nunique"), vinte_clutch=("vinta", "sum"),
        punti_fatti=("pf", "sum"), punti_subiti=("ps", "sum")).reset_index()
    out["diff_clutch"] = out["punti_fatti"] - out["punti_subiti"]
    out["record_clutch"] = out["vinte_clutch"].astype(int).astype(str) + "-" + (
        out["partite_clutch"] - out["vinte_clutch"]).astype(int).astype(str)
    return out


def assist_network(ev: pd.DataFrame) -> pd.DataFrame:
    """Coppie assistente -> realizzatore: canestri e punti."""
    rows = []
    for pid, g in ev.groupby("partita_id", sort=False):
        recs = g.to_dict("records")
        for i, e in enumerate(recs):
            if e["tipo"] != "assist" or not e["giocatore_id"]:
                continue
            for j in (i - 1, i - 2, i + 1):
                if 0 <= j < len(recs):
                    s = recs[j]
                    if (s["tipo"] in ("tiro2_fatto", "tiro3_fatto") and s["squadra_id"] ==
                            e["squadra_id"] and s["secondi"] == e["secondi"] and s["giocatore_id"]):
                        rows.append((e["campionato_id"], e["squadra_id"], e["giocatore_id"],
                                     s["giocatore_id"], PUNTI[s["tipo"]]))
                        break
    d = pd.DataFrame(rows, columns=["campionato_id", "squadra_id", "assistente", "realizzatore",
                                    "punti"])
    if d.empty:
        return d
    return d.groupby(["campionato_id", "squadra_id", "assistente", "realizzatore"]).agg(
        canestri=("punti", "size"), punti=("punti", "sum")).reset_index().sort_values(
        "canestri", ascending=False)


def possession_origins(ev: pd.DataFrame) -> pd.DataFrame:
    """Origine dei punti di ogni squadra (stima dalla cronaca):
    da palla persa avversaria, da seconda occasione (rimbalzo offensivo), in contropiede
    (entro 8 secondi da rimbalzo difensivo o recupero)."""
    d = origins_by_game(ev)
    if d.empty:
        return d
    return _aggregate_origins(d)


def origins_by_game(ev: pd.DataFrame) -> pd.DataFrame:
    """Una riga per ogni canestro (o libero): partita, squadra, punti, origine del possesso."""
    rows = []
    for pid, g in ev.groupby("partita_id", sort=False):
        start = {}   # squadra -> (tipo inizio possesso, secondi)
        for e in g.itertuples():
            sid, opp, t = e.squadra_id, e.avversario_id, e.secondi or 0
            if e.tipo == "rimb_dif":
                start[sid] = ("rimbalzo", t)
            elif e.tipo == "recupero":
                start[sid] = ("palla_persa", t)
            elif e.tipo == "persa":
                start[opp] = ("palla_persa", t)
            elif e.tipo == "rimb_off":
                start[sid] = ("seconda", t)
            if e.punti:
                origine, t0 = start.get(sid, ("rimessa", t))
                contropiede = origine in ("rimbalzo", "palla_persa") and (t - t0) <= CONTROPIEDE_S \
                    and e.tipo != "tl_fatto"
                rows.append((e.campionato_id, pid, sid, e.punti, origine, contropiede))
                # Dopo un canestro (o un libero) la palla passa all'avversario su rimessa
                start[opp] = ("rimessa", t)
    return pd.DataFrame(rows, columns=["campionato_id", "partita_id", "squadra_id", "punti",
                                       "origine", "contropiede"])


def _aggregate_origins(d: pd.DataFrame) -> pd.DataFrame:
    tot = d.groupby(["campionato_id", "squadra_id"])["punti"].sum()
    n_g = d.groupby(["campionato_id", "squadra_id"])["partita_id"].nunique()
    out = pd.DataFrame({
        "partite": n_g,
        "punti_da_perse": d[d.origine == "palla_persa"].groupby(["campionato_id", "squadra_id"])
        ["punti"].sum(),
        "punti_seconda_occasione": d[d.origine == "seconda"].groupby(
            ["campionato_id", "squadra_id"])["punti"].sum(),
        "punti_contropiede": d[d.contropiede].groupby(["campionato_id", "squadra_id"])
        ["punti"].sum(),
        "punti_totali": tot,
    }).fillna(0).reset_index()
    for c in ("punti_da_perse", "punti_seconda_occasione", "punti_contropiede"):
        out[f"{c}_pg"] = out[c] / out["partite"]
        out[f"quota_{c}"] = 100 * out[c] / out["punti_totali"]
    return out


def runs(ev: pd.DataFrame, soglia: int = 8) -> pd.DataFrame:
    """Parziali: per squadra, quanti break da almeno `soglia` punti a zero piazza e subisce,
    e il break massimo."""
    rows = []
    for pid, g in ev[ev["punti"] > 0].groupby("partita_id", sort=False):
        cur_sid, cur = None, 0
        sids = set(g["squadra_casa_id"].iloc[:1]) | set(g["squadra_ospite_id"].iloc[:1])
        best = {s: 0 for s in sids}
        made = {s: 0 for s in sids}
        for e in g.itertuples():
            if e.squadra_id == cur_sid:
                cur += e.punti
            else:
                if cur_sid is not None and cur >= soglia:
                    made[cur_sid] += 1
                cur_sid, cur = e.squadra_id, e.punti
            best[cur_sid] = max(best[cur_sid], cur)
        if cur_sid is not None and cur >= soglia:
            made[cur_sid] += 1
        a, b = list(sids) if len(sids) == 2 else (list(sids) * 2)[:2]
        camp = g["campionato_id"].iloc[0]
        rows.append((camp, pid, a, made[a], made[b], best[a], best[b]))
        rows.append((camp, pid, b, made[b], made[a], best[b], best[a]))
    d = pd.DataFrame(rows, columns=["campionato_id", "partita_id", "squadra_id", "break_fatti",
                                    "break_subiti", "max_fatto", "max_subito"])
    if d.empty:
        return d
    return d.groupby(["campionato_id", "squadra_id"]).agg(
        partite=("partita_id", "nunique"), break_fatti=("break_fatti", "sum"),
        break_subiti=("break_subiti", "sum"), max_fatto=("max_fatto", "max"),
        max_subito=("max_subito", "max")).reset_index().assign(
        break_fatti_pg=lambda x: x["break_fatti"] / x["partite"],
        break_subiti_pg=lambda x: x["break_subiti"] / x["partite"])


def fouls(ev: pd.DataFrame) -> pd.DataFrame:
    """Falli per giocatore: media per partita, quota di partite con problemi di falli
    (2+ nel primo quarto o 3+ all'intervallo), partite chiuse per 5 falli."""
    f = ev[(ev["tipo"] == "fallo") & ev["giocatore_id"].notna()]
    if f.empty:
        return pd.DataFrame()
    per_game = f.groupby(["campionato_id", "squadra_id", "giocatore_id", "partita_id"]).agg(
        totali=("tipo", "size"),
        q1=("periodo", lambda p: (p == 1).sum()),
        primo_tempo=("periodo", lambda p: (p <= 2).sum())).reset_index()
    per_game["problemi"] = (per_game["q1"] >= 2) | (per_game["primo_tempo"] >= 3)
    per_game["fuori_5"] = per_game["totali"] >= 5
    return per_game.groupby(["campionato_id", "squadra_id", "giocatore_id"]).agg(
        partite_con_falli=("partita_id", "nunique"), falli=("totali", "sum"),
        partite_problemi=("problemi", "sum"), uscite_5_falli=("fuori_5", "sum")).reset_index()


def team_fouls_bonus(ev: pd.DataFrame) -> pd.DataFrame:
    """Minuto medio del periodo in cui la squadra commette il 5° fallo (avversari in bonus)."""
    f = ev[ev["tipo"].isin(["fallo", "fallo_tecnico"]) & (ev["periodo"] <= 4)].copy()
    if f.empty:
        return pd.DataFrame()
    f["k"] = f.groupby(["partita_id", "squadra_id", "periodo"]).cumcount() + 1
    quinto = f[f["k"] == 5].copy()
    quinto["minuto_periodo"] = (quinto["secondi"] - (quinto["periodo"] - 1) * 600) / 60
    n_per = f.groupby(["campionato_id", "squadra_id"]).apply(
        lambda x: x[["partita_id", "periodo"]].drop_duplicates().shape[0], include_groups=False)
    out = quinto.groupby(["campionato_id", "squadra_id"]).agg(
        periodi_in_bonus=("periodo", "size"), minuto_medio_bonus=("minuto_periodo", "mean"))
    out = out.reindex(n_per.index).fillna({"periodi_in_bonus": 0})
    out["quota_periodi_bonus"] = 100 * out["periodi_in_bonus"] / n_per
    return out.reset_index()


def timeouts(ev: pd.DataFrame, finestra: int = 120) -> pd.DataFrame:
    """Effetto dei propri timeout: differenza punti nei 2 minuti dopo e nei 2 minuti prima."""
    t_out = ev[ev["tipo"] == "timeout"]
    rows = []
    scoring = ev[ev["punti"] > 0]
    by_game = {pid: g for pid, g in scoring.groupby("partita_id")}
    for e in t_out.itertuples():
        g = by_game.get(e.partita_id)
        if g is None:
            continue
        t = e.secondi or 0
        dopo = g[(g["secondi"] > t) & (g["secondi"] <= t + finestra)]
        prima = g[(g["secondi"] > t - finestra) & (g["secondi"] <= t)]
        d_dopo = dopo.loc[dopo.squadra_id == e.squadra_id, "punti"].sum() - \
            dopo.loc[dopo.squadra_id != e.squadra_id, "punti"].sum()
        d_prima = prima.loc[prima.squadra_id == e.squadra_id, "punti"].sum() - \
            prima.loc[prima.squadra_id != e.squadra_id, "punti"].sum()
        rows.append((e.campionato_id, e.squadra_id, d_prima, d_dopo))
    d = pd.DataFrame(rows, columns=["campionato_id", "squadra_id", "diff_prima", "diff_dopo"])
    if d.empty:
        return d
    return d.groupby(["campionato_id", "squadra_id"]).agg(
        timeout=("diff_dopo", "size"), diff_prima=("diff_prima", "mean"),
        diff_dopo=("diff_dopo", "mean")).reset_index()


def shot_profile(ev: pd.DataFrame, zone_ok: set) -> pd.DataFrame:
    """Tiri per zona, per giocatore. Area / fuori area solo dalle partite in cui la cronaca
    distingue le zone (zone_ok = insieme di partita_id)."""
    s = ev[ev["tipo"].isin(TIRI) & ev["giocatore_id"].notna()].copy()
    if s.empty:
        return pd.DataFrame()
    s["fatto"] = s["tipo"].str.endswith("fatto")
    s["affidabile"] = s["partita_id"].isin(zone_ok)
    keys = ["campionato_id", "squadra_id", "giocatore_id"]
    out = s.groupby(keys).agg(tiri=("tipo", "size")).reset_index()
    for nome, mask in (("area", (s.zona.isin(["area", "schiacciata"])) & s.affidabile),
                       ("media", (s.zona == "fuori_area") & s.affidabile),
                       ("tre", s.zona == "tre"), ("schiacciate", s.zona == "schiacciata")):
        g = s[mask].groupby(keys).agg(**{f"{nome}_t": ("tipo", "size"),
                                         f"{nome}_r": ("fatto", "sum")}).reset_index()
        out = out.merge(g, on=keys, how="left")
    conteggi = [c for c in out.columns if c.endswith(("_t", "_r"))]
    out[conteggi] = out[conteggi].fillna(0).astype(int)
    rel = s[s.affidabile & s.tipo.str.startswith("tiro2")].groupby(keys).size()
    out = out.merge(rel.rename("tiri2_zona").reset_index(), on=keys, how="left")
    out["tiri2_zona"] = out["tiri2_zona"].fillna(0).astype(int)
    for nome in ("area", "media", "tre"):
        out[f"{nome}_pct"] = 100 * out[f"{nome}_r"] / out[f"{nome}_t"].where(out[f"{nome}_t"] > 0)
    out["quota_area"] = 100 * out["area_t"] / out["tiri2_zona"].where(out["tiri2_zona"] > 0)
    return out


# ------------------------------------------------------------------ abbinamento codici

def _tokens(nome: str) -> frozenset:
    import unicodedata
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return frozenset(t for t in "".join(c if c.isalnum() else " " for c in s).split() if len(t) > 1)


def align_ids(eventi: list[dict], box: dict, nomi_pbp: dict) -> int:
    """Allinea i codici giocatore della cronaca a quelli del box score (in alcune stagioni la
    cronaca usa codici diversi). Abbina per nome all'interno della stessa squadra.
    Restituisce il numero di codici non abbinati."""
    per_lato = {}
    for lato in ("casa", "ospite"):
        per_lato[lato] = {g["giocatore_id"]: _tokens(g["nome"]) for g in box[lato]["giocatori"]}
    mappa, non_abbinati = {}, set()
    for e in eventi:
        gid = e["giocatore_id"]
        if not gid or gid in per_lato[e["lato"]]:
            continue
        if gid not in mappa:
            tk = _tokens(nomi_pbp.get(gid, ""))
            match = [b for b, t in per_lato[e["lato"]].items() if t and t == tk]
            if not match and tk:  # almeno una parola del nome in comune, e un solo candidato
                match = [b for b, t in per_lato[e["lato"]].items() if t & tk]
                match = match if len(match) == 1 else []
            mappa[gid] = match[0] if match else None
            if not match:
                non_abbinati.add(gid)
        e["giocatore_id"] = mappa[gid]
    return len(non_abbinati)
