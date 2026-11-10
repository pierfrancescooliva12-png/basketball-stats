"""Statistiche avanzate del giocatore, raccolte in cinque famiglie e rese leggibili per lo staff.

Per ogni voce: il valore, la posizione rispetto ai giocatori dello stesso campionato con minuti
sufficienti (percentuale di giocatori che fanno peggio) e una lettura in parole. Sono le voci
delle schede "advanced" (rating con il giocatore in campo, passaggi, rimbalzi, tiro e palle
perse, utilizzo e impatto), calcolate dai tabellini e dalla cronaca della Lega.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import analysis as A

MIN_PARTITE, MIN_MINUTI_PG = 3, 10.0      # per entrare nel confronto con il campionato


@dataclass(frozen=True)
class Voce:
    chiave: str
    sigla: str
    nome: str
    dec: int
    suffisso: str
    verso: int            # 1: più alto è meglio · -1: più basso è meglio · 0: descrive, non giudica
    cosa: str             # che cosa misura, in una riga
    alto: str             # lettura quando è tra i valori più alti del campionato
    basso: str            # lettura quando è tra i più bassi


GRUPPI: list[tuple[str, str, list[Voce]]] = [
    ("Squadra con lui in campo", "punti ogni 100 possessi mentre è in campo (dalla cronaca)", [
        Voce("ortg_on", "OFFRTG", "Attacco con lui in campo", 1, "", 1,
             "Punti segnati dalla squadra ogni 100 possessi quando è in campo",
             "con lui in campo la squadra segna molto", "con lui in campo la squadra segna poco"),
        Voce("drtg_on", "DEFRTG", "Difesa con lui in campo", 1, "", -1,
             "Punti subiti dalla squadra ogni 100 possessi quando è in campo",
             "con lui in campo la squadra subisce poco", "con lui in campo la squadra subisce molto"),
        Voce("net_on", "NETRTG", "Saldo con lui in campo", 1, "", 1,
             "Attacco meno difesa: il margine della squadra ogni 100 possessi con lui in campo",
             "con lui in campo la squadra è nettamente avanti", "con lui in campo la squadra va sotto"),
    ]),
    ("Passaggi e gestione", "quanto crea per i compagni e quanto costa in palle perse", [
        Voce("ast_pct", "AST%", "Canestri dei compagni assistiti", 1, "%", 1,
             "Quota dei canestri dei compagni che nascono da un suo assist, mentre è in campo",
             "crea molto per i compagni", "crea poco per i compagni"),
        Voce("ast_to", "AST/TO", "Assist per palla persa", 2, "", 1,
             "Assist forniti per ogni palla persa",
             "gestisce la palla con sicurezza", "perde più palloni di quanti ne crea"),
        Voce("ast_ratio", "AST RATIO", "Assist ogni 100 azioni", 1, "", 1,
             "Assist ogni 100 azioni che chiude (tiri, liberi, assist, palle perse)",
             "quando ha la palla spesso la passa per un canestro", "quando ha la palla raramente assiste"),
    ]),
    ("Rimbalzi", "quota dei rimbalzi disponibili che prende mentre è in campo", [
        Voce("orb_pct", "OREB%", "Rimbalzi d'attacco", 1, "%", 1,
             "Quota dei rimbalzi offensivi disponibili che cattura",
             "regala seconde occasioni alla squadra", "va poco a rimbalzo d'attacco"),
        Voce("drb_pct", "DREB%", "Rimbalzi difensivi", 1, "%", 1,
             "Quota dei rimbalzi difensivi disponibili che cattura",
             "chiude i possessi avversari a rimbalzo", "prende pochi rimbalzi difensivi"),
        Voce("trb_pct", "REB%", "Rimbalzi totali", 1, "%", 1,
             "Quota di tutti i rimbalzi disponibili che cattura",
             "domina a rimbalzo", "incide poco a rimbalzo"),
    ]),
    ("Tiro e palle perse", "quanto rende ogni tiro e quanti palloni spreca", [
        Voce("efg_pct", "EFG%", "Tiro dal campo effettivo", 1, "%", 1,
             "Percentuale dal campo che dà più peso ai tiri da tre",
             "tira dal campo con grande resa", "tira dal campo con poca resa"),
        Voce("ts_pct", "TS%", "Tiro reale", 1, "%", 1,
             "Resa complessiva al tiro: da due, da tre e liberi insieme",
             "ogni suo tiro rende molto", "ogni suo tiro rende poco"),
        Voce("to_ratio", "TO RATIO", "Palle perse ogni 100 azioni", 1, "", -1,
             "Palle perse ogni 100 azioni che chiude",
             "spreca pochi palloni", "spreca molti palloni"),
    ]),
    ("Utilizzo e impatto", "quanto gioco passa da lui e quanto pesa sulla partita", [
        Voce("usg_pct", "USG%", "Azioni della squadra che chiude", 1, "%", 0,
             "Quota delle azioni di squadra (tiri, liberi, palle perse) che chiude mentre è in campo",
             "l'attacco passa da lui", "tocca pochi palloni in attacco"),
        Voce("pie", "PIE", "Impatto sulla partita", 1, "%", 1,
             "Quota di tutto ciò che accade nelle sue partite (punti, rimbalzi, assist, recuperi, "
             "errori) che porta la sua firma",
             "pesa moltissimo sulle partite", "pesa poco sulle partite"),
        Voce("pace", "PACE", "Ritmo della squadra", 1, "", 0,
             "Possessi della sua squadra ogni 40 minuti",
             "gioca in una squadra che corre", "gioca in una squadra dal ritmo basso"),
    ]),
]
VOCI = [v for _, _, voci in GRUPPI for v in voci]


def _pie_num(d: pd.DataFrame, p: str = "") -> pd.Series:
    """Numeratore del PIE: tutto ciò che di utile o dannoso finisce a tabellino."""
    g = lambda c: d[f"{p}{c}"]  # noqa: E731
    return (g("punti") + g("t2m") + g("t3m") + g("tlm") - g("t2a") - g("t3a") - g("tla")
            + g("rimb_dif") + 0.5 * g("rimb_off") + g("assist") + g("recuperate")
            + 0.5 * g("stoppate") - g("falli_commessi") - g("perse"))


def pie(bg: pd.DataFrame, bs: pd.DataFrame) -> pd.DataFrame:
    """PIE per giocatore: la sua parte del totale delle partite giocate (le due squadre insieme),
    solo sulle partite con il tabellino affidabile."""
    b = bs[bs["affidabile"]]
    tot = pd.DataFrame({"partita_id": b["partita_id"], "squadra_id": b["squadra_id"],
                        "pie_partita": _pie_num(b) + _pie_num(b, "opp_")})
    g = bg[bg["giocata"] & bg["affidabile"]].merge(tot, on=["partita_id", "squadra_id"], how="inner")
    g = g.assign(pie_num=_pie_num(g))
    s = g.groupby(["squadra_id", "giocatore_id"])[["pie_num", "pie_partita"]].sum().reset_index()
    s["pie"] = 100 * s["pie_num"] / s["pie_partita"].where(s["pie_partita"] > 0)
    return s[["squadra_id", "giocatore_id", "pie"]]


def tabella(ctx) -> pd.DataFrame:
    """Una riga per giocatore e squadra con tutte le voci avanzate (una volta per contesto)."""
    if "_avanzate" in ctx.__dict__:
        return ctx.__dict__["_avanzate"]
    p = ctx.players.copy()
    oo = ctx.on_off
    if not oo.empty:
        p = p.merge(oo[["squadra_id", "giocatore_id", "ortg_on", "drtg_on"]],
                    on=["squadra_id", "giocatore_id"], how="left")
    else:
        p["ortg_on"] = p["drtg_on"] = np.nan
    for c in ("net_on",):
        if c not in p:
            p[c] = np.nan
    p = p.merge(pie(ctx.bg, ctx.bs), on=["squadra_id", "giocatore_id"], how="left")
    p["to_ratio"] = 100 * A._div(p["perse"], p["fga"] + A.FT * p["tla"] + p["assist"] + p["perse"])
    p = p.merge(ctx.profile[["squadra_id", "pace"]], on="squadra_id", how="left")
    ctx.__dict__["_avanzate"] = p
    return p


def _livello(pct: float, verso: int) -> str:
    if verso == 0:
        return "alto" if pct >= 80 else "medio-alto" if pct >= 60 else "nella media" if pct >= 40 \
            else "medio-basso" if pct >= 20 else "basso"
    return "tra i migliori" if pct >= 80 else "sopra la media" if pct >= 60 else "nella media" if pct >= 40 \
        else "sotto la media" if pct >= 20 else "tra i più deboli"


def _it(v: float, dec: int) -> str:
    return f"{v:.{dec}f}".replace(".", ",")


def scheda(ctx, sid: int, gid: str) -> dict | None:
    """Le cinque famiglie per un giocatore: valore, posizione nel campionato e lettura.

    {"gruppi": [{"titolo", "sotto", "righe": [{sigla, nome, cosa, valore, testo, pct, verso,
    livello, lettura}]}], "confronto": n. di giocatori del campionato nel confronto,
    "pochi_dati": bool, "sintesi": [frasi]}; None se il giocatore non c'è."""
    t = tabella(ctx)
    riga = t[(t["squadra_id"] == sid) & (t["giocatore_id"] == gid)]
    if riga.empty:
        return None
    me = riga.iloc[0]
    rif = t[(t["campionato_id"] == me["campionato_id"]) & (t["partite"] >= MIN_PARTITE)
            & (t["minuti_pg"] >= MIN_MINUTI_PG)]
    gruppi, forti, deboli = [], [], []
    for titolo, sotto, voci in GRUPPI:
        righe = []
        for v in voci:
            val = me.get(v.chiave)
            ok = val is not None and pd.notna(val) and np.isfinite(val)
            serie = rif[v.chiave].replace([np.inf, -np.inf], np.nan).dropna() if v.chiave in rif else pd.Series(dtype=float)
            pct = None
            if ok and len(serie) >= 8:
                sotto_di_me = (serie < val).mean() if v.verso >= 0 else (serie > val).mean()
                pct = float(100 * sotto_di_me)
            livello = _livello(pct, v.verso) if pct is not None else ""
            lettura = ""
            if pct is not None:
                if pct >= 80:
                    lettura = v.alto
                elif pct < 20:
                    lettura = v.basso
                if v.verso != 0 and pct >= 85:
                    forti.append((pct, v.alto))
                elif v.verso != 0 and pct < 15:
                    deboli.append((pct, v.basso))
            righe.append({"chiave": v.chiave, "sigla": v.sigla, "nome": v.nome, "cosa": v.cosa,
                          "valore": float(val) if ok else None,
                          "testo": (("+" if v.chiave == "net_on" and val > 0 else "") + _it(val, v.dec) + v.suffisso)
                          if ok else "–",
                          "pct": pct, "verso": v.verso, "livello": livello, "lettura": lettura})
        gruppi.append({"titolo": titolo, "sotto": sotto, "righe": righe})
    sintesi = [x for _, x in sorted(forti, reverse=True)[:3]] + [x for _, x in sorted(deboli)[:2]]
    pochi = bool(me["partite"] < MIN_PARTITE or me["minuti_pg"] < MIN_MINUTI_PG)
    return {"gruppi": gruppi, "confronto": int(len(rif)), "pochi_dati": pochi, "sintesi": sintesi,
            "forti": [x for _, x in sorted(forti, reverse=True)[:3]],
            "deboli": [x for _, x in sorted(deboli)[:2]]}


def tabella_squadra(ctx, sid: int, n: int = 10) -> pd.DataFrame:
    """Per il report di squadra: i giocatori più utilizzati con le voci avanzate principali."""
    t = tabella(ctx)
    t = t[(t["squadra_id"] == sid) & (t["partite"] >= 1)].sort_values("minuti", ascending=False).head(n)
    return t[["giocatore_id", "giocatore", "minuti_pg", "net_on", "usg_pct", "ts_pct", "efg_pct", "ast_pct",
              "to_ratio", "trb_pct", "pie"]].reset_index(drop=True)
