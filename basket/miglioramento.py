"""Aree da migliorare della propria squadra: dove lavorare in allenamento e quanto vale.

- priorita(): i Four Factors in attacco e in difesa confrontati con il campionato, con il
  guadagno (punti per 100 possessi e vittorie su 30 partite) se si raggiunge la media o il
  livello delle migliori;
- punti_regalati(): punti concessi da palle perse, seconde occasioni e contropiede, punti
  lasciati ai liberi, rispetto al campionato;
- momenti_critici(): i momenti della partita in cui la squadra perde terreno;
- quintetti_estremi(): i quintetti migliori e peggiori, con la soglia di minuti adatta;
- dettagli_giocatori(): abitudini individuali che costano punti (liberi, palle perse, scelta
  di tiro, tiro da 3, falli), con la stima dei punti a partita in gioco.
"""

import numpy as np
import pandas as pd

from . import chiavi as C
from . import previsioni as F

PARTITE_STAGIONE = 30

# voce: (nome, colonna, più alto è meglio, peso sul Net rating per unità, scala)
VOCI = [
    ("Tiro dal campo (triple pesate)", "efg_pct", True, C.PESI["efg"], "In attacco"),
    ("Palle perse", "tov_pct", False, -C.PESI["tov"], "In attacco"),
    ("Rimbalzi offensivi", "orb_pct", True, C.PESI["orb"], "In attacco"),
    ("Liberi segnati", "ft_rate", True, C.PESI["ftr"], "In attacco"),
    ("Tiro concesso agli avversari", "opp_efg_pct", False, C.PESI["efg"], "In difesa"),
    ("Palle perse forzate", "opp_tov_pct", True, -C.PESI["tov"], "In difesa"),
    ("Rimbalzi difensivi", "drb_pct", True, C.PESI["orb"], "In difesa"),
    ("Tiri liberi concessi", "opp_ft_rate", False, C.PESI["ftr"], "In difesa"),
]


def _vittorie(net: float, d_net: float, poss: float) -> float:
    """Vittorie in più su una stagione contro un avversario medio, a campo neutro."""
    p0 = F._phi(net * poss / 100 / F.SIGMA)
    p1 = F._phi((net + d_net) * poss / 100 / F.SIGMA)
    return PARTITE_STAGIONE * (p1 - p0)


# voci espresse anche come numero a partita: (unità, base su cui si calcola la percentuale)
UNITA = {"tov_pct": "palle perse", "opp_tov_pct": "palle perse forzate",
         "orb_pct": "rimbalzi offensivi", "drb_pct": "rimbalzi difensivi",
         "ft_rate": "liberi segnati", "opp_ft_rate": "liberi concessi"}


def _base(me, col: str) -> float:
    """Eventi a partita su cui si calcola la voce (azioni per le palle perse, rimbalzi
    disponibili per i rimbalzi, tiri dal campo per i liberi)."""
    g = max(1.0, float(me.get("partite", 1) or 1))
    serve = {"tov_pct": ["pace", "rimb_off"], "opp_tov_pct": ["pace", "opp_rimb_off"],
             "orb_pct": ["rimb_off", "orb_pct"],
             "ft_rate": ["fga"], "drb_pct": ["rimb_dif", "drb_pct"],
             "opp_ft_rate": ["opp_t2a", "opp_t3a"]}.get(col)
    if not serve or any(pd.isna(me.get(c, np.nan)) for c in serve):
        return np.nan
    # palle perse % = perse / azioni, con azioni = tiri + 0,44 liberi + perse = possessi +
    # rimbalzi offensivi (i possessi vengono dalle sole partite con box score completo)
    if col == "tov_pct":
        return float(me["pace"]) + float(me["rimb_off"]) / g
    if col == "opp_tov_pct":
        return float(me["pace"]) + float(me["opp_rimb_off"]) / g
    # rimbalzi: la base è quella che restituisce i rimbalzi reali a partita
    if col == "orb_pct":
        return float(me["rimb_off"]) / g / (float(me["orb_pct"]) / 100) if me["orb_pct"] else np.nan
    if col == "drb_pct":
        return float(me["rimb_dif"]) / g / (float(me["drb_pct"]) / 100) if me["drb_pct"] else np.nan
    if col == "ft_rate":
        return float(me["fga"]) / g
    if col == "opp_ft_rate":
        return (float(me["opp_t2a"]) + float(me["opp_t3a"])) / g
    return np.nan


