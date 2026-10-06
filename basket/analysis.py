"""Analisi statistiche: medie, per 40 minuti, metriche avanzate, trend e split.

Formule principali (Dean Oliver / basketball-reference):
    Possessi  = FGA - OREB + TOV + 0.44 * FTA   (media tra le due squadre della partita)
    ORtg      = 100 * Punti / Possessi             DRtg = 100 * Punti subiti / Possessi
    eFG%      = (FGM + 0.5 * 3PM) / FGA            TS%  = Punti / (2 * (FGA + 0.44 * FTA))
    TOV%      = TOV / (FGA + 0.44 * FTA + TOV)     OREB% = OREB / (OREB + DREB avversari)
    FT rate   = FTM / FGA
    USG%      = 100 * (FGA + 0.44 FTA + TOV) * (MinSquadra / 5) / (Min * (FGA+0.44FTA+TOV squadra))
    AST ratio = 100 * AST / (FGA + 0.44 * FTA + AST + TOV)
    Game Score = PTS + 0.4 FGM - 0.7 FGA - 0.4 (FTA-FTM) + 0.7 OREB + 0.3 DREB + STL
                 + 0.7 AST + 0.7 BLK - 0.4 PF - TOV
    Percentuali individuali (OREB%, DREB%, AST%, STL%, BLK%): quota delle occasioni di
    squadra mentre il giocatore era in campo, stimata con la quota di minuti.
    Vittorie attese (pitagorica) = PF^14 / (PF^14 + PS^14)
"""

import json
import sqlite3

import numpy as np
import pandas as pd

COUNT_STATS = [
    "punti", "t2m", "t2a", "t3m", "t3a", "tlm", "tla", "rimb_off", "rimb_dif", "rimb_tot",
    "assist", "perse", "recuperate", "stoppate", "stoppate_subite",
    "falli_commessi", "falli_subiti", "valutazione",
]
FT = 0.44

# Controllo qualità: sotto questo ritmo (possessi per 40') il box score ufficiale è
# considerato incompleto (tiri tentati / rimbalzi / perse non registrati del tutto).
# Queste partite restano valide per risultati, punti e totali, ma sono escluse
# da percentuali e metriche avanzate.
MIN_PACE_AFFIDABILE = 58.0

TEAM_ADV = ["fg_pct", "t2_pct", "t3_pct", "tl_pct", "efg_pct", "ts_pct", "possessi", "pace",
            "ortg", "drtg", "net_rtg", "tov_pct", "orb_pct", "ft_rate", "opp_efg_pct",
            "opp_tov_pct", "drb_pct", "opp_ft_rate", "ast_ratio"]
PLAYER_ADV = ["fg_pct", "t2_pct", "t3_pct", "tl_pct", "efg_pct", "ts_pct", "usg_pct",
              "ast_ratio", "ast_pct", "orb_pct", "drb_pct", "trb_pct", "stl_pct", "blk_pct",
              "tov_pct", "ft_rate", "t3a_rate"]


# ------------------------------------------------------------------ caricamento

def load_box_giocatore(conn: sqlite3.Connection, stagione: str | None = None) -> pd.DataFrame:
    df = pd.read_sql_query(
        """
        SELECT b.*, g.nome AS giocatore, s.nome AS squadra,
               p.campionato_id, p.stagione, p.giornata, p.data, p.gameid,
               CASE WHEN b.squadra_id = p.squadra_casa_id THEN 1 ELSE 0 END AS casa,
               CASE WHEN b.squadra_id = p.squadra_casa_id THEN p.squadra_ospite_id
                    ELSE p.squadra_casa_id END AS avversario_id
        FROM box_giocatore b
        JOIN partite p USING (partita_id)
        JOIN giocatori g USING (giocatore_id)
        JOIN squadre s ON s.squadra_id = b.squadra_id
        WHERE (:stagione IS NULL OR p.stagione = :stagione)
        """,
        conn, params={"stagione": stagione},
    )
    df["minuti"] = df["minuti"].fillna(0.0)
    df[COUNT_STATS] = df[COUNT_STATS].fillna(0)
    df["giocata"] = df["minuti"] > 0
    nomi = dict(conn.execute("SELECT squadra_id, nome FROM squadre").fetchall())
    df["avversario"] = df["avversario_id"].map(nomi)
    df = df.merge(game_quality(conn, stagione)[["partita_id", "affidabile"]], on="partita_id",
                  how="left")
    df["affidabile"] = df["affidabile"].fillna(True).astype(bool)
    return df


