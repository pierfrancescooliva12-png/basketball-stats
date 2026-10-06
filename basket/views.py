"""Tabelle pronte da mostrare (Excel e dashboard), con intestazioni in italiano."""

import pandas as pd

from . import analysis as A
from . import config

TEAM_BASE = {"campionato": "Campionato", "squadra": "Squadra", "partite": "PG",
             "vinte": "V", "perse_partite": "P"}
PLAYER_BASE = {"campionato": "Campionato", "giocatore": "Giocatore", "squadra": "Squadra",
               "partite": "PG", "quintetti": "Quint.", "minuti_pg": "Min"}

TEAM_MEDIE = TEAM_BASE | {
    "punti_pg": "Punti", "punti_subiti_pg": "Subiti", "t2m_pg": "2PM", "t2a_pg": "2PA",
    "t2_pct": "2P%", "t3m_pg": "3PM", "t3a_pg": "3PA", "t3_pct": "3P%", "tlm_pg": "TLM",
    "tla_pg": "TLA", "tl_pct": "TL%", "rimb_off_pg": "RO", "rimb_dif_pg": "RD",
    "rimb_tot_pg": "RT", "assist_pg": "Ass", "perse_pg": "Perse", "recuperate_pg": "Rec",
    "stoppate_pg": "Stop", "falli_commessi_pg": "Falli", "valutazione_pg": "Val",
}
TEAM_P40 = TEAM_BASE | {
    "punti_p40": "Punti/40", "rimb_off_p40": "RO/40", "rimb_dif_p40": "RD/40",
    "rimb_tot_p40": "RT/40", "assist_p40": "Ass/40", "perse_p40": "Perse/40",
    "recuperate_p40": "Rec/40", "stoppate_p40": "Stop/40", "t3a_p40": "3PA/40",
    "tla_p40": "TLA/40", "valutazione_p40": "Val/40",
}
TEAM_AVANZATE = TEAM_BASE | {
    "pace": "Pace", "ortg": "ORtg", "drtg": "DRtg", "net_rtg": "Net Rtg",
    "efg_pct": "eFG%", "ts_pct": "TS%", "tov_pct": "TOV%", "orb_pct": "OREB%",
    "ft_rate": "FT rate", "opp_efg_pct": "eFG% avv.", "opp_tov_pct": "TOV% avv.",
    "drb_pct": "DREB%", "opp_ft_rate": "FT rate avv.", "ast_ratio": "AST ratio",
}
PLAYER_MEDIE = PLAYER_BASE | {
    "punti_pg": "Punti", "t2m_pg": "2PM", "t2a_pg": "2PA", "t2_pct": "2P%",
    "t3m_pg": "3PM", "t3a_pg": "3PA", "t3_pct": "3P%", "tlm_pg": "TLM", "tla_pg": "TLA",
    "tl_pct": "TL%", "rimb_off_pg": "RO", "rimb_dif_pg": "RD", "rimb_tot_pg": "RT",
    "assist_pg": "Ass", "perse_pg": "Perse", "recuperate_pg": "Rec", "stoppate_pg": "Stop",
    "falli_commessi_pg": "Falli", "falli_subiti_pg": "F. sub.", "valutazione_pg": "Val",
}
PLAYER_TOTALI = PLAYER_BASE | {
    "minuti": "Min tot", "punti": "Punti", "t2m": "2PM", "t2a": "2PA", "t3m": "3PM",
    "t3a": "3PA", "tlm": "TLM", "tla": "TLA", "rimb_off": "RO", "rimb_dif": "RD",
    "rimb_tot": "RT", "assist": "Ass", "perse": "Perse", "recuperate": "Rec",
    "stoppate": "Stop", "falli_commessi": "Falli", "valutazione": "Val",
}
PLAYER_P40 = PLAYER_BASE | {
    "punti_p40": "Punti/40", "rimb_off_p40": "RO/40", "rimb_dif_p40": "RD/40",
    "rimb_tot_p40": "RT/40", "assist_p40": "Ass/40", "perse_p40": "Perse/40",
    "recuperate_p40": "Rec/40", "stoppate_p40": "Stop/40", "fga_p40": "FGA/40",
    "t3a_p40": "3PA/40", "tla_p40": "TLA/40", "valutazione_p40": "Val/40",
}
PLAYER_AVANZATE = PLAYER_BASE | {
    "fg_pct": "FG%", "efg_pct": "eFG%", "ts_pct": "TS%", "t3_pct": "3P%", "tl_pct": "TL%",
    "usg_pct": "USG%", "ast_ratio": "AST ratio", "game_score_pg": "Game Score",
    "punti_p40": "Punti/40",
}
PLAYER_RUOLO = PLAYER_BASE | {
    "ast_pct": "AST%", "tov_pct": "TOV%", "orb_pct": "OREB%", "drb_pct": "DREB%",
    "trb_pct": "REB%", "stl_pct": "STL%", "blk_pct": "BLK%", "t3a_rate": "% tiri da 3",
    "ft_rate": "FTA/FGA", "falli_subiti_p40": "F. sub./40", "doppie_doppie": "Doppie doppie",
    "max_punti": "Max punti", "punti_cv": "Variabilità punti",
}
TEAM_PROFILO = TEAM_BASE | {
    "pyth_pct": "V% attesa", "vinte_attese": "V attese", "fortuna": "Fortuna",
    "record_pp": "Punto a punto", "sos": "Forza calendario", "quota_punti_2": "% punti da 2",
    "quota_punti_3": "% punti da 3", "quota_punti_tl": "% punti TL",
    "ast_su_canestri": "% canestri assistiti", "quota_punti_panchina": "% punti panchina",
    "quota_minuti_panchina": "% minuti panchina", "quota_top2": "% punti top 2",
    "diff_q1": "Diff Q1", "diff_q2": "Diff Q2", "diff_q3": "Diff Q3", "diff_q4": "Diff Q4",
}
TREND = {
    "campionato": "Campionato", "giocatore": "Giocatore", "squadra": "Squadra", "partite": "PG",
    "punti_pg": "Punti stag.", "punti_pg_ult5": "Punti ult.5", "punti_pg_delta": "Δ Punti",
    "rimb_tot_pg": "RT stag.", "rimb_tot_pg_ult5": "RT ult.5",
    "assist_pg": "Ass stag.", "assist_pg_ult5": "Ass ult.5",
    "valutazione_pg": "Val stag.", "valutazione_pg_ult5": "Val ult.5",
    "valutazione_pg_delta": "Δ Val", "ts_pct": "TS% stag.", "ts_pct_ult5": "TS% ult.5",
    "minuti_pg": "Min stag.", "minuti_pg_ult5": "Min ult.5",
}
CLASSIFICA = {"campionato": "Campionato", "pos": "Pos", "squadra": "Squadra",
              "punti_classifica": "Pt", "partite": "PG", "vinte": "V", "perse_partite": "P",
              "punti": "PF", "punti_subiti": "PS", "diff": "Diff", "ortg": "ORtg",
              "drtg": "DRtg", "net_rtg": "Net Rtg"}


