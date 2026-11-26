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


# ------------------------------------------------------------------ con lui e senza di lui
# Le voci di squadra dipendono dalla forza della squadra: in una squadra di testa sono alte per tutti,
# in una di coda basse per tutti. Il confronto più giusto è con la sua stessa squadra quando lui è
# in panchina: stesse metriche, con lui in campo e senza di lui (dalla cronaca e dai quintetti).

@dataclass(frozen=True)
class VoceOnOff:
    chiave: str
    sigla: str
    nome: str
    dec: int
    suffisso: str
    verso: int            # 1: più alto è meglio per la squadra · -1: più basso è meglio


VOCI_ONOFF = [
    VoceOnOff("ortg", "OFFRTG", "Punti segnati ogni 100 possessi", 1, "", 1),
    VoceOnOff("drtg", "DEFRTG", "Punti subiti ogni 100 possessi", 1, "", -1),
    VoceOnOff("net", "NETRTG", "Saldo ogni 100 possessi", 1, "", 1),
    VoceOnOff("efg", "EFG%", "Tiro effettivo della squadra", 1, "%", 1),
    VoceOnOff("opp_efg", "EFG% AVV.", "Tiro effettivo concesso agli avversari", 1, "%", -1),
    VoceOnOff("tov", "TOV%", "Palle perse della squadra ogni 100 azioni", 1, "%", -1),
    VoceOnOff("orb", "OREB%", "Rimbalzi d'attacco della squadra", 1, "%", 1),
    VoceOnOff("drb", "DREB%", "Rimbalzi difensivi della squadra", 1, "%", 1),
]
MIN_POSS_OFF = 40          # possessi senza di lui per un confronto affidabile
_CONTA = {"fga": ("tiro2_fatto", "tiro2_sbagliato", "tiro3_fatto", "tiro3_sbagliato"),
          "fgm": ("tiro2_fatto", "tiro3_fatto"), "fg3m": ("tiro3_fatto",),
          "fta": ("tl_fatto", "tl_sbagliato"), "tov": ("persa",), "orb": ("rimb_off",), "drb": ("rimb_dif",)}


def _fattori(d: pd.DataFrame, p: str = "") -> pd.DataFrame:
    """Le voci di squadra da somme di punti, possessi ed eventi (p: "" per il totale, "o_" ecc.)."""
    g = lambda c: d[f"{p}{c}"]  # noqa: E731
    out = pd.DataFrame(index=d.index)
    out["ortg"] = 100 * A._div(g("pf"), g("poss_f"))
    out["drtg"] = 100 * A._div(g("ps"), g("poss_s"))
    out["net"] = 100 * A._div(g("pf") - g("ps"), (g("poss_f") + g("poss_s")) / 2)   # come NETRTG
    out["efg"] = 100 * A._div(g("f_fgm") + 0.5 * g("f_fg3m"), g("f_fga"))
    out["opp_efg"] = 100 * A._div(g("s_fgm") + 0.5 * g("s_fg3m"), g("s_fga"))
    out["tov"] = 100 * A._div(g("f_tov"), g("f_fga") + A.FT * g("f_fta") + g("f_tov"))
    out["orb"] = 100 * A._div(g("f_orb"), g("f_orb") + g("s_drb"))
    out["drb"] = 100 * A._div(g("f_drb"), g("f_drb") + g("s_orb"))
    return out


def stint_eventi(ev: pd.DataFrame, stints: pd.DataFrame) -> pd.DataFrame:
    """Gli stint con i conteggi delle azioni della squadra (f_) e degli avversari (s_) mentre
    quel quintetto era in campo. Un'azione va nello stint in corso al suo istante di gioco."""
    st = stints.reset_index(drop=True).copy()
    st["_stint"] = np.arange(len(st))
    cols = [f"{l}_{k}" for l in ("f", "s") for k in _CONTA]
    if ev.empty or st.empty:
        for c in cols:
            st[c] = 0.0
        return st
    tipi = {t for v in _CONTA.values() for t in v}
    e = ev[ev["tipo"].isin(tipi) & ev["squadra_id"].notna()][
        ["partita_id", "secondi", "squadra_id", "tipo", "squadra_casa_id", "squadra_ospite_id"]].copy()
    e["squadra_id"] = e["squadra_id"].astype(int)
    e["avversario"] = np.where(e["squadra_id"] == e["squadra_casa_id"], e["squadra_ospite_id"],
                               e["squadra_casa_id"]).astype(int)
    e["secondi"] = e["secondi"].astype(float)
    chiavi = st[["partita_id", "squadra_id", "inizio", "_stint"]].copy()
    chiavi["inizio"] = chiavi["inizio"].astype(float)
    chiavi = chiavi.sort_values("inizio")
    pezzi = []
    for lato, chi in (("f", "squadra_id"), ("s", "avversario")):
        x = e.rename(columns={"squadra_id": "_attore"}).assign(squadra_id=e[chi].values)
        x = x.sort_values("secondi")
        m = pd.merge_asof(x, chiavi, left_on="secondi", right_on="inizio", by=["partita_id", "squadra_id"],
                          direction="backward")
        m = m[m["_stint"].notna()]
        for k, tipi_k in _CONTA.items():
            m[f"{lato}_{k}"] = m["tipo"].isin(tipi_k).astype(float)
        pezzi.append(m.groupby("_stint")[[f"{lato}_{k}" for k in _CONTA]].sum())
    conti = pd.concat(pezzi, axis=1).reindex(st["_stint"]).fillna(0.0)
    conti.index = st.index
    return pd.concat([st, conti[cols]], axis=1)