def load_box_squadra(conn: sqlite3.Connection, stagione: str | None = None) -> pd.DataFrame:
    """Una riga per squadra e partita, con le statistiche dell'avversario (prefisso opp_)."""
    bs = pd.read_sql_query(
        """
        SELECT b.*, s.nome AS squadra, p.campionato_id, p.stagione, p.giornata, p.data, p.gameid
        FROM box_squadra b
        JOIN partite p USING (partita_id)
        JOIN squadre s ON s.squadra_id = b.squadra_id
        WHERE (:stagione IS NULL OR p.stagione = :stagione)
        """,
        conn, params={"stagione": stagione},
    )
    stat_cols = ["minuti"] + COUNT_STATS
    opp = bs[["partita_id", "squadra_id", "squadra"] + stat_cols].rename(
        columns={c: f"opp_{c}" for c in stat_cols + ["squadra"]} | {"squadra_id": "avversario_id"})
    bs = bs.merge(opp, on=["partita_id", "avversario_id"], how="left")
    bs = bs.rename(columns={"opp_squadra": "avversario"})
    bs["vinta"] = bs["punti"] > bs["punti_subiti"]
    bs = bs.merge(_quality(bs), on="partita_id", how="left")
    return bs.sort_values(["data", "partita_id"]).reset_index(drop=True)


def _quality(bs: pd.DataFrame) -> pd.DataFrame:
    """Ritmo della partita e flag di affidabilità del box score."""
    poss = (possessi_grezzi(bs) + possessi_grezzi(bs, "opp_")) / 2
    q = pd.DataFrame({"partita_id": bs["partita_id"],
                      "pace_partita": 40 * _div(poss, bs["minuti"].where(bs["minuti"] > 0, 200) / 5)})
    q = q.groupby("partita_id", as_index=False)["pace_partita"].mean()
    q["affidabile"] = q["pace_partita"] >= MIN_PACE_AFFIDABILE
    return q


def game_quality(conn: sqlite3.Connection, stagione: str | None = None) -> pd.DataFrame:
    return load_box_squadra(conn, stagione)[["partita_id", "pace_partita", "affidabile"]
                                            ].drop_duplicates()


# ------------------------------------------------------------------ formule

