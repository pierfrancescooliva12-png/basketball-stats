"""Contesto di analisi di una stagione: carica i dati una volta e calcola su richiesta
tutte le analisi (box score, cronaca, previsioni, avvisi). Usato da dashboard e report PDF."""

from functools import cached_property

import pandas as pd

from . import analysis as A
from . import approfondimenti as X
from . import avvisi, config, db
from . import pbp as P
from . import previsioni as F


class Contesto:
    def __init__(self, conn, stagione: str = config.STAGIONE):
        self.conn = conn
        self.stagione = stagione

    # ---------------------------------------------------------------- box score
    @cached_property
    def bs(self) -> pd.DataFrame:
        return A.load_box_squadra(self.conn, self.stagione)

    @cached_property
    def bg(self) -> pd.DataFrame:
        return A.load_box_giocatore(self.conn, self.stagione)

    @cached_property
    def quarters(self) -> pd.DataFrame:
        return A.load_quarters(self.conn, self.stagione)

    @cached_property
    def players(self) -> pd.DataFrame:
        p = A.player_summary(self.bg, self.bs)
        oo = self.on_off
        if not oo.empty:
            p = p.merge(oo[["squadra_id", "giocatore_id", "plus_minus", "plus_minus_40",
                            "net_on", "net_off", "on_off", "minuti_campo"]],
                        on=["squadra_id", "giocatore_id"], how="left")
        return p

    @cached_property
    def profile(self) -> pd.DataFrame:
        prof = A.team_profile(self.bs, self.bg, self.quarters)
        for extra in (self.origins, self.runs_, self.clutch_teams, self.bonus, self.timeouts_):
            if extra is not None and not extra.empty:
                cols = [c for c in extra.columns if c not in prof.columns or c == "squadra_id"]
                prof = prof.merge(extra[cols], on="squadra_id", how="left")
        return prof

    @cached_property
    def nomi_giocatori(self) -> dict:
        return dict(self.conn.execute("SELECT giocatore_id, nome FROM giocatori").fetchall())

    @cached_property
    def nomi_squadre(self) -> dict:
        return dict(self.conn.execute("SELECT squadra_id, nome FROM squadre").fetchall())

    # ---------------------------------------------------------------- cronaca
    @cached_property
    def ev(self) -> pd.DataFrame:
        return P.load_events(self.conn, self.stagione)

    @cached_property
    def stints(self) -> pd.DataFrame:
        return P.load_stints(self.conn, self.stagione)

    @cached_property
    def copertura(self) -> pd.DataFrame:
        return P.coverage(self.conn, self.stagione)

    @cached_property
    def zone_ok(self) -> set:
        if not P._has_table(self.conn, "pbp_qualita"):
            return set()
        return {r[0] for r in self.conn.execute(
            "SELECT q.partita_id FROM pbp_qualita q JOIN partite p USING (partita_id) "
            "WHERE q.zone_affidabili = 1 AND p.stagione = ?", (self.stagione,))}

    def _ev(self, fn, *args):
        return fn(self.ev, *args) if not self.ev.empty else pd.DataFrame()

    @cached_property
    def on_off(self) -> pd.DataFrame:
        return P.on_off(self.stints) if not self.stints.empty else pd.DataFrame()

    @cached_property
    def lineups(self) -> pd.DataFrame:
        lu = P.lineups(self.stints) if not self.stints.empty else pd.DataFrame()
        if not lu.empty:
            lu["giocatori"] = lu["quintetto"].map(lambda q: P.name_lineup(q, self.nomi_giocatori))
        return lu

    @cached_property
    def clutch_players(self) -> pd.DataFrame:
        c = self._ev(P.clutch_players)
        if not c.empty:
            c["giocatore"] = c["giocatore_id"].map(self.nomi_giocatori)
        return c

    @cached_property
    def clutch_teams(self) -> pd.DataFrame:
        return P.clutch_teams(self.ev, self.bs) if not self.ev.empty else pd.DataFrame()

    @cached_property
    def assists(self) -> pd.DataFrame:
        a = self._ev(P.assist_network)
        if not a.empty:
            a["da"] = a["assistente"].map(self.nomi_giocatori)
            a["a"] = a["realizzatore"].map(self.nomi_giocatori)
        return a

    @cached_property
    def origins(self) -> pd.DataFrame:
        return self._ev(P.possession_origins)

    @cached_property
    def runs_(self) -> pd.DataFrame:
        return self._ev(P.runs)

    @cached_property
    def fouls(self) -> pd.DataFrame:
        f = self._ev(P.fouls)
        if not f.empty:
            f["giocatore"] = f["giocatore_id"].map(self.nomi_giocatori)
        return f

    @cached_property
    def bonus(self) -> pd.DataFrame:
        return self._ev(P.team_fouls_bonus)

    @cached_property
    def timeouts_(self) -> pd.DataFrame:
        return self._ev(P.timeouts)

    @cached_property
    def shots(self) -> pd.DataFrame:
        s = self._ev(P.shot_profile, self.zone_ok)
        if not s.empty:
            s["giocatore"] = s["giocatore_id"].map(self.nomi_giocatori)
        return s

    # ---------------------------------------------------------------- approfondimenti
    @cached_property
    def altezze(self) -> dict:
        if not P._has_table(self.conn, "giocatori_info"):
            return {}
        return {g: h for g, h in self.conn.execute(
            "SELECT giocatore_id, altezza_cm FROM giocatori_info WHERE altezza_cm > 150")}

    @cached_property
    def rotazioni(self) -> dict:
        return X.rotazioni(self.stints)

    @cached_property
    def taglie(self) -> pd.DataFrame:
        return X.taglia_quintetti(self.stints, self.altezze)

    @cached_property
    def momenti(self) -> pd.DataFrame:
        return X.momenti(self.ev)

    @cached_property
    def origini_partita(self) -> pd.DataFrame:
        return self._ev(P.origins_by_game)

    @cached_property
    def origini_concesse(self) -> pd.DataFrame:
        return X.origini_concesse(self.origini_partita, self.ev) if not self.ev.empty \
            else pd.DataFrame()

    @cached_property
    def partite(self) -> pd.DataFrame:
        return pd.read_sql_query(
            "SELECT partita_id, campionato_id, giornata, data, squadra_casa_id, "
            "squadra_ospite_id, palazzetto FROM partite WHERE stagione = ?",
            self.conn, params=(self.stagione,))

    @cached_property
    def calendario_fisico(self) -> pd.DataFrame:
        return X.calendario_fisico(self.bs, self.partite)

    @cached_property
    def presenze(self) -> pd.DataFrame:
        return X.presenze(self.bg, self.bs)

    # ---------------------------------------------------------------- previsioni e avvisi
    @cached_property
    def alerts(self) -> pd.DataFrame:
        return avvisi.alerts(self.bs, self.bg) if not self.bs.empty else pd.DataFrame()

    def forze(self, campionato_id: str) -> pd.DataFrame:
        bs = self.bs[self.bs["campionato_id"] == campionato_id]
        return F.strengths(bs, self._prior)

    @cached_property
    def _prior(self) -> dict:
        return F.prior_from_previous(self.conn, self.stagione)

    def hca(self, campionato_id: str) -> float:
        return F.home_advantage(self.conn, campionato_id)

    def next_game(self, squadra_id: int) -> dict | None:
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(calendario)")}
        stream = "c.stream_url" if "stream_url" in cols else "NULL"
        r = self.conn.execute(
            f"""SELECT c.partita_id, c.giornata, c.data, c.ora, c.squadra_casa_id,
                      c.squadra_ospite_id, c.campionato_id, {stream}
               FROM calendario c WHERE c.stagione = ? AND c.stato != 'finished'
                 AND (c.squadra_casa_id = ? OR c.squadra_ospite_id = ?)
               ORDER BY c.data, c.ora LIMIT 1""",
            (self.stagione, squadra_id, squadra_id)).fetchone()
        if not r:
            return None
        keys = ["partita_id", "giornata", "data", "ora", "casa_id", "ospite_id",
                "campionato_id", "stream_url"]
        g = dict(zip(keys, r))
        g["casa"] = self.nomi_squadre.get(g["casa_id"])
        g["ospite"] = self.nomi_squadre.get(g["ospite_id"])
        try:
            g["previsione"] = F.predict(self.forze(g["campionato_id"]), g["casa_id"],
                                        g["ospite_id"], self.hca(g["campionato_id"]))
        except KeyError:
            g["previsione"] = None
        return g

    def simulation(self, campionato_id: str, n: int = 5000) -> pd.DataFrame:
        return F.simulate(self.conn, campionato_id, self.stagione, n=n)


def open_readonly(stagione: str = config.STAGIONE) -> Contesto:
    return Contesto(db.connect(config.DB_PATH, readonly=True), stagione)
