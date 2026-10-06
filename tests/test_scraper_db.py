import json
from pathlib import Path

import pytest

from basket import db, update
from basket.scraper import ParseError, parse_boxscore, parse_schedule

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_parse_boxscore_totals_consistent():
    box = parse_boxscore(load("boxscore_ita2_412.html"))
    assert box["casa"]["nome"] == "Unieuro Forlì"
    assert box["casa"]["id"] == 10050
    assert box["ospite"]["id"] == 100118
    assert box["casa"]["totali"]["punti"] == 80
    assert box["ospite"]["totali"]["punti"] == 73
    for side in ("casa", "ospite"):
        team = box[side]
        assert sum(p["punti"] for p in team["giocatori"]) == team["totali"]["punti"]
        assert sum(p["minuti"] or 0 for p in team["giocatori"]) == pytest.approx(200)
        assert sum(p["t3m"] for p in team["giocatori"]) == team["totali"]["t3m"]
    assert [p["casa"] for p in box["parziali"]] == [31, 16, 18, 15]
    first = box["casa"]["giocatori"][0]
    assert first["giocatore_id"] == "A402160"
    assert first["quintetto"] is True
    assert (first["t2m"], first["t2a"], first["rimb_dif"]) == (4, 8, 4)


def test_parse_boxscore_rejects_unexpected_page():
    with pytest.raises(ParseError):
        parse_boxscore("<html><body>pagina cambiata</body></html>")


class FakeResponse:
    def __init__(self, status, text):
        self.status_code = status
        self.text = text

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeClient:
    """Serve la giornata 2 di A2 dal JSON salvato; box score solo per ita2_412."""

    def __init__(self):
        self.n_requests = 0
        self.urls = []
        sched = json.loads(load("schedule_ita2_r2.json"))
        self.schedule = [g for g in sched if g["gameid"] == "ita2_412"]

    def get(self, url, params=None):
        self.n_requests += 1
        self.urls.append((url, params))
        if params and params.get("task") == "schedule":
            if params["round"] == 2:
                return FakeResponse(200, json.dumps(self.schedule))
            return FakeResponse(404, '{"error":{"code":"102"}}')
        if url.endswith("/wp/match/ita2_412/ita2/x2627"):
            return FakeResponse(200, load("boxscore_ita2_412.html"))
        return FakeResponse(404, "")


def test_update_is_incremental(tmp_path, monkeypatch):
    from basket import config
    monkeypatch.setattr(config, "CRONACA_DIR", tmp_path / "cronaca")
    conn = db.connect(tmp_path / "t.sqlite")
    client = FakeClient()
    s = update.update_league(conn, client, "ita2", "x2627", {2})
    assert s["nuove"] == 1 and not s["errori"]
    row = conn.execute("SELECT punti_casa, punti_ospite FROM partite").fetchone()
    assert row == (80, 73)
    n_box = conn.execute("SELECT COUNT(*) FROM box_giocatore").fetchone()[0]
    assert n_box == 22
    bs = conn.execute(
        "SELECT casa, punti, punti_subiti, perse, perse_squadra FROM box_squadra "
        "ORDER BY casa DESC").fetchall()
    assert bs[0] == (1, 80, 73, 13, 0)
    assert bs[1] == (0, 73, 80, 14, 1)

    # Secondo giro: giornata completa, nessuna nuova richiesta al sito
    before = client.n_requests
    s = update.update_league(conn, client, "ita2", "x2627", {2})
    assert s["nuove"] == 0
    assert client.n_requests == before


def test_parse_schedule_and_giornate():
    games = parse_schedule(json.loads(load("schedule_ita2_r2.json")), "ita2", "x2627")
    assert len(games) == 10
    assert games[0]["data"] == "2026-10-03"
    assert update.parse_giornate("1-2") == {1, 2}
    assert update.parse_giornate("1,3,5-6") == {1, 3, 5, 6}