def _div(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(b != 0, a / b, np.nan)
    return out if out.ndim else float(out)


def _fga(df, p=""):
    return df[f"{p}t2a"] + df[f"{p}t3a"]


def _fgm(df, p=""):
    return df[f"{p}t2m"] + df[f"{p}t3m"]


def possessi_grezzi(df, p=""):
    return _fga(df, p) - df[f"{p}rimb_off"] + df[f"{p}perse"] + FT * df[f"{p}tla"]


def add_shooting(df: pd.DataFrame) -> pd.DataFrame:
    """Percentuali di tiro, eFG%, TS% (in %)."""
    df = df.copy()
    fga, fgm = _fga(df), _fgm(df)
    df["fgm"], df["fga"] = fgm, fga
    df["fg_pct"] = 100 * _div(fgm, fga)
    df["t2_pct"] = 100 * _div(df["t2m"], df["t2a"])
    df["t3_pct"] = 100 * _div(df["t3m"], df["t3a"])
    df["tl_pct"] = 100 * _div(df["tlm"], df["tla"])
    df["efg_pct"] = 100 * _div(fgm + 0.5 * df["t3m"], fga)
    df["ts_pct"] = 100 * _div(df["punti"], 2 * (fga + FT * df["tla"]))
    return df


def team_ratings(df: pd.DataFrame) -> pd.DataFrame:
    """Metriche avanzate di squadra su righe che hanno sia le statistiche proprie
    sia quelle avversarie (opp_). Funziona sia su singole partite sia su somme."""
    df = add_shooting(df)
    poss = (possessi_grezzi(df) + possessi_grezzi(df, "opp_")) / 2
    df["possessi"] = poss
    minuti_partita = df["minuti"].where(df["minuti"] > 0, 200) / 5
    df["pace"] = 40 * _div(poss, minuti_partita)
    df["ortg"] = 100 * _div(df["punti"], poss)
    df["drtg"] = 100 * _div(df["punti_subiti"], poss)
    df["net_rtg"] = df["ortg"] - df["drtg"]
    # Four Factors, attacco
    df["tov_pct"] = 100 * _div(df["perse"], _fga(df) + FT * df["tla"] + df["perse"])
    df["orb_pct"] = 100 * _div(df["rimb_off"], df["rimb_off"] + df["opp_rimb_dif"])
    df["ft_rate"] = _div(df["tlm"], _fga(df))
    # Four Factors, difesa (valori concessi agli avversari)
    opp_fga = _fga(df, "opp_")
    df["opp_efg_pct"] = 100 * _div(_fgm(df, "opp_") + 0.5 * df["opp_t3m"], opp_fga)
    df["opp_tov_pct"] = 100 * _div(df["opp_perse"], opp_fga + FT * df["opp_tla"] + df["opp_perse"])
    df["drb_pct"] = 100 * _div(df["rimb_dif"], df["rimb_dif"] + df["opp_rimb_off"])
    df["opp_ft_rate"] = _div(df["opp_tlm"], opp_fga)
    df["ast_ratio"] = 100 * _div(df["assist"], _fga(df) + FT * df["tla"] + df["assist"] + df["perse"])
    return df


# ------------------------------------------------------------------ squadre

def team_summary(bs: pd.DataFrame, by: list[str] | None = None) -> pd.DataFrame:
    """Riepilogo di squadra: record, medie a partita, per 40 minuti e avanzate.

    Le metriche avanzate si calcolano sulle somme (non come media delle percentuali)
    e solo sulle partite con box score affidabile."""
    keys = ["campionato_id", "squadra_id", "squadra"] + (by or [])
    out = _team_summary(bs, by)
    return _replace_adv(out, _team_summary(bs[bs["affidabile"]], by), keys, TEAM_ADV)


def _replace_adv(base: pd.DataFrame, rel: pd.DataFrame, keys: list[str],
                 cols: list[str]) -> pd.DataFrame:
    """Sostituisce le metriche avanzate con quelle calcolate sulle sole partite affidabili."""
    rel = rel[keys + cols + ["partite"]].rename(columns={"partite": "partite_avanzate"})
    out = base.drop(columns=cols).merge(rel, on=keys, how="left")
    out["partite_avanzate"] = out["partite_avanzate"].fillna(0).astype(int)
    return out


def _team_summary(bs: pd.DataFrame, by: list[str] | None = None) -> pd.DataFrame:
    keys = ["campionato_id", "squadra_id", "squadra"] + (by or [])
    sum_cols = (["minuti", "punti", "punti_subiti"] + COUNT_STATS[1:]
                + [c for c in bs.columns if c.startswith("opp_")])
    g = bs.groupby(keys, dropna=False)
    tot = g[sum_cols].sum()
    tot["partite"] = g.size()
    tot["vinte"] = g["vinta"].sum()
    tot["perse_partite"] = tot["partite"] - tot["vinte"]
    tot = team_ratings(tot.reset_index())
    for c in ["punti", "punti_subiti", "rimb_off", "rimb_dif", "rimb_tot", "assist",
              "perse", "recuperate", "stoppate", "valutazione", "t3m", "t3a", "tlm", "tla",
              "t2m", "t2a", "falli_commessi"]:
        tot[f"{c}_pg"] = tot[c] / tot["partite"]
        tot[f"{c}_p40"] = 40 * _div(tot[c], tot["minuti"] / 5)
    tot["vittorie_pct"] = 100 * tot["vinte"] / tot["partite"]
    return tot


def standings(bs: pd.DataFrame) -> pd.DataFrame:
    t = team_summary(bs)
    t["punti_classifica"] = 2 * t["vinte"]
    t["diff"] = t["punti"] - t["punti_subiti"]
    t = t.sort_values(["campionato_id", "punti_classifica", "diff"], ascending=[True, False, False])
    t["pos"] = t.groupby("campionato_id").cumcount() + 1
    return t


def team_last_n(bs: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    last = bs.sort_values(["data", "partita_id"]).groupby("squadra_id").tail(n)
    out = team_summary(last)
    out["ultime"] = n
    return out


# ------------------------------------------------------------------ giocatori

def _team_game_totals(bs: pd.DataFrame) -> pd.DataFrame:
    """Totali di squadra e avversari per partita, usati dalle percentuali individuali."""
    t = bs[["partita_id", "squadra_id"]].copy()
    t["tm_minuti"] = bs["minuti"].where(bs["minuti"] > 0, 200)
    t["tm_poss_used"] = _fga(bs) + FT * bs["tla"] + bs["perse"]
    t["tm_fgm"] = _fgm(bs)
    t["tm_reb_off_chances"] = bs["rimb_off"] + bs["opp_rimb_dif"]
    t["tm_reb_dif_chances"] = bs["rimb_dif"] + bs["opp_rimb_off"]
    t["opp_poss"] = (possessi_grezzi(bs) + possessi_grezzi(bs, "opp_")) / 2
    t["opp_2pa"] = bs["opp_t2a"]
    return t


# Denominatori di squadra pesati sulla quota di minuti del giocatore
_SHARE_COLS = {
    "sh_poss_used": "tm_poss_used", "sh_fgm": "tm_fgm", "sh_reb_off": "tm_reb_off_chances",
    "sh_reb_dif": "tm_reb_dif_chances", "sh_opp_poss": "opp_poss", "sh_opp_2pa": "opp_2pa",
}


def game_score(df: pd.DataFrame) -> pd.Series:
    """Game Score (Hollinger): sintesi del rendimento in una partita."""
    return (df["punti"] + 0.4 * _fgm(df) - 0.7 * _fga(df) - 0.4 * (df["tla"] - df["tlm"])
            + 0.7 * df["rimb_off"] + 0.3 * df["rimb_dif"] + df["recuperate"]
            + 0.7 * df["assist"] + 0.7 * df["stoppate"] - 0.4 * df["falli_commessi"]
            - df["perse"])


def _double_double(df: pd.DataFrame) -> pd.Series:
    cats = (df[["punti", "rimb_tot", "assist", "recuperate", "stoppate"]] >= 10).sum(axis=1)
    return cats >= 2


def player_summary(bg: pd.DataFrame, bs: pd.DataFrame, by: list[str] | None = None,
                   min_partite: int = 0) -> pd.DataFrame:
    """Riepilogo giocatori: totali, medie a partita, per 40 minuti, avanzate.

    Si contano solo le partite in cui il giocatore è entrato (minuti > 0).
    Percentuali e metriche avanzate escludono le partite con box score incompleto."""
    keys = ["campionato_id", "giocatore_id", "giocatore", "squadra_id", "squadra"] + (by or [])
    out = _player_summary(bg, bs, by)
    rel = _player_summary(bg[bg["affidabile"]], bs, by)
    out = _replace_adv(out, rel, keys, PLAYER_ADV)
    if min_partite:
        out = out[out["partite"] >= min_partite]
    return out.sort_values("punti_pg", ascending=False).reset_index(drop=True)


def _player_summary(bg: pd.DataFrame, bs: pd.DataFrame, by: list[str] | None = None
                    ) -> pd.DataFrame:
    played = bg[bg["giocata"]].merge(_team_game_totals(bs), on=["partita_id", "squadra_id"],
                                     how="left")
    played["poss_used"] = _fga(played) + FT * played["tla"] + played["perse"]
    # Quota di minuti del giocatore sul totale di squadra (1 = sempre in campo)
    quota = played["minuti"] / (played["tm_minuti"] / 5)
    for share, col in _SHARE_COLS.items():
        played[share] = quota * played[col]
    played["game_score"] = game_score(played)
    played["doppia_doppia"] = _double_double(played)
    keys = ["campionato_id", "giocatore_id", "giocatore", "squadra_id", "squadra"] + (by or [])
    g = played.groupby(keys, dropna=False)
    tot = g[["minuti"] + COUNT_STATS + ["poss_used", "game_score", "doppia_doppia"]
            + list(_SHARE_COLS)].sum()
    tot["partite"] = g.size()
    tot["quintetti"] = g["quintetto"].sum()
    tot["punti_std"] = g["punti"].std(ddof=0)
    tot["max_punti"] = g["punti"].max()
    tot = add_shooting(tot.reset_index())
    tot["doppie_doppie"] = tot.pop("doppia_doppia").astype(int)
    tot["usg_pct"] = 100 * _div(tot["poss_used"], tot["sh_poss_used"])
    tot["ast_ratio"] = 100 * _div(tot["assist"], tot["fga"] + FT * tot["tla"] + tot["assist"]
                                  + tot["perse"])
    # Percentuali individuali (stile basketball-reference)
    tot["ast_pct"] = 100 * _div(tot["assist"], tot["sh_fgm"] - tot["fgm"])
    tot["orb_pct"] = 100 * _div(tot["rimb_off"], tot["sh_reb_off"])
    tot["drb_pct"] = 100 * _div(tot["rimb_dif"], tot["sh_reb_dif"])
    tot["trb_pct"] = 100 * _div(tot["rimb_tot"], tot["sh_reb_off"] + tot["sh_reb_dif"])
    tot["stl_pct"] = 100 * _div(tot["recuperate"], tot["sh_opp_poss"])
    tot["blk_pct"] = 100 * _div(tot["stoppate"], tot["sh_opp_2pa"])
    tot["tov_pct"] = 100 * _div(tot["perse"], tot["fga"] + FT * tot["tla"] + tot["perse"])
    tot["ft_rate"] = _div(tot["tla"], tot["fga"])
    tot["t3a_rate"] = 100 * _div(tot["t3a"], tot["fga"])
    tot["minuti_pg"] = tot["minuti"] / tot["partite"]
    tot["game_score_pg"] = tot["game_score"] / tot["partite"]
    tot["game_score_p40"] = 40 * _div(tot["game_score"], tot["minuti"])
    # Costanza: coefficiente di variazione dei punti (più basso = più costante)
    tot["punti_cv"] = _div(tot["punti_std"], tot["punti"] / tot["partite"])
    for c in COUNT_STATS + ["fgm", "fga"]:
        tot[f"{c}_pg"] = tot[c] / tot["partite"]
        tot[f"{c}_p40"] = 40 * _div(tot[c], tot["minuti"])
    return tot.drop(columns=["poss_used"] + list(_SHARE_COLS))


def player_trend(bg: pd.DataFrame, bs: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Medie nelle ultime n partite giocate a confronto con la stagione."""
    played = bg[bg["giocata"]].sort_values(["data", "partita_id"])
    last = played.groupby(["giocatore_id", "squadra_id"]).tail(n)
    season = player_summary(bg, bs)
    recent = player_summary(last.assign(giocata=True), bs)
    cols = ["punti_pg", "rimb_tot_pg", "assist_pg", "valutazione_pg", "minuti_pg", "ts_pct",
            "usg_pct"]
    out = season[["campionato_id", "giocatore_id", "giocatore", "squadra_id", "squadra",
                  "partite"] + cols].merge(
        recent[["giocatore_id", "squadra_id", "partite"] + cols],
        on=["giocatore_id", "squadra_id"], suffixes=("", f"_ult{n}"))
    for c in cols:
        out[f"{c}_delta"] = out[f"{c}_ult{n}"] - out[c]
    return out


def player_game_log(bg: pd.DataFrame, giocatore_id: str) -> pd.DataFrame:
    log = bg[(bg["giocatore_id"] == giocatore_id) & bg["giocata"]].sort_values(
        ["data", "partita_id"])
    return add_shooting(log)


def league_averages(team_tot: pd.DataFrame) -> pd.DataFrame:
    """Media del campionato delle metriche di squadra (per i confronti nello scouting)."""
    cols = ["ortg", "drtg", "net_rtg", "pace", "efg_pct", "tov_pct", "orb_pct", "ft_rate",
            "opp_efg_pct", "opp_tov_pct", "drb_pct", "opp_ft_rate", "ts_pct", "t3_pct",
            "ast_ratio", "punti_pg", "punti_subiti_pg"]
    return team_tot.groupby("campionato_id")[cols].mean()


# ------------------------------------------------------------------ profilo squadra

PYTH_EXP = 14.0
CLOSE_MARGIN = 5


def load_quarters(conn: sqlite3.Connection, stagione: str | None = None) -> pd.DataFrame:
    """Punti per periodo: una riga per squadra, partita e periodo."""
    rows = []
    for pid, camp, casa, ospite, parz in conn.execute(
            "SELECT partita_id, campionato_id, squadra_casa_id, squadra_ospite_id, parziali "
            "FROM partite WHERE (:s IS NULL OR stagione = :s)", {"s": stagione}):
        for p in json.loads(parz or "[]"):
            rows.append((pid, camp, casa, p["periodo"], p["casa"], p["ospite"]))
            rows.append((pid, camp, ospite, p["periodo"], p["ospite"], p["casa"]))
    return pd.DataFrame(rows, columns=["partita_id", "campionato_id", "squadra_id", "periodo",
                                       "fatti", "subiti"])


def quarter_profile(q: pd.DataFrame) -> pd.DataFrame:
    """Media punti fatti/subiti e differenza per quarto (supplementari esclusi)."""
    q = q[q["periodo"] <= 4]
    out = q.groupby(["campionato_id", "squadra_id", "periodo"])[["fatti", "subiti"]].mean()
    out["diff"] = out["fatti"] - out["subiti"]
    wide = out["diff"].unstack("periodo").add_prefix("diff_q")
    return wide.reset_index()


def team_profile(bs: pd.DataFrame, bg: pd.DataFrame, quarters: pd.DataFrame | None = None
                 ) -> pd.DataFrame:
    """Statistiche di contesto per squadra: fortuna, partite punto a punto, calendario,
    panchina, distribuzione dei punti, dipendenza dai migliori realizzatori, quarti."""
    tot = team_summary(bs)
    keys = ["campionato_id", "squadra_id"]
    # Vittorie attese (pitagorica)
    pf, pa = tot["punti"].astype(float), tot["punti_subiti"].astype(float)
    tot["pyth_pct"] = 100 * pf ** PYTH_EXP / (pf ** PYTH_EXP + pa ** PYTH_EXP)
    tot["vinte_attese"] = tot["pyth_pct"] / 100 * tot["partite"]
    tot["fortuna"] = tot["vinte"] - tot["vinte_attese"]
    # Partite punto a punto
    margin = (bs["punti"] - bs["punti_subiti"]).abs()
    close = bs[margin <= CLOSE_MARGIN].groupby(keys)["vinta"].agg(["sum", "count"])
    close.columns = ["vinte_pp", "partite_pp"]
    tot = tot.merge(close.reset_index(), on=keys, how="left")
    tot[["vinte_pp", "partite_pp"]] = tot[["vinte_pp", "partite_pp"]].fillna(0).astype(int)
    tot["record_pp"] = tot["vinte_pp"].astype(str) + "-" + (tot["partite_pp"]
                                                            - tot["vinte_pp"]).astype(str)
    # Forza del calendario: Net rating medio degli avversari affrontati
    net = tot.set_index("squadra_id")["net_rtg"]
    sos = bs.assign(opp_net=bs["avversario_id"].map(net)).groupby(keys)["opp_net"].mean()
    tot = tot.merge(sos.rename("sos").reset_index(), on=keys, how="left")
    # Distribuzione dei punti
    tot["quota_punti_2"] = 100 * _div(2 * tot["t2m"], tot["punti"])
    tot["quota_punti_3"] = 100 * _div(3 * tot["t3m"], tot["punti"])
    tot["quota_punti_tl"] = 100 * _div(tot["tlm"], tot["punti"])
    tot["ast_su_canestri"] = 100 * _div(tot["assist"], tot["t2m"] + tot["t3m"])
    # Panchina e dipendenza dai migliori realizzatori
    played = bg[bg["giocata"]]
    bench = played[played["quintetto"] == 0].groupby(keys)[["punti", "minuti"]].sum()
    allp = played.groupby(keys)[["punti", "minuti"]].sum()
    share = (100 * bench / allp).rename(columns={"punti": "quota_punti_panchina",
                                                 "minuti": "quota_minuti_panchina"})
    tot = tot.merge(share.reset_index(), on=keys, how="left")
    by_player = played.groupby(keys + ["giocatore_id"])["punti"].sum().reset_index()
    top2 = (by_player.sort_values("punti", ascending=False).groupby(keys).head(2)
            .groupby(keys)["punti"].sum())
    tot = tot.merge((100 * top2 / allp["punti"]).rename("quota_top2").reset_index(),
                    on=keys, how="left")
    if quarters is not None and not quarters.empty:
        tot = tot.merge(quarter_profile(quarters), on=keys, how="left")
    return tot


# ------------------------------------------------------------------ leader e percentili

def qualified(players: pd.DataFrame, min_quota_partite: float = 0.5,
              min_minuti: float = 10.0) -> pd.DataFrame:
    """Giocatori con abbastanza partite e minuti per comparire nelle classifiche."""
    max_g = players.groupby("campionato_id")["partite"].transform("max")
    return players[(players["partite"] >= np.ceil(max_g * min_quota_partite))
                   & (players["minuti_pg"] >= min_minuti)]


def leaders(players: pd.DataFrame, col: str, n: int = 10, ascending: bool = False
            ) -> pd.DataFrame:
    return qualified(players).dropna(subset=[col]).sort_values(col, ascending=ascending).head(n)


# metrica -> (etichetta, True se più alto è meglio)
PERCENTILE_METRICS = {
    "punti_p40": ("Punti / 40'", True),
    "ts_pct": ("TS%", True),
    "usg_pct": ("Usage", True),
    "t3_pct": ("% da 3", True),
    "ft_rate": ("Frequenza ai liberi", True),
    "ast_pct": ("Assist %", True),
    "tov_pct": ("Palle perse %", False),
    "orb_pct": ("Rimb. offensivi %", True),
    "drb_pct": ("Rimb. difensivi %", True),
    "stl_pct": ("Recuperi %", True),
    "blk_pct": ("Stoppate %", True),
    "game_score_pg": ("Game Score", True),
}


def percentiles(players: pd.DataFrame, giocatore_id: str, squadra_id: int) -> pd.DataFrame:
    """Percentile del giocatore (0-100, 100 = migliore) nel suo campionato,
    rispetto ai giocatori con almeno 10 minuti di media."""
    me = players[(players["giocatore_id"] == giocatore_id) & (players["squadra_id"] == squadra_id)]
    if me.empty:
        return pd.DataFrame(columns=["Metrica", "Valore", "Percentile"])
    me = me.iloc[0]
    pool = players[(players["campionato_id"] == me["campionato_id"])
                   & (players["minuti_pg"] >= 10)]
    rows = []
    for col, (label, higher) in PERCENTILE_METRICS.items():
        vals = pool[col].dropna()
        if pd.isna(me[col]) or vals.empty:
            continue
        pct = (vals < me[col]).mean() + 0.5 * (vals == me[col]).mean()
        rows.append({"Metrica": label, "Valore": me[col],
                     "Percentile": round(100 * (pct if higher else 1 - pct))})
    return pd.DataFrame(rows)
