"""Aree da migliorare della propria squadra: dove lavorare in allenamento e quanto vale.

- priorita(): i Four Factors in attacco e in difesa confrontati con il campionato, con il
  guadagno (punti per 100 possessi e vittorie su 30 partite) se si raggiunge la media o il
  livello delle migliori;
- punti_regalati(): punti concessi da palle perse, seconde occasioni e contropiede, punti
  lasciati ai liberi, rispetto al campionato;
- momenti_critici(): i momenti della partita in cui la squadra perde terreno;
- quintetti_da_rivedere(): quintetti molto usati con saldo negativo, e i migliori;
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
    ("Tiro (eFG%)", "efg_pct", True, C.PESI["efg"], "In attacco"),
    ("Palle perse %", "tov_pct", False, -C.PESI["tov"], "In attacco"),
    ("Rimbalzi offensivi %", "orb_pct", True, C.PESI["orb"], "In attacco"),
    ("Tiri liberi (segnati per tiro)", "ft_rate", True, C.PESI["ftr"], "In attacco"),
    ("Tiro concesso (eFG%)", "opp_efg_pct", False, C.PESI["efg"], "In difesa"),
    ("Palle perse forzate %", "opp_tov_pct", True, -C.PESI["tov"], "In difesa"),
    ("Rimbalzi difensivi %", "drb_pct", True, C.PESI["orb"], "In difesa"),
    ("Tiri liberi concessi", "opp_ft_rate", False, C.PESI["ftr"], "In difesa"),
]


def _vittorie(net: float, d_net: float, poss: float) -> float:
    """Vittorie in più su una stagione contro un avversario medio, a campo neutro."""
    p0 = F._phi(net * poss / 100 / F.SIGMA)
    p1 = F._phi((net + d_net) * poss / 100 / F.SIGMA)
    return PARTITE_STAGIONE * (p1 - p0)


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
        righe.append({"voce": nome, "colonna": col, "lato": lato, "valore": v, "media": media,
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


def quintetti_da_rivedere(lineups: pd.DataFrame, sid: int, minuti_min: float = 20.0
                          ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(peggiori, migliori) tra i quintetti con almeno minuti_min minuti insieme."""
    if lineups is None or lineups.empty:
        return pd.DataFrame(), pd.DataFrame()
    q = lineups[(lineups["squadra_id"] == sid) & (lineups["minuti"] >= minuti_min)]
    peggiori = q[q["net_rtg"] < 0].sort_values("plus_minus").head(3)
    migliori = q[q["net_rtg"] > 0].sort_values("plus_minus", ascending=False).head(3)
    return peggiori.reset_index(drop=True), migliori.reset_index(drop=True)


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
            add("Palle perse", f"{tov:.0f}% dei possessi usati finisce in palla persa "
                f"({r.perse_pg:.1f} a partita)", (tov - lega["tov_pct"].median()) / 100 *
                (r.fga_pg + 0.44 * r.tla_pg + r.perse_pg) * 1.05)
        ts = getattr(r, "ts_pct", np.nan)
        if pd.notna(ts) and pd.notna(usg) and usg >= 22 and ts < ts_med - 4:
            tiri = r.fga_pg + 0.44 * r.tla_pg
            add("Scelta di tiro", f"usa il {usg:.0f}% dei possessi con il {ts:.0f}% di tiro "
                f"reale (mediana {ts_med:.0f}%)", 2 * (ts_med - ts) / 100 * tiri)
        if r.falli_commessi_p40 >= 5.5 and r.minuti_pg >= 15:
            add("Falli", f"{r.falli_commessi_p40:.1f} falli ogni 40 minuti: rischia di uscire "
                "presto o di mandare in bonus gli avversari", np.nan)
    out = pd.DataFrame(righe)
    if out.empty:
        return out
    return out.sort_values("punti_pg", ascending=False, na_position="last").reset_index(drop=True)


def sintesi(pri: pd.DataFrame, regalati: pd.DataFrame, dett: pd.DataFrame, n: int = 3
            ) -> list[str]:
    """Le aree principali in parole."""
    out = []
    for r in pri[pri["sotto_media"]].head(2).itertuples():
        d = 2 if "ft" in r.colonna else 1
        out.append(f"{r.voce} ({r.lato.lower()}): {r.valore:.{d}f}, {r.posizione}° su "
                   f"{r.squadre}; arrivare alla media ({r.media:.{d}f}) vale circa "
                   f"{r.vittorie:+.1f} vittorie su {PARTITE_STAGIONE} partite")
    if not regalati.empty and regalati["differenza"].iloc[0] > 0.5:
        r = regalati.iloc[0]
        out.append(f"{r['voce']}: {r['valore']:.1f} a partita contro {r['media']:.1f} di media")
    if not dett.empty and pd.notna(dett["punti_pg"].iloc[0]):
        r = dett.iloc[0]
        out.append(f"{r['giocatore']} – {r['area'].lower()}: {r['dettaglio']}")
    return out[: n + 1]