def _label_league(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["campionato"] = df["campionato_id"].map(config.CAMPIONATI).fillna(df["campionato_id"])
    return df


def select(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    df = _label_league(df) if "campionato_id" in df.columns else df
    cols = [c for c in mapping if c in df.columns]
    return df[cols].rename(columns=mapping)


def casa_trasferta_squadre(bs: pd.DataFrame) -> pd.DataFrame:
    t = A.team_summary(bs, by=["casa"])
    t["dove"] = t["casa"].map({1: "Casa", 0: "Trasferta"})
    return select(t.sort_values(["campionato_id", "squadra", "casa"], ascending=[True, True, False]),
                  {"campionato": "Campionato", "squadra": "Squadra", "dove": "Dove",
                   "partite": "PG", "vinte": "V", "perse_partite": "P", "punti_pg": "Punti",
                   "punti_subiti_pg": "Subiti", "ortg": "ORtg", "drtg": "DRtg",
                   "net_rtg": "Net Rtg", "efg_pct": "eFG%", "tov_pct": "TOV%",
                   "orb_pct": "OREB%"})


def casa_trasferta_giocatori(bg: pd.DataFrame, bs: pd.DataFrame) -> pd.DataFrame:
    p = A.player_summary(bg, bs, by=["casa"])
    p["dove"] = p["casa"].map({1: "Casa", 0: "Trasferta"})
    return select(p.sort_values(["campionato_id", "squadra", "giocatore", "casa"],
                                ascending=[True, True, True, False]),
                  {"campionato": "Campionato", "giocatore": "Giocatore", "squadra": "Squadra",
                   "dove": "Dove", "partite": "PG", "minuti_pg": "Min", "punti_pg": "Punti",
                   "rimb_tot_pg": "RT", "assist_pg": "Ass", "valutazione_pg": "Val",
                   "efg_pct": "eFG%", "ts_pct": "TS%", "usg_pct": "USG%"})


def partite(conn, stagione: str | None = None) -> pd.DataFrame:
    df = pd.read_sql_query(
        """SELECT p.partita_id, p.campionato_id, p.giornata, p.data, sc.nome AS casa, p.punti_casa,
                  p.punti_ospite, so.nome AS ospite, p.palazzetto, p.url
           FROM partite p
           JOIN squadre sc ON sc.squadra_id = p.squadra_casa_id
           JOIN squadre so ON so.squadra_id = p.squadra_ospite_id
           WHERE (:s IS NULL OR p.stagione = :s)
           ORDER BY p.campionato_id, p.giornata, p.data""", conn, params={"s": stagione})
    df = df.merge(A.game_quality(conn, stagione), on="partita_id", how="left")
    df["completo"] = df["affidabile"].map({True: "Sì", False: "No (escluso da avanzate)"})
    return select(df, {"campionato": "Campionato", "giornata": "Giornata", "data": "Data",
                       "casa": "Casa", "punti_casa": "PC", "punti_ospite": "PO",
                       "ospite": "Ospite", "palazzetto": "Palazzetto",
                       "completo": "Box score completo", "url": "Box score"})
