"""Report di scouting su una squadra avversaria.

    python -m basket.scouting "Forlì"          # scrive reports/scouting_<squadra>.md
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field

import pandas as pd

from . import analysis as A
from . import config, db

# metrica -> (etichetta, True se "più alto è meglio")
FACTORS = {
    "ortg": ("Rating offensivo (ORtg)", True),
    "drtg": ("Rating difensivo (DRtg)", False),
    "net_rtg": ("Net rating", True),
    "pace": ("Ritmo (possessi/40')", None),
    "efg_pct": ("eFG% in attacco", True),
    "tov_pct": ("Palle perse % in attacco", False),
    "orb_pct": ("Rimbalzi offensivi %", True),
    "ft_rate": ("Liberi segnati / tiri dal campo", True),
    "opp_efg_pct": ("eFG% concessa", False),
    "opp_tov_pct": ("Palle perse forzate %", True),
    "drb_pct": ("Rimbalzi difensivi %", True),
    "opp_ft_rate": ("Liberi concessi / tiri avversari", False),
    "t3_pct": ("% da 3", True),
    "quota_tiri_3": ("Quota tiri da 3 su tiri dal campo", None),
    "ast_ratio": ("Assist ratio", True),
}


@dataclass
class ScoutingReport:
    squadra: str
    campionato: str
    record: str
    posizione: int | None
    profilo: pd.DataFrame
    giocatori: pd.DataFrame
    ultime: pd.DataFrame
    casa_trasferta: pd.DataFrame
    periodi: pd.DataFrame
    punti_forza: list[str] = field(default_factory=list)
    punti_deboli: list[str] = field(default_factory=list)
    prossima: str | None = None


def build_report(conn, squadra_id: int) -> ScoutingReport:
    bs = A.load_box_squadra(conn)
    bg = A.load_box_giocatore(conn)
    team_rows = bs[bs["squadra_id"] == squadra_id]
    if team_rows.empty:
        raise ValueError("Nessuna partita giocata per questa squadra")
    camp = team_rows["campionato_id"].iloc[0]
    bs_c = bs[bs["campionato_id"] == camp]

    tot = A.team_summary(bs_c)
    tot["quota_tiri_3"] = 100 * tot["t3a"] / (tot["t2a"] + tot["t3a"])
    me = tot[tot["squadra_id"] == squadra_id].iloc[0]
    n = len(tot)

    rows, forza, deboli = [], [], []
    for col, (label, higher_better) in FACTORS.items():
        val, media = me[col], tot[col].mean()
        asc = False if higher_better is None else not higher_better
        r = tot[col].rank(ascending=asc, method="min")[me.name]
        rank = int(r) if pd.notna(r) else None
        rows.append({"Metrica": label, "Valore": val, "Media campionato": media,
                     "Posizione": f"{rank}/{n}" if rank else "-"})
        if higher_better is not None and n >= 4 and rank:
            fmt = ".2f" if col.endswith("ft_rate") else ".1f"
            testo = f"{label}: {val:{fmt}} ({rank}° su {n}, media {media:{fmt}})"
            if rank <= max(1, round(n * 0.25)):
                forza.append(testo)
            elif rank > n - max(1, round(n * 0.25)):
                deboli.append(testo)
    profilo = pd.DataFrame(rows)

    pl = A.player_summary(bg[bg["squadra_id"] == squadra_id], bs)
    pl = pl.sort_values("minuti", ascending=False)
    giocatori = pl[["giocatore", "partite", "quintetti", "minuti_pg", "punti_pg", "rimb_tot_pg",
                    "assist_pg", "perse_pg", "t3m_pg", "t3_pct", "ts_pct", "usg_pct",
                    "valutazione_pg"]].rename(columns={
        "giocatore": "Giocatore", "partite": "PG", "quintetti": "Quint.", "minuti_pg": "Min",
        "punti_pg": "Punti", "rimb_tot_pg": "Rimb", "assist_pg": "Ass", "perse_pg": "Perse",
        "t3m_pg": "3PM", "t3_pct": "3P%", "ts_pct": "TS%", "usg_pct": "USG%",
        "valutazione_pg": "Val"})

    last = A.team_ratings(team_rows.tail(5).copy())
    ultime = pd.DataFrame({
        "Data": last["data"], "G.": last["giornata"],
        "Avversario": last["avversario"],
        "Dove": last["casa"].map({1: "Casa", 0: "Trasferta"}),
        "Risultato": [f"{'V' if v else 'P'} {p}-{s}" for v, p, s in
                      zip(last["vinta"], last["punti"], last["punti_subiti"])],
        "ORtg": last["ortg"].where(last["affidabile"]),
        "DRtg": last["drtg"].where(last["affidabile"]),
        "eFG%": last["efg_pct"].where(last["affidabile"]),
        "Note": last["affidabile"].map({True: "", False: "box score incompleto"}),
    }).iloc[::-1]

    split = A.team_summary(team_rows, by=["casa"])
    casa_trasferta = pd.DataFrame({
        "Dove": split["casa"].map({1: "Casa", 0: "Trasferta"}),
        "Partite": split["partite"],
        "V-P": [f"{v}-{p}" for v, p in zip(split["vinte"], split["perse_partite"])],
        "Punti fatti": split["punti_pg"], "Punti subiti": split["punti_subiti_pg"],
        "ORtg": split["ortg"], "DRtg": split["drtg"], "eFG%": split["efg_pct"],
    })

    periodi = _periods(conn, squadra_id)
    pos = A.standings(bs_c)
    posizione = int(pos.loc[pos["squadra_id"] == squadra_id, "pos"].iloc[0])

    return ScoutingReport(
        squadra=me["squadra"], campionato=config.CAMPIONATI.get(camp, camp),
        record=f"{int(me['vinte'])}-{int(me['perse_partite'])}", posizione=posizione,
        profilo=profilo, giocatori=giocatori, ultime=ultime, casa_trasferta=casa_trasferta,
        periodi=periodi, punti_forza=forza, punti_deboli=deboli,
        prossima=_next_game(conn, squadra_id),
    )


def _periods(conn, squadra_id: int) -> pd.DataFrame:
    rows = conn.execute(
        "SELECT squadra_casa_id, parziali FROM partite "
        "WHERE squadra_casa_id = ? OR squadra_ospite_id = ?", (squadra_id, squadra_id)).fetchall()
    data = []
    for casa_id, parz in rows:
        side, other = ("casa", "ospite") if casa_id == squadra_id else ("ospite", "casa")
        for p in json.loads(parz or "[]"):
            label = f"Q{p['periodo']}" if p["periodo"] <= 4 else f"OT{p['periodo'] - 4}"
            data.append({"Periodo": label, "Fatti": p[side], "Subiti": p[other]})
    if not data:
        return pd.DataFrame(columns=["Periodo", "Fatti", "Subiti", "Diff"])
    df = pd.DataFrame(data).groupby("Periodo", sort=False)[["Fatti", "Subiti"]].mean()
    df["Diff"] = df["Fatti"] - df["Subiti"]
    return df.reset_index()


def _next_game(conn, squadra_id: int) -> str | None:
    row = conn.execute(
        """SELECT c.data, c.ora, c.giornata, sc.nome, so.nome FROM calendario c
           JOIN squadre sc ON sc.squadra_id = c.squadra_casa_id
           JOIN squadre so ON so.squadra_id = c.squadra_ospite_id
           WHERE (c.squadra_casa_id = ? OR c.squadra_ospite_id = ?)
             AND c.stato != 'finished'
           ORDER BY c.data, c.ora LIMIT 1""", (squadra_id, squadra_id)).fetchone()
    if not row:
        return None
    data, ora, giornata, casa, ospite = row
    return f"{giornata}ª giornata, {data} {ora or ''}: {casa} - {ospite}".strip()


def to_markdown(r: ScoutingReport) -> str:
    def table(df):
        return df.to_markdown(index=False, floatfmt=".1f")

    lines = [
        f"# Scouting: {r.squadra}",
        f"{r.campionato} {config.STAGIONE_LABEL} · Record {r.record} · {r.posizione}° posto",
    ]
    if r.prossima:
        lines.append(f"Prossima partita: {r.prossima}")
    lines += ["", "## Punti di forza"] + [f"- {x}" for x in r.punti_forza or ["(nessuno marcato)"]]
    lines += ["", "## Punti deboli"] + [f"- {x}" for x in r.punti_deboli or ["(nessuno marcato)"]]
    lines += ["", "## Profilo di squadra", table(r.profilo),
              "", "## Giocatori (per minuti giocati)", table(r.giocatori),
              "", "## Ultime 5 partite", table(r.ultime),
              "", "## Casa / trasferta", table(r.casa_trasferta),
              "", "## Punti medi per periodo", table(r.periodi), ""]
    return "\n".join(lines)


def find_team(conn, query: str) -> list[tuple[int, str]]:
    return conn.execute("SELECT squadra_id, nome FROM squadre WHERE nome LIKE ? ORDER BY nome",
                        (f"%{query}%",)).fetchall()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Report di scouting su una squadra")
    ap.add_argument("squadra", help="nome (anche parziale) della squadra")
    args = ap.parse_args(argv)
    conn = db.connect(config.DB_PATH, readonly=True)
    teams = find_team(conn, args.squadra)
    if len(teams) != 1:
        print("Squadre trovate:", ", ".join(n for _, n in teams) or "nessuna")
        return 1
    report = build_report(conn, teams[0][0])
    config.REPORTS_DIR.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", teams[0][1].lower()).strip("_")
    out = config.REPORTS_DIR / f"scouting_{slug}.md"
    out.write_text(to_markdown(report), encoding="utf-8")
    print(f"Scritto {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
