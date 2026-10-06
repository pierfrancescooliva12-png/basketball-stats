"""Approfondimenti per lo staff: rotazioni, taglia dei quintetti, momenti della partita,
origine dei punti concessi, riposo e trasferte, presenze, confronto tra categorie e frasi
di sintesi su squadre e giocatori.

Tutte le funzioni lavorano sui dati già caricati (box score, cronaca, quintetti verificati)
e restituiscono tabelle pronte da mostrare.
"""

import math

import numpy as np
import pandas as pd

from . import analysis as A
from . import luoghi

FINE_REGOLAMENTARE = 2400          # 40 minuti, in secondi


# ------------------------------------------------------------------ rotazioni

def _minuti_stint(st: pd.DataFrame) -> pd.DataFrame:
    """Secondi in campo per giocatore e minuto di gioco (solo tempi regolamentari)."""
    rows = []
    for s in st.itertuples():
        ini, fin = int(s.inizio), int(min(s.fine, FINE_REGOLAMENTARE))
        if fin <= ini:
            continue
        for m in range(ini // 60, math.ceil(fin / 60)):
            sec = min(fin, (m + 1) * 60) - max(ini, m * 60)
            if sec > 0:
                rows.append((s.campionato_id, s.squadra_id, s.partita_id, s.quintetto, m, sec))
    d = pd.DataFrame(rows, columns=["campionato_id", "squadra_id", "partita_id", "quintetto",
                                    "minuto", "secondi"])
    d = d.assign(giocatore_id=d["quintetto"].str.split(",")).explode("giocatore_id")
    return d.drop(columns="quintetto")


def rotazioni(st: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Schema delle rotazioni di ogni squadra, dalle partite con quintetti verificati.

    Restituisce:
      griglia   squadra, giocatore, minuto (0-39) e quota delle partite in cui era in campo
      giocatori quota da titolare, minuti medi, quota in campo negli ultimi 5', minuto medio
                del primo ingresso per chi parte dalla panchina
      squadre   partite analizzate, minuto medio del primo cambio, giocatori in rotazione,
                quintetto base più usato e quota di partite in cui è partito
    """
    vuoto = {"griglia": pd.DataFrame(), "giocatori": pd.DataFrame(), "squadre": pd.DataFrame()}
    if st is None or st.empty:
        return vuoto
    st = st.sort_values(["partita_id", "squadra_id", "inizio"])
    n_part = st.groupby("squadra_id")["partita_id"].nunique().rename("partite")
    m = _minuti_stint(st)
    griglia = (m.groupby(["campionato_id", "squadra_id", "giocatore_id", "minuto"])["secondi"]
               .sum().reset_index())
    griglia = griglia.merge(n_part, on="squadra_id")
    griglia["quota"] = (100 * griglia["secondi"] / (60 * griglia["partite"])).clip(upper=100)

    primo = st.groupby(["partita_id", "squadra_id"]).head(1)
    titolari = primo.assign(giocatore_id=primo["quintetto"].str.split(",")).explode("giocatore_id")
    quota_tit = titolari.groupby(["squadra_id", "giocatore_id"])["partita_id"].nunique()

    x = st.assign(giocatore_id=st["quintetto"].str.split(",")).explode("giocatore_id")
    per_gioc = x.groupby(["campionato_id", "squadra_id", "giocatore_id"]).agg(
        secondi=("secondi", "sum"), partite_giocate=("partita_id", "nunique")).reset_index()
    per_gioc = per_gioc.merge(n_part, on="squadra_id")
    per_gioc["minuti_pg"] = per_gioc["secondi"] / 60 / per_gioc["partite_giocate"]
    per_gioc["quota_titolare"] = 100 * per_gioc.set_index(["squadra_id", "giocatore_id"]).index.map(
        quota_tit).fillna(0).to_numpy() / per_gioc["partite"]
    finale = m[m["minuto"] >= 35].groupby(["squadra_id", "giocatore_id"])["secondi"].sum()
    per_gioc["quota_finale"] = (100 * per_gioc.set_index(["squadra_id", "giocatore_id"]).index.map(
        finale).fillna(0).to_numpy() / (300 * per_gioc["partite"])).clip(upper=100)
    # primo ingresso di chi non parte in quintetto
    tit_set = set(zip(titolari["partita_id"], titolari["squadra_id"], titolari["giocatore_id"]))
    ingressi = x.groupby(["partita_id", "squadra_id", "giocatore_id"])["inizio"].min().reset_index()
    ingressi = ingressi[[(p, s, g) not in tit_set for p, s, g in
                         zip(ingressi["partita_id"], ingressi["squadra_id"],
                             ingressi["giocatore_id"])]]
    ing = ingressi.groupby(["squadra_id", "giocatore_id"])["inizio"].median() / 60
    per_gioc["minuto_ingresso"] = per_gioc.set_index(["squadra_id", "giocatore_id"]).index.map(
        ing).to_numpy()

    primo_cambio = st.groupby(["partita_id", "squadra_id"])["fine"].first()
    sq = pd.DataFrame({"partite": n_part,
                       "minuto_primo_cambio": primo_cambio.groupby("squadra_id").median() / 60})
    in_rot = x.groupby(["partita_id", "squadra_id", "giocatore_id"])["secondi"].sum()
    sq["giocatori_rotazione"] = (in_rot[in_rot >= 300].groupby(["partita_id", "squadra_id"]).size()
                                 .groupby("squadra_id").mean())
    base = primo.groupby(["squadra_id", "quintetto"]).size().rename("volte").reset_index()
    base = base.sort_values("volte", ascending=False).groupby("squadra_id").head(1)
    sq = sq.join(base.set_index("squadra_id"))
    sq["quota_quintetto_base"] = 100 * sq["volte"] / sq["partite"]
    return {"griglia": griglia, "giocatori": per_gioc, "squadre": sq.reset_index()}


# ------------------------------------------------------------------ taglia dei quintetti

TAGLIE = ["Piccolo", "Medio", "Grande"]


def taglia_quintetti(st: pd.DataFrame, altezze: dict) -> pd.DataFrame:
    """Rendimento dei quintetti per taglia (altezza media dei cinque in campo).

    Le soglie sono i terzili del campionato (pesati per minuti): "piccolo" è un quintetto
    più basso di due terzi di quelli usati nel campionato."""
    if st is None or st.empty or not altezze:
        return pd.DataFrame()
    q = st["quintetto"].drop_duplicates()
    medie = {}
    for k in q:
        h = [altezze.get(g) for g in k.split(",")]
        h = [v for v in h if v and not pd.isna(v)]
        medie[k] = sum(h) / len(h) if len(h) >= 4 else np.nan
    d = st.assign(altezza=st["quintetto"].map(medie)).dropna(subset=["altezza"])
    if d.empty:
        return pd.DataFrame()
    parti = []
    for camp, g in d.groupby("campionato_id"):
        o = g.sort_values("altezza", kind="stable")
        prima = (o["secondi"].cumsum() - o["secondi"]) / o["secondi"].sum()
        taglia = pd.Series(np.select([prima < 1 / 3, prima >= 2 / 3], ["Piccolo", "Grande"],
                                     "Medio"), index=o.index)
        # stessa altezza, stessa taglia (quella della maggior parte dei minuti)
        taglia = taglia.groupby(o["altezza"]).transform(lambda x: x.mode().iloc[0])
        o = o.assign(taglia=taglia)
        piccoli, grandi = o[o["taglia"] == "Piccolo"], o[o["taglia"] == "Grande"]
        t1 = piccoli["altezza"].max() if not piccoli.empty else np.nan
        t2 = grandi["altezza"].min() if not grandi.empty else np.nan
        parti.append(o.assign(soglia_bassa=t1, soglia_alta=t2))
    d = pd.concat(parti)
    out = d.groupby(["campionato_id", "squadra_id", "taglia"]).agg(
        secondi=("secondi", "sum"), pf=("punti_fatti", "sum"), ps=("punti_subiti", "sum"),
        poss_f=("poss_fatti", "sum"), poss_s=("poss_subiti", "sum"),
        altezza=("altezza", "mean"), soglia_bassa=("soglia_bassa", "first"),
        soglia_alta=("soglia_alta", "first")).reset_index()
    tot = out.groupby("squadra_id")["secondi"].transform("sum")
    out["quota_minuti"] = 100 * out["secondi"] / tot
    out["minuti"] = out["secondi"] / 60
    out["ortg"] = 100 * out["pf"] / out["poss_f"].where(out["poss_f"] > 0)
    out["drtg"] = 100 * out["ps"] / out["poss_s"].where(out["poss_s"] > 0)
    out["net_rtg"] = out["ortg"] - out["drtg"]
    out.loc[out["minuti"] < 10, ["ortg", "drtg", "net_rtg"]] = np.nan
    out["taglia"] = pd.Categorical(out["taglia"], TAGLIE, ordered=True)
    return out.sort_values(["squadra_id", "taglia"])


def altezza_in_campo(st: pd.DataFrame, altezze: dict) -> pd.Series:
    """Altezza media in campo di ogni squadra (pesata per minuti)."""
    if st is None or st.empty:
        return pd.Series(dtype=float)
    x = st.assign(giocatore_id=st["quintetto"].str.split(",")).explode("giocatore_id")
    x["h"] = x["giocatore_id"].map(altezze)
    x = x.dropna(subset=["h"])
    return (x["h"] * x["secondi"]).groupby(x["squadra_id"]).sum() / \
        x.groupby("squadra_id")["secondi"].sum()


# ------------------------------------------------------------------ momenti della partita

MOMENTI = {
    "inizio": ("Primi 3' di partita", lambda p, s: (p == 1) & (s < 180)),
    "fine_quarto": ("Ultimi 2' di ogni quarto",
                    lambda p, s: (p <= 4) & ((s % 600) >= 480)),
    "rientro": ("Primi 3' del 3° quarto", lambda p, s: (s >= 1200) & (s < 1380)),
    "ultimi5": ("Ultimi 5' del 4° quarto", lambda p, s: (p == 4) & (s >= 2100)),
}


def momenti(ev: pd.DataFrame) -> pd.DataFrame:
    """Punti fatti e subiti a partita in momenti chiave (dalla cronaca), con la posizione
    nel campionato per differenza."""
    if ev is None or ev.empty:
        return pd.DataFrame()
    pt = ev[ev["punti"] > 0]
    partite = pd.concat([ev[["partita_id", "squadra_casa_id", "campionato_id"]].rename(
        columns={"squadra_casa_id": "squadra_id"}),
        ev[["partita_id", "squadra_ospite_id", "campionato_id"]].rename(
            columns={"squadra_ospite_id": "squadra_id"})]).drop_duplicates()
    n = partite.groupby(["campionato_id", "squadra_id"])["partita_id"].nunique()
    righe = []
    for chiave, (etichetta, filtro) in MOMENTI.items():
        f = pt[filtro(pt["periodo"], pt["secondi"])]
        fatti = f.groupby(["campionato_id", "squadra_id"])["punti"].sum()
        subiti = f.groupby(["campionato_id", "avversario_id"])["punti"].sum()
        subiti.index = subiti.index.set_names(["campionato_id", "squadra_id"])
        df = pd.DataFrame({"partite": n, "fatti": fatti, "subiti": subiti}).fillna(0)
        df["fatti_pg"] = df["fatti"] / df["partite"]
        df["subiti_pg"] = df["subiti"] / df["partite"]
        df["diff_pg"] = df["fatti_pg"] - df["subiti_pg"]
        df["posizione"] = df.groupby(level="campionato_id")["diff_pg"].rank(
            ascending=False, method="min").astype(int)
        df["squadre"] = df.groupby(level="campionato_id")["diff_pg"].transform("size")
        df["momento"], df["etichetta"] = chiave, etichetta
        righe.append(df.reset_index())
    return pd.concat(righe, ignore_index=True)


# ------------------------------------------------------------------ origine dei punti concessi

def origini_concesse(origini_partita: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    """Punti concessi da palle perse, secondi tiri e contropiede, a partita."""
    if origini_partita is None or origini_partita.empty:
        return pd.DataFrame()
    avv = ev[["partita_id", "squadra_id", "avversario_id"]].dropna().drop_duplicates(
        ["partita_id", "squadra_id"])
    d = origini_partita.merge(avv, on=["partita_id", "squadra_id"])
    g = d.groupby(["campionato_id", "avversario_id"])
    out = pd.DataFrame({
        "partite": g["partita_id"].nunique(),
        "concessi_da_perse": d[d["origine"] == "palla_persa"].groupby(
            ["campionato_id", "avversario_id"])["punti"].sum(),
        "concessi_seconda_occasione": d[d["origine"] == "seconda"].groupby(
            ["campionato_id", "avversario_id"])["punti"].sum(),
        "concessi_contropiede": d[d["contropiede"]].groupby(
            ["campionato_id", "avversario_id"])["punti"].sum(),
    }).fillna(0)
    for c in ("concessi_da_perse", "concessi_seconda_occasione", "concessi_contropiede"):
        out[f"{c}_pg"] = out[c] / out["partite"]
    out.index = out.index.set_names(["campionato_id", "squadra_id"])
    return out.reset_index().drop(columns="partite")


# ------------------------------------------------------------------ riposo e trasferte

def _classe_riposo(giorni):
    if pd.isna(giorni):
        return None
    return "Ravvicinata (≤ 3 giorni)" if giorni <= 3 else (
        "Normale (4-6 giorni)" if giorni <= 6 else "Lunga (7+ giorni)")


def _classe_viaggio(km):
    if pd.isna(km):
        return None
    return "Vicina (< 250 km)" if km < 250 else (
        "Media (250-500 km)" if km <= 500 else "Lunga (> 500 km)")


def calendario_fisico(bs: pd.DataFrame, partite: pd.DataFrame) -> pd.DataFrame:
    """Per ogni partita di ogni squadra: giorni di riposo dalla partita precedente e
    chilometri di trasferta (andata, stimati su strada)."""
    if bs.empty:
        return pd.DataFrame()
    cit = luoghi.citta_partite(partite)
    d = bs[["partita_id", "squadra_id", "data", "casa"]].merge(
        cit[["partita_id", "citta", "citta_casa", "citta_ospite"]], on="partita_id", how="left")
    d["data_dt"] = pd.to_datetime(d["data"], errors="coerce")
    d = d.sort_values(["squadra_id", "data_dt"])
    d["giorni_riposo"] = d.groupby("squadra_id")["data_dt"].diff().dt.days
    d["citta_squadra"] = np.where(d["casa"] == 1, d["citta_casa"], d["citta_ospite"])
    d["km"] = [0.0 if c == 1 else luoghi.distanza_km(cs, cg)
               for c, cs, cg in zip(d["casa"], d["citta_squadra"], d["citta"])]
    d["riposo"] = d["giorni_riposo"].map(_classe_riposo)
    d["viaggio"] = [None if c == 1 else _classe_viaggio(k) for c, k in zip(d["casa"], d["km"])]
    return d.drop(columns="data_dt")


def rendimento_per(bs: pd.DataFrame, cal: pd.DataFrame, colonna: str) -> pd.DataFrame:
    """Rendimento (record, punti, Net rating) di ogni squadra per classe di riposo o viaggio."""
    if cal.empty:
        return pd.DataFrame()
    x = bs.merge(cal[["partita_id", "squadra_id", colonna]], on=["partita_id", "squadra_id"])
    x = x.dropna(subset=[colonna])
    if x.empty:
        return pd.DataFrame()
    t = A.team_summary(x, by=[colonna])
    return t


def prossima_trasferta(cal_squadra_ultima: pd.Series | None, data: str, citta_partita: str | None,
                       citta_squadra: str | None, in_casa: bool) -> dict:
    """Riposo e km per la prossima partita di una squadra."""
    out = {"giorni_riposo": None, "km": 0.0 if in_casa else luoghi.distanza_km(citta_squadra,
                                                                              citta_partita)}
    if cal_squadra_ultima is not None and data:
        try:
            out["giorni_riposo"] = (pd.Timestamp(data) - pd.Timestamp(cal_squadra_ultima)).days
        except (ValueError, TypeError):
            pass
    return out


# ------------------------------------------------------------------ presenze

def presenze(bg: pd.DataFrame, bs: pd.DataFrame) -> pd.DataFrame:
    """Presenze di ogni giocatore nella sua squadra: partite della squadra dalla prima
    all'ultima volta in cui è a referto, partite saltate (non a referto), partite a referto
    senza entrare."""
    if bg.empty:
        return pd.DataFrame()
    giornate = bs[["squadra_id", "partita_id", "data"]].drop_duplicates()
    giornate = giornate.assign(data_dt=pd.to_datetime(giornate["data"], errors="coerce"))
    ref = bg[["squadra_id", "giocatore_id", "partita_id", "minuti"]].merge(
        giornate[["partita_id", "squadra_id", "data_dt"]], on=["partita_id", "squadra_id"])
    span = ref.groupby(["squadra_id", "giocatore_id"]).agg(
        prima=("data_dt", "min"), ultima=("data_dt", "max"),
        a_referto=("partita_id", "nunique"),
        giocate=("minuti", lambda s: int((s > 0).sum()))).reset_index()
    per_sq = {s: g["data_dt"].sort_values().to_numpy() for s, g in giornate.groupby("squadra_id")}
    ultima_sq = giornate.groupby("squadra_id")["data_dt"].max()
    periodo, dopo = [], []
    for r in span.itertuples():
        date = per_sq.get(r.squadra_id, np.array([]))
        periodo.append(int(((date >= r.prima) & (date <= r.ultima)).sum()))
        dopo.append(int((date > r.ultima).sum()))
    span["partite_periodo"] = periodo
    span["saltate"] = span["partite_periodo"] - span["a_referto"]
    span["senza_entrare"] = span["a_referto"] - span["giocate"]
    span["assente_ultime"] = dopo        # partite consecutive non a referto, fino all'ultima
    span["presenze_pct"] = 100 * span["a_referto"] / span["partite_periodo"]
    span["ultima_squadra"] = span["squadra_id"].map(ultima_sq)
    return span.drop(columns=["prima", "ultima", "ultima_squadra"])


# ------------------------------------------------------------------ dalla B all'A2

STAT_CATEGORIA = {
    "punti_p40": ("Punti per 40'", "ratio"), "rimb_tot_p40": ("Rimbalzi per 40'", "ratio"),
    "assist_p40": ("Assist per 40'", "ratio"), "game_score_p40": ("Game Score per 40'", "ratio"),
    "ts_pct": ("TS%", "diff"), "usg_pct": ("Usage %", "diff"),
}
MIN_COPPIE = 12


def _migliore_linea(lines: pd.DataFrame) -> pd.DataFrame:
    return lines.sort_values("minuti").groupby(["giocatore_id", "stagione", "categoria"]).tail(1)


def coppie_categoria(lines: pd.DataFrame, min_minuti: float = 12, min_partite: int = 3
                     ) -> pd.DataFrame:
    """Giocatori che hanno giocato sia in B Nazionale sia in A2 (nella stessa stagione o in
    due stagioni consecutive): una riga per coppia di linee B / A2."""
    ok = lines[(lines["minuti_pg"] >= min_minuti) & (lines["partite"] >= min_partite)]
    ok = _migliore_linea(ok)
    stagioni = sorted(ok["stagione"].unique())
    idx = {s: i for i, s in enumerate(stagioni)}
    b = ok[ok["categoria"] == "B Nazionale"]
    a = ok[ok["categoria"] == "A2"]
    m = b.merge(a, on="giocatore_id", suffixes=("_b", "_a2"))
    if m.empty:
        return m
    gap = m["stagione_a2"].map(idx) - m["stagione_b"].map(idx)
    return m[gap.abs() <= 1]


def fattori_categoria(lines: pd.DataFrame) -> pd.DataFrame:
    """Quanto cambiano le statistiche passando dalla B Nazionale all'A2, stimato dai giocatori
    che hanno giocato in entrambe. Per i conteggi è un fattore (mediana dei rapporti), per le
    percentuali una differenza (mediana)."""
    c = coppie_categoria(lines)
    rows = []
    for col, (lab, tipo) in STAT_CATEGORIA.items():
        if c.empty or f"{col}_b" not in c:
            rows.append((col, lab, tipo, np.nan, 0))
            continue
        xb, xa = c[f"{col}_b"].astype(float), c[f"{col}_a2"].astype(float)
        ok = xb.notna() & xa.notna()
        if tipo == "ratio":
            ok &= (xb > 0) & (xa > 0)
            v = float(np.exp(np.median(np.log(xa[ok] / xb[ok])))) if ok.sum() else np.nan
        else:
            v = float(np.median(xa[ok] - xb[ok])) if ok.sum() else np.nan
        rows.append((col, lab, tipo, v, int(ok.sum())))
    return pd.DataFrame(rows, columns=["statistica", "etichetta", "tipo", "valore", "coppie"])


def proiezione_a2(lines: pd.DataFrame, fattori: pd.DataFrame) -> pd.DataFrame:
    """Statistiche attese in A2 per i giocatori di B Nazionale (colonne *_a2)."""
    out = lines.copy()
    for f in fattori.itertuples():
        if pd.isna(f.valore) or f.statistica not in out:
            continue
        out[f"{f.statistica}_a2"] = out[f.statistica] * f.valore if f.tipo == "ratio" \
            else out[f.statistica] + f.valore
    return out


# ------------------------------------------------------------------ frasi di sintesi

# metrica -> (descrizione se alta, descrizione se bassa, True se alto è meglio)
FRASI_SQUADRA = {
    "ortg": ("attacco tra i più efficienti", "attacco poco efficiente", True),
    "drtg": ("difesa che concede molto", "difesa tra le più solide", False),
    "pace": ("gioca a ritmo alto", "gioca a ritmo basso, a metà campo", None),
    "quota_punti_3": ("si affida molto al tiro da 3", "tira poco da 3", None),
    "t3_pct": ("tira bene da 3", "tira male da 3", True),
    "orb_pct": ("domina il rimbalzo offensivo", "va poco a rimbalzo offensivo", True),
    "drb_pct": ("protegge bene il rimbalzo difensivo", "concede molti rimbalzi offensivi", True),
    "tov_pct": ("perde molti palloni", "perde pochi palloni", False),
    "opp_tov_pct": ("forza molte palle perse", "forza poche palle perse", True),
    "ft_rate": ("va spesso in lunetta", "va poco in lunetta", True),
    "quota_punti_panchina": ("ha una panchina che segna molto", "dipende dai titolari", None),
    "quota_top2": ("dipende dai due migliori realizzatori", "ha punti ben distribuiti", None),
    "punti_contropiede_pg": ("segna molto in contropiede", "segna poco in contropiede", None),
    "diff_q4": ("chiude forte nell'ultimo quarto", "cala nell'ultimo quarto", True),
}


def _estremi(valori: pd.Series, chi, n_estremi: float = 0.2):
    """Percentile (0-100) del valore di `chi` nella serie."""
    v = valori.dropna()
    if chi not in v.index or len(v) < 5:
        return None
    return 100 * (v.rank(pct=True, method="average")[chi])


def frase_squadra(profile: pd.DataFrame, squadra_id, max_voci: int = 4) -> list[str]:
    """Le caratteristiche più marcate di una squadra rispetto al campionato, in parole."""
    p = profile.set_index("squadra_id")
    voci = []
    for col, (alta, bassa, _) in FRASI_SQUADRA.items():
        if col not in p:
            continue
        pct = _estremi(p[col], squadra_id)
        if pct is None:
            continue
        if pct >= 80:
            voci.append((pct, alta))
        elif pct <= 20:
            voci.append((100 - pct, bassa))
    voci.sort(reverse=True)
    return [t for _, t in voci[:max_voci]]


FRASI_GIOCATORE = {
    "punti_p40": ("realizzatore di alto volume", "segna poco", True),
    "t3_pct": ("tira molto bene da 3", "tira male da 3", True),
    "ts_pct": ("molto efficiente al tiro", "poco efficiente al tiro", True),
    "t3a_rate": ("tiratore da 3 per scelta", "attacca poco dall'arco", None),
    "ast_pct": ("crea molto per i compagni", "crea poco per i compagni", True),
    "trb_pct": ("presenza forte a rimbalzo", "va poco a rimbalzo", True),
    "stl_pct": ("ruba molti palloni", None, True),
    "blk_pct": ("protegge il ferro", None, True),
    "tov_pct": ("perde molti palloni", "perde pochi palloni", False),
    "ft_rate": ("cerca il contatto e va in lunetta", None, True),
    "usg_pct": ("accentra molti possessi", "tocca pochi possessi", None),
}


def frase_giocatore(players: pd.DataFrame, giocatore_id, squadra_id, max_voci: int = 4,
                    min_minuti: float = 10) -> list[str]:
    """Le caratteristiche più marcate di un giocatore rispetto al campionato, in parole."""
    q = players[players["minuti_pg"] >= min_minuti].set_index(["giocatore_id", "squadra_id"])
    chi = (giocatore_id, squadra_id)
    if chi not in q.index:
        return []
    voci = []
    for col, (alta, bassa, _) in FRASI_GIOCATORE.items():
        if col not in q:
            continue
        if col == "t3_pct" and q.loc[chi, "t3a_pg"] < 2:
            continue                      # percentuale da 3 solo con un volume minimo
        pct = _estremi(q[col], chi)
        if pct is None:
            continue
        if pct >= 50 and alta:
            voci.append((pct, alta))
        elif pct < 50 and bassa:
            voci.append((100 - pct, bassa))
    voci.sort(reverse=True)
    # le voci più marcate (oltre l'80° percentile); almeno due se ce ne sono oltre il 70°
    forti = [t for v, t in voci if v >= 80]
    if len(forti) < 2:
        forti = [t for v, t in voci if v >= 70][:2]
    return forti[:max_voci]


def posizione(serie: pd.Series, chi, piu_alto_meglio: bool = True) -> tuple[int, int] | None:
    """Posizione (1 = migliore) e numero di elementi confrontati."""
    v = serie.dropna()
    if chi not in v.index:
        return None
    r = v.rank(ascending=not piu_alto_meglio, method="min")[chi]
    return int(r), len(v)
