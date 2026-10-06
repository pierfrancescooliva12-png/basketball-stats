"""Avvisi automatici di scouting e modulo "la mia squadra".

Avvisi generati dai box score dopo ogni giornata:
- assenza di un giocatore importante nell'ultima partita (possibile infortunio o squalifica);
- minuti in forte crescita o calo nelle ultime 3 partite;
- giocatore in forma o in calo (Game Score ultime 3 vs stagione);
- cambio di quintetto rispetto alla partita precedente;
- massimo stagionale di punti nell'ultima partita;
- serie di vittorie o sconfitte della squadra.
"""

import pandas as pd

from . import analysis as A

PRIORITA = {"assenza": 1, "quintetto": 2, "minuti": 2, "forma": 3, "massimo": 3, "serie": 2}


def _last_games(bs: pd.DataFrame, squadra_id: int, n: int) -> list[str]:
    t = bs[bs["squadra_id"] == squadra_id].sort_values(["data", "partita_id"])
    return t["partita_id"].tolist()[-n:]


def alerts(bs: pd.DataFrame, bg: pd.DataFrame) -> pd.DataFrame:
    rows = []
    bg = bg.copy()
    bg["game_score"] = A.game_score(bg)
    for sid, team in bs.groupby("squadra_id"):
        squadra = team["squadra"].iloc[0]
        camp = team["campionato_id"].iloc[0]
        games = team.sort_values(["data", "partita_id"])
        ids = games["partita_id"].tolist()
        if len(ids) < 2:
            continue
        last, prev = ids[-1], ids[-2]
        data_last = games["data"].iloc[-1]
        p = bg[bg["squadra_id"] == sid]

        def add(tipo, testo, giocatore=None):
            rows.append({"campionato_id": camp, "squadra_id": sid, "squadra": squadra,
                         "giocatore": giocatore, "tipo": tipo, "testo": testo,
                         "data": data_last, "priorita": PRIORITA[tipo]})

        # Serie di risultati
        esiti = games["vinta"].tolist()
        k = 1
        while k < len(esiti) and esiti[-k - 1] == esiti[-1]:
            k += 1
        if k >= 3:
            add("serie", f"{k} {'vittorie' if esiti[-1] else 'sconfitte'} consecutive")

        # Cambio di quintetto
        q_last = set(p[(p.partita_id == last) & (p.quintetto == 1)]["giocatore"])
        q_prev = set(p[(p.partita_id == prev) & (p.quintetto == 1)]["giocatore"])
        if q_last and q_prev and q_last != q_prev:
            dentro = ", ".join(sorted(q_last - q_prev))
            fuori = ", ".join(sorted(q_prev - q_last))
            add("quintetto", f"Quintetto cambiato: dentro {dentro}, fuori {fuori}")

        before = p[p.partita_id.isin(ids[:-1])]
        played_before = before[before["giocata"]]
        n_before = len(ids) - 1
        for gid, g in played_before.groupby("giocatore_id"):
            nome = g["giocatore"].iloc[0]
            pres, mpg = len(g), g["minuti"].mean()
            ultimo = p[(p.partita_id == last) & (p.giocatore_id == gid)]
            gioca_ultima = (not ultimo.empty) and bool(ultimo["giocata"].iloc[0])
            # Assenza di un giocatore di rotazione
            if pres >= max(1, 0.6 * n_before) and mpg >= 15 and not gioca_ultima:
                add("assenza", f"Non ha giocato l'ultima partita ({mpg:.0f}' di media prima)",
                    nome)
                continue
            if not gioca_ultima:
                continue
            all_g = p[(p.giocatore_id == gid) & p["giocata"]].sort_values(["data", "partita_id"])
            if len(all_g) >= 5:
                recent, older = all_g.tail(3), all_g.iloc[:-3]
                dm = recent["minuti"].mean() - older["minuti"].mean()
                if abs(dm) >= 7:
                    add("minuti", f"Minuti {'in crescita' if dm > 0 else 'in calo'}: "
                        f"{recent['minuti'].mean():.0f}' nelle ultime 3 contro "
                        f"{older['minuti'].mean():.0f}' prima", nome)
                dg = recent["game_score"].mean() - older["game_score"].mean()
                if older["minuti"].mean() >= 12 and abs(dg) >= 5:
                    add("forma", f"{'In forma' if dg > 0 else 'In calo'}: Game Score "
                        f"{recent['game_score'].mean():.1f} nelle ultime 3 contro "
                        f"{older['game_score'].mean():.1f}", nome)
            pts = ultimo["punti"].iloc[0]
            if len(all_g) >= 4 and pts >= 15 and pts > all_g.iloc[:-1]["punti"].max():
                add("massimo", f"Massimo stagionale: {int(pts)} punti nell'ultima partita", nome)
    out = pd.DataFrame(rows, columns=["campionato_id", "squadra_id", "squadra", "giocatore",
                                      "tipo", "testo", "data", "priorita"])
    return out.sort_values(["priorita", "squadra"])


def split_by_opponent(bs: pd.DataFrame, squadra_id: int) -> pd.DataFrame:
    """Rendimento contro la metà alta e la metà bassa del campionato (per Net rating)."""
    camp = bs.loc[bs["squadra_id"] == squadra_id, "campionato_id"].iloc[0]
    t = A.team_summary(bs[bs["campionato_id"] == camp])
    med = t["net_rtg"].median()
    forti = set(t.loc[t["net_rtg"] >= med, "squadra_id"])
    mine = bs[bs["squadra_id"] == squadra_id].copy()
    mine["avversari"] = mine["avversario_id"].map(
        lambda x: "Metà alta" if x in forti else "Metà bassa")
    return A.team_summary(mine, by=["avversari"])


def rolling_form(bs: pd.DataFrame, squadra_id: int, n: int = 5) -> pd.DataFrame:
    """Andamento partita per partita di ORtg, DRtg ed eFG% con media mobile."""
    mine = bs[(bs["squadra_id"] == squadra_id) & bs["affidabile"]].sort_values(
        ["data", "partita_id"]).copy()
    if mine.empty:
        return mine
    r = A.team_ratings(mine)
    for c in ("ortg", "drtg", "net_rtg", "efg_pct", "tov_pct", "orb_pct", "ft_rate"):
        r[f"{c}_mm"] = r[c].rolling(n, min_periods=1).mean()
    return r


# Obiettivi di riferimento per i Four Factors (modificabili dallo staff nella dashboard)
OBIETTIVI_DEFAULT = {"efg_pct": 53.0, "tov_pct": 13.0, "orb_pct": 32.0, "ft_rate": 0.24,
                     "opp_efg_pct": 48.0, "opp_tov_pct": 16.0, "drb_pct": 72.0,
                     "opp_ft_rate": 0.20}
OBIETTIVO_MEGLIO_ALTO = {"efg_pct": True, "tov_pct": False, "orb_pct": True, "ft_rate": True,
                         "opp_efg_pct": False, "opp_tov_pct": True, "drb_pct": True,
                         "opp_ft_rate": False}