def on_off_squadra(ctx) -> pd.DataFrame:
    """Per giocatore e squadra: le VOCI_ONOFF con lui in campo (_on) e senza di lui (_off), con i
    possessi giocati con e senza. Calcolata una volta per contesto."""
    if "_onoff_squadra" in ctx.__dict__:
        return ctx.__dict__["_onoff_squadra"]
    st = stint_eventi(ctx.ev, ctx.stints) if not ctx.stints.empty else pd.DataFrame()
    if st.empty:
        ctx.__dict__["_onoff_squadra"] = pd.DataFrame()
        return ctx.__dict__["_onoff_squadra"]
    st = st.rename(columns={"punti_fatti": "pf", "punti_subiti": "ps", "poss_fatti": "poss_f",
                            "poss_subiti": "poss_s"})
    somme = ["pf", "ps", "poss_f", "poss_s"] + [f"{l}_{k}" for l in ("f", "s") for k in _CONTA]
    x = st.assign(giocatore_id=st["quintetto"].str.split(",")).explode("giocatore_id")
    on = x.groupby(["squadra_id", "giocatore_id"])[somme].sum()
    tot = st.groupby("squadra_id")[somme].sum()
    off = tot.reindex(on.index.get_level_values("squadra_id")).set_axis(on.index) - on
    r = pd.concat([_fattori(on).add_suffix("_on"), _fattori(off).add_suffix("_off")], axis=1)
    r["poss_on"] = (on["poss_f"] + on["poss_s"]) / 2
    r["poss_off"] = (off["poss_f"] + off["poss_s"]) / 2
    for v in VOCI_ONOFF:
        r[f"{v.chiave}_off"] = r[f"{v.chiave}_off"].where(r["poss_off"] >= MIN_POSS_OFF)
        r[f"{v.chiave}_diff"] = r[f"{v.chiave}_on"] - r[f"{v.chiave}_off"]
    r = r.reset_index()
    ctx.__dict__["_onoff_squadra"] = r
    return r


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
    # compagni con minuti sufficienti (lui sempre compreso): la posizione dentro la squadra
    compagni = t[(t["squadra_id"] == sid) & (((t["partite"] >= MIN_PARTITE) & (t["minuti_pg"] >= MIN_MINUTI_PG))
                                             | (t["giocatore_id"] == gid))]
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
            squadra = _posizione_squadra(compagni, gid, v, val) if ok else None
            righe.append({"chiave": v.chiave, "sigla": v.sigla, "nome": v.nome, "cosa": v.cosa,
                          "in_squadra": squadra,
                          "valore": float(val) if ok else None,
                          "testo": (("+" if v.chiave == "net_on" and val > 0 else "") + _it(val, v.dec) + v.suffisso)
                          if ok else "–",
                          "pct": pct, "verso": v.verso, "livello": livello, "lettura": lettura})
        gruppi.append({"titolo": titolo, "sotto": sotto, "righe": righe})
    con_senza = _con_senza(ctx, sid, gid, me["campionato_id"])
    if con_senza and con_senza["pct_net"] is not None:
        if con_senza["pct_net"] >= 85:
            forti.append((con_senza["pct_net"], "con lui in campo la sua squadra rende molto meglio che senza"))
        elif con_senza["pct_net"] < 15:
            deboli.append((con_senza["pct_net"], "con lui in campo la sua squadra rende meno che senza"))
    sintesi = [x for _, x in sorted(forti, reverse=True)[:3]] + [x for _, x in sorted(deboli)[:2]]
    pochi = bool(me["partite"] < MIN_PARTITE or me["minuti_pg"] < MIN_MINUTI_PG)
    return {"gruppi": gruppi, "confronto": int(len(rif)), "pochi_dati": pochi, "sintesi": sintesi,
            "con_senza": con_senza, "compagni": int(len(compagni)),
            "forti": [x for _, x in sorted(forti, reverse=True)[:3]],
            "deboli": [x for _, x in sorted(deboli)[:2]]}


