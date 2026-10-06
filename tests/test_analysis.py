from pathlib import Path

import pytest

from basket import analysis as A
from basket import db, export_excel, scouting
from basket.scraper import parse_boxscore

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture
def conn(tmp_path):
    conn = db.connect(tmp_path / "t.sqlite")
    box = parse_boxscore((FIX / "boxscore_ita2_412.html").read_text(encoding="utf-8"))
    game = dict(gameid="ita2_412", campionato="ita2", stagione="x2627", giornata=2,
                data="2026-10-03", ora="20:30", squadra_casa_id=10050,
                squadra_casa="Unieuro Forlì", squadra_ospite_id=100118,
                squadra_ospite="Sella Cento", punti_casa=80, punti_ospite=73,
                palazzetto="Unieuro Arena", stato="finished")
    db.upsert_campionato(conn, "ita2", "x2627", "Serie A2")
    db.save_calendario(conn, [game])
    db.save_partita(conn, game, box, "url")
    return conn


def test_team_ratings(conn):
    t = A.team_summary(A.load_box_squadra(conn)).set_index("squadra_id")
    forli, cento = t.loc[10050], t.loc[100118]
    # Possessi identici per le due squadre; ORtg di una = DRtg dell'altra
    assert forli["possessi"] == pytest.approx(cento["possessi"])
    assert forli["ortg"] == pytest.approx(cento["drtg"])
    assert forli["net_rtg"] == pytest.approx(-cento["net_rtg"])
    # Possessi: Forlì 60 FGA - 10 OREB + 13 TOV + 0.44*20 = 71.8; Cento 65-13+14+7.04 = 73.04
    assert forli["possessi"] == pytest.approx((71.8 + 73.04) / 2)
    assert forli["efg_pct"] == pytest.approx(100 * (27 + 5) / 60)
    assert forli["orb_pct"] + cento["drb_pct"] == pytest.approx(100)


def test_player_metrics(conn):
    bs, bg = A.load_box_squadra(conn), A.load_box_giocatore(conn)
    p = A.player_summary(bg, bs)
    # L'usage medio pesato sui minuti è ~20% (5 giocatori in campo)
    for _, g in p.groupby("squadra_id"):
        assert (g["usg_pct"] * g["minuti"]).sum() / g["minuti"].sum() == pytest.approx(20, abs=0.5)
    woodson = p[p["giocatore"] == "Avery Woodson"].iloc[0]
    assert woodson["ts_pct"] == pytest.approx(100 * 26 / (2 * (14 + 0.44 * 4)))
    assert woodson["punti_p40"] == pytest.approx(26 * 40 / 33)
    # Chi non è entrato non viene conteggiato
    assert p["partite"].min() == 1 and (p["minuti"] > 0).all()


def test_report_and_excel(conn, tmp_path):
    r = scouting.build_report(conn, 10050)
    assert r.record == "1-0" and r.posizione == 1
    assert "Scouting: Unieuro Forlì" in scouting.to_markdown(r)
    sheets = export_excel.build_sheets(conn)
    export_excel.write_excel(sheets, tmp_path / "r.xlsx")
    assert (tmp_path / "r.xlsx").stat().st_size > 0
    assert len(sheets["Giocatori medie"]) == 20