def a_partita(col: str, valore: float, base: float) -> float:
    if col not in UNITA or pd.isna(base):
        return np.nan
    return valore * base if col in ("ft_rate", "opp_ft_rate") else valore / 100 * base


def leggibile(r, quale: str) -> str:
    """Valore di una voce per tabelle e frasi: numero a partita (palle perse, rimbalzi,
    liberi); il tiro resta in percentuale."""
    v = r[quale]
    pct = f"{v:.2f}" if "ft" in r["colonna"] else f"{v:.1f}%"
    n = r.get(f"{quale}_n", np.nan)
    if r["colonna"] not in UNITA or pd.isna(n):
        return pct.replace(".", ",")
    if "ft" in r["colonna"]:
        return f"{n:.1f}".replace(".", ",")
    return f"{n:.1f}".replace(".", ",")


def priorita(profile: pd.DataFrame, sid: int) -> pd.DataFrame:
    """Una riga per voce: valore, media e livello delle migliori (quartile), posizione,
    obiettivo (la media se si è sotto, altrimenti il livello delle migliori) e quanto vale
    raggiungerlo."""
    pr = profile.set_index("squadra_id")
    me = pr.loc[sid]
    poss = float(me.get("pace", 72) or 72)
    net = float(me.get("net_rtg", 0) or 0)
    righe = []
    for nome, col, alto, peso, lato in VOCI:
        v, s = float(me[col]), pr[col].astype(float)
        media = float(s.mean())
        migliori = float(s.quantile(0.75 if alto else 0.25))
        sotto = (v < media) if alto else (v > media)
        obiettivo = media if sotto else migliori
        passo = max(0.0, (obiettivo - v) if alto else (v - obiettivo))
        d_net = abs(peso) * passo
        pos = int(s.rank(ascending=not alto, method="min")[sid])
        base = _base(me, col)
        righe.append({"valore_n": a_partita(col, v, base), "media_n": a_partita(col, media, base),
                      "migliori_n": a_partita(col, migliori, base),
                      "obiettivo_n": a_partita(col, obiettivo, base), "unita": UNITA.get(col, ""),
                      "voce": nome, "colonna": col, "lato": lato, "valore": v, "media": media,
                      "migliori": migliori, "posizione": pos, "squadre": len(s),
                      "sotto_media": sotto, "obiettivo": obiettivo, "guadagno_net": d_net,
                      "vittorie": _vittorie(net, d_net, poss)})
    out = pd.DataFrame(righe)
    out["ordine"] = out["sotto_media"].astype(int) * 1000 + out["guadagno_net"]
    return out.sort_values("ordine", ascending=False).drop(columns="ordine").reset_index(drop=True)


def punti_regalati(profile: pd.DataFrame, concessi: pd.DataFrame, sid: int) -> pd.DataFrame:
    """Punti concessi o lasciati per strada a partita, confrontati con il campionato."""
    pr = profile.set_index("squadra_id")
    g = pr["partite"].replace(0, np.nan)
    voci = {}
    if concessi is not None and not concessi.empty:
        cc = concessi.set_index("squadra_id")
        for col, nome in (("concessi_da_perse_pg", "Punti concessi dalle vostre palle perse"),
                          ("concessi_seconda_occasione_pg", "Punti concessi su seconde occasioni"),
                          ("concessi_contropiede_pg", "Punti concessi in contropiede")):
            if col in cc:
                voci[nome] = (cc[col].reindex(pr.index), False)
    voci["Tiri liberi sbagliati a partita"] = ((pr["tla"] - pr["tlm"]) / g, False)
    voci["Palle perse a partita"] = (pr["perse"] / g, False)
    voci["Falli commessi a partita"] = (pr["falli_commessi"] / g, False)
    righe = []
    for nome, (s, alto) in voci.items():
        s = s.astype(float)
        if pd.isna(s.get(sid)):
            continue
        v, media = float(s[sid]), float(s.mean())
        righe.append({"voce": nome, "valore": v, "media": media, "differenza": v - media,
                      "posizione": int(s.rank(ascending=not alto, method="min")[sid]),
                      "squadre": int(s.notna().sum())})
    out = pd.DataFrame(righe)
    if out.empty:
        return out
    return out.sort_values("differenza", ascending=False).reset_index(drop=True)