def _posizione_squadra(compagni: pd.DataFrame, gid: str, v: Voce, val: float) -> dict | None:
    """Posizione tra i compagni nella voce: {"pos": 2, "su": 9, "testo": "2° su 9"} (1° = il migliore;
    per le voci che descrivono, 1° = il valore più alto)."""
    serie = compagni[v.chiave].replace([np.inf, -np.inf], np.nan).dropna() if v.chiave in compagni else None
    if serie is None or len(serie) < 3:
        return None
    meglio = (serie < val).sum() if v.verso == -1 else (serie > val).sum()
    pos = int(meglio) + 1
    return {"pos": pos, "su": int(len(serie)), "testo": f"{pos}° su {len(serie)}"}


def _con_senza(ctx, sid: int, gid: str, camp: str) -> dict | None:
    """La squadra con lui in campo e senza di lui sulle VOCI_ONOFF, con la differenza e la posizione
    della differenza nel campionato (pct_net: quanti giocatori hanno un saldo con/senza peggiore)."""
    oo = on_off_squadra(ctx)
    if oo.empty:
        return None
    me = oo[(oo["squadra_id"] == sid) & (oo["giocatore_id"] == gid)]
    if me.empty:
        return None
    me = me.iloc[0]
    t = tabella(ctx)
    rif = t[(t["campionato_id"] == camp) & (t["partite"] >= MIN_PARTITE) & (t["minuti_pg"] >= MIN_MINUTI_PG)]
    rif = oo.merge(rif[["squadra_id", "giocatore_id"]], on=["squadra_id", "giocatore_id"])
    righe = []
    for v in VOCI_ONOFF:
        con, senza = me[f"{v.chiave}_on"], me[f"{v.chiave}_off"]
        ok_c, ok_s = pd.notna(con) and np.isfinite(con), pd.notna(senza) and np.isfinite(senza)
        diff = float(con - senza) if ok_c and ok_s else None
        meglio = None if diff is None or abs(diff) < 0.05 else (diff > 0) == (v.verso > 0)
        segno = "" if diff is None else ("+" if diff > 0 else "")
        unita = " punti" if v.chiave in ("ortg", "drtg", "net") else " punti %"
        righe.append({"chiave": v.chiave, "sigla": v.sigla, "nome": v.nome, "verso": v.verso,
                      "con": float(con) if ok_c else None, "senza": float(senza) if ok_s else None,
                      "diff": diff, "meglio": meglio,
                      "testo_con": (("+" if v.chiave == "net" and con > 0 else "") + _it(con, v.dec) + v.suffisso) if ok_c else "–",
                      "testo_senza": (("+" if v.chiave == "net" and senza > 0 else "") + _it(senza, v.dec) + v.suffisso) if ok_s else "–",
                      "testo_diff": (segno + _it(diff, v.dec) + (unita if diff is not None else "")) if diff is not None else "–"})
    pct = None
    serie = rif["net_diff"].replace([np.inf, -np.inf], np.nan).dropna()
    if pd.notna(me["net_diff"]) and len(serie) >= 8:
        pct = float(100 * (serie < me["net_diff"]).mean())
    return {"righe": righe, "poss_on": float(me["poss_on"]), "poss_off": float(me["poss_off"]),
            "pochi_senza": bool(me["poss_off"] < MIN_POSS_OFF), "pct_net": pct, "confronto": int(len(serie))}


def tabella_squadra(ctx, sid: int, n: int = 10) -> pd.DataFrame:
    """Per il report di squadra: i giocatori più utilizzati con le voci avanzate principali."""
    t = tabella(ctx)
    t = t[(t["squadra_id"] == sid) & (t["partite"] >= 1)].sort_values("minuti", ascending=False).head(n)
    return t[["giocatore_id", "giocatore", "minuti_pg", "net_on", "usg_pct", "ts_pct", "efg_pct", "ast_pct",
              "to_ratio", "trb_pct", "pie"]].reset_index(drop=True)
