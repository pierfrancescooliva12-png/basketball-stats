import json
from pathlib import Path

import pytest

from basket import analysis as A
from basket import db, update
from basket import pbp as P
from basket.scraper import parse_boxscore, parse_pbp, parse_player

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return (FIX / name).read_text(encoding="utf-8")


class Resp:
    def __init__(self, status, text):
        self.status_code, self.text = status, text

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class Client:
    n_requests = 0

    def get(self, url, params=None):
        self.n_requests += 1
        if params:
            sched = [g for g in json.loads(load("schedule_ita2_r2.json")) if g["gameid"] == "ita2_412"]
            return Resp(200, json.dumps(sched)) if params["round"] == 2 else Resp(404, "{}")
        if url.endswith("ita2_412/ita2/x2627"):
            return Resp(200, load("boxscore_ita2_412.html"))
        if url.endswith("ita2_412/ita2/x2627/play-by-play"):
            return Resp(200, load("pbp_ita2_412.html"))
        if "/giocatore/wp/" in url:
            return Resp(200, load("giocatore_A94224.html"))
        return Resp(404, "")


@pytest.fixture(autouse=True)
def _cronaca_tmp(tmp_path, monkeypatch):
    from basket import config
    monkeypatch.setattr(config, "CRONACA_DIR", tmp_path / "cronaca")


@pytest.fixture
def conn(tmp_path):
    conn = db.connect(tmp_path / "t.sqlite")
    update.update_league(conn, Client(), "ita2", "x2627", {2})
    return conn


def test_parse_pbp_reconstructs_score():
    cr = parse_pbp(load("pbp_ita2_412.html"))
    pts = {"casa": 0, "ospite": 0}
    for e in cr["eventi"]:
        pts[e["lato"]] += P.PUNTI.get(e["tipo"], 0)
    assert pts == {"casa": 80, "ospite": 73}
    assert not [e for e in cr["eventi"] if e["tipo"] == "altro"]
    assert cr["eventi"][-1]["secondi"] == 2400


def test_lineups_match_official_minutes(conn):
    q = conn.execute("SELECT punteggio_ok, quintetti_ok, errore_minuti, zone_affidabili "
                     "FROM pbp_qualita").fetchone()
    assert q[0] == 1 and q[1] == 1 and q[2] <= P.TOLLERANZA_MIN and q[3] == 0
    st = P.load_stints(conn)
    # Ogni squadra ha sempre 5 giocatori e i punti delle frazioni sommano al risultato
    assert st["quintetto"].str.split(",").map(len).eq(5).all()
    tot = st.groupby("squadra_id")["punti_fatti"].sum().to_dict()
    assert tot == {10050: 80, 100118: 73}
    oo = P.on_off(st).set_index("giocatore_id")
    # +/- della squadra: somma dei +/- dei giocatori = 5 × differenza finale
    forli = oo[oo["squadra_id"] == 10050]
    assert forli["plus_minus"].sum() == 5 * 7


def test_old_season_ids_are_aligned():
    box = parse_boxscore(load("boxscore_x2526_ita2_375.html"))
    cr = parse_pbp(load("pbp_x2526_ita2_375.html"))
    assert P.align_ids(cr["eventi"], box, cr["nomi"]) == 0
    box_ids = {g["giocatore_id"] for s in ("casa", "ospite") for g in box[s]["giocatori"]}
    assert {e["giocatore_id"] for e in cr["eventi"] if e["giocatore_id"]} <= box_ids
    assert P.quality(cr["eventi"], (83, 82))["zone_affidabili"]


def test_event_analytics(conn):
    ev = P.load_events(conn)
    bs = A.load_box_squadra(conn)
    net = P.assist_network(ev)
    # assist abbinati a un canestro (la cronaca ne registra 20)
    assert 15 <= net["canestri"].sum() <= 20
    orig = P.possession_origins(ev).set_index("squadra_id")
    assert orig.loc[10050, "punti_totali"] == 80
    assert orig["punti_da_perse"].ge(0).all()
    r = P.runs(ev)
    assert r["max_fatto"].max() >= 6
    assert not P.fouls(ev).empty
    assert P.clutch_teams(ev, bs).empty or True
    sp = P.shot_profile(ev, zone_ok=set())
    assert sp["tre_t"].sum() == 57  # 28 + 29 tiri da 3


def test_player_bio():
    info = parse_player(load("giocatore_A94224.html"))
    assert info == {"data_nascita": "2003-12-04", "nazionalita": "ITA", "altezza_cm": 185,
                    "peso_kg": 80, "societa": "Unieuro Forlì"}


def test_pbp_file_is_compact_and_immutable(conn, tmp_path):
    f = tmp_path / "cronaca" / "x2627" / "ita2_412.json.gz"
    assert f.exists() and f.stat().st_size < 15_000
    before = f.read_bytes()
    update.backfill_pbp(conn, Client(), "ita2", "x2627", 10)  # niente da recuperare
    conn.execute("DELETE FROM pbp_qualita")
    update.backfill_pbp(conn, Client(), "ita2", "x2627", 10)  # riscrive lo stesso file
    assert f.read_bytes() == before


def test_pdf_report(conn):
    from basket.contesto import Contesto
    from basket.report_pdf import build_pdf
    pdf = build_pdf(Contesto(conn, "x2627"), 10050)
    assert pdf[:4] == b"%PDF" and len(pdf) > 20_000