def momenti_critici(momenti: pd.DataFrame, sid: int) -> pd.DataFrame:
    if momenti is None or momenti.empty:
        return pd.DataFrame()
    m = momenti[momenti["squadra_id"] == sid]
    return m.sort_values("diff_pg").reset_index(drop=True)


# minuti "virtuali" a Net rating zero: il rating di un quintetto con pochi minuti insieme viene
# avvicinato allo zero, così 6 minuti fortunati non battono 60 minuti solidi
MINUTI_PRUDENZA = 30.0


def soglia_quintetti(lineups: pd.DataFrame, sid: int) -> float:
    """Minuti minimi insieme per considerare un quintetto: il 2% dei minuti della squadra
    con quintetti verificati, tra 5 (inizio stagione) e 25."""
    q = lineups[lineups["squadra_id"] == sid]
    return float(np.clip(round(0.02 * q["minuti"].sum()), 5, 25)) if not q.empty else 5.0


def quintetti_estremi(lineups: pd.DataFrame, sid: int, n: int = 3,
                      minuti_min: float | None = None
                      ) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """(migliori, peggiori, soglia): quintetti con almeno `soglia` minuti insieme, ordinati per
    Net rating prudente (net_stimato = net_rtg · minuti / (minuti + MINUTI_PRUDENZA))."""
    if lineups is None or lineups.empty:
        return pd.DataFrame(), pd.DataFrame(), 5.0
    soglia = soglia_quintetti(lineups, sid) if minuti_min is None else minuti_min
    q = lineups[(lineups["squadra_id"] == sid) & (lineups["minuti"] >= soglia)].copy()
    q = q[q["net_rtg"].notna()]
    q["net_stimato"] = q["net_rtg"] * q["minuti"] / (q["minuti"] + MINUTI_PRUDENZA)
    migliori = q[q["net_stimato"] > 0].sort_values("net_stimato", ascending=False).head(n)
    peggiori = q[(q["net_stimato"] < 0) & ~q.index.isin(migliori.index)].sort_values(
        "net_stimato").head(n)
    return migliori.reset_index(drop=True), peggiori.reset_index(drop=True), soglia


def dettagli_giocatori(players: pd.DataFrame, sid: int, minuti_min: float = 10.0
                       ) -> pd.DataFrame:
    """Abitudini individuali che costano punti, con la stima dei punti a partita in gioco
    rispetto alla media del campionato."""
    lega = players[players["minuti_pg"] >= minuti_min]
    p = lega[lega["squadra_id"] == sid]
    if p.empty:
        return pd.DataFrame()
    tl = lega["tlm"].sum() / max(1, lega["tla"].sum())
    t3 = lega["t3m"].sum() / max(1, lega["t3a"].sum())
    tov75 = lega["tov_pct"].quantile(0.75) if "tov_pct" in lega else np.nan
    ts_med = lega["ts_pct"].median() if "ts_pct" in lega else np.nan
    righe = []
    for r in p.itertuples():
        def add(area, testo, punti):
            righe.append({"giocatore_id": r.giocatore_id, "giocatore": r.giocatore,
                          "area": area, "dettaglio": testo, "punti_pg": punti,
                          "minuti_pg": r.minuti_pg})
        if r.tla_pg >= 2 and r.tl_pct < 100 * tl - 8:
            add("Tiri liberi", f"{r.tl_pct:.0f}% su {r.tla_pg:.1f} tentativi a partita "
                f"(media del campionato {100 * tl:.0f}%)", (tl - r.tl_pct / 100) * r.tla_pg)
        if r.t3a_pg >= 3 and r.t3_pct < 100 * t3 - 5:
            add("Tiro da 3", f"{r.t3_pct:.0f}% su {r.t3a_pg:.1f} tentativi a partita "
                f"(media {100 * t3:.0f}%)", 3 * (t3 - r.t3_pct / 100) * r.t3a_pg)
        usg = getattr(r, "usg_pct", np.nan)
        tov = getattr(r, "tov_pct", np.nan)
        if pd.notna(tov) and pd.notna(tov75) and tov > tov75 and r.perse_pg >= 1.5:
            add("Palle perse", f"{r.perse_pg:.1f} a partita: perde 1 pallone ogni {100 / tov:.1f} azioni", (tov - lega["tov_pct"].median()) / 100 *
                (r.fga_pg + 0.44 * r.tla_pg + r.perse_pg) * 1.05)
        ts = getattr(r, "ts_pct", np.nan)
        if pd.notna(ts) and pd.notna(usg) and usg >= 22 and ts < ts_med - 4:
            tiri = r.fga_pg + 0.44 * r.tla_pg
            add("Scelta di tiro", f"conclude molte azioni ({tiri + r.perse_pg:.1f} a partita) con "
                f"{2 * ts / 100:.2f} punti per tiro (normale {2 * ts_med / 100:.2f})", 2 * (ts_med - ts) / 100 * tiri)
        if r.falli_commessi_p40 >= 5.5 and r.minuti_pg >= 15:
            add("Falli", f"{r.falli_commessi_p40:.1f} falli ogni 40 minuti: rischia di uscire "
                "presto o di mandare in bonus gli avversari", np.nan)
    out = pd.DataFrame(righe)
    if out.empty:
        return out
    return out.sort_values("punti_pg", ascending=False, na_position="last").reset_index(drop=True)


def tutte_insieme(pri: pd.DataFrame, net: float, poss: float) -> dict:
    """Vittorie in più raggiungendo insieme tutti gli obiettivi delle voci sotto la media
    (gli effetti dei Four Factors sul Net rating si sommano)."""
    s = pri[pri["sotto_media"]]
    d_net = float(s["guadagno_net"].sum())
    return {"voci": len(s), "guadagno_net": d_net, "vittorie": _vittorie(net, d_net, poss)}


def sintesi(pri: pd.DataFrame, regalati: pd.DataFrame, dett: pd.DataFrame, n: int = 3
            ) -> list[str]:
    """Le aree principali in parole."""
    out = []
    for _, r in pri[pri["sotto_media"]].head(2).iterrows():
        if r["unita"] and pd.notna(r["valore_n"]):
            out.append(f"{r['voce'].replace(' %', '')} ({r['lato'].lower()}): "
                       f"{r['valore_n']:.1f} {r['unita']} a partita, {r['posizione']}° su "
                       f"{r['squadre']}; arrivare alla media ({r['media_n']:.1f} a partita) vale "
                       f"circa {r['vittorie']:+.1f} vittorie su {PARTITE_STAGIONE} partite")
        else:
            d = 2 if "ft" in r["colonna"] else 1
            out.append(f"{r['voce']} ({r['lato'].lower()}): {r['valore']:.{d}f}, "
                       f"{r['posizione']}° su {r['squadre']}; arrivare alla media "
                       f"({r['media']:.{d}f}) vale circa {r['vittorie']:+.1f} vittorie su "
                       f"{PARTITE_STAGIONE} partite")
    if not regalati.empty and regalati["differenza"].iloc[0] > 0.5:
        r = regalati.iloc[0]
        out.append(f"{r['voce']}: {r['valore']:.1f} a partita contro {r['media']:.1f} di media")
    if not dett.empty and pd.notna(dett["punti_pg"].iloc[0]):
        r = dett.iloc[0]
        out.append(f"{r['giocatore']} – {r['area'].lower()}: {r['dettaglio']}")
    return out[: n + 1]
